-- ============================================================================
-- Migration: Add Yahoo Mail Support
-- Version: 001
-- Date: 2026-01-14
-- Description: Adds columns for Yahoo Mail integration with encrypted credentials
-- ============================================================================

-- Add Yahoo email column
ALTER TABLE users ADD COLUMN yahoo_email VARCHAR(255);

-- Add encrypted App Password storage
ALTER TABLE users ADD COLUMN yahoo_app_password_encrypted TEXT;

-- Add connection timestamp
ALTER TABLE users ADD COLUMN yahoo_connected_at TIMESTAMP;

-- Add last sync timestamp for Yahoo
ALTER TABLE users ADD COLUMN yahoo_last_sync TIMESTAMP;

-- Create index for Yahoo email lookups
CREATE INDEX IF NOT EXISTS idx_users_yahoo_email ON users(yahoo_email);

-- ============================================================================
-- Optional: Multi-provider support table (for future expansion)
-- Uncomment if you want to support multiple email accounts per user
-- ============================================================================

/*
CREATE TABLE IF NOT EXISTS email_providers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    provider VARCHAR(50) NOT NULL,  -- 'google', 'yahoo', 'outlook', 'icloud'
    provider_email VARCHAR(255) NOT NULL,
    credentials_encrypted TEXT NOT NULL,
    auth_method VARCHAR(50) DEFAULT 'oauth2',  -- 'oauth2', 'app_password'
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_sync TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    sync_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, provider, provider_email)
);

CREATE INDEX idx_email_providers_user ON email_providers(user_id);
CREATE INDEX idx_email_providers_active ON email_providers(is_active) WHERE is_active = TRUE;
*/

-- ============================================================================
-- Verification query (run after migration)
-- ============================================================================
-- SELECT sql FROM sqlite_master WHERE type='table' AND name='users';
