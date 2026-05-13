import os
import secrets

# Configuration file for BookCreatorAI
# Replace with your actual Gemini API key from https://makersuite.google.com/app/apikey

GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

# Database configuration
SQLALCHEMY_DATABASE_URI = 'sqlite:///database/books.db'
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Secret key for Flask sessions - generate secure key if not set
def get_secret_key():
    """Get or generate a secure secret key"""
    key = os.environ.get('SECRET_KEY')
    if key and key != 'your-secret-key-change-in-production':
        return key
    instance_dir = os.path.join(os.path.dirname(__file__), 'instance')
    key_file = os.path.join(instance_dir, '.secret_key')
    try:
        if os.path.exists(key_file):
            with open(key_file, 'r', encoding='utf-8') as f:
                stored = f.read().strip()
                if stored:
                    return stored
    except Exception:
        pass

    generated = secrets.token_hex(32)
    try:
        os.makedirs(instance_dir, exist_ok=True)
        with open(key_file, 'w', encoding='utf-8') as f:
            f.write(generated)
    except Exception:
        pass
    return generated

SECRET_KEY = get_secret_key()

# Stripe configuration
STRIPE_SECRET_KEY = os.environ.get('STRIPE_SECRET_KEY')
STRIPE_PUBLISHABLE_KEY = os.environ.get('STRIPE_PUBLISHABLE_KEY')
STRIPE_WEBHOOK_SECRET = os.environ.get('STRIPE_WEBHOOK_SECRET')

# Stripe Price IDs (create these in your Stripe Dashboard)
STRIPE_PRICES = {
    'pro_monthly': os.environ.get('STRIPE_PRICE_PRO_MONTHLY'),
    'pro_yearly': os.environ.get('STRIPE_PRICE_PRO_YEARLY'),
    'premium_monthly': os.environ.get('STRIPE_PRICE_PREMIUM_MONTHLY'),
    'premium_yearly': os.environ.get('STRIPE_PRICE_PREMIUM_YEARLY'),
}

# App URL for Stripe redirects
APP_URL = os.environ.get('APP_URL', 'http://localhost:5000')

# Security settings
SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'  # HTTPS only in production
SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to session cookie
SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = 3600  # 1 hour

# Rate limiting settings
RATE_LIMIT_ENABLED = True
RATE_LIMIT_DEFAULT = '100 per minute'  # For authenticated users
RATE_LIMIT_ANONYMOUS = '20 per minute'  # For anonymous users
RATE_LIMIT_API = '30 per minute'  # For API endpoints

# Cache settings
CACHE_TYPE = os.environ.get('CACHE_TYPE', 'simple')  # 'simple', 'redis', 'memcached'
CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes
CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

# Environment
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
DEBUG = FLASK_ENV == 'development'
