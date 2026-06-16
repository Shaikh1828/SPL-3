"""
Authentication service for user registration, login, and token management.

Story coverage: US-1.1 (registration), US-1.2 (password reset)
"""

from typing import Optional, Tuple
from sqlalchemy.orm import Session
import structlog

from src.models.user import User
from src.security import hash_password, verify_password, validate_password_strength
from src.security import create_access_token, create_refresh_token, decode_token, get_user_id_from_token

logger = structlog.get_logger()


class AuthService:
    """Authentication business logic service."""

    @staticmethod
    def register_user(db: Session, username: str, email: str, password: str) -> Optional[User]:
        """
        Register a new user.

        Args:
            db: Database session
            username: Desired username
            email: Email address
            password: Plain text password

        Returns:
            Created User object or None if registration fails

        Raises:
            ValueError: If validation fails (duplicate email/username, weak password)
        """
        # Validate password strength
        is_valid, error_msg = validate_password_strength(password)
        if not is_valid:
            raise ValueError(f"Password validation failed: {error_msg}")

        # Check for duplicate username
        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            raise ValueError("Username already exists")

        # Check for duplicate email
        existing_email = db.query(User).filter(User.email == email).first()
        if existing_email:
            raise ValueError("Email already registered")

        # Hash password and create user
        password_hash = hash_password(password)
        user = User(
            username=username,
            email=email,
            password_hash=password_hash,
            role="spectator",  # Default role
            is_active=True,
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        logger.info("user_registered", user_id=user.id, username=username)
        return user

    @staticmethod
    def login_user(db: Session, username: str, password: str) -> Optional[dict]:
        """
        Authenticate user and return tokens.

        Args:
            db: Database session
            username: Username
            password: Plain text password

        Returns:
            Dictionary with access_token, refresh_token, token_type, expires_in or None if login fails
        """
        # Query user by username
        user = db.query(User).filter(User.username == username).first()
        if not user:
            logger.warning("login_failed", username=username, reason="user_not_found")
            return None

        # Verify password
        if not verify_password(password, user.password_hash):
            logger.warning("login_failed", user_id=user.id, reason="invalid_password")
            return None

        if not user.is_active:
            logger.warning("login_failed", user_id=user.id, reason="user_inactive")
            return None

        # Generate tokens
        access_token = create_access_token(user.id, role=user.role)
        refresh_token = create_refresh_token(user.id)

        logger.info("user_login_success", user_id=user.id, username=username)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "Bearer",
            "expires_in": 28800,  # 8 hours in seconds
        }

    @staticmethod
    def verify_token(token: str) -> Optional[int]:
        """
        Verify a JWT token and return user ID.

        Args:
            token: JWT token string

        Returns:
            User ID if token is valid, None otherwise
        """
        user_id = get_user_id_from_token(token)
        if user_id:
            logger.debug("token_verified", user_id=user_id)
        else:
            logger.warning("token_verification_failed")
        return user_id

    @staticmethod
    def refresh_access_token(refresh_token: str, db: Session = None) -> Optional[str]:
        """
        Generate a new access token from a refresh token.

        Args:
            refresh_token: Refresh token string
            db: Database session (optional, used to lookup current role)

        Returns:
            New access token or None if refresh token invalid
        """
        payload = decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            logger.warning("refresh_token_invalid")
            return None

        user_id = get_user_id_from_token(refresh_token)
        if not user_id:
            logger.warning("refresh_token_decode_failed")
            return None

        # Look up current role from DB if session provided
        role = "spectator"
        if db is not None:
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                role = user.role

        new_access_token = create_access_token(user_id, role=role)
        logger.info("access_token_refreshed", user_id=user_id)
        return new_access_token

    @staticmethod
    def reset_password(db: Session, user_id: int, old_password: str, new_password: str) -> bool:
        """
        Reset user password.

        Args:
            db: Database session
            user_id: User ID
            old_password: Current password for verification
            new_password: New password

        Returns:
            True if successful, False otherwise
        """
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            logger.warning("password_reset_failed", user_id=user_id, reason="user_not_found")
            return False

        # Verify old password
        if not verify_password(old_password, user.password_hash):
            logger.warning("password_reset_failed", user_id=user_id, reason="invalid_password")
            return False

        # Validate new password strength
        is_valid, error_msg = validate_password_strength(new_password)
        if not is_valid:
            logger.warning("password_reset_failed", user_id=user_id, reason=f"weak_password: {error_msg}")
            return False

        # Update password
        user.password_hash = hash_password(new_password)
        db.commit()

        logger.info("password_reset_success", user_id=user_id)
        return True

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> Optional[User]:
        """Get user by ID."""
        return db.query(User).filter(User.id == user_id).first()

    @staticmethod
    def get_user_by_username(db: Session, username: str) -> Optional[User]:
        """Get user by username."""
        return db.query(User).filter(User.username == username).first()
