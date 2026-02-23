"""
Multi-Provider OAuth2 Authentication Module
============================================

Implements OAuth2 flows for Google, Yahoo, and Microsoft using Authlib.
Handles provider-specific user info parsing and token encryption.

Providers:
    - Google: Gmail access via googleapis.com
    - Yahoo: Yahoo Mail (App Password fallback - OAuth2 restricted 2026)
    - Microsoft: Outlook/Hotmail/Live via Microsoft Graph API

Author: MailRemover Team
Version: 2.2.0
"""

import os
import secrets
from typing import Optional, Dict, Any
from urllib.parse import urljoin

from authlib.integrations.flask_client import OAuth
from flask import session, url_for, request

from crypto_utils import encrypt_credential, decrypt_credential

# =============================================================================
# OAuth Provider Configuration
# =============================================================================

# Dynamic base URL detection
def get_base_url() -> str:
    """Get base URL for redirect URIs, supporting dev and production."""
    # Check for explicit override
    base_url = os.environ.get('MAILREMOVER_BASE_URL')
    if base_url:
        return base_url.rstrip('/')

    # Production default
    return 'https://mailremover.com'


def get_redirect_uri(provider: str) -> str:
    """Generate dynamic redirect URI for a provider."""
    base = get_base_url()
    # Google uses /callback (the original route)
    if provider == 'google':
        return f"{base}/callback"
    # Yahoo uses /auth/yahoo directly (not /callback)
    if provider == 'yahoo':
        return f"{base}/auth/yahoo"
    return f"{base}/auth/{provider}/callback"


# Provider configurations
PROVIDER_CONFIGS = {
    'google': {
        'name': 'google',
        'display_name': 'Google',
        'color': '#4285F4',
        'client_id': os.environ.get('GOOGLE_CLIENT_ID', ''),
        'client_secret': os.environ.get('GOOGLE_CLIENT_SECRET', ''),
        'authorize_url': 'https://accounts.google.com/o/oauth2/v2/auth',
        'token_url': 'https://oauth2.googleapis.com/token',
        'userinfo_url': 'https://www.googleapis.com/oauth2/v3/userinfo',
        'scopes': ['openid', 'email', 'profile', 'https://www.googleapis.com/auth/gmail.modify'],
        'jwks_uri': 'https://www.googleapis.com/oauth2/v3/certs',
    },
    'yahoo': {
        'name': 'yahoo',
        'display_name': 'Yahoo',
        'color': '#6001d2',
        # DISABLED: Yahoo OAuth temporarily disabled until IMAP integration is complete
        # Yahoo OAuth only provides identity, not mail access - needs App Password + IMAP
        'client_id': '',  # Disabled - was: os.environ.get('YAHOO_CLIENT_ID', '')
        'client_secret': '',  # Disabled - was: os.environ.get('YAHOO_CLIENT_SECRET', '')
        'authorize_url': 'https://api.login.yahoo.com/oauth2/request_auth',
        'token_url': 'https://api.login.yahoo.com/oauth2/get_token',
        'userinfo_url': 'https://api.login.yahoo.com/openid/v1/userinfo',
        'scopes': ['openid'],
    },
    'microsoft': {
        'name': 'microsoft',
        'display_name': 'Microsoft',
        'color': '#f25022',
        'client_id': os.environ.get('MICROSOFT_CLIENT_ID', ''),
        'client_secret': os.environ.get('MICROSOFT_CLIENT_SECRET', ''),
        # Use /consumers endpoint for personal accounts (@hotmail.com, @live.com, @outlook.com)
        # Note: /common supports both personal + work, /consumers restricts to personal only
        'authorize_url': 'https://login.microsoftonline.com/consumers/oauth2/v2.0/authorize',
        'token_url': 'https://login.microsoftonline.com/consumers/oauth2/v2.0/token',
        'userinfo_url': 'https://graph.microsoft.com/v1.0/me',
        'scopes': ['openid', 'profile', 'email', 'User.Read', 'Mail.Read', 'Mail.ReadWrite', 'offline_access'],
        'jwks_uri': 'https://login.microsoftonline.com/consumers/discovery/v2.0/keys',
    },
}


# =============================================================================
# OAuth Client Setup
# =============================================================================

def init_oauth(app):
    """Initialize OAuth clients for all providers."""
    oauth = OAuth(app)

    # Register Google OAuth client
    google_config = PROVIDER_CONFIGS['google']
    if google_config['client_id']:
        oauth.register(
            name='google',
            client_id=google_config['client_id'],
            client_secret=google_config['client_secret'],
            authorize_url=google_config['authorize_url'],
            access_token_url=google_config['token_url'],
            api_base_url='https://www.googleapis.com/',
            userinfo_endpoint=google_config['userinfo_url'],
            client_kwargs={
                'scope': ' '.join(google_config['scopes']),
                'token_endpoint_auth_method': 'client_secret_post',
            },
            jwks_uri=google_config['jwks_uri'],
        )

    # Register Microsoft OAuth client (supports Outlook, Hotmail, Live)
    ms_config = PROVIDER_CONFIGS['microsoft']
    if ms_config['client_id']:
        oauth.register(
            name='microsoft',
            client_id=ms_config['client_id'],
            client_secret=ms_config['client_secret'],
            authorize_url=ms_config['authorize_url'],
            access_token_url=ms_config['token_url'],
            api_base_url='https://graph.microsoft.com/v1.0/',
            userinfo_endpoint=ms_config['userinfo_url'],
            client_kwargs={
                'scope': ' '.join(ms_config['scopes']),
                'token_endpoint_auth_method': 'client_secret_post',
            },
            jwks_uri=ms_config['jwks_uri'],
        )

    # Note: Yahoo OAuth is restricted, we don't register it
    # Yahoo users will use App Password + IMAP flow

    return oauth


# =============================================================================
# User Info Parsing (Provider-Specific)
# =============================================================================

def parse_google_userinfo(userinfo: Dict[str, Any]) -> Dict[str, Any]:
    """Parse Google OAuth2 userinfo response."""
    return {
        'provider': 'google',
        'provider_id': userinfo.get('sub'),
        'email': userinfo.get('email'),
        'display_name': userinfo.get('name', userinfo.get('email', '').split('@')[0]),
        'given_name': userinfo.get('given_name'),
        'family_name': userinfo.get('family_name'),
        'avatar_url': userinfo.get('picture'),
        'email_verified': userinfo.get('email_verified', False),
    }


def parse_microsoft_userinfo(userinfo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Microsoft Graph API /me response.

    Microsoft Graph returns:
    {
        "id": "unique-user-id",
        "displayName": "John Doe",
        "givenName": "John",
        "surname": "Doe",
        "mail": "john@outlook.com",  # May be null for personal accounts
        "userPrincipalName": "john_outlook.com#EXT#@..."  # For personal accounts
    }
    """
    # For personal accounts, mail might be null - use userPrincipalName
    email = userinfo.get('mail') or userinfo.get('userPrincipalName', '')

    # Clean up userPrincipalName format (remove #EXT# suffix for display)
    if '#EXT#' in email:
        email = email.split('#EXT#')[0].replace('_', '@')

    return {
        'provider': 'microsoft',
        'provider_id': userinfo.get('id'),
        'email': email,
        'display_name': userinfo.get('displayName', email.split('@')[0] if email else 'User'),
        'given_name': userinfo.get('givenName'),
        'family_name': userinfo.get('surname'),
        'avatar_url': None,  # Microsoft Graph requires separate call for photo
        'email_verified': True,  # Microsoft accounts are verified
    }


def parse_yahoo_userinfo(userinfo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse Yahoo OpenID Connect userinfo response.

    Yahoo returns:
    {
        "sub": "unique-user-id",
        "name": "John Doe",
        "given_name": "John",
        "family_name": "Doe",
        "email": "john@yahoo.com",
        "picture": "https://..."
    }
    """
    return {
        'provider': 'yahoo',
        'provider_id': userinfo.get('sub'),
        'email': userinfo.get('email'),
        'display_name': userinfo.get('name', userinfo.get('email', '').split('@')[0]),
        'given_name': userinfo.get('given_name'),
        'family_name': userinfo.get('family_name'),
        'avatar_url': userinfo.get('picture'),
        'email_verified': userinfo.get('email_verified', False),
    }


def parse_userinfo(provider: str, userinfo: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse userinfo based on provider with universal email fallback.

    Email fallback sequence (handles provider differences):
        - email: Google, Yahoo standard
        - mail: Microsoft Graph primary
        - userPrincipalName: Microsoft personal account fallback
    """
    parsers = {
        'google': parse_google_userinfo,
        'microsoft': parse_microsoft_userinfo,
        'yahoo': parse_yahoo_userinfo,
    }
    parser = parsers.get(provider, lambda x: x)
    parsed = parser(userinfo)

    # Universal email fallback: email -> mail -> userPrincipalName
    if not parsed.get('email'):
        email = (
            userinfo.get('email') or
            userinfo.get('mail') or
            userinfo.get('userPrincipalName', '')
        )
        # Clean userPrincipalName format (#EXT# suffix for personal accounts)
        if '#EXT#' in email:
            email = email.split('#EXT#')[0].replace('_', '@')
        parsed['email'] = email

    return parsed


# =============================================================================
# Token Storage (Encrypted)
# =============================================================================

def encrypt_tokens(token_data: Dict[str, Any]) -> Dict[str, str]:
    """Encrypt OAuth tokens for database storage."""
    encrypted = {}

    if token_data.get('access_token'):
        encrypted['access_token_encrypted'] = encrypt_credential(token_data['access_token'])

    if token_data.get('refresh_token'):
        encrypted['refresh_token_encrypted'] = encrypt_credential(token_data['refresh_token'])

    return encrypted


def decrypt_tokens(encrypted_data: Dict[str, str]) -> Dict[str, Optional[str]]:
    """Decrypt OAuth tokens from database."""
    decrypted = {}

    if encrypted_data.get('access_token_encrypted'):
        decrypted['access_token'] = decrypt_credential(encrypted_data['access_token_encrypted'])

    if encrypted_data.get('refresh_token_encrypted'):
        decrypted['refresh_token'] = decrypt_credential(encrypted_data['refresh_token_encrypted'])

    return decrypted


# =============================================================================
# Session Helpers
# =============================================================================

def store_provider_session(provider: str, userinfo: Dict[str, Any], token_data: Dict[str, Any]):
    """Store provider authentication in session."""
    parsed = parse_userinfo(provider, userinfo)

    # Normalize provider name: 'google' -> 'gmail' for consistency with UI
    normalized_provider = 'gmail' if provider == 'google' else provider

    session['auth_provider'] = normalized_provider
    session['user_email'] = parsed.get('email')
    session['user_display_name'] = parsed.get('display_name')
    session['provider_id'] = parsed.get('provider_id')

    # Note: Token data is stored in provider-specific keys (google_credentials,
    # microsoft_credentials, yahoo_credentials) by the callback handlers in app.py.
    # We don't store oauth_tokens here to avoid session size bloat.

    # Update connected providers list
    if 'connected_providers' not in session:
        session['connected_providers'] = []

    connected = session['connected_providers']
    provider_entry = {'name': normalized_provider, 'email': parsed.get('email')}

    existing = next((p for p in connected if p['name'] == normalized_provider), None)
    if existing:
        existing['email'] = parsed.get('email')
    else:
        connected.append(provider_entry)

    session['connected_providers'] = connected
    session['primary_provider'] = normalized_provider


def is_provider_configured(provider: str) -> bool:
    """Check if a provider has OAuth credentials configured."""
    config = PROVIDER_CONFIGS.get(provider, {})
    return bool(config.get('client_id') and config.get('client_secret'))


def get_provider_config(provider: str) -> Optional[Dict[str, Any]]:
    """Get configuration for a provider."""
    return PROVIDER_CONFIGS.get(provider)
