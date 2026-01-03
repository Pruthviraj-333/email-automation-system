import os
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import logging
from email.mime.text import MIMEText as MIMETextPart


from email_formatter import format_for_gmail

logger = logging.getLogger(__name__)

# Import configuration variables
from config import (
    GMAIL_CREDENTIALS_FILE,
    GMAIL_TOKEN_FILE,
    GMAIL_SCOPES
)


class GmailClient:
    def __init__(self):
        """Initialize Gmail API client"""
        self.service = self._authenticate()

    def _authenticate(self):
        """Authenticate with Gmail API"""
        creds = None

        # Load existing token
        if os.path.exists(GMAIL_TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(GMAIL_TOKEN_FILE, GMAIL_SCOPES)

        # If no valid credentials, let user log in
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    GMAIL_CREDENTIALS_FILE, GMAIL_SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save credentials for next run
            with open(GMAIL_TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())

        return build('gmail', 'v1', credentials=creds)

    def fetch_unread_emails(self, max_results: int = 10):
        """Fetch unread emails from inbox"""
        try:
            # Search for unread emails
            results = self.service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=max_results
            ).execute()

            messages = results.get('messages', [])

            if not messages:
                return []

            emails = []
            for message in messages:
                email_data = self._get_email_details(message['id'])
                if email_data:
                    emails.append(email_data)

            return emails

        except HttpError as error:
            logger.error(f"An error occurred fetching emails: {error}")
            return []

    def _get_email_details(self, message_id: str):
        """Get detailed information about an email"""
        try:
            message = self.service.users().messages().get(
                userId='me',
                id=message_id,
                format='full'
            ).execute()

            headers = message['payload']['headers']
            subject = self._get_header(headers, 'Subject')
            sender = self._get_header(headers, 'From')
            date = self._get_header(headers, 'Date')

            # Get email body
            body = self._get_email_body(message['payload'])

            # Get thread ID
            thread_id = message.get('threadId')

            return {
                'id': message_id,
                'thread_id': thread_id,
                'subject': subject,
                'from': sender,
                'date': date,
                'body': body
            }

        except HttpError as error:
            logger.error(f"An error occurred getting email details: {error}")
            return None

    def _get_header(self, headers, name):
        """Extract header value by name"""
        for header in headers:
            if header['name'] == name:
                return header['value']
        return ''

    def _get_email_body(self, payload):
        """Extract email body from payload"""
        body = ''

        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
                        break
                elif part['mimeType'] == 'text/html' and not body:
                    if 'data' in part['body']:
                        body = base64.urlsafe_b64decode(
                            part['body']['data']
                        ).decode('utf-8')
        elif 'body' in payload and 'data' in payload['body']:
            body = base64.urlsafe_b64decode(
                payload['body']['data']
            ).decode('utf-8')

        return body

    def send_reply(self, to: str, subject: str, body: str, thread_id: str = None):
        """Send a reply email with proper formatting"""
        try:
            # Format the email properly
            formatted = format_for_gmail(body)
            
            # Create multipart message
            message = MIMEMultipart('alternative')
            message['to'] = to
            message['subject'] = subject
            
            # Add plain text version (MOST IMPORTANT for Gmail)
            part_plain = MIMETextPart(formatted['plain'], 'plain', 'utf-8')
            message.attach(part_plain)
            
            # Add HTML version
            part_html = MIMETextPart(formatted['html'], 'html', 'utf-8')
            message.attach(part_html)

            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode('utf-8')

            send_message = {'raw': raw_message}

            # If thread_id is provided, add it to make it a reply
            if thread_id:
                send_message['threadId'] = thread_id

            self.service.users().messages().send(
                userId='me',
                body=send_message
            ).execute()

            logger.info(f"Reply sent successfully to {to}")
            return True

        except HttpError as error:
            logger.error(f"An error occurred sending reply: {error}")
            return False

    def mark_as_read(self, message_id: str):
        """Mark an email as read"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True

        except HttpError as error:
            logger.error(f"An error occurred marking as read: {error}")
            return False

    def add_label(self, message_id: str, label_id: str):
        """Add a label to an email"""
        try:
            self.service.users().messages().modify(
                userId='me',
                id=message_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            return True

        except HttpError as error:
            logger.error(f"An error occurred adding label: {error}")
            return False

    def get_or_create_label(self, label_name: str):
        """Get label ID by name or create if doesn't exist"""
        try:
            # Get all labels
            results = self.service.users().labels().list(userId='me').execute()
            labels = results.get('labels', [])

            # Check if label exists
            for label in labels:
                if label['name'] == label_name:
                    return label['id']

            # Create new label
            label_object = {
                'name': label_name,
                'labelListVisibility': 'labelShow',
                'messageListVisibility': 'show'
            }

            created_label = self.service.users().labels().create(
                userId='me',
                body=label_object
            ).execute()

            return created_label['id']

        except HttpError as error:
            logger.error(f"An error occurred with labels: {error}")
            return None