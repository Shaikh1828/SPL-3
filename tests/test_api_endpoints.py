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
                "password_confirm": "SecurePass123!",
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
                "password_confirm": "SecurePass123!",
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
            json={"name": "New Session", "round_number": 1},
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

    def test_upload_score_image(
        self, test_client: TestClient, test_session, test_session_archer, auth_headers
    ):
        """Test uploading and scoring a shot image."""
        mock_image = b"\xff\xd8\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
        
        session_id = test_session.id
        session_archer_id = test_session_archer.id
        
        response = test_client.post(
            f"/api/sessions/{session_id}/scores/upload",
            data={
                "session_archer_id": session_archer_id,
                "round": 1,
                "arrow_num": 1,
            },
            files={"file": ("shot.jpg", mock_image, "image/jpeg")},
            headers=auth_headers,
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "zone" in data
        assert "points" in data
        assert "image_id" in data

    def test_batch_score_directory(
        self, test_client: TestClient, test_session, test_session_archer, auth_headers
    ):
        """Test batch directory scoring endpoint."""
        import tempfile
        import shutil
        import os
        
        # Create a temp directory inside workspace
        temp_dir = tempfile.mkdtemp(dir=".")
        try:
            # Create mock images
            mock_image = b"\xff\xd8\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\' \",#\x1c\x1c(7),01444\x1f\'9=82<.342\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01\x00\x00?\x00\xbf\x00\xff\xd9"
            with open(os.path.join(temp_dir, "shot1.jpg"), "wb") as f:
                f.write(mock_image)
            with open(os.path.join(temp_dir, "shot2.png"), "wb") as f:
                f.write(mock_image)
                
            session_id = test_session.id
            session_archer_id = test_session_archer.id
            
            # 1. Dry run mode
            response = test_client.post(
                f"/api/sessions/{session_id}/scores/batch-directory",
                json={
                    "directory_path": temp_dir,
                    "session_archer_id": 0,
                    "round": 1,
                },
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["filename"] == "shot1.jpg"
            assert data[1]["filename"] == "shot2.png"
            assert data[0]["status"] == "success"
            
            # 2. Database record mode
            response = test_client.post(
                f"/api/sessions/{session_id}/scores/batch-directory",
                json={
                    "directory_path": temp_dir,
                    "session_archer_id": session_archer_id,
                    "round": 1,
                },
                headers=auth_headers,
            )
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2
            assert data[0]["score_id"] is not None
            
        finally:
            shutil.rmtree(temp_dir)

    def test_get_score_image_not_found(
        self, test_client: TestClient, test_score, auth_headers
    ):
        """Test getting score image when file does not exist."""
        # Score does not have image_id
        response = test_client.get(f"/api/scores/{test_score.id}/image", headers=auth_headers)
        assert response.status_code == 400  # "Score does not have an associated image"

    def test_override_score_forbidden(
        self, test_client: TestClient, test_score, auth_headers
    ):
        """Test that scorer cannot override score."""
        response = test_client.put(
            f"/api/scores/{test_score.id}/override",
            json={"zone": 10, "points": 10, "reason": "Manually corrected"},
            headers=auth_headers,
        )
        assert response.status_code == 403

    def test_override_score_admin_success(
        self, test_client: TestClient, test_db, test_score, admin_auth_headers
    ):
        """Test that admin can override score and it updates the total score and audit log."""
        # Get session archer initial total score
        session_archer = test_score.session_archer
        initial_score = session_archer.total_score
        
        response = test_client.put(
            f"/api/scores/{test_score.id}/override",
            json={"zone": 10, "points": 10, "reason": "Manually corrected"},
            headers=admin_auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["zone"] == 10
        assert data["points"] == 10
        
        # Verify database update
        test_db.refresh(test_score)
        test_db.refresh(session_archer)
        assert test_score.points == 10
        
        # Recalculate diff
        assert session_archer.total_score == recalculated_total_helper(test_db, session_archer.id)
        
        # Verify AuditLog entry
        from src.models.audit import AuditLog
        audit = test_db.query(AuditLog).filter(AuditLog.resource_id == test_score.id, AuditLog.action == "score_override").first()
        assert audit is not None
        assert "old_points" in audit.details
        assert "Manually corrected" in audit.details

def recalculated_total_helper(db, session_archer_id):
    from src.models.scoring import Score
    from sqlalchemy import func
    return db.query(func.sum(Score.points)).filter(Score.session_archer_id == session_archer_id).scalar() or 0


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
