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
    """Create realistic ongoing, completed, and upcoming tournaments."""
    logger.info("seeding_tournaments")

    now = datetime.utcnow()
    tournaments_data = [
        # --- ONGOING TOURNAMENTS WITH ELIMINATION STAGES ---
        {
            "name": "National Outdoor Archery Championship 2026",
            "location": "National Sports Stadium Range, Dhaka",
            "description": "Premiere 70m national outdoor archery championship featuring 12-archer qualification, semi-finals cut, and medal finals.",
            "start_date": now - timedelta(days=1),
            "end_date": now + timedelta(days=3),
            "sessions": [
                {"name": "Session 1 - Recurve Men & Women 720 Qualification", "round_number": 1, "num_lanes": 12, "arrows_per_round": 6, "status": "completed"},
                {"name": "Session 2 - 1/4 & Semi-Final Elimination", "round_number": 2, "num_lanes": 6, "arrows_per_round": 6, "status": "completed"},
                {"name": "Session 3 - Gold & Bronze Medal Finals", "round_number": 3, "num_lanes": 4, "arrows_per_round": 6, "status": "active"},
            ],
        },
        {
            "name": "Asia Cup Archery Stage 2 - 2026",
            "location": "BKSP Archery Ground, Savar",
            "description": "Continental stage-2 tournament with 12 international competitors and multi-camera elimination brackets.",
            "start_date": now - timedelta(hours=18),
            "end_date": now + timedelta(days=2),
            "sessions": [
                {"name": "Session 1 - Qualification 70m", "round_number": 1, "num_lanes": 12, "arrows_per_round": 6, "status": "completed"},
                {"name": "Session 2 - 1/8 & Semi-Finals Elimination", "round_number": 2, "num_lanes": 6, "arrows_per_round": 6, "status": "active"},
            ],
        },
        # --- COMPLETED TOURNAMENTS ---
        {
            "name": "Bangladesh Independence Cup 2026",
            "location": "Army Stadium Archery Arena, Dhaka",
            "description": "Annual Independence Day Invitational. Completed 3-stage championship with qualification cut and medal ceremony.",
            "start_date": now - timedelta(days=14),
            "end_date": now - timedelta(days=10),
            "sessions": [
                {"name": "Stage 1 - Qualification 720", "round_number": 1, "num_lanes": 12, "arrows_per_round": 6, "status": "completed"},
                {"name": "Stage 2 - Semi-Finals Elimination", "round_number": 2, "num_lanes": 6, "arrows_per_round": 6, "status": "completed"},
                {"name": "Stage 3 - Gold Medal Finals", "round_number": 3, "num_lanes": 4, "arrows_per_round": 6, "status": "completed"},
            ],
        },
        {
            "name": "Teer 14th National Archery Championship",
            "location": "Shaheed Ahsan Ullah Master Stadium, Tongi",
            "description": "Historic national championship crowned with national team records in 70m individual recurve.",
            "start_date": now - timedelta(days=32),
            "end_date": now - timedelta(days=28),
            "sessions": [
                {"name": "Session 1 - Championship Qualification 720", "round_number": 1, "num_lanes": 12, "arrows_per_round": 6, "status": "completed"},
                {"name": "Session 2 - Medal Match Finals", "round_number": 2, "num_lanes": 4, "arrows_per_round": 6, "status": "completed"},
            ],
        },
        {
            "name": "Winter Invitational Grand Prix 2025",
            "location": "Sylhet International Sports Range",
            "description": "International winter open tournament. Fully concluded with official records archived.",
            "start_date": now - timedelta(days=90),
            "end_date": now - timedelta(days=86),
            "sessions": [
                {"name": "All-Stars Final Round", "round_number": 1, "num_lanes": 6, "arrows_per_round": 6, "status": "completed"},
            ],
        },
        # --- UPCOMING TOURNAMENTS ---
        {
            "name": "Asian Archery Grand Prix 2026",
            "location": "Chittagong Port Sports Complex",
            "description": "Upcoming international major tournament scheduled next month with 16 nations participating.",
            "start_date": now + timedelta(days=12),
            "end_date": now + timedelta(days=16),
            "sessions": [
                {"name": "Preliminary Round A", "round_number": 1, "num_lanes": 6, "arrows_per_round": 6, "status": "paused"},
            ],
        },
        {
            "name": "Inter-University Archery Meet 2026",
            "location": "University Physical Education Field",
            "description": "National collegiate archery championship scheduled for next semester.",
            "start_date": now + timedelta(days=25),
            "end_date": now + timedelta(days=28),
            "sessions": [
                {"name": "Collegiate Qualification", "round_number": 1, "num_lanes": 6, "arrows_per_round": 6, "status": "paused"},
            ],
        },
    ]

    tournaments = []
    sessions_to_create = []

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
            t_obj = t
        else:
            existing.location = t_data["location"]
            existing.description = t_data["description"]
            existing.start_date = t_data["start_date"]
            existing.end_date = t_data["end_date"]
            db.commit()
            tournaments.append(existing)
            t_obj = existing

        # Create tournament-specific sessions
        for s_template in t_data.get("sessions", []):
            existing_sess = db.query(TournamentSession).filter(
                TournamentSession.tournament_id == t_obj.id,
                TournamentSession.name == s_template["name"],
            ).first()

            if not existing_sess:
                sess = TournamentSession(
                    tournament_id=t_obj.id,
                    name=s_template["name"],
                    round_number=s_template["round_number"],
                    num_lanes=s_template["num_lanes"],
                    arrows_per_round=s_template["arrows_per_round"],
                    status=s_template["status"],
                    start_time=t_data["start_date"] if s_template["status"] in ["active", "completed"] else None,
                    end_time=t_data["end_date"] if s_template["status"] == "completed" else None,
                )
                db.add(sess)
                db.commit()
                db.refresh(sess)
                sessions_to_create.append(sess)
            else:
                existing_sess.status = s_template["status"]
                existing_sess.round_number = s_template["round_number"]
                existing_sess.num_lanes = s_template["num_lanes"]
                db.commit()
                sessions_to_create.append(existing_sess)

    logger.info("tournaments_seeded", count=len(tournaments))
    return tournaments, sessions_to_create


def seed_session_archers(db: Session, sessions: list):
    """Register archers across elimination tiers for every session."""
    logger.info("seeding_session_archers")

    # 12-Archer Roster
    all_competitors = [
        (1, "Brady Ellison"),
        (2, "Mete Gazoz"),
        (3, "Kim Woo-jin"),
        (4, "Marcus D'Almeida"),
        (5, "Deepika Kumari"),
        (6, "An San"),
        (7, "Ruman Shana"),
        (8, "Casey Kaufhold"),
        (9, "Md Sagor Islam"),
        (10, "Zahid Hasan"),
        (11, "Nasrin Akter"),
        (12, "Atanu Das"),
    ]

    # Qualified tiers
    tier_semi_finalists = [all_competitors[0], all_competitors[2], all_competitors[5], all_competitors[1], all_competitors[3], all_competitors[4]]
    tier_finalists = [all_competitors[0], all_competitors[2], all_competitors[5], all_competitors[1]]

    session_archers = []
    for session in sessions:
        s_name_lower = session.name.lower()
        
        # Decide which competitor roster qualifies for this stage
        if session.round_number == 3 or "finals" in s_name_lower or "gold" in s_name_lower:
            roster = tier_finalists[:session.num_lanes]
        elif session.round_number == 2 or "semi" in s_name_lower or "elimination" in s_name_lower or "1/4" in s_name_lower:
            roster = tier_semi_finalists[:session.num_lanes]
        else:
            # Qualification round
            roster = all_competitors[:session.num_lanes]

        for lane_idx, (user_id, archer_name) in enumerate(roster):
            lane_num = lane_idx + 1

            existing = db.query(SessionArcher).filter(
                SessionArcher.session_id == session.id,
                SessionArcher.archer_id == user_id,
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
                existing.lane_number = lane_num
                db.commit()
                session_archers.append(existing)

    logger.info("session_archers_seeded", count=len(session_archers))
    return session_archers


def seed_scores(db: Session, session_archers: list):
    """Seed realistic arrow impacts with zone calculation and total synchronization across 5 ends."""
    logger.info("seeding_scores")

    scores = []
    # Seed scores for active sessions across 5 ends (30 arrows per archer)
    for sa in session_archers:
        existing_scores = db.query(Score).filter(Score.session_archer_id == sa.id).all()
        # If already populated with 5 ends (at least 30 arrows), keep or sync
        if existing_scores and len(existing_scores) >= 30:
            total_pts = sum(s.points for s in existing_scores)
            sa.total_score = total_pts
            sa.current_round = max(s.round for s in existing_scores)
            db.commit()
            scores.extend(existing_scores)
            continue
        elif existing_scores:
            # Clear incomplete ends to re-seed 5 full ends
            for es in existing_scores:
                db.delete(es)
            db.commit()

        # Skill profile based on lane number (1 to 6)
        lane = sa.lane_number or 1
        total_accumulated = 0

        # Generate realistic scores for 5 ends (6 arrows per end = 30 arrows total)
        for round_num in range(1, 6):
            # Fatigue / pacing factor per end (End 1 fresh, End 2 peak, End 3 steady, End 4 fatigue dip, End 5 final push)
            end_fatigue_bias = {
                1: 0.0,
                2: 0.05,   # warming up & peaked
                3: 0.0,
                4: -0.06,  # fatigue dip
                5: 0.02,   # adrenaline finish
            }.get(round_num, 0.0)

            for arrow_num in range(1, 7):
                roll = random.random() + end_fatigue_bias

                # Archer specific distribution
                if lane == 3:  # Kim Woo-jin (world champion level ~9.7 avg)
                    if roll > 0.35:
                        points = 10
                        is_x = random.random() > 0.45
                    elif roll > 0.08:
                        points = 9
                        is_x = False
                    elif roll > 0.02:
                        points = 8
                        is_x = False
                    else:
                        points = 7
                        is_x = False
                elif lane in (1, 6):  # Brady Ellison / An San (~9.5 avg)
                    if roll > 0.42:
                        points = 10
                        is_x = random.random() > 0.5
                    elif roll > 0.15:
                        points = 9
                        is_x = False
                    elif roll > 0.05:
                        points = 8
                        is_x = False
                    else:
                        points = 7
                        is_x = False
                elif lane in (2, 4):  # Mete Gazoz / Marcus D'Almeida (~9.2 avg)
                    if roll > 0.50:
                        points = 10
                        is_x = random.random() > 0.6
                    elif roll > 0.22:
                        points = 9
                        is_x = False
                    elif roll > 0.08:
                        points = 8
                        is_x = False
                    elif roll > 0.03:
                        points = 7
                        is_x = False
                    else:
                        points = 6
                        is_x = False
                else:  # Deepika Kumari & others (~8.9 avg, wider histogram spread)
                    if roll > 0.55:
                        points = 10
                        is_x = random.random() > 0.65
                    elif roll > 0.28:
                        points = 9
                        is_x = False
                    elif roll > 0.12:
                        points = 8
                        is_x = False
                    elif roll > 0.05:
                        points = 7
                        is_x = False
                    elif roll > 0.02:
                        points = 6
                        is_x = False
                    else:
                        points = 5
                        is_x = False

                zone = points
                img_suffix = "x" if is_x else "normal"
                score = Score(
                    session_id=sa.session_id,
                    session_archer_id=sa.id,
                    round=round_num,
                    arrow_num=arrow_num,
                    zone=zone,
                    points=points,
                    confidence=round(random.uniform(0.93, 0.99), 3),
                    validated_by_ai=True,
                    image_id=f"target_scan_{sa.session_id}_{round_num}_{arrow_num}_{img_suffix}.jpg",
                )
                db.add(score)
                scores.append(score)
                total_accumulated += points

        sa.total_score = total_accumulated
        sa.current_round = 5
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

        # Clean up obsolete/duplicate test tournaments
        dummy_tournaments = db.query(Tournament).filter(
            (Tournament.name.ilike("%E2E Olympic%")) | 
            (Tournament.name == "Test Tournament") | 
            (Tournament.name == "Test No Location")
        ).all()
        for dt in dummy_tournaments:
            dt_sessions = db.query(TournamentSession).filter(TournamentSession.tournament_id == dt.id).all()
            for s in dt_sessions:
                db.delete(s)
            db.delete(dt)
        db.commit()

        tournaments, sessions = seed_tournaments(db, admin_user)
        session_archers = seed_session_archers(db, sessions)
        scores = seed_scores(db, session_archers)
        cameras = seed_cameras(db)
        camera_assignments = seed_camera_assignments(db, sessions, cameras)

        # Integrity check: verify that archer totals match sum of individual score points
        for sa in session_archers:
            calc_sum = db.query(func.sum(Score.points)).filter(Score.session_archer_id == sa.id).scalar() or 0
            if sa.total_score != calc_sum:
                sa.total_score = calc_sum
                db.commit()

        print("\n" + "="*60)
        print("[+] ARCHERY SCORING SYSTEM -- SEED DATA INITIALIZED")
        print("="*60)
        print(f"   Users: {len(users)} (Admin: admin / admin123!, Scorer: scorer / scorer123!)")
        print(f"   Realistic Tournaments: {len(tournaments)}")
        print(f"   Active & Completed Sessions: {len(sessions)}")
        print(f"   Registered Archers: {len(session_archers)}")
        print(f"   Arrow Impact Scores: {len(scores)}")
        print(f"   Cameras Assigned: {len(camera_assignments)}")
        print("="*60 + "\n")

    except Exception as e:
        logger.exception("seed_data_error", error=str(e))
        print(f"\n❌ Seed data failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
