"""Password hashing (Argon2id) and session token generation."""

import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError

SESSION_COOKIE = "dossier_session"
CSRF_COOKIE = "dossier_csrf"
CSRF_HEADER = "x-csrf-token"

_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password with Argon2id (SEC-2 / FR-2).

    Args:
        password (str): The plaintext password.

    Returns:
        str: The salted Argon2id hash.
    """
    return _hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """Verify a plaintext password against a stored hash.

    Args:
        password_hash (str): The stored Argon2id hash.
        password (str): The plaintext password to check.

    Returns:
        bool: True if the password matches.
    """
    try:
        return _hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError):
        return False


def new_token() -> str:
    """Generate a cryptographically random token for sessions and CSRF.

    Returns:
        str: A URL-safe 256-bit random token.
    """
    return secrets.token_urlsafe(32)
