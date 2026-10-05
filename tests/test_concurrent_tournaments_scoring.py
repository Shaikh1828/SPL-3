"""
Integration tests for concurrent tournaments, multi-session scoring, and data field integrity.
"""

from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from src.models.tournament import Tournament, Session as TournamentSession
from src.models.scoring import SessionArcher, Score


def test_concurrent_tournaments_and_scoring_integrity(test_client: TestClient, test_db: Session, admin_auth_headers: dict):
    """
    Test multiple concurrent tournaments:
    1. Create 2 concurrent tournaments with active sessions and archers.
    2. Record scores for archers in each concurrent tournament.
    3. Verify data fields (session_id, session_archer_id, round, arrow_num, points, zone, total_score).
    4. Test score undo / deletion with total recalculation.
    5. Verify tournament-wide leaderboard rankings and score aggregation.
    """
    headers = admin_auth_headers
    now = datetime.utcnow()

    # 1. Create Tournament A & B
    t_a = Tournament(
        name="National Championship 2026",
        location="Range A",
        start_date=now,
        end_date=now + timedelta(days=3),
        created_by_user_id=1,
    )
    t_b = Tournament(
        name="Spring Grand Prix 2026",
        location="Range B",
        start_date=now,
        end_date=now + timedelta(days=3),
        created_by_user_id=1,
    )
    test_db.add_all([t_a, t_b])
    test_db.commit()
    test_db.refresh(t_a)
    test_db.refresh(t_b)

    # 2. Create Sessions for both tournaments
    s_a = TournamentSession(
        tournament_id=t_a.id,
        name="Session 1 - Recurve",
        round_number=1,
        num_lanes=6,
        arrows_per_round=6,
        status="active",
    )
    s_b = TournamentSession(
        tournament_id=t_b.id,
        name="Session 1 - Compound",
        round_number=1,
        num_lanes=6,
        arrows_per_round=6,
        status="active",
    )
    test_db.add_all([s_a, s_b])
    test_db.commit()
    test_db.refresh(s_a)
    test_db.refresh(s_b)

    # 3. Create Archers in both sessions
    sa_a1 = SessionArcher(session_id=s_a.id, archer_id=1, archer_name="Brady Ellison", lane_number=1, total_score=0)
    sa_a2 = SessionArcher(session_id=s_a.id, archer_id=2, archer_name="Mete Gazoz", lane_number=2, total_score=0)
    sa_b1 = SessionArcher(session_id=s_b.id, archer_id=3, archer_name="Kim Woo-jin", lane_number=1, total_score=0)
    test_db.add_all([sa_a1, sa_a2, sa_b1])
    test_db.commit()
    test_db.refresh(sa_a1)
    test_db.refresh(sa_a2)
    test_db.refresh(sa_b1)

    # 4. Record a 10-point arrow for Archer A1 in Tournament A
    score_payload_a = {
        "session_archer_id": sa_a1.id,
        "round": 1,
        "arrow_num": 1,
        "zone": 10,
        "points": 10,
        "image_id": "test_10.jpg",
    }
    res_score_a = test_client.post(f"/api/sessions/{s_a.id}/scores", json=score_payload_a, headers=headers)
    assert res_score_a.status_code == 201
    score_a = res_score_a.json()

    # Verify exact field mappings
    assert score_a["session_id"] == s_a.id
    assert score_a["session_archer_id"] == sa_a1.id
    assert score_a["round"] == 1
    assert score_a["arrow_num"] == 1
    assert score_a["points"] == 10
    assert score_a["zone"] == 10

    # Verify SessionArcher A1 total score is updated
    test_db.refresh(sa_a1)
    assert sa_a1.total_score == 10

    # 5. Record a 9-point arrow for Archer B1 in concurrent Tournament B
    score_payload_b = {
        "session_archer_id": sa_b1.id,
        "round": 1,
        "arrow_num": 1,
        "zone": 9,
        "points": 9,
    }
    res_score_b = test_client.post(f"/api/sessions/{s_b.id}/scores", json=score_payload_b, headers=headers)
    assert res_score_b.status_code == 201

    # Verify Tournament B isolation
    test_db.refresh(sa_b1)
    assert sa_b1.total_score == 9
    assert sa_a1.total_score == 10

    # 6. Test Undo / Deletion of Archer A1's score
    res_del = test_client.delete(f"/api/scores/{score_a['id']}", headers=headers)
    assert res_del.status_code == 200

    # Verify total_score reverted accurately after deletion
    test_db.refresh(sa_a1)
    assert sa_a1.total_score == 0

    # 7. Record additional scores and test Tournament-wide Leaderboard
    score_payload_a_new = {
        "session_archer_id": sa_a1.id,
        "round": 1,
        "arrow_num": 1,
        "zone": 10,
        "points": 10,
    }
    test_client.post(f"/api/sessions/{s_a.id}/scores", json=score_payload_a_new, headers=headers)

    score_payload_a2 = {
        "session_archer_id": sa_a2.id,
        "round": 1,
        "arrow_num": 1,
        "zone": 8,
        "points": 8,
    }
    test_client.post(f"/api/sessions/{s_a.id}/scores", json=score_payload_a2, headers=headers)

    res_lead = test_client.get(f"/api/tournaments/{t_a.id}/leaderboard", headers=headers)
    assert res_lead.status_code == 200
    lead_items = res_lead.json()
    assert len(lead_items) == 2

    # Brady Ellison (10 pts) should be rank 1, Mete Gazoz (8 pts) rank 2
    assert lead_items[0]["archer_name"] == "Brady Ellison"
    assert lead_items[0]["rank"] == 1
    assert lead_items[0]["total_score"] == 10
    assert lead_items[1]["archer_name"] == "Mete Gazoz"
    assert lead_items[1]["rank"] == 2
    assert lead_items[1]["total_score"] == 8
