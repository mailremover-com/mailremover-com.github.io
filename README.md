# MailRemover Web Application

Flask-based web application for cleaning Gmail inboxes.

---

## Quick Start Commands

### 1. Install Dependencies

```bash
# SSH into your VM
ssh user@your-vm-ip

# Navigate to web_app directory
cd /path/to/web_app

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Create credentials.json

Create the file `credentials.json` in the `web_app` directory:

```bash
nano credentials.json
```

Paste this structure (fill in your values from Google Cloud Console):

```json
{
  "web": {
    "client_id": "YOUR_CLIENT_ID.apps.googleusercontent.com",
    "client_secret": "YOUR_CLIENT_SECRET",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["https://mailremover.com/callback"]
  }
}
```

### 3. Set Environment Variables

```bash
# Generate a secret key
export FLASK_SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")

# Set redirect URI (must match Google Cloud Console exactly)
export OAUTH_REDIRECT_URI="https://mailremover.com/callback"
```

### 4. Run the Application

**Development (testing):**
```bash
python app.py
```

**Production (with Gunicorn):**
```bash
gunicorn -b 127.0.0.1:8000 -w 2 app:app
```

---

## Google Cloud Console Setup

### Step 1: Create OAuth Client ID

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project
3. Navigate to **APIs & Services** → **Credentials**
4. Click **+ CREATE CREDENTIALS** → **OAuth client ID**
5. Select **Web application**
6. Configure:
   - **Name**: MailRemover Web
   - **Authorized JavaScript origins**: `https://mailremover.com`
   - **Authorized redirect URIs**: `https://mailremover.com/callback`
7. Click **Create**
8. Copy the **Client ID** and **Client Secret**

### Step 2: Update credentials.json

Replace the placeholder values:

```json
{
  "web": {
    "client_id": "123456789-abcdefg.apps.googleusercontent.com",
    "client_secret": "GOCSPX-your-secret-here",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "redirect_uris": ["https://mailremover.com/callback"]
  }
}
```

### Step 3: Configure OAuth Consent Screen

1. Go to **APIs & Services** → **OAuth consent screen**
2. Ensure these are set:
   - **App name**: MailRemover
   - **User support email**: Your email
   - **App logo**: (optional)
   - **Application home page**: `https://mailremover.com`
   - **Privacy policy**: `https://mailremover.com/privacy`
   - **Authorized domains**: `mailremover.com`
3. Add scope: `https://www.googleapis.com/auth/gmail.modify`

---

## Nginx Configuration

If using Nginx as reverse proxy:

```nginx
server {
    listen 443 ssl;
    server_name mailremover.com;

    ssl_certificate /etc/letsencrypt/live/mailremover.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mailremover.com/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 80;
    server_name mailremover.com;
    return 301 https://$server_name$request_uri;
}
```

Reload Nginx:
```bash
sudo nginx -t && sudo systemctl reload nginx
```

---

## Running as a Service (systemd)

Create `/etc/systemd/system/mailremover.service`:

```ini
[Unit]
Description=MailRemover Web Application
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/path/to/web_app
Environment="FLASK_SECRET_KEY=your-secret-key-here"
Environment="OAUTH_REDIRECT_URI=https://mailremover.com/callback"
ExecStart=/path/to/web_app/venv/bin/gunicorn -b 127.0.0.1:8000 -w 2 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mailremover
sudo systemctl start mailremover
sudo systemctl status mailremover
```

---

## Troubleshooting

### "redirect_uri_mismatch" Error

The redirect URI in your code must **exactly match** what's in Google Cloud Console.

Check:
1. `OAUTH_REDIRECT_URI` environment variable
2. `redirect_uris` in credentials.json
3. **Authorized redirect URIs** in Google Cloud Console

All three must be identical: `https://mailremover.com/callback`

### "Access blocked: This app's request is invalid"

Usually means:
- Missing or mismatched `client_id`
- Wrong OAuth client type (must be "Web application", not "Desktop")

### Session Issues

If login doesn't persist:
```bash
# Make sure FLASK_SECRET_KEY is set and consistent
export FLASK_SECRET_KEY="a-long-random-string-that-stays-the-same"
```

---

## File Structure

```
web_app/
├── app.py              # Main Flask application
├── credentials.json    # Google OAuth credentials (DO NOT COMMIT)
├── requirements.txt    # Python dependencies
├── README.md          # This file
└── templates/
    ├── index.html     # Login page
    ├── dashboard.html # Main dashboard
    └── error.html     # Error page
```

---

## Security Notes

- **Never commit credentials.json** to git
- Use HTTPS in production (required for OAuth)
- Set a strong `FLASK_SECRET_KEY`
- Consider adding rate limiting for production
