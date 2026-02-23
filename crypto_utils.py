"""
Encryption Utilities for MailRemover
=====================================

AES-256 encryption for storing sensitive credentials like Yahoo App Passwords.

Security: Uses Fernet (AES-128-CBC with HMAC) for authenticated encryption.
For production, consider upgrading to AES-256-GCM.

Author: MailRemover Team
Version: 1.0.0
"""

import os
import base64
import hashlib
from typing import Optional
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


# =============================================================================
# ENCRYPTION KEY MANAGEMENT
# =============================================================================

def get_encryption_key() -> bytes:
    """
    Get or generate the encryption key from environment variable.

    The key should be set as MAILREMOVER_ENCRYPTION_KEY in .env
    If not set, generates a deterministic key from FLASK_SECRET_KEY.

    Returns:
        32-byte encryption key
    """
    # Check for dedicated encryption key
    encryption_key = os.environ.get('MAILREMOVER_ENCRYPTION_KEY')

    if encryption_key:
        # Decode if base64 encoded
        try:
            key = base64.urlsafe_b64decode(encryption_key)
            if len(key) == 32:
                return base64.urlsafe_b64encode(key)
        except:
            pass

        # Hash the key to get consistent length
        return base64.urlsafe_b64encode(
            hashlib.sha256(encryption_key.encode()).digest()
        )

    # Fall back to deriving from Flask secret key
    flask_secret = os.environ.get('FLASK_SECRET_KEY', 'default-dev-key-change-in-production')

    # Use PBKDF2 to derive a key
    salt = b'mailremover-yahoo-v1'  # Static salt for deterministic key
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )

    key = kdf.derive(flask_secret.encode())
    return base64.urlsafe_b64encode(key)


def get_fernet() -> Fernet:
    """Get Fernet instance for encryption/decryption."""
    return Fernet(get_encryption_key())


# =============================================================================
# ENCRYPTION FUNCTIONS
# =============================================================================

def encrypt_credential(plaintext: str) -> str:
    """
    Encrypt a credential (e.g., Yahoo App Password) for database storage.

    Args:
        plaintext: The credential to encrypt

    Returns:
        Base64-encoded encrypted string, safe for database storage
    """
    if not plaintext:
        return ""

    fernet = get_fernet()
    encrypted = fernet.encrypt(plaintext.encode())
    return encrypted.decode('utf-8')


def decrypt_credential(encrypted: str) -> Optional[str]:
    """
    Decrypt a credential from database.

    Args:
        encrypted: Base64-encoded encrypted string

    Returns:
        Decrypted plaintext, or None if decryption fails
    """
    if not encrypted:
        return None

    try:
        fernet = get_fernet()
        decrypted = fernet.decrypt(encrypted.encode())
        return decrypted.decode('utf-8')
    except InvalidToken:
        print("Decryption failed: Invalid token or key mismatch")
        return None
    except Exception as e:
        print(f"Decryption error: {e}")
        return None


# =============================================================================
# YAHOO-SPECIFIC HELPERS
# =============================================================================

def encrypt_yahoo_password(app_password: str) -> str:
    """
    Encrypt Yahoo App Password for storage.

    Args:
        app_password: 16-character Yahoo App Password

    Returns:
        Encrypted password string
    """
    # Clean the password (remove spaces, lowercase)
    cleaned = app_password.replace(" ", "").strip()
    return encrypt_credential(cleaned)


def decrypt_yahoo_password(encrypted_password: str) -> Optional[str]:
    """
    Decrypt stored Yahoo App Password.

    Args:
        encrypted_password: Encrypted password from database

    Returns:
        Decrypted App Password, or None if failed
    """
    return decrypt_credential(encrypted_password)


# =============================================================================
# DATABASE INTEGRATION
# =============================================================================

def store_yahoo_credentials(user_email: str, yahoo_email: str, app_password: str, db_connection) -> bool:
    """
    Store encrypted Yahoo credentials in database.

    Args:
        user_email: MailRemover user's email (primary key)
        yahoo_email: Yahoo email address to connect
        app_password: Yahoo App Password (will be encrypted)
        db_connection: SQLite database connection

    Returns:
        True if successful
    """
    try:
        encrypted_password = encrypt_yahoo_password(app_password)

        cursor = db_connection.cursor()
        cursor.execute('''
            UPDATE users
            SET yahoo_email = ?,
                yahoo_app_password_encrypted = ?,
                yahoo_connected_at = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (yahoo_email, encrypted_password, user_email))

        db_connection.commit()
        return cursor.rowcount > 0

    except Exception as e:
        print(f"Error storing Yahoo credentials: {e}")
        return False


def get_yahoo_credentials(user_email: str, db_connection) -> Optional[dict]:
    """
    Retrieve and decrypt Yahoo credentials from database.

    Args:
        user_email: MailRemover user's email
        db_connection: SQLite database connection

    Returns:
        Dict with yahoo_email and app_password, or None
    """
    try:
        cursor = db_connection.cursor()
        cursor.execute('''
            SELECT yahoo_email, yahoo_app_password_encrypted
            FROM users
            WHERE email = ? AND yahoo_email IS NOT NULL
        ''', (user_email,))

        row = cursor.fetchone()
        if not row:
            return None

        yahoo_email, encrypted_password = row

        if not encrypted_password:
            return None

        decrypted_password = decrypt_yahoo_password(encrypted_password)
        if not decrypted_password:
            return None

        return {
            "yahoo_email": yahoo_email,
            "app_password": decrypted_password
        }

    except Exception as e:
        print(f"Error retrieving Yahoo credentials: {e}")
        return None


def clear_yahoo_credentials(user_email: str, db_connection) -> bool:
    """
    Clear Yahoo credentials from database (for Secure Sign-Out).

    Args:
        user_email: MailRemover user's email
        db_connection: SQLite database connection

    Returns:
        True if successful
    """
    try:
        cursor = db_connection.cursor()
        cursor.execute('''
            UPDATE users
            SET yahoo_email = NULL,
                yahoo_app_password_encrypted = NULL,
                yahoo_connected_at = NULL,
                yahoo_last_sync = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (user_email,))

        db_connection.commit()
        return True

    except Exception as e:
        print(f"Error clearing Yahoo credentials: {e}")
        return False


# =============================================================================
# VALIDATION
# =============================================================================

def validate_yahoo_app_password(password: str) -> tuple[bool, str]:
    """
    Validate Yahoo App Password format.

    Yahoo App Passwords are 16 characters (letters only, no spaces).

    Returns:
        (is_valid, error_message)
    """
    cleaned = password.replace(" ", "").strip()

    if not cleaned:
        return False, "App Password cannot be empty"

    if len(cleaned) != 16:
        return False, f"App Password must be 16 characters (got {len(cleaned)})"

    if not cleaned.isalpha():
        return False, "App Password should only contain letters"

    return True, "Valid"


# =============================================================================
# MULTI-PROVIDER SUPPORT (email_accounts table)
# =============================================================================

import uuid

def store_provider_credentials(
    user_id: int,
    provider: str,
    email: str,
    credentials: str,
    auth_method: str,
    display_name: str = None,
    db_connection=None
) -> Optional[str]:
    """
    Store encrypted provider credentials in the email_accounts table.

    Args:
        user_id: User's database ID
        provider: Provider name (gmail, yahoo, outlook, etc.)
        email: Email address for this provider
        credentials: Credential to encrypt (App Password or OAuth refresh token)
        auth_method: 'oauth2' or 'app_password'
        display_name: Optional friendly name like "Work Yahoo"
        db_connection: SQLite database connection

    Returns:
        Account ID if successful, None otherwise
    """
    try:
        encrypted_key = encrypt_credential(credentials)
        account_id = str(uuid.uuid4())

        cursor = db_connection.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO email_accounts
            (id, user_id, provider, email, display_name, encrypted_key, auth_method, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'active', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (account_id, user_id, provider, email, display_name, encrypted_key, auth_method))

        db_connection.commit()
        return account_id

    except Exception as e:
        print(f"Error storing {provider} credentials: {e}")
        return None


def get_provider_credentials(
    user_id: int,
    provider: str,
    email: str = None,
    db_connection=None
) -> Optional[dict]:
    """
    Retrieve and decrypt provider credentials from email_accounts table.

    Args:
        user_id: User's database ID
        provider: Provider name
        email: Specific email (optional - if not provided, returns first active)
        db_connection: SQLite database connection

    Returns:
        Dict with account info and decrypted credentials, or None
    """
    try:
        cursor = db_connection.cursor()

        if email:
            cursor.execute('''
                SELECT id, email, display_name, encrypted_key, auth_method, status, last_sync_at, emails_cleaned
                FROM email_accounts
                WHERE user_id = ? AND provider = ? AND email = ? AND status = 'active'
            ''', (user_id, provider, email))
        else:
            cursor.execute('''
                SELECT id, email, display_name, encrypted_key, auth_method, status, last_sync_at, emails_cleaned
                FROM email_accounts
                WHERE user_id = ? AND provider = ? AND status = 'active'
                LIMIT 1
            ''', (user_id, provider))

        row = cursor.fetchone()
        if not row:
            return None

        account_id, email, display_name, encrypted_key, auth_method, status, last_sync, emails_cleaned = row

        decrypted_key = decrypt_credential(encrypted_key) if encrypted_key else None

        return {
            "id": account_id,
            "email": email,
            "display_name": display_name,
            "credentials": decrypted_key,
            "auth_method": auth_method,
            "status": status,
            "last_sync_at": last_sync,
            "emails_cleaned": emails_cleaned
        }

    except Exception as e:
        print(f"Error retrieving {provider} credentials: {e}")
        return None


def get_user_providers(user_id: int, db_connection=None) -> list:
    """
    Get list of all connected providers for a user.

    Args:
        user_id: User's database ID
        db_connection: SQLite database connection

    Returns:
        List of dicts with provider info (without decrypted credentials)
    """
    try:
        cursor = db_connection.cursor()
        cursor.execute('''
            SELECT id, provider, email, display_name, auth_method, status, last_sync_at, emails_cleaned
            FROM email_accounts
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))

        providers = []
        for row in cursor.fetchall():
            providers.append({
                "id": row[0],
                "provider": row[1],
                "email": row[2],
                "display_name": row[3],
                "auth_method": row[4],
                "status": row[5],
                "last_sync_at": row[6],
                "emails_cleaned": row[7]
            })

        return providers

    except Exception as e:
        print(f"Error getting user providers: {e}")
        return []


def update_provider_status(
    account_id: str,
    status: str,
    last_error: str = None,
    db_connection=None
) -> bool:
    """
    Update provider account status.

    Args:
        account_id: Email account ID
        status: New status (active, reauth_required, disconnected, error)
        last_error: Error message if status is error
        db_connection: SQLite database connection

    Returns:
        True if successful
    """
    try:
        cursor = db_connection.cursor()
        cursor.execute('''
            UPDATE email_accounts
            SET status = ?, last_error = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (status, last_error, account_id))

        db_connection.commit()
        return cursor.rowcount > 0

    except Exception as e:
        print(f"Error updating provider status: {e}")
        return False


def delete_provider_account(account_id: str, db_connection=None) -> bool:
    """
    Delete a provider account (disconnect).

    Args:
        account_id: Email account ID to delete
        db_connection: SQLite database connection

    Returns:
        True if successful
    """
    try:
        cursor = db_connection.cursor()
        cursor.execute('DELETE FROM email_accounts WHERE id = ?', (account_id,))
        db_connection.commit()
        return cursor.rowcount > 0

    except Exception as e:
        print(f"Error deleting provider account: {e}")
        return False


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    # Test encryption/decryption
    test_password = "abcdefghijklmnop"  # 16 char test

    print("Testing encryption...")
    encrypted = encrypt_yahoo_password(test_password)
    print(f"Encrypted: {encrypted[:50]}...")

    decrypted = decrypt_yahoo_password(encrypted)
    print(f"Decrypted: {decrypted}")
    print(f"Match: {decrypted == test_password}")

    # Test validation
    print("\nTesting validation...")
    valid, msg = validate_yahoo_app_password("abcd efgh ijkl mnop")
    print(f"With spaces: {valid} - {msg}")

    valid, msg = validate_yahoo_app_password("short")
    print(f"Too short: {valid} - {msg}")
