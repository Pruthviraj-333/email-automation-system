import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Gmail Configuration
GMAIL_CREDENTIALS_FILE = 'credentials.json'
GMAIL_TOKEN_FILE = 'token.json'
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

# Groq Configuration
GROQ_API_KEY = os.getenv('GROQ_API_KEY')

LLM_MODEL = "llama-3.3-70b-versatile"

# Database Configuration
DATABASE_NAME = 'emails.db'

# Processing Configuration
CHECK_INTERVAL = 120  # seconds 
MAX_EMAILS_PER_CHECK = 10

# Human-in-the-Loop Configuration
REQUIRE_APPROVAL = True  # Set to False to disable human approval (auto-send mode)

# Auto-approve certain categories (emails in these categories will be sent automatically)
# Examples: ["marketing"], ["support", "marketing"], []
AUTO_APPROVE_CATEGORIES = []  # Empty list = require approval for all emails

# Email Processing Rules
SKIP_SENDERS = [
    'no-reply@',
    'noreply@',
    'notifications@',
    'do-not-reply@'
]

# Priority senders (optional - for future use)
PRIORITY_SENDERS = [
    # Add important email addresses here that should always get priority
    # 'client@important.com'
]

# Logging Configuration
LOG_LEVEL = 'INFO'  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_FILE = 'email_automation.log'