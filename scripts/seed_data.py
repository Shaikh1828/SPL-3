"""
Seed data script for comprehensive database initialization & concurrent tournament testing.

Populates database with concurrent tournaments, multi-round sessions, realistic archers across lanes,
cameras, and scored arrow impacts with full total calculation and validation.

Usage:
    python -m scripts.seed_data
"""

import sys
import random
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func

from src.database import SessionLocal
from src.models.user import User
from src.models.tournament import Tournament, Session as TournamentSession
from src.models.scoring import SessionArcher, Score
from src.models.camera import Camera, CameraLaneAssignment
from src.security import hash_password
import structlog

logger = structlog.get_logger()


def seed_users(db: Session):
    """Create seed users across all roles."""
    logger.info("seeding_users")

    users = [
        User(
            username="admin",
            email="admin@archeryscore.com",
            password_hash=hash_password("admin123!"),
            role="admin",
            is_active=True,
        ),
        User(
            username="scorer",
            email="scorer@archeryscore.com",
            password_hash=hash_password("scorer123!"),
            role="scorer",
            is_active=True,
        ),
        User(
            username="scorer2",
            email="scorer2@archeryscore.com",
            password_hash=hash_password("scorer123!"),
            role="scorer",
            is_active=True,
        ),
        User(
            username="spectator1",
            email="spectator1@archeryscore.com",
            password_hash=hash_password("spectator123!"),
            role="spectator",
            is_active=True,
        ),
        # International & Club Competitor Users
        User(username="brady_ellison", email="brady@archeryscore.com", password_hash=hash_password("Archer123!"), role="archer", is_active=True),
        User(username="kim_woojin", email="kim@archeryscore.com", password_hash=hash_password("Archer123!"), role="archer", is_active=True),
        User(username="mete_gazoz", email="mete@archeryscore.com", password_hash=hash_password("Archer123!"), role="archer", is_active=True),
        User(username="marcus_dalmeida", email="marcus@archeryscore.com", password_hash=hash_password("Archer123!"), role="archer", is_active=True),
        User(username="deepika_kumari", email="deepika@archeryscore.com", password_hash=hash_password("Archer123!"), role="archer", is_active=True),
        User(username="an_san", email="ansan@archeryscore.com", password_hash=hash_password("Archer123!"), role="archer", is_active=True),
        User(username="john_smith", email="john@archeryscore.com", password_hash=hash_password("Archer123!"), role="archer", is_active=True),
        User(username="jane_doe", email="jane@archeryscore.com", password_hash=hash_password("Archer123!"), role="archer", is_active=True),
    ]

    db_users = []
    for user in users:
        existing = db.query(User).filter(User.username == user.username).first()
        if not existing:
            db.add(user)
            db.commit()
            db.refresh(user)
            db_users.append(user)
        else:
            db_users.append(existing)

    logger.info("users_seeded", count=len(db_users))
    return db_users


def seed_tournaments(db: Session, admin_user: User):
    """Create concurrent active & upcoming seed tournaments."""
    logger.info("seeding_tournaments")

    now = datetime.utcnow()
    tournaments_data = [
        {
            "name": "National Outdoor Archery Championship 2026",
            "location": "National Sports Stadium Range",
            "description": "Premiere 70m national outdoor archery championship with recurve and compound categories.",
            "start_date": now - timedelta(days=1),
            "end_date": now + timedelta(days=4),
        },
        {
            "name": "Spring Grand Prix 2026",
            "location": "Central Park Archery Range",
            "description": "Annual international spring grand prix tournament with multi-lane AI target vision.",
            "start_date": now,
            "end_date": now + timedelta(days=3),
        },
        {
            "name": "Olympic Qualification Trials 2026",
            "location": "Elite Performance Archery Center",
            "description": "High-stakes Olympic team qualification trials with precision millimeter scoring.",
            "start_date": now - timedelta(hours=6),
            "end_date": now + timedelta(days=2),
        },
        {
            "name": "Summer Regional Qualifier 2026",
            "location": "Downtown Sports Complex",
            "description": "Regional qualifier for summer games and youth cup championships.",
            "start_date": now + timedelta(days=5),
            "end_date": now + timedelta(days=8),
        },
    ]

    tournaments = []
    for t_data in tournaments_data:
        existing = db.query(Tournament).filter(Tournament.name == t_data["name"]).first()
        if not existing:
            t = Tournament(
                name=t_data["name"],
                location=t_data["location"],
                description=t_data["description"],
                start_date=t_data["start_date"],
                end_date=t_data["end_date"],
                created_by_user_id=admin_user.id,
            )
            db.add(t)
            db.commit()
            db.refresh(t)
            tournaments.append(t)
        else:
            tournaments.append(existing)

    logger.info("tournaments_seeded", count=len(tournaments))
    return tournaments


def seed_sessions(db: Session, tournaments: list):
    """Create multi-round active sessions for each concurrent tournament."""
    logger.info("seeding_sessions")

    sessions = []
    session_templates = [
        {"name": "Session 1 - Qualification 720 Round", "round_number": 1, "num_lanes": 6, "arrows_per_round": 6, "status": "active"},
        {"name": "Session 2 - Elimination 1/8 Finals", "round_number": 2, "num_lanes": 6, "arrows_per_round": 6, "status": "active"},
        {"name": "Session 3 - Gold & Bronze Medal Match", "round_number": 3, "num_lanes": 4, "arrows_per_round": 3, "status": "paused"},
    ]

    for tournament in tournaments:
        for idx, template in enumerate(session_templates):
            existing = db.query(TournamentSession).filter(
                TournamentSession.tournament_id == tournament.id,
                TournamentSession.name == template["name"],
            ).first()

            if not existing:
                session = TournamentSession(
                    tournament_id=tournament.id,
                    name=template["name"],
                    round_number=template["round_number"],
                    num_lanes=template["num_lanes"],
                    arrows_per_round=template["arrows_per_round"],
                    status=template["status"],
                    start_time=datetime.utcnow() if template["status"] == "active" else None,
                )
                db.add(session)
                db.commit()
                db.refresh(session)
                sessions.append(session)
            else:
                sessions.append(existing)

    logger.info("sessions_seeded", count=len(sessions))
    return sessions


def seed_session_archers(db: Session, sessions: list):
    """Register archers across all shooting lanes for every session."""
    logger.info("seeding_session_archers")

    competitors = [
        (1, "Brady Ellison"),
        (2, "Mete Gazoz"),
        (3, "Kim Woo-jin"),
        (4, "Marcus D'Almeida"),
        (5, "Deepika Kumari"),
        (6, "An San"),
    ]

    session_archers = []
    for session in sessions:
        max_lanes = min(session.num_lanes, len(competitors))
        for lane_idx in range(max_lanes):
            user_id, archer_name = competitors[lane_idx]
            lane_num = lane_idx + 1

            existing = db.query(SessionArcher).filter(
                SessionArcher.session_id == session.id,
                SessionArcher.lane_number == lane_num,
            ).first()

            if not existing:
                sa = SessionArcher(
                    session_id=session.id,
                    archer_id=user_id,
                    archer_name=archer_name,
                    lane_number=lane_num,
                    current_round=1,
                    total_score=0,
                )
                db.add(sa)
                db.commit()
                db.refresh(sa)
                session_archers.append(sa)
            else:
                session_archers.append(existing)

    logger.info("session_archers_seeded", count=len(session_archers))
    return session_archers


def seed_scores(db: Session, session_archers: list):
    """Seed realistic arrow impacts with zone calculation and total synchronization."""
    logger.info("seeding_scores")

    scores = []
    # Seed scores for active sessions
    for sa in session_archers:
        existing_scores = db.query(Score).filter(Score.session_archer_id == sa.id).all()
        if existing_scores:
            # Recalculate and synchronize total_score
            total_pts = sum(s.points for s in existing_scores)
            sa.total_score = total_pts
            db.commit()
            scores.extend(existing_scores)
            continue

        # Generate realistic scores for 2 ends (6 arrows per end = 12 arrows)
        total_accumulated = 0
        for round_num in range(1, 3):
            for arrow_num in range(1, 7):
                # World-class archery distribution (higher probability of 10s and 9s)
                roll = random.random()
                if roll > 0.40:
                    zone = 10
                    points = 10
                    is_x = random.random() > 0.5
                elif roll > 0.15:
                    zone = 9
                    points = 9
                    is_x = False
                elif roll > 0.05:
                    zone = 8
                    points = 8
                    is_x = False
                else:
                    zone = 7
                    points = 7
                    is_x = False

                score = Score(
                    session_id=sa.session_id,
                    session_archer_id=sa.id,
                    round=round_num,
                    arrow_num=arrow_num,
                    zone=zone,
                    points=points,
                    confidence=round(random.uniform(0.92, 0.99), 3),
                    validated_by_ai=True,
                    image_id=f"target_scan_{sa.session_id}_{round_num}_{arrow_num}.jpg",
                )
                db.add(score)
                scores.append(score)
                total_accumulated += points

        sa.total_score = total_accumulated
        sa.current_round = 2
        db.commit()

    db.commit()
    logger.info("scores_seeded", count=len(scores))
    return scores


def seed_cameras(db: Session):
    """Create 6 RTSP/USB camera targets for lane vision."""
    logger.info("seeding_cameras")

    cameras = [
        Camera(name="Target Lane 1 Cam", camera_type="RTSP", url="rtsp://camera1.local:554/live/target1", status="connected"),
        Camera(name="Target Lane 2 Cam", camera_type="RTSP", url="rtsp://camera2.local:554/live/target2", status="connected"),
        Camera(name="Target Lane 3 Cam", camera_type="RTSP", url="rtsp://camera3.local:554/live/target3", status="connected"),
        Camera(name="Target Lane 4 Cam", camera_type="RTSP", url="rtsp://camera4.local:554/live/target4", status="connected"),
        Camera(name="Target Lane 5 Cam", camera_type="RTSP", url="rtsp://camera5.local:554/live/target5", status="connected"),
        Camera(name="Target Lane 6 Cam", camera_type="USB", url="camera:///dev/video0", status="connected"),
    ]

    db_cameras = []
    for cam in cameras:
        existing = db.query(Camera).filter(Camera.name == cam.name).first()
        if not existing:
            db.add(cam)
            db.commit()
            db.refresh(cam)
            db_cameras.append(cam)
        else:
            db_cameras.append(existing)

    logger.info("cameras_seeded", count=len(db_cameras))
    return db_cameras


def seed_camera_assignments(db: Session, sessions: list, cameras: list):
    """Assign cameras to all lanes for active sessions."""
    logger.info("seeding_camera_assignments")

    assignments = []
    for session in sessions:
        if session.status != "active":
            continue

        num_lanes = min(session.num_lanes, len(cameras))
        for lane_idx in range(num_lanes):
            lane_num = lane_idx + 1
            camera = cameras[lane_idx]

            existing = db.query(CameraLaneAssignment).filter(
                CameraLaneAssignment.session_id == session.id,
                CameraLaneAssignment.lane == lane_num,
            ).first()

            if not existing:
                assignment = CameraLaneAssignment(
                    camera_id=camera.id,
                    session_id=session.id,
                    lane=lane_num,
                )
                db.add(assignment)
                assignments.append(assignment)

    db.commit()
    logger.info("camera_assignments_seeded", count=len(assignments))
    return assignments


def main():
    """Run all seed operations and verify database integrity."""
    logger.info("seed_data_starting")
    db = SessionLocal()

    try:
        users = seed_users(db)
        admin_user = users[0]

        tournaments = seed_tournaments(db, admin_user)
        sessions = seed_sessions(db, tournaments)
        session_archers = seed_session_archers(db, sessions)
        scores = seed_scores(db, session_archers)
        cameras = seed_cameras(db)
        camera_assignments = seed_camera_assignments(db, sessions, cameras)

        # Integrity check: verify that archer totals match sum of individual score points
        for sa in session_archers[:15]:
            calc_sum = db.query(func.sum(Score.points)).filter(Score.session_archer_id == sa.id).scalar() or 0
            if sa.total_score != calc_sum:
                sa.total_score = calc_sum
                db.commit()

        print("\n" + "="*60)
        print("🎯 ARCHERY SCORING SYSTEM — SEED DATA INITIALIZED")
        print("="*60)
        print(f"   👥 Users: {len(users)} (Admin: admin / admin123!, Scorer: scorer / scorer123!)")
        print(f"   🏆 Concurrent Tournaments: {len(tournaments)}")
        print(f"   🎯 Active Sessions: {len(sessions)}")
        print(f"   🏹 Registered Archers: {len(session_archers)}")
        print(f"   📊 Arrow Impact Scores: {len(scores)}")
        print(f"   📹 Cameras Assigned: {len(camera_assignments)}")
        print("="*60 + "\n")

    except Exception as e:
        logger.exception("seed_data_error", error=str(e))
        print(f"\n❌ Seed data failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
