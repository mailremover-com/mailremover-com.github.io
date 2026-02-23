#!/usr/bin/env python3
"""
MailRemover - Subscription Verification Script
===============================================

Run this on your VM to verify database entries are correct.

Usage:
    python verify_subscription.py                    # Show all users
    python verify_subscription.py rphister@gmail.com # Show specific user
"""

import sqlite3
import sys
from datetime import datetime, date
from pathlib import Path

# Database paths (same logic as database.py)
DB_PATH = Path('/var/www/mailremover/mailremover.db')
if not DB_PATH.parent.exists():
    DB_PATH = Path(__file__).parent / 'mailremover.db'


def get_db():
    """Get database connection."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def print_header(text):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f" {text}")
    print("=" * 60)


def print_user(user):
    """Print user details in a formatted way."""
    tier_colors = {
        'free': '\033[90m',      # Gray
        'purge': '\033[95m',     # Magenta
        'pro': '\033[92m',       # Green
        'lifetime': '\033[93m',  # Yellow
    }
    reset = '\033[0m'
    tier = user['tier']
    color = tier_colors.get(tier, '')

    print(f"\n  Email:          {user['email']}")
    print(f"  Tier:           {color}{tier.upper()}{reset}")
    print(f"  Status:         {user['subscription_status']}")

    if user['tier'] == 'purge' and user['purge_expires_at']:
        expires = datetime.strptime(user['purge_expires_at'], '%Y-%m-%d').date()
        days_left = (expires - date.today()).days
        if days_left > 0:
            print(f"  Purge Expires:  {user['purge_expires_at']} ({days_left} days remaining)")
        else:
            print(f"  Purge Expires:  {user['purge_expires_at']} \033[91m(EXPIRED)\033[0m")

    print(f"  Stripe Customer: {user['stripe_customer_id'] or 'None'}")
    print(f"  Stripe Sub ID:   {user['stripe_subscription_id'] or 'None'}")
    print(f"  Total Cleaned:   {user['total_emails_cleaned']:,} emails")
    print(f"  Monthly Deletes: {user['monthly_deletes']:,}")
    print(f"  Created:         {user['created_at']}")
    print(f"  Updated:         {user['updated_at']}")

    if user.get('deleted_at'):
        print(f"  \033[91mSOFT DELETED:    {user['deleted_at']}\033[0m")


def verify_all_users():
    """Show all users in the database."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users ORDER BY updated_at DESC')
    users = cursor.fetchall()

    print_header(f"All Users ({len(users)} total)")

    if not users:
        print("\n  No users found in database.")
    else:
        for user in users:
            print_user(dict(user))
            print("  " + "-" * 40)

    # Show tier distribution
    cursor.execute('''
        SELECT tier, COUNT(*) as count
        FROM users
        WHERE deleted_at IS NULL
        GROUP BY tier
    ''')
    tiers = cursor.fetchall()

    print_header("Tier Distribution")
    for t in tiers:
        print(f"  {t['tier'].upper():10} {t['count']} users")

    # Show settings
    cursor.execute("SELECT * FROM settings")
    settings = cursor.fetchall()

    print_header("Settings")
    for s in settings:
        print(f"  {s['key']}: {s['value']}")

    conn.close()


def verify_user(email):
    """Show specific user details."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    user = cursor.fetchone()

    if not user:
        print(f"\n\033[91mUser not found: {email}\033[0m")
        conn.close()
        return

    print_header(f"User Details: {email}")
    print_user(dict(user))

    # Show cleanup history
    cursor.execute('''
        SELECT * FROM cleanup_history
        WHERE user_id = ?
        ORDER BY created_at DESC
        LIMIT 10
    ''', (user['id'],))
    history = cursor.fetchall()

    if history:
        print_header("Recent Cleanup History (last 10)")
        for h in history:
            print(f"  {h['created_at']} - {h['emails_deleted']:,} emails")
            if h['query_used']:
                print(f"    Query: {h['query_used'][:50]}...")

    conn.close()


def check_purge_expirations():
    """Check for expiring/expired purge subscriptions."""
    conn = get_db()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT email, purge_expires_at
        FROM users
        WHERE tier = 'purge' AND purge_expires_at IS NOT NULL
        ORDER BY purge_expires_at ASC
    ''')
    purge_users = cursor.fetchall()

    print_header("Purge Subscription Status")

    if not purge_users:
        print("\n  No active Purge subscriptions.")
    else:
        for user in purge_users:
            expires = datetime.strptime(user['purge_expires_at'], '%Y-%m-%d').date()
            days_left = (expires - date.today()).days

            if days_left < 0:
                status = f"\033[91mEXPIRED ({abs(days_left)} days ago)\033[0m"
            elif days_left <= 3:
                status = f"\033[93mEXPIRES SOON ({days_left} days)\033[0m"
            else:
                status = f"\033[92m{days_left} days remaining\033[0m"

            print(f"  {user['email']}: {status}")

    conn.close()


if __name__ == '__main__':
    print("\n" + "=" * 60)
    print(" MailRemover - Subscription Verification")
    print(f" Database: {DB_PATH}")
    print(f" Exists: {DB_PATH.exists()}")
    print("=" * 60)

    if not DB_PATH.exists():
        print("\n\033[91mERROR: Database file not found!\033[0m")
        print(f"Expected at: {DB_PATH}")
        sys.exit(1)

    if len(sys.argv) > 1:
        # Specific user lookup
        email = sys.argv[1]
        verify_user(email)
    else:
        # Show all users and status
        verify_all_users()
        check_purge_expirations()

    print("\n")
