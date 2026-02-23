"""
Yahoo Mail Connector
=====================

IMAP-based connector for Yahoo Mail using App Passwords.

Inherits from BaseConnector for consistent interface.

Author: MailRemover Team
Version: 2.1.0
"""

import imaplib
import ssl
import email
from email.header import decode_header
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import re

from .base_connector import (
    BaseConnector,
    ConnectionResult,
    EmailMessage,
    AuthMethod,
)


class YahooConnector(BaseConnector):
    """
    Yahoo Mail connector using IMAP + App Passwords.

    Yahoo OAuth2 is currently restricted for new clients (as of 2026),
    so we use App Passwords for authentication.
    """

    # Provider metadata
    PROVIDER_NAME = "yahoo"
    DISPLAY_NAME = "Yahoo Mail"
    COLOR = "#6001D2"  # Yahoo purple
    ICON = "yahoo"
    AUTH_METHOD = AuthMethod.APP_PASSWORD

    # IMAP configuration
    IMAP_HOST = "imap.mail.yahoo.com"
    IMAP_PORT = 993
    SMTP_HOST = "smtp.mail.yahoo.com"
    SMTP_PORT = 465

    # Yahoo-specific folder mappings (Yahoo uses different names)
    FOLDER_MAP = {
        "inbox": "Inbox",
        "sent": "Sent",
        "drafts": "Draft",       # Singular, not "Drafts"
        "trash": "Trash",
        "spam": "Bulk Mail",     # Yahoo calls spam "Bulk Mail"
        "archive": "Archive",
    }

    FOLDER_REVERSE_MAP = {v: k for k, v in FOLDER_MAP.items()}

    def __init__(self, email_address: str, app_password: str):
        """
        Initialize Yahoo connector.

        Args:
            email_address: Yahoo email address
            app_password: 16-character App Password (not regular password)
        """
        super().__init__(email_address, app_password)
        self._imap: Optional[imaplib.IMAP4_SSL] = None

    def _create_ssl_context(self) -> ssl.SSLContext:
        """Create secure SSL context."""
        context = ssl.create_default_context()
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        return context

    def _clean_app_password(self, password: str) -> str:
        """Clean and format App Password."""
        return password.replace(" ", "").strip().lower()

    # =========================================================================
    # Required Abstract Method Implementations
    # =========================================================================

    def test_connection(self) -> ConnectionResult:
        """Test Yahoo Mail connection with credentials."""
        try:
            context = self._create_ssl_context()
            imap = imaplib.IMAP4_SSL(
                host=self.IMAP_HOST,
                port=self.IMAP_PORT,
                ssl_context=context
            )

            password = self._clean_app_password(self._credentials)
            imap.login(self.email, password)

            # Verify inbox access
            status, _ = imap.select("Inbox", readonly=True)
            if status != "OK":
                imap.logout()
                return ConnectionResult(
                    success=False,
                    message="Could not access inbox"
                )

            # Get message count
            status, messages = imap.search(None, "ALL")
            message_count = len(messages[0].split()) if messages[0] else 0

            imap.logout()

            return ConnectionResult(
                success=True,
                message=f"Connected successfully. {message_count} messages in inbox.",
                details={"message_count": message_count}
            )

        except imaplib.IMAP4.error as e:
            error_msg = str(e).upper()
            if "AUTHENTICATIONFAILED" in error_msg or "LOGIN" in error_msg:
                self._last_error = "Invalid email or App Password"
                return ConnectionResult(
                    success=False,
                    message="Invalid email or App Password. Please verify your credentials."
                )
            self._last_error = str(e)
            return ConnectionResult(success=False, message=f"IMAP error: {e}")

        except ssl.SSLError as e:
            self._last_error = str(e)
            return ConnectionResult(success=False, message=f"SSL error: {e}")

        except Exception as e:
            self._last_error = str(e)
            return ConnectionResult(success=False, message=f"Connection failed: {e}")

    def connect(self) -> bool:
        """Establish IMAP connection."""
        try:
            context = self._create_ssl_context()
            self._imap = imaplib.IMAP4_SSL(
                host=self.IMAP_HOST,
                port=self.IMAP_PORT,
                ssl_context=context
            )

            password = self._clean_app_password(self._credentials)
            self._imap.login(self.email, password)
            return True

        except Exception as e:
            self._last_error = str(e)
            self._imap = None
            return False

    def disconnect(self) -> None:
        """Close IMAP connection."""
        if self._imap:
            try:
                self._imap.logout()
            except:
                pass
            self._imap = None

    def get_inbox_stats(self) -> Dict[str, int]:
        """Get inbox statistics."""
        stats = {"total": 0, "unread": 0}

        if not self._imap:
            return stats

        try:
            status, _ = self._imap.select("Inbox", readonly=True)
            if status != "OK":
                return stats

            # Total messages
            status, messages = self._imap.search(None, "ALL")
            if status == "OK" and messages[0]:
                stats["total"] = len(messages[0].split())

            # Unread messages
            status, messages = self._imap.search(None, "UNSEEN")
            if status == "OK" and messages[0]:
                stats["unread"] = len(messages[0].split())

        except Exception as e:
            self._last_error = str(e)

        return stats

    def search_emails(
        self,
        query: str,
        folder: str = "inbox",
        max_results: int = 500
    ) -> List[EmailMessage]:
        """
        Search for emails in Yahoo Mail.

        Args:
            query: IMAP search query (e.g., 'FROM "newsletter@"')
            folder: Folder to search in
            max_results: Maximum results to return

        Returns:
            List of EmailMessage objects
        """
        messages = []

        if not self._imap:
            return messages

        try:
            # Map folder name
            yahoo_folder = self.normalize_folder(folder)

            status, _ = self._imap.select(yahoo_folder, readonly=True)
            if status != "OK":
                return messages

            # Execute search
            status, data = self._imap.search(None, query)
            if status != "OK":
                return messages

            message_ids = data[0].split()[:max_results]

            # Fetch message headers
            for msg_id in message_ids:
                try:
                    status, msg_data = self._imap.fetch(msg_id, "(RFC822.HEADER)")
                    if status != "OK":
                        continue

                    raw_email = msg_data[0][1]
                    msg = email.message_from_bytes(raw_email)

                    # Decode headers
                    subject = self._decode_header(msg.get("Subject", ""))
                    from_addr = self._decode_header(msg.get("From", ""))
                    to_addr = self._decode_header(msg.get("To", ""))
                    date_str = msg.get("Date", "")

                    # Parse date
                    try:
                        date = email.utils.parsedate_to_datetime(date_str)
                    except:
                        date = datetime.now()

                    messages.append(EmailMessage(
                        id=msg_id.decode(),
                        provider=self.PROVIDER_NAME,
                        from_address=from_addr,
                        to_address=to_addr,
                        subject=subject[:200],
                        date=date,
                    ))

                except Exception:
                    continue

        except Exception as e:
            self._last_error = str(e)

        return messages

    def move_to_trash(self, message_ids: List[str]) -> Tuple[int, int]:
        """Move messages to Trash folder."""
        success = 0
        errors = 0

        if not self._imap:
            return 0, len(message_ids)

        try:
            trash_folder = self.FOLDER_MAP["trash"]

            for msg_id in message_ids:
                try:
                    # Copy to Trash
                    status, _ = self._imap.copy(msg_id.encode(), trash_folder)
                    if status == "OK":
                        # Mark original as deleted
                        self._imap.store(msg_id.encode(), "+FLAGS", "\\Deleted")
                        success += 1
                    else:
                        errors += 1
                except:
                    errors += 1

            # Expunge deleted messages
            self._imap.expunge()

        except Exception as e:
            self._last_error = str(e)
            errors = len(message_ids) - success

        return success, errors

    def get_folders(self) -> List[str]:
        """Get list of available folders."""
        folders = []

        if not self._imap:
            return folders

        try:
            status, folder_list = self._imap.list()
            if status != "OK":
                return folders

            for folder_data in folder_list:
                if isinstance(folder_data, bytes):
                    decoded = folder_data.decode()
                    match = re.search(r'"/" "?([^"]+)"?$', decoded)
                    if match:
                        folder_name = match.group(1).strip('"')
                        folders.append(folder_name)

        except Exception as e:
            self._last_error = str(e)

        return folders

    # =========================================================================
    # Optional Method Overrides
    # =========================================================================

    def move_to_archive(self, message_ids: List[str]) -> Tuple[int, int]:
        """Move messages to Archive folder."""
        success = 0
        errors = 0

        if not self._imap:
            return 0, len(message_ids)

        try:
            archive_folder = self.FOLDER_MAP["archive"]

            for msg_id in message_ids:
                try:
                    status, _ = self._imap.copy(msg_id.encode(), archive_folder)
                    if status == "OK":
                        self._imap.store(msg_id.encode(), "+FLAGS", "\\Deleted")
                        success += 1
                    else:
                        errors += 1
                except:
                    errors += 1

            self._imap.expunge()

        except Exception as e:
            self._last_error = str(e)

        return success, errors

    def mark_as_spam(self, message_ids: List[str]) -> Tuple[int, int]:
        """Move messages to Bulk Mail (spam) folder."""
        success = 0
        errors = 0

        if not self._imap:
            return 0, len(message_ids)

        try:
            spam_folder = self.FOLDER_MAP["spam"]  # "Bulk Mail"

            for msg_id in message_ids:
                try:
                    status, _ = self._imap.copy(msg_id.encode(), spam_folder)
                    if status == "OK":
                        self._imap.store(msg_id.encode(), "+FLAGS", "\\Deleted")
                        success += 1
                    else:
                        errors += 1
                except:
                    errors += 1

            self._imap.expunge()

        except Exception as e:
            self._last_error = str(e)

        return success, errors

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def normalize_folder(self, folder: str) -> str:
        """Convert internal folder name to Yahoo folder name."""
        return self.FOLDER_MAP.get(folder.lower(), folder)

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
# Utility Functions
# =============================================================================

def is_yahoo_email(email_address: str) -> bool:
    """Check if email is a Yahoo/AOL domain."""
    yahoo_domains = [
        "yahoo.com", "yahoo.co.uk", "yahoo.ca", "yahoo.com.au",
        "yahoo.co.in", "yahoo.co.jp", "yahoo.de", "yahoo.fr",
        "ymail.com", "rocketmail.com",
        "aol.com", "aim.com",
        "att.net", "sbcglobal.net", "bellsouth.net",
    ]
    domain = email_address.lower().split("@")[-1]
    return domain in yahoo_domains


def validate_app_password(password: str) -> Tuple[bool, str]:
    """
    Validate Yahoo App Password format.

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
