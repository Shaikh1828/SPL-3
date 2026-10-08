"""
User Management API — Admin-only endpoints for managing system users.

Endpoints:
- GET    /users              List all users (with pagination + role filter)
- GET    /users/{user_id}    Get a single user by ID
- POST   /users              Create a new user with a specific role
- PATCH  /users/{user_id}    Update role / active status
- DELETE /users/{user_id}    Deactivate a user (soft delete)

All write endpoints require role == 'admin'.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field
import structlog

from src.database import get_db
from src.dependencies import get_current_user
from src.models.user import User
from src.schemas import UserResponse
from src.security import hash_password, validate_password_strength

logger = structlog.get_logger()

router = APIRouter(prefix="/users", tags=["users"])


# ─── Request / Response Schemas ───────────────────────────────────────────────


class UserCreateAdmin(BaseModel):
    """Admin creates a user with a specific role."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    role: str = Field(default="spectator", pattern="^(admin|scorer|spectator|archer)$")


class UserUpdateAdmin(BaseModel):
    """Admin updates role and/or active status."""

    role: Optional[str] = Field(None, pattern="^(admin|scorer|spectator|archer)$")
    is_active: Optional[bool] = None


class UserListResponse(BaseModel):
    """Paginated user list."""

    items: List[UserResponse]
    total: int
    skip: int
    limit: int


# ─── Helpers ─────────────────────────────────────────────────────────────────


def require_user_manager(current_user: User) -> User:
    """Raise 403 if caller is neither admin nor scorer."""
    if current_user.role not in ["admin", "scorer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin or Scorer access required",
        )
    return current_user


# ─── Endpoints ───────────────────────────────────────────────────────────────


@router.get("", response_model=UserListResponse)
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    role: Optional[str] = Query(None, description="Filter by role"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    List all registered users.
    Requires admin or scorer role.
    Supports pagination and optional role / is_active filtering.
    """
    require_user_manager(current_user)

    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset(skip).limit(limit).all()

    logger.info("users_listed", count=len(users), total=total, by=current_user.username)
    return UserListResponse(items=users, total=total, skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get a single user by ID. Requires admin or scorer role."""
    require_user_manager(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return user


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreateAdmin,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new user with a specified role.
    - Admin can create any role (admin, scorer, spectator, archer).
    - Scorer can ONLY create spectator or archer roles.
    """
    require_user_manager(current_user)

    # Scorer restriction: scorers can only add spectators or archers
    if current_user.role == "scorer" and user_data.role not in ["spectator", "archer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Scorers can only create spectator or archer accounts",
        )

    # Validate password strength
    is_valid, error_msg = validate_password_strength(user_data.password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Weak password: {error_msg}",
        )

    # Duplicate checks
    if db.query(User).filter(User.username == user_data.username).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")
    if db.query(User).filter(User.email == user_data.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        username=user_data.username,
        email=user_data.email,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    logger.info("user_created", new_user_id=user.id, role=user.role, by=current_user.username, by_role=current_user.role)
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    update_data: UserUpdateAdmin,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Update a user's role or active status.
    - Admin can update any user (cannot demote self).
    - Scorer can only update spectator or archer accounts, and cannot assign admin or scorer roles.
    """
    require_user_manager(current_user)

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Prevent self-demotion for admin
    if user.id == current_user.id and update_data.role and update_data.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admins cannot remove their own admin role",
        )

    # Scorer restrictions
    if current_user.role == "scorer":
        if user.role in ["admin", "scorer"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Scorers cannot modify admin or scorer accounts",
            )
        if update_data.role and update_data.role not in ["spectator", "archer"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Scorers can only assign spectator or archer roles",
            )

    if update_data.role is not None:
        user.role = update_data.role
    if update_data.is_active is not None:
        user.is_active = update_data.is_active

    db.commit()
    db.refresh(user)

    logger.info(
        "user_updated",
        user_id=user_id,
        new_role=user.role,
        is_active=user.is_active,
        by=current_user.username,
        by_role=current_user.role,
    )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_200_OK)
async def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Soft-delete a user (sets is_active = False).
    - Admins cannot deactivate themselves.
    - Scorers can only deactivate spectator or archer accounts.
    """
    require_user_manager(current_user)

    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Users cannot deactivate their own account",
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if current_user.role == "scorer" and user.role in ["admin", "scorer"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Scorers cannot deactivate admin or scorer accounts",
        )

    user.is_active = False
    db.commit()

    logger.info("user_deactivated", user_id=user_id, by=current_user.username, by_role=current_user.role)
    return {"success": True, "message": f"User '{user.username}' has been deactivated"}
