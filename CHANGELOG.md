# MailRemover Changelog

All notable changes to MailRemover are documented in this file.

Format: [Semantic Versioning](https://semver.org/)

---

## [2.2.0] "Sovereign Entry" - 2026-01-14

### Added
- **Sovereign Entry**: Unified multi-provider login (`/auth/login/<provider>`)
- **Dedicated Login Page**: `login.html` with responsive three-button layout
- **Microsoft OAuth2**: Full OAuth2/OpenID Connect via `/common` endpoint
  - Supports: Outlook.com, Hotmail.com, Live.com, Microsoft 365
- **Provider-Aware Theming**: CSS variables that change accent colors
  - Google: `#4285F4` (official Google blue)
  - Yahoo: `#6001d2` (Yahoo purple)
  - Microsoft: `#f25022` (Microsoft red/gradient)
- **User Display Names**: Personalized greetings using provider profile data
- **Unified Auth Callback**: `/auth/<provider>/callback` with provider-specific parsing
- **What's New Modal**: Auto-displays on first visit to new version

### Database (Migration 004)
- `provider_type` - User's auth provider (google, yahoo, microsoft)
- `provider_id` - Provider-specific unique identifier
- `oauth_access_token_encrypted` - Fernet-encrypted access token
- `oauth_refresh_token_encrypted` - Fernet-encrypted refresh token
- `oauth_token_expires_at` - Token expiration timestamp
- Unique constraint on `(provider_type, provider_id)`

### Security
- All OAuth tokens encrypted with Fernet (via `crypto_utils.py`) before DB storage
- Dynamic `redirect_uri` generation for dev/prod environments
- CSRF state tokens per provider (`oauth_state_{provider}`)

### Technical
- New module: `auth_providers.py` with provider configs and parsers
- Routes: `/auth/login/<provider>`, `/auth/<provider>/callback`, `/login-page`
- Microsoft Graph API userinfo parsing (handles personal account formats)
- Yahoo OAuth2 gracefully falls back to App Password flow (OAuth restricted 2026)
- Zero-downtime migration: Existing Google users remain active

---

## [2.1.0] - 2026-01-14

### Added
- **Yahoo Mail Support**: IMAP integration via App Passwords
- **Multi-Provider Architecture**: BaseConnector abstract class for extensibility
- **Provider Strip UI**: Sidebar icons showing connected accounts (Gmail/Yahoo/Outlook)
- **Homemail Teaser**: CSS firework animation for upcoming feature
- **Version Footer**: Dynamic version display fetched from `/version.json`
- **Provider Choice Login**: Three-button login interface on landing page

### Database
- `email_accounts` table for normalized multi-provider storage
- `provider_config` table with provider metadata

### Security
- AES-256 encryption for credential storage via `crypto_utils.py`
- Yahoo App Password validation and secure storage

---

## [2.0.0] - 2026-01-13

### Added
- **Secure Sign-Out**: Renamed from "Wipe All Session Data" to reduce anxiety
- **Safety Vault**: UI section explaining temporary data storage
- **Security Promise**: Footer explaining "We never delete your emails"
- **Yahoo R&D**: Research confirming App Password approach (OAuth2 restricted)

### Changed
- Dashboard copy updated to emphasize data safety
- Suggestion box improved with better UX

---

## [1.x.x] - Previous Releases

### Core Features
- Gmail OAuth2 authentication
- Smart email scanning with Gmail search syntax
- Batch move to trash (up to 600 emails per batch)
- Practice Mode for safe exploration
- Protected Keywords system
- Sender grouping and analysis
- Real-time inbox statistics
- Stripe integration for subscriptions

### Subscription Tiers
- Free: Limited monthly deletes
- Maintenance ($5/mo): Unlimited organizing
- Lifetime: One-time unlimited access
- Purge: 7-day intensive cleaning pass

---

## Deployment Notes

### Environment Variables Required
```bash
# Google OAuth
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=

# Microsoft OAuth (for Outlook)
MICROSOFT_CLIENT_ID=
MICROSOFT_CLIENT_SECRET=
MICROSOFT_REDIRECT_URI=https://mailremover.com/callback/outlook

# Encryption
MAILREMOVER_ENCRYPTION_KEY=

# Stripe
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
```

### Migration Commands
```bash
# Run all migrations
sqlite3 mailremover.db < migrations/001_add_yahoo_columns.sql
sqlite3 mailremover.db < migrations/002_email_accounts_table.sql
sqlite3 mailremover.db < migrations/003_multi_provider_users.sql
```

---

*This changelog is automatically updated with each deployment.*
