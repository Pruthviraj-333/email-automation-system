from pydantic import BaseModel, Field
from typing import List, Literal


class EmailAnalysis(BaseModel):
    """Model for email analysis results"""
    category: Literal["work", "personal", "marketing", "support", "urgent", "unknown"]
    priority: int = Field(ge=1, le=5, description="Priority from 1 (low) to 5 (high)")
    requires_response: bool
    sentiment: Literal["positive", "neutral", "negative"]
    key_points: List[str]
    suggested_action: str


class EmailDecision(BaseModel):
    """Model for email action decision"""
    action: Literal["respond", "skip"]
    reasoning: str


class EmailResponse(BaseModel):
    """Model for generated email response"""
    response_body: str
    tone: Literal["formal", "casual", "friendly"]
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence score between 0 and 1")


class EmailMetadata(BaseModel):
    """Model for email metadata"""
    id: str
    subject: str
    sender: str
    received_date: str
    thread_id: str = None


class ProcessedEmail(BaseModel):
    """Model for processed email record"""
    email_id: str
    subject: str
    sender: str
    processed_date: str
    status: Literal["responded", "skipped", "rejected", "error"]
    category: str = None
    priority: int = None
    sentiment: str = None
    response_sent: str = None
    thread_id: str = None