"""
Push Notification Service for Alma do Livro
"""
import os
import json
from datetime import datetime

# VAPID keys for Web Push
# Generate these with: openssl ecparam -genkey -name prime256v1 -out private_key.pem
# Then: openssl ec -in private_key.pem -pubout -outform DER | tail -c 65 | base64 | tr '/+' '_-' | tr -d '\n'

VAPID_PRIVATE_KEY = os.environ.get('VAPID_PRIVATE_KEY', '-----BEGIN PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgbZHWDUnubpXd3kCe\nYpfWyCLoioLi6MudCc/8J+ALZJahRANCAAT52YaJf/BX3lFBSsCM8hxJUdpceMUQ\nQzjThetfvBKMHG/uZNEFSm4UozHtepvZs1bgEpscD0On690YXlJ0dgkG\n-----END PRIVATE KEY-----')
VAPID_PUBLIC_KEY = os.environ.get('VAPID_PUBLIC_KEY', 'BPnZhol_8FfeUUFKwIzyHElR2lx4xRBDONOF61-8Eowcb-5k0QVKbhSjMe16m9mzVuASmxwPQ6fr3RheUnR2CQY')
VAPID_CLAIMS = {
    'sub': 'mailto:suporte@almadolivro.com'
}


def send_push_notification(subscription, title, body, url=None, notification_type='general'):
    """
    Send a push notification to a single subscription
    
    Args:
        subscription: PushSubscription model instance
        title: Notification title
        body: Notification body text
        url: URL to open when clicked
        notification_type: Type of notification for tracking
    
    Returns:
        bool: True if sent successfully
    """
    try:
        from pywebpush import webpush, WebPushException
    except ImportError:
        print("[Notifications] pywebpush not installed. Run: pip install pywebpush")
        return False
    
    try:
        subscription_info = {
            'endpoint': subscription.endpoint,
            'keys': {
                'p256dh': subscription.p256dh_key,
                'auth': subscription.auth_key
            }
        }
        
        payload = json.dumps({
            'title': title,
            'body': body,
            'icon': '/static/icon-192.png',
            'badge': '/static/badge-72.png',
            'tag': f'alma-{notification_type}',
            'data': {
                'url': url or '/explorer',
                'type': notification_type
            },
            'requireInteraction': notification_type in ['usage_reset', 'new_feature']
        })
        
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims=VAPID_CLAIMS
        )
        
        # Update last_used timestamp
        subscription.last_used = datetime.utcnow()
        
        return True
        
    except Exception as e:
        print(f"[Notifications] Error sending push: {e}")
        
        # If subscription is invalid, mark as inactive
        if 'expired' in str(e).lower() or '410' in str(e) or '404' in str(e):
            subscription.is_active = False
        
        return False


def send_notification_to_user(user, title, body, url=None, notification_type='general', save_to_db=True):
    """
    Send notification to all active subscriptions for a user
    
    Args:
        user: User model instance
        title: Notification title
        body: Notification body
        url: URL to open
        notification_type: Type of notification
        save_to_db: Whether to save notification to history
    
    Returns:
        int: Number of successful sends
    """
    from models.book import db, PushSubscription, Notification
    
    # Check user preferences
    subscriptions = PushSubscription.query.filter_by(
        user_id=user.id,
        is_active=True
    ).all()
    
    if not subscriptions:
        return 0
    
    # Filter by notification type preference
    filtered_subs = []
    for sub in subscriptions:
        if notification_type == 'usage_reset' and sub.notify_usage_reset:
            filtered_subs.append(sub)
        elif notification_type == 'new_feature' and sub.notify_new_features:
            filtered_subs.append(sub)
        elif notification_type == 'tip' and sub.notify_tips:
            filtered_subs.append(sub)
        elif notification_type == 'promo' and sub.notify_promotions:
            filtered_subs.append(sub)
        elif notification_type == 'general':
            filtered_subs.append(sub)
    
    success_count = 0
    for sub in filtered_subs:
        if send_push_notification(sub, title, body, url, notification_type):
            success_count += 1
    
    # Save notification to database
    if save_to_db:
        notification = Notification(
            user_id=user.id,
            title=title,
            body=body,
            notification_type=notification_type,
            url=url
        )
        db.session.add(notification)
    
    db.session.commit()
    
    return success_count


def send_broadcast_notification(title, body, url=None, notification_type='general'):
    """
    Send notification to all users with active subscriptions
    
    Args:
        title: Notification title
        body: Notification body
        url: URL to open
        notification_type: Type of notification
    
    Returns:
        dict: Stats about the broadcast
    """
    from models.book import db, PushSubscription, User
    
    # Get all active subscriptions
    subscriptions = PushSubscription.query.filter_by(is_active=True).all()
    
    total = len(subscriptions)
    success = 0
    failed = 0
    
    for sub in subscriptions:
        # Check preference
        should_send = False
        if notification_type == 'new_feature' and sub.notify_new_features:
            should_send = True
        elif notification_type == 'tip' and sub.notify_tips:
            should_send = True
        elif notification_type == 'promo' and sub.notify_promotions:
            should_send = True
        elif notification_type == 'general':
            should_send = True
        
        if should_send:
            if send_push_notification(sub, title, body, url, notification_type):
                success += 1
            else:
                failed += 1
    
    db.session.commit()
    
    return {
        'total': total,
        'success': success,
        'failed': failed
    }


def notify_usage_reset(user):
    """
    Notify user that their monthly usage has been reset
    """
    title = "🎉 Limite Mensal Reiniciado!"
    body = f"O teu limite de análises foi reiniciado. Tens agora {user.get_usage_limit()} análises disponíveis este mês!"
    url = "/explorer"
    
    return send_notification_to_user(user, title, body, url, 'usage_reset')


def notify_usage_warning(user, percentage):
    """
    Notify user when they're approaching their usage limit
    """
    title = f"⚠️ {percentage}% do Limite Usado"
    body = f"Já usaste {percentage}% das tuas análises mensais. Considera fazer upgrade para mais análises!"
    url = "/subscription/pricing"
    
    return send_notification_to_user(user, title, body, url, 'usage_reset')


def notify_new_feature(title, description, url='/explorer'):
    """
    Notify all users about a new feature
    """
    return send_broadcast_notification(
        title=f"✨ {title}",
        body=description,
        url=url,
        notification_type='new_feature'
    )


def check_and_reset_usage():
    """
    Check all users and reset monthly usage if needed.
    Should be called daily by a scheduled job.
    
    Returns:
        dict: Stats about resets
    """
    from models.book import db, User
    from datetime import datetime, timedelta
    
    today = datetime.utcnow().date()
    first_of_month = today.replace(day=1)
    
    # Find users whose usage should be reset
    users_to_reset = User.query.filter(
        (User.usage_reset_date == None) | 
        (User.usage_reset_date < first_of_month)
    ).all()
    
    reset_count = 0
    notified_count = 0
    
    for user in users_to_reset:
        old_usage = user.usage_count
        user.usage_count = 0
        user.usage_reset_date = datetime.utcnow()
        
        # Only notify if they had some usage
        if old_usage > 0:
            if notify_usage_reset(user) > 0:
                notified_count += 1
        
        reset_count += 1
    
    db.session.commit()
    
    return {
        'reset_count': reset_count,
        'notified_count': notified_count
    }
