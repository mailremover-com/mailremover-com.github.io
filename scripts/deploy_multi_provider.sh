#!/bin/bash
# ============================================================================
# Multi-Provider Integration Deployment Script
# ============================================================================
# Run this script on GoldenSignal to deploy multi-provider architecture
# Usage: bash scripts/deploy_multi_provider.sh
# ============================================================================

set -e

VM_HOST="ray@136.115.158.48"
REMOTE_PATH="/var/www/mailremover"

echo "========================================"
echo "  Multi-Provider v2.2.0 Deployment"
echo "========================================"

# Step 1: Sync files to production
echo ""
echo "[1/6] Syncing files to production server..."
deploy

# Step 2: Install cryptography dependency on server
echo ""
echo "[2/6] Installing cryptography package on server..."
ssh $VM_HOST "cd $REMOTE_PATH && source venv/bin/activate && pip install cryptography --quiet"

# Step 3: Run database migration 001 (if not already applied)
echo ""
echo "[3/6] Running database migration 001..."
ssh $VM_HOST "cd $REMOTE_PATH && sqlite3 mailremover.db < migrations/001_add_yahoo_columns.sql 2>/dev/null || echo 'Migration 001 already applied'"

# Step 4: Run database migration 002 (email_accounts table)
echo ""
echo "[4/6] Running database migration 002 (email_accounts table)..."
ssh $VM_HOST "cd $REMOTE_PATH && sqlite3 mailremover.db < migrations/002_email_accounts_table.sql 2>/dev/null || echo 'Migration 002 already applied'"

# Step 5: Run database migration 003 (provider tokens)
echo ""
echo "[5/6] Running database migration 003 (provider tokens)..."
ssh $VM_HOST "cd $REMOTE_PATH && sqlite3 mailremover.db < migrations/003_multi_provider_users.sql 2>/dev/null || echo 'Migration 003 already applied'"

# Verify migrations
echo "    Verifying email_accounts table..."
ssh $VM_HOST "cd $REMOTE_PATH && sqlite3 mailremover.db \"SELECT name FROM sqlite_master WHERE type='table' AND name='email_accounts';\" | grep email_accounts && echo '    email_accounts table created successfully'"

# Step 6: Fix permissions and restart service
echo ""
echo "[6/6] Fixing permissions and restarting service..."
ssh $VM_HOST "sudo chown -R rphister:www-data $REMOTE_PATH && sudo chmod -R 775 $REMOTE_PATH && sudo systemctl restart mailremover"

# Verify service
echo ""
echo "Verifying service status..."
ssh $VM_HOST "sudo systemctl is-active mailremover"

echo ""
echo "========================================"
echo "  Multi-Provider Deployment Complete! v2.2.0"
echo "========================================"
echo ""
echo "New files deployed:"
echo "  - connectors/base_connector.py (abstract base class)"
echo "  - connectors/yahoo_connector.py (Yahoo IMAP integration)"
echo "  - connectors/outlook_connector.py (Microsoft OAuth2 integration)"
echo "  - migrations/003_provider_tokens.sql"
echo "  - version.json (v2.2.0)"
echo "  - Updated dashboard.html (Provider theming + welcome greeting)"
echo "  - Updated crypto_utils.py (multi-provider support)"
echo ""
echo "Features added:"
echo "  - Sovereign Entry: Multi-provider login"
echo "  - Microsoft OAuth2 integration"
echo "  - Provider-aware theming (Gmail/Yahoo/Outlook)"
echo "  - Enhanced user profile support"
echo "  - Database schema for provider tokens"
echo ""
