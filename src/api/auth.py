"""
Authentication API routes.

Story coverage: US-1.1 (registration), US-1.2 (password reset)
Endpoints:
- POST /auth/register
- POST /auth/login
- POST /auth/refresh
- POST /auth/reset-password
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
import structlog

from src.database import get_db
from src.services.auth_service import AuthService
from src.schemas import UserCreate, UserResponse, LoginRequest, LoginResponse, PasswordResetRequest, RefreshRequest
from src.dependencies import get_current_user
from src.models.user import User

logger = structlog.get_logger()

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    Story: US-1.1

    Args:
        user_data: Registration data (username, email, password)
        db: Database session

    Returns:
        Created user object

    Raises:
        HTTPException: 400 if validation fails, 409 if email already registered
    """
    try:
        user = AuthService.register_user(
            db, user_data.username, user_data.email, user_data.password
        )
        logger.info("user_registered_via_api", user_id=user.id, username=user.username)
        return user
    except ValueError as e:
        if "Username already exists" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Username already registered",
            )
        elif "Email already registered" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e),
            )
    except Exception as e:
        logger.exception("registration_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=LoginResponse)
async def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT tokens.

    Story: US-1.2

    Args:
        credentials: Login credentials (username, password)
        db: Database session

    Returns:
        Access token, refresh token, expiration

    Raises:
        HTTPException: 401 if credentials invalid
    """
    try:
        result = AuthService.login_user(db, credentials.username, credentials.password)

        if not result:
            logger.warning("login_failed_via_api", username=credentials.username)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
            )

        logger.info("login_success_via_api", username=credentials.username)
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("login_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@router.post("/refresh", response_model=LoginResponse)
async def refresh_token(body: RefreshRequest, db: Session = Depends(get_db)):
    """
    Refresh access token using refresh token.

    Story: US-1.2

    Args:
        body: Body containing refresh_token string
        db: Database session

    Returns:
        New access token

    Raises:
        HTTPException: 401 if refresh token invalid
    """
    try:
        refresh_token_str = body.refresh_token

        new_access_token = AuthService.refresh_access_token(refresh_token_str, db)

        if not new_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired refresh token",
            )

        logger.info("token_refreshed_via_api")

        return {
            "access_token": new_access_token,
            "refresh_token": refresh_token_str,
            "token_type": "Bearer",
            "expires_in": 28800,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("token_refresh_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.post("/reset-password", status_code=status.HTTP_200_OK)
async def reset_password(
    reset_data: PasswordResetRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Reset password for authenticated user.

    Story: US-1.2

    Args:
        reset_data: Old password and new password
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message

    Raises:
        HTTPException: 400 if validation fails
    """
    try:
        success = AuthService.reset_password(
            db,
            current_user.id,
            reset_data.old_password,
            reset_data.new_password,
        )

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset failed",
            )

        logger.info("password_reset_via_api", user_id=current_user.id)

        return {"success": True, "message": "Password reset successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("password_reset_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed",
        )
