"""
Base Connector - Abstract base class for all email providers
=============================================================

All provider connectors (Yahoo, Outlook, AOL, etc.) inherit from this class.
This ensures consistent interface across all providers.

Author: MailRemover Team
Version: 2.1.0
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum


class AuthMethod(Enum):
    """Authentication methods supported by providers."""
    OAUTH2 = "oauth2"
    APP_PASSWORD = "app_password"


class ConnectionStatus(Enum):
    """Connection status states."""
    ACTIVE = "active"
    REAUTH_REQUIRED = "reauth_required"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class ConnectionResult:
    """Result of a connection test or operation."""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


@dataclass
class EmailMessage:
    """Standardized email message representation."""
    id: str
    provider: str
    from_address: str
    to_address: str
    subject: str
    date: datetime
    snippet: Optional[str] = None
    labels: Optional[List[str]] = None
    size_bytes: Optional[int] = None


@dataclass
class ProviderInfo:
    """Provider configuration and metadata."""
    name: str
    display_name: str
    color: str  # Hex color for UI
    icon: str  # Icon name or URL
    auth_method: AuthMethod
    imap_host: Optional[str] = None
    imap_port: Optional[int] = None
    smtp_host: Optional[str] = None
    smtp_port: Optional[int] = None


class BaseConnector(ABC):
    """
    Abstract base class for email provider connectors.

    All provider-specific connectors must implement these methods
    to ensure consistent behavior across the application.
    """

    # Provider metadata - override in subclasses
    PROVIDER_NAME: str = "base"
    DISPLAY_NAME: str = "Base Provider"
    COLOR: str = "#808080"
    ICON: str = "mail"
    AUTH_METHOD: AuthMethod = AuthMethod.OAUTH2

    def __init__(self, email: str, credentials: str):
        """
        Initialize connector with credentials.

        Args:
            email: User's email address for this provider
            credentials: Encrypted credential string (OAuth token or App Password)
        """
        self.email = email
        self._credentials = credentials  # Keep encrypted
        self._connection = None
        self._last_error: Optional[str] = None

    @property
    def provider_info(self) -> ProviderInfo:
        """Get provider metadata."""
        return ProviderInfo(
            name=self.PROVIDER_NAME,
            display_name=self.DISPLAY_NAME,
            color=self.COLOR,
            icon=self.ICON,
            auth_method=self.AUTH_METHOD,
        )

    @property
    def last_error(self) -> Optional[str]:
        """Get the last error message."""
        return self._last_error

    # =========================================================================
    # Abstract Methods - Must be implemented by subclasses
    # =========================================================================

    @abstractmethod
    def test_connection(self) -> ConnectionResult:
        """
        Test if the credentials are valid and connection works.

        Returns:
            ConnectionResult with success status and message
        """
        pass

    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the email provider.

        Returns:
            True if connection successful
        """
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Close the connection to the provider."""
        pass

    @abstractmethod
    def get_inbox_stats(self) -> Dict[str, int]:
        """
        Get inbox statistics.

        Returns:
            Dict with 'total', 'unread', and optionally other counts
        """
        pass

    @abstractmethod
    def search_emails(
        self,
        query: str,
        folder: str = "inbox",
        max_results: int = 500
    ) -> List[EmailMessage]:
        """
        Search for emails matching a query.

        Args:
            query: Search query (provider-specific format)
            folder: Folder to search in
            max_results: Maximum number of results

        Returns:
            List of EmailMessage objects
        """
        pass

    @abstractmethod
    def move_to_trash(self, message_ids: List[str]) -> Tuple[int, int]:
        """
        Move messages to trash folder.

        Args:
            message_ids: List of message IDs to trash

        Returns:
            Tuple of (success_count, error_count)
        """
        pass

    @abstractmethod
    def get_folders(self) -> List[str]:
        """
        Get list of available folders/labels.

        Returns:
            List of folder names
        """
        pass

    # =========================================================================
    # Optional Methods - Override if provider supports these features
    # =========================================================================

    def move_to_archive(self, message_ids: List[str]) -> Tuple[int, int]:
        """
        Move messages to archive folder.
        Default implementation moves to archive if available.

        Returns:
            Tuple of (success_count, error_count)
        """
        # Default: not supported
        return 0, len(message_ids)

    def mark_as_spam(self, message_ids: List[str]) -> Tuple[int, int]:
        """
        Mark messages as spam.

        Returns:
            Tuple of (success_count, error_count)
        """
        # Default: not supported
        return 0, len(message_ids)

    def permanently_delete(self, message_ids: List[str]) -> Tuple[int, int]:
        """
        Permanently delete messages (use with caution).

        Returns:
            Tuple of (success_count, error_count)
        """
        # Default: not supported for safety
        return 0, len(message_ids)

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def normalize_folder(self, folder: str) -> str:
        """
        Convert internal folder name to provider-specific name.
        Override in subclasses if provider uses different names.

        Args:
            folder: Internal folder name (inbox, spam, trash, etc.)

        Returns:
            Provider-specific folder name
        """
        return folder.capitalize()

    def __enter__(self):
        """Context manager entry - establishes connection."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - closes connection."""
        self.disconnect()

    def __repr__(self):
        return f"<{self.__class__.__name__}(email='{self.email}')>"


# =============================================================================
# Helper function for connector implementations
# =============================================================================

def format_search_query(
    from_address: Optional[str] = None,
    subject: Optional[str] = None,
    older_than_days: Optional[int] = None,
    has_attachment: Optional[bool] = None,
    is_unread: Optional[bool] = None,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Build a standardized search query dict.
    Connectors can convert this to their native format.
    """
    query = {}
    if from_address:
        query['from'] = from_address
    if subject:
        query['subject'] = subject
    if older_than_days:
        query['older_than_days'] = older_than_days
    if has_attachment is not None:
        query['has_attachment'] = has_attachment
    if is_unread is not None:
        query['is_unread'] = is_unread
    if label:
        query['label'] = label
    return query
