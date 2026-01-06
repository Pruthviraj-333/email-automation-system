"""
Gmail OAuth 2.0 Integration
Handles the OAuth flow for connecting user Gmail accounts
"""
import os
import pickle
from datetime import datetime, timedelta
from typing import Optional, Dict
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

# OAuth Configuration
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/userinfo.email',
    'openid'
]

# This should be your application's redirect URI
# For development: http://localhost:3000/oauth/callback
# For production: https://yourdomain.com/oauth/callback
REDIRECT_URI = os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:3000/oauth/callback')

# Path to your OAuth credentials file
CREDENTIALS_FILE = 'credentials.json'


class GmailOAuth:
    """Handle Gmail OAuth operations"""
    
    def __init__(self):
        self.credentials_file = CREDENTIALS_FILE
        self.redirect_uri = REDIRECT_URI
        self.scopes = SCOPES
    
    def get_authorization_url(self, state: str) -> str:
        """
        Generate OAuth authorization URL
        
        Args:
            state: Random state string for security
            
        Returns:
            Authorization URL to redirect user to
        """
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.scopes,
                redirect_uri=self.redirect_uri
            )
            
            authorization_url, _ = flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state,
                prompt='consent'  # Force consent screen to get refresh token
            )
            
            logger.info(f"Generated OAuth URL with state: {state}")
            return authorization_url
            
        except Exception as e:
            logger.error(f"Error generating OAuth URL: {e}")
            raise
    
    def exchange_code_for_tokens(self, code: str, state: str) -> Dict:
        """
        Exchange authorization code for access and refresh tokens
        
        Args:
            code: Authorization code from OAuth callback
            state: State parameter for verification
            
        Returns:
            Dictionary containing tokens and user info
        """
        try:
            flow = Flow.from_client_secrets_file(
                self.credentials_file,
                scopes=self.scopes,
                redirect_uri=self.redirect_uri,
                state=state
            )
            
            # Exchange code for credentials
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Get user email from Google
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            gmail_email = user_info.get('email')
            
            # Calculate token expiry
            token_expiry = None
            if credentials.expiry:
                token_expiry = credentials.expiry
            else:
                # Default to 1 hour from now
                token_expiry = datetime.utcnow() + timedelta(hours=1)
            
            result = {
                'access_token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'token_expiry': token_expiry,
                'gmail_email': gmail_email,
                'scopes': credentials.scopes
            }
            
            logger.info(f"Successfully exchanged code for tokens: {gmail_email}")
            return result
            
        except Exception as e:
            logger.error(f"Error exchanging code for tokens: {e}")
            raise
    
    def refresh_access_token(self, refresh_token: str) -> Dict:
        """
        Refresh an expired access token
        
        Args:
            refresh_token: The refresh token
            
        Returns:
            Dictionary with new access token and expiry
        """
        try:
            credentials = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=self._get_client_id(),
                client_secret=self._get_client_secret(),
                scopes=self.scopes
            )
            
            # Refresh the token
            credentials.refresh(Request())
            
            token_expiry = credentials.expiry or (datetime.utcnow() + timedelta(hours=1))
            
            result = {
                'access_token': credentials.token,
                'token_expiry': token_expiry
            }
            
            logger.info("Successfully refreshed access token")
            return result
            
        except Exception as e:
            logger.error(f"Error refreshing access token: {e}")
            raise
    
    def _get_client_id(self) -> str:
        """Get OAuth client ID from credentials file"""
        import json
        with open(self.credentials_file, 'r') as f:
            creds = json.load(f)
            if 'web' in creds:
                return creds['web']['client_id']
            elif 'installed' in creds:
                return creds['installed']['client_id']
            else:
                raise ValueError("Invalid credentials file format")
    
    def _get_client_secret(self) -> str:
        """Get OAuth client secret from credentials file"""
        import json
        with open(self.credentials_file, 'r') as f:
            creds = json.load(f)
            if 'web' in creds:
                return creds['web']['client_secret']
            elif 'installed' in creds:
                return creds['installed']['client_secret']
            else:
                raise ValueError("Invalid credentials file format")
    
    def build_gmail_service(self, access_token: str, refresh_token: Optional[str] = None):
        """
        Build Gmail API service with user credentials
        
        Args:
            access_token: User's access token
            refresh_token: User's refresh token (optional)
            
        Returns:
            Gmail API service object
        """
        try:
            credentials = Credentials(
                token=access_token,
                refresh_token=refresh_token,
                token_uri='https://oauth2.googleapis.com/token',
                client_id=self._get_client_id(),
                client_secret=self._get_client_secret(),
                scopes=self.scopes
            )
            
            service = build('gmail', 'v1', credentials=credentials)
            return service
            
        except Exception as e:
            logger.error(f"Error building Gmail service: {e}")
            raise
    
    def validate_token(self, access_token: str) -> bool:
        """
        Validate if an access token is still valid
        
        Args:
            access_token: Token to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            credentials = Credentials(token=access_token)
            service = build('gmail', 'v1', credentials=credentials)
            
            # Try to make a simple API call
            service.users().getProfile(userId='me').execute()
            return True
            
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return False


# Singleton instance
gmail_oauth = GmailOAuth()