"""
Security module for authentication and authorization.

Handles:
- Password hashing with bcrypt
- JWT token generation and validation
- Token refresh logic
- Password strength validation
"""

from datetime import datetime, timedelta
from typing import Optional

import jwt
import bcrypt

from src.config import settings


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        Hashed password string
    """
    # Encode password and hash it
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain text password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password from database

    Returns:
        True if password matches, False otherwise
    """
    try:
        password_bytes = plain_password.encode('utf-8')
        hashed_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hashed_bytes)
    except Exception:
        return False


def validate_password_strength(password: str) -> tuple[bool, Optional[str]]:
    """
    Validate password strength.

    Requirements:
    - At least 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    - At least one special character

    Args:
        password: Password to validate

    Returns:
        Tuple of (is_valid, error_message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters"

    if not any(c.isupper() for c in password):
        return False, "Password must contain at least one uppercase letter"

    if not any(c.islower() for c in password):
        return False, "Password must contain at least one lowercase letter"

    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit"

    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        return False, "Password must contain at least one special character"

    return True, None


def create_access_token(user_id: int, expires_in_hours: Optional[int] = None) -> str:
    """
    Create a JWT access token.

    Args:
        user_id: User ID to include in token
        expires_in_hours: Hours until token expires (defaults to settings)

    Returns:
        JWT token string

    Raises:
        Exception: If JWT configuration is invalid
    """
    if expires_in_hours is None:
        expires_in_hours = settings.jwt_expiration_hours

    expire = datetime.utcnow() + timedelta(hours=expires_in_hours)
    payload = {"sub": str(user_id), "exp": expire, "iat": datetime.utcnow(), "type": "access"}

    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token


def create_refresh_token(user_id: int) -> str:
    """
    Create a JWT refresh token.

    Args:
        user_id: User ID to include in token

    Returns:
        JWT token string
    """
    expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expiration_days)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "refresh",
    }

    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token


def decode_token(token: str) -> Optional[dict]:
    """
    Decode and validate a JWT token.

    Args:
        token: JWT token to decode

    Returns:
        Token payload dictionary if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def get_user_id_from_token(token: str) -> Optional[int]:
    """
    Extract user ID from a token.

    Args:
        token: JWT token

    Returns:
        User ID if token is valid, None otherwise
    """
    payload = decode_token(token)
    if payload and "sub" in payload:
        try:
            return int(payload["sub"])
        except (ValueError, TypeError):
            return None
    return None
