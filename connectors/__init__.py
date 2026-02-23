"""
Email Provider Connectors
=========================

Modular connector system for multi-provider email support.

Supported Providers:
- Gmail (OAuth2)
- Yahoo (App Password + IMAP)
- Outlook (Microsoft Graph API) - Coming Soon
- AOL (App Password + IMAP) - Coming Soon
- iCloud (App-Specific Password + IMAP) - Coming Soon
"""

from .base_connector import BaseConnector, ConnectionResult
from .yahoo_connector import YahooConnector

# Provider registry - add new connectors here
CONNECTORS = {
    'yahoo': YahooConnector,
    # 'outlook': OutlookConnector,  # Coming soon
    # 'aol': AOLConnector,          # Coming soon
}


def get_connector(provider: str) -> type:
    """Get the connector class for a provider."""
    connector = CONNECTORS.get(provider.lower())
    if not connector:
        raise ValueError(f"Unknown provider: {provider}. Available: {list(CONNECTORS.keys())}")
    return connector


def create_connector(provider: str, email: str, credentials: str) -> BaseConnector:
    """Factory function to create a connector instance."""
    connector_class = get_connector(provider)
    return connector_class(email, credentials)


__all__ = [
    'BaseConnector',
    'ConnectionResult',
    'YahooConnector',
    'get_connector',
    'create_connector',
    'CONNECTORS',
]
