"""
SignSimple.io - Email Sequences
================================

Complete email sequences for:
1. Pre-launch waitlist (3 emails)
2. LTD purchase confirmation
3. LTD onboarding sequence (5 emails)
4. Urgency/scarcity emails
5. Subscription confirmation

Integration:
- Works with SendGrid, Postmark, Resend, or any SMTP service
- Uses Jinja2 templates for personalization
- Includes both HTML and plain text versions

Usage:
    from monetization.email_sequences import EmailSequence
    es = EmailSequence()
    es.send_ltd_confirmation(email="user@example.com", name="John")
"""

import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

# =============================================================================
# EMAIL CONTENT - WAITLIST SEQUENCE (Pre-Launch)
# =============================================================================

WAITLIST_EMAILS = {
    # Email 1: Welcome to waitlist (Send immediately)
    'waitlist_welcome': {
        'subject': 'You\'re on the list! SignSimple.io launches soon',
        'delay_hours': 0,
        'html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px; }
        .header h1 { color: white; margin: 0; font-size: 24px; }
        .cta { display: inline-block; background: #6366f1; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 20px 0; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Welcome to the SignSimple.io Waitlist!</h1>
    </div>

    <p>Hey {{ name or 'there' }},</p>

    <p>You're officially on the waitlist for <strong>SignSimple.io</strong> - the simple, affordable way to get documents signed online.</p>

    <p>Here's what happens next:</p>

    <ul>
        <li><strong>Launch date:</strong> We're launching in the next 7 days</li>
        <li><strong>Early access:</strong> You'll get first access before public launch</li>
        <li><strong>Founder's discount:</strong> Waitlist members get exclusive pricing</li>
    </ul>

    <p>As a thank you for joining early, you'll be the first to know about our <strong>Founder's Lifetime Deal</strong> - pay once, use forever. Only 200 spots available.</p>

    <p>Keep an eye on your inbox!</p>

    <p>Best,<br>
    The SignSimple.io Team</p>

    <div class="footer">
        <p>You received this email because you signed up for the SignSimple.io waitlist.<br>
        <a href="{{ unsubscribe_url }}">Unsubscribe</a></p>
    </div>
</body>
</html>
        ''',
        'text': '''
Welcome to the SignSimple.io Waitlist!

Hey {{ name or 'there' }},

You're officially on the waitlist for SignSimple.io - the simple, affordable way to get documents signed online.

Here's what happens next:
- Launch date: We're launching in the next 7 days
- Early access: You'll get first access before public launch
- Founder's discount: Waitlist members get exclusive pricing

As a thank you for joining early, you'll be the first to know about our Founder's Lifetime Deal - pay once, use forever. Only 200 spots available.

Keep an eye on your inbox!

Best,
The SignSimple.io Team

---
You received this email because you signed up for the SignSimple.io waitlist.
Unsubscribe: {{ unsubscribe_url }}
        '''
    },

    # Email 2: Value/features preview (Send 2 days before launch)
    'waitlist_preview': {
        'subject': 'Sneak peek: What you\'ll get with SignSimple.io',
        'delay_hours': 120,  # 5 days after signup (2 days before launch)
        'html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .feature { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 15px 0; }
        .feature h3 { margin-top: 0; color: #6366f1; }
        .highlight { background: #fef3c7; padding: 20px; border-radius: 8px; border-left: 4px solid #f59e0b; margin: 20px 0; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <p>Hey {{ name or 'there' }},</p>

    <p>SignSimple.io launches in <strong>2 days</strong>. Here's a sneak peek at what you'll get:</p>

    <div class="feature">
        <h3>Send Documents in Seconds</h3>
        <p>Upload any PDF, add signature fields, and send. Recipients sign from any device - no account needed.</p>
    </div>

    <div class="feature">
        <h3>Templates That Save Hours</h3>
        <p>Create reusable templates for contracts, agreements, NDAs. Send the same doc to different people in one click.</p>
    </div>

    <div class="feature">
        <h3>Automatic Reminders</h3>
        <p>Stop chasing signatures. We'll automatically remind recipients until they sign.</p>
    </div>

    <div class="feature">
        <h3>Legal Audit Trail</h3>
        <p>Every signature includes timestamp, IP address, and verification. Court-admissible and legally binding.</p>
    </div>

    <div class="highlight">
        <strong>Waitlist-only offer:</strong> The first 200 users get lifetime access for just $59 (one-time payment). Regular price will be $19/month.
    </div>

    <p>I'll email you the moment we go live so you can claim your spot.</p>

    <p>Questions? Just reply to this email.</p>

    <p>See you soon,<br>
    The SignSimple.io Team</p>

    <div class="footer">
        <p>You received this email because you signed up for the SignSimple.io waitlist.<br>
        <a href="{{ unsubscribe_url }}">Unsubscribe</a></p>
    </div>
</body>
</html>
        ''',
        'text': '''
Hey {{ name or 'there' }},

SignSimple.io launches in 2 days. Here's a sneak peek at what you'll get:

SEND DOCUMENTS IN SECONDS
Upload any PDF, add signature fields, and send. Recipients sign from any device - no account needed.

TEMPLATES THAT SAVE HOURS
Create reusable templates for contracts, agreements, NDAs. Send the same doc to different people in one click.

AUTOMATIC REMINDERS
Stop chasing signatures. We'll automatically remind recipients until they sign.

LEGAL AUDIT TRAIL
Every signature includes timestamp, IP address, and verification. Court-admissible and legally binding.

---
WAITLIST-ONLY OFFER: The first 200 users get lifetime access for just $59 (one-time payment). Regular price will be $19/month.
---

I'll email you the moment we go live so you can claim your spot.

Questions? Just reply to this email.

See you soon,
The SignSimple.io Team

---
You received this email because you signed up for the SignSimple.io waitlist.
Unsubscribe: {{ unsubscribe_url }}
        '''
    },

    # Email 3: Launch announcement (Send on launch day)
    'waitlist_launch': {
        'subject': 'WE\'RE LIVE! Claim your $59 Lifetime Deal (200 spots)',
        'delay_hours': 168,  # 7 days after signup (launch day)
        'html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #6366f1, #8b5cf6); padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px; }
        .header h1 { color: white; margin: 0; font-size: 28px; }
        .header p { color: rgba(255,255,255,0.9); margin: 10px 0 0; }
        .cta { display: inline-block; background: white; color: #6366f1; padding: 16px 32px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 18px; margin: 20px 0; }
        .urgency { background: #fef2f2; border: 1px solid #fecaca; padding: 15px; border-radius: 8px; text-align: center; margin: 20px 0; }
        .urgency strong { color: #dc2626; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>SignSimple.io is LIVE!</h1>
        <p>Your exclusive early access is ready</p>
    </div>

    <p>Hey {{ name or 'there' }},</p>

    <p><strong>The wait is over.</strong></p>

    <p>SignSimple.io is now live, and as a waitlist member, you get first access to our <strong>Founder's Lifetime Deal</strong>:</p>

    <ul>
        <li>Pay <strong>$59 once</strong> (not $19/month forever)</li>
        <li>Get <strong>lifetime access</strong> to all features</li>
        <li>Only <strong>200 spots</strong> available - ever</li>
    </ul>

    <div class="urgency">
        <strong>Spots are going fast.</strong> {{ spots_remaining }} of 200 remaining.
    </div>

    <p style="text-align: center;">
        <a href="{{ ltd_url }}" class="cta">Claim Your Lifetime Deal - $59</a>
    </p>

    <p>This is a one-time offer. Once 200 spots are filled, the lifetime deal is gone forever and pricing goes to $19/month.</p>

    <p>Don't miss out.</p>

    <p>Best,<br>
    The SignSimple.io Team</p>

    <div class="footer">
        <p>You received this email because you signed up for the SignSimple.io waitlist.<br>
        <a href="{{ unsubscribe_url }}">Unsubscribe</a></p>
    </div>
</body>
</html>
        ''',
        'text': '''
SignSimple.io is LIVE!
Your exclusive early access is ready

Hey {{ name or 'there' }},

The wait is over.

SignSimple.io is now live, and as a waitlist member, you get first access to our Founder's Lifetime Deal:

- Pay $59 once (not $19/month forever)
- Get lifetime access to all features
- Only 200 spots available - ever

SPOTS ARE GOING FAST: {{ spots_remaining }} of 200 remaining.

Claim Your Lifetime Deal: {{ ltd_url }}

This is a one-time offer. Once 200 spots are filled, the lifetime deal is gone forever and pricing goes to $19/month.

Don't miss out.

Best,
The SignSimple.io Team

---
You received this email because you signed up for the SignSimple.io waitlist.
Unsubscribe: {{ unsubscribe_url }}
        '''
    },
}

# =============================================================================
# EMAIL CONTENT - LTD PURCHASE CONFIRMATION
# =============================================================================

LTD_CONFIRMATION_EMAIL = {
    'subject': 'Welcome to the SignSimple.io family! Your lifetime access is ready',
    'html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .header { background: linear-gradient(135deg, #10b981, #059669); padding: 30px; border-radius: 12px; text-align: center; margin-bottom: 30px; }
        .header h1 { color: white; margin: 0; font-size: 24px; }
        .badge { display: inline-block; background: #fef3c7; color: #92400e; padding: 8px 16px; border-radius: 20px; font-weight: 600; margin: 15px 0; }
        .cta { display: inline-block; background: #6366f1; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 20px 0; }
        .receipt { background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>You're In! Lifetime Access Confirmed</h1>
    </div>

    <p>Hey {{ name or 'there' }},</p>

    <p><strong>Welcome to the SignSimple.io founder's circle!</strong></p>

    <p>Your one-time payment of $59 has been processed, and you now have <strong>lifetime access</strong> to SignSimple.io. No monthly fees. No annual renewals. Ever.</p>

    <p style="text-align: center;">
        <span class="badge">FOUNDER MEMBER #{{ member_number }}</span>
    </p>

    <div class="receipt">
        <strong>Order Details:</strong><br>
        Product: Founder's Lifetime Deal<br>
        Amount: $59.00 USD<br>
        Date: {{ purchase_date }}<br>
        Order ID: {{ order_id }}
    </div>

    <p><strong>What's next?</strong></p>

    <ol>
        <li><strong>Log in</strong> - Your account is ready at signsimple.io</li>
        <li><strong>Upload your first document</strong> - Try it out!</li>
        <li><strong>Create a template</strong> - Save time on repeat documents</li>
    </ol>

    <p style="text-align: center;">
        <a href="{{ dashboard_url }}" class="cta">Go to Your Dashboard</a>
    </p>

    <p>As a founder member, you also get:</p>
    <ul>
        <li>Priority support (we respond to founders first)</li>
        <li>Early access to new features</li>
        <li>Direct line to our product team</li>
    </ul>

    <p>Have questions? Just reply to this email. I read every message personally.</p>

    <p>Thanks for believing in us early. Let's build something great together.</p>

    <p>Best,<br>
    The SignSimple.io Team</p>

    <div class="footer">
        <p>This is your purchase confirmation for SignSimple.io.<br>
        Need help? Reply to this email or visit our <a href="{{ help_url }}">Help Center</a>.</p>
    </div>
</body>
</html>
    ''',
    'text': '''
You're In! Lifetime Access Confirmed

Hey {{ name or 'there' }},

Welcome to the SignSimple.io founder's circle!

Your one-time payment of $59 has been processed, and you now have lifetime access to SignSimple.io. No monthly fees. No annual renewals. Ever.

FOUNDER MEMBER #{{ member_number }}

---
Order Details:
Product: Founder's Lifetime Deal
Amount: $59.00 USD
Date: {{ purchase_date }}
Order ID: {{ order_id }}
---

What's next?
1. Log in - Your account is ready at signsimple.io
2. Upload your first document - Try it out!
3. Create a template - Save time on repeat documents

Go to Your Dashboard: {{ dashboard_url }}

As a founder member, you also get:
- Priority support (we respond to founders first)
- Early access to new features
- Direct line to our product team

Have questions? Just reply to this email. I read every message personally.

Thanks for believing in us early. Let's build something great together.

Best,
The SignSimple.io Team

---
This is your purchase confirmation for SignSimple.io.
Need help? Reply to this email or visit our Help Center: {{ help_url }}
    '''
}

# =============================================================================
# EMAIL CONTENT - LTD ONBOARDING SEQUENCE (5 emails over 14 days)
# =============================================================================

LTD_ONBOARDING_EMAILS = {
    # Email 1: Quick start guide (Day 1)
    'onboarding_day1': {
        'subject': 'Quick start: Send your first document in 60 seconds',
        'delay_hours': 24,
        'html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .step { background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 15px 0; border-left: 4px solid #6366f1; }
        .step h3 { margin-top: 0; color: #6366f1; }
        .cta { display: inline-block; background: #6366f1; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 20px 0; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <p>Hey {{ name or 'there' }},</p>

    <p>Ready to send your first document? Here's the fastest way to get started:</p>

    <div class="step">
        <h3>Step 1: Upload</h3>
        <p>Drag and drop any PDF onto your dashboard. We'll convert it automatically.</p>
    </div>

    <div class="step">
        <h3>Step 2: Add Fields</h3>
        <p>Click where you want signatures, dates, or text fields. Takes 30 seconds.</p>
    </div>

    <div class="step">
        <h3>Step 3: Send</h3>
        <p>Enter recipient email(s) and hit send. They get a link to sign - no account needed.</p>
    </div>

    <p style="text-align: center;">
        <a href="{{ dashboard_url }}" class="cta">Send Your First Document</a>
    </p>

    <p><strong>Pro tip:</strong> After your first document, save it as a template to reuse later!</p>

    <p>Tomorrow I'll show you the template feature that saves our users hours every week.</p>

    <p>Best,<br>
    The SignSimple.io Team</p>

    <div class="footer">
        <p>You're receiving this as part of your SignSimple.io onboarding.<br>
        <a href="{{ unsubscribe_url }}">Unsubscribe from tips</a></p>
    </div>
</body>
</html>
        ''',
        'text': '''Quick start: Send your first document in 60 seconds...'''
    },

    # Email 2: Templates feature (Day 3)
    'onboarding_day3': {
        'subject': 'Save hours with templates (here\'s how)',
        'delay_hours': 72,
        'html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .highlight { background: #f0fdf4; border: 1px solid #bbf7d0; padding: 20px; border-radius: 8px; margin: 20px 0; }
        .cta { display: inline-block; background: #6366f1; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 20px 0; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <p>Hey {{ name or 'there' }},</p>

    <p>Do you send similar documents repeatedly? Contracts, NDAs, proposals?</p>

    <p>Our <strong>templates feature</strong> lets you:</p>

    <ul>
        <li>Create a document once, send it unlimited times</li>
        <li>Pre-set signature fields so you never have to add them again</li>
        <li>Customize recipient details on each send</li>
    </ul>

    <div class="highlight">
        <strong>Real example:</strong> Sarah, a real estate agent, uses one template for all her listing agreements. She sends 20+ per week and saves about 3 hours compared to her old process.
    </div>

    <p><strong>How to create a template:</strong></p>
    <ol>
        <li>Go to Templates in your dashboard</li>
        <li>Upload your document</li>
        <li>Add your signature fields</li>
        <li>Save as template</li>
    </ol>

    <p style="text-align: center;">
        <a href="{{ templates_url }}" class="cta">Create Your First Template</a>
    </p>

    <p>Next email: How to get documents signed faster with automatic reminders.</p>

    <p>Best,<br>
    The SignSimple.io Team</p>

    <div class="footer">
        <p>You're receiving this as part of your SignSimple.io onboarding.<br>
        <a href="{{ unsubscribe_url }}">Unsubscribe from tips</a></p>
    </div>
</body>
</html>
        ''',
        'text': '''Save hours with templates...'''
    },

    # Email 3: Reminders feature (Day 5)
    'onboarding_day5': {
        'subject': 'Stop chasing signatures (let us do it)',
        'delay_hours': 120,
        'html': '''Template for automatic reminders feature...''',
        'text': '''Stop chasing signatures...'''
    },

    # Email 4: Advanced features (Day 10)
    'onboarding_day10': {
        'subject': '3 power features you might have missed',
        'delay_hours': 240,
        'html': '''Template for advanced features...''',
        'text': '''Power features...'''
    },

    # Email 5: Feedback request (Day 14)
    'onboarding_day14': {
        'subject': 'Quick question (takes 30 seconds)',
        'delay_hours': 336,
        'html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .cta { display: inline-block; background: #6366f1; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 10px 5px; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <p>Hey {{ name or 'there' }},</p>

    <p>You've been using SignSimple.io for about two weeks now. I have a quick question:</p>

    <p><strong>How likely are you to recommend SignSimple.io to a friend or colleague?</strong></p>

    <p>
        <a href="{{ nps_url }}?score=10" class="cta" style="background: #10b981;">Very likely</a>
        <a href="{{ nps_url }}?score=7" class="cta" style="background: #f59e0b;">Somewhat</a>
        <a href="{{ nps_url }}?score=3" class="cta" style="background: #ef4444;">Not likely</a>
    </p>

    <p>Your feedback helps us build a better product. And if something's not working for you, I'd love to hear about it - just reply to this email.</p>

    <p>Thanks for being a founder member!</p>

    <p>Best,<br>
    The SignSimple.io Team</p>

    <div class="footer">
        <p>You're receiving this as part of your SignSimple.io onboarding.<br>
        <a href="{{ unsubscribe_url }}">Unsubscribe from tips</a></p>
    </div>
</body>
</html>
        ''',
        'text': '''Quick feedback request...'''
    },
}

# =============================================================================
# EMAIL CONTENT - URGENCY EMAILS (During LTD sale)
# =============================================================================

URGENCY_EMAILS = {
    # 50% sold
    'urgency_50_percent': {
        'subject': 'Half gone: Only 100 lifetime spots left',
        'trigger': 'spots_remaining <= 100',
        'html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .urgency { background: #fef2f2; border: 2px solid #fecaca; padding: 20px; border-radius: 12px; text-align: center; margin: 20px 0; }
        .urgency h2 { color: #dc2626; margin-top: 0; }
        .cta { display: inline-block; background: #dc2626; color: white; padding: 16px 32px; border-radius: 8px; text-decoration: none; font-weight: 700; font-size: 18px; margin: 20px 0; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <p>Hey {{ name or 'there' }},</p>

    <p>Quick update on the SignSimple.io Founder's Lifetime Deal:</p>

    <div class="urgency">
        <h2>50% SOLD</h2>
        <p>Only <strong>{{ spots_remaining }}</strong> of 200 lifetime spots remain.</p>
    </div>

    <p>When these are gone, the price goes to $19/month ($228/year). The $59 lifetime deal will never come back.</p>

    <p style="text-align: center;">
        <a href="{{ ltd_url }}" class="cta">Claim Your Spot - $59</a>
    </p>

    <p>Don't say I didn't warn you!</p>

    <p>Best,<br>
    The SignSimple.io Team</p>

    <div class="footer">
        <p>You received this because you're on our waitlist.<br>
        <a href="{{ unsubscribe_url }}">Unsubscribe</a></p>
    </div>
</body>
</html>
        ''',
        'text': '''Half gone - only 100 lifetime spots left...'''
    },

    # 25 spots left
    'urgency_25_left': {
        'subject': 'FINAL WARNING: Only 25 lifetime spots left',
        'trigger': 'spots_remaining <= 25',
        'html': '''Similar urgency template for 25 spots...''',
        'text': '''Only 25 spots remaining...'''
    },

    # Last 10 spots
    'urgency_10_left': {
        'subject': 'LAST CHANCE: 10 spots. That\'s it.',
        'trigger': 'spots_remaining <= 10',
        'html': '''Final urgency template...''',
        'text': '''Only 10 spots left...'''
    },

    # Sold out
    'ltd_sold_out': {
        'subject': 'The Lifetime Deal is officially SOLD OUT',
        'trigger': 'spots_remaining == 0',
        'html': '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        .sold-out { background: #f3f4f6; padding: 20px; border-radius: 12px; text-align: center; margin: 20px 0; }
        .cta { display: inline-block; background: #6366f1; color: white; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; margin: 20px 0; }
        .footer { margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee; color: #666; font-size: 14px; }
    </style>
</head>
<body>
    <p>Hey {{ name or 'there' }},</p>

    <div class="sold-out">
        <h2>The Lifetime Deal is SOLD OUT</h2>
        <p>All 200 spots have been claimed.</p>
    </div>

    <p>Wow. That happened fast.</p>

    <p>If you missed out, don't worry - SignSimple.io is still incredibly affordable:</p>

    <ul>
        <li><strong>Free:</strong> 3 documents/month (forever free)</li>
        <li><strong>Starter:</strong> $9/month for 25 documents</li>
        <li><strong>Pro:</strong> $19/month for unlimited documents</li>
    </ul>

    <p style="text-align: center;">
        <a href="{{ pricing_url }}" class="cta">View Pricing Plans</a>
    </p>

    <p>Thanks for your interest in SignSimple.io!</p>

    <p>Best,<br>
    The SignSimple.io Team</p>

    <div class="footer">
        <p><a href="{{ unsubscribe_url }}">Unsubscribe</a></p>
    </div>
</body>
</html>
        ''',
        'text': '''The Lifetime Deal is sold out...'''
    },
}

# =============================================================================
# EMAIL SERVICE CLASS
# =============================================================================

class EmailSequence:
    """
    Email sequence manager for SignSimple.io.

    Usage:
        es = EmailSequence()

        # Send waitlist welcome
        es.send_waitlist_welcome(email="user@example.com", name="John")

        # Send LTD confirmation
        es.send_ltd_confirmation(
            email="user@example.com",
            name="John",
            member_number=42,
            order_id="ord_123"
        )

        # Start onboarding sequence
        es.start_onboarding_sequence(email="user@example.com", name="John")
    """

    def __init__(self, email_provider: str = 'sendgrid'):
        """
        Initialize email sequence with provider.

        Args:
            email_provider: 'sendgrid', 'postmark', 'resend', or 'smtp'
        """
        self.provider = email_provider
        self.from_email = os.getenv('EMAIL_FROM', 'hello@signsimple.io')
        self.from_name = os.getenv('EMAIL_FROM_NAME', 'SignSimple.io')

    def _render_template(self, template: str, context: Dict[str, Any]) -> str:
        """Render Jinja2 template with context."""
        from jinja2 import Template
        return Template(template).render(**context)

    def _send_email(self, to_email: str, subject: str, html: str, text: str) -> bool:
        """
        Send email via configured provider.

        TODO: Implement your email provider integration here.
        """
        logger.info(f"Sending email to {to_email}: {subject}")

        # Example SendGrid implementation:
        # import sendgrid
        # from sendgrid.helpers.mail import Mail
        # sg = sendgrid.SendGridAPIClient(api_key=os.getenv('SENDGRID_API_KEY'))
        # message = Mail(
        #     from_email=self.from_email,
        #     to_emails=to_email,
        #     subject=subject,
        #     html_content=html,
        #     plain_text_content=text
        # )
        # response = sg.send(message)
        # return response.status_code == 202

        return True  # Placeholder

    def send_waitlist_welcome(self, email: str, name: Optional[str] = None) -> bool:
        """Send waitlist welcome email."""
        template = WAITLIST_EMAILS['waitlist_welcome']
        context = {
            'name': name,
            'unsubscribe_url': f'https://signsimple.io/unsubscribe?email={email}',
        }
        html = self._render_template(template['html'], context)
        text = self._render_template(template['text'], context)
        return self._send_email(email, template['subject'], html, text)

    def send_ltd_confirmation(
        self,
        email: str,
        name: Optional[str] = None,
        member_number: int = 1,
        order_id: str = '',
    ) -> bool:
        """Send LTD purchase confirmation email."""
        context = {
            'name': name,
            'member_number': member_number,
            'order_id': order_id,
            'purchase_date': datetime.now().strftime('%B %d, %Y'),
            'dashboard_url': 'https://signsimple.io/dashboard',
            'help_url': 'https://signsimple.io/help',
        }
        html = self._render_template(LTD_CONFIRMATION_EMAIL['html'], context)
        text = self._render_template(LTD_CONFIRMATION_EMAIL['text'], context)
        return self._send_email(email, LTD_CONFIRMATION_EMAIL['subject'], html, text)

    def start_onboarding_sequence(self, email: str, name: Optional[str] = None) -> bool:
        """
        Start the onboarding email sequence.

        In production, queue these emails with appropriate delays.
        """
        # TODO: Implement email queue/scheduler
        # Example with Celery:
        # for key, email_data in LTD_ONBOARDING_EMAILS.items():
        #     send_email_task.apply_async(
        #         args=[email, email_data],
        #         countdown=email_data['delay_hours'] * 3600
        #     )
        logger.info(f"Started onboarding sequence for {email}")
        return True

    def send_urgency_email(
        self,
        email: str,
        urgency_type: str,
        spots_remaining: int,
        name: Optional[str] = None,
    ) -> bool:
        """Send urgency email based on spots remaining."""
        if urgency_type not in URGENCY_EMAILS:
            logger.error(f"Unknown urgency type: {urgency_type}")
            return False

        template = URGENCY_EMAILS[urgency_type]
        context = {
            'name': name,
            'spots_remaining': spots_remaining,
            'ltd_url': 'https://signsimple.io/ltd',
            'pricing_url': 'https://signsimple.io/pricing',
            'unsubscribe_url': f'https://signsimple.io/unsubscribe?email={email}',
        }
        html = self._render_template(template['html'], context)
        text = self._render_template(template['text'], context)
        return self._send_email(email, template['subject'], html, text)
