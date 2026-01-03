from fastapi import FastAPI, HTTPException, BackgroundTasks, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
from datetime import datetime
import logging
from contextlib import asynccontextmanager

from db import Database
from gmail_client import GmailClient
from llm_client import LLMClient
from models import EmailAnalysis, EmailDecision, EmailResponse
from config import MAX_EMAILS_PER_CHECK

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global instances
db = None
gmail = None
llm = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize services on startup"""
    global db, gmail, llm
    logger.info("Initializing services...")
    db = Database()
    gmail = GmailClient()
    llm = LLMClient()
    logger.info("Services initialized successfully")
    yield
    logger.info("Shutting down services...")


app = FastAPI(
    title="Email Automation API",
    description="API for automated email processing and approval",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models for API
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
    body_full: str  # NEW: Store full body
    category: str
    priority: int
    sentiment: str
    draft_response: str
    edited_response: Optional[str] = None  # NEW: Track if edited
    tone: str
    confidence: float
    created_at: str


class ApprovalRequest(BaseModel):
    email_id: str
    action: str
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


# In-memory storage for pending responses
pending_responses: Dict[str, PendingResponse] = {}

# NEW: Storage for edited responses
edited_responses: Dict[str, str] = {}  # email_id -> edited response text


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "ok",
        "message": "Email Automation API is running",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/emails/fetch", response_model=List[EmailItem])
async def fetch_new_emails(max_results: int = 10):
    """Fetch new unread emails from Gmail"""
    try:
        emails = gmail.fetch_unread_emails(max_results=max_results)
        
        email_items = []
        for email in emails:
            if not db.is_processed(email["id"]):
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
async def process_emails(background_tasks: BackgroundTasks):
    """Process all unread emails and generate draft responses"""
    try:
        emails = gmail.fetch_unread_emails(max_results=MAX_EMAILS_PER_CHECK)
        processed_count = 0
        
        for email in emails:
            if db.is_processed(email["id"]):
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
                
                pending_responses[email["id"]] = PendingResponse(
                    email_id=email["id"],
                    subject=email["subject"],
                    sender=email["from"],
                    body_preview=email["body"][:300] + "..." if len(email["body"]) > 300 else email["body"],
                    body_full=email["body"],  # NEW: Store full body
                    category=analysis.category,
                    priority=analysis.priority,
                    sentiment=analysis.sentiment,
                    draft_response=response.response_body,
                    edited_response=None,  # NEW: Initialize as None
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
            "pending_count": len(pending_responses),
            "message": f"Processed {processed_count} emails"
        }
        
    except Exception as e:
        logger.error(f"Error in process_emails: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/pending", response_model=List[PendingResponse])
async def get_pending_responses():
    """Get all pending responses waiting for approval"""
    return list(pending_responses.values())


@app.post("/api/approve/{email_id}")
async def approve_response(email_id: str, request: ApprovalRequest):
    """Approve, reject, or edit a single response"""
    if email_id not in pending_responses:
        raise HTTPException(status_code=404, detail="Email not found in pending responses")
    
    pending = pending_responses[email_id]
    
    try:
        if request.action == "approve":
            # Use edited response if available, otherwise use draft
            response_to_send = edited_responses.get(email_id, pending.draft_response)
            
            success = gmail.send_reply(
                to=pending.sender,
                subject=f"Re: {pending.subject}",
                body=response_to_send,
                thread_id=None
            )
            
            if success:
                db.mark_as_processed(
                    email_id=email_id,
                    status="responded",
                    response_sent=response_to_send,
                    category=pending.category,
                    priority=pending.priority,
                    sentiment=pending.sentiment,
                    subject=pending.subject,
                    sender=pending.sender
                )
                del pending_responses[email_id]
                if email_id in edited_responses:
                    del edited_responses[email_id]
                return {"success": True, "message": "Response sent successfully"}
            else:
                raise HTTPException(status_code=500, detail="Failed to send email")
        
        elif request.action == "edit":
            if request.edited_response:
                success = gmail.send_reply(
                    to=pending.sender,
                    subject=f"Re: {pending.subject}",
                    body=request.edited_response,
                    thread_id=None
                )
                
                if success:
                    db.mark_as_processed(
                        email_id=email_id,
                        status="responded",
                        response_sent=request.edited_response,
                        category=pending.category,
                        priority=pending.priority,
                        sentiment=pending.sentiment,
                        subject=pending.subject,
                        sender=pending.sender
                    )
                    del pending_responses[email_id]
                    if email_id in edited_responses:
                        del edited_responses[email_id]
                    return {"success": True, "message": "Edited response sent successfully"}
                else:
                    raise HTTPException(status_code=500, detail="Failed to send email")
        
        elif request.action == "save_edit":
            # Save edited response without sending
            if request.edited_response:
                edited_responses[email_id] = request.edited_response
                # Update the pending response object to reflect the edit
                pending_responses[email_id].edited_response = request.edited_response
                logger.info(f"Saved edited response for {email_id}")
                return {"success": True, "message": "Response saved", "edited_response": request.edited_response}
        
        elif request.action == "reject":
            db.mark_as_processed(
                email_id=email_id,
                status="rejected",
                category=pending.category,
                priority=pending.priority,
                sentiment=pending.sentiment,
                subject=pending.subject,
                sender=pending.sender
            )
            del pending_responses[email_id]
            if email_id in edited_responses:
                del edited_responses[email_id]
            return {"success": True, "message": "Response rejected"}
        
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
            
    except Exception as e:
        logger.error(f"Error approving response: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/batch-approve")
async def batch_approve_v2(request: BatchApprovalRequest = Body(...)):
    """Batch approve/reject multiple responses"""
    try:
        logger.info(f"Batch request received with {len(request.approvals)} items")
        
        approvals = request.approvals
        results = []

        for item in approvals:
            email_id = item.email_id
            action = item.action
            
            logger.info(f"Processing {email_id} - {action}")

            if email_id not in pending_responses:
                results.append({
                    "email_id": email_id,
                    "success": False,
                    "error": "Email not found"
                })
                continue

            pending = pending_responses[email_id]

            try:
                if action == "approve":
                    success = gmail.send_reply(
                        to=pending.sender,
                        subject=f"Re: {pending.subject}",
                        body=pending.draft_response,
                        thread_id=None
                    )

                    if success:
                        db.mark_as_processed(
                            email_id=email_id,
                            status="responded",
                            response_sent=pending.draft_response,
                            category=pending.category,
                            priority=pending.priority,
                            sentiment=pending.sentiment,
                            subject=pending.subject,
                            sender=pending.sender
                        )
                        del pending_responses[email_id]

                        results.append({
                            "email_id": email_id,
                            "success": True,
                            "message": "Sent"
                        })
                    else:
                        results.append({
                            "email_id": email_id,
                            "success": False,
                            "error": "Failed to send"
                        })

                elif action == "reject":
                    db.mark_as_processed(
                        email_id=email_id,
                        status="rejected",
                        category=pending.category,
                        priority=pending.priority,
                        sentiment=pending.sentiment,
                        subject=pending.subject,
                        sender=pending.sender
                    )
                    del pending_responses[email_id]

                    results.append({
                        "email_id": email_id,
                        "success": True,
                        "message": "Rejected"
                    })

            except Exception as e:
                logger.error(f"Error processing {email_id}: {e}")
                results.append({
                    "email_id": email_id,
                    "success": False,
                    "error": str(e)
                })

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
async def get_stats():
    """Get processing statistics"""
    stats = db.get_stats()
    
    return StatsResponse(
        total_processed=stats.get("total_processed", 0),
        processed_today=stats.get("processed_today", 0),
        by_status=stats.get("by_status", {}),
        by_category=stats.get("by_category", {}),
        pending_approvals=len(pending_responses)
    )


@app.delete("/api/pending/clear")
async def clear_pending():
    """Clear all pending responses"""
    count = len(pending_responses)
    pending_responses.clear()
    return {
        "success": True,
        "message": f"Cleared {count} pending responses"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)