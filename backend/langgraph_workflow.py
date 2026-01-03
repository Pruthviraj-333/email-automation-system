from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal
from models import EmailAnalysis, EmailDecision, EmailResponse
import logging

logger = logging.getLogger(__name__)


class EmailWorkflowState(TypedDict):
    email_id: str
    subject: str
    sender: str
    body: str
    thread_id: str
    analysis: EmailAnalysis
    decision: EmailDecision
    response: EmailResponse
    user_approval: bool  # Track user approval
    approval_status: str  # "pending", "approved", "rejected", "auto"


class HumanInLoopWorkflow:
    def __init__(self, gmail_client, llm_client, db):
        self.gmail = gmail_client
        self.llm = llm_client
        self.db = db
        
        # Build the workflow graph
        workflow = StateGraph(EmailWorkflowState)
        
        # Add all nodes
        workflow.add_node("analyze", self.analyze_email)
        workflow.add_node("decide", self.decide_action)
        workflow.add_node("generate_response", self.generate_response)
        workflow.add_node("request_approval", self.request_approval)
        workflow.add_node("send_response", self.send_response)
        workflow.add_node("skip", self.skip_email)
        
        # Set entry point
        workflow.set_entry_point("analyze")
        
        # Add edges
        workflow.add_edge("analyze", "decide")
        workflow.add_conditional_edges(
            "decide",
            self.should_respond,
            {
                "respond": "generate_response",
                "skip": "skip"
            }
        )
        workflow.add_edge("generate_response", "request_approval")
        workflow.add_conditional_edges(
            "request_approval",
            self.check_approval,
            {
                "approved": "send_response",
                "rejected": "skip",
                "auto": "send_response"
            }
        )
        workflow.add_edge("send_response", END)
        workflow.add_edge("skip", END)
        
        self.app = workflow.compile()

    def analyze_email(self, state: EmailWorkflowState) -> EmailWorkflowState:
        """Analyze the email using LLM"""
        logger.info(f"Analyzing email: {state['subject']}")
        try:
            # Truncate body if too long to avoid token limits
            body = state["body"]
            max_body_length = 4000  # Keep body under 4000 chars to avoid token limits
            if len(body) > max_body_length:
                body = body[:max_body_length] + "\n\n[Email truncated due to length]"
                logger.info(f"Truncated email body from {len(state['body'])} to {max_body_length} chars")
            
            analysis = self.llm.analyze_email(
                state["subject"],
                state["sender"],
                body,
                state.get("thread_id")
            )
            state["analysis"] = analysis
        except Exception as e:
            logger.error(f"Error analyzing email: {e}")
            # Create a default analysis to continue workflow
            state["analysis"] = EmailAnalysis(
                category="unknown",
                priority=3,
                requires_response=False,
                sentiment="neutral",
                key_points=["Failed to analyze"],
                suggested_action="Manual review required"
            )
        return state

    def decide_action(self, state: EmailWorkflowState) -> EmailWorkflowState:
        """Decide what action to take"""
        logger.info(f"Deciding action for: {state['subject']}")
        decision = self.llm.decide_action(
            state["analysis"],
            state["subject"],
            state["sender"]
        )
        state["decision"] = decision
        logger.info(f"Decision: {decision.action.capitalize()}")
        return state

    def should_respond(self, state: EmailWorkflowState) -> Literal["respond", "skip"]:
        """Route based on decision"""
        return "respond" if state["decision"].action == "respond" else "skip"

    def generate_response(self, state: EmailWorkflowState) -> EmailWorkflowState:
        """Generate email response"""
        logger.info(f"Generating response for: {state['subject']}")
        response = self.llm.generate_response(
            state["subject"],
            state["sender"],
            state["body"],
            state["analysis"]
        )
        state["response"] = response
        state["approval_status"] = "pending"
        return state

    def request_approval(self, state: EmailWorkflowState) -> EmailWorkflowState:
        """Request human approval before sending"""
        from config import AUTO_APPROVE_CATEGORIES
        
        logger.info(f"Requesting approval for: {state['subject']}")
        
        # Auto-approve certain categories
        if state["analysis"].category in AUTO_APPROVE_CATEGORIES:
            state["user_approval"] = True
            state["approval_status"] = "auto"
            logger.info("Auto-approved based on category")
            return state
        
        # Display email details and draft response for human review
        print("\n" + "="*70)
        print("📧 EMAIL REQUIRES APPROVAL")
        print("="*70)
        print(f"From: {state['sender']}")
        print(f"Subject: {state['subject']}")
        print(f"Category: {state['analysis'].category}")
        print(f"Priority: {state['analysis'].priority}/5")
        print(f"Sentiment: {state['analysis'].sentiment}")
        print(f"\nEmail Body Preview:")
        print("-" * 70)
        print(state['body'][:300] + "..." if len(state['body']) > 300 else state['body'])
        print("-" * 70)
        print(f"\n📝 DRAFT RESPONSE:")
        print("-" * 70)
        print(state['response'].response_body)
        print("-" * 70)
        print(f"Tone: {state['response'].tone} | Confidence: {state['response'].confidence:.2f}")
        print("="*70)
        
        # Get user input
        while True:
            choice = input("\n👤 Approve this response? (y/n/e=edit): ").lower().strip()
            
            if choice == 'y':
                state["user_approval"] = True
                state["approval_status"] = "approved"
                logger.info("[OK] Response approved by user")
                break
            elif choice == 'n':
                state["user_approval"] = False
                state["approval_status"] = "rejected"
                logger.info("[NO] Response rejected by user")
                break
            elif choice == 'e':
                print("\n✏️  Enter your edited response (press Enter twice to finish):")
                lines = []
                while True:
                    line = input()
                    if line == "" and len(lines) > 0 and lines[-1] == "":
                        lines.pop()
                        break
                    lines.append(line)
                
                edited_response = "\n".join(lines)
                if edited_response.strip():
                    state['response'].response_body = edited_response
                    state["user_approval"] = True
                    state["approval_status"] = "approved"
                    logger.info("[OK] Response edited and approved by user")
                    break
            else:
                print("Invalid input. Please enter 'y', 'n', or 'e'")
        
        return state

    def check_approval(self, state: EmailWorkflowState) -> Literal["approved", "rejected", "auto"]:
        """Route based on approval status"""
        return state["approval_status"]

    def send_response(self, state: EmailWorkflowState) -> EmailWorkflowState:
        """Send the email response"""
        logger.info(f"Sending response for: {state['subject']}")
        
        success = self.gmail.send_reply(
            to=state["sender"],
            subject=f"Re: {state['subject']}",
            body=state["response"].response_body,
            thread_id=state.get("thread_id")
        )
        
        if success:
            logger.info("Response sent successfully")
            # Mark as processed in database
            self.db.mark_as_processed(
                email_id=state["email_id"],
                status="responded",
                response_sent=state["response"].response_body,
                category=state["analysis"].category,
                priority=state["analysis"].priority,
                sentiment=state["analysis"].sentiment,
                subject=state["subject"],
                sender=state["sender"],
                thread_id=state.get("thread_id")
            )
        else:
            logger.error("Failed to send response")
        
        return state

    def skip_email(self, state: EmailWorkflowState) -> EmailWorkflowState:
        """Skip the email without responding"""
        logger.info(f"Skipping email: {state['subject']}")
        self.db.mark_as_processed(
            email_id=state["email_id"],
            status="skipped",
            category=state.get("analysis", {}).category if state.get("analysis") else None,
            priority=state.get("analysis", {}).priority if state.get("analysis") else None,
            sentiment=state.get("analysis", {}).sentiment if state.get("analysis") else None,
            subject=state["subject"],
            sender=state["sender"],
            thread_id=state.get("thread_id")
        )
        return state

    def process_email(self, email_data: dict) -> dict:
        """Process a single email through the workflow"""
        initial_state = EmailWorkflowState(
            email_id=email_data["id"],
            subject=email_data["subject"],
            sender=email_data["from"],
            body=email_data["body"],
            thread_id=email_data.get("thread_id"),
            analysis=None,
            decision=None,
            response=None,
            user_approval=False,
            approval_status="pending"
        )
        
        try:
            result = self.app.invoke(initial_state)
            return result
        except Exception as e:
            logger.error(f"Error processing email: {e}")
            return initial_state