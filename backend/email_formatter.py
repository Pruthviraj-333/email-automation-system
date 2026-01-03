"""
Email content formatting and cleaning utilities
"""

import re
from html.parser import HTMLParser
from io import StringIO


class HTMLStripper(HTMLParser):
    """Strip HTML tags from email content"""
    def __init__(self):
        super().__init__()
        self.reset()
        self.strict = False
        self.convert_charrefs = True
        self.text = StringIO()
    
    def handle_data(self, d):
        self.text.write(d)
    
    def get_data(self):
        return self.text.getvalue()


def strip_html_tags(html_content):
    """Remove HTML tags from email content"""
    s = HTMLStripper()
    s.feed(html_content)
    return s.get_data()


def clean_email_body(body):
    """
    Clean and format email body for better readability
    
    Args:
        body: Raw email body text
        
    Returns:
        Cleaned and formatted email body
    """
    if not body:
        return ""
    
    # Strip HTML tags
    body = strip_html_tags(body)
    
    # Remove [image: ...] markers
    body = re.sub(r'\[image:.*?\]', '[Image]', body, flags=re.IGNORECASE)
    
    # Remove excessive newlines (more than 2)
    body = re.sub(r'\n{3,}', '\n\n', body)
    
    # Remove leading/trailing whitespace from each line
    lines = [line.strip() for line in body.split('\n')]
    body = '\n'.join(lines)
    
    # Remove multiple spaces
    body = re.sub(r' {2,}', ' ', body)
    
    # Remove email signatures (common patterns)
    signature_patterns = [
        r'--\s*\n.*$',  # -- signature
        r'Sent from.*$',  # "Sent from my iPhone"
        r'Get Outlook.*$',  # "Get Outlook for iOS"
    ]
    for pattern in signature_patterns:
        body = re.sub(pattern, '', body, flags=re.MULTILINE | re.DOTALL)
    
    # Remove quoted text (> at start of line)
    body = re.sub(r'^>.*$', '', body, flags=re.MULTILINE)
    
    # Final cleanup
    body = body.strip()
    
    return body


def format_email_response(response_text, subject, recipient_name=None):
    """
    Format AI-generated response for sending via email
    
    Args:
        response_text: Raw response from LLM
        subject: Email subject
        recipient_name: Optional recipient name
        
    Returns:
        Properly formatted HTML email
    """
    # Clean up the response text
    response_text = response_text.strip()
    
    # Convert plain text to HTML with proper formatting
    html_body = """
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            font-size: 14px;
            line-height: 1.6;
            color: #333333;
            max-width: 600px;
        }
        p {
            margin: 0 0 16px 0;
        }
        .email-content {
            padding: 20px 0;
        }
    </style>
</head>
<body>
    <div class="email-content">
"""
    
    # Split by double newlines for paragraphs
    paragraphs = response_text.split('\n\n')
    
    for para in paragraphs:
        if para.strip():
            # Replace single newlines with <br> tags
            para_html = para.strip().replace('\n', '<br>\n')
            html_body += f'        <p>{para_html}</p>\n'
    
    html_body += """    </div>
</body>
</html>
"""
    
    return html_body


def create_plain_text_email(response_text):
    """
    Create a clean plain text version of the email
    Ensures proper line breaks are preserved
    
    Args:
        response_text: Raw response text
        
    Returns:
        Clean plain text email with proper formatting
    """
    # Clean up formatting
    text = response_text.strip()
    
    # Ensure proper paragraph spacing (double newline between paragraphs)
    # First normalize all line breaks
    text = text.replace('\r\n', '\n').replace('\r', '\n')
    
    # Remove excessive newlines (more than 2)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # Ensure there's always a newline at the end
    if not text.endswith('\n'):
        text += '\n'
    
    return text


def format_for_gmail(response_text):
    """
    Format response specifically for Gmail API
    Gmail accepts both plain text and HTML
    
    Args:
        response_text: Raw response text
        
    Returns:
        Dictionary with both plain and HTML versions
    """
    plain = create_plain_text_email(response_text)
    html = format_email_response(response_text, subject="", recipient_name=None)
    
    return {
        'plain': plain,
        'html': html
    }