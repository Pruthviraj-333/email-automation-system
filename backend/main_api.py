"""
Complete Multi-User Email Automation API
Supports user authentication, Gmail OAuth, and per-user email processing
"""
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends, Body, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
from datetime import datetime
import logging
import secrets
from contextlib import asynccontextmanager

# Import our modules
from db_updated import Database
from user_gmail_client import create_gmail_client_for_user
from llm_client import LLMClient
from models import EmailAnalysis, EmailDecision, EmailResponse
from config import MAX_EMAILS_PER_CHECK
from auth import (
    UserCreate, UserLogin, Token, UserResponse,
    create_user, authenticate_user, create_access_token,
    get_current_user, user_to_response, update_gmail_tokens,
    get_db, UserModel
)
from gmail_oauth import gmail_oauth

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global instances
db = None
llm = None

# In-memory storage for OAuth states and pending responses
oauth_states: Dict[str, str] = {}  # state -> user_id
pending_responses: Dict[str, Dict] = {}  # user_id -> {email_id -> PendingResponse}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    global db, llm
    logger.info("🚀 Initializing services...")
    db = Database()
    llm = LLMClient()
    logger.info("✅ Services initialized successfully")
    yield
    logger.info("🛑 Shutting down services...")


app = FastAPI(
    title="Email Automation API",
    description="Multi-user AI-powered email automation with Gmail OAuth",
    version="2.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
#    allow_origins=["http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# PYDANTIC MODELS
# ============================================================================

class EmailItem(BaseModel):
    id: str
    subject: str
    sender: str
    body: str
    preview: str
    thread_id: Optional[str] = None
    received_date: Optional[str] = None


class PendingResponse(BaseModel):
    email_id: str
    subject: str
    sender: str
    body_preview: str
    body_full: str
    category: str
    priority: int
    sentiment: str
    draft_response: str
    edited_response: Optional[str] = None
    tone: str
    confidence: float
    created_at: str


class ApprovalRequest(BaseModel):
    email_id: str
    action: str  # "approve", "reject", "edit", "save_edit"
    edited_response: Optional[str] = None


class ApprovalItem(BaseModel):
    email_id: str
    action: str


class BatchApprovalRequest(BaseModel):
    approvals: List[ApprovalItem]


class StatsResponse(BaseModel):
    total_processed: int
    processed_today: int
    by_status: Dict[str, int]
    by_category: Dict[str, int]
    pending_approvals: int


class OAuthCallbackRequest(BaseModel):
    code: str
    state: str


# ============================================================================
# AUTHENTICATION ROUTES
# ============================================================================

@app.post("/api/auth/register", response_model=Token)
async def register(user_data: UserCreate, db_session = Depends(get_db)):
    """Register a new user"""
    try:
        # Create user
        user = create_user(db_session, user_data)
        
        # Create access token
        access_token = create_access_token(data={"sub": user.id})
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            user=user_to_response(user)
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error during registration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/auth/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db_session = Depends(get_db)):
    """Login user and return JWT token"""
    user = authenticate_user(db_session, form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    return Token(
        access_token=access_token,
        token_type="bearer",
        user=user_to_response(user)
    )


@app.get("/api/auth/me", response_model=UserResponse)
async def get_me(current_user: UserModel = Depends(get_current_user)):
    """Get current user info"""
    return user_to_response(current_user)


@app.post("/api/auth/logout")
async def logout():
    """Logout user (client-side should clear token)"""
    return {"message": "Logged out successfully"}


# ============================================================================
# GMAIL OAUTH ROUTES
# ============================================================================

@app.get("/api/oauth/gmail/connect")
async def gmail_connect(current_user: UserModel = Depends(get_current_user)):
    """
    Initiate Gmail OAuth flow
    Returns the authorization URL to redirect user to
    """
    try:
        # Generate a secure random state
        state = secrets.token_urlsafe(32)
        
        # Store state with user_id
        oauth_states[state] = current_user.id
        
        # Get authorization URL
        auth_url = gmail_oauth.get_authorization_url(state)
        
        logger.info(f"Generated OAuth URL for user: {current_user.email}")
        
        return {
            "auth_url": auth_url,
            "state": state
        }
    except Exception as e:
        logger.error(f"Error generating OAuth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/oauth/gmail/callback")
async def gmail_callback(
    callback_data: OAuthCallbackRequest,
    db_session = Depends(get_db)
):
    """
    Handle Gmail OAuth callback
    Exchange authorization code for tokens
    """
    try:
        code = callback_data.code
        state = callback_data.state
        
        # Verify state
        if state not in oauth_states:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        user_id = oauth_states[state]
        
        # Exchange code for tokens
        token_data = gmail_oauth.exchange_code_for_tokens(code, state)
        
        # Update user's Gmail tokens in database
        update_gmail_tokens(
            db_session,
            user_id,
            gmail_email=token_data['gmail_email'],
            access_token=token_data['access_token'],
            refresh_token=token_data['refresh_token'],
            token_expiry=token_data['token_expiry']
        )
        
        # Clean up state
        del oauth_states[state]
        
        logger.info(f"Successfully connected Gmail for user: {user_id}")
        
        return {
            "success": True,
            "message": "Gmail connected successfully",
            "gmail_email": token_data['gmail_email']
        }
        
    except Exception as e:
        logger.error(f"Error in OAuth callback: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/oauth/gmail/disconnect")
async def gmail_disconnect(
    current_user: UserModel = Depends(get_current_user),
    db_session = Depends(get_db)
):
    """Disconnect Gmail from user account"""
    try:
        current_user.gmail_connected = False
        current_user.gmail_email = None
        current_user.gmail_access_token = None
        current_user.gmail_refresh_token = None
        current_user.gmail_token_expiry = None
        
        db_session.commit()
        
        logger.info(f"Disconnected Gmail for user: {current_user.email}")
        
        return {"success": True, "message": "Gmail disconnected"}
    except Exception as e:
        logger.error(f"Error disconnecting Gmail: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# EMAIL PROCESSING ROUTES
# ============================================================================

@app.get("/api/emails/fetch", response_model=List[EmailItem])
async def fetch_new_emails(
    max_results: int = 10,
    current_user: UserModel = Depends(get_current_user)
):
    """Fetch new unread emails from user's Gmail"""
    try:
        if not current_user.gmail_connected:
            raise HTTPException(status_code=400, detail="Gmail not connected")
        
        # Create Gmail client for this user
        gmail_client = create_gmail_client_for_user(
            current_user.gmail_access_token,
            current_user.gmail_refresh_token
        )
        
        emails = gmail_client.fetch_unread_emails(max_results=max_results)
        
        email_items = []
        for email in emails:
            if not db.is_processed(email["id"], current_user.id):
                email_items.append(EmailItem(
                    id=email["id"],
                    subject=email["subject"],
                    sender=email["from"],
                    body=email["body"],
                    preview=email["body"][:200] + "..." if len(email["body"]) > 200 else email["body"],
                    thread_id=email.get("thread_id"),
                    received_date=email.get("date")
                ))
        
        return email_items
    except Exception as e:
        logger.error(f"Error fetching emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/emails/process")
async def process_emails(
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_user)
):
    """Process all unread emails and generate draft responses"""
    try:
        if not current_user.gmail_connected:
            raise HTTPException(status_code=400, detail="Gmail not connected")
        
        # Create Gmail client for this user
        gmail_client = create_gmail_client_for_user(
            current_user.gmail_access_token,
            current_user.gmail_refresh_token
        )
        
        emails = gmail_client.fetch_unread_emails(max_results=MAX_EMAILS_PER_CHECK)
        processed_count = 0
        
        # Initialize pending responses dict for this user if not exists
        if current_user.id not in pending_responses:
            pending_responses[current_user.id] = {}
        
        for email in emails:
            if db.is_processed(email["id"], current_user.id):
                continue
            
            try:
                body = email["body"]
                if len(body) > 4000:
                    body = body[:4000] + "\n\n[Email truncated]"
                
                analysis = llm.analyze_email(
                    email["subject"],
                    email["from"],
                    body,
                    email.get("thread_id")
                )
                
                decision = llm.decide_action(
                    analysis,
                    email["subject"],
                    email["from"]
                )
                
                if decision.action == "skip":
                    db.mark_as_processed(
                        email_id=email["id"],
                        user_id=current_user.id,
                        status="skipped",
                        category=analysis.category,
                        priority=analysis.priority,
                        sentiment=analysis.sentiment,
                        subject=email["subject"],
                        sender=email["from"],
                        thread_id=email.get("thread_id")
                    )
                    continue
                
                response = llm.generate_response(
                    email["subject"],
                    email["from"],
                    body,
                    analysis
                )
                
                pending_responses[current_user.id][email["id"]] = PendingResponse(
                    email_id=email["id"],
                    subject=email["subject"],
                    sender=email["from"],
                    body_preview=email["body"][:300] + "..." if len(email["body"]) > 300 else email["body"],
                    body_full=email["body"],
                    category=analysis.category,
                    priority=analysis.priority,
                    sentiment=analysis.sentiment,
                    draft_response=response.response_body,
                    edited_response=None,
                    tone=response.tone,
                    confidence=response.confidence,
                    created_at=datetime.now().isoformat()
                )
                
                processed_count += 1
                
            except Exception as e:
                logger.error(f"Error processing email {email['id']}: {e}")
                continue
        
        return {
            "success": True,
            "processed_count": processed_count,
            "pending_count": len(pending_responses.get(current_user.id, {})),
            "message": f"Processed {processed_count} emails"
        }
        
    except Exception as e:
        logger.error(f"Error in process_emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pending", response_model=List[PendingResponse])
async def get_pending_responses(current_user: UserModel = Depends(get_current_user)):
    """Get all pending responses waiting for approval for current user"""
    user_pending = pending_responses.get(current_user.id, {})
    return list(user_pending.values())


@app.post("/api/approve/{email_id}")
async def approve_response(
    email_id: str,
    request: ApprovalRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Approve, reject, or edit a single response"""
    user_pending = pending_responses.get(current_user.id, {})
    
    if email_id not in user_pending:
        raise HTTPException(status_code=404, detail="Email not found in pending responses")
    
    pending = user_pending[email_id]
    
    try:
        # Create Gmail client for this user
        gmail_client = create_gmail_client_for_user(
            current_user.gmail_access_token,
            current_user.gmail_refresh_token
        )
        
        if request.action == "approve":
            response_to_send = pending.edited_response or pending.draft_response
            
            success = gmail_client.send_reply(
                to=pending.sender,
                subject=f"Re: {pending.subject}",
                body=response_to_send,
                thread_id=None
            )
            
            if success:
                db.mark_as_processed(
                    email_id=email_id,
                    user_id=current_user.id,
                    status="responded",
                    response_sent=response_to_send,
                    category=pending.category,
                    priority=pending.priority,
                    sentiment=pending.sentiment,
                    subject=pending.subject,
                    sender=pending.sender
                )
                del user_pending[email_id]
                return {"success": True, "message": "Response sent successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to send email")
        
        elif request.action == "edit":
            if request.edited_response:
                success = gmail_client.send_reply(
                    to=pending.sender,
                    subject=f"Re: {pending.subject}",
                    body=request.edited_response,
                    thread_id=None
                )
                
                if success:
                    db.mark_as_processed(
                        email_id=email_id,
                        user_id=current_user.id,
                        status="responded",
                        response_sent=request.edited_response,
                        category=pending.category,
                        priority=pending.priority,
                        sentiment=pending.sentiment,
                        subject=pending.subject,
                        sender=pending.sender
                    )
                    del user_pending[email_id]
                    return {"success": True, "message": "Edited response sent successfully"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to send email")
        
        elif request.action == "save_edit":
            if request.edited_response:
                user_pending[email_id].edited_response = request.edited_response
                logger.info(f"Saved edited response for {email_id}")
                return {"success": True, "message": "Response saved", "edited_response": request.edited_response}
        
        elif request.action == "reject":
            db.mark_as_processed(
                email_id=email_id,
                user_id=current_user.id,
                status="rejected",
                category=pending.category,
                priority=pending.priority,
                sentiment=pending.sentiment,
                subject=pending.subject,
                sender=pending.sender
            )
            del user_pending[email_id]
            return {"success": True, "message": "Response rejected"}
        
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
            
    except Exception as e:
        logger.error(f"Error approving response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/batch-approve")
async def batch_approve(
    request: BatchApprovalRequest,
    current_user: UserModel = Depends(get_current_user)
):
    """Batch approve/reject multiple responses"""
    try:
        user_pending = pending_responses.get(current_user.id, {})
        results = []
        
        # Create Gmail client once
        gmail_client = create_gmail_client_for_user(
            current_user.gmail_access_token,
            current_user.gmail_refresh_token
        )

        for item in request.approvals:
            email_id = item.email_id
            action = item.action

            if email_id not in user_pending:
                results.append({
                    "email_id": email_id,
                    "success": False,
                    "error": "Email not found"
                })
                continue

            pending = user_pending[email_id]

            try:
                if action == "approve":
                    success = gmail_client.send_reply(
                        to=pending.sender,
                        subject=f"Re: {pending.subject}",
                        body=pending.draft_response,
                        thread_id=None
                    )

                    if success:
                        db.mark_as_processed(
                            email_id=email_id,
                            user_id=current_user.id,
                            status="responded",
                            response_sent=pending.draft_response,
                            category=pending.category,
                            priority=pending.priority,
                            sentiment=pending.sentiment,
                            subject=pending.subject,
                            sender=pending.sender
                        )
                        del user_pending[email_id]
                        results.append({"email_id": email_id, "success": True, "message": "Sent"})
                    else:
                        results.append({"email_id": email_id, "success": False, "error": "Failed to send"})

                elif action == "reject":
                    db.mark_as_processed(
                        email_id=email_id,
                        user_id=current_user.id,
                        status="rejected",
                        category=pending.category,
                        priority=pending.priority,
                        sentiment=pending.sentiment,
                        subject=pending.subject,
                        sender=pending.sender
                    )
                    del user_pending[email_id]
                    results.append({"email_id": email_id, "success": True, "message": "Rejected"})

            except Exception as e:
                logger.error(f"Error processing {email_id}: {e}")
                results.append({"email_id": email_id, "success": False, "error": str(e)})

        successful = sum(1 for r in results if r.get("success", False))

        return {
            "total": len(results),
            "successful": successful,
            "failed": len(results) - successful,
            "results": results
        }
    except Exception as e:
        logger.error(f"Batch approve error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(current_user: UserModel = Depends(get_current_user)):
    """Get processing statistics for current user"""
    stats = db.get_stats(current_user.id)
    user_pending = pending_responses.get(current_user.id, {})
    
    return StatsResponse(
        total_processed=stats.get("total_processed", 0),
        processed_today=stats.get("processed_today", 0),
        by_status=stats.get("by_status", {}),
        by_category=stats.get("by_category", {}),
        pending_approvals=len(user_pending)
    )


@app.delete("/api/pending/clear")
async def clear_pending(current_user: UserModel = Depends(get_current_user)):
    """Clear all pending responses for current user"""
    user_pending = pending_responses.get(current_user.id, {})
    count = len(user_pending)
    pending_responses[current_user.id] = {}
    return {
        "success": True,
        "message": f"Cleared {count} pending responses"
    }


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Email Automation API v2.0 is running",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)