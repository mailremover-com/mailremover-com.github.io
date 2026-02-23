-- ============================================================================
-- Migration: Normalized Email Accounts Table (Multi-Provider Support)
-- Version: 002
-- Date: 2026-01-14
-- Description: Creates a dedicated table for email provider connections
--              Supports Gmail, Yahoo, Outlook, and future providers
-- ============================================================================

-- Drop the Yahoo columns we just added (moving to normalized table)
-- Note: SQLite doesn't support DROP COLUMN easily, so we'll just leave them
-- and deprecate their use. New code will use email_accounts table.

-- Create the normalized email_accounts table
CREATE TABLE IF NOT EXISTS email_accounts (
    id TEXT PRIMARY KEY,  -- UUID as TEXT for SQLite
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Provider identification
    provider TEXT NOT NULL CHECK(provider IN ('gmail', 'yahoo', 'outlook', 'icloud', 'aol')),
    email TEXT NOT NULL,
    display_name TEXT,  -- User-friendly name like "Work Yahoo" or "Personal Gmail"

    -- Encrypted credentials
    -- For OAuth: stores encrypted refresh_token
    -- For App Password: stores encrypted app_password
    encrypted_key TEXT,
    auth_method TEXT NOT NULL CHECK(auth_method IN ('oauth2', 'app_password')) DEFAULT 'oauth2',

    -- Connection status
    status TEXT NOT NULL CHECK(status IN ('active', 'reauth_required', 'disconnected', 'error')) DEFAULT 'active',
    last_error TEXT,  -- Store last error message for troubleshooting

    -- Sync tracking
    last_sync_at TIMESTAMP,
    emails_cleaned INTEGER DEFAULT 0,  -- Total emails cleaned via this account

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Ensure unique provider+email per user
    UNIQUE(user_id, provider, email)
);

-- Create indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_email_accounts_user ON email_accounts(user_id);
CREATE INDEX IF NOT EXISTS idx_email_accounts_provider ON email_accounts(provider);
CREATE INDEX IF NOT EXISTS idx_email_accounts_status ON email_accounts(status);
CREATE INDEX IF NOT EXISTS idx_email_accounts_active ON email_accounts(user_id, status)
    WHERE status = 'active';

-- ============================================================================
-- Provider Configuration Table (for future extensibility)
-- ============================================================================

CREATE TABLE IF NOT EXISTS provider_config (
    provider TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    icon_url TEXT,
    color TEXT,  -- Hex color for UI
    auth_method TEXT NOT NULL,  -- 'oauth2' or 'app_password'
    imap_host TEXT,
    imap_port INTEGER,
    smtp_host TEXT,
    smtp_port INTEGER,
    is_active BOOLEAN DEFAULT TRUE,  -- Can disable providers
    setup_instructions TEXT,  -- Markdown instructions for users
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insert default provider configurations
INSERT OR IGNORE INTO provider_config (provider, display_name, color, auth_method, imap_host, imap_port, smtp_host, smtp_port, setup_instructions) VALUES
    ('gmail', 'Gmail', '#EA4335', 'oauth2', 'imap.gmail.com', 993, 'smtp.gmail.com', 587, 'Connect securely with your Google account.'),
    ('yahoo', 'Yahoo Mail', '#6001D2', 'app_password', 'imap.mail.yahoo.com', 993, 'smtp.mail.yahoo.com', 465, 'Generate an App Password at account.yahoo.com/security'),
    ('outlook', 'Outlook', '#0078D4', 'oauth2', 'outlook.office365.com', 993, 'smtp.office365.com', 587, 'Connect with your Microsoft account.'),
    ('aol', 'AOL Mail', '#31459B', 'app_password', 'imap.aol.com', 993, 'smtp.aol.com', 465, 'Generate an App Password at login.aol.com/account/security'),
    ('icloud', 'iCloud Mail', '#A2AAAD', 'app_password', 'imap.mail.me.com', 993, 'smtp.mail.me.com', 587, 'Generate an App-Specific Password at appleid.apple.com');

-- ============================================================================
-- Verification queries (run after migration)
-- ============================================================================
-- SELECT * FROM email_accounts;
-- SELECT * FROM provider_config;
