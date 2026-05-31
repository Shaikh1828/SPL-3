"""
Integration tests for API endpoints.

Tests complete request/response flows for all major endpoints.
"""

import pytest
from fastapi.testclient import TestClient


# ============================================================================
# Authentication API Integration Tests
# ============================================================================


class TestAuthenticationAPI:
    """Integration tests for authentication endpoints."""

    def test_register_endpoint_success(self, test_client: TestClient):
        """Test user registration endpoint."""
        response = test_client.post(
            "/api/auth/register",
            json={
                "username": "newuser",
                "email": "new@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["username"] == "newuser"
        assert data["email"] == "new@example.com"

    def test_register_endpoint_duplicate_email(self, test_client: TestClient, test_user):
        """Test registration fails with duplicate email."""
        response = test_client.post(
            "/api/auth/register",
            json={
                "username": "otheruser",
                "email": "test@example.com",
                "password": "SecurePass123!",
            },
        )

        assert response.status_code == 409

    def test_login_endpoint_success(self, test_client: TestClient, test_user):
        """Test login endpoint."""
        response = test_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "TestPassword123!"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "Bearer"

    def test_login_endpoint_invalid_credentials(self, test_client: TestClient, test_user):
        """Test login fails with invalid credentials."""
        response = test_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "WrongPassword123!"},
        )

        assert response.status_code == 401

    def test_refresh_token_endpoint(self, test_client: TestClient, test_user):
        """Test token refresh endpoint."""
        # Get initial tokens
        login_response = test_client.post(
            "/api/auth/login",
            json={"username": "testuser", "password": "TestPassword123!"},
        )
        refresh_token = login_response.json()["refresh_token"]

        # Refresh
        response = test_client.post(
            "/api/auth/refresh",
            json={"refresh_token": refresh_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

    def test_reset_password_endpoint(
        self, test_client: TestClient, test_user, auth_headers
    ):
        """Test password reset endpoint."""
        response = test_client.post(
            "/api/auth/reset-password",
            json={
                "old_password": "TestPassword123!",
                "new_password": "NewPassword456!",
            },
            headers=auth_headers,
        )

        assert response.status_code == 200


# ============================================================================
# Tournament API Integration Tests
# ============================================================================


class TestTournamentAPI:
    """Integration tests for tournament endpoints."""

    def test_list_tournaments(self, test_client: TestClient, test_tournament):
        """Test listing tournaments."""
        response = test_client.get("/api/tournaments")

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    def test_create_tournament(self, test_client: TestClient, auth_headers):
        """Test creating tournament."""
        from datetime import datetime, timedelta

        response = test_client.post(
            "/api/tournaments",
            json={
                "name": "New Tournament",
                "location": "Test Location",
                "start_date": datetime.utcnow().isoformat(),
                "end_date": (datetime.utcnow() + timedelta(days=1)).isoformat(),
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Tournament"

    def test_get_tournament(self, test_client: TestClient, test_tournament):
        """Test getting tournament by ID."""
        response = test_client.get(f"/api/tournaments/{test_tournament.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_tournament.id
        assert data["name"] == "Test Tournament"


# ============================================================================
# Session API Integration Tests
# ============================================================================


class TestSessionAPI:
    """Integration tests for session endpoints."""

    def test_list_sessions(self, test_client: TestClient, test_tournament, test_session):
        """Test listing sessions."""
        response = test_client.get(
            f"/api/tournaments/{test_tournament.id}/sessions"
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    def test_create_session(self, test_client: TestClient, test_tournament, auth_headers):
        """Test creating session."""
        response = test_client.post(
            f"/api/tournaments/{test_tournament.id}/sessions",
            json={"name": "New Session"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "New Session"
        assert data["status"] == "active"

    def test_get_session(self, test_client: TestClient, test_session):
        """Test getting session by ID."""
        response = test_client.get(f"/api/sessions/{test_session.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_session.id

    def test_update_session_status(self, test_client: TestClient, test_session, auth_headers):
        """Test updating session status."""
        response = test_client.patch(
            f"/api/sessions/{test_session.id}",
            json={"status": "paused"},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"

    def test_add_archer_to_session(
        self, test_client: TestClient, test_session, auth_headers
    ):
        """Test adding archer to session."""
        response = test_client.post(
            f"/api/sessions/{test_session.id}/archers",
            json={"archer_id": 2, "archer_name": "New Archer"},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["archer_id"] == 2
        assert data["archer_name"] == "New Archer"


# ============================================================================
# Score API Integration Tests
# ============================================================================


class TestScoreAPI:
    """Integration tests for scoring endpoints."""

    def test_record_score(
        self, test_client: TestClient, test_session, test_session_archer, auth_headers
    ):
        """Test recording score."""
        response = test_client.post(
            f"/api/sessions/{test_session.id}/scores",
            json={
                "session_archer_id": test_session_archer.id,
                "round": 1,
                "arrow_num": 1,
                "zone": 8,
                "points": 8,
            },
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["zone"] == 8
        assert data["points"] == 8

    def test_list_session_scores(
        self, test_client: TestClient, test_session, test_score
    ):
        """Test listing scores in session."""
        response = test_client.get(f"/api/sessions/{test_session.id}/scores")

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0

    def test_get_score(self, test_client: TestClient, test_score):
        """Test getting score by ID."""
        response = test_client.get(f"/api/scores/{test_score.id}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_score.id

    def test_validate_score(
        self, test_client: TestClient, test_score, auth_headers
    ):
        """Test validating score."""
        response = test_client.post(
            f"/api/scores/{test_score.id}/validate",
            json={"validated": True},
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["validated_by_ai"] is True


# ============================================================================
# Camera API Integration Tests
# ============================================================================


class TestCameraAPI:
    """Integration tests for camera endpoints."""

    def test_list_session_cameras(
        self, test_client: TestClient, test_session, test_camera
    ):
        """Test listing cameras in session."""
        response = test_client.get(f"/api/sessions/{test_session.id}/cameras")

        assert response.status_code == 200
        # May be empty until camera assigned to session

    def test_connect_camera(
        self, test_client: TestClient, test_session, test_camera, auth_headers
    ):
        """Test connecting camera."""
        response = test_client.post(
            f"/api/sessions/{test_session.id}/cameras/{test_camera.id}/connect",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"

    def test_disconnect_camera(
        self, test_client: TestClient, test_session, test_camera, auth_headers
    ):
        """Test disconnecting camera."""
        response = test_client.post(
            f"/api/sessions/{test_session.id}/cameras/{test_camera.id}/disconnect",
            headers=auth_headers,
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "disconnected"

    def test_assign_camera_to_lane(
        self, test_client: TestClient, test_session, test_camera, auth_headers
    ):
        """Test assigning camera to lane."""
        response = test_client.post(
            f"/api/sessions/{test_session.id}/cameras/assign",
            json={"camera_id": test_camera.id, "lane": 1},
            headers=auth_headers,
        )

        assert response.status_code == 201
        data = response.json()
        assert data["lane"] == 1
        assert data["camera_id"] == test_camera.id


# ============================================================================
# Leaderboard API Integration Tests
# ============================================================================


class TestLeaderboardAPI:
    """Integration tests for leaderboard endpoints."""

    def test_get_leaderboard(self, test_client: TestClient, test_session):
        """Test getting leaderboard."""
        response = test_client.get(f"/api/sessions/{test_session.id}/leaderboard")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_leaderboard_skip_cache(self, test_client: TestClient, test_session):
        """Test getting leaderboard with cache bypass."""
        response = test_client.get(
            f"/api/sessions/{test_session.id}/leaderboard",
            params={"use_cache": False},
        )

        assert response.status_code == 200


# ============================================================================
# Health API Integration Tests
# ============================================================================


class TestHealthAPI:
    """Integration tests for health endpoints."""

    def test_health_check(self, test_client: TestClient):
        """Test basic health check."""
        response = test_client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["ok", "degraded", "down"]

    def test_detailed_health_check(self, test_client: TestClient):
        """Test detailed health check."""
        response = test_client.get("/api/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "components" in data


# ============================================================================
# Root API Integration Tests
# ============================================================================


class TestRootAPI:
    """Integration tests for root endpoint."""

    def test_root_endpoint(self, test_client: TestClient):
        """Test root endpoint."""
        response = test_client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "docs" in data
