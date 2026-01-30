from cryptography.fernet import Fernet
from app.config import settings
import base64
import hashlib


def _get_fernet() -> Fernet:
    """
    Create a Fernet instance using a stable key derived from JWT secret.
    """
    # Derive a 32-byte key from JWT secret (stable across restarts)
    secret = settings.jwt_secret_key.encode()
    key = base64.urlsafe_b64encode(hashlib.sha256(secret).digest())
    return Fernet(key)


def encrypt_token(token: str) -> str:
    """
    Encrypt sensitive tokens before storing in DB.
    """
    f = _get_fernet()
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted_token: str) -> str:
    """
    Decrypt sensitive tokens for API usage.
    """
    f = _get_fernet()
    return f.decrypt(encrypted_token.encode()).decode()
