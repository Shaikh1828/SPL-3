"""
FastAPI dependency injection functions.

Provides:
- Database session dependency
- Current user from JWT token
- Optional current user
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthCredentials
from sqlalchemy.orm import Session

from src.database import get_db
from src.security import get_user_id_from_token
from src.models.user import User

security = HTTPBearer()


def get_current_user(
    db: Session = Depends(get_db), credentials: HTTPAuthCredentials = Depends(security)
) -> User:
    """
    Get current authenticated user from JWT token.

    Args:
        db: Database session
        credentials: HTTP Bearer credentials

    Returns:
        Authenticated User object

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    # Decode token and get user ID
    user_id = get_user_id_from_token(token)

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Query user from database
    user = db.query(User).filter(User.id == user_id).first()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def get_optional_user(
    db: Session = Depends(get_db), credentials: Optional[HTTPAuthCredentials] = Depends(security)
) -> Optional[User]:
    """
    Get current user if authenticated, otherwise None.

    Args:
        db: Database session
        credentials: Optional HTTP Bearer credentials

    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None

    token = credentials.credentials
    user_id = get_user_id_from_token(token)

    if not user_id:
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if user and user.is_active:
        return user

    return None


def require_role(required_role: str):
    """
    Dependency factory for role-based access control.

    Args:
        required_role: Required role (admin, scorer, spectator, archer)

    Returns:
        Dependency function
    """

    def check_role(user: User = Depends(get_current_user)) -> User:
        if user.role != required_role and user.role != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires {required_role} role",
            )
        return user

    return check_role
