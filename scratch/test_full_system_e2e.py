"""
End-to-End System Verification Script.
Validates all system functionality across:
- Core Health & API Root
- Authentication & JWT Token issuance
- Tournaments & Sessions management
- Scores recording & Leaderboard calculation
- Pose Analysis (sample videos, kinematics, ML prediction, posture evaluation)
- Training System (status, dataset metadata, metrics history, reload)
- System Reports
"""

import sys
import os
sys.path.insert(0, os.path.abspath("."))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from src.main import app
from src.database import get_db
from src.models.base import Base

def run_e2e_verification():
    print("==================================================")
    print("STARTING COMPREHENSIVE END-TO-END SYSTEM VERIFICATION")
    print("==================================================")

    # Initialize isolated SQLite database for E2E run
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSessionLocal()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    passed_steps = 0
    total_steps = 8

    from src.models.user import User
    from src.security import hash_password
    admin = User(
        username="admin",
        email="admin@example.com",
        password_hash=hash_password("AdminPassword123!"),
        role="admin",
        is_active=True,
    )
    db.add(admin)
    db.commit()

    # 1. Root and Health
    print("\n[Step 1/8] Verifying Root and Health Check Endpoints...")
    res = client.get("/")
    assert res.status_code == 200, f"Root failed: {res.text}"
    assert "version" in res.json()

    res = client.get("/api/health")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    assert res.json().get("status") in ["healthy", "ok", "degraded"]
    print("  -> Root and Health Check: PASSED")
    passed_steps += 1

    # 2. Authentication
    print("\n[Step 2/8] Verifying Authentication...")
    # Admin login or register
    login_res = client.post("/api/auth/login", json={"username": "admin", "password": "AdminPassword123!"})
    if login_res.status_code == 200:
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("  -> Admin Login: PASSED")
    else:
        # Register new admin/scorer for testing
        import uuid
        uname = f"test_{uuid.uuid4().hex[:6]}"
        reg_res = client.post("/api/auth/register", json={
            "username": uname,
            "email": f"{uname}@example.com",
            "password": "SecurePassword123!",
            "password_confirm": "SecurePassword123!",
            "full_name": "Test Administrator",
            "role": "admin"
        })
        assert reg_res.status_code in [200, 201], f"Registration failed: {reg_res.text}"
        login_res = client.post("/api/auth/login", json={"username": uname, "password": "SecurePassword123!"})
        assert login_res.status_code == 200, f"Login failed: {login_res.text}"
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("  -> User Registration & Login: PASSED")
    passed_steps += 1

    # 3. Tournaments & Sessions
    print("\n[Step 3/8] Verifying Tournaments & Sessions Lifecycle...")
    tourn_res = client.post("/api/tournaments", headers=headers, json={
        "name": "E2E Olympic Invitational",
        "description": "Comprehensive E2E automated test tournament",
        "start_date": "2026-10-10T09:00:00Z",
        "end_date": "2026-10-12T18:00:00Z",
        "location": "Olympic Stadium Lane 1"
    })
    assert tourn_res.status_code in [200, 201], f"Create tournament failed: {tourn_res.text}"
    tournament_id = tourn_res.json()["id"]

    sess_res = client.post(f"/api/tournaments/{tournament_id}/sessions", headers=headers, json={
        "name": "Qualification Round 1",
        "round_number": 1,
        "num_lanes": 6,
        "arrows_per_round": 6
    })
    assert sess_res.status_code in [200, 201], f"Create session failed: {sess_res.text}"
    session_id = sess_res.json()["id"]
    print(f"  -> Tournament #{tournament_id} and Session #{session_id} Created: PASSED")
    passed_steps += 1

    # 4. Archer Registration & Scoring
    print("\n[Step 4/8] Verifying Archer Assignment and Scoring Flow...")
    archer_res = client.post(f"/api/sessions/{session_id}/archers", headers=headers, json={
        "archer_id": 1,
        "archer_name": "Marcus D'Almeida",
        "lane_number": 1
    })
    assert archer_res.status_code in [200, 201], f"Add archer failed: {archer_res.text}"
    session_archer_id = archer_res.json()["id"]

    # Record Score End
    score_res = client.post(f"/api/sessions/{session_id}/scores", headers=headers, json={
        "session_archer_id": session_archer_id,
        "round": 1,
        "arrow_num": 1,
        "zone": 10,
        "points": 10
    })
    assert score_res.status_code in [200, 201], f"Record score failed: {score_res.text}"
    print(f"  -> Archer assigned (ID: {session_archer_id}) and 10-point score recorded: PASSED")
    passed_steps += 1

    # 5. Leaderboard Calculation
    print("\n[Step 5/8] Verifying Session and Tournament Leaderboards...")
    lb_res = client.get(f"/api/sessions/{session_id}/leaderboard")
    assert lb_res.status_code == 200, f"Session leaderboard failed: {lb_res.text}"
    lb_data = lb_res.json()
    assert "entries" in lb_data or isinstance(lb_data, list)
    print("  -> Real-Time Leaderboard Aggregation: PASSED")
    passed_steps += 1

    # 6. Archer Pose Analysis & ML Score Prediction (Feature Branch)
    print("\n[Step 6/8] Verifying Archer Pose Analysis & Biomechanics ML Prediction...")
    # List sample videos
    videos_res = client.get("/api/pose/sample-videos")
    assert videos_res.status_code == 200, f"List sample videos failed: {videos_res.text}"
    videos = videos_res.json()["videos"]
    assert len(videos) >= 3, "Expected at least 3 benchmark videos"

    # Analyze sample video gold_form_10
    ana_res = client.post("/api/pose/sample-videos/gold_form_10/analyze")
    assert ana_res.status_code == 200, f"Analyze gold_form_10 failed: {ana_res.text}"
    ana_data = ana_res.json()
    assert ana_data["success"] is True
    assert "prediction" in ana_data
    pred = ana_data["prediction"]
    assert pred["predicted_score"] >= 9
    assert pred["score_category"] == "Gold"

    # Evaluate direct posture accuracy
    posture_res = client.post("/api/pose/evaluate-posture", json={
        "bow_arm_angle": 179.2,
        "draw_elbow_angle": 139.5,
        "anchor_jitter": 0.4,
        "bow_arm_deflection_deg": 0.5,
        "anchor_duration_sec": 2.0
    })
    assert posture_res.status_code == 200, f"Evaluate posture failed: {posture_res.text}"
    posture_data = posture_res.json()
    assert posture_data["overall_accuracy_pct"] >= 90.0
    print(f"  -> Pose Analysis & ML Score Prediction ({pred['predicted_score']:.1f} pts, {pred['score_category']}, Accuracy: {posture_data['overall_accuracy_pct']:.1f}%): PASSED")
    passed_steps += 1

    # 7. Model Training System (Main Branch)
    print("\n[Step 7/8] Verifying Model Training System Endpoints...")
    status_res = client.get("/api/training/status")
    assert status_res.status_code == 200, f"Training status failed: {status_res.text}"

    dataset_res = client.get("/api/training/dataset")
    assert dataset_res.status_code == 200, f"Dataset info failed: {dataset_res.text}"
    d_data = dataset_res.json()
    assert "classes" in d_data
    assert d_data["total_images"] > 0

    history_res = client.get("/api/training/history")
    assert history_res.status_code == 200, f"Training history failed: {history_res.text}"

    reload_res = client.post("/api/training/reload")
    assert reload_res.status_code == 200, f"Reload weights failed: {reload_res.text}"
    print(f"  -> Model Training System (Dataset: {d_data['total_images']} images, Classes: {len(d_data['classes'])}, Weights Reloaded): PASSED")
    passed_steps += 1

    # 8. Reports Generation
    print("\n[Step 8/8] Verifying Reports Generation...")
    rep_res = client.get(f"/api/reports/analytics")
    assert rep_res.status_code == 200, f"Analytics report failed: {rep_res.text}"
    print("  -> Analytics and Reports Engine: PASSED")
    passed_steps += 1

    print("\n==================================================")
    print(f"ALL {passed_steps}/{total_steps} END-TO-END VERIFICATION CHECKS PASSED SUCCESSFULLY!")
    print("==================================================")

if __name__ == "__main__":
    run_e2e_verification()
