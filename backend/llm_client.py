from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from models import EmailAnalysis, EmailDecision, EmailResponse
import logging

logger = logging.getLogger(__name__)

# Import configuration variables
from config import GROQ_API_KEY, LLM_MODEL


class LLMClient:
    def __init__(self):
        self.llm = ChatGroq(
            api_key=GROQ_API_KEY,
            model_name=LLM_MODEL,
            temperature=0.3
        )
        logger.info(f"LLM Client initialized with model: {LLM_MODEL}")

    def analyze_email(self, subject: str, sender: str, body: str, thread_id: str = None) -> EmailAnalysis:
        """Analyze email and categorize it"""
        parser = PydanticOutputParser(pydantic_object=EmailAnalysis)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an email analysis assistant. Analyze emails and provide structured output.
            
IMPORTANT: Return ONLY a valid JSON object with the exact fields specified, no schema wrapper.
Do NOT wrap your response in a schema structure with 'description', 'properties', or 'required' fields.

{format_instructions}"""),
            ("user", """Analyze this email:

Subject: {subject}
From: {sender}
Body: {body}

Return a JSON object (not a schema) with these exact fields:
- category: one of "work", "personal", "marketing", "support", "urgent"
- priority: integer from 1-5
- requires_response: boolean
- sentiment: one of "positive", "neutral", "negative"
- key_points: array of strings
- suggested_action: string""")
        ])
        
        chain = prompt | self.llm | parser
        
        result = chain.invoke({
            "subject": subject,
            "sender": sender,
            "body": body,
            "format_instructions": parser.get_format_instructions()
        })
        
        return result

    def decide_action(self, analysis: EmailAnalysis, subject: str, sender: str) -> EmailDecision:
        """Decide what action to take on the email"""
        parser = PydanticOutputParser(pydantic_object=EmailDecision)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an email decision assistant. Based on email analysis, decide the action to take.
            
IMPORTANT: Return ONLY a valid JSON object with the exact fields specified, no schema wrapper.

{format_instructions}"""),
            ("user", """Based on this email analysis, decide the action:

Subject: {subject}
From: {sender}
Category: {category}
Priority: {priority}
Requires Response: {requires_response}
Sentiment: {sentiment}
Key Points: {key_points}

Rules:
- Respond to urgent emails (priority >= 4) from known contacts
- Skip marketing emails  
- Skip automated notifications
- Respond to questions or requests that need a reply

Return a JSON object with:
- action: "respond" or "skip"
- reasoning: string explaining why""")
        ])
        
        chain = prompt | self.llm | parser
        
        result = chain.invoke({
            "subject": subject,
            "sender": sender,
            "category": analysis.category,
            "priority": analysis.priority,
            "requires_response": analysis.requires_response,
            "sentiment": analysis.sentiment,
            "key_points": ", ".join(analysis.key_points),
            "format_instructions": parser.get_format_instructions()
        })
        
        return result

    def generate_response(self, subject: str, sender: str, body: str, analysis: EmailAnalysis) -> EmailResponse:
        """Generate an appropriate email response"""
        parser = PydanticOutputParser(pydantic_object=EmailResponse)
        
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an email response assistant. Generate appropriate, professional email responses.

CRITICAL: You MUST return ONLY valid JSON. Do NOT include any text before or after the JSON object.
Do NOT write the email response as plain text before the JSON.
Do NOT include explanations, preambles, or any other text.

START your response with {{ and END with }}

IMPORTANT FORMATTING RULES:
1. Use proper paragraph breaks (double newline \\n\\n) between main ideas
2. Use single newlines (\\n) for line breaks within paragraphs
3. Keep paragraphs short (2-3 sentences)
4. Start with a greeting on its own line
5. End with a closing on its own line
6. Structure: Greeting → Body paragraphs → Closing → Signature

Example JSON format (this is what you should return):
{{
  "response_body": "Hello [Name],\\n\\nThank you for your email.\\n\\nI understand your concern.\\n\\nBest regards,\\n[Name]",
  "tone": "friendly",
  "confidence": 0.9
}}

{format_instructions}"""),
            ("user", """Generate a response for this email:

Subject: {subject}
From: {sender}
Body: {body}

Analysis:
Category: {category}
Priority: {priority}
Sentiment: {sentiment}
Key Points: {key_points}

Generate a professional, well-formatted response that:
1. Acknowledges the email
2. Addresses the key points
3. Is appropriate for the context and priority
4. Uses proper paragraph breaks and formatting
5. Maintains a {sentiment_tone} tone

REMEMBER: Return ONLY the JSON object, nothing else. Start with {{ and end with }}""")
        ])
        
        # Determine tone based on sentiment
        sentiment_tone = "helpful and empathetic" if analysis.sentiment == "negative" else "friendly and professional"
        
        chain = prompt | self.llm
        
        try:
            result = chain.invoke({
                "subject": subject,
                "sender": sender,
                "body": body,
                "category": analysis.category,
                "priority": analysis.priority,
                "sentiment": analysis.sentiment,
                "key_points": ", ".join(analysis.key_points),
                "sentiment_tone": sentiment_tone,
                "format_instructions": parser.get_format_instructions()
            })
            
            # Extract JSON from the response
            response_text = result.content if hasattr(result, 'content') else str(result)
            
            # Try to find JSON in the response using regex
            import json
            import re
            
            # Method 1: Try to find JSON object with regex (handles text before/after)
            json_match = re.search(r'\{[\s\S]*\}', response_text)
            if json_match:
                json_str = json_match.group(0)
                try:
                    parsed_data = json.loads(json_str)
                    return EmailResponse(**parsed_data)
                except json.JSONDecodeError as e:
                    logger.error(f"JSON parsing failed: {e}")
                    logger.error(f"Attempted to parse: {json_str[:200]}")
            
            # Method 2: Try to parse the whole thing
            try:
                parsed_data = json.loads(response_text)
                return EmailResponse(**parsed_data)
            except json.JSONDecodeError:
                pass
            
            # If all parsing fails, log and return fallback
            logger.error(f"All JSON parsing methods failed for response")
            logger.error(f"Raw response (first 500 chars): {response_text[:500]}")
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
        
        # Fallback: Create a basic response
        return EmailResponse(
            response_body=f"Thank you for your email regarding: {subject}\n\nI have received your message and will respond shortly.\n\nBest regards",
            tone="formal",
            confidence=0.5
        )