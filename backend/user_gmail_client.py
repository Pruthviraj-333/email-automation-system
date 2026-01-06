"""
User-specific Gmail Client
Handles Gmail operations for individual users with their own OAuth tokens
"""
import base64
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.errors import HttpError
from datetime import datetime
import logging

from gmail_oauth import gmail_oauth
from email_formatter import format_for_gmail

logger = logging.getLogger(__name__)


class UserGmailClient:
    """Gmail client for a specific user"""
    
    def __init__(self, access_token: str, refresh_token: str = None):
        """
        Initialize Gmail client for a user
        
        Args:
            access_token: User's Gmail access token
            refresh_token: User's Gmail refresh token
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.service = gmail_oauth.build_gmail_service(access_token, refresh_token)
    
    def fetch_unread_emails(self, max_results: int = 10):
        """Fetch unread emails from user's inbox"""
        try:
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
            logger.error(f"Error fetching emails: {error}")
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
            logger.error(f"Error getting email details: {error}")
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
            
            # Add plain text version
            part_plain = MIMEText(formatted['plain'], 'plain', 'utf-8')
            message.attach(part_plain)
            
            # Add HTML version
            part_html = MIMEText(formatted['html'], 'html', 'utf-8')
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
            logger.error(f"Error sending reply: {error}")
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
            logger.error(f"Error marking as read: {error}")
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
            logger.error(f"Error adding label: {error}")
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
            logger.error(f"Error with labels: {error}")
            return None
    
    def get_user_email(self):
        """Get the user's Gmail email address"""
        try:
            profile = self.service.users().getProfile(userId='me').execute()
            return profile.get('emailAddress')
        except HttpError as error:
            logger.error(f"Error getting user email: {error}")
            return None


def create_gmail_client_for_user(access_token: str, refresh_token: str = None) -> UserGmailClient:
    """
    Factory function to create a Gmail client for a user
    
    Args:
        access_token: User's access token
        refresh_token: User's refresh token
        
    Returns:
        UserGmailClient instance
    """
    return UserGmailClient(access_token, refresh_token)