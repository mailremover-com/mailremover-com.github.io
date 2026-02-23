#!/bin/bash
# ============================================================================
# Multi-Provider Integration Deployment Script
# ============================================================================
# Run this script on GoldenSignal to deploy multi-provider architecture
# Usage: bash scripts/deploy_yahoo.sh
# ============================================================================

set -e

VM_HOST="ray@136.115.158.48"
REMOTE_PATH="/var/www/mailremover"

echo "========================================"
echo "  Multi-Provider v2.1.0 Deployment"
echo "========================================"

# Step 1: Sync files to production
echo ""
echo "[1/5] Syncing files to production server..."
deploy

# Step 2: Install cryptography dependency on server
echo ""
echo "[2/5] Installing cryptography package on server..."
ssh $VM_HOST "cd $REMOTE_PATH && source venv/bin/activate && pip install cryptography --quiet"

# Step 3: Run database migration 001 (if not already applied)
echo ""
echo "[3/5] Running database migration 001..."
ssh $VM_HOST "cd $REMOTE_PATH && sqlite3 mailremover.db < migrations/001_add_yahoo_columns.sql 2>/dev/null || echo 'Migration 001 already applied'"

# Step 4: Run database migration 002 (email_accounts table)
echo ""
echo "[4/5] Running database migration 002 (email_accounts table)..."
ssh $VM_HOST "cd $REMOTE_PATH && sqlite3 mailremover.db < migrations/002_email_accounts_table.sql 2>/dev/null || echo 'Migration 002 already applied'"

# Verify migrations
echo "    Verifying email_accounts table..."
ssh $VM_HOST "cd $REMOTE_PATH && sqlite3 mailremover.db \"SELECT name FROM sqlite_master WHERE type='table' AND name='email_accounts';\" | grep email_accounts && echo '    email_accounts table created successfully'"

# Step 5: Fix permissions and restart service
echo ""
echo "[5/5] Fixing permissions and restarting service..."
ssh $VM_HOST "sudo chown -R rphister:www-data $REMOTE_PATH && sudo chmod -R 775 $REMOTE_PATH && sudo systemctl restart mailremover"

# Verify service
echo ""
echo "Verifying service status..."
ssh $VM_HOST "sudo systemctl is-active mailremover"

echo ""
echo "========================================"
echo "  Deployment Complete! v2.1.0"
echo "========================================"
echo ""
echo "New files deployed:"
echo "  - connectors/base_connector.py (abstract base class)"
echo "  - connectors/yahoo_connector.py (Yahoo IMAP integration)"
echo "  - migrations/002_email_accounts_table.sql"
echo "  - version.json"
echo "  - Updated dashboard.html (Provider Strip + version footer)"
echo "  - Updated crypto_utils.py (multi-provider support)"
echo ""
echo "Features added:"
echo "  - Provider Strip UI in sidebar (Gmail/Yahoo/Outlook)"
echo "  - Version display in footer (v2.1.0)"
echo "  - Normalized email_accounts table"
echo "  - BaseConnector architecture for extensibility"
echo ""
