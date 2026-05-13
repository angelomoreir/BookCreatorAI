"""
Subscription management routes for Stripe integration
"""
import stripe
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime
from models.book import db, User, SubscriptionHistory, PLAN_CONFIG
import config

subscription_bp = Blueprint('subscription', __name__)

# Configure Stripe
stripe.api_key = config.STRIPE_SECRET_KEY


def get_or_create_stripe_customer(user):
    """Get existing Stripe customer or create new one"""
    if user.stripe_customer_id:
        try:
            customer = stripe.Customer.retrieve(user.stripe_customer_id)
            if not customer.get('deleted'):
                return customer
        except stripe.error.InvalidRequestError:
            pass
    
    # Create new customer
    customer = stripe.Customer.create(
        email=user.email,
        name=user.name,
        metadata={'user_id': user.id}
    )
    user.stripe_customer_id = customer.id
    db.session.commit()
    return customer


@subscription_bp.route('/pricing')
def pricing():
    """Display pricing page"""
    return render_template('subscription/pricing.html', 
                         plans=PLAN_CONFIG,
                         stripe_key=config.STRIPE_PUBLISHABLE_KEY)


@subscription_bp.route('/checkout/<plan>/<billing>')
@login_required
def checkout(plan, billing):
    """Create Stripe Checkout session"""
    if plan not in ['pro', 'premium']:
        flash('Plano inválido.', 'error')
        return redirect(url_for('subscription.pricing'))
    
    if billing not in ['monthly', 'yearly']:
        flash('Período de faturação inválido.', 'error')
        return redirect(url_for('subscription.pricing'))
    
    # Get price ID from config
    price_key = f'{plan}_{billing}'
    price_id = config.STRIPE_PRICES.get(price_key)
    
    if not price_id:
        flash('Configuração de preço não encontrada. Contacte o suporte.', 'error')
        return redirect(url_for('subscription.pricing'))
    
    try:
        # Get or create Stripe customer
        customer = get_or_create_stripe_customer(current_user)
        
        # Create checkout session
        checkout_session = stripe.checkout.Session.create(
            customer=customer.id,
            payment_method_types=['card'],
            line_items=[{
                'price': price_id,
                'quantity': 1,
            }],
            mode='subscription',
            success_url=config.APP_URL + url_for('subscription.success') + '?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=config.APP_URL + url_for('subscription.pricing'),
            metadata={
                'user_id': current_user.id,
                'plan': plan,
                'billing': billing
            }
        )
        
        return redirect(checkout_session.url)
    
    except stripe.error.StripeError as e:
        flash(f'Erro ao processar pagamento: {str(e)}', 'error')
        return redirect(url_for('subscription.pricing'))


@subscription_bp.route('/success')
@login_required
def success():
    """Handle successful checkout"""
    session_id = request.args.get('session_id')
    
    if session_id:
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            
            # Update will be handled by webhook, but show success message
            flash('Subscrição ativada com sucesso! Obrigado pela sua compra.', 'success')
        except stripe.error.StripeError:
            flash('Pagamento processado. A sua subscrição será ativada em breve.', 'info')
    
    return redirect(url_for('profile'))


@subscription_bp.route('/manage')
@login_required
def manage():
    """Subscription management page"""
    # Get subscription history
    history = SubscriptionHistory.query.filter_by(user_id=current_user.id)\
        .order_by(SubscriptionHistory.created_at.desc())\
        .limit(10).all()
    
    return render_template('subscription/manage.html',
                         plans=PLAN_CONFIG,
                         history=history,
                         stripe_key=config.STRIPE_PUBLISHABLE_KEY)


@subscription_bp.route('/portal')
@login_required
def customer_portal():
    """Redirect to Stripe Customer Portal for subscription management"""
    if not current_user.stripe_customer_id:
        flash('Não tem uma subscrição ativa.', 'error')
        return redirect(url_for('subscription.pricing'))
    
    try:
        portal_session = stripe.billing_portal.Session.create(
            customer=current_user.stripe_customer_id,
            return_url=config.APP_URL + url_for('subscription.manage')
        )
        return redirect(portal_session.url)
    except stripe.error.StripeError as e:
        flash(f'Erro ao aceder ao portal: {str(e)}', 'error')
        return redirect(url_for('subscription.manage'))


@subscription_bp.route('/cancel', methods=['POST'])
@login_required
def cancel():
    """Cancel subscription at end of billing period"""
    if not current_user.stripe_subscription_id:
        return jsonify({'success': False, 'error': 'Sem subscrição ativa'}), 400
    
    try:
        # Cancel at period end (user keeps access until end of paid period)
        subscription = stripe.Subscription.modify(
            current_user.stripe_subscription_id,
            cancel_at_period_end=True
        )
        
        current_user.subscription_status = 'canceled'
        db.session.commit()
        
        # Log cancellation
        history = SubscriptionHistory(
            user_id=current_user.id,
            plan=current_user.plan,
            action='canceled',
            stripe_subscription_id=current_user.stripe_subscription_id
        )
        db.session.add(history)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Subscrição cancelada. Terá acesso até ao fim do período pago.'
        })
    
    except stripe.error.StripeError as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@subscription_bp.route('/reactivate', methods=['POST'])
@login_required
def reactivate():
    """Reactivate a canceled subscription"""
    if not current_user.stripe_subscription_id:
        return jsonify({'success': False, 'error': 'Sem subscrição para reativar'}), 400
    
    try:
        subscription = stripe.Subscription.modify(
            current_user.stripe_subscription_id,
            cancel_at_period_end=False
        )
        
        current_user.subscription_status = 'active'
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Subscrição reativada com sucesso!'
        })
    
    except stripe.error.StripeError as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@subscription_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle Stripe webhooks"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    
    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, config.STRIPE_WEBHOOK_SECRET
        )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400
    
    # Handle the event
    if event['type'] == 'checkout.session.completed':
        handle_checkout_completed(event['data']['object'])
    
    elif event['type'] == 'customer.subscription.updated':
        handle_subscription_updated(event['data']['object'])
    
    elif event['type'] == 'customer.subscription.deleted':
        handle_subscription_deleted(event['data']['object'])
    
    elif event['type'] == 'invoice.paid':
        handle_invoice_paid(event['data']['object'])
    
    elif event['type'] == 'invoice.payment_failed':
        handle_payment_failed(event['data']['object'])
    
    return jsonify({'status': 'success'})


def handle_checkout_completed(session):
    """Handle successful checkout"""
    user_id = session.get('metadata', {}).get('user_id')
    plan = session.get('metadata', {}).get('plan')
    subscription_id = session.get('subscription')
    
    if not user_id or not plan:
        return
    
    user = User.query.get(int(user_id))
    if not user:
        return
    
    amount = session.get('amount_total', 0) / 100
    currency = session.get('currency', 'eur').upper()
    
    # Update user subscription
    user.plan = plan
    user.stripe_subscription_id = subscription_id
    user.subscription_status = 'active'
    user.usage_count = 0  # Reset usage on new subscription
    
    # Log subscription creation
    history = SubscriptionHistory(
        user_id=user.id,
        plan=plan,
        action='created',
        stripe_subscription_id=subscription_id,
        amount=amount,
        currency=currency
    )
    db.session.add(history)
    db.session.commit()
    
    # Send subscription confirmation email
    try:
        from utils.email_service import send_subscription_confirmation
        plan_name = PLAN_CONFIG.get(plan, {}).get('name', plan.capitalize())
        send_subscription_confirmation(user.email, user.name, plan_name, amount, currency)
    except Exception as e:
        print(f"Error sending subscription confirmation email: {e}")
    
    # Track in analytics
    try:
        from utils.analytics import tracker
        tracker.track_subscription(user.id, plan, 'started', amount)
    except Exception as e:
        print(f"Analytics error: {e}")


def handle_subscription_updated(subscription):
    """Handle subscription updates (upgrades/downgrades)"""
    customer_id = subscription.get('customer')
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    
    if not user:
        return
    
    # Get the price to determine the plan
    items = subscription.get('items', {}).get('data', [])
    if items:
        price_id = items[0].get('price', {}).get('id')
        
        # Determine plan from price ID
        new_plan = None
        for plan_key, price_key in [('pro', 'pro_monthly'), ('pro', 'pro_yearly'),
                                     ('premium', 'premium_monthly'), ('premium', 'premium_yearly')]:
            if config.STRIPE_PRICES.get(price_key) == price_id:
                new_plan = plan_key
                break
        
        if new_plan and new_plan != user.plan:
            old_plan = user.plan
            user.plan = new_plan
            
            # Log the change
            action = 'upgraded' if PLAN_CONFIG[new_plan]['price_monthly'] > PLAN_CONFIG.get(old_plan, {}).get('price_monthly', 0) else 'downgraded'
            history = SubscriptionHistory(
                user_id=user.id,
                plan=new_plan,
                action=action,
                stripe_subscription_id=subscription.get('id')
            )
            db.session.add(history)
    
    # Update status
    status = subscription.get('status')
    if status == 'active':
        user.subscription_status = 'active'
    elif status == 'past_due':
        user.subscription_status = 'past_due'
    elif status in ['canceled', 'unpaid']:
        user.subscription_status = 'canceled'
    
    # Update end date
    current_period_end = subscription.get('current_period_end')
    if current_period_end:
        user.subscription_end_date = datetime.fromtimestamp(current_period_end)
    
    db.session.commit()


def handle_subscription_deleted(subscription):
    """Handle subscription cancellation/deletion"""
    customer_id = subscription.get('customer')
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    
    if not user:
        return
    
    # Get end date before updating
    end_date = user.subscription_end_date.strftime('%d/%m/%Y') if user.subscription_end_date else 'N/A'
    
    # Downgrade to free
    user.plan = 'free'
    user.subscription_status = 'none'
    user.stripe_subscription_id = None
    
    # Log cancellation
    history = SubscriptionHistory(
        user_id=user.id,
        plan='free',
        action='canceled',
        stripe_subscription_id=subscription.get('id')
    )
    db.session.add(history)
    db.session.commit()
    
    # Send cancellation email
    try:
        from utils.email_service import send_subscription_cancelled
        send_subscription_cancelled(user.email, user.name, end_date)
    except Exception as e:
        print(f"Error sending cancellation email: {e}")


def handle_invoice_paid(invoice):
    """Handle successful invoice payment (renewal)"""
    customer_id = invoice.get('customer')
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    
    if not user:
        return
    
    amount = invoice.get('amount_paid', 0) / 100
    currency = invoice.get('currency', 'eur').upper()
    
    # Reset monthly usage on renewal
    user.usage_count = 0
    user.usage_reset_date = datetime.utcnow()
    
    # Log renewal
    history = SubscriptionHistory(
        user_id=user.id,
        plan=user.plan,
        action='renewed',
        stripe_invoice_id=invoice.get('id'),
        amount=amount,
        currency=currency,
        period_start=datetime.fromtimestamp(invoice.get('period_start', 0)) if invoice.get('period_start') else None,
        period_end=datetime.fromtimestamp(invoice.get('period_end', 0)) if invoice.get('period_end') else None
    )
    db.session.add(history)
    db.session.commit()
    
    # Send invoice email
    try:
        from utils.email_service import send_invoice_email
        invoice_data = {
            'invoice_number': invoice.get('number', invoice.get('id', 'N/A')),
            'date': datetime.utcnow().strftime('%d/%m/%Y'),
            'description': f"Subscrição {PLAN_CONFIG.get(user.plan, {}).get('name', user.plan)}",
            'period': 'Mensal',
            'amount': amount,
            'currency': currency
        }
        send_invoice_email(user.email, user.name, invoice_data)
    except Exception as e:
        print(f"Error sending invoice email: {e}")


def handle_payment_failed(invoice):
    """Handle failed payment"""
    customer_id = invoice.get('customer')
    user = User.query.filter_by(stripe_customer_id=customer_id).first()
    
    if not user:
        return
    
    user.subscription_status = 'past_due'
    db.session.commit()


# API endpoint to get current plan info
@subscription_bp.route('/api/plan-info')
@login_required
def plan_info():
    """Get current user's plan information"""
    from utils.rate_limiter import get_usage_info, check_and_reset_monthly_usage
    
    # Check and reset if needed
    check_and_reset_monthly_usage(current_user)
    
    config = current_user.get_plan_config()
    usage_info = get_usage_info(current_user)
    
    return jsonify({
        'plan': current_user.plan,
        'plan_name': config['name'],
        'usage_count': current_user.usage_count,
        'usage_limit': current_user.get_usage_limit(),
        'usage_remaining': usage_info['usage_remaining'],
        'usage_percentage': usage_info['usage_percentage'],
        'reset_date': usage_info['reset_date'],
        'days_until_reset': usage_info['days_until_reset'],
        'is_limit_reached': usage_info['is_limit_reached'],
        'subscription_status': current_user.subscription_status,
        'features': config['features'],
        'limits': config['limits']
    })


@subscription_bp.route('/api/usage')
@login_required
def usage_info():
    """Get detailed usage information"""
    from utils.rate_limiter import get_usage_info, check_and_reset_monthly_usage
    
    check_and_reset_monthly_usage(current_user)
    return jsonify(get_usage_info(current_user))
