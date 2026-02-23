"""
Yahoo Mail Connector for MailRemover
=====================================

IMAP/SMTP integration for Yahoo Mail using App Passwords.
OAuth2 is currently restricted for new clients (as of 2026).

Author: MailRemover Team
Version: 1.0.0
"""

import imaplib
import smtplib
import ssl
import email
from email.header import decode_header
from typing import Tuple, Optional, List, Dict, Any
from datetime import datetime
import re

# =============================================================================
# YAHOO MAIL CONFIGURATION
# =============================================================================

YAHOO_CONFIG = {
    "provider": "yahoo",
    "display_name": "Yahoo Mail",
    "imap": {
        "host": "imap.mail.yahoo.com",
        "port": 993,
        "secure": True,
    },
    "smtp": {
        "host": "smtp.mail.yahoo.com",
        "port": 465,
        "secure": True,
    },
    "rate_limit": {
        "max_connections_per_hour": 100,
        "max_actions_per_minute": 30,
    }
}

# Yahoo uses different folder names than Gmail
YAHOO_FOLDER_MAP = {
    # Internal name -> Yahoo folder name
    "inbox": "Inbox",
    "sent": "Sent",
    "drafts": "Draft",        # Singular (not "Drafts")
    "trash": "Trash",
    "spam": "Bulk Mail",      # Yahoo calls spam "Bulk Mail"
    "archive": "Archive",
}

# Reverse mapping for normalizing Yahoo folders to internal names
YAHOO_FOLDER_REVERSE_MAP = {v: k for k, v in YAHOO_FOLDER_MAP.items()}


# =============================================================================
# CONNECTION & AUTHENTICATION
# =============================================================================

def create_ssl_context() -> ssl.SSLContext:
    """Create a secure SSL context for Yahoo connections."""
    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    return context


def verify_connection(email_address: str, app_password: str) -> bool:
    """
    Verify Yahoo Mail credentials are valid.

    Args:
        email_address: Yahoo email address
        app_password: 16-character App Password from Yahoo

    Returns:
        True if connection successful, False otherwise
    """
    success, _ = test_yahoo_connection(email_address, app_password)
    return success


def test_yahoo_connection(email_address: str, app_password: str) -> Tuple[bool, Optional[str]]:
    """
    Test Yahoo Mail IMAP connection with App Password.

    Args:
        email_address: Yahoo email address
        app_password: 16-character App Password

    Returns:
        (success: bool, message: str) - Success status and message
    """
    try:
        context = create_ssl_context()

        # Connect to Yahoo IMAP
        imap = imaplib.IMAP4_SSL(
            host=YAHOO_CONFIG["imap"]["host"],
            port=YAHOO_CONFIG["imap"]["port"],
            ssl_context=context
        )

        # Authenticate with App Password
        imap.login(email_address, app_password)

        # Verify inbox access
        status, _ = imap.select("Inbox", readonly=True)
        if status != "OK":
            imap.logout()
            return False, "Could not access inbox"

        # Get message count to verify read access
        status, messages = imap.search(None, "ALL")
        if status != "OK":
            imap.logout()
            return False, "Could not read messages"

        message_count = len(messages[0].split()) if messages[0] else 0

        imap.logout()
        return True, f"Connected successfully. {message_count} messages in inbox."

    except imaplib.IMAP4.error as e:
        error_msg = str(e).upper()
        if "AUTHENTICATIONFAILED" in error_msg or "LOGIN" in error_msg:
            return False, "Invalid email or App Password. Please verify your credentials."
        return False, f"IMAP error: {str(e)}"

    except ssl.SSLError as e:
        return False, f"SSL/TLS error: {str(e)}"

    except Exception as e:
        return False, f"Connection failed: {str(e)}"


def test_smtp_connection(email_address: str, app_password: str) -> Tuple[bool, Optional[str]]:
    """
    Test Yahoo Mail SMTP connection.

    Returns:
        (success: bool, message: str)
    """
    try:
        context = create_ssl_context()

        smtp = smtplib.SMTP_SSL(
            host=YAHOO_CONFIG["smtp"]["host"],
            port=YAHOO_CONFIG["smtp"]["port"],
            context=context
        )

        smtp.login(email_address, app_password)
        smtp.quit()

        return True, "SMTP connection successful"

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed. Check your App Password."
    except Exception as e:
        return False, f"SMTP error: {str(e)}"


# =============================================================================
# FOLDER OPERATIONS
# =============================================================================

def get_yahoo_folders(email_address: str, app_password: str) -> Tuple[bool, List[str]]:
    """
    Retrieve available folders from Yahoo Mail account.

    Returns:
        (success: bool, folders: list)
    """
    try:
        context = create_ssl_context()
        imap = imaplib.IMAP4_SSL(
            host=YAHOO_CONFIG["imap"]["host"],
            port=YAHOO_CONFIG["imap"]["port"],
            ssl_context=context
        )

        imap.login(email_address, app_password)

        status, folder_list = imap.list()
        if status != "OK":
            return False, []

        folders = []
        for folder_data in folder_list:
            if isinstance(folder_data, bytes):
                # Parse folder name from IMAP response
                decoded = folder_data.decode()
                # Extract folder name after delimiter
                match = re.search(r'"/" "?([^"]+)"?$', decoded)
                if match:
                    folder_name = match.group(1).strip('"')
                    folders.append(folder_name)

        imap.logout()
        return True, folders

    except Exception as e:
        return False, []


def normalize_folder_name(yahoo_folder: str) -> str:
    """Convert Yahoo folder name to internal standard name."""
    return YAHOO_FOLDER_REVERSE_MAP.get(yahoo_folder, yahoo_folder.lower())


def get_yahoo_folder_name(internal_name: str) -> str:
    """Convert internal folder name to Yahoo folder name."""
    return YAHOO_FOLDER_MAP.get(internal_name.lower(), internal_name)


# =============================================================================
# EMAIL OPERATIONS
# =============================================================================

class YahooMailClient:
    """Yahoo Mail client for MailRemover operations."""

    def __init__(self, email_address: str, app_password: str):
        self.email_address = email_address
        self.app_password = app_password
        self.imap: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> bool:
        """Establish IMAP connection."""
        try:
            context = create_ssl_context()
            self.imap = imaplib.IMAP4_SSL(
                host=YAHOO_CONFIG["imap"]["host"],
                port=YAHOO_CONFIG["imap"]["port"],
                ssl_context=context
            )
            self.imap.login(self.email_address, self.app_password)
            return True
        except Exception as e:
            print(f"Yahoo connection error: {e}")
            return False

    def disconnect(self):
        """Close IMAP connection."""
        if self.imap:
            try:
                self.imap.logout()
            except:
                pass
            self.imap = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def get_inbox_stats(self) -> Dict[str, int]:
        """Get inbox statistics."""
        stats = {"total": 0, "unread": 0}

        if not self.imap:
            return stats

        try:
            status, _ = self.imap.select("Inbox", readonly=True)
            if status != "OK":
                return stats

            # Total messages
            status, messages = self.imap.search(None, "ALL")
            if status == "OK" and messages[0]:
                stats["total"] = len(messages[0].split())

            # Unread messages
            status, messages = self.imap.search(None, "UNSEEN")
            if status == "OK" and messages[0]:
                stats["unread"] = len(messages[0].split())

        except Exception as e:
            print(f"Error getting stats: {e}")

        return stats

    def search_messages(self, query: str, folder: str = "Inbox",
                        max_results: int = 500) -> List[Dict[str, Any]]:
        """
        Search messages in Yahoo Mail.

        Args:
            query: IMAP search query (e.g., 'FROM "newsletter@"')
            folder: Folder to search in
            max_results: Maximum messages to return

        Returns:
            List of message dictionaries with id, from, subject, date
        """
        messages = []

        if not self.imap:
            return messages

        try:
            # Map folder name if needed
            yahoo_folder = get_yahoo_folder_name(folder)

            status, _ = self.imap.select(yahoo_folder, readonly=True)
            if status != "OK":
                return messages

            # Execute search
            status, data = self.imap.search(None, query)
            if status != "OK":
                return messages

            message_ids = data[0].split()

            # Limit results
            message_ids = message_ids[:max_results]

            # Fetch message headers
            for msg_id in message_ids:
                try:
                    status, msg_data = self.imap.fetch(msg_id, "(RFC822.HEADER)")
                    if status != "OK":
                        continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Decode headers
                    subject = self._decode_header(msg.get("Subject", ""))
                    from_addr = self._decode_header(msg.get("From", ""))
                    date_str = msg.get("Date", "")

                    messages.append({
                        "id": msg_id.decode(),
                        "from": from_addr,
                        "subject": subject[:100],
                        "date": date_str,
                    })

                except Exception as e:
                    continue

        except Exception as e:
            print(f"Search error: {e}")

        return messages

    def move_to_trash(self, message_ids: List[str]) -> Tuple[int, int]:
        """
        Move messages to Trash folder.

        Args:
            message_ids: List of message IDs to trash

        Returns:
            (success_count, error_count)
        """
        success = 0
        errors = 0

        if not self.imap:
            return 0, len(message_ids)

        try:
            trash_folder = YAHOO_FOLDER_MAP["trash"]

            for msg_id in message_ids:
                try:
                    # Copy to Trash
                    status, _ = self.imap.copy(msg_id, trash_folder)
                    if status == "OK":
                        # Mark original as deleted
                        self.imap.store(msg_id, "+FLAGS", "\\Deleted")
                        success += 1
                    else:
                        errors += 1
                except:
                    errors += 1

            # Expunge deleted messages
            self.imap.expunge()

        except Exception as e:
            print(f"Trash error: {e}")
            errors = len(message_ids) - success

        return success, errors

    def move_to_spam(self, message_ids: List[str]) -> Tuple[int, int]:
        """Move messages to Bulk Mail (spam) folder."""
        success = 0
        errors = 0

        if not self.imap:
            return 0, len(message_ids)

        try:
            spam_folder = YAHOO_FOLDER_MAP["spam"]  # "Bulk Mail"

            for msg_id in message_ids:
                try:
                    status, _ = self.imap.copy(msg_id, spam_folder)
                    if status == "OK":
                        self.imap.store(msg_id, "+FLAGS", "\\Deleted")
                        success += 1
                    else:
                        errors += 1
                except:
                    errors += 1

            self.imap.expunge()

        except Exception as e:
            print(f"Spam move error: {e}")

        return success, errors

    def _decode_header(self, header_value: str) -> str:
        """Decode email header value."""
        if not header_value:
            return ""
        try:
            decoded_parts = decode_header(header_value)
            result = ""
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    result += part.decode(encoding or "utf-8", errors="replace")
                else:
                    result += part
            return result
        except:
            return str(header_value)


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def is_yahoo_email(email_address: str) -> bool:
    """Check if email address is a Yahoo/AOL domain."""
    yahoo_domains = [
        "yahoo.com", "yahoo.co.uk", "yahoo.ca", "yahoo.com.au",
        "yahoo.co.in", "yahoo.co.jp", "yahoo.de", "yahoo.fr",
        "yahoo.es", "yahoo.it", "yahoo.com.br", "yahoo.com.mx",
        "ymail.com", "rocketmail.com",
        "aol.com", "aim.com", "aol.co.uk",
        "att.net", "sbcglobal.net", "bellsouth.net",  # AT&T uses Yahoo
    ]

    domain = email_address.lower().split("@")[-1]
    return domain in yahoo_domains


def format_app_password(raw_password: str) -> str:
    """
    Clean and format App Password.
    Yahoo App Passwords are 16 characters, sometimes shown with spaces.
    """
    # Remove all spaces and convert to lowercase
    return raw_password.replace(" ", "").lower()


# =============================================================================
# MAIN (for testing)
# =============================================================================

if __name__ == "__main__":
    # Test connection (replace with actual credentials)
    test_email = input("Yahoo Email: ")
    test_password = input("App Password: ")

    success, message = test_yahoo_connection(test_email, test_password)
    print(f"Connection: {'SUCCESS' if success else 'FAILED'}")
    print(f"Message: {message}")

    if success:
        success, folders = get_yahoo_folders(test_email, test_password)
        print(f"\nFolders: {folders}")
