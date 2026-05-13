"""
Security utilities for rate limiting, input validation, and IP blocking.
"""
import re
import time
import hashlib
from functools import wraps
from threading import Lock
from flask import request, jsonify, current_app
from flask_login import current_user


# In-memory rate limit storage (use Redis in production)
_rate_limits = {}
_rate_lock = Lock()


class RateLimiter:
    """
    Token bucket rate limiter with per-IP and per-user tracking.
    """
    
    def __init__(self):
        self._buckets = {}
        self._lock = Lock()
    
    def _get_key(self, identifier, endpoint=None):
        """Generate unique key for rate limiting"""
        if endpoint:
            return f"{identifier}:{endpoint}"
        return identifier
    
    def _parse_limit(self, limit_string):
        """Parse limit string like '100 per minute' into (count, seconds)"""
        match = re.match(r'(\d+)\s+per\s+(second|minute|hour|day)', limit_string.lower())
        if not match:
            return 100, 60  # Default: 100 per minute
        
        count = int(match.group(1))
        period = match.group(2)
        
        seconds = {
            'second': 1,
            'minute': 60,
            'hour': 3600,
            'day': 86400
        }.get(period, 60)
        
        return count, seconds
    
    def is_allowed(self, identifier, limit_string='100 per minute', endpoint=None):
        """
        Check if request is allowed under rate limit.
        Returns (allowed: bool, remaining: int, reset_time: int)
        """
        max_requests, window = self._parse_limit(limit_string)
        key = self._get_key(identifier, endpoint)
        now = time.time()
        
        with self._lock:
            if key not in self._buckets:
                self._buckets[key] = {
                    'tokens': max_requests - 1,
                    'last_update': now,
                    'window_start': now
                }
                return True, max_requests - 1, int(now + window)
            
            bucket = self._buckets[key]
            elapsed = now - bucket['last_update']
            
            # Refill tokens based on elapsed time
            refill_rate = max_requests / window
            bucket['tokens'] = min(max_requests, bucket['tokens'] + elapsed * refill_rate)
            bucket['last_update'] = now
            
            # Reset window if needed
            if now - bucket['window_start'] >= window:
                bucket['window_start'] = now
                bucket['tokens'] = max_requests
            
            if bucket['tokens'] >= 1:
                bucket['tokens'] -= 1
                remaining = int(bucket['tokens'])
                reset_time = int(bucket['window_start'] + window)
                return True, remaining, reset_time
            else:
                reset_time = int(bucket['window_start'] + window)
                return False, 0, reset_time
    
    def cleanup(self, max_age=3600):
        """Remove old entries to prevent memory leaks"""
        now = time.time()
        with self._lock:
            expired = [
                k for k, v in self._buckets.items()
                if now - v['last_update'] > max_age
            ]
            for k in expired:
                del self._buckets[k]


# Global rate limiter instance
rate_limiter = RateLimiter()


def get_client_ip():
    """Get real client IP, considering proxies"""
    # Check for forwarded IP (behind proxy/load balancer)
    if request.headers.get('X-Forwarded-For'):
        return request.headers.get('X-Forwarded-For').split(',')[0].strip()
    if request.headers.get('X-Real-IP'):
        return request.headers.get('X-Real-IP')
    return request.remote_addr


def rate_limit(limit=None, per_user=True, per_ip=True):
    """
    Decorator for rate limiting endpoints.
    
    Args:
        limit: Rate limit string (e.g., '30 per minute')
        per_user: Apply limit per authenticated user
        per_ip: Apply limit per IP address
    
    Usage:
        @rate_limit('30 per minute')
        def api_endpoint():
            ...
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            import config
            
            if not getattr(config, 'RATE_LIMIT_ENABLED', True):
                return f(*args, **kwargs)
            
            # Determine limit
            if limit:
                rate_limit_str = limit
            elif current_user.is_authenticated:
                rate_limit_str = getattr(config, 'RATE_LIMIT_DEFAULT', '100 per minute')
            else:
                rate_limit_str = getattr(config, 'RATE_LIMIT_ANONYMOUS', '20 per minute')
            
            # Get identifier
            identifiers = []
            if per_ip:
                identifiers.append(f"ip:{get_client_ip()}")
            if per_user and current_user.is_authenticated:
                identifiers.append(f"user:{current_user.id}")
            
            # Check all identifiers
            for identifier in identifiers:
                allowed, remaining, reset_time = rate_limiter.is_allowed(
                    identifier, 
                    rate_limit_str,
                    endpoint=request.endpoint
                )
                
                if not allowed:
                    response = jsonify({
                        'success': False,
                        'error': 'Demasiados pedidos. Por favor aguarde.',
                        'rate_limited': True,
                        'retry_after': reset_time - int(time.time())
                    })
                    response.status_code = 429
                    response.headers['X-RateLimit-Limit'] = rate_limit_str
                    response.headers['X-RateLimit-Remaining'] = '0'
                    response.headers['X-RateLimit-Reset'] = str(reset_time)
                    response.headers['Retry-After'] = str(reset_time - int(time.time()))
                    return response
            
            # Add rate limit headers to response
            result = f(*args, **kwargs)
            
            # If result is a tuple (response, status_code), handle it
            if isinstance(result, tuple):
                return result
            
            return result
        return decorated_function
    return decorator


# ==================== INPUT VALIDATION ====================

def sanitize_string(value, max_length=500, allow_html=False):
    """
    Sanitize string input to prevent XSS and injection attacks.
    """
    if not value:
        return ''
    
    value = str(value).strip()
    
    # Truncate to max length
    if len(value) > max_length:
        value = value[:max_length]
    
    if not allow_html:
        # Remove/escape HTML tags
        value = re.sub(r'<[^>]+>', '', value)
        # Escape special characters
        value = value.replace('&', '&amp;')
        value = value.replace('<', '&lt;')
        value = value.replace('>', '&gt;')
        value = value.replace('"', '&quot;')
        value = value.replace("'", '&#x27;')
    
    return value


def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_book_title(title):
    """Validate book title"""
    if not title or len(title.strip()) < 1:
        return False, 'Título é obrigatório'
    if len(title) > 500:
        return False, 'Título demasiado longo (máx. 500 caracteres)'
    return True, None


def validate_author(author):
    """Validate author name"""
    if author and len(author) > 300:
        return False, 'Nome do autor demasiado longo (máx. 300 caracteres)'
    return True, None


# ==================== IP BLOCKING ====================

def is_ip_blocked(ip_address):
    """Check if IP is blocked"""
    from models.book import BlockedIP
    from datetime import datetime
    
    blocked = BlockedIP.query.filter_by(ip_address=ip_address, is_active=True).first()
    
    if blocked:
        # Check if block has expired
        if blocked.expires_at and blocked.expires_at < datetime.utcnow():
            blocked.is_active = False
            from models.book import db
            db.session.commit()
            return False
        return True
    
    return False


def check_blocked_ip():
    """Middleware function to check if current IP is blocked"""
    ip = get_client_ip()
    if is_ip_blocked(ip):
        return jsonify({
            'success': False,
            'error': 'Acesso bloqueado. Contacte o suporte.',
            'blocked': True
        }), 403
    return None


# ==================== SECURITY HEADERS ====================

def add_security_headers(response):
    """Add security headers to response"""
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'SAMEORIGIN'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    
    # Content Security Policy (adjust as needed)
    csp = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://js.stripe.com; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "connect-src 'self' https://api.stripe.com; "
        "frame-src https://js.stripe.com;"
    )
    response.headers['Content-Security-Policy'] = csp
    
    return response
