"""
Seed data script for comprehensive database initialization & realistic tournament progression testing.

Populates database with:
1. Multi-role user accounts (admin, scorer, spectator, archers)
2. 24+ world-class and national archers with realistic profiles
3. 6 complete tournaments (Ongoing, Completed, Upcoming)
4. Multi-stage elimination brackets:
   - Stage 1: Qualification / Preliminary (16 archers)
   - Stage 2: Quarter-Finals (Top 8 advance, 8 eliminated)
   - Stage 3: Semi-Finals (Top 4 advance, 4 eliminated)
   - Stage 4: Medal Finals (Gold & Bronze matches)
5. Realistic arrow scores (10-X, 10, 9, 8, 7) reflecting Olympic-tier skill distributions
6. Realistic fatigue curves across ends (fresh -> peak -> fatigue dip -> final adrenaline push)
7. Full lane camera assignments & AI telemetry metadata

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


# Master Competitor Registry (24 Elite & National Archers with specific skill profiles)
ARCHERS_REGISTRY = [
    {"id": 101, "username": "kim_woojin", "name": "Kim Woo-jin", "country": "KOR", "tier": "god", "email": "kim.woojin@archeryscore.com"},
    {"id": 102, "username": "brady_ellison", "name": "Brady Ellison", "country": "USA", "tier": "god", "email": "brady.ellison@archeryscore.com"},
    {"id": 103, "username": "lim_sihyeon", "name": "Lim Si-hyeon", "country": "KOR", "tier": "god", "email": "lim.sihyeon@archeryscore.com"},
    {"id": 104, "username": "mete_gazoz", "name": "Mete Gazoz", "country": "TUR", "tier": "elite", "email": "mete.gazoz@archeryscore.com"},
    {"id": 105, "username": "marcus_dalmeida", "name": "Marcus D'Almeida", "country": "BRA", "tier": "elite", "email": "marcus.dalmeida@archeryscore.com"},
    {"id": 106, "username": "an_san", "name": "An San", "country": "KOR", "tier": "elite", "email": "an.san@archeryscore.com"},
    {"id": 107, "username": "casey_kaufhold", "name": "Casey Kaufhold", "country": "USA", "tier": "elite", "email": "casey.kaufhold@archeryscore.com"},
    {"id": 108, "username": "florian_unruh", "name": "Florian Unruh", "country": "GER", "tier": "elite", "email": "florian.unruh@archeryscore.com"},
    {"id": 109, "username": "ruman_shana", "name": "Md Ruman Shana", "country": "BAN", "tier": "pro", "email": "ruman.shana@archeryscore.com"},
    {"id": 110, "username": "sagor_islam", "name": "Md Sagor Islam", "country": "BAN", "tier": "pro", "email": "sagor.islam@archeryscore.com"},
    {"id": 111, "username": "deepika_kumari", "name": "Deepika Kumari", "country": "IND", "tier": "pro", "email": "deepika.kumari@archeryscore.com"},
    {"id": 112, "username": "zheng_yichai", "name": "Zheng Yichai", "country": "CHN", "tier": "pro", "email": "zheng.yichai@archeryscore.com"},
    {"id": 113, "username": "mauro_nespoli", "name": "Mauro Nespoli", "country": "ITA", "tier": "pro", "email": "mauro.nespoli@archeryscore.com"},
    {"id": 114, "username": "thomas_chirault", "name": "Thomas Chirault", "country": "FRA", "tier": "pro", "email": "thomas.chirault@archeryscore.com"},
    {"id": 115, "username": "baptiste_addis", "name": "Baptiste Addis", "country": "FRA", "tier": "pro", "email": "baptiste.addis@archeryscore.com"},
    {"id": 116, "username": "tang_chihchun", "name": "Tang Chih-Chun", "country": "TPE", "tier": "pro", "email": "tang.chihchun@archeryscore.com"},
    {"id": 117, "username": "zahid_hasan", "name": "Zahid Hasan", "country": "BAN", "tier": "national", "email": "zahid.hasan@archeryscore.com"},
    {"id": 118, "username": "nasrin_akter", "name": "Nasrin Akter", "country": "BAN", "tier": "national", "email": "nasrin.akter@archeryscore.com"},
    {"id": 119, "username": "atanu_das", "name": "Atanu Das", "country": "IND", "tier": "national", "email": "atanu.das@archeryscore.com"},
    {"id": 120, "username": "steve_wijler", "name": "Steve Wijler", "country": "NED", "tier": "national", "email": "steve.wijler@archeryscore.com"},
    {"id": 121, "username": "takaharu_furukawa", "name": "Takaharu Furukawa", "country": "JPN", "tier": "national", "email": "takaharu.furukawa@archeryscore.com"},
    {"id": 122, "username": "alejandra_valencia", "name": "Alejandra Valencia", "country": "MEX", "tier": "national", "email": "alejandra.valencia@archeryscore.com"},
    {"id": 123, "username": "jack_williams", "name": "Jack Williams", "country": "USA", "tier": "national", "email": "jack.williams@archeryscore.com"},
    {"id": 124, "username": "jane_doe", "name": "Jane Doe", "country": "GBR", "tier": "club", "email": "jane.doe@archeryscore.com"},
]


def seed_users(db: Session):
    """Create system role accounts and archer competitor profiles."""
    logger.info("seeding_users")

    system_users = [
        User(username="admin", email="admin@archeryscore.com", password_hash=hash_password("admin123!"), role="admin", is_active=True),
        User(username="scorer", email="scorer@archeryscore.com", password_hash=hash_password("scorer123!"), role="scorer", is_active=True),
        User(username="scorer2", email="scorer2@archeryscore.com", password_hash=hash_password("scorer123!"), role="scorer", is_active=True),
        User(username="spectator1", email="spectator1@archeryscore.com", password_hash=hash_password("Spectator123!"), role="spectator", is_active=True),
    ]

    all_users = list(system_users)
    for a in ARCHERS_REGISTRY:
        all_users.append(
            User(
                username=a["username"],
                email=a["email"],
                password_hash=hash_password("Archer123!"),
                role="archer",
                is_active=True,
            )
        )

    db_users = []
    for u in all_users:
        existing = db.query(User).filter(User.username == u.username).first()
        if not existing:
            db.add(u)
            db.commit()
            db.refresh(u)
            db_users.append(u)
        else:
            db_users.append(existing)

    logger.info("users_seeded", count=len(db_users))
    return db_users


def generate_arrow_score(tier: str, end_num: int, arrow_num: int) -> tuple[int, bool, float]:
    """
    Generate realistic arrow score and AI confidence based on tier and end fatigue.
    
    End Fatigue Curve:
      - End 1: Normal baseline
      - End 2: Peak focus
      - End 3: High focus
      - End 4: Fatigue dip (fatigue effects onset)
      - End 5: Final adrenaline surge
    """
    fatigue_delta = {
        1: 0.00,
        2: 0.08,   # Peak
        3: 0.03,   # Sustained
        4: -0.10,  # Fatigue dip
        5: 0.05,   # Adrenaline push
    }.get(end_num, 0.0)

    roll = random.random() + fatigue_delta

    if tier == "god":  # ~9.75 average (Kim Woo-jin, Brady Ellison, Lim Si-hyeon)
        if roll > 0.32:
            points = 10
            is_x = random.random() > 0.40
        elif roll > 0.06:
            points = 9
            is_x = False
        elif roll > 0.01:
            points = 8
            is_x = False
        else:
            points = 7
            is_x = False
    elif tier == "elite":  # ~9.45 average (Mete Gazoz, Marcus D'Almeida, An San, Casey Kaufhold)
        if roll > 0.42:
            points = 10
            is_x = random.random() > 0.50
        elif roll > 0.12:
            points = 9
            is_x = False
        elif roll > 0.03:
            points = 8
            is_x = False
        else:
            points = 7
            is_x = False
    elif tier == "pro":  # ~9.10 average (Ruman Shana, Sagor Islam, Deepika Kumari)
        if roll > 0.52:
            points = 10
            is_x = random.random() > 0.60
        elif roll > 0.20:
            points = 9
            is_x = False
        elif roll > 0.06:
            points = 8
            is_x = False
        elif roll > 0.01:
            points = 7
            is_x = False
        else:
            points = 6
            is_x = False
    else:  # National / Club (~8.50 average)
        if roll > 0.62:
            points = 10
            is_x = random.random() > 0.70
        elif roll > 0.30:
            points = 9
            is_x = False
        elif roll > 0.12:
            points = 8
            is_x = False
        elif roll > 0.04:
            points = 7
            is_x = False
        elif roll > 0.01:
            points = 6
            is_x = False
        else:
            points = 5
            is_x = False

    confidence = round(random.uniform(0.94, 0.995), 3)
    return points, is_x, confidence


def seed_database(db: Session, admin_user: User):
    """
    Seed multiple realistic tournaments with full multi-stage elimination brackets.
    """
    logger.info("seeding_tournaments_and_elimination_brackets")
    now = datetime.utcnow()

    # Clear old score, session_archer, session, and tournament records cleanly
    db.query(CameraLaneAssignment).delete()
    db.query(Score).delete()
    db.query(SessionArcher).delete()
    db.query(TournamentSession).delete()
    db.query(Tournament).delete()
    db.commit()

    # Build Map of username/name to User object
    users_by_username = {u.username: u for u in db.query(User).all()}

    # Definition of 5 Distinct Tournaments
    tournament_configs = [
        # 1. Summer Regional Qualifier 2026 (ONGOING)
        {
            "name": "Summer Regional Qualifier 2026",
            "location": "National Archery Arena, Dhaka",
            "description": "Premiere world ranking tournament featuring 16 international champions progressing through 1/4 finals, semi-finals, and live medal shootouts.",
            "start_date": now - timedelta(days=2),
            "end_date": now + timedelta(days=2),
            "stages": [
                {
                    "name": "Qualification Round 720 (16 Archers)",
                    "round_number": 1,
                    "num_lanes": 16,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 5,
                    "status": "completed",
                    "archers_count": 16,  # 16 start
                },
                {
                    "name": "Quarter-Finals 1/4 Elimination (Top 8)",
                    "round_number": 2,
                    "num_lanes": 8,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 4,
                    "status": "completed",
                    "archers_count": 8,   # Top 8 advance (8 eliminated)
                },
                {
                    "name": "Semi-Finals Elimination (Top 4)",
                    "round_number": 3,
                    "num_lanes": 4,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 4,
                    "status": "completed",
                    "archers_count": 4,   # Top 4 advance (4 eliminated)
                },
                {
                    "name": "Gold & Bronze Medal Finals (Live Match)",
                    "round_number": 4,
                    "num_lanes": 4,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 3,   # Live ongoing (3 ends completed out of 5)
                    "status": "active",
                    "archers_count": 4,   # Top 4 shoot medal match
                },
            ],
        },
        # 2. World Archery Championship 2026 (COMPLETED)
        {
            "name": "World Archery Championship 2026",
            "location": "Olympic Training Range, Savar",
            "description": "World Championship premier stage with 16 elite archers.",
            "start_date": now - timedelta(days=8),
            "end_date": now - timedelta(days=5),
            "stages": [
                {
                    "name": "Recurve 720 Qualification",
                    "round_number": 1,
                    "num_lanes": 16,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 5,
                    "status": "completed",
                    "archers_count": 16,
                },
                {
                    "name": "Championship Finals",
                    "round_number": 2,
                    "num_lanes": 4,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 5,
                    "status": "completed",
                    "archers_count": 4,
                },
            ],
        },
        # 2. Asia Cup Archery Grand Prix 2026 (COMPLETED)
        {
            "name": "Asia Cup Archery Grand Prix 2026",
            "location": "BKSP Archery Ground, Savar",
            "description": "Continental Grand Prix with 16 elite Asian and international archers. Fully completed multi-stage bracket.",
            "start_date": now - timedelta(days=15),
            "end_date": now - timedelta(days=12),
            "stages": [
                {
                    "name": "Stage 1 - Recurve 70m Qualification (16 Archers)",
                    "round_number": 1,
                    "num_lanes": 16,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 5,
                    "status": "completed",
                    "archers_count": 16,
                },
                {
                    "name": "Stage 2 - Quarter-Finals Bracket (Top 8)",
                    "round_number": 2,
                    "num_lanes": 8,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 4,
                    "status": "completed",
                    "archers_count": 8,
                },
                {
                    "name": "Stage 3 - Semi-Finals Cut (Top 4)",
                    "round_number": 3,
                    "num_lanes": 4,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 4,
                    "status": "completed",
                    "archers_count": 4,
                },
                {
                    "name": "Stage 4 - Gold & Bronze Medal Shootout",
                    "round_number": 4,
                    "num_lanes": 4,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 5,
                    "status": "completed",
                    "archers_count": 4,
                },
            ],
        },
        # 3. Bangladesh National Outdoor Championship 2026 (COMPLETED)
        {
            "name": "Bangladesh National Outdoor Championship 2026",
            "location": "Shaheed Ahsan Ullah Master Stadium, Tongi",
            "description": "Annual National Archery Championship with 12 national team competitors advancing to championship finals.",
            "start_date": now - timedelta(days=35),
            "end_date": now - timedelta(days=32),
            "stages": [
                {
                    "name": "National Qualification 720 (12 Archers)",
                    "round_number": 1,
                    "num_lanes": 12,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 5,
                    "status": "completed",
                    "archers_count": 12,
                },
                {
                    "name": "Championship Semi-Finals (Top 4)",
                    "round_number": 2,
                    "num_lanes": 4,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 4,
                    "status": "completed",
                    "archers_count": 4,
                },
                {
                    "name": "National Gold Medal Final",
                    "round_number": 3,
                    "num_lanes": 2,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 5,
                    "status": "completed",
                    "archers_count": 2,
                },
            ],
        },
        # 4. Winter Indoor Invitational Grand Prix 2025 (COMPLETED)
        {
            "name": "Winter Indoor Invitational Grand Prix 2025",
            "location": "Sylhet International Sports Range",
            "description": "18m Indoor international open tournament with precision spot target scoring.",
            "start_date": now - timedelta(days=90),
            "end_date": now - timedelta(days=87),
            "stages": [
                {
                    "name": "18m Indoor Ranking Round (12 Archers)",
                    "round_number": 1,
                    "num_lanes": 12,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 5,
                    "status": "completed",
                    "archers_count": 12,
                },
                {
                    "name": "Indoor Medal Match Finals (Top 4)",
                    "round_number": 2,
                    "num_lanes": 4,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 5,
                    "status": "completed",
                    "archers_count": 4,
                },
            ],
        },
        # 5. Olympic Selection Trials 2026 (UPCOMING / PAUSED)
        {
            "name": "Olympic Selection Trials 2026",
            "location": "National Sports Complex Arena, Mirpur",
            "description": "Upcoming national Olympic selection trials featuring 16 registered recurve archers.",
            "start_date": now + timedelta(days=14),
            "end_date": now + timedelta(days=18),
            "stages": [
                {
                    "name": "Trial Stage 1 - 70m Ranking",
                    "round_number": 1,
                    "num_lanes": 16,
                    "arrows_per_round": 6,
                    "ends_to_shoot": 0,
                    "status": "paused",
                    "archers_count": 16,
                },
            ],
        },
    ]

    total_scores_count = 0
    total_archers_registered = 0
    all_seeded_sessions = []

    for t_conf in tournament_configs:
        tourney = Tournament(
            name=t_conf["name"],
            location=t_conf["location"],
            description=t_conf["description"],
            start_date=t_conf["start_date"],
            end_date=t_conf["end_date"],
            created_by_user_id=admin_user.id,
        )
        db.add(tourney)
        db.commit()
        db.refresh(tourney)

        # Track surviving archers round by round
        current_qualified_archers = ARCHERS_REGISTRY[:16]

        for stage_conf in t_conf["stages"]:
            sess = TournamentSession(
                tournament_id=tourney.id,
                name=stage_conf["name"],
                round_number=stage_conf["round_number"],
                num_lanes=stage_conf["num_lanes"],
                arrows_per_round=stage_conf["arrows_per_round"],
                status=stage_conf["status"],
                start_time=t_conf["start_date"] if stage_conf["status"] in ["active", "completed"] else None,
                end_time=t_conf["end_date"] if stage_conf["status"] == "completed" else None,
            )
            db.add(sess)
            db.commit()
            db.refresh(sess)
            all_seeded_sessions.append(sess)

            archers_for_this_stage = current_qualified_archers[:stage_conf["archers_count"]]
            stage_results = []

            # Register Session Archers and shoot arrows
            for lane_idx, archer_data in enumerate(archers_for_this_stage):
                lane_num = lane_idx + 1
                user_obj = users_by_username.get(archer_data["username"])
                user_id = user_obj.id if user_obj else archer_data["id"]

                sa = SessionArcher(
                    session_id=sess.id,
                    archer_id=user_id,
                    archer_name=archer_data["name"],
                    lane_number=lane_num,
                    current_round=1,
                    total_score=0,
                )
                db.add(sa)
                db.commit()
                db.refresh(sa)
                total_archers_registered += 1

                # Generate arrows if ends_to_shoot > 0
                accumulated_total = 0
                tens_count = 0
                xs_count = 0
                ends_shot = stage_conf["ends_to_shoot"]

                if ends_shot > 0:
                    for end_num in range(1, ends_shot + 1):
                        for arrow_num in range(1, stage_conf["arrows_per_round"] + 1):
                            pts, is_x, conf = generate_arrow_score(archer_data["tier"], end_num, arrow_num)
                            if pts == 10:
                                tens_count += 1
                            if is_x:
                                xs_count += 1

                            img_suffix = "x" if is_x else "normal"
                            score = Score(
                                session_id=sess.id,
                                session_archer_id=sa.id,
                                round=end_num,
                                arrow_num=arrow_num,
                                zone=pts,
                                points=pts,
                                confidence=conf,
                                validated_by_ai=True,
                                image_id=f"target_scan_{sess.id}_{end_num}_{arrow_num}_{img_suffix}.jpg",
                            )
                            db.add(score)
                            accumulated_total += pts
                            total_scores_count += 1

                    sa.total_score = accumulated_total
                    sa.current_round = ends_shot
                    db.commit()

                stage_results.append({
                    "archer_data": archer_data,
                    "total_score": accumulated_total,
                    "tens_count": tens_count,
                    "xs_count": xs_count,
                })

            # Sort archers by score to determine who advances to the next elimination stage
            stage_results.sort(key=lambda x: (-x["total_score"], -x["tens_count"], -x["xs_count"]))
            current_qualified_archers = [item["archer_data"] for item in stage_results]

    db.commit()
    logger.info("database_seeded_successfully", total_scores=total_scores_count, total_archers=total_archers_registered)
    return all_seeded_sessions


def seed_cameras_and_assignments(db: Session, sessions: list):
    """Seed camera hardware and map active lanes."""
    logger.info("seeding_cameras_and_assignments")

    cameras_data = [
        {"name": "Lane 1 Cam (Target A)", "camera_type": "RTSP", "url": "rtsp://cam-lane1.local:554/live"},
        {"name": "Lane 2 Cam (Target B)", "camera_type": "RTSP", "url": "rtsp://cam-lane2.local:554/live"},
        {"name": "Lane 3 Cam (Target C)", "camera_type": "RTSP", "url": "rtsp://cam-lane3.local:554/live"},
        {"name": "Lane 4 Cam (Target D)", "camera_type": "RTSP", "url": "rtsp://cam-lane4.local:554/live"},
        {"name": "Lane 5 Cam (Target E)", "camera_type": "RTSP", "url": "rtsp://cam-lane5.local:554/live"},
        {"name": "Lane 6 Cam (Target F)", "camera_type": "RTSP", "url": "rtsp://cam-lane6.local:554/live"},
    ]

    cameras = []
    for c_data in cameras_data:
        existing = db.query(Camera).filter(Camera.name == c_data["name"]).first()
        if not existing:
            c = Camera(name=c_data["name"], camera_type=c_data["camera_type"], url=c_data["url"], status="connected")
            db.add(c)
            db.commit()
            db.refresh(c)
            cameras.append(c)
        else:
            cameras.append(existing)

    # Assign cameras to active sessions
    assignments_count = 0
    for s in sessions:
        if s.status == "active":
            for lane_idx in range(min(s.num_lanes, len(cameras))):
                existing_assignment = db.query(CameraLaneAssignment).filter(
                    CameraLaneAssignment.session_id == s.id,
                    CameraLaneAssignment.lane == lane_idx + 1,
                ).first()
                if not existing_assignment:
                    assignment = CameraLaneAssignment(
                        camera_id=cameras[lane_idx].id,
                        session_id=s.id,
                        lane=lane_idx + 1,
                    )
                    db.add(assignment)
                    assignments_count += 1
    db.commit()
    logger.info("cameras_assigned", count=assignments_count)


def main():
    """Run all seed operations and print validation summary."""
    print("\n" + "="*65)
    print("🎯 ARCHERY SCORING SYSTEM — HIGH REALISM DATABASE SEEDER")
    print("="*65)
    db = SessionLocal()

    try:
        users = seed_users(db)
        admin_user = users[0]

        sessions = seed_database(db, admin_user)
        seed_cameras_and_assignments(db, sessions)

        # Integrity Check
        total_tourneys = db.query(Tournament).count()
        total_sessions = db.query(TournamentSession).count()
        total_archers = db.query(SessionArcher).count()
        total_scores = db.query(Score).count()
        total_tens = db.query(Score).filter(Score.points == 10).count()
        total_nines = db.query(Score).filter(Score.points == 9).count()

        print(f"\n✅ DATABASE SEEDING COMPLETED SUCCESSFULLY!")
        print(f"   • Total Tournaments:      {total_tourneys}")
        print(f"   • Elimination Sessions:   {total_sessions}")
        print(f"   • Registered Archers:     {total_archers}")
        print(f"   • Arrow Score Impacts:    {total_scores:,}")
        print(f"   • Perfect 10s Recorded:   {total_tens:,} ({round((total_tens/total_scores)*100, 1)}%)")
        print(f"   • Solid 9s Recorded:      {total_nines:,} ({round((total_nines/total_scores)*100, 1)}%)")
        print("="*65 + "\n")

    except Exception as e:
        logger.exception("seed_failed", error=str(e))
        print(f"\n❌ Seed failed: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
