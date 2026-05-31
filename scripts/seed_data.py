"""
Seed data script for database initialization.

Populates database with test data for development and demonstration.

Usage:
    python -m scripts.seed_data
"""

import sys
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from src.database import SessionLocal
from src.models.user import User
from src.models.tournament import Tournament, Session as TournamentSession
from src.models.scoring import SessionArcher, Score
from src.models.camera import Camera, CameraLaneAssignment
from src.security import hash_password
import structlog

logger = structlog.get_logger()


def seed_users(db: Session):
    """Create seed users."""
    logger.info("seeding_users")

    users = [
        User(
            username="admin",
            email="admin@archery.local",
            password_hash=hash_password("AdminPass123!"),
            role="admin",
            is_active=True,
        ),
        User(
            username="scorer1",
            email="scorer1@archery.local",
            password_hash=hash_password("ScorerPass123!"),
            role="scorer",
            is_active=True,
        ),
        User(
            username="scorer2",
            email="scorer2@archery.local",
            password_hash=hash_password("ScorerPass123!"),
            role="scorer",
            is_active=True,
        ),
        User(
            username="spectator1",
            email="spectator1@archery.local",
            password_hash=hash_password("SpectatorPass123!"),
            role="spectator",
            is_active=True,
        ),
        User(
            username="archer1",
            email="archer1@archery.local",
            password_hash=hash_password("ArcherPass123!"),
            role="archer",
            is_active=True,
        ),
    ]

    for user in users:
        existing = db.query(User).filter(User.username == user.username).first()
        if not existing:
            db.add(user)

    db.commit()
    logger.info("users_seeded", count=len(users))
    return users


def seed_tournaments(db: Session, admin_user: User):
    """Create seed tournaments."""
    logger.info("seeding_tournaments")

    now = datetime.utcnow()
    tournaments = [
        Tournament(
            name="Spring Championship 2026",
            location="Central Park Archery Range",
            start_date=now,
            end_date=now + timedelta(days=3),
            created_by_user_id=admin_user.id,
        ),
        Tournament(
            name="Summer Qualifier 2026",
            location="Downtown Sports Complex",
            start_date=now + timedelta(days=7),
            end_date=now + timedelta(days=10),
            created_by_user_id=admin_user.id,
        ),
    ]

    for tournament in tournaments:
        existing = db.query(Tournament).filter(
            Tournament.name == tournament.name
        ).first()
        if not existing:
            db.add(tournament)

    db.commit()
    logger.info("tournaments_seeded", count=len(tournaments))
    return tournaments


def seed_sessions(db: Session, tournaments: list):
    """Create seed sessions."""
    logger.info("seeding_sessions")

    sessions = []
    for tournament in tournaments:
        for i in range(3):
            session = TournamentSession(
                tournament_id=tournament.id,
                name=f"Session {i+1}",
                status="active" if i == 0 else "paused",
            )
            existing = db.query(TournamentSession).filter(
                TournamentSession.tournament_id == tournament.id,
                TournamentSession.name == session.name,
            ).first()
            if not existing:
                db.add(session)
                sessions.append(session)

    db.commit()
    logger.info("sessions_seeded", count=len(sessions))
    return sessions


def seed_session_archers(db: Session, sessions: list):
    """Create seed session archers."""
    logger.info("seeding_session_archers")

    archer_names = [
        "John Smith",
        "Jane Doe",
        "Bob Johnson",
        "Alice Williams",
        "Charlie Brown",
    ]

    session_archers = []
    for session in sessions:
        for archer_id, archer_name in enumerate(archer_names, start=1):
            session_archer = SessionArcher(
                session_id=session.id,
                archer_id=archer_id,
                archer_name=archer_name,
                current_round=1,
                total_score=0,
            )
            existing = db.query(SessionArcher).filter(
                SessionArcher.session_id == session.id,
                SessionArcher.archer_id == archer_id,
            ).first()
            if not existing:
                db.add(session_archer)
                session_archers.append(session_archer)

    db.commit()
    logger.info("session_archers_seeded", count=len(session_archers))
    return session_archers


def seed_scores(db: Session, session_archers: list):
    """Create seed scores."""
    logger.info("seeding_scores")

    import random

    scores = []
    for session_archer in session_archers[:10]:  # Limit for performance
        for round_num in range(1, 4):
            for arrow_num in range(1, 7):
                # Random zone and points (0-10)
                zone = random.randint(0, 10)
                points = random.randint(max(0, zone - 2), min(10, zone + 2))

                score = Score(
                    session_id=session_archer.session_id,
                    session_archer_id=session_archer.id,
                    round=round_num,
                    arrow_num=arrow_num,
                    zone=zone,
                    points=points,
                    validated_by_ai=random.choice([True, False]),
                )

                existing = db.query(Score).filter(
                    Score.session_archer_id == session_archer.id,
                    Score.round == round_num,
                    Score.arrow_num == arrow_num,
                ).first()

                if not existing:
                    db.add(score)
                    scores.append(score)

    db.commit()
    logger.info("scores_seeded", count=len(scores))
    return scores


def seed_cameras(db: Session):
    """Create seed cameras."""
    logger.info("seeding_cameras")

    cameras = [
        Camera(
            name="Lane 1 Camera",
            camera_type="RTSP",
            url="rtsp://camera1.local:554/stream",
            status="connected",
        ),
        Camera(
            name="Lane 2 Camera",
            camera_type="RTSP",
            url="rtsp://camera2.local:554/stream",
            status="connected",
        ),
        Camera(
            name="Lane 3 Camera",
            camera_type="USB",
            url="camera:///dev/video0",
            status="disconnected",
        ),
    ]

    for camera in cameras:
        existing = db.query(Camera).filter(Camera.name == camera.name).first()
        if not existing:
            db.add(camera)

    db.commit()
    logger.info("cameras_seeded", count=len(cameras))
    return cameras


def seed_camera_assignments(db: Session, sessions: list, cameras: list):
    """Create seed camera lane assignments."""
    logger.info("seeding_camera_assignments")

    assignments = []
    for session in sessions[:1]:  # Only assign to first session
        for i, camera in enumerate(cameras[:2], start=1):
            assignment = CameraLaneAssignment(
                camera_id=camera.id,
                session_id=session.id,
                lane=i,
            )

            existing = db.query(CameraLaneAssignment).filter(
                CameraLaneAssignment.session_id == session.id,
                CameraLaneAssignment.lane == i,
            ).first()

            if not existing:
                db.add(assignment)
                assignments.append(assignment)

    db.commit()
    logger.info("camera_assignments_seeded", count=len(assignments))
    return assignments


def main():
    """Run all seed operations."""
    logger.info("seed_data_starting")

    db = SessionLocal()

    try:
        # Seed in order of dependencies
        users = seed_users(db)
        admin_user = users[0]

        tournaments = seed_tournaments(db, admin_user)
        sessions = seed_sessions(db, tournaments)
        session_archers = seed_session_archers(db, sessions)
        scores = seed_scores(db, session_archers)
        cameras = seed_cameras(db)
        camera_assignments = seed_camera_assignments(db, sessions, cameras)

        logger.info(
            "seed_data_complete",
            users=len(users),
            tournaments=len(tournaments),
            sessions=len(sessions),
            session_archers=len(session_archers),
            scores=len(scores),
            cameras=len(cameras),
            camera_assignments=len(camera_assignments),
        )

        print("\n✅ Seed data created successfully!")
        print(f"   - Users: {len(users)}")
        print(f"   - Tournaments: {len(tournaments)}")
        print(f"   - Sessions: {len(sessions)}")
        print(f"   - Archers: {len(session_archers)}")
        print(f"   - Scores: {len(scores)}")
        print(f"   - Cameras: {len(cameras)}")
        print(f"   - Camera Assignments: {len(camera_assignments)}")

    except Exception as e:
        logger.exception("seed_data_error", error=str(e))
        print(f"\n❌ Seed data failed: {e}")
        sys.exit(1)

    finally:
        db.close()


if __name__ == "__main__":
    main()
