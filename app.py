"""
MailRemover - Flask Web Application with Direct SSL
====================================================

A privacy-focused web app for cleaning Gmail inboxes.
Runs with direct SSL handling on port 8000.

Routes:
    /                   - Homepage (login or dashboard)
    /login              - Initiate Google OAuth flow
    /callback           - OAuth callback from Google
    /login/yahoo        - Redirect to dashboard with Yahoo App Password modal
                          (Yahoo OAuth2 is restricted as of 2026)
    /login/outlook      - Initiate Microsoft OAuth2 flow for Outlook
    /callback/outlook   - OAuth callback from Microsoft
    /logout             - Clear session and revoke access
    /scan               - Scan inbox with query
    /trash              - Move selected emails to trash
    /archive            - Archive selected emails

Usage:
    sudo python app.py  # Requires sudo for Let's Encrypt certs
"""

import os
import ssl
import json
import secrets
import stripe
from pathlib import Path
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Load environment variables from .env file
load_dotenv()
from functools import wraps

# Thread-local storage for Gmail service instances
_thread_local = threading.local()
from flask import (
    Flask,
    redirect,
    url_for,
    session,
    request,
    render_template,
    jsonify,
    flash,
    send_file,
)
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from werkzeug.middleware.proxy_fix import ProxyFix

# Local imports
import database as db
from crypto_utils import encrypt_credential, decrypt_credential
import vault_r2

# =============================================================================
# Configuration
# =============================================================================

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

# =============================================================================
# Session Security Configuration (Required for OAuth Verification)
# =============================================================================
app.config.update(
    SESSION_COOKIE_SECURE=True,       # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY=True,     # Prevent JavaScript access to session cookie
    SESSION_COOKIE_SAMESITE='Lax',    # CSRF protection for cross-site requests
    PERMANENT_SESSION_LIFETIME=604800,  # 7 days in seconds
)

# ProxyFix: Handle X-Forwarded-Proto from Nginx/Gunicorn for correct redirect_uri
# x_for=1: Trust X-Forwarded-For (client IP)
# x_proto=1: Trust X-Forwarded-Proto (https detection)
# x_host=1: Trust X-Forwarded-Host (domain)
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# OAuth Configuration
# Google OAuth - prefer environment variables over credentials.json file
GOOGLE_CLIENT_ID = os.environ.get('GOOGLE_CLIENT_ID', '')
GOOGLE_CLIENT_SECRET = os.environ.get('GOOGLE_CLIENT_SECRET', '')
CLIENT_SECRETS_FILE = 'credentials.json'  # Fallback only
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

# Production SSL Configuration
SSL_CERT = '/etc/letsencrypt/live/mailremover.com/fullchain.pem'
SSL_KEY = '/etc/letsencrypt/live/mailremover.com/privkey.pem'

# Fixed redirect URI for production
REDIRECT_URI = 'https://mailremover.com/callback'

# Token file path
TOKEN_FILE = Path('/var/www/mailremover/token.json')

# Stripe Configuration
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY', '')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY', '')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET', '')
STRIPE_PRICES = {
    'maintenance': os.environ.get('STRIPE_PRICE_MAINTENANCE', ''),  # $5/mo Maintenance subscription
    'purge': os.environ.get('STRIPE_PRICE_PURGE', ''),  # $15 One-Time Purge
}

# Microsoft OAuth2 Configuration (for Outlook)
# Note: Yahoo OAuth2 is restricted for new clients (as of 2026) - use App Password + IMAP instead
MICROSOFT_CLIENT_ID = os.environ.get('MICROSOFT_CLIENT_ID', '')
MICROSOFT_CLIENT_SECRET = os.environ.get('MICROSOFT_CLIENT_SECRET', '')
# Dynamic redirect URI based on environment (dev vs prod)
# Set MICROSOFT_REDIRECT_URI env var in development to override production default
MICROSOFT_REDIRECT_URI = os.environ.get('MICROSOFT_REDIRECT_URI', 'https://mailremover.com/callback/outlook')
MICROSOFT_AUTHORIZE_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
MICROSOFT_TOKEN_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
# OpenID Connect scopes for profile info + Mail permissions
# - openid: Required for OpenID Connect
# - profile: Access to user's display name (displayName, givenName, surname)
# - email: Access to user's email address
# - Mail.Read/Mail.ReadWrite: Access to user's mailbox
MICROSOFT_SCOPES = ['openid', 'profile', 'email', 'Mail.Read', 'Mail.ReadWrite']


# =============================================================================
# Helper Functions
# =============================================================================

def get_flow():
    """Create OAuth flow for web application.

    Prefers environment variables (GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET) for security.
    Falls back to credentials.json file if environment variables are not set.
    """
    # Prefer environment variables over credentials file (more secure)
    if GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET:
        # Build client config from environment variables (web application format)
        client_config = {
            'web': {
                'client_id': GOOGLE_CLIENT_ID,
                'client_secret': GOOGLE_CLIENT_SECRET,
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'redirect_uris': [REDIRECT_URI],
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
    else:
        # Fallback to credentials.json file
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=SCOPES,
            redirect_uri=REDIRECT_URI
        )
    return flow


def credentials_to_dict(credentials):
    """Convert credentials object to dictionary for session storage."""
    return {
        'token': credentials.token,
        'refresh_token': credentials.refresh_token,
        'token_uri': credentials.token_uri,
        'client_id': credentials.client_id,
        'client_secret': credentials.client_secret,
        'scopes': list(credentials.scopes) if credentials.scopes else SCOPES
    }


def save_token(credentials):
    """Save credentials to token.json file."""
    try:
        token_data = credentials_to_dict(credentials)
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token_data, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save token: {e}")


def load_token():
    """Load credentials from token.json file if it exists."""
    if not TOKEN_FILE.exists():
        return None

    try:
        with open(TOKEN_FILE, 'r') as f:
            token_data = json.load(f)

        credentials = Credentials(
            token=token_data.get('token'),
            refresh_token=token_data.get('refresh_token'),
            token_uri=token_data.get('token_uri'),
            client_id=token_data.get('client_id'),
            client_secret=token_data.get('client_secret'),
            scopes=token_data.get('scopes', SCOPES)
        )

        # Refresh if expired
        if credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
            save_token(credentials)

        return credentials
    except Exception as e:
        print(f"Warning: Could not load token: {e}")
        return None


def clear_auth(clear_providers=False, provider=None):
    """Clear authentication data from session, optionally for a specific provider.

    Args:
        clear_providers: If True, clears everything including connected_providers list
        provider: If specified, only clears credentials for this provider (preserves others)
    """
    print(f"clear_auth: clear_providers={clear_providers}, provider={provider}")

    if clear_providers:
        # Nuclear option - clear everything
        session.clear()
        print(f"clear_auth: Cleared entire session")
    elif provider:
        # Surgical option - only clear specific provider's credentials
        provider_key_map = {
            'google': 'google_credentials',
            'gmail': 'google_credentials',
            'microsoft': 'microsoft_credentials',
            'outlook': 'microsoft_credentials',
            'yahoo': 'yahoo_credentials',
        }
        cred_key = provider_key_map.get(provider)
        if cred_key and cred_key in session:
            del session[cred_key]
            print(f"clear_auth: Removed {cred_key} from session")

        # Also remove from connected_providers list
        connected = session.get('connected_providers', [])
        session['connected_providers'] = [p for p in connected if p.get('name') != provider]

        # If we just removed the primary provider, switch to another
        if session.get('primary_provider') == provider:
            remaining = session.get('connected_providers', [])
            if remaining:
                session['primary_provider'] = remaining[0].get('name', 'gmail')
            else:
                session.pop('primary_provider', None)

        session.modified = True
        print(f"clear_auth: Updated connected_providers = {session.get('connected_providers')}")
    else:
        # Legacy behavior - clear session but preserve connected_providers
        connected_providers = session.get('connected_providers', [])
        google_creds = session.get('google_credentials')
        microsoft_creds = session.get('microsoft_credentials')
        yahoo_creds = session.get('yahoo_credentials')
        primary = session.get('primary_provider')

        session.clear()

        # Restore provider data
        if connected_providers:
            session['connected_providers'] = connected_providers
        if google_creds:
            session['google_credentials'] = google_creds
            session['credentials'] = google_creds  # Legacy key
        if microsoft_creds:
            session['microsoft_credentials'] = microsoft_creds
        if yahoo_creds:
            session['yahoo_credentials'] = yahoo_creds
        if primary:
            session['primary_provider'] = primary

        session.modified = True
        print(f"clear_auth: Preserved provider credentials during auth clear")


def verify_provider_tokens() -> dict:
    """
    Verify OAuth tokens for all providers on page load.

    Returns dict with:
        - valid_providers: List of providers with working tokens
        - invalid_providers: List of providers with expired/missing tokens
        - should_reauth: True if primary provider token is invalid
    """
    result = {
        'valid_providers': [],
        'invalid_providers': [],
        'should_reauth': False,
        'google_valid': False,
        'yahoo_valid': False,
        'microsoft_valid': False,
    }

    # Debug: Log session keys at start
    print(f"verify_provider_tokens: Session keys = {list(session.keys())}")

    # Check Google/Gmail credentials (check google_credentials first, fallback to credentials)
    google_creds = session.get('google_credentials') or session.get('credentials')
    print(f"verify_provider_tokens: google_creds found = {google_creds is not None}")
    if google_creds:
        try:
            credentials = Credentials(
                token=google_creds.get('token'),
                refresh_token=google_creds.get('refresh_token'),
                token_uri=google_creds.get('token_uri'),
                client_id=google_creds.get('client_id'),
                client_secret=google_creds.get('client_secret'),
                scopes=google_creds.get('scopes', SCOPES)
            )

            # Try to refresh if expired
            if credentials.expired and credentials.refresh_token:
                print(f"verify_provider_tokens: Google token expired, attempting refresh...")
                try:
                    credentials.refresh(Request())
                    # Store in both locations for compatibility
                    refreshed = credentials_to_dict(credentials)
                    session['google_credentials'] = refreshed
                    session['credentials'] = refreshed
                    session.modified = True
                    # BUG FIX: Mark as valid AFTER successful refresh
                    result['valid_providers'].append('google')
                    result['google_valid'] = True
                    print(f"verify_provider_tokens: Google token refreshed successfully")
                except Exception as refresh_err:
                    print(f"verify_provider_tokens: Google token refresh failed: {refresh_err}")
                    result['invalid_providers'].append('google')
                    result['google_valid'] = False
            else:
                # Quick validation - check if token exists
                if credentials.token:
                    result['valid_providers'].append('google')
                    result['google_valid'] = True
                    print(f"verify_provider_tokens: Google token valid (not expired)")
                else:
                    result['invalid_providers'].append('google')
                    print(f"verify_provider_tokens: Google token missing")
        except Exception as e:
            print(f"verify_provider_tokens: Google token verification failed: {e}")
            result['invalid_providers'].append('google')
    else:
        # No Google credentials found - only mark invalid if not checking other providers
        print(f"verify_provider_tokens: No Google credentials in session")
        result['invalid_providers'].append('google')

    # Check Microsoft credentials
    if 'microsoft_credentials' in session:
        try:
            ms_creds = session['microsoft_credentials']
            # Check for 'token' (unified auth) or 'access_token' (legacy MS callback)
            token = ms_creds.get('token') or ms_creds.get('access_token')
            if token:
                result['valid_providers'].append('microsoft')
                result['microsoft_valid'] = True
                print(f"verify_provider_tokens: Microsoft token valid")
            else:
                result['invalid_providers'].append('microsoft')
                print(f"verify_provider_tokens: Microsoft token missing")
        except Exception as e:
            print(f"verify_provider_tokens: Microsoft token verification failed: {e}")
            result['invalid_providers'].append('microsoft')

    # Check Yahoo credentials
    if 'yahoo_credentials' in session:
        try:
            yahoo_creds = session['yahoo_credentials']
            if yahoo_creds.get('token'):
                result['valid_providers'].append('yahoo')
                result['yahoo_valid'] = True
                print(f"verify_provider_tokens: Yahoo token valid")
            else:
                result['invalid_providers'].append('yahoo')
                print(f"verify_provider_tokens: Yahoo token missing")
        except Exception as e:
            print(f"verify_provider_tokens: Yahoo token verification failed: {e}")
            result['invalid_providers'].append('yahoo')

    # Check if we have any valid credentials at all
    primary = session.get('primary_provider', 'gmail')
    print(f"verify_provider_tokens: primary_provider = {primary}, valid = {result['valid_providers']}")

    # Only require reauth if the PRIMARY provider is invalid AND no other providers are valid
    if primary in ['google', 'gmail'] and not result['google_valid']:
        # Only force reauth if Google is primary AND no other providers are valid
        if not result['microsoft_valid'] and not result['yahoo_valid']:
            result['should_reauth'] = True
            print(f"verify_provider_tokens: should_reauth=True (Google primary, no fallbacks)")
    elif primary == 'microsoft' and not result['microsoft_valid']:
        if not result['google_valid'] and not result['yahoo_valid']:
            result['should_reauth'] = True
            print(f"verify_provider_tokens: should_reauth=True (Microsoft primary, no fallbacks)")
    elif primary == 'yahoo' and not result['yahoo_valid']:
        if not result['google_valid'] and not result['microsoft_valid']:
            result['should_reauth'] = True
            print(f"verify_provider_tokens: should_reauth=True (Yahoo primary, no fallbacks)")

    print(f"verify_provider_tokens: Final result = {result}")
    return result


def sync_connected_providers():
    """
    Synchronize connected_providers list with actual token state.
    Removes providers that no longer have valid credentials.
    Also ensures primary_provider is valid after sync.
    """
    token_status = verify_provider_tokens()
    connected = session.get('connected_providers', [])
    print(f"sync_connected_providers: Before sync: {connected}")

    # Filter to only providers with valid tokens
    valid_connected = []
    for provider in connected:
        name = provider.get('name', '')
        if name in ['gmail', 'google'] and token_status['google_valid']:
            valid_connected.append(provider)
        elif name == 'yahoo' and token_status.get('yahoo_valid', False):
            valid_connected.append(provider)
        elif name in ['microsoft', 'outlook'] and token_status.get('microsoft_valid', False):
            valid_connected.append(provider)

    session['connected_providers'] = valid_connected
    print(f"sync_connected_providers: After sync: {valid_connected}")

    # Ensure primary_provider is still valid after cleanup
    current_primary = session.get('primary_provider', 'gmail')
    valid_names = [p.get('name', '') for p in valid_connected]

    # Handle gmail/google aliasing
    if current_primary in ['gmail', 'google']:
        if 'gmail' not in valid_names and 'google' not in valid_names:
            # Primary provider was removed, switch to first available
            if valid_connected:
                new_primary = valid_connected[0].get('name', 'gmail')
                session['primary_provider'] = new_primary
                print(f"sync_connected_providers: Primary switched from {current_primary} to {new_primary}")
    elif current_primary not in valid_names:
        # Primary provider was removed, switch to first available
        if valid_connected:
            new_primary = valid_connected[0].get('name', 'gmail')
            session['primary_provider'] = new_primary
            print(f"sync_connected_providers: Primary switched from {current_primary} to {new_primary}")

    session.modified = True
    return valid_connected


def init_provider_session(provider='gmail', email=None):
    """Initialize or update provider session data.

    This function manages the multi-provider session state, allowing users
    to connect multiple email providers (Gmail, Yahoo, Microsoft) simultaneously.

    Args:
        provider: Provider name ('gmail', 'yahoo', 'microsoft')
        email: User's email address for this provider
    """
    print(f"init_provider_session: Initializing provider={provider}, email={email}")

    # Initialize connected_providers list if not exists
    if 'connected_providers' not in session:
        session['connected_providers'] = []

    # Add provider to connected list if not already present
    connected = session['connected_providers']
    provider_entry = {'name': provider, 'email': email}

    # Check if provider already connected (update email if so)
    existing = next((p for p in connected if p['name'] == provider), None)
    if existing:
        existing['email'] = email
        print(f"init_provider_session: Updated existing provider {provider} with email {email}")
    else:
        connected.append(provider_entry)
        session['connected_providers'] = connected
        print(f"init_provider_session: Added new provider {provider}")

    # Set primary_provider if not set, or if this is the first connection
    if 'primary_provider' not in session or len(connected) == 1:
        session['primary_provider'] = provider
        print(f"init_provider_session: Set primary_provider to {provider}")

    session.modified = True
    print(f"init_provider_session: Final connected_providers = {session['connected_providers']}")


def get_connected_providers():
    """Get list of connected providers with their details."""
    return session.get('connected_providers', [])


def get_primary_provider():
    """Get the current primary provider."""
    return session.get('primary_provider', 'gmail')


def get_user_display_name():
    """Get user's display name for personalized greetings.

    Returns the display name in order of preference:
    1. Stored display name from OAuth profile (Microsoft Graph displayName/givenName)
    2. First part of email address (before @)
    3. 'User' as fallback

    Returns:
        str: User's display name for UI personalization
    """
    return session.get('user_display_name', session.get('user_email', 'User').split('@')[0])


def set_primary_provider(provider):
    """Set the primary provider for the session."""
    connected = session.get('connected_providers', [])
    provider_names = [p['name'] for p in connected]
    if provider in provider_names:
        session['primary_provider'] = provider
        session.modified = True
        print(f"Primary provider set to: {provider}")
        return True
    print(f"Failed to set primary provider to {provider}. Connected: {provider_names}")
    return False


def get_credentials():
    """Get credentials from session or token file, refresh if needed.

    Checks google_credentials first (normalized key), then falls back to
    credentials (legacy key) for backward compatibility.
    """
    # Check for Google credentials (normalized key first, then legacy fallback)
    creds_dict = session.get('google_credentials') or session.get('credentials')

    if creds_dict:
        print(f"get_credentials: Found credentials in session")
        try:
            credentials = Credentials(
                token=creds_dict.get('token'),
                refresh_token=creds_dict.get('refresh_token'),
                token_uri=creds_dict.get('token_uri'),
                client_id=creds_dict.get('client_id'),
                client_secret=creds_dict.get('client_secret'),
                scopes=creds_dict.get('scopes', SCOPES)
            )

            # Refresh if expired
            if credentials.expired and credentials.refresh_token:
                try:
                    print(f"get_credentials: Token expired, refreshing...")
                    credentials.refresh(Request())
                    refreshed = credentials_to_dict(credentials)
                    # Store in BOTH keys for consistency
                    session['google_credentials'] = refreshed
                    session['credentials'] = refreshed
                    session.modified = True
                    save_token(credentials)
                    print(f"get_credentials: Token refreshed and saved")
                except Exception as e:
                    print(f"get_credentials: Token refresh failed: {e}")
                    clear_auth()
                    return None

            # Validate token by making a test API call
            try:
                service = build('gmail', 'v1', credentials=credentials)
                profile = service.users().getProfile(userId='me').execute()
                # Update user email in session
                session['user_email'] = profile.get('emailAddress', 'Unknown')
                return credentials
            except Exception as e:
                print(f"get_credentials: Token validation failed: {e}")
                clear_auth()
                return None

        except Exception as e:
            print(f"get_credentials: Credentials creation failed: {e}")
            clear_auth()
            return None

    # Fall back to token file
    print(f"get_credentials: No session credentials, checking token file...")
    credentials = load_token()
    if credentials:
        try:
            # Validate token by making a test API call
            service = build('gmail', 'v1', credentials=credentials)
            profile = service.users().getProfile(userId='me').execute()
            creds_dict = credentials_to_dict(credentials)
            # Store in BOTH keys for consistency
            session['google_credentials'] = creds_dict
            session['credentials'] = creds_dict
            session['user_email'] = profile.get('emailAddress', 'Unknown')
            session.modified = True
            print(f"get_credentials: Loaded from token file, email={session['user_email']}")
            return credentials
        except Exception as e:
            print(f"get_credentials: Token file validation failed: {e}")
            # Token from file is invalid, delete it
            try:
                TOKEN_FILE.unlink(missing_ok=True)
            except:
                pass
            clear_auth()
            return None

    print(f"get_credentials: No valid credentials found")
    return None


def get_gmail_service():
    """Get authenticated Gmail API service."""
    credentials = get_credentials()
    if not credentials:
        return None
    return build('gmail', 'v1', credentials=credentials)


def login_required(f):
    """Decorator to require authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        credentials = get_credentials()
        if not credentials:
            return redirect(url_for('login', _external=True, _scheme='https'))
        return f(*args, **kwargs)
    return decorated_function


# =============================================================================
# Security Headers Middleware (Required for OAuth Verification)
# =============================================================================

@app.after_request
def set_security_headers(response):
    """Add security headers to all responses."""
    # Prevent MIME type sniffing
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # Prevent clickjacking
    response.headers['X-Frame-Options'] = 'DENY'
    # Enable HSTS (1 year)
    response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    # XSS Protection (legacy browsers)
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Referrer policy
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    # Permissions policy (disable unnecessary features)
    response.headers['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=()'
    return response


# =============================================================================
# Routes - Authentication
# =============================================================================

@app.route('/')
def index():
    """Homepage - show login or dashboard."""
    # Check for existing credentials (session or token file)
    credentials = get_credentials()
    if credentials:
        return redirect(url_for('dashboard', _external=True, _scheme='https'))
    return render_template('index.html')


@app.route('/privacy')
def privacy():
    """Privacy Policy page."""
    return render_template('privacy.html')


@app.route('/tos')
def tos():
    """Terms of Service page."""
    return render_template('tos.html')


@app.route('/support')
def support():
    """Support page with verified security channels."""
    return render_template('support.html')


@app.route('/version.json')
def version_json():
    """Serve version information as JSON."""
    import json
    import os
    version_file = os.path.join(os.path.dirname(__file__), 'version.json')
    try:
        with open(version_file, 'r') as f:
            return app.response_class(
                response=f.read(),
                mimetype='application/json'
            )
    except FileNotFoundError:
        return {'version': '2.1.0', 'release_date': '2026-01-14'}


@app.route('/pricing')
def pricing():
    """Pricing page."""
    user_email = session.get('user_email')
    user_tier = 'free'

    if user_email:
        user = db.get_or_create_user(user_email)
        user_tier = user.get('tier', 'free')

    spots_remaining = db.get_lifetime_spots_remaining()
    return render_template(
        'pricing.html',
        user_email=user_email,
        user_tier=user_tier,
        spots_remaining=spots_remaining
    )


# =============================================================================
# Routes - Stripe Payments
# =============================================================================

@app.route('/create-checkout', methods=['POST'])
@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout():
    """Create a Stripe Checkout session for Purge ($15) or Maintenance ($5/mo)."""
    price_type = request.form.get('price_type', 'maintenance')
    user_email = session.get('user_email')

    if not user_email:
        flash('Please sign in first.', 'error')
        return redirect(url_for('login', _external=True, _scheme='https'))

    # Ensure user exists in database
    user = db.get_or_create_user(user_email)

    # Check if already has active Maintenance subscription
    if user.get('tier') == 'pro' and user.get('subscription_status') == 'active':
        flash('You already have an active Maintenance subscription!', 'info')
        return redirect(url_for('dashboard', _external=True, _scheme='https'))

    # Check if already has active Purge
    if user.get('tier') == 'purge':
        flash('You already have an active Purge! Enjoy your 30 days of unlimited cleaning.', 'info')
        return redirect(url_for('dashboard', _external=True, _scheme='https'))

    try:
        # Get or create Stripe customer
        customer_id = user.get('stripe_customer_id')
        if not customer_id:
            customer = stripe.Customer.create(email=user_email)
            customer_id = customer.id
            db.update_user_stripe(user_email, customer_id)

        # Determine mode based on price type
        # purge = one-time payment, maintenance = subscription
        mode = 'payment' if price_type == 'purge' else 'subscription'
        price_id = STRIPE_PRICES.get(price_type)

        if not price_id:
            # Price ID not configured - show error
            flash('Payment system not fully configured. Please contact support.', 'error')
            return redirect(url_for('pricing', _external=True, _scheme='https'))

        # Create checkout session with production settings
        checkout_params = {
            'customer': customer_id,
            'line_items': [{'price': price_id, 'quantity': 1}],
            'mode': mode,
            'success_url': 'https://mailremover.com/success?session_id={CHECKOUT_SESSION_ID}',
            'cancel_url': 'https://mailremover.com/cancel',
            'metadata': {
                'user_email': user_email,
                'price_type': price_type
            }
        }

        # Add statement descriptor for one-time payments (Purge)
        if mode == 'payment':
            checkout_params['payment_intent_data'] = {
                'statement_descriptor': 'MAILREMOVER.COM',
                'statement_descriptor_suffix': 'PURGE'
            }
        else:
            # For subscriptions, set descriptor in subscription data
            checkout_params['subscription_data'] = {
                'description': 'MailRemover Maintenance - Unlimited email cleaning'
            }

        checkout_session = stripe.checkout.Session.create(**checkout_params)

        return redirect(checkout_session.url, code=303)

    except stripe.error.StripeError as e:
        flash(f'Payment error: {str(e)}', 'error')
        return redirect(url_for('pricing', _external=True, _scheme='https'))


@app.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')

    # Debug logging
    print(f"[WEBHOOK DEBUG] Received webhook request")
    print(f"[WEBHOOK DEBUG] Signature header: {sig_header[:50]}..." if sig_header else "[WEBHOOK DEBUG] Signature header: MISSING")
    print(f"[WEBHOOK DEBUG] Payload length: {len(payload)} bytes")
    print(f"[WEBHOOK DEBUG] Webhook secret configured: {bool(STRIPE_WEBHOOK_SECRET)}")
    print(f"[WEBHOOK DEBUG] Webhook secret starts with: {STRIPE_WEBHOOK_SECRET[:10]}..." if STRIPE_WEBHOOK_SECRET else "N/A")

    if not STRIPE_WEBHOOK_SECRET:
        print("[WEBHOOK ERROR] Stripe webhook secret not configured")
        return jsonify({'status': 'webhook_secret_missing'}), 400

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
        print(f"[WEBHOOK DEBUG] Event constructed successfully: {event['type']}")
    except ValueError as e:
        print(f"[WEBHOOK ERROR] Invalid payload: {str(e)}")
        return jsonify({'status': 'invalid_payload', 'error': str(e)}), 400
    except stripe.error.SignatureVerificationError as e:
        print(f"[WEBHOOK ERROR] Signature verification failed: {str(e)}")
        print(f"[WEBHOOK DEBUG] Expected secret starts with: {STRIPE_WEBHOOK_SECRET[:15]}...")
        return jsonify({'status': 'invalid_signature', 'error': str(e)}), 400

    # Handle the event
    event_type = event['type']
    data = event['data']['object']

    print(f"Stripe webhook received: {event_type}")

    if event_type == 'checkout.session.completed':
        # Payment successful
        customer_email = data.get('customer_email') or data.get('metadata', {}).get('user_email')
        price_type = data.get('metadata', {}).get('price_type', 'maintenance')
        subscription_id = data.get('subscription')

        if customer_email:
            if price_type == 'purge':
                # One-time purge: 30 days of unlimited access
                db.upgrade_user_to_purge(customer_email)
                print(f"User {customer_email} upgraded to Purge (30 days)")
            else:
                # Maintenance subscription ($5/mo)
                db.upgrade_user_to_pro(customer_email, subscription_id)
                print(f"User {customer_email} upgraded to Maintenance")

    elif event_type == 'customer.subscription.updated':
        # Subscription status changed
        customer_id = data.get('customer')
        status = data.get('status')
        user = db.get_user_by_stripe_customer(customer_id)

        if user:
            if status == 'active':
                db.update_subscription_status(user['email'], 'active')
            elif status in ('past_due', 'unpaid'):
                db.update_subscription_status(user['email'], 'past_due')
            print(f"Subscription status updated for {user['email']}: {status}")

    elif event_type == 'customer.subscription.deleted':
        # Subscription canceled
        customer_id = data.get('customer')
        user = db.get_user_by_stripe_customer(customer_id)

        if user:
            db.downgrade_user_to_free(user['email'])
            print(f"User {user['email']} downgraded to Free")

    elif event_type == 'invoice.payment_failed':
        # Payment failed
        customer_id = data.get('customer')
        user = db.get_user_by_stripe_customer(customer_id)

        if user:
            db.update_subscription_status(user['email'], 'past_due')
            print(f"Payment failed for {user['email']}")

    return jsonify({'status': 'success'}), 200


@app.route('/success')
@login_required
def success():
    """Payment success page."""
    user_email = session.get('user_email')
    demo_mode = request.args.get('demo') == '1'
    session_id = request.args.get('session_id')
    price_type_param = request.args.get('price_type', 'maintenance')
    receipt_url = None

    # Update session with new tier
    if user_email:
        user = db.get_or_create_user(user_email)

        # If coming from Stripe, verify the session and get receipt
        if session_id and not demo_mode:
            try:
                checkout_session = stripe.checkout.Session.retrieve(session_id, expand=['payment_intent', 'invoice'])
                price_type = checkout_session.metadata.get('price_type', 'maintenance')

                if checkout_session.payment_status == 'paid':
                    if price_type == 'purge':
                        db.upgrade_user_to_purge(user_email)
                        # Get receipt from payment intent for one-time payments
                        if checkout_session.payment_intent:
                            payment_intent = checkout_session.payment_intent
                            if hasattr(payment_intent, 'latest_charge') and payment_intent.latest_charge:
                                try:
                                    charge = stripe.Charge.retrieve(payment_intent.latest_charge)
                                    receipt_url = charge.receipt_url
                                except Exception:
                                    pass
                    else:
                        db.upgrade_user_to_pro(user_email, checkout_session.subscription)
                        # Get receipt from invoice for subscriptions
                        if checkout_session.invoice:
                            receipt_url = checkout_session.invoice.hosted_invoice_url

                    # Refresh user data
                    user = db.get_user_by_email(user_email)
            except Exception as e:
                print(f"Error verifying checkout session: {e}")

        # For demo mode, use session tier set during checkout
        if demo_mode:
            user_tier = session.get('user_tier', 'purge' if price_type_param == 'purge' else 'pro')
        else:
            user_tier = user.get('tier', 'free')

        session['user_tier'] = user_tier
        total_cleaned = user.get('total_emails_cleaned', 0)
    else:
        user_tier = 'free'
        total_cleaned = 0

    return render_template(
        'success.html',
        user_email=user_email,
        user_tier=user_tier,
        total_cleaned=total_cleaned,
        demo_mode=demo_mode,
        receipt_url=receipt_url
    )


@app.route('/cancel')
def cancel():
    """Payment canceled page."""
    return render_template('cancel.html')


@app.route('/billing')
@login_required
def billing():
    """Redirect to Stripe Customer Portal for subscription management."""
    user_email = session.get('user_email')
    user = db.get_user_by_email(user_email)

    if not user or not user.get('stripe_customer_id'):
        flash('No billing information found.', 'error')
        return redirect(url_for('pricing', _external=True, _scheme='https'))

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=user['stripe_customer_id'],
            return_url=url_for('dashboard', _external=True, _scheme='https')
        )
        return redirect(portal_session.url, code=303)
    except stripe.error.StripeError as e:
        flash(f'Error accessing billing portal: {str(e)}', 'error')
        return redirect(url_for('dashboard', _external=True, _scheme='https'))


@app.route('/login')
def login():
    """Initiate OAuth flow or use existing token."""
    # Check for force reset parameter
    if request.args.get('reset') == '1':
        print("Force reset requested")
        session.clear()
        try:
            TOKEN_FILE.unlink(missing_ok=True)
        except:
            pass

    # First check if we already have valid credentials in token file
    credentials = load_token()
    if credentials:
        try:
            # Validate by making API call
            service = build('gmail', 'v1', credentials=credentials)
            profile = service.users().getProfile(userId='me').execute()
            user_email = profile.get('emailAddress')

            if user_email and user_email != 'Unknown':
                # Preserve Yahoo modal flag before updating session
                show_yahoo_modal = session.get('show_yahoo_modal', False)
                creds_dict = credentials_to_dict(credentials)
                # Store in BOTH keys for consistency
                session['google_credentials'] = creds_dict
                session['credentials'] = creds_dict  # Legacy fallback
                session['user_email'] = user_email
                # Initialize provider session for Gmail
                init_provider_session(provider='gmail', email=user_email)
                print(f"Login: Restored session from token file for {user_email}")
                flash('Signed in with existing session!', 'success')
                # If user came from Yahoo login, redirect with modal trigger
                if show_yahoo_modal:
                    return redirect(url_for('dashboard', _external=True, _scheme='https', provider='yahoo'))
                return redirect(url_for('dashboard', _external=True, _scheme='https'))
        except Exception as e:
            print(f"Existing token invalid: {e}")
            # Token is invalid, clear everything
            session.clear()
            try:
                TOKEN_FILE.unlink(missing_ok=True)
            except:
                pass

    # Preserve flags that should survive the OAuth flow
    show_yahoo_modal = session.get('show_yahoo_modal', False)

    # Clear any stale session data before starting fresh OAuth
    session.clear()

    # Restore preserved flags
    if show_yahoo_modal:
        session['show_yahoo_modal'] = True

    # Start fresh OAuth flow
    flow = get_flow()

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state'] = state

    authorization_url, _ = flow.authorization_url(
        access_type='offline',
        state=state,
        prompt='consent'  # Force consent to get refresh token
    )

    return redirect(authorization_url)


@app.route('/callback')
def callback():
    """Handle OAuth callback from Google."""
    # Verify state token
    stored_state = session.get('oauth_state')
    received_state = request.args.get('state')

    if not stored_state or received_state != stored_state:
        print(f"State mismatch: stored={stored_state}, received={received_state}")
        # Clear session and force fresh login
        session.clear()
        flash('Session expired. Please try again.', 'error')
        return redirect(url_for('login', reset='1', _external=True, _scheme='https'))

    # Check for errors from Google
    if 'error' in request.args:
        error_msg = request.args.get('error')
        print(f"OAuth error from Google: {error_msg}")
        session.clear()
        flash(f"Authorization failed: {error_msg}", 'error')
        return redirect(url_for('index', _external=True, _scheme='https'))

    try:
        flow = get_flow()

        # Reconstruct the authorization response URL with https
        auth_response = request.url
        if auth_response.startswith('http://'):
            auth_response = 'https://' + auth_response[7:]

        flow.fetch_token(authorization_response=auth_response)

        credentials = flow.credentials
        creds_dict = credentials_to_dict(credentials)

        # Store in BOTH google_credentials (primary) and credentials (backward compat)
        # This ensures verify_provider_tokens() finds the credentials correctly
        session['google_credentials'] = creds_dict
        session['credentials'] = creds_dict  # Legacy fallback for get_credentials()
        print(f"Callback: Stored credentials in both 'google_credentials' and 'credentials' keys")

        # Save token to file for persistence
        save_token(credentials)

        # Get user email for display
        service = build('gmail', 'v1', credentials=credentials)
        profile = service.users().getProfile(userId='me').execute()
        user_email = profile.get('emailAddress')

        if not user_email:
            raise Exception("Could not retrieve user email")

        session['user_email'] = user_email
        print(f"Successfully authenticated: {user_email}")

        # Initialize provider session for Gmail
        init_provider_session(provider='gmail', email=user_email)

        flash('Successfully signed in!', 'success')

        # Check if user came from Yahoo login - redirect with Yahoo modal trigger
        if session.pop('show_yahoo_modal', False):
            return redirect(url_for('dashboard', _external=True, _scheme='https', provider='yahoo'))

        return redirect(url_for('dashboard', _external=True, _scheme='https'))

    except Exception as e:
        print(f"Callback error: {e}")
        # Clear everything on failure
        session.clear()
        try:
            TOKEN_FILE.unlink(missing_ok=True)
        except:
            pass
        flash(f'Authentication failed: {str(e)}', 'error')
        return redirect(url_for('index', _external=True, _scheme='https'))


@app.route('/logout')
def logout():
    """Clear session and logout completely."""
    # Clear all session data
    session.clear()

    # Also delete the token file to force re-authentication
    try:
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
            print("Token file deleted on logout")
    except Exception as e:
        print(f"Could not delete token file: {e}")

    flash('You have been signed out.', 'info')
    return redirect(url_for('index', _external=True, _scheme='https'))


@app.route('/force-logout')
def force_logout():
    """Force clear everything and redirect to login."""
    session.clear()
    try:
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
    except:
        pass
    return redirect(url_for('index', _external=True, _scheme='https'))


# =============================================================================
# Routes - Multi-Provider Authentication (Yahoo, Microsoft/Outlook)
# =============================================================================

@app.route('/login/yahoo')
def login_yahoo():
    """
    Yahoo Mail authentication redirect.

    IMPORTANT: Yahoo OAuth2 is NOT AVAILABLE for new applications.
    ============================================================

    As of 2026, Yahoo has RESTRICTED OAuth2 access for new client applications.
    This means:
    - We CANNOT register new OAuth2 applications with Yahoo
    - Yahoo's OAuth2 consent flow is not available to us
    - Any attempt to implement Yahoo OAuth2 would fail at the application
      registration stage

    THE CORRECT APPROACH: Yahoo App Password + IMAP
    -----------------------------------------------
    Instead of OAuth2, we use Yahoo's App Password feature which:
    1. Is officially supported by Yahoo for third-party applications
    2. Provides secure authentication without storing the user's main password
    3. Works with IMAP protocol for email access
    4. Can be revoked by users at any time from their Yahoo account settings

    How it works:
    - User generates an App Password in their Yahoo Account Security settings
    - User enters their Yahoo email + App Password in our modal
    - We use IMAP with SSL to authenticate and access their mailbox
    - The App Password is stored securely for the session

    This is the ONLY viable method for Yahoo Mail integration in 2026+.
    """
    # Set flag to indicate Yahoo modal should be shown
    session['show_yahoo_modal'] = True
    flash('Yahoo Mail requires an App Password for secure access. Please configure it below.', 'info')
    return redirect(url_for('dashboard', _external=True, _scheme='https', provider='yahoo'))


@app.route('/login/outlook')
@app.route('/login/microsoft')  # Alias for broader Microsoft branding
def login_outlook():
    """
    Initiate Microsoft OAuth2 flow for Outlook/Microsoft 365 accounts.

    Accessible via /login/outlook or /login/microsoft (alias).
    Covers Outlook.com, Hotmail, Live.com, and Microsoft 365 accounts.

    Uses Microsoft Graph API OAuth2 for secure authentication.
    """
    # Check if Microsoft OAuth is configured
    if not MICROSOFT_CLIENT_ID or not MICROSOFT_CLIENT_SECRET:
        flash('Outlook integration coming soon! Please check back later.', 'info')
        return redirect(url_for('index', _external=True, _scheme='https'))

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    session['oauth_state_microsoft'] = state

    # Build authorization URL with required parameters
    params = {
        'client_id': MICROSOFT_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': MICROSOFT_REDIRECT_URI,
        'scope': ' '.join(MICROSOFT_SCOPES),
        'response_mode': 'query',
        'state': state,
        'prompt': 'consent'  # Force consent to ensure we get refresh token
    }

    # Construct the full authorization URL
    from urllib.parse import urlencode
    authorization_url = f"{MICROSOFT_AUTHORIZE_URL}?{urlencode(params)}"

    return redirect(authorization_url)


@app.route('/callback/outlook')
def callback_outlook():
    """
    Handle OAuth callback from Microsoft.

    Exchanges the authorization code for access and refresh tokens,
    then retrieves user profile information.
    """
    # Check if Microsoft OAuth is configured
    if not MICROSOFT_CLIENT_ID or not MICROSOFT_CLIENT_SECRET:
        flash('Outlook integration is not configured.', 'error')
        return redirect(url_for('index', _external=True, _scheme='https'))

    # Verify state token for CSRF protection
    stored_state = session.get('oauth_state_microsoft')
    received_state = request.args.get('state')

    if not stored_state or received_state != stored_state:
        print(f"Microsoft OAuth state mismatch: stored={stored_state}, received={received_state}")
        session.pop('oauth_state_microsoft', None)
        flash('Session expired. Please try again.', 'error')
        return redirect(url_for('index', _external=True, _scheme='https'))

    # Check for errors from Microsoft
    if 'error' in request.args:
        error_msg = request.args.get('error_description', request.args.get('error', 'Unknown error'))
        print(f"Microsoft OAuth error: {error_msg}")
        session.pop('oauth_state_microsoft', None)
        flash(f"Authorization failed: {error_msg}", 'error')
        return redirect(url_for('index', _external=True, _scheme='https'))

    # Get authorization code
    code = request.args.get('code')
    if not code:
        flash('No authorization code received from Microsoft.', 'error')
        return redirect(url_for('index', _external=True, _scheme='https'))

    try:
        import requests

        # Exchange authorization code for tokens
        token_data = {
            'client_id': MICROSOFT_CLIENT_ID,
            'client_secret': MICROSOFT_CLIENT_SECRET,
            'code': code,
            'redirect_uri': MICROSOFT_REDIRECT_URI,
            'grant_type': 'authorization_code',
            'scope': ' '.join(MICROSOFT_SCOPES)
        }

        token_response = requests.post(
            MICROSOFT_TOKEN_URL,
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        if token_response.status_code != 200:
            error_data = token_response.json()
            error_msg = error_data.get('error_description', error_data.get('error', 'Token exchange failed'))
            print(f"Microsoft token exchange error: {error_msg}")
            flash(f'Authentication failed: {error_msg}', 'error')
            return redirect(url_for('index', _external=True, _scheme='https'))

        tokens = token_response.json()
        access_token = tokens.get('access_token')
        refresh_token = tokens.get('refresh_token')

        if not access_token:
            flash('No access token received from Microsoft.', 'error')
            return redirect(url_for('index', _external=True, _scheme='https'))

        # Get user profile from Microsoft Graph API
        profile_response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers={'Authorization': f'Bearer {access_token}'}
        )

        if profile_response.status_code != 200:
            print(f"Microsoft profile fetch error: {profile_response.text}")
            flash('Failed to retrieve user profile from Microsoft.', 'error')
            return redirect(url_for('index', _external=True, _scheme='https'))

        profile = profile_response.json()
        user_email = profile.get('mail') or profile.get('userPrincipalName')

        if not user_email:
            flash('Could not retrieve email address from Microsoft account.', 'error')
            return redirect(url_for('index', _external=True, _scheme='https'))

        # Extract user's display name from Microsoft Graph profile
        # Microsoft Graph /me returns: displayName, givenName, surname, etc.
        # Priority: displayName > givenName > first part of email
        user_display_name = (
            profile.get('displayName') or
            profile.get('givenName') or
            user_email.split('@')[0]
        )

        # Store Microsoft credentials in session (use 'token' key for consistency with unified auth)
        session['microsoft_credentials'] = {
            'token': access_token,  # Use 'token' for consistency with unified auth
            'access_token': access_token,  # Keep for backward compatibility
            'refresh_token': refresh_token,
            'token_type': tokens.get('token_type', 'Bearer'),
            'expires_in': tokens.get('expires_in'),
            'scope': tokens.get('scope')
        }
        session['user_email'] = user_email
        session['user_display_name'] = user_display_name
        session['auth_provider'] = 'microsoft'

        # Initialize provider session for Microsoft (enables multi-provider support)
        init_provider_session(provider='microsoft', email=user_email)
        session.modified = True
        print(f"Microsoft session initialized: email={user_email}, connected_providers={session.get('connected_providers')}")

        # Clear the state token
        session.pop('oauth_state_microsoft', None)

        print(f"Successfully authenticated Microsoft user: {user_email} ({user_display_name})")
        flash(f'Welcome, {user_display_name}! Successfully signed in with Microsoft.', 'success')
        return redirect(url_for('dashboard', _external=True, _scheme='https'))

    except requests.RequestException as e:
        print(f"Microsoft OAuth request error: {e}")
        flash(f'Network error during authentication: {str(e)}', 'error')
        return redirect(url_for('index', _external=True, _scheme='https'))
    except Exception as e:
        print(f"Microsoft OAuth callback error: {e}")
        session.pop('oauth_state_microsoft', None)
        flash(f'Authentication failed: {str(e)}', 'error')
        return redirect(url_for('index', _external=True, _scheme='https'))


# =============================================================================
# Routes - Unified Auth (Authlib-based Sovereign Entry)
# =============================================================================

@app.route('/auth/login')
@app.route('/auth/login/<provider>')
def auth_login(provider='google'):
    """
    Unified OAuth2 login endpoint for all providers.

    Supports: google, yahoo, microsoft
    Dynamic redirect_uri generation for dev/prod environments.
    """
    from auth_providers import (
        PROVIDER_CONFIGS, is_provider_configured,
        get_redirect_uri, get_base_url
    )

    # Validate provider
    if provider not in PROVIDER_CONFIGS:
        flash(f'Unknown provider: {provider}', 'error')
        return redirect(url_for('login_page', _external=True, _scheme='https'))

    config = PROVIDER_CONFIGS[provider]

    # Check if provider is configured
    if not is_provider_configured(provider):
        flash(f'{config["display_name"]} integration coming soon!', 'info')
        return redirect(url_for('login_page', _external=True, _scheme='https'))

    # Generate state token for CSRF protection
    state = secrets.token_urlsafe(32)
    session[f'oauth_state_{provider}'] = state

    # Build authorization URL
    redirect_uri = get_redirect_uri(provider)
    params = {
        'client_id': config['client_id'],
        'response_type': 'code',
        'redirect_uri': redirect_uri,
        'scope': ' '.join(config['scopes']),
        'state': state,
    }

    # Google-specific params
    if provider == 'google':
        params['access_type'] = 'offline'
        params['prompt'] = 'consent'

    # Microsoft-specific params
    if provider == 'microsoft':
        params['response_mode'] = 'query'
        params['prompt'] = 'consent'

    from urllib.parse import urlencode
    authorization_url = f"{config['authorize_url']}?{urlencode(params)}"

    print(f"Initiating {provider} OAuth: redirect_uri={redirect_uri}")
    return redirect(authorization_url)


@app.route('/auth/yahoo')  # Yahoo uses /auth/yahoo directly as callback
@app.route('/auth/<provider>/callback')
def auth_callback(provider='yahoo'):
    """
    Unified OAuth2 callback handler for all providers.

    Handles provider-specific user info parsing and token storage.
    """
    import requests as http_requests
    from auth_providers import (
        PROVIDER_CONFIGS, parse_userinfo, store_provider_session,
        encrypt_tokens, get_redirect_uri
    )

    if provider not in PROVIDER_CONFIGS:
        flash('Unknown provider', 'error')
        return redirect(url_for('login_page', _external=True, _scheme='https'))

    config = PROVIDER_CONFIGS[provider]

    # Verify state token
    stored_state = session.get(f'oauth_state_{provider}')
    received_state = request.args.get('state')

    if not stored_state or received_state != stored_state:
        print(f"{provider} OAuth state mismatch")
        session.pop(f'oauth_state_{provider}', None)
        flash('Session expired. Please try again.', 'error')
        return redirect(url_for('login_page', _external=True, _scheme='https'))

    # Check for errors
    if 'error' in request.args:
        error_msg = request.args.get('error_description', request.args.get('error'))
        print(f"{provider} OAuth error: {error_msg}")
        flash(f'Authorization failed: {error_msg}', 'error')
        return redirect(url_for('login_page', _external=True, _scheme='https'))

    # Get authorization code
    code = request.args.get('code')
    if not code:
        flash('No authorization code received.', 'error')
        return redirect(url_for('login_page', _external=True, _scheme='https'))

    try:
        # Exchange code for tokens
        redirect_uri = get_redirect_uri(provider)
        token_data = {
            'client_id': config['client_id'],
            'client_secret': config['client_secret'],
            'code': code,
            'redirect_uri': redirect_uri,
            'grant_type': 'authorization_code',
        }

        token_response = http_requests.post(
            config['token_url'],
            data=token_data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )

        if token_response.status_code != 200:
            error_data = token_response.json()
            error_msg = error_data.get('error_description', error_data.get('error', 'Token exchange failed'))
            raise Exception(error_msg)

        tokens = token_response.json()
        access_token = tokens.get('access_token')

        if not access_token:
            raise Exception('No access token received')

        # Fetch user info
        print(f"Fetching userinfo from: {config['userinfo_url']}")
        userinfo_response = http_requests.get(
            config['userinfo_url'],
            headers={'Authorization': f'Bearer {access_token}'}
        )

        if userinfo_response.status_code != 200:
            error_detail = userinfo_response.text
            print(f"Userinfo fetch failed ({userinfo_response.status_code}): {error_detail}")
            raise Exception(f'Failed to get user info (HTTP {userinfo_response.status_code}): {error_detail[:200]}')

        userinfo = userinfo_response.json()

        # Parse provider-specific userinfo
        parsed = parse_userinfo(provider, userinfo)
        user_email = parsed.get('email')
        display_name = parsed.get('display_name', user_email.split('@')[0] if user_email else 'User')

        # Store in session
        store_provider_session(provider, userinfo, tokens)

        # Set core session variables for ALL providers
        session['user_email'] = user_email
        session['user_display_name'] = display_name

        # Provider-specific credential storage (ISOLATED - no cross-contamination)
        if provider == 'google':
            google_creds = {
                'token': access_token,
                'refresh_token': tokens.get('refresh_token'),
                'token_uri': config['token_url'],
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'scopes': config['scopes']
            }
            # Store in google_credentials (primary) and credentials (backward compat)
            session['google_credentials'] = google_creds
            session['credentials'] = google_creds  # For legacy Gmail API code
            init_provider_session(provider='gmail', email=user_email)
            print(f"Google session initialized: email={user_email}")
            session.modified = True

        elif provider == 'microsoft':
            # Store ONLY in microsoft_credentials - DO NOT overwrite session['credentials']
            session['microsoft_credentials'] = {
                'token': access_token,
                'refresh_token': tokens.get('refresh_token'),
                'token_uri': config['token_url'],
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'scopes': config['scopes']
            }
            # DO NOT overwrite session['credentials'] - that's for Google
            init_provider_session(provider='microsoft', email=user_email)
            print(f"Microsoft session initialized: email={user_email}, connected_providers={session.get('connected_providers')}")
            session.modified = True

        elif provider == 'yahoo':
            # Store ONLY in yahoo_credentials - DO NOT overwrite session['credentials']
            session['yahoo_credentials'] = {
                'token': access_token,
                'refresh_token': tokens.get('refresh_token'),
                'token_uri': config['token_url'],
                'client_id': config['client_id'],
                'client_secret': config['client_secret'],
                'scopes': config['scopes']
            }
            # DO NOT overwrite session['credentials'] - that's for Google
            session['yahoo_email'] = user_email  # Store Yahoo email separately
            init_provider_session(provider='yahoo', email=user_email)
            print(f"Yahoo session initialized: email={user_email}, connected_providers={session.get('connected_providers')}")
            session.modified = True

        # Store encrypted tokens in database
        encrypted = encrypt_tokens(tokens)
        try:
            db.update_user_provider_tokens(
                email=user_email,
                provider=provider,
                access_token=encrypted.get('access_token_encrypted'),
                refresh_token=encrypted.get('refresh_token_encrypted'),
                expires_at=tokens.get('expires_at')
            )
            db.update_user_display_name(user_email, display_name)
        except Exception as db_err:
            print(f"Warning: Could not store tokens in DB: {db_err}")

        # Clear state token
        session.pop(f'oauth_state_{provider}', None)

        print(f"Successfully authenticated {provider} user: {user_email} ({display_name})")
        flash(f'Welcome, {display_name}!', 'success')
        return redirect(url_for('dashboard', _external=True, _scheme='https'))

    except Exception as e:
        print(f"{provider} OAuth callback error: {e}")
        session.pop(f'oauth_state_{provider}', None)
        flash(f'Authentication failed: {str(e)}', 'error')
        return redirect(url_for('login_page', _external=True, _scheme='https'))


@app.route('/login-page')
def login_page():
    """Render the Sovereign Entry login page."""
    return render_template('login.html')


# =============================================================================
# Routes - Dashboard & Gmail Operations
# =============================================================================

@app.route('/dashboard')
def dashboard():
    """Main dashboard with inbox stats."""
    # === CONNECTION CHECK: Verify OAuth tokens on every page load ===
    token_status = verify_provider_tokens()
    print(f"Dashboard: Token status: {token_status}")
    print(f"Dashboard: Session keys: {list(session.keys())}")
    print(f"Dashboard: connected_providers: {session.get('connected_providers')}")

    # If no valid credentials, clear stale session and redirect to login
    if token_status['should_reauth'] or not token_status['valid_providers']:
        print(f"Dashboard: Token verification failed. Valid: {token_status['valid_providers']}, Invalid: {token_status['invalid_providers']}")
        # Clear everything including stale provider data
        clear_auth(clear_providers=True)
        flash('Your session has expired. Please sign in again.', 'info')
        return redirect(url_for('login_page', _external=True, _scheme='https'))

    # Sync connected_providers with actual token state
    sync_connected_providers()

    # Handle provider switch from URL parameter FIRST (before fetching stats)
    requested_provider = request.args.get('provider')
    if requested_provider:
        if set_primary_provider(requested_provider):
            print(f"Dashboard: Switched to provider: {requested_provider}")
        else:
            print(f"Dashboard: Failed to switch to provider: {requested_provider}")

    # Get current primary provider and connected providers
    primary_provider = get_primary_provider()
    connected_providers = get_connected_providers()
    print(f"Dashboard: Current primary_provider = {primary_provider}")

    # Get email for the current primary provider (not the session default)
    user_email = session.get('user_email')  # Fallback
    for provider_info in connected_providers:
        provider_name = provider_info.get('name', '')
        # Match provider name (handle google/gmail alias)
        if provider_name == primary_provider or \
           (provider_name in ['google', 'gmail'] and primary_provider in ['google', 'gmail']):
            user_email = provider_info.get('email', user_email)
            break
    print(f"Dashboard: Displaying email for {primary_provider}: {user_email}")

    # If user_email is missing or "Unknown", force re-authentication
    if not user_email or user_email == 'Unknown':
        print("Dashboard: Missing user_email, forcing re-auth")
        clear_auth(clear_providers=True)
        flash('Session expired. Please sign in again.', 'info')
        return redirect(url_for('login_page', _external=True, _scheme='https'))

    # Fetch inbox stats based on current provider
    stats = {'total': 0, 'unread': 0, 'storage_mb': 0, 'storage_percent': 0, 'provider': primary_provider}

    if primary_provider in ['gmail', 'google']:
        # Gmail API stats
        try:
            service = get_gmail_service()
            if service:
                profile = service.users().getProfile(userId='me').execute()
                stats['total'] = int(profile.get('messagesTotal', 0))

                unread_result = service.users().messages().list(
                    userId='me', q='is:unread', maxResults=1
                ).execute()
                stats['unread'] = unread_result.get('resultSizeEstimate', 0)

                stats['storage_mb'] = round(stats['total'] * 0.075, 1)
                stats['storage_percent'] = min(round((stats['storage_mb'] / 15000) * 100, 1), 100)
        except Exception as e:
            print(f"Error fetching Gmail stats: {e}")

    elif primary_provider == 'microsoft':
        # Microsoft Graph API stats with folder breakdown
        try:
            ms_creds = session.get('microsoft_credentials', {})
            if ms_creds.get('token'):
                import requests as http_requests
                headers = {'Authorization': f'Bearer {ms_creds["token"]}'}

                # Fetch all main folders: inbox, junkemail, sentitems
                folders = {
                    'inbox': 'inbox',
                    'junk': 'junkemail',
                    'sent': 'sentitems'
                }
                folder_counts = {}
                total_emails = 0
                total_unread = 0

                for name, folder_id in folders.items():
                    try:
                        response = http_requests.get(
                            f'https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}',
                            headers=headers
                        )
                        if response.status_code == 200:
                            data = response.json()
                            folder_counts[name] = {
                                'total': data.get('totalItemCount', 0),
                                'unread': data.get('unreadItemCount', 0)
                            }
                            total_emails += folder_counts[name]['total']
                            total_unread += folder_counts[name]['unread']
                        else:
                            print(f"Microsoft Graph {name} folder error: {response.status_code}")
                            folder_counts[name] = {'total': 0, 'unread': 0}
                    except Exception as folder_err:
                        print(f"Error fetching {name} folder: {folder_err}")
                        folder_counts[name] = {'total': 0, 'unread': 0}

                # Aggregate stats
                stats['total'] = total_emails
                stats['unread'] = total_unread
                stats['storage_mb'] = round(total_emails * 0.05, 1)  # Estimate
                stats['storage_percent'] = min(round((stats['storage_mb'] / 15000) * 100, 1), 100)
                stats['folders'] = folder_counts  # Breakdown by folder
                print(f"Microsoft folders: inbox={folder_counts.get('inbox', {}).get('total', 0)}, "
                      f"junk={folder_counts.get('junk', {}).get('total', 0)}, "
                      f"sent={folder_counts.get('sent', {}).get('total', 0)}")
        except Exception as e:
            print(f"Error fetching Microsoft stats: {e}")

    elif primary_provider == 'yahoo':
        # Yahoo stats (placeholder - would require IMAP connection)
        stats['total'] = 0
        stats['unread'] = 0
        stats['storage_mb'] = 0
        stats['storage_percent'] = 0

    # Get user tier and stats from database
    user = db.get_or_create_user(user_email)
    user_tier = user.get('tier', 'free')

    # Check if purge has expired
    if user_tier == 'purge':
        db.check_purge_expiration(user_email)
        user = db.get_user_by_email(user_email)
        user_tier = user.get('tier', 'free')

    remaining_deletes = db.get_remaining_deletes(user_email)
    total_cleaned = user.get('total_emails_cleaned', 0)
    purge_expires_at = user.get('purge_expires_at') if user_tier == 'purge' else None
    purge_days_remaining = db.get_purge_days_remaining(user_email) if user_tier == 'purge' else None

    # Get user's display name for personalized greetings
    user_display_name = get_user_display_name()

    return render_template(
        'dashboard.html',
        user_email=user_email,
        user_display_name=user_display_name,
        stats=stats,
        user_tier=user_tier,
        remaining_deletes=remaining_deletes,
        total_cleaned=total_cleaned,
        purge_expires_at=purge_expires_at,
        purge_days_remaining=purge_days_remaining,
        primary_provider=primary_provider,
        connected_providers=connected_providers
    )


@app.route('/api/stats')
@login_required
def api_stats():
    """
    API endpoint for inbox statistics.

    Accepts ?provider= query parameter to specify which provider to fetch stats from.
    Priority: URL param > session primary_provider > default (gmail)
    """
    import requests as http_requests

    # Get provider from query param (highest priority) or session
    provider = request.args.get('provider') or get_primary_provider()

    stats = {
        'total': 0,
        'unread': 0,
        'storage_mb': 0,
        'storage_percent': 0,
        'provider': provider
    }

    try:
        if provider in ['gmail', 'google']:
            # Gmail API stats
            service = get_gmail_service()
            if not service:
                return jsonify({'error': 'Gmail not authenticated', 'provider': provider}), 401

            profile = service.users().getProfile(userId='me').execute()
            stats['total'] = int(profile.get('messagesTotal', 0))

            unread_result = service.users().messages().list(
                userId='me', q='is:unread', maxResults=1
            ).execute()
            stats['unread'] = unread_result.get('resultSizeEstimate', 0)

            stats['storage_mb'] = round(stats['total'] * 0.075, 1)
            stats['storage_percent'] = min(round((stats['storage_mb'] / 15000) * 100, 1), 100)

        elif provider == 'microsoft':
            # Microsoft Graph API stats with folder breakdown
            ms_creds = session.get('microsoft_credentials', {})
            if not ms_creds.get('token'):
                return jsonify({'error': 'Microsoft not authenticated', 'provider': provider}), 401

            headers = {'Authorization': f'Bearer {ms_creds["token"]}'}

            # Fetch all main folders: inbox, junkemail, sentitems
            folders = {'inbox': 'inbox', 'junk': 'junkemail', 'sent': 'sentitems'}
            folder_counts = {}
            total_emails = 0
            total_unread = 0

            for name, folder_id in folders.items():
                try:
                    response = http_requests.get(
                        f'https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}',
                        headers=headers,
                        timeout=10
                    )
                    if response.status_code == 200:
                        data = response.json()
                        folder_counts[name] = {
                            'total': data.get('totalItemCount', 0),
                            'unread': data.get('unreadItemCount', 0)
                        }
                        total_emails += folder_counts[name]['total']
                        total_unread += folder_counts[name]['unread']
                    elif response.status_code == 401:
                        return jsonify({'error': 'Microsoft token expired', 'provider': provider}), 401
                    else:
                        print(f"Microsoft Graph {name} folder error: {response.status_code}")
                        folder_counts[name] = {'total': 0, 'unread': 0}
                except Exception as folder_err:
                    print(f"Error fetching {name}: {folder_err}")
                    folder_counts[name] = {'total': 0, 'unread': 0}

            stats['total'] = total_emails
            stats['unread'] = total_unread
            stats['storage_mb'] = round(total_emails * 0.05, 1)  # Estimate ~50KB per email
            stats['storage_percent'] = min(round((stats['storage_mb'] / 15000) * 100, 1), 100)
            stats['folders'] = folder_counts

        elif provider == 'yahoo':
            # Yahoo stats (placeholder - IMAP integration)
            yahoo_creds = session.get('yahoo_credentials', {})
            if not yahoo_creds.get('token'):
                return jsonify({'error': 'Yahoo not authenticated', 'provider': provider}), 401
            # Return zeros for now until IMAP is implemented
            stats['total'] = 0
            stats['unread'] = 0

        else:
            return jsonify({'error': f'Unknown provider: {provider}'}), 400

        return jsonify(stats)

    except Exception as e:
        print(f"Error fetching stats for {provider}: {e}")
        return jsonify({'error': str(e), 'provider': provider}), 500


@app.route('/api/switch-provider', methods=['POST'])
@login_required
def api_switch_provider():
    """API endpoint to switch the primary provider."""
    data = request.get_json()
    provider = data.get('provider')

    if not provider:
        return jsonify({'error': 'Provider name required'}), 400

    connected = get_connected_providers()
    provider_names = [p['name'] for p in connected]

    if provider not in provider_names:
        return jsonify({
            'error': f'Provider {provider} is not connected',
            'connected_providers': provider_names
        }), 400

    if set_primary_provider(provider):
        return jsonify({
            'success': True,
            'primary_provider': provider,
            'connected_providers': connected
        })
    else:
        return jsonify({'error': 'Failed to switch provider'}), 500


@app.route('/api/providers')
@login_required
def api_providers():
    """API endpoint to get provider information."""
    return jsonify({
        'primary_provider': get_primary_provider(),
        'connected_providers': get_connected_providers()
    })


@app.route('/api/check_updates')
@login_required
def api_check_updates():
    """
    API endpoint for polling - returns total count and latest message ID.

    Provider-aware: Accepts ?provider= query parameter to lock to specific provider.
    This prevents "Ghost Refresh" where Gmail stats overwrite Microsoft stats.
    """
    import requests as http_requests
    import time

    # Get provider from query param (highest priority) or session
    provider = request.args.get('provider') or get_primary_provider()

    try:
        if provider in ['gmail', 'google']:
            # Gmail API
            service = get_gmail_service()
            if not service:
                return jsonify({'error': 'Gmail not authenticated', 'provider': provider}), 401

            profile = service.users().getProfile(userId='me').execute()
            total = int(profile.get('messagesTotal', 0))

            unread_result = service.users().messages().list(
                userId='me', q='is:unread', maxResults=1
            ).execute()
            unread = unread_result.get('resultSizeEstimate', 0)

            latest_result = service.users().messages().list(
                userId='me', maxResults=1
            ).execute()
            messages = latest_result.get('messages', [])
            latest_id = messages[0]['id'] if messages else None

            return jsonify({
                'total': total,
                'unread': unread,
                'latest_id': latest_id,
                'provider': provider,
                'timestamp': int(time.time())
            })

        elif provider == 'microsoft':
            # Microsoft Graph API with folder breakdown
            ms_creds = session.get('microsoft_credentials', {})
            if not ms_creds.get('token'):
                return jsonify({'error': 'Microsoft not authenticated', 'provider': provider}), 401

            headers = {'Authorization': f'Bearer {ms_creds["token"]}'}

            # Fetch all main folders: inbox, junkemail, sentitems
            folders = {'inbox': 'inbox', 'junk': 'junkemail', 'sent': 'sentitems'}
            folder_counts = {}
            total_emails = 0
            total_unread = 0

            for name, folder_id in folders.items():
                try:
                    response = http_requests.get(
                        f'https://graph.microsoft.com/v1.0/me/mailFolders/{folder_id}',
                        headers=headers,
                        timeout=10
                    )
                    if response.status_code == 200:
                        data = response.json()
                        folder_counts[name] = {
                            'total': data.get('totalItemCount', 0),
                            'unread': data.get('unreadItemCount', 0)
                        }
                        total_emails += folder_counts[name]['total']
                        total_unread += folder_counts[name]['unread']
                    elif response.status_code == 401:
                        return jsonify({'error': 'Microsoft token expired', 'provider': provider}), 401
                    else:
                        folder_counts[name] = {'total': 0, 'unread': 0}
                except Exception as folder_err:
                    print(f"Error fetching {name}: {folder_err}")
                    folder_counts[name] = {'total': 0, 'unread': 0}

            return jsonify({
                'total': total_emails,
                'unread': total_unread,
                'folders': folder_counts,
                'latest_id': None,
                'provider': provider,
                'timestamp': int(time.time())
            })

        elif provider == 'yahoo':
            # Yahoo - placeholder until IMAP integration
            yahoo_creds = session.get('yahoo_credentials', {})
            if not yahoo_creds.get('token'):
                return jsonify({'error': 'Yahoo not authenticated', 'provider': provider}), 401

            return jsonify({
                'total': 0,
                'unread': 0,
                'latest_id': None,
                'provider': provider,
                'timestamp': int(time.time())
            })

        else:
            return jsonify({'error': f'Unknown provider: {provider}'}), 400

    except Exception as e:
        print(f"Error in check_updates for {provider}: {e}")
        return jsonify({'error': str(e), 'provider': provider}), 500


@app.route('/api/filter-counts')
@login_required
def api_filter_counts():
    """GOLD MASTER v4.0 - HARD SYNC WITH GMAIL LABEL IDs"""
    from datetime import datetime
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    print(f"\n{'='*70}")
    print(f"[SYNC v4.0] API CALLED AT {ts}")
    print(f"{'='*70}")

    service = get_gmail_service()
    if not service:
        print(f"[SYNC] ERROR: Not authenticated")
        return jsonify({'error': 'Not authenticated'}), 401

    counts = {}

    # EXACT Gmail System Label IDs - using labels().get() for accuracy
    label_map = {
        'inbox': 'INBOX',
        'starred': 'STARRED',
        'sent': 'SENT',
        'drafts': 'DRAFT',
        'spam': 'SPAM',
        'updates': 'CATEGORY_UPDATES',
        'promotions': 'CATEGORY_PROMOTIONS',
        'purchases': 'CATEGORY_PURCHASES',
    }

    try:
        # Fetch ALL label counts using labels().get() - DIRECT FROM GMAIL
        for name, label_id in label_map.items():
            try:
                label_info = service.users().labels().get(
                    userId='me',
                    id=label_id
                ).execute()
                count = label_info.get('messagesTotal', 0)
                counts[name] = count
                print(f"[SYNC] {name.upper()} Label Count: {count} (ID: {label_id})")
            except Exception as e:
                counts[name] = 0
                print(f"[SYNC] {name.upper()} ERROR: {str(e)}")

        # Unread requires a query (not a label)
        try:
            unread_result = service.users().messages().list(
                userId='me',
                q='is:unread',
                maxResults=1
            ).execute()
            counts['unread'] = unread_result.get('resultSizeEstimate', 0)
            print(f"[SYNC] UNREAD Label Count: {counts['unread']} (query: is:unread)")
        except Exception as e:
            counts['unread'] = 0
            print(f"[SYNC] UNREAD ERROR: {str(e)}")

        print(f"[SYNC] {'='*50}")
        print(f"[SYNC] FINAL COUNTS: {counts}")
        print(f"[SYNC] VERSION: v4.0-HARDSYNC")
        print(f"[SYNC] {'='*50}\n")

        return jsonify({
            'counts': counts,
            'timestamp': ts,
            'version': 'v4.0-HARDSYNC'
        })

    except Exception as e:
        print(f"[SYNC] FATAL ERROR: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/data-truth')
@login_required
def api_data_truth():
    """
    DATA TRUTH ENGINE - Compare Gmail's thread count vs our message count.
    Returns both numbers for transparency display.
    """
    from datetime import datetime
    ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    query = request.args.get('q', 'in:inbox')

    print(f"\n{'='*70}")
    print(f"[DATA-TRUTH] Query: {query} at {ts}")
    print(f"{'='*70}")

    service = get_gmail_service()
    if not service:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        # Get THREAD count (what Gmail shows users)
        thread_result = service.users().threads().list(
            userId='me',
            q=query,
            maxResults=1
        ).execute()
        thread_count = thread_result.get('resultSizeEstimate', 0)

        # Get MESSAGE count (what we actually delete - the real data)
        message_result = service.users().messages().list(
            userId='me',
            q=query,
            maxResults=1
        ).execute()
        message_count = message_result.get('resultSizeEstimate', 0)

        print(f"[DATA-TRUTH] Gmail Threads: {thread_count}")
        print(f"[DATA-TRUTH] Actual Messages: {message_count}")
        print(f"[DATA-TRUTH] Hidden Data Ratio: {message_count / thread_count:.1f}x" if thread_count > 0 else "[DATA-TRUTH] No threads")

        return jsonify({
            'query': query,
            'thread_count': thread_count,
            'message_count': message_count,
            'ratio': round(message_count / thread_count, 2) if thread_count > 0 else 0,
            'timestamp': ts,
            'version': 'DATA-TRUTH-v1'
        })

    except Exception as e:
        print(f"[DATA-TRUTH] ERROR: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/suggestion', methods=['POST'])
@login_required
def submit_suggestion():
    """Submit a user suggestion/feedback."""
    user_email = session.get('user_email')
    data = request.get_json()
    suggestion_text = data.get('suggestion', '').strip()

    if not suggestion_text:
        return jsonify({'error': 'Suggestion cannot be empty'}), 400

    if len(suggestion_text) > 2000:
        return jsonify({'error': 'Suggestion too long (max 2000 characters)'}), 400

    try:
        result = db.add_suggestion(user_email, suggestion_text)

        # Log for real-time notification (will appear in server logs)
        print(f"\n{'='*60}")
        print(f"NEW SUGGESTION from {user_email}")
        print(f"{'='*60}")
        print(f"{suggestion_text}")
        print(f"{'='*60}\n")

        return jsonify({
            'success': True,
            'message': 'Thank you for your feedback!',
            'suggestion_id': result['id']
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/suggestions')
@login_required
def admin_suggestions():
    """Admin page to view all suggestions (admin only)."""
    user_email = session.get('user_email')

    # Only allow admin access
    if user_email not in db.ADMIN_EMAILS:
        return jsonify({'error': 'Access denied'}), 403

    suggestions = db.get_all_suggestions()
    new_count = db.get_suggestion_count()

    return render_template(
        'admin_suggestions.html',
        suggestions=suggestions,
        new_count=new_count
    )


@app.route('/scan', methods=['POST'])
@login_required
def scan():
    """Scan inbox with Gmail query using parallel batch processing."""
    query = request.form.get('query', '').strip()
    exclude_ids = request.form.getlist('exclude_ids')  # IDs to exclude (safelist)

    if not query:
        return jsonify({'error': 'Query is required'}), 400

    service = get_gmail_service()
    if not service:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        # DATA TRUTH: Get thread count first (what Gmail shows users)
        thread_result = service.users().threads().list(
            userId='me',
            q=query,
            maxResults=1
        ).execute()
        thread_count = thread_result.get('resultSizeEstimate', 0)

        # Fetch messages matching query (what we actually process)
        messages = []
        page_token = None
        max_results = 500  # Limit for safety
        total_estimate = 0  # Gmail's total message estimate

        # Parallel page fetching for large result sets
        def fetch_page(token=None):
            return service.users().messages().list(
                userId='me',
                q=query,
                pageToken=token,
                maxResults=100
            ).execute()

        first_fetch = True
        while len(messages) < max_results:
            result = fetch_page(page_token)

            # Capture total estimate from first API call (Gmail's count)
            if first_fetch:
                total_estimate = result.get('resultSizeEstimate', 0)
                first_fetch = False

            batch_messages = result.get('messages', [])
            if not batch_messages:
                break

            # Filter out excluded IDs (safelist)
            if exclude_ids:
                exclude_set = set(exclude_ids)
                batch_messages = [m for m in batch_messages if m['id'] not in exclude_set]

            messages.extend(batch_messages)

            page_token = result.get('nextPageToken')
            if not page_token:
                break

        if not messages:
            return jsonify({
                'count': 0,
                'total_estimate': total_estimate,
                'thread_count': thread_count,
                'senders': {},
                'message': 'No messages found matching your query.'
            })

        # Sender aggregation
        senders = {}

        def process_batch(batch_ids):
            """Process a batch of message IDs and return sender data."""
            local_senders = {}
            batch = service.new_batch_http_request()

            def make_callback(msg_id):
                def callback(request_id, response, exception):
                    if exception:
                        return
                    headers = response.get('payload', {}).get('headers', [])
                    sender = '(unknown)'
                    subject = '(No Subject)'
                    date = ''
                    for h in headers:
                        name_lower = h['name'].lower()
                        if name_lower == 'from':
                            sender = h['value']
                            if '<' in sender and '>' in sender:
                                sender = sender.split('<')[1].split('>')[0]
                            sender = sender.lower().strip()
                        elif name_lower == 'subject':
                            subject = h['value'] or '(No Subject)'
                        elif name_lower == 'date':
                            date = h['value']

                    # Extract labelIds for badge display
                    label_ids = response.get('labelIds', [])

                    if sender not in local_senders:
                        local_senders[sender] = {'count': 0, 'ids': [], 'messages': []}
                    local_senders[sender]['count'] += 1
                    local_senders[sender]['ids'].append(msg_id)
                    local_senders[sender]['messages'].append({
                        'id': msg_id,
                        'subject': subject[:100],
                        'date': date,
                        'labels': label_ids
                    })
                return callback

            for msg_id in batch_ids:
                req = service.users().messages().get(
                    userId='me',
                    id=msg_id,
                    format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                )
                batch.add(req, callback=make_callback(msg_id))

            batch.execute()
            return local_senders

        # Process batches sequentially (thread-safe with Google API)
        batch_size = 50
        batches = [
            [m['id'] for m in messages[i:i+batch_size]]
            for i in range(0, len(messages), batch_size)
        ]

        for batch_ids in batches:
            local_senders = process_batch(batch_ids)
            # Merge results
            for sender, data in local_senders.items():
                if sender not in senders:
                    senders[sender] = {'count': 0, 'ids': [], 'messages': []}
                senders[sender]['count'] += data['count']
                senders[sender]['ids'].extend(data['ids'])
                senders[sender]['messages'].extend(data['messages'])

        # Sort by count descending
        sorted_senders = dict(sorted(
            senders.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        ))

        # DATA TRUTH: Calculate hidden data ratio
        hidden_ratio = round(len(messages) / thread_count, 1) if thread_count > 0 else 0

        return jsonify({
            'count': len(messages),
            'total_estimate': total_estimate,
            'thread_count': thread_count,
            'hidden_ratio': hidden_ratio,
            'senders': {k: v['count'] for k, v in sorted_senders.items()},
            'sender_data': sorted_senders
        })

    except HttpError as e:
        return jsonify({'error': f'Gmail API error: {e.reason}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/message/<msg_id>')
@login_required
def get_message(msg_id):
    """Fetch a single email's full content for preview."""
    service = get_gmail_service()
    if not service:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        # Fetch full message
        message = service.users().messages().get(
            userId='me',
            id=msg_id,
            format='full'
        ).execute()

        # Extract headers
        headers = message.get('payload', {}).get('headers', [])
        header_dict = {}
        for h in headers:
            name = h['name'].lower()
            if name in ['from', 'to', 'subject', 'date']:
                header_dict[name] = h['value']

        # Extract body content
        def get_body_content(payload):
            """Recursively extract body content from message payload."""
            body_html = None
            body_text = None

            # Check if this part has a body
            if 'body' in payload and payload['body'].get('data'):
                import base64
                data = payload['body']['data']
                decoded = base64.urlsafe_b64decode(data).decode('utf-8', errors='replace')
                mime_type = payload.get('mimeType', '')

                if 'text/html' in mime_type:
                    body_html = decoded
                elif 'text/plain' in mime_type:
                    body_text = decoded

            # Check parts (for multipart messages)
            if 'parts' in payload:
                for part in payload['parts']:
                    mime_type = part.get('mimeType', '')

                    if mime_type == 'text/html' and not body_html:
                        if 'body' in part and part['body'].get('data'):
                            import base64
                            body_html = base64.urlsafe_b64decode(
                                part['body']['data']
                            ).decode('utf-8', errors='replace')

                    elif mime_type == 'text/plain' and not body_text:
                        if 'body' in part and part['body'].get('data'):
                            import base64
                            body_text = base64.urlsafe_b64decode(
                                part['body']['data']
                            ).decode('utf-8', errors='replace')

                    # Recursively check nested parts (multipart/alternative, etc.)
                    elif 'parts' in part:
                        nested_html, nested_text = get_body_content(part)
                        if nested_html and not body_html:
                            body_html = nested_html
                        if nested_text and not body_text:
                            body_text = nested_text

            return body_html, body_text

        payload = message.get('payload', {})
        body_html, body_text = get_body_content(payload)

        # Prefer HTML, fall back to plain text
        body = body_html if body_html else body_text
        body_type = 'html' if body_html else 'text'

        # If still no body, check top-level
        if not body and payload.get('body', {}).get('data'):
            import base64
            body = base64.urlsafe_b64decode(
                payload['body']['data']
            ).decode('utf-8', errors='replace')
            body_type = 'html' if 'text/html' in payload.get('mimeType', '') else 'text'

        return jsonify({
            'id': msg_id,
            'from': header_dict.get('from', 'Unknown'),
            'to': header_dict.get('to', ''),
            'subject': header_dict.get('subject', '(No Subject)'),
            'date': header_dict.get('date', ''),
            'body': body or '(No content)',
            'body_type': body_type
        })

    except HttpError as e:
        return jsonify({'error': f'Gmail API error: {e.reason}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/trash', methods=['POST'])
@login_required
def trash():
    """Move selected emails to trash (or simulate in dry_run mode)."""
    data = request.get_json()
    message_ids = data.get('message_ids', [])
    dry_run = data.get('dry_run', True)  # Default to safe mode
    query_used = data.get('query', '')  # Optional: track what query was used

    user_email = session.get('user_email')

    if not message_ids:
        return jsonify({'error': 'No messages selected'}), 400

    if len(message_ids) > 1000:
        return jsonify({'error': 'Too many messages (max 1000)'}), 400

    # Check tier limits (only for live mode)
    if not dry_run and user_email:
        user = db.get_or_create_user(user_email)
        user_tier = user.get('tier', 'free')

        # Check if purge has expired
        if user_tier == 'purge':
            db.check_purge_expiration(user_email)
            user = db.get_user_by_email(user_email)
            user_tier = user.get('tier', 'free')

        if user_tier == 'free':
            remaining = db.get_remaining_deletes(user_email)
            if remaining <= 0:
                return jsonify({
                    'error': 'limit_reached',
                    'message': 'You have reached your monthly trash limit. Upgrade to Pro for unlimited.',
                    'remaining': 0,
                    'upgrade_url': '/pricing'
                }), 402  # Payment Required

            # Limit to remaining deletes
            if len(message_ids) > remaining:
                return jsonify({
                    'error': 'limit_exceeded',
                    'message': f'You can only trash {remaining} more emails this month. Upgrade to Pro for unlimited.',
                    'remaining': remaining,
                    'requested': len(message_ids),
                    'upgrade_url': '/pricing'
                }), 402

    # DRY RUN MODE - Return simulation results without calling Gmail API
    if dry_run:
        return jsonify({
            'success': True,
            'dry_run': True,
            'would_trash': len(message_ids),
            'message': f'Successfully moved {len(message_ids)} emails to Trash. Items in Trash are NEVER permanently removed!'
        })

    # LIVE MODE - Actually trash the emails with parallel processing
    service = get_gmail_service()
    if not service:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        # Thread-safe counters using list (mutable in closure)
        counters = {'trashed': 0, 'errors': 0}
        counter_lock = threading.Lock()

        def trash_batch(batch_ids):
            """Trash a batch of messages."""
            try:
                service.users().messages().batchModify(
                    userId='me',
                    body={
                        'ids': batch_ids,
                        'addLabelIds': ['TRASH'],
                        'removeLabelIds': ['INBOX']
                    }
                ).execute()
                with counter_lock:
                    counters['trashed'] += len(batch_ids)
                return len(batch_ids), 0
            except HttpError:
                with counter_lock:
                    counters['errors'] += len(batch_ids)
                return 0, len(batch_ids)

        # Split into batches of 100 (Gmail API limit)
        batches = [message_ids[i:i+100] for i in range(0, len(message_ids), 100)]

        # Process batches in parallel (up to 5x faster for large deletions)
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(trash_batch, batch) for batch in batches]
            for future in as_completed(futures):
                pass  # Results tracked via counters dict

        trashed = counters['trashed']
        errors = counters['errors']

        # Record emails cleaned in database
        if trashed > 0 and user_email:
            updated_user = db.record_emails_cleaned(user_email, trashed, query_used)
            remaining = db.get_remaining_deletes(user_email) if updated_user else None
        else:
            remaining = None

        response_data = {
            'success': True,
            'dry_run': False,
            'trashed': trashed,
            'errors': errors,
            'message': f'Successfully moved {trashed} emails to Trash. Items in Trash are automatically deleted after 30 days.'
        }
        if remaining is not None:
            response_data['remaining_deletes'] = remaining

        # AUTO-BACKUP to user's R2 vault (runs in background, never blocks response)
        vault_creds = get_vault_creds(user_email) if user_email else None
        if vault_creds and trashed > 0:
            def run_vault_backup(creds, ids, gmail_service, email):
                import base64
                for mid in ids:
                    try:
                        msg = gmail_service.users().messages().get(
                            userId='me', id=mid, format='raw'
                        ).execute()
                        raw_bytes = base64.urlsafe_b64decode(msg['raw'] + '==')
                        meta = gmail_service.users().messages().get(
                            userId='me', id=mid, format='metadata',
                            metadataHeaders=['Subject', 'From']
                        ).execute()
                        hdrs = {h['name']: h['value'] for h in meta.get('payload', {}).get('headers', [])}
                        vault_r2.backup_email(
                            creds['account_id'], creds['access_key'], creds['secret_key'],
                            creds['bucket'], email, mid,
                            hdrs.get('Subject', 'no-subject'),
                            hdrs.get('From', ''),
                            raw_bytes
                        )
                    except Exception:
                        continue

            backup_thread = threading.Thread(
                target=run_vault_backup,
                args=(vault_creds, message_ids, service, user_email),
                daemon=True
            )
            backup_thread.start()
            response_data['vault_backup'] = 'started'

        return jsonify(response_data)

    except HttpError as e:
        return jsonify({'error': f'Gmail API error: {e.reason}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500




@app.route('/api/trash-list', methods=['GET'])
@login_required
def trash_list():
    service = get_gmail_service()
    if not service:
        return jsonify({'error': 'Not authenticated'}), 401
    try:
        results = service.users().messages().list(
            userId='me', labelIds=['TRASH'], maxResults=100
        ).execute()
        messages = results.get('messages', [])
        total = results.get('resultSizeEstimate', 0)
        items = []
        for msg_info in messages[:50]:
            try:
                msg = service.users().messages().get(
                    userId='me', id=msg_info['id'], format='metadata',
                    metadataHeaders=['From', 'Subject', 'Date']
                ).execute()
                headers = {h['name']: h['value'] for h in msg.get('payload', {}).get('headers', [])}
                size_bytes = int(msg.get('sizeEstimate', 0))
                items.append({
                    'id': msg['id'],
                    'from': headers.get('From', 'Unknown'),
                    'subject': headers.get('Subject', '(No Subject)'),
                    'date': headers.get('Date', ''),
                    'internalDate': int(msg.get('internalDate', 0)) / 1000,
                    'sizeMB': round(size_bytes / (1024 * 1024), 3)
                })
            except Exception:
                continue
        return jsonify({'ok': True, 'total': total, 'items': items})
    except HttpError as e:
        return jsonify({'error': f'Gmail API error: {e.reason}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/rescue', methods=['POST'])
@login_required
def rescue_emails():
    import zipfile, io, base64, re as _re
    from datetime import datetime as _dt
    data = request.get_json()
    message_ids = data.get('message_ids', [])
    if not message_ids:
        return jsonify({'error': 'No messages selected'}), 400
    if len(message_ids) > 100:
        return jsonify({'error': 'Max 100 emails per rescue'}), 400
    service = get_gmail_service()
    if not service:
        return jsonify({'error': 'Not authenticated'}), 401
    try:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
            for msg_id in message_ids:
                try:
                    msg = service.users().messages().get(
                        userId='me', id=msg_id, format='raw'
                    ).execute()
                    raw_bytes = base64.urlsafe_b64decode(msg['raw'] + '==')
                    meta = service.users().messages().get(
                        userId='me', id=msg_id, format='metadata',
                        metadataHeaders=['Subject']
                    ).execute()
                    hdrs = {h['name']: h['value'] for h in meta.get('payload', {}).get('headers', [])}
                    subject = hdrs.get('Subject', 'no-subject')[:50]
                    safe_subject = _re.sub(r'[^\w\s-]', '', subject).strip()[:40]
                    zf.writestr(f'{msg_id}_{safe_subject}.eml', raw_bytes)
                except Exception:
                    continue
        zip_buffer.seek(0)
        return send_file(
            zip_buffer, mimetype='application/zip', as_attachment=True,
            download_name=f'mailremover_rescue_{_dt.now().strftime("%Y%m%d_%H%M%S")}.zip'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500



@app.route('/archive', methods=['POST'])
@login_required
def archive():
    """Archive selected emails (remove from inbox)."""
    data = request.get_json()
    message_ids = data.get('message_ids', [])

    if not message_ids:
        return jsonify({'error': 'No messages selected'}), 400

    service = get_gmail_service()
    if not service:
        return jsonify({'error': 'Not authenticated'}), 401

    try:
        archived = 0

        for i in range(0, len(message_ids), 100):
            batch_ids = message_ids[i:i+100]

            service.users().messages().batchModify(
                userId='me',
                body={
                    'ids': batch_ids,
                    'removeLabelIds': ['INBOX']
                }
            ).execute()
            archived += len(batch_ids)

        return jsonify({
            'success': True,
            'archived': archived,
            'message': f'Archived {archived} messages.'
        })

    except HttpError as e:
        return jsonify({'error': f'Gmail API error: {e.reason}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =============================================================================
# Routes - CASA Compliance (Data Deletion)
# =============================================================================



# =============================================================================
# PERSONAL VAULT — BYOS Cloudflare R2
# =============================================================================

def get_vault_creds(user_email):
    """Get decrypted R2 credentials for a user. Returns dict or None."""
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT r2_account_id_enc, r2_access_key_enc, r2_secret_key_enc, r2_bucket_name_enc, r2_vault_enabled FROM users WHERE email=?",
            (user_email,)
        )
        row = cursor.fetchone()
        if not row or not row[4]:
            return None
        account_id = decrypt_credential(row[0])
        access_key = decrypt_credential(row[1])
        secret_key = decrypt_credential(row[2])
        bucket    = decrypt_credential(row[3])
        if not all([account_id, access_key, secret_key, bucket]):
            return None
        return {'account_id': account_id, 'access_key': access_key,
                'secret_key': secret_key, 'bucket': bucket}
    finally:
        conn.close()


@app.route('/api/vault/connect', methods=['POST'])
@login_required
def vault_connect():
    data = request.get_json()
    account_id = (data.get('account_id') or '').strip()
    access_key = (data.get('access_key') or '').strip()
    secret_key = (data.get('secret_key') or '').strip()
    bucket     = (data.get('bucket') or '').strip()

    if not all([account_id, access_key, secret_key, bucket]):
        return jsonify({'ok': False, 'error': 'All fields required'}), 400

    # Test connection before saving
    ok, msg = vault_r2.test_connection(account_id, access_key, secret_key, bucket)
    if not ok:
        return jsonify({'ok': False, 'error': msg}), 400

    user_email = session['user_email']
    conn = db.get_connection()
    try:
        conn.execute(
            """UPDATE users SET
                r2_account_id_enc=?, r2_access_key_enc=?, r2_secret_key_enc=?,
                r2_bucket_name_enc=?, r2_vault_enabled=1
               WHERE email=?""",
            (encrypt_credential(account_id), encrypt_credential(access_key),
             encrypt_credential(secret_key), encrypt_credential(bucket), user_email)
        )
        conn.commit()
    finally:
        conn.close()

    return jsonify({'ok': True, 'message': 'Vault connected successfully'})


@app.route('/api/vault/status', methods=['GET'])
@login_required
def vault_status():
    user_email = session['user_email']
    creds = get_vault_creds(user_email)
    if not creds:
        return jsonify({'ok': True, 'connected': False})
    ok, msg = vault_r2.test_connection(
        creds['account_id'], creds['access_key'], creds['secret_key'], creds['bucket']
    )
    return jsonify({'ok': True, 'connected': ok, 'message': msg,
                    'bucket': creds['bucket']})


@app.route('/api/vault/disconnect', methods=['POST'])
@login_required
def vault_disconnect():
    user_email = session['user_email']
    conn = db.get_connection()
    try:
        conn.execute(
            """UPDATE users SET r2_account_id_enc=NULL, r2_access_key_enc=NULL,
               r2_secret_key_enc=NULL, r2_bucket_name_enc=NULL, r2_vault_enabled=0
               WHERE email=?""", (user_email,)
        )
        conn.commit()
    finally:
        conn.close()
    return jsonify({'ok': True})


@app.route('/api/vault/browse', methods=['GET'])
@login_required
def vault_browse():
    user_email = session['user_email']
    creds = get_vault_creds(user_email)
    if not creds:
        return jsonify({'ok': False, 'error': 'Vault not connected'}), 400

    search = request.args.get('search', '').strip()
    token  = request.args.get('token')

    result = vault_r2.list_vault(
        creds['account_id'], creds['access_key'], creds['secret_key'],
        creds['bucket'], user_email, search=search or None,
        continuation_token=token or None
    )
    return jsonify(result)


@app.route('/api/vault/download', methods=['POST'])
@login_required
def vault_download():
    import io
    user_email = session['user_email']
    creds = get_vault_creds(user_email)
    if not creds:
        return jsonify({'error': 'Vault not connected'}), 400

    data = request.get_json()
    key  = data.get('key', '')

    # Security: key must start with user's email prefix
    if not key.startswith(user_email + '/'):
        return jsonify({'error': 'Access denied'}), 403

    ok, result = vault_r2.download_email(
        creds['account_id'], creds['access_key'], creds['secret_key'],
        creds['bucket'], key
    )
    if not ok:
        return jsonify({'error': result}), 500

    filename = key.split('/')[-1]
    return send_file(
        io.BytesIO(result),
        mimetype='message/rfc822',
        as_attachment=True,
        download_name=filename
    )

@app.route('/api/delete-my-data', methods=['POST'])
@login_required
def delete_my_data():
    """
    CASA/GDPR Compliance: Delete all user data.

    This endpoint:
    1. Revokes the Google OAuth token
    2. Deletes all user data from our database
    3. Cancels any active Stripe subscription
    4. Clears the session

    Returns JSON with deletion confirmation.
    """
    user_email = session.get('user_email')

    if not user_email:
        return jsonify({'error': 'Not authenticated'}), 401

    result = {
        'email': user_email,
        'google_token_revoked': False,
        'database_deleted': False,
        'stripe_subscription_canceled': False,
        'session_cleared': False
    }

    # 1. Revoke Google OAuth token
    try:
        credentials = get_credentials()
        if credentials and credentials.token:
            import requests
            revoke_response = requests.post(
                'https://oauth2.googleapis.com/revoke',
                params={'token': credentials.token},
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            result['google_token_revoked'] = revoke_response.status_code == 200
    except Exception as e:
        print(f"Error revoking Google token: {e}")

    # 2. Cancel Stripe subscription if active
    try:
        user = db.get_user_by_email(user_email)
        if user and user.get('stripe_subscription_id'):
            stripe.Subscription.cancel(user['stripe_subscription_id'])
            result['stripe_subscription_canceled'] = True
    except Exception as e:
        print(f"Error canceling Stripe subscription: {e}")

    # 3. Delete user data from database
    try:
        db_result = db.delete_user_data(user_email)
        result['database_deleted'] = db_result.get('deleted', False)
        result['history_records_deleted'] = db_result.get('history_records_deleted', 0)
    except Exception as e:
        print(f"Error deleting user data: {e}")

    # 4. Delete token file if it exists
    try:
        if TOKEN_FILE.exists():
            TOKEN_FILE.unlink()
    except Exception as e:
        print(f"Error deleting token file: {e}")

    # 5. Clear session
    session.clear()
    result['session_cleared'] = True

    return jsonify({
        'success': True,
        'message': 'Your data has been deleted from MailRemover.',
        'details': result
    })


@app.route('/delete-account')
@login_required
def delete_account_page():
    """Page for users to confirm account deletion."""
    user_email = session.get('user_email')
    return render_template('delete_account.html', user_email=user_email)


# =============================================================================
# Error Handlers
# =============================================================================

@app.errorhandler(404)
def not_found(e):
    return render_template('error.html', error='Page not found'), 404


@app.errorhandler(500)
def server_error(e):
    return render_template('error.html', error='Server error'), 500


# =============================================================================
# Main - Direct SSL with Let's Encrypt
# =============================================================================

if __name__ == '__main__':
    # Initialize database
    print("Initializing database...")
    db.init_db()

    # Create SSL context
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_context.load_cert_chain(SSL_CERT, SSL_KEY)

    print("=" * 60)
    print("MailRemover - Starting with Direct SSL")
    print("=" * 60)
    print(f"URL: https://mailremover.com:8000")
    print(f"Callback: {REDIRECT_URI}")
    print(f"Token file: {TOKEN_FILE}")
    print(f"Token exists: {TOKEN_FILE.exists()}")
    print(f"Database: {db.get_db_path()}")
    print(f"Stripe configured: {bool(stripe.api_key)}")
    print(f"Lifetime spots: {db.get_lifetime_spots_remaining()}")
    print("=" * 60)

    # Run with SSL
    app.run(
        host='0.0.0.0',
        port=8000,
        ssl_context=ssl_context,
        debug=False
    )
