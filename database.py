"""
Database module for MailRemover
================================

SQLite database for user management, subscription tracking, and usage stats.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, date
from contextlib import contextmanager
from typing import Optional

from crypto_utils import encrypt_credential, decrypt_credential

# Admin emails - automatically get lifetime unlimited access
ADMIN_EMAILS = [
    'rphister@gmail.com',
    'mrunnels19@gmail.com',
]

# Database file path
DB_PATH = Path('/var/www/mailremover/mailremover.db')

# For local development, use relative path
if not DB_PATH.parent.exists():
    DB_PATH = Path(__file__).parent / 'mailremover.db'


def get_db_path():
    """Get the database path."""
    return str(DB_PATH)


@contextmanager
def get_db():
    """Context manager for database connections."""
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize the database with required tables."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                tier TEXT DEFAULT 'free' CHECK(tier IN ('free', 'pro', 'purge', 'lifetime')),
                stripe_customer_id TEXT,
                stripe_subscription_id TEXT,
                subscription_status TEXT DEFAULT 'none' CHECK(subscription_status IN ('none', 'active', 'canceled', 'past_due', 'lifetime', 'purge')),
                purge_expires_at DATE,
                total_emails_cleaned INTEGER DEFAULT 0,
                monthly_deletes INTEGER DEFAULT 0,
                monthly_reset_date DATE,
                deleted_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Add deleted_at column if it doesn't exist (for existing databases)
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN deleted_at TIMESTAMP')
        except sqlite3.OperationalError:
            pass  # Column already exists

        # Add multi-provider columns if they don't exist (migration 003)
        multi_provider_columns = [
            ('initial_provider', "TEXT DEFAULT 'gmail'"),
            ('provider_id', 'TEXT'),
            ('display_name', 'TEXT'),
            ('access_token_encrypted', 'TEXT'),
            ('refresh_token_encrypted', 'TEXT'),
            ('token_expires_at', 'TIMESTAMP'),
            ('last_provider_sync', 'TIMESTAMP'),
        ]
        for col_name, col_type in multi_provider_columns:
            try:
                cursor.execute(f'ALTER TABLE users ADD COLUMN {col_name} {col_type}')
            except sqlite3.OperationalError:
                pass  # Column already exists

        # Lifetime spots tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        # Initialize lifetime spots if not exists
        cursor.execute('''
            INSERT OR IGNORE INTO settings (key, value) VALUES ('lifetime_spots_remaining', '500')
        ''')

        # Cleanup history for weekly reports
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cleanup_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                emails_deleted INTEGER NOT NULL,
                query_used TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        # User suggestions/feedback table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS suggestions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_email TEXT NOT NULL,
                suggestion_text TEXT NOT NULL,
                status TEXT DEFAULT 'new' CHECK(status IN ('new', 'reviewed', 'implemented', 'declined')),
                admin_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        print(f"Database initialized at {DB_PATH}")


def get_or_create_user(email: str) -> dict:
    """Get existing user or create new one. Restores soft-deleted accounts."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Try to get existing user (including soft-deleted)
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()

        if row:
            user = dict(row)

            # If account was soft-deleted, restore it (but keep usage stats to prevent abuse)
            if user.get('deleted_at'):
                cursor.execute('''
                    UPDATE users
                    SET deleted_at = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE email = ?
                ''', (email,))
                user['deleted_at'] = None

            # Auto-upgrade admins to lifetime
            if email.lower() in [e.lower() for e in ADMIN_EMAILS] and user['tier'] != 'lifetime':
                cursor.execute('''
                    UPDATE users
                    SET tier = 'lifetime', subscription_status = 'lifetime', updated_at = CURRENT_TIMESTAMP
                    WHERE email = ?
                ''', (email,))
                user['tier'] = 'lifetime'
                user['subscription_status'] = 'lifetime'

            # Check if monthly reset is needed
            if user['monthly_reset_date']:
                reset_date = datetime.strptime(user['monthly_reset_date'], '%Y-%m-%d').date()
                if date.today() >= reset_date:
                    # Reset monthly deletes
                    next_reset = date.today().replace(day=1)
                    if next_reset.month == 12:
                        next_reset = next_reset.replace(year=next_reset.year + 1, month=1)
                    else:
                        next_reset = next_reset.replace(month=next_reset.month + 1)

                    cursor.execute('''
                        UPDATE users
                        SET monthly_deletes = 0, monthly_reset_date = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE email = ?
                    ''', (next_reset.isoformat(), email))
                    user['monthly_deletes'] = 0
            return user

        # Create new user
        next_month = date.today().replace(day=1)
        if next_month.month == 12:
            next_month = next_month.replace(year=next_month.year + 1, month=1)
        else:
            next_month = next_month.replace(month=next_month.month + 1)

        # Check if new user is an admin
        tier = 'lifetime' if email.lower() in [e.lower() for e in ADMIN_EMAILS] else 'free'
        status = 'lifetime' if tier == 'lifetime' else 'none'

        cursor.execute('''
            INSERT INTO users (email, tier, subscription_status, monthly_reset_date) VALUES (?, ?, ?, ?)
        ''', (email, tier, status, next_month.isoformat()))

        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        return dict(cursor.fetchone())


def get_user_by_email(email: str) -> dict | None:
    """Get user by email (excludes soft-deleted users)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE email = ? AND deleted_at IS NULL', (email,))
        row = cursor.fetchone()
        return dict(row) if row else None


def get_user_by_stripe_customer(customer_id: str) -> dict | None:
    """Get user by Stripe customer ID (excludes soft-deleted users)."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE stripe_customer_id = ? AND deleted_at IS NULL', (customer_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_user_stripe(email: str, customer_id: str, subscription_id: str = None) -> None:
    """Update user's Stripe customer and subscription IDs."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET stripe_customer_id = ?, stripe_subscription_id = ?, updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (customer_id, subscription_id, email))


def upgrade_user_to_pro(email: str, subscription_id: str = None) -> None:
    """Upgrade user to Pro (Maintenance) tier."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET tier = 'pro', subscription_status = 'active',
                stripe_subscription_id = ?, purge_expires_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (subscription_id, email))


def upgrade_user_to_purge(email: str) -> None:
    """Upgrade user to Purge tier (30 days of unlimited access).
    If user already has active Purge, extends by 30 days instead of resetting.
    """
    from datetime import timedelta

    with get_db() as conn:
        cursor = conn.cursor()

        # Check if user already has active purge
        cursor.execute('SELECT tier, purge_expires_at FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()

        if row and row['tier'] == 'purge' and row['purge_expires_at']:
            # User already has active purge - extend by 30 days from current expiration
            current_expires = datetime.strptime(row['purge_expires_at'], '%Y-%m-%d').date()
            # If not expired yet, extend from current date; otherwise from today
            if current_expires > date.today():
                expires_at = current_expires + timedelta(days=30)
                print(f"[PURGE] Extending existing purge for {email} to {expires_at}")
            else:
                expires_at = date.today() + timedelta(days=30)
                print(f"[PURGE] Expired purge renewed for {email} to {expires_at}")
        else:
            # New purge - 30 days from today
            expires_at = date.today() + timedelta(days=30)
            print(f"[PURGE] New purge for {email} expires {expires_at}")

        cursor.execute('''
            UPDATE users
            SET tier = 'purge', subscription_status = 'purge',
                purge_expires_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (expires_at.isoformat(), email))


def check_purge_expiration(email: str) -> bool:
    """Check if user's purge has expired. Returns True if expired and user was downgraded."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT tier, purge_expires_at FROM users WHERE email = ?', (email,))
        row = cursor.fetchone()

        if not row or row['tier'] != 'purge':
            return False

        if row['purge_expires_at']:
            expires = datetime.strptime(row['purge_expires_at'], '%Y-%m-%d').date()
            if date.today() > expires:
                # Purge expired, downgrade to free
                cursor.execute('''
                    UPDATE users
                    SET tier = 'free', subscription_status = 'none',
                        purge_expires_at = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE email = ?
                ''', (email,))
                return True
    return False


def upgrade_user_to_lifetime(email: str) -> bool:
    """Upgrade user to Lifetime tier. Returns False if no spots left."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Check spots remaining
        cursor.execute("SELECT value FROM settings WHERE key = 'lifetime_spots_remaining'")
        row = cursor.fetchone()
        spots = int(row['value']) if row else 0

        if spots <= 0:
            return False

        # Decrement spots and upgrade user
        cursor.execute('''
            UPDATE settings SET value = ? WHERE key = 'lifetime_spots_remaining'
        ''', (str(spots - 1),))

        cursor.execute('''
            UPDATE users
            SET tier = 'lifetime', subscription_status = 'lifetime', updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (email,))

        return True


def downgrade_user_to_free(email: str) -> None:
    """Downgrade user to Free tier."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET tier = 'free', subscription_status = 'canceled', updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (email,))


def update_subscription_status(email: str, status: str) -> None:
    """Update user's subscription status."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET subscription_status = ?, updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (status, email))


def record_emails_cleaned(email: str, count: int, query: str = None) -> dict:
    """Record emails cleaned and update user stats. Returns updated user."""
    with get_db() as conn:
        cursor = conn.cursor()

        # Get user
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()
        if not user:
            return None

        user = dict(user)

        # Update totals
        cursor.execute('''
            UPDATE users
            SET total_emails_cleaned = total_emails_cleaned + ?,
                monthly_deletes = monthly_deletes + ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (count, count, email))

        # Record in history
        cursor.execute('''
            INSERT INTO cleanup_history (user_id, emails_deleted, query_used)
            VALUES (?, ?, ?)
        ''', (user['id'], count, query))

        # Get updated user
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        return dict(cursor.fetchone())


def get_remaining_deletes(email: str) -> int:
    """Get remaining deletes for user this month. Returns -1 for unlimited."""
    user = get_user_by_email(email)
    if not user:
        return 100  # Default for new users

    # Check if purge expired first
    if user['tier'] == 'purge':
        check_purge_expiration(email)
        user = get_user_by_email(email)  # Refresh

    if user['tier'] in ('pro', 'purge', 'lifetime'):
        return -1  # Unlimited

    return max(0, 100 - user['monthly_deletes'])


def get_purge_days_remaining(email: str) -> int | None:
    """Get days remaining for purge users. Returns None if not a purge user."""
    user = get_user_by_email(email)
    if not user or user['tier'] != 'purge' or not user.get('purge_expires_at'):
        return None

    expires = datetime.strptime(user['purge_expires_at'], '%Y-%m-%d').date()
    days_left = (expires - date.today()).days
    return max(0, days_left)


def get_lifetime_spots_remaining() -> int:
    """Get remaining lifetime spots."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT value FROM settings WHERE key = 'lifetime_spots_remaining'")
        row = cursor.fetchone()
        return int(row['value']) if row else 0


def get_user_stats(email: str) -> dict:
    """Get user's cleanup statistics."""
    with get_db() as conn:
        cursor = conn.cursor()

        user = get_user_by_email(email)
        if not user:
            return {}

        # Get recent cleanup history
        cursor.execute('''
            SELECT SUM(emails_deleted) as total_week
            FROM cleanup_history
            WHERE user_id = ? AND created_at >= datetime('now', '-7 days')
        ''', (user['id'],))
        week_stats = cursor.fetchone()

        return {
            'total_emails_cleaned': user['total_emails_cleaned'],
            'monthly_deletes': user['monthly_deletes'],
            'tier': user['tier'],
            'emails_cleaned_this_week': week_stats['total_week'] or 0
        }


def delete_user_data(email: str) -> dict:
    """
    Soft-delete user data (CASA/GDPR compliance).
    Clears sensitive data but keeps email + usage stats to prevent free tier abuse.
    Returns summary of what was deleted.
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Get user first
        cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
        user = cursor.fetchone()

        if not user:
            return {'deleted': False, 'reason': 'User not found'}

        user = dict(user)
        user_id = user['id']

        # Delete cleanup history (actual user data)
        cursor.execute('DELETE FROM cleanup_history WHERE user_id = ?', (user_id,))
        history_deleted = cursor.rowcount

        # Soft-delete: clear sensitive data but keep email + usage stats
        cursor.execute('''
            UPDATE users
            SET deleted_at = CURRENT_TIMESTAMP,
                stripe_customer_id = NULL,
                stripe_subscription_id = NULL,
                subscription_status = 'none',
                tier = 'free',
                purge_expires_at = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (user_id,))

        return {
            'deleted': True,
            'email': email,
            'history_records_deleted': history_deleted,
            'stripe_customer_id': user.get('stripe_customer_id'),  # For external cleanup
            'total_emails_cleaned': user.get('total_emails_cleaned', 0),
            'monthly_deletes_preserved': user.get('monthly_deletes', 0)
        }


def add_suggestion(email: str, suggestion_text: str) -> dict:
    """Add a user suggestion to the database."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO suggestions (user_email, suggestion_text)
            VALUES (?, ?)
        ''', (email, suggestion_text))

        suggestion_id = cursor.lastrowid
        return {
            'id': suggestion_id,
            'email': email,
            'suggestion_text': suggestion_text,
            'created_at': datetime.now().isoformat()
        }


def get_all_suggestions(status: str = None) -> list:
    """Get all suggestions, optionally filtered by status."""
    with get_db() as conn:
        cursor = conn.cursor()
        if status:
            cursor.execute('''
                SELECT * FROM suggestions WHERE status = ? ORDER BY created_at DESC
            ''', (status,))
        else:
            cursor.execute('SELECT * FROM suggestions ORDER BY created_at DESC')
        return [dict(row) for row in cursor.fetchall()]


def get_suggestion_count() -> int:
    """Get count of new (unreviewed) suggestions."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM suggestions WHERE status = 'new'")
        row = cursor.fetchone()
        return row['count'] if row else 0


# =============================================================================
# MULTI-PROVIDER USER MANAGEMENT
# =============================================================================

def update_user_provider_tokens(
    email: str,
    provider: str,
    access_token: str,
    refresh_token: str,
    expires_at: datetime = None
) -> bool:
    """
    Store encrypted OAuth tokens for a user's provider.

    Args:
        email: User's email address
        provider: Provider name (gmail, yahoo, outlook, etc.)
        access_token: OAuth access token (will be encrypted)
        refresh_token: OAuth refresh token (will be encrypted)
        expires_at: Token expiration datetime

    Returns:
        True if successful, False otherwise
    """
    with get_db() as conn:
        cursor = conn.cursor()

        # Encrypt tokens before storage
        access_token_enc = encrypt_credential(access_token) if access_token else None
        refresh_token_enc = encrypt_credential(refresh_token) if refresh_token else None

        # Format expires_at for SQLite
        expires_str = expires_at.isoformat() if expires_at else None

        cursor.execute('''
            UPDATE users
            SET access_token_encrypted = ?,
                refresh_token_encrypted = ?,
                token_expires_at = ?,
                initial_provider = COALESCE(initial_provider, ?),
                last_provider_sync = CURRENT_TIMESTAMP,
                updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (access_token_enc, refresh_token_enc, expires_str, provider, email))

        return cursor.rowcount > 0


def get_user_provider_tokens(email: str, provider: str = None) -> Optional[dict]:
    """
    Retrieve and decrypt OAuth tokens for a user.

    Args:
        email: User's email address
        provider: Provider name (optional, for validation)

    Returns:
        Dict with decrypted tokens and metadata, or None if not found
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT access_token_encrypted, refresh_token_encrypted,
                   token_expires_at, initial_provider, last_provider_sync,
                   provider_id, display_name
            FROM users
            WHERE email = ? AND deleted_at IS NULL
        ''', (email,))

        row = cursor.fetchone()
        if not row:
            return None

        # If provider specified, validate it matches
        if provider and row['initial_provider'] and row['initial_provider'] != provider:
            return None

        # Decrypt tokens
        access_token = decrypt_credential(row['access_token_encrypted']) if row['access_token_encrypted'] else None
        refresh_token = decrypt_credential(row['refresh_token_encrypted']) if row['refresh_token_encrypted'] else None

        # Parse expires_at
        expires_at = None
        if row['token_expires_at']:
            try:
                expires_at = datetime.fromisoformat(row['token_expires_at'])
            except (ValueError, TypeError):
                pass

        return {
            'access_token': access_token,
            'refresh_token': refresh_token,
            'expires_at': expires_at,
            'provider': row['initial_provider'],
            'provider_id': row['provider_id'],
            'display_name': row['display_name'],
            'last_sync': row['last_provider_sync']
        }


def set_user_initial_provider(email: str, provider: str) -> bool:
    """
    Set the user's initial/primary authentication provider.

    Args:
        email: User's email address
        provider: Provider name (gmail, yahoo, outlook, etc.)

    Returns:
        True if successful, False otherwise
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET initial_provider = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (provider, email))

        return cursor.rowcount > 0


def update_user_display_name(email: str, display_name: str) -> bool:
    """
    Update the user's display name (from provider profile).

    Args:
        email: User's email address
        display_name: Display name from provider

    Returns:
        True if successful, False otherwise
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET display_name = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (display_name, email))

        return cursor.rowcount > 0


def update_user_provider_id(email: str, provider_id: str) -> bool:
    """
    Update the user's provider-specific ID.

    Args:
        email: User's email address
        provider_id: Provider-specific user identifier

    Returns:
        True if successful, False otherwise
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET provider_id = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (provider_id, email))

        return cursor.rowcount > 0


def clear_user_provider_tokens(email: str) -> bool:
    """
    Clear OAuth tokens for a user (for logout/disconnect).

    Args:
        email: User's email address

    Returns:
        True if successful, False otherwise
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE users
            SET access_token_encrypted = NULL,
                refresh_token_encrypted = NULL,
                token_expires_at = NULL,
                last_provider_sync = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE email = ?
        ''', (email,))

        return cursor.rowcount > 0


def is_token_expired(email: str) -> bool:
    """
    Check if the user's access token is expired.

    Args:
        email: User's email address

    Returns:
        True if expired or no token, False if valid
    """
    tokens = get_user_provider_tokens(email)
    if not tokens or not tokens.get('expires_at'):
        return True

    return datetime.now() >= tokens['expires_at']


# Initialize database on import
if __name__ == '__main__':
    init_db()
