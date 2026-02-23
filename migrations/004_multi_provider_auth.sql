-- ============================================================================
-- Migration 004: Multi-Provider Authentication Schema
-- Version: 2.2.0
-- Date: 2026-01-14
-- Description: Adds provider_type, provider_id, and encrypted token storage
--              Zero-downtime: Existing Google users remain active
-- ============================================================================

-- Add provider_type column (defaults to 'google' for existing users)
ALTER TABLE users ADD COLUMN provider_type TEXT DEFAULT 'google';

-- Add provider_id (provider-specific unique identifier)
ALTER TABLE users ADD COLUMN provider_id TEXT;

-- Add encrypted token storage columns
ALTER TABLE users ADD COLUMN oauth_access_token_encrypted TEXT;
ALTER TABLE users ADD COLUMN oauth_refresh_token_encrypted TEXT;
ALTER TABLE users ADD COLUMN oauth_token_expires_at TIMESTAMP;
ALTER TABLE users ADD COLUMN oauth_scopes TEXT;

-- Add provider metadata
ALTER TABLE users ADD COLUMN provider_email TEXT;
ALTER TABLE users ADD COLUMN provider_display_name TEXT;
ALTER TABLE users ADD COLUMN provider_avatar_url TEXT;

-- Create index for provider lookups
CREATE INDEX IF NOT EXISTS idx_users_provider_type ON users(provider_type);
CREATE INDEX IF NOT EXISTS idx_users_provider_id ON users(provider_id);

-- Create unique constraint for provider_type + provider_id combination
-- This allows same email across different providers
CREATE UNIQUE INDEX IF NOT EXISTS idx_users_provider_unique
ON users(provider_type, provider_id) WHERE provider_id IS NOT NULL;

-- Update existing users to have provider_type = 'google'
UPDATE users SET provider_type = 'google' WHERE provider_type IS NULL;

-- ============================================================================
-- Verification Queries (run after migration)
-- ============================================================================
-- SELECT provider_type, COUNT(*) FROM users GROUP BY provider_type;
-- PRAGMA table_info(users);
