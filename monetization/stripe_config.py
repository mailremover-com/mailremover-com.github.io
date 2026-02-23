"""
SignSimple.io - Stripe Payment Configuration
=============================================

This module handles all Stripe payment processing for:
- Founder's Lifetime Deal ($59 one-time)
- Starter Plan ($9/month or $90/year)
- Pro Plan ($19/month or $190/year)

Setup Instructions:
1. Create a Stripe account at https://stripe.com
2. Get your API keys from https://dashboard.stripe.com/apikeys
3. Create products and prices in Stripe Dashboard
4. Add the price IDs to your .env file

Environment Variables Required:
- STRIPE_SECRET_KEY: Your Stripe secret key (sk_live_... or sk_test_...)
- STRIPE_PUBLISHABLE_KEY: Your publishable key (pk_live_... or pk_test_...)
- STRIPE_WEBHOOK_SECRET: Webhook signing secret (whsec_...)
- STRIPE_PRICE_LTD: Price ID for Lifetime Deal
- STRIPE_PRICE_STARTER_MONTHLY: Price ID for Starter monthly
- STRIPE_PRICE_STARTER_YEARLY: Price ID for Starter yearly
- STRIPE_PRICE_PRO_MONTHLY: Price ID for Pro monthly
- STRIPE_PRICE_PRO_YEARLY: Price ID for Pro yearly
"""

import os
import stripe
from flask import Blueprint, request, redirect, url_for, jsonify, session, render_template
from functools import wraps
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Stripe
stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

# Create Blueprint
payments_bp = Blueprint('payments', __name__)

# =============================================================================
# STRIPE PRICE CONFIGURATION
# =============================================================================

PRICE_CONFIG = {
    # Founder's Lifetime Deal - One-time payment
    'lifetime': {
        'price_id': os.getenv('STRIPE_PRICE_LTD', 'price_ltd_placeholder'),
        'mode': 'payment',  # One-time payment
        'name': "Founder's Lifetime Deal",
        'amount': 5900,  # $59.00 in cents
        'type': 'lifetime',
        'success_url': '/success?session_id={CHECKOUT_SESSION_ID}&type=lifetime',
        'cancel_url': '/ltd',
    },

    # Starter Plan - Monthly
    'starter_monthly': {
        'price_id': os.getenv('STRIPE_PRICE_STARTER_MONTHLY', 'price_starter_monthly_placeholder'),
        'mode': 'subscription',
        'name': 'Starter Monthly',
        'amount': 900,  # $9.00/month in cents
        'type': 'subscription',
        'success_url': '/success?session_id={CHECKOUT_SESSION_ID}&type=starter',
        'cancel_url': '/pricing',
    },

    # Starter Plan - Yearly
    'starter_yearly': {
        'price_id': os.getenv('STRIPE_PRICE_STARTER_YEARLY', 'price_starter_yearly_placeholder'),
        'mode': 'subscription',
        'name': 'Starter Yearly',
        'amount': 9000,  # $90.00/year in cents
        'type': 'subscription',
        'success_url': '/success?session_id={CHECKOUT_SESSION_ID}&type=starter',
        'cancel_url': '/pricing',
    },

    # Pro Plan - Monthly
    'pro_monthly': {
        'price_id': os.getenv('STRIPE_PRICE_PRO_MONTHLY', 'price_pro_monthly_placeholder'),
        'mode': 'subscription',
        'name': 'Pro Monthly',
        'amount': 1900,  # $19.00/month in cents
        'type': 'subscription',
        'success_url': '/success?session_id={CHECKOUT_SESSION_ID}&type=pro',
        'cancel_url': '/pricing',
    },

    # Pro Plan - Yearly
    'pro_yearly': {
        'price_id': os.getenv('STRIPE_PRICE_PRO_YEARLY', 'price_pro_yearly_placeholder'),
        'mode': 'subscription',
        'name': 'Pro Yearly',
        'amount': 19000,  # $190.00/year in cents
        'type': 'subscription',
        'success_url': '/success?session_id={CHECKOUT_SESSION_ID}&type=pro',
        'cancel_url': '/pricing',
    },
}

# =============================================================================
# LTD SPOTS TRACKING
# =============================================================================

# In production, this should be stored in a database
LTD_CONFIG = {
    'total_spots': 200,
    'price_cents': 5900,
    'deal_end_days': 7,  # Deal ends after 7 days
}

def get_ltd_spots_remaining():
    """
    Get the number of LTD spots remaining.
    In production, query your database for count of LTD purchases.
    """
    # TODO: Replace with actual database query
    # Example: return LTD_CONFIG['total_spots'] - db.query(LTDPurchase).count()
    from database import get_ltd_purchase_count
    try:
        sold = get_ltd_purchase_count()
        return max(0, LTD_CONFIG['total_spots'] - sold)
    except:
        # Fallback for demo
        return 147  # Demo value

def is_ltd_available():
    """Check if LTD is still available."""
    return get_ltd_spots_remaining() > 0

# =============================================================================
# CHECKOUT SESSION CREATION
# =============================================================================

@payments_bp.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """
    Create a Stripe Checkout Session for the selected price type.

    Expects form data with:
    - price_type: One of 'lifetime', 'starter_monthly', 'starter_yearly',
                  'pro_monthly', 'pro_yearly'
    """
    try:
        price_type = request.form.get('price_type', 'lifetime')

        if price_type not in PRICE_CONFIG:
            logger.error(f"Invalid price type: {price_type}")
            return redirect(url_for('pricing'))

        config = PRICE_CONFIG[price_type]

        # Check LTD availability
        if price_type == 'lifetime' and not is_ltd_available():
            logger.warning("LTD purchase attempted but sold out")
            return redirect(url_for('ltd_sold_out'))

        # Get user email if logged in
        customer_email = session.get('user_email')

        # Build checkout session parameters
        checkout_params = {
            'payment_method_types': ['card'],
            'line_items': [{
                'price': config['price_id'],
                'quantity': 1,
            }],
            'mode': config['mode'],
            'success_url': request.host_url.rstrip('/') + config['success_url'],
            'cancel_url': request.host_url.rstrip('/') + config['cancel_url'],
            'metadata': {
                'price_type': price_type,
                'plan_name': config['name'],
            },
            'allow_promotion_codes': True,
        }

        # Add customer email if available
        if customer_email:
            checkout_params['customer_email'] = customer_email

        # For subscriptions, allow customer to manage billing
        if config['mode'] == 'subscription':
            checkout_params['billing_address_collection'] = 'required'
            checkout_params['subscription_data'] = {
                'metadata': {
                    'price_type': price_type,
                }
            }

        # For lifetime deals, add invoice generation
        if price_type == 'lifetime':
            checkout_params['invoice_creation'] = {
                'enabled': True,
                'invoice_data': {
                    'description': "SignSimple.io Founder's Lifetime Deal",
                    'metadata': {
                        'deal_type': 'lifetime',
                    },
                },
            }

        # Create the checkout session
        checkout_session = stripe.checkout.Session.create(**checkout_params)

        logger.info(f"Created checkout session: {checkout_session.id} for {price_type}")

        return redirect(checkout_session.url, code=303)

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        return redirect(url_for('error', message='Payment processing error'))
    except Exception as e:
        logger.error(f"Checkout error: {str(e)}")
        return redirect(url_for('error', message='An error occurred'))

# =============================================================================
# WEBHOOK HANDLING
# =============================================================================

@payments_bp.route('/webhook/stripe', methods=['POST'])
def stripe_webhook():
    """
    Handle Stripe webhook events.

    Key events handled:
    - checkout.session.completed: Payment successful
    - customer.subscription.created: New subscription
    - customer.subscription.updated: Subscription changed
    - customer.subscription.deleted: Subscription cancelled
    - invoice.payment_failed: Payment failed
    """
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        logger.error(f"Invalid payload: {str(e)}")
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the event
    event_type = event['type']
    event_data = event['data']['object']

    logger.info(f"Received webhook: {event_type}")

    if event_type == 'checkout.session.completed':
        handle_checkout_completed(event_data)
    elif event_type == 'customer.subscription.created':
        handle_subscription_created(event_data)
    elif event_type == 'customer.subscription.updated':
        handle_subscription_updated(event_data)
    elif event_type == 'customer.subscription.deleted':
        handle_subscription_deleted(event_data)
    elif event_type == 'invoice.payment_failed':
        handle_payment_failed(event_data)

    return jsonify({'status': 'success'}), 200

def handle_checkout_completed(session_data):
    """
    Handle successful checkout completion.

    For LTD: Grant lifetime access, decrement spots, send confirmation email
    For subscriptions: Grant appropriate access level
    """
    customer_email = session_data.get('customer_email')
    price_type = session_data.get('metadata', {}).get('price_type')
    customer_id = session_data.get('customer')

    logger.info(f"Checkout completed: {customer_email}, {price_type}")

    if price_type == 'lifetime':
        # Grant lifetime access
        grant_lifetime_access(customer_email, customer_id, session_data)
        # Decrement spots counter
        decrement_ltd_spots()
        # Send confirmation email
        send_ltd_confirmation_email(customer_email)
    else:
        # Handle subscription
        subscription_id = session_data.get('subscription')
        grant_subscription_access(customer_email, customer_id, subscription_id, price_type)
        send_subscription_confirmation_email(customer_email, price_type)

def handle_subscription_created(subscription):
    """Handle new subscription creation."""
    customer_id = subscription.get('customer')
    status = subscription.get('status')
    logger.info(f"Subscription created: {customer_id}, status: {status}")

def handle_subscription_updated(subscription):
    """Handle subscription updates (upgrades, downgrades, etc.)."""
    customer_id = subscription.get('customer')
    status = subscription.get('status')
    logger.info(f"Subscription updated: {customer_id}, status: {status}")
    # Update user's access level based on new plan

def handle_subscription_deleted(subscription):
    """Handle subscription cancellation."""
    customer_id = subscription.get('customer')
    logger.info(f"Subscription deleted: {customer_id}")
    # Revoke access or downgrade to free tier

def handle_payment_failed(invoice):
    """Handle failed payment."""
    customer_id = invoice.get('customer')
    customer_email = invoice.get('customer_email')
    logger.warning(f"Payment failed: {customer_email}")
    # Send payment failed email, potentially pause access

# =============================================================================
# DATABASE OPERATIONS (Implement based on your database)
# =============================================================================

def grant_lifetime_access(email, customer_id, session_data):
    """
    Grant lifetime access to a user.

    TODO: Implement with your database
    """
    logger.info(f"Granting lifetime access to: {email}")
    # Example implementation:
    # user = User.query.filter_by(email=email).first()
    # if not user:
    #     user = User(email=email)
    # user.plan = 'lifetime'
    # user.stripe_customer_id = customer_id
    # user.ltd_purchased_at = datetime.utcnow()
    # db.session.add(user)
    # db.session.commit()

def decrement_ltd_spots():
    """
    Decrement the LTD spots counter.

    TODO: Implement with your database
    """
    logger.info("Decrementing LTD spots")
    # Example: LTDCounter.query.first().sold += 1

def grant_subscription_access(email, customer_id, subscription_id, price_type):
    """
    Grant subscription access to a user.

    TODO: Implement with your database
    """
    plan = 'starter' if 'starter' in price_type else 'pro'
    logger.info(f"Granting {plan} access to: {email}")

def send_ltd_confirmation_email(email):
    """
    Send LTD purchase confirmation email.

    TODO: Implement with your email service
    """
    logger.info(f"Sending LTD confirmation to: {email}")
    # Use your email service (SendGrid, Postmark, etc.)

def send_subscription_confirmation_email(email, price_type):
    """
    Send subscription confirmation email.

    TODO: Implement with your email service
    """
    logger.info(f"Sending subscription confirmation to: {email}")

# =============================================================================
# CUSTOMER PORTAL
# =============================================================================

@payments_bp.route('/billing-portal', methods=['POST'])
def billing_portal():
    """
    Create a Stripe Customer Portal session for managing subscriptions.
    """
    customer_id = session.get('stripe_customer_id')

    if not customer_id:
        return redirect(url_for('login'))

    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=request.host_url.rstrip('/') + '/dashboard',
        )
        return redirect(portal_session.url, code=303)
    except stripe.error.StripeError as e:
        logger.error(f"Portal error: {str(e)}")
        return redirect(url_for('dashboard'))

# =============================================================================
# STRIPE PRODUCT SETUP SCRIPT
# =============================================================================

def create_stripe_products():
    """
    One-time script to create Stripe products and prices.
    Run this once during initial setup.

    Usage: python -c "from stripe_config import create_stripe_products; create_stripe_products()"
    """

    # Create Lifetime Deal Product
    ltd_product = stripe.Product.create(
        name="SignSimple.io Founder's Lifetime Deal",
        description="Lifetime access to SignSimple.io - Pay once, use forever",
    )

    ltd_price = stripe.Price.create(
        product=ltd_product.id,
        unit_amount=5900,  # $59.00
        currency='usd',
    )
    print(f"LTD Price ID: {ltd_price.id}")

    # Create Starter Product
    starter_product = stripe.Product.create(
        name="SignSimple.io Starter",
        description="Starter plan for freelancers and individuals",
    )

    starter_monthly = stripe.Price.create(
        product=starter_product.id,
        unit_amount=900,  # $9.00
        currency='usd',
        recurring={'interval': 'month'},
    )
    print(f"Starter Monthly Price ID: {starter_monthly.id}")

    starter_yearly = stripe.Price.create(
        product=starter_product.id,
        unit_amount=9000,  # $90.00
        currency='usd',
        recurring={'interval': 'year'},
    )
    print(f"Starter Yearly Price ID: {starter_yearly.id}")

    # Create Pro Product
    pro_product = stripe.Product.create(
        name="SignSimple.io Pro",
        description="Pro plan for growing businesses",
    )

    pro_monthly = stripe.Price.create(
        product=pro_product.id,
        unit_amount=1900,  # $19.00
        currency='usd',
        recurring={'interval': 'month'},
    )
    print(f"Pro Monthly Price ID: {pro_monthly.id}")

    pro_yearly = stripe.Price.create(
        product=pro_product.id,
        unit_amount=19000,  # $190.00
        currency='usd',
        recurring={'interval': 'year'},
    )
    print(f"Pro Yearly Price ID: {pro_yearly.id}")

    print("\n--- Add these to your .env file ---")
    print(f"STRIPE_PRICE_LTD={ltd_price.id}")
    print(f"STRIPE_PRICE_STARTER_MONTHLY={starter_monthly.id}")
    print(f"STRIPE_PRICE_STARTER_YEARLY={starter_yearly.id}")
    print(f"STRIPE_PRICE_PRO_MONTHLY={pro_monthly.id}")
    print(f"STRIPE_PRICE_PRO_YEARLY={pro_yearly.id}")

# =============================================================================
# INTEGRATION WITH FLASK APP
# =============================================================================

def init_payments(app):
    """
    Initialize payments blueprint with Flask app.

    Usage in app.py:
        from monetization.stripe_config import init_payments
        init_payments(app)
    """
    app.register_blueprint(payments_bp)

    # Add context processor for templates
    @app.context_processor
    def inject_ltd_data():
        return {
            'ltd_active': is_ltd_available(),
            'spots_remaining': get_ltd_spots_remaining(),
        }
