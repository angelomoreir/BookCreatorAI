import base64
import hashlib
from cryptography.fernet import Fernet, InvalidToken

import config

_FERNET_PREFIX = 'gAAAA'  # Fernet tokens always start with this


def _fernet():
    """Build a Fernet instance from the app secret key."""
    key = base64.urlsafe_b64encode(
        hashlib.sha256(config.SECRET_KEY.encode()).digest()
    )
    return Fernet(key)


def encrypt_value(value):
    """Encrypt a string for storage. Returns ciphertext (str) or the input if empty."""
    if not value:
        return value
    return _fernet().encrypt(value.encode()).decode()


def decrypt_value(value):
    """Decrypt a stored value. Legacy plaintext values (pre-encryption) are
    returned as-is so existing rows keep working until rotated."""
    if not value:
        return value
    if value.startswith(_FERNET_PREFIX):
        try:
            return _fernet().decrypt(value.encode()).decode()
        except InvalidToken:
            return None
    return value
