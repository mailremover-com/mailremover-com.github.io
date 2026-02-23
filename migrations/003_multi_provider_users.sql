-- ============================================================================
-- Migration: Multi-Provider User Authentication Support
-- Version: 003
-- Date: 2026-01-14
-- Description: Adds columns to users table for multi-provider OAuth support
--              Stores encrypted access/refresh tokens and provider metadata
-- ============================================================================

-- Add columns for multi-provider support
ALTER TABLE users ADD COLUMN initial_provider TEXT DEFAULT 'gmail';
ALTER TABLE users ADD COLUMN provider_id TEXT;  -- Provider-specific user ID
ALTER TABLE users ADD COLUMN display_name TEXT;  -- User's display name from provider
ALTER TABLE users ADD COLUMN access_token_encrypted TEXT;  -- Encrypted OAuth access token
ALTER TABLE users ADD COLUMN refresh_token_encrypted TEXT;  -- Encrypted OAuth refresh token
ALTER TABLE users ADD COLUMN token_expires_at TIMESTAMP;  -- Token expiration time
ALTER TABLE users ADD COLUMN last_provider_sync TIMESTAMP;  -- Last sync with provider

-- Create index for provider lookups
CREATE INDEX IF NOT EXISTS idx_users_initial_provider ON users(initial_provider);
CREATE INDEX IF NOT EXISTS idx_users_provider_id ON users(provider_id);

-- ============================================================================
-- Verification query (run after migration)
-- ============================================================================
-- SELECT sql FROM sqlite_master WHERE type='table' AND name='users';
