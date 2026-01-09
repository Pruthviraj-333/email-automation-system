"""
Google OAuth for User Authentication (Sign in with Google)
"""
import os
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import logging

logger = logging.getLogger(__name__)

# OAuth Configuration for User Login
# NOTE: Using full Gmail scopes so user login also grants Gmail access
USER_AUTH_SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify'
]

CREDENTIALS_FILE = 'credentials.json'
REDIRECT_URI = os.getenv('OAUTH_REDIRECT_URI', 'http://localhost:3000/auth/callback')


class GoogleAuthHandler:
    """Handle Google OAuth for user authentication (login/signup)"""
    
    def __init__(self):
        self.credentials_file = CREDENTIALS_FILE
        self.redirect_uri = REDIRECT_URI
        self.scopes = USER_AUTH_SCOPES
    
    def get_login_url(self, state: str) -> str:
        """
        Generate Google OAuth URL for user login
        
        Args:
            state: Random state string for security
            
        Returns:
            Authorization URL for Google login
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
                prompt='select_account'  # Always show account picker
            )
            
            logger.info(f"Generated Google login URL with state: {state}")
            return authorization_url
            
        except Exception as e:
            logger.error(f"Error generating Google login URL: {e}")
            raise
    
    def verify_google_token(self, code: str, state: str) -> dict:
        """
        Verify Google OAuth token and get user info
        Also returns Gmail tokens if scopes include Gmail
        
        Args:
            code: Authorization code from Google
            state: State parameter for verification
            
        Returns:
            Dictionary with user info and optionally Gmail tokens
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
            
            # Get user info from Google
            service = build('oauth2', 'v2', credentials=credentials)
            user_info = service.userinfo().get().execute()
            
            result = {
                'email': user_info.get('email'),
                'name': user_info.get('name'),
                'picture': user_info.get('picture'),
                'google_id': user_info.get('id'),
                'verified_email': user_info.get('verified_email', False),
                # Include Gmail tokens if Gmail scopes were granted
                'gmail_access_token': credentials.token if credentials.token else None,
                'gmail_refresh_token': credentials.refresh_token if credentials.refresh_token else None,
                'gmail_token_expiry': credentials.expiry if credentials.expiry else None
            }
            
            logger.info(f"Successfully verified Google token for: {result['email']}")
            return result
            
        except Exception as e:
            logger.error(f"Error verifying Google token: {e}")
            raise


# Singleton instance
google_auth_handler = GoogleAuthHandler()