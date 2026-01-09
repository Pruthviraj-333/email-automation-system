"""
Authentication and User Management System
"""
import os
import uuid
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, EmailStr, validator
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.orm import Session
import logging

from db_updated import Base, SessionLocal, engine

logger = logging.getLogger(__name__)

# Security Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-super-secret-key-change-this-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


# Database Models
class UserModel(Base):
    __tablename__ = "users"
    
    id = Column(String(255), primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for Google login
    name = Column(String(255), nullable=False)
    google_id = Column(String(255), unique=True, nullable=True, index=True)  # NEW
    picture = Column(String(512), nullable=True)  # NEW: Profile picture
    auth_provider = Column(String(50), default='email')  # NEW: 'email' or 'google'
    gmail_connected = Column(Boolean, default=False)
    gmail_email = Column(String(255), nullable=True)
    gmail_refresh_token = Column(Text, nullable=True)
    gmail_access_token = Column(Text, nullable=True)
    gmail_token_expiry = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)


# Pydantic Models
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: str
    
    @validator('password')
    def validate_password(cls, v):
        if len(v) < 6:
            raise ValueError('Password must be at least 6 characters long')
        if len(v) > 72:
            raise ValueError('Password cannot be longer than 72 characters')
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    picture: Optional[str] = None
    auth_provider: str
    gmail_connected: bool
    gmail_email: Optional[str] = None
    created_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserResponse


# Create tables
Base.metadata.create_all(bind=engine)


# Helper Functions
def get_db():
    """Get database session"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    # Bcrypt has a 72 byte limit, truncate if necessary
    if len(plain_password.encode('utf-8')) > 72:
        plain_password = plain_password[:72]
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password"""
    # Bcrypt has a 72 byte limit, truncate if necessary
    if len(password.encode('utf-8')) > 72:
        password = password[:72]
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user_by_email(db: Session, email: str) -> Optional[UserModel]:
    """Get user by email"""
    return db.query(UserModel).filter(UserModel.email == email).first()


def get_user_by_id(db: Session, user_id: str) -> Optional[UserModel]:
    """Get user by ID"""
    return db.query(UserModel).filter(UserModel.id == user_id).first()


def create_user(db: Session, user: UserCreate) -> UserModel:
    """Create new user"""
    # Check if user already exists
    existing_user = get_user_by_email(db, user.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create new user
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(user.password)
    
    db_user = UserModel(
        id=user_id,
        email=user.email,
        hashed_password=hashed_password,
        name=user.name,
        gmail_connected=False
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"Created new user: {user.email}")
    return db_user


def authenticate_user(db: Session, email: str, password: str) -> Optional[UserModel]:
    """Authenticate user with email and password"""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> UserModel:
    """Get current authenticated user from JWT token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = get_user_by_id(db, user_id)
    if user is None:
        raise credentials_exception
    
    return user


def get_user_by_google_id(db: Session, google_id: str) -> Optional[UserModel]:
    """Get user by Google ID"""
    return db.query(UserModel).filter(UserModel.google_id == google_id).first()


def create_user_from_google(db: Session, google_data: dict) -> UserModel:
    """Create new user from Google OAuth data"""
    # Check if user already exists by email
    existing_user = get_user_by_email(db, google_data['email'])
    if existing_user:
        # Update with Google ID if not set
        if not existing_user.google_id:
            existing_user.google_id = google_data['google_id']
            existing_user.picture = google_data.get('picture')
            existing_user.auth_provider = 'google'
            db.commit()
            db.refresh(existing_user)
        return existing_user
    
    # Create new user
    user_id = str(uuid.uuid4())
    
    db_user = UserModel(
        id=user_id,
        email=google_data['email'],
        hashed_password=None,  # No password for Google login
        name=google_data['name'],
        google_id=google_data['google_id'],
        picture=google_data.get('picture'),
        auth_provider='google',
        gmail_connected=False
    )
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"Created new user from Google: {google_data['email']}")
    return db_user


def user_to_response(user: UserModel) -> UserResponse:
    """Convert UserModel to UserResponse"""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        picture=user.picture,
        auth_provider=user.auth_provider,
        gmail_connected=user.gmail_connected,
        gmail_email=user.gmail_email,
        created_at=user.created_at
    )


def update_gmail_tokens(
    db: Session,
    user_id: str,
    gmail_email: str,
    access_token: str,
    refresh_token: Optional[str] = None,
    token_expiry: Optional[datetime] = None
):
    """Update user's Gmail tokens"""
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.gmail_connected = True
    user.gmail_email = gmail_email
    user.gmail_access_token = access_token
    
    if refresh_token:
        user.gmail_refresh_token = refresh_token
    
    if token_expiry:
        user.gmail_token_expiry = token_expiry
    
    db.commit()
    db.refresh(user)
    
    logger.info(f"Updated Gmail tokens for user: {user.email}")
    return user