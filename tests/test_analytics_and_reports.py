"""
Integration tests for Analytics and Multi-Format Reports endpoints.
"""

import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session as SQLSession

from src.models.user import User
from src.models.tournament import Tournament, Session as SessionModel
from src.models.scoring import SessionArcher, Score


@pytest.fixture
def populated_report_data(test_db: SQLSession, test_user: User, test_admin_user: User):
    """Create tournaments, sessions, archers, and scores for testing reporting and analytics."""
    # Tournament 1
    t1 = Tournament(
        name="Championship Classic 2026",
        location="National Archery Arena",
        description="Major open championship",
        start_date=datetime.utcnow() - timedelta(days=5),
        end_date=datetime.utcnow() + timedelta(days=2),
        created_by_user_id=test_admin_user.id,
    )
    # Tournament 2
    t2 = Tournament(
        name="Summer Grand Prix",
        location="Olympic Park",
        description="Longitudinal evaluation event",
        start_date=datetime.utcnow() - timedelta(days=20),
        end_date=datetime.utcnow() - timedelta(days=18),
        created_by_user_id=test_admin_user.id,
    )

    test_db.add_all([t1, t2])
    test_db.commit()
    test_db.refresh(t1)
    test_db.refresh(t2)

    # Sessions
    s1 = SessionModel(
        tournament_id=t1.id,
        name="T1 Qualification Match",
        round_number=1,
        status="active",
        num_lanes=4,
        arrows_per_round=3,
    )
    s2 = SessionModel(
        tournament_id=t2.id,
        name="T2 Elimination Stage",
        round_number=1,
        status="completed",
        num_lanes=4,
        arrows_per_round=3,
    )
    test_db.add_all([s1, s2])
    test_db.commit()
    test_db.refresh(s1)
    test_db.refresh(s2)

    # Archers
    sa1_t1 = SessionArcher(
        session_id=s1.id,
        archer_id=test_user.id,
        archer_name=test_user.username,
        lane_number=1,
        total_score=58,
        current_round=2,
    )
    sa2_t1 = SessionArcher(
        session_id=s1.id,
        archer_id=test_admin_user.id,
        archer_name=test_admin_user.username,
        lane_number=2,
        total_score=52,
        current_round=2,
    )
    sa1_t2 = SessionArcher(
        session_id=s2.id,
        archer_id=test_user.id,
        archer_name=test_user.username,
        lane_number=1,
        total_score=29,
        current_round=1,
    )
    test_db.add_all([sa1_t1, sa2_t1, sa1_t2])
    test_db.commit()
    test_db.refresh(sa1_t1)
    test_db.refresh(sa2_t1)
    test_db.refresh(sa1_t2)

    # Scores for sa1_t1 (Round 1: 10, 10, 9 = 29; Round 2: 10, 10, 9 = 29)
    scores = [
        Score(session_id=s1.id, session_archer_id=sa1_t1.id, round=1, arrow_num=1, zone=10, points=10, image_id="x_1", validated_by_ai=True, confidence=0.98),
        Score(session_id=s1.id, session_archer_id=sa1_t1.id, round=1, arrow_num=2, zone=10, points=10, image_id="arrow_2", validated_by_ai=True, confidence=0.96),
        Score(session_id=s1.id, session_archer_id=sa1_t1.id, round=1, arrow_num=3, zone=9, points=9, image_id="arrow_3", validated_by_ai=True, confidence=0.94),
        Score(session_id=s1.id, session_archer_id=sa1_t1.id, round=2, arrow_num=1, zone=10, points=10, image_id="x_4", validated_by_ai=True, confidence=0.99),
        Score(session_id=s1.id, session_archer_id=sa1_t1.id, round=2, arrow_num=2, zone=10, points=10, image_id="arrow_5", validated_by_ai=False, confidence=0.92),
        Score(session_id=s1.id, session_archer_id=sa1_t1.id, round=2, arrow_num=3, zone=9, points=9, image_id="arrow_6", validated_by_ai=True, confidence=0.95),
        # sa2_t1 scores (Round 1: 9, 8, 8 = 25; Round 2: 10, 9, 8 = 27)
        Score(session_id=s1.id, session_archer_id=sa2_t1.id, round=1, arrow_num=1, zone=9, points=9, image_id="arrow_7", validated_by_ai=True, confidence=0.91),
        Score(session_id=s1.id, session_archer_id=sa2_t1.id, round=1, arrow_num=2, zone=8, points=8, image_id="arrow_8", validated_by_ai=True, confidence=0.88),
        Score(session_id=s1.id, session_archer_id=sa2_t1.id, round=1, arrow_num=3, zone=8, points=8, image_id="arrow_9", validated_by_ai=True, confidence=0.89),
        Score(session_id=s1.id, session_archer_id=sa2_t1.id, round=2, arrow_num=1, zone=10, points=10, image_id="arrow_10", validated_by_ai=True, confidence=0.97),
        Score(session_id=s1.id, session_archer_id=sa2_t1.id, round=2, arrow_num=2, zone=9, points=9, image_id="arrow_11", validated_by_ai=True, confidence=0.93),
        Score(session_id=s1.id, session_archer_id=sa2_t1.id, round=2, arrow_num=3, zone=8, points=8, image_id="arrow_12", validated_by_ai=True, confidence=0.90),
        # sa1_t2 in Summer Grand Prix (Round 1: 10, 10, 9 = 29)
        Score(session_id=s2.id, session_archer_id=sa1_t2.id, round=1, arrow_num=1, zone=10, points=10, image_id="x_13", validated_by_ai=True, confidence=0.99),
        Score(session_id=s2.id, session_archer_id=sa1_t2.id, round=1, arrow_num=2, zone=10, points=10, image_id="arrow_14", validated_by_ai=True, confidence=0.95),
        Score(session_id=s2.id, session_archer_id=sa1_t2.id, round=1, arrow_num=3, zone=9, points=9, image_id="arrow_15", validated_by_ai=True, confidence=0.93),
    ]
    test_db.add_all(scores)
    test_db.commit()

    return {
        "tournament_1": t1,
        "tournament_2": t2,
        "session_1": s1,
        "session_2": s2,
        "archer_1": test_user,
        "archer_2": test_admin_user,
    }


def test_get_global_and_tournament_analytics(test_client: TestClient, populated_report_data):
    """Test retrieving aggregated analytics for all tournaments and filtered by tournament."""
    # Global
    resp = test_client.get("/api/reports/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_arrows_shot"] == 15
    assert data["total_archers"] == 2
    assert "score_distribution" in data
    assert "end_progression" in data
    assert "lane_accuracy" in data
    assert "ai_metrics" in data
    assert data["ai_metrics"]["total_arrows"] == 15

    # Filter by Tournament 1
    t1_id = populated_report_data["tournament_1"].id
    resp_t1 = test_client.get(f"/api/reports/analytics?tournament_id={t1_id}")
    assert resp_t1.status_code == 200
    t1_data = resp_t1.json()
    assert t1_data["tournament_id"] == t1_id
    assert t1_data["total_arrows_shot"] == 12

    # Filter by Session 1
    s1_id = populated_report_data["session_1"].id
    resp_s1 = test_client.get(f"/api/reports/analytics?session_id={s1_id}")
    assert resp_s1.status_code == 200
    s1_data = resp_s1.json()
    assert s1_data["session_id"] == s1_id
    assert s1_data["total_arrows_shot"] == 12


def test_list_archers_directory(test_client: TestClient, populated_report_data):
    """Test listing distinct archers across all tournaments."""
    resp = test_client.get("/api/reports/archers/directory")
    assert resp.status_code == 200
    archers = resp.json()
    assert len(archers) >= 2
    # Verify archer 1 participated in 2 tournaments
    archer1_item = next(a for a in archers if a["archer_id"] == populated_report_data["archer_1"].id)
    assert archer1_item["tournaments_count"] == 2
    assert archer1_item["total_score"] == 87  # 58 + 29


def test_get_archer_longitudinal_analytics(test_client: TestClient, populated_report_data):
    """Test longitudinal performance tracking across multiple tournaments for an athlete."""
    archer1 = populated_report_data["archer_1"]
    resp = test_client.get(f"/api/reports/archers/{archer1.id}/analytics")
    assert resp.status_code == 200
    data = resp.json()
    assert data["archer_id"] == archer1.id
    assert data["tournaments_participated"] == 2
    assert len(data["tournaments"]) == 2
    assert data["total_career_points"] == 87
    assert data["total_tens"] >= 4
    assert data["total_xs"] >= 2
    assert data["career_high_end"] == 29
    assert data["consistency_index"] >= 0.0


def test_generate_session_reports_pdf_csv_json(
    test_client: TestClient,
    populated_report_data,
    admin_auth_headers: dict,
):
    """Test generating session reports in PDF, CSV, and JSON formats."""
    s1_id = populated_report_data["session_1"].id

    # PDF
    resp_pdf = test_client.post(
        f"/api/sessions/{s1_id}/reports?format=pdf",
        headers=admin_auth_headers,
    )
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert len(resp_pdf.content) > 0

    # CSV
    resp_csv = test_client.post(
        f"/api/sessions/{s1_id}/reports?format=csv",
        headers=admin_auth_headers,
    )
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    assert b"Rank,Archer Name,Archer ID,Lane,Total Score" in resp_csv.content

    # JSON
    resp_json = test_client.post(
        f"/api/sessions/{s1_id}/reports?format=json",
        headers=admin_auth_headers,
    )
    assert resp_json.status_code == 200
    assert resp_json.headers["content-type"] == "application/json"
    json_data = resp_json.json()
    assert json_data["session"]["id"] == s1_id
    assert "leaderboard" in json_data


def test_generate_tournament_reports_pdf_csv_json(
    test_client: TestClient,
    populated_report_data,
    admin_auth_headers: dict,
):
    """Test generating tournament-wide reports in PDF, CSV, and JSON formats."""
    t1_id = populated_report_data["tournament_1"].id

    # PDF
    resp_pdf = test_client.post(
        f"/api/tournaments/{t1_id}/reports?format=pdf",
        headers=admin_auth_headers,
    )
    assert resp_pdf.status_code == 200
    assert resp_pdf.headers["content-type"] == "application/pdf"
    assert len(resp_pdf.content) > 0

    # CSV
    resp_csv = test_client.post(
        f"/api/tournaments/{t1_id}/reports?format=csv",
        headers=admin_auth_headers,
    )
    assert resp_csv.status_code == 200
    assert "text/csv" in resp_csv.headers["content-type"]
    assert b"Rank,Archer Name,Archer ID,Total Score" in resp_csv.content

    # JSON
    resp_json = test_client.post(
        f"/api/tournaments/{t1_id}/reports?format=json",
        headers=admin_auth_headers,
    )
    assert resp_json.status_code == 200
    assert resp_json.headers["content-type"] == "application/json"
    json_data = resp_json.json()
    assert json_data["tournament"]["id"] == t1_id
    assert "leaderboard" in json_data


