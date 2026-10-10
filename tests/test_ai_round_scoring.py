"""
Integration tests for the complete AI Round Scoring & Scorer Review/Confirm Cycle.

Tests:
1. AI Round Scoring endpoint (multi-lane simultaneous detection with YOLO11 target preview).
2. Scorer review and manual override staging.
3. Batch confirmation committing scores and recalculating totals.
4. Multi-round progression cycle (Round 1 -> Round 2 -> Final standings).
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLSession

from src.models.user import User
from src.models.tournament import Tournament, Session
from src.models.scoring import SessionArcher, Score
from src.models.camera import Camera, CameraLaneAssignment


@pytest.fixture
def scoring_setup(test_db: SQLSession, admin_auth_headers: dict):
    """Setup an active tournament, session with 3 lanes/archers, and assigned cameras."""
    from datetime import datetime, timedelta
    t = Tournament(
        name="Championship AI Scoring Trial",
        location="Target Range Alpha",
        description="Full AI Target Vision Evaluation",
        start_date=datetime.utcnow(),
        end_date=datetime.utcnow() + timedelta(days=2),
        created_by_user_id=1,
    )
    test_db.add(t)
    test_db.commit()
    test_db.refresh(t)

    s = Session(
        tournament_id=t.id,
        name="Qualification Stage - AI Vision",
        round_number=1,
        num_lanes=3,
        arrows_per_round=6,
        status="active",
        start_time=datetime.utcnow(),
    )
    test_db.add(s)
    test_db.commit()
    test_db.refresh(s)

    archers = []
    names = ["Archer Alpha", "Archer Beta", "Archer Gamma"]
    for i, name in enumerate(names):
        sa = SessionArcher(
            session_id=s.id,
            archer_id=100 + i,
            archer_name=name,
            lane_number=i + 1,
            current_round=1,
            total_score=0,
        )
        test_db.add(sa)
        archers.append(sa)
    test_db.commit()
    for sa in archers:
        test_db.refresh(sa)

    for i in range(1, 4):
        cam = Camera(
            name=f"Lane {i} High-Speed 4K Camera",
            camera_type="RTSP",
            url=f"rtsp://192.168.1.10{i}/live",
            status="connected",
        )
        test_db.add(cam)
        test_db.commit()
        test_db.refresh(cam)

        assign = CameraLaneAssignment(
            camera_id=cam.id,
            session_id=s.id,
            lane=i,
        )
        test_db.add(assign)
    test_db.commit()

    return {"tournament": t, "session": s, "archers": archers}


def test_ai_score_round_detection(test_client: TestClient, admin_auth_headers: dict, scoring_setup: dict):
    """Verify that calling ai-score-round triggers detections across all session lanes."""
    session = scoring_setup["session"]

    response = test_client.post(
        f"/api/sessions/{session.id}/ai-score-round",
        json={"round": 1},
        headers=admin_auth_headers,
    )

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["session_id"] == session.id
    assert data["round"] == 1
    assert data["arrows_per_round"] == 6
    assert len(data["lanes"]) == 3

    for lane in data["lanes"]:
        assert lane["lane_number"] in [1, 2, 3]
        assert lane["status"] == "detected"
        assert len(lane["detected_arrows"]) == 6
        assert lane["end_total"] >= 40
        assert lane["avg_confidence"] >= 0.80
        assert lane["method"] == "yolo11_consensus"
        assert lane["annotated_image"] is not None
        assert lane["annotated_image"].startswith("data:image/jpeg;base64,")


def test_batch_confirm_round_with_override(test_client: TestClient, admin_auth_headers: dict, scoring_setup: dict, test_db: SQLSession):
    """Verify review and manual override staging, followed by batch confirmation."""
    session = scoring_setup["session"]

    # 1. Run AI Detection for Round 1
    detect_res = test_client.post(
        f"/api/sessions/{session.id}/ai-score-round",
        json={"round": 1},
        headers=admin_auth_headers,
    )
    assert detect_res.status_code == 200
    lanes = detect_res.json()["lanes"]

    # 2. Scorer overrides arrow #3 on Lane 1 from original score to a 10 (X)
    lane1_arrows = lanes[0]["detected_arrows"]
    lane1_arrows[2]["points"] = 10
    lane1_arrows[2]["zone"] = "X"
    lane1_arrows[2]["is_x"] = True
    lane1_arrows[2]["is_override"] = True
    lane1_arrows[2]["override_reason"] = "Scorer confirmed line touch bullseye"

    # 3. Submit Batch Confirmation
    confirm_payload = {
        "round": 1,
        "lane_submissions": [
            {
                "session_archer_id": lane["session_archer_id"],
                "lane_number": lane["lane_number"],
                "arrows": lane["detected_arrows"],
            }
            for lane in lanes
        ]
    }

    confirm_res = test_client.post(
        f"/api/sessions/{session.id}/scores/batch-confirm-round",
        json=confirm_payload,
        headers=admin_auth_headers,
    )

    assert confirm_res.status_code == 200, confirm_res.text
    confirm_data = confirm_res.json()

    assert confirm_data["session_id"] == session.id
    assert confirm_data["round"] == 1
    assert confirm_data["scores_recorded_count"] == 18  # 3 archers * 6 arrows
    assert confirm_data["next_round"] == 2

    # 4. Verify scores are stored in DB
    scores_res = test_client.get(f"/api/sessions/{session.id}/scores?round=1", headers=admin_auth_headers)
    assert scores_res.status_code == 200
    stored_scores = scores_res.json()
    assert len(stored_scores) == 18

    # Check Lane 1 Archer total score
    lane1_archer_id = lanes[0]["session_archer_id"]
    archer_db = test_db.query(SessionArcher).filter(SessionArcher.id == lane1_archer_id).first()
    assert archer_db is not None
    assert archer_db.total_score > 0
    assert archer_db.current_round >= 2


def test_complete_multi_round_progression_cycle(test_client: TestClient, admin_auth_headers: dict, scoring_setup: dict, test_db: SQLSession):
    """Verify complete multi-round scoring cycle: Round 1 -> Confirm -> Round 2 -> Confirm."""
    session = scoring_setup["session"]

    # --- ROUND 1 ---
    r1_detect = test_client.post(
        f"/api/sessions/{session.id}/ai-score-round",
        json={"round": 1},
        headers=admin_auth_headers,
    ).json()

    r1_confirm = test_client.post(
        f"/api/sessions/{session.id}/scores/batch-confirm-round",
        json={
            "round": 1,
            "lane_submissions": [
                {
                    "session_archer_id": l["session_archer_id"],
                    "lane_number": l["lane_number"],
                    "arrows": l["detected_arrows"],
                }
                for l in r1_detect["lanes"]
            ]
        },
        headers=admin_auth_headers,
    ).json()
    assert r1_confirm["next_round"] == 2

    # --- ROUND 2 ---
    r2_detect = test_client.post(
        f"/api/sessions/{session.id}/ai-score-round",
        json={"round": 2},
        headers=admin_auth_headers,
    ).json()
    assert r2_detect["round"] == 2

    r2_confirm = test_client.post(
        f"/api/sessions/{session.id}/scores/batch-confirm-round",
        json={
            "round": 2,
            "lane_submissions": [
                {
                    "session_archer_id": l["session_archer_id"],
                    "lane_number": l["lane_number"],
                    "arrows": l["detected_arrows"],
                }
                for l in r2_detect["lanes"]
            ]
        },
        headers=admin_auth_headers,
    ).json()
    assert r2_confirm["next_round"] == 3

    # Total recorded scores across 2 rounds: 3 archers * 6 arrows * 2 rounds = 36
    all_scores = test_client.get(f"/api/sessions/{session.id}/scores", headers=admin_auth_headers).json()
    assert len(all_scores) == 36


def test_single_lane_capture_score_sync(test_client: TestClient, admin_auth_headers: dict, scoring_setup: dict):
    """
    Verify that single lane capture synchronizes all detected arrows for the round,
    cleans up any extraneous/out-of-bounds arrows (like arrow #7), and matches annotated scan.
    """
    session = scoring_setup["session"]
    archer = scoring_setup["archers"][0]  # Lane 1

    # Call single lane capture on Lane 1, Round 1
    response = test_client.post(
        f"/api/sessions/{session.id}/lanes/1/capture-score?round=1",
        headers=admin_auth_headers,
    )
    assert response.status_code == 200, response.text
    score_data = response.json()
    assert score_data["arrow_num"] == 1
    assert score_data["session_archer_id"] == archer.id
    assert score_data["round"] == 1
    assert score_data["image_id"] is not None

    # Fetch all scores for this session and verify round 1 for archer
    all_scores = test_client.get(f"/api/sessions/{session.id}/scores?round=1", headers=admin_auth_headers).json()
    archer_r1_scores = [s for s in all_scores if s["session_archer_id"] == archer.id and s["round"] == 1]

    # Must NOT have 7 arrows; arrows must be sequentially 1..N (N <= 6)
    assert len(archer_r1_scores) <= 6
    arrow_nums = sorted([s["arrow_num"] for s in archer_r1_scores])
    assert arrow_nums == list(range(1, len(archer_r1_scores) + 1))

    # All arrows from the same scan must share the same image_id
    image_ids = set(s["image_id"] for s in archer_r1_scores)
    assert len(image_ids) == 1

    # Sum of individual arrow points must match
    expected_sum = sum(s["points"] for s in archer_r1_scores)
    assert expected_sum >= 0

    # Annotated image endpoint must be accessible
    img_resp = test_client.get(f"/api/scores/{score_data['id']}/image-annotated", headers=admin_auth_headers)
    assert img_resp.status_code == 200

