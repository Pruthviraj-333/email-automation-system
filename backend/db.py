import os
from datetime import datetime
from typing import Optional, List, Dict
import logging
from sqlalchemy import create_engine, Column, String, Integer, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:pass123@localhost:5432/email_automation')

# Create SQLAlchemy engine
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Define Email model
class EmailModel(Base):
    __tablename__ = "emails"
    
    id = Column(String(255), primary_key=True, index=True)
    subject = Column(Text)
    sender = Column(String(255), index=True)
    received_date = Column(DateTime)
    processed_date = Column(DateTime, index=True)
    status = Column(String(50), index=True)
    category = Column(String(50), index=True)
    priority = Column(Integer)
    sentiment = Column(String(50))
    response_sent = Column(Text)
    thread_id = Column(String(255))


class Database:
    def __init__(self):
        """Initialize database connection and create tables"""
        self.init_database()

    def init_database(self):
        """Create all tables"""
        try:
            Base.metadata.create_all(bind=engine)
            logger.info("Database initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
            raise

    def get_session(self) -> Session:
        """Get a database session"""
        return SessionLocal()

    def is_processed(self, email_id: str) -> bool:
        """Check if an email has been processed"""
        session = self.get_session()
        try:
            result = session.query(EmailModel).filter(EmailModel.id == email_id).first()
            return result is not None
        finally:
            session.close()

    def mark_as_processed(
        self,
        email_id: str,
        status: str,
        response_sent: Optional[str] = None,
        category: Optional[str] = None,
        priority: Optional[int] = None,
        sentiment: Optional[str] = None,
        subject: Optional[str] = None,
        sender: Optional[str] = None,
        thread_id: Optional[str] = None
    ):
        """Mark an email as processed"""
        session = self.get_session()
        try:
            processed_date = datetime.now()
            
            # Check if email already exists
            email = session.query(EmailModel).filter(EmailModel.id == email_id).first()
            
            if email:
                # Update existing record
                email.subject = subject or email.subject
                email.sender = sender or email.sender
                email.processed_date = processed_date
                email.status = status
                email.category = category or email.category
                email.priority = priority or email.priority
                email.sentiment = sentiment or email.sentiment
                email.response_sent = response_sent
                email.thread_id = thread_id or email.thread_id
            else:
                # Create new record
                email = EmailModel(
                    id=email_id,
                    subject=subject,
                    sender=sender,
                    received_date=datetime.now(),
                    processed_date=processed_date,
                    status=status,
                    category=category,
                    priority=priority,
                    sentiment=sentiment,
                    response_sent=response_sent,
                    thread_id=thread_id
                )
                session.add(email)
            
            session.commit()
            logger.info(f"Marked email {email_id} as {status}")
        except Exception as e:
            session.rollback()
            logger.error(f"Error marking email as processed: {e}")
            raise
        finally:
            session.close()

    def get_processed_emails(
        self,
        limit: int = 100,
        status: Optional[str] = None ) -> List[Dict]:
        
        """Get processed emails from database"""
        session = self.get_session()
        try:
            query = session.query(EmailModel)
            
            if status:
                query = query.filter(EmailModel.status == status)
            
            query = query.order_by(EmailModel.processed_date.desc()).limit(limit)
            
            results = []
            for email in query.all():
                results.append({
                    'id': email.id,
                    'subject': email.subject,
                    'sender': email.sender,
                    'received_date': email.received_date.isoformat() if email.received_date else None,
                    'processed_date': email.processed_date.isoformat() if email.processed_date else None,
                    'status': email.status,
                    'category': email.category,
                    'priority': email.priority,
                    'sentiment': email.sentiment,
                    'response_sent': email.response_sent,
                    'thread_id': email.thread_id
                })
            
            return results
        finally:
            session.close()

    def get_stats(self) -> Dict:
        """Get processing statistics"""
        session = self.get_session()
        try:
            stats = {}
            
            # Total processed
            total = session.query(EmailModel).count()
            stats['total_processed'] = total
            
            # By status
            status_counts = session.query(
                EmailModel.status,
                EmailModel.id
            ).all()
            
            by_status = {}
            for status, _ in status_counts:
                if status:
                    by_status[status] = by_status.get(status, 0) + 1
            stats['by_status'] = by_status
            
            # By category
            category_counts = session.query(
                EmailModel.category,
                EmailModel.id
            ).all()
            
            by_category = {}
            for category, _ in category_counts:
                if category:
                    by_category[category] = by_category.get(category, 0) + 1
            stats['by_category'] = by_category
            
            # Today's processed
            today = datetime.now().date()
            today_count = session.query(EmailModel).filter(
                EmailModel.processed_date >= datetime.combine(today, datetime.min.time())
            ).count()
            stats['processed_today'] = today_count
            
            return stats
        finally:
            session.close()

    def cleanup_old_records(self, days: int = 30) -> int:
        """Delete records older than specified days"""
        session = self.get_session()
        try:
            cutoff_date = datetime.now()
            from datetime import timedelta
            cutoff_date = cutoff_date - timedelta(days=days)
            
            deleted = session.query(EmailModel).filter(
                EmailModel.processed_date < cutoff_date
            ).delete()
            
            session.commit()
            logger.info(f"Cleaned up {deleted} old records")
            return deleted
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up records: {e}")
            raise
        finally:
            session.close()

    def get_email_by_id(self, email_id: str) -> Optional[Dict]:
        """Get a specific email by ID"""
        session = self.get_session()
        try:
            email = session.query(EmailModel).filter(EmailModel.id == email_id).first()
            
            if not email:
                return None
            
            return {
                'id': email.id,
                'subject': email.subject,
                'sender': email.sender,
                'received_date': email.received_date.isoformat() if email.received_date else None,
                'processed_date': email.processed_date.isoformat() if email.processed_date else None,
                'status': email.status,
                'category': email.category,
                'priority': email.priority,
                'sentiment': email.sentiment,
                'response_sent': email.response_sent,
                'thread_id': email.thread_id
            }
        finally:
            session.close()

    def search_emails(
        self,
        search_term: str = None,
        category: str = None,
        status: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Search emails with filters"""
        session = self.get_session()
        try:
            query = session.query(EmailModel)
            
            if search_term:
                search_pattern = f"%{search_term}%"
                query = query.filter(
                    (EmailModel.subject.ilike(search_pattern)) |
                    (EmailModel.sender.ilike(search_pattern))
                )
            
            if category:
                query = query.filter(EmailModel.category == category)
            
            if status:
                query = query.filter(EmailModel.status == status)
            
            query = query.order_by(EmailModel.processed_date.desc()).limit(limit)
            
            results = []
            for email in query.all():
                results.append({
                    'id': email.id,
                    'subject': email.subject,
                    'sender': email.sender,
                    'status': email.status,
                    'category': email.category,
                    'priority': email.priority,
                    'processed_date': email.processed_date.isoformat() if email.processed_date else None
                })
            
            return results
        finally:
            session.close()


# Test connection
if __name__ == "__main__":
    try:
        db = Database()
        print("✓ Database connection successful!")
        stats = db.get_stats()
        print(f"Stats: {stats}")
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print("\nMake sure:")
        print("1. PostgreSQL is running")
        print("2. Database 'email_automation' exists")
        print("3. DATABASE_URL in .env is correct")