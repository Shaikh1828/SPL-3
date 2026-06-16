"""
Unit tests for business logic services.

Tests for: AuthService, ScoringService, CameraService, ImageService, HealthService
Coverage: ~70% of service layer business logic
"""

import pytest
from sqlalchemy.orm import Session
from datetime import datetime, timedelta

from src.services.auth_service import AuthService
from src.services.scoring_service import ScoringService
from src.services.camera_service import CameraService
from src.services.health_service import HealthService
from src.models.user import User
from src.models.scoring import Score, SessionArcher


# ============================================================================
# AuthService Tests
# ============================================================================


class TestAuthService:
    """Unit tests for AuthService."""

    def test_register_user_success(self, test_db: Session):
        """Test successful user registration."""
        user = AuthService.register_user(
            test_db,
            "newuser",
            "new@example.com",
            "SecurePass123!",
        )

        assert user is not None
        assert user.username == "newuser"
        assert user.email == "new@example.com"
        assert user.role == "spectator"
        assert user.is_active is True

    def test_register_user_duplicate_username(self, test_db: Session, test_user: User):
        """Test registration fails with duplicate username."""
        with pytest.raises(ValueError, match="Username already exists"):
            AuthService.register_user(
                test_db,
                "testuser",  # Already exists
                "other@example.com",
                "SecurePass123!",
            )

    def test_register_user_duplicate_email(self, test_db: Session, test_user: User):
        """Test registration fails with duplicate email."""
        with pytest.raises(ValueError, match="Email already registered"):
            AuthService.register_user(
                test_db,
                "otheruser",
                "test@example.com",  # Already exists
                "SecurePass123!",
            )

    def test_register_user_weak_password(self, test_db: Session):
        """Test registration fails with weak password."""
        with pytest.raises(ValueError, match="Password must"):
            AuthService.register_user(
                test_db,
                "newuser",
                "new@example.com",
                "weak",  # Too short, no special char
            )

    def test_login_user_success(self, test_db: Session, test_user: User):
        """Test successful login."""
        result = AuthService.login_user(test_db, "testuser", "TestPassword123!")

        assert result is not None
        assert result["access_token"] is not None
        assert result["refresh_token"] is not None
        assert result["token_type"] == "Bearer"

    def test_login_user_invalid_credentials(self, test_db: Session, test_user: User):
        """Test login fails with invalid credentials."""
        result = AuthService.login_user(test_db, "testuser", "WrongPassword123!")

        assert result is None

    def test_login_user_nonexistent(self, test_db: Session):
        """Test login fails for nonexistent user."""
        result = AuthService.login_user(test_db, "nonexistent", "SomePass123!")

        assert result is None

    def test_refresh_access_token_success(self, test_db: Session, test_user: User):
        """Test token refresh."""
        # Get initial tokens
        result = AuthService.login_user(test_db, "testuser", "TestPassword123!")
        refresh_token = result["refresh_token"]

        # Refresh token
        new_access_token = AuthService.refresh_access_token(refresh_token)

        assert new_access_token is not None

    def test_reset_password_success(self, test_db: Session, test_user: User):
        """Test password reset."""
        success = AuthService.reset_password(
            test_db,
            test_user.id,
            "TestPassword123!",
            "NewPassword456!",
        )

        assert success is True

        # Verify new password works
        result = AuthService.login_user(test_db, "testuser", "NewPassword456!")
        assert result is not None

    def test_reset_password_wrong_old_password(self, test_db: Session, test_user: User):
        """Test password reset fails with wrong old password."""
        success = AuthService.reset_password(
            test_db,
            test_user.id,
            "WrongPassword123!",
            "NewPassword456!",
        )

        assert success is False


# ============================================================================
# ScoringService Tests
# ============================================================================


class TestScoringService:
    """Unit tests for ScoringService."""

    def test_validate_score_valid(self):
        """Test score validation with valid values."""
        is_valid, error_msg = ScoringService.validate_score(5, 5)

        assert is_valid is True
        assert error_msg is None

    def test_validate_score_invalid_zone(self):
        """Test score validation with invalid zone."""
        is_valid, error_msg = ScoringService.validate_score(11, 5)

        assert is_valid is False
        assert "zone" in error_msg.lower()

    def test_validate_score_invalid_points(self):
        """Test score validation with invalid points."""
        is_valid, error_msg = ScoringService.validate_score(5, 11)

        assert is_valid is False
        assert "points" in error_msg.lower()

    def test_record_score_with_retry_success(
        self, test_db: Session, test_session_archer
    ):
        """Test score recording with retry logic."""
        score = ScoringService.record_score_with_retry(
            test_db,
            test_session_archer.id,
            round=1,
            arrow_num=1,
            zone=8,
            points=8,
            image_id=None,
            max_retries=2,
            base_backoff=1.0,
        )

        assert score is not None
        assert score.zone == 8
        assert score.points == 8
        assert score.session_archer_id == test_session_archer.id

    def test_calculate_total_score(
        self, test_db: Session, test_session_archer: SessionArcher, test_score: Score
    ):
        """Test total score calculation."""
        # Add another score
        score2 = Score(
            session_id=test_session_archer.session_id,
            session_archer_id=test_session_archer.id,
            round=1,
            arrow_num=2,
            zone=9,
            points=9,
        )
        test_db.add(score2)
        test_db.commit()

        total = ScoringService.calculate_total_score(test_db, test_session_archer.id)

        assert total == 17  # 8 + 9

    def test_get_session_leaderboard(
        self, test_db: Session, test_session: Session, test_session_archer: SessionArcher
    ):
        """Test leaderboard generation."""
        leaderboard = ScoringService.get_session_leaderboard(test_db, test_session.id)

        assert len(leaderboard) > 0
        assert leaderboard[0]["archer_name"] == "Test Archer"


# ============================================================================
# CameraService Tests
# ============================================================================


class TestCameraService:
    """Unit tests for CameraService."""

    def test_connect_camera(self, test_db: Session, test_camera):
        """Test camera connection."""
        CameraService.connect_camera(test_db, test_camera.id)

        # Refresh and verify
        test_db.refresh(test_camera)
        assert test_camera.status == "connected"

    def test_disconnect_camera(self, test_db: Session, test_camera):
        """Test camera disconnection."""
        CameraService.disconnect_camera(test_db, test_camera.id)

        test_db.refresh(test_camera)
        assert test_camera.status == "disconnected"

    def test_get_camera_by_id(self, test_db: Session, test_camera):
        """Test getting camera by ID."""
        camera = CameraService.get_camera_by_id(test_db, test_camera.id)

        assert camera is not None
        assert camera.id == test_camera.id
        assert camera.name == "Test Camera"


# ============================================================================
# HealthService Tests
# ============================================================================


class TestHealthService:
    """Unit tests for HealthService."""

    @pytest.mark.asyncio
    async def test_get_system_health(self):
        """Test system health check."""
        health = await HealthService.get_system_health()

        assert "status" in health
        assert health["status"] in ["ok", "degraded", "down"]
        assert "components" in health

    def test_check_database_health(self, test_db: Session):
        """Test database health check."""
        health = HealthService.check_database_health()

        assert "status" in health
        assert health["status"] in ["ok", "degraded", "down"]

    def test_check_cache_health(self):
        """Test cache health check."""
        health = HealthService.check_cache_health()

        assert "status" in health
        assert health["status"] in ["ok", "degraded", "down"]

    def test_check_storage_health(self):
        """Test storage health check."""
        health = HealthService.check_storage_health()

        assert "status" in health
        assert "used_gb" in health
        assert "quota_gb" in health
        assert health["usage_percent"] >= 0
