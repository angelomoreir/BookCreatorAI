"""
Rate Limiting utilities for SaaS usage control
"""
from functools import wraps
from flask import jsonify, request
from flask_login import current_user
from datetime import datetime, timedelta
from models.book import db, PLAN_CONFIG


def check_and_reset_monthly_usage(user):
    """Check if monthly usage should be reset and reset if needed"""
    if user.usage_reset_date is None:
        # First time - set reset date to first of next month
        user.usage_reset_date = get_next_reset_date()
        user.usage_count = 0
        db.session.commit()
        return True
    
    now = datetime.utcnow()
    if now >= user.usage_reset_date:
        # Reset usage and set next reset date
        user.usage_count = 0
        user.usage_reset_date = get_next_reset_date()
        db.session.commit()
        return True
    
    return False


def get_next_reset_date():
    """Get the first day of next month as reset date"""
    now = datetime.utcnow()
    if now.month == 12:
        return datetime(now.year + 1, 1, 1)
    return datetime(now.year, now.month + 1, 1)


def get_days_until_reset(user):
    """Get number of days until usage resets"""
    if user.usage_reset_date is None:
        return 0
    
    now = datetime.utcnow()
    delta = user.usage_reset_date - now
    return max(0, delta.days)


def get_usage_info(user):
    """Get detailed usage information for a user"""
    check_and_reset_monthly_usage(user)
    
    plan_config = PLAN_CONFIG.get(user.plan, PLAN_CONFIG['free'])
    limit = plan_config['limits']['analyses_per_month']
    
    return {
        'plan': user.plan,
        'plan_name': plan_config['name'],
        'usage_count': user.usage_count,
        'usage_limit': limit,
        'usage_remaining': max(0, limit - user.usage_count),
        'usage_percentage': min(100, int((user.usage_count / limit) * 100)) if limit > 0 else 100,
        'reset_date': user.usage_reset_date.strftime('%Y-%m-%d') if user.usage_reset_date else None,
        'days_until_reset': get_days_until_reset(user),
        'is_limit_reached': user.usage_count >= limit
    }


def rate_limit(feature=None):
    """
    Decorator to enforce rate limiting based on user's plan.
    
    Args:
        feature: Optional feature name to check specific feature access
    
    Usage:
        @rate_limit()  # Just check usage limit
        @rate_limit(feature='quiz')  # Check usage limit + feature access
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Allow anonymous users with basic features (no rate limit tracking)
            if not current_user.is_authenticated:
                if feature:
                    # Anonymous users can't access premium features
                    return jsonify({
                        'success': False,
                        'error': 'Faça login para aceder a esta funcionalidade.',
                        'login_required': True
                    }), 401
                return f(*args, **kwargs)
            
            # Check and reset monthly usage if needed
            check_and_reset_monthly_usage(current_user)
            
            # Get plan configuration
            plan_config = PLAN_CONFIG.get(current_user.plan, PLAN_CONFIG['free'])
            limit = plan_config['limits']['analyses_per_month']
            
            # Check usage limit
            if current_user.usage_count >= limit:
                return jsonify({
                    'success': False,
                    'error': f'Limite mensal de {limit} análises atingido. Faça upgrade para continuar.',
                    'upgrade_required': True,
                    'usage_info': get_usage_info(current_user)
                }), 429  # Too Many Requests
            
            # Check feature access if specified
            if feature:
                features = plan_config.get('features', {})
                if not features.get(feature, False):
                    return jsonify({
                        'success': False,
                        'error': f'Esta funcionalidade requer plano Pro ou Premium.',
                        'upgrade_required': True,
                        'feature': feature,
                        'current_plan': current_user.plan
                    }), 403  # Forbidden
            
            # Increment usage counter
            current_user.usage_count += 1
            db.session.commit()
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def check_feature_access(feature):
    """
    Check if current user has access to a specific feature.
    Returns tuple (has_access, error_response)
    """
    if not current_user.is_authenticated:
        return False, {
            'success': False,
            'error': 'Faça login para aceder a esta funcionalidade.',
            'login_required': True
        }
    
    plan_config = PLAN_CONFIG.get(current_user.plan, PLAN_CONFIG['free'])
    features = plan_config.get('features', {})
    
    if not features.get(feature, False):
        return False, {
            'success': False,
            'error': f'Esta funcionalidade requer plano Pro ou Premium.',
            'upgrade_required': True,
            'feature': feature,
            'current_plan': current_user.plan
        }
    
    return True, None


def increment_usage_if_authenticated():
    """Increment usage counter for authenticated users"""
    if current_user.is_authenticated:
        check_and_reset_monthly_usage(current_user)
        current_user.usage_count += 1
        db.session.commit()
        return True
    return False


class UsageTracker:
    """
    Context manager for tracking usage with rollback capability.
    Useful when you want to only count usage on successful operations.
    
    Usage:
        with UsageTracker() as tracker:
            # Do operation
            if success:
                tracker.commit()  # Count this usage
            # If not committed, usage won't be counted
    """
    def __init__(self, user=None):
        self.user = user or (current_user if current_user.is_authenticated else None)
        self.committed = False
        self.original_count = None
    
    def __enter__(self):
        if self.user:
            check_and_reset_monthly_usage(self.user)
            self.original_count = self.user.usage_count
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self.committed and self.user and self.original_count is not None:
            # Rollback if not committed
            self.user.usage_count = self.original_count
            db.session.commit()
        return False
    
    def commit(self):
        """Commit the usage increment"""
        if self.user:
            self.user.usage_count = (self.original_count or 0) + 1
            db.session.commit()
            self.committed = True
    
    def can_proceed(self):
        """Check if user can proceed with operation"""
        if not self.user:
            return True
        
        plan_config = PLAN_CONFIG.get(self.user.plan, PLAN_CONFIG['free'])
        limit = plan_config['limits']['analyses_per_month']
        return self.user.usage_count < limit
