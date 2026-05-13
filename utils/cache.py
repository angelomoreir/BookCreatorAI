"""
Cache utilities for API responses and expensive operations.
Reduces API costs and improves response times.
"""
import hashlib
import json
import time
from functools import wraps
from threading import Lock

# Simple in-memory cache (replace with Redis in production)
_cache = {}
_cache_lock = Lock()


class SimpleCache:
    """Thread-safe in-memory cache with TTL support"""
    
    def __init__(self):
        self._cache = {}
        self._lock = Lock()
    
    def get(self, key):
        """Get value from cache if not expired"""
        with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if expiry is None or time.time() < expiry:
                    return value
                else:
                    del self._cache[key]
        return None
    
    def set(self, key, value, timeout=300):
        """Set value in cache with optional timeout (seconds)"""
        with self._lock:
            expiry = time.time() + timeout if timeout else None
            self._cache[key] = (value, expiry)
    
    def delete(self, key):
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self):
        """Clear all cache"""
        with self._lock:
            self._cache.clear()
    
    def cleanup(self):
        """Remove expired entries"""
        with self._lock:
            now = time.time()
            expired = [k for k, (v, exp) in self._cache.items() if exp and now >= exp]
            for k in expired:
                del self._cache[k]
    
    def stats(self):
        """Get cache statistics"""
        with self._lock:
            return {
                'entries': len(self._cache),
                'keys': list(self._cache.keys())[:20]  # First 20 keys
            }


# Global cache instance
cache = SimpleCache()


def generate_cache_key(*args, **kwargs):
    """Generate a unique cache key from arguments"""
    key_data = json.dumps({'args': args, 'kwargs': kwargs}, sort_keys=True, default=str)
    return hashlib.md5(key_data.encode()).hexdigest()


def cached(timeout=300, key_prefix=''):
    """
    Decorator to cache function results.
    
    Args:
        timeout: Cache timeout in seconds (default 5 minutes)
        key_prefix: Optional prefix for cache key
    
    Usage:
        @cached(timeout=600, key_prefix='book_analysis')
        def analyze_book(title, author):
            # Expensive API call
            return result
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{f.__name__}:{generate_cache_key(*args, **kwargs)}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Call function and cache result
            result = f(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        return decorated_function
    return decorator


def cache_ai_response(title, author, aspect, language, response, timeout=3600):
    """
    Cache an AI response for a book analysis.
    Uses longer timeout (1 hour default) since book content doesn't change.
    """
    key = f"ai:{aspect}:{generate_cache_key(title.lower(), author.lower() if author else '', language)}"
    cache.set(key, response, timeout)


def get_cached_ai_response(title, author, aspect, language):
    """Get cached AI response if available"""
    key = f"ai:{aspect}:{generate_cache_key(title.lower(), author.lower() if author else '', language)}"
    return cache.get(key)


def invalidate_book_cache(title, author=None):
    """Invalidate all cached responses for a specific book"""
    prefix = f"ai:"
    with cache._lock:
        keys_to_delete = [
            k for k in cache._cache.keys() 
            if k.startswith(prefix) and title.lower() in k.lower()
        ]
        for k in keys_to_delete:
            del cache._cache[k]
