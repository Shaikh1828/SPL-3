"""
Scoring service for arrow detection, validation, and score recording.

Implements:
- NFR Pattern #2: Scoring Failure Recovery (auto-retry with notification)
- NFR Pattern #4: Image Fallback Chain
- Score validation and calculation
- Leaderboard updates

Story coverage: US-2.2 (scoring rules), US-3.1 (real-time updates), US-3.2 (arrow detection), US-3.3 (leaderboard)
"""

import time
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy.exc import OperationalError
import structlog

from src.models.scoring import Score, SessionArcher
from src.models.tournament import Session as SessionModel
from src.events import publish_event, EventType
from src.cache import cache_manager, invalidate_leaderboard_cache, get_leaderboard_cache_key

logger = structlog.get_logger()

# Zone to points mapping (standard archery scoring)
ZONE_POINTS_MAPPING = {
    10: 10,  # Gold/bullseye
    9: 9,
    8: 8,
    7: 7,
    6: 6,
    5: 5,
    4: 4,
    3: 3,
    2: 2,
    1: 1,
    0: 0,  # Miss
}


class ScoringService:
    """Business logic for scoring operations."""

    @staticmethod
    def validate_score(zone: int, points: int) -> Tuple[bool, Optional[str]]:
        """
        Validate zone and points values.

        Args:
            zone: Zone number (0-10)
            points: Points awarded (0-10)

        Returns:
            Tuple of (is_valid, error_message)
        """
        if zone < 0 or zone > 10:
            return False, f"Zone must be 0-10, got {zone}"

        if points < 0 or points > 10:
            return False, f"Points must be 0-10, got {points}"

        # Validate zone-to-points mapping
        if zone not in ZONE_POINTS_MAPPING:
            return False, f"Invalid zone: {zone}"

        # Optional: Enforce strict mapping (zone must match points)
        # if ZONE_POINTS_MAPPING[zone] != points:
        #     return False, f"Zone {zone} should have {ZONE_POINTS_MAPPING[zone]} points, got {points}"

        return True, None

    @staticmethod
    def record_score_with_retry(
        db: Session,
        session_archer_id: int,
        round: int,
        arrow_num: int,
        zone: int,
        points: int,
        image_id: Optional[str] = None,
        max_retries: int = 2,
        base_backoff: float = 1.0,
    ) -> Optional[Score]:
        """
        Record a score with retry logic on database failure.

        Implements NFR Pattern #2: Scoring Failure Recovery

        Args:
            db: Database session
            session_archer_id: SessionArcher ID
            round: Round number
            arrow_num: Arrow number in round
            zone: Detected zone (0-10)
            points: Points to award
            image_id: Image file ID
            max_retries: Maximum retry attempts
            base_backoff: Base backoff time (exponential)

        Returns:
            Created Score object or None if all retries fail

        Raises:
            ValueError: If validation fails
        """
        # Validate score
        is_valid, error_msg = ScoringService.validate_score(zone, points)
        if not is_valid:
            raise ValueError(f"Score validation failed: {error_msg}")

        # Get session archer
        session_archer = db.query(SessionArcher).filter(SessionArcher.id == session_archer_id).first()
        if not session_archer:
            raise ValueError(f"SessionArcher not found: {session_archer_id}")

        last_error = None

        # Retry loop with exponential backoff (Pattern #2)
        for attempt in range(max_retries):
            try:
                # Create score record
                score = Score(
                    session_id=session_archer.session_id,
                    session_archer_id=session_archer_id,
                    round=round,
                    arrow_num=arrow_num,
                    zone=zone,
                    points=points,
                    image_id=image_id,
                    validated_by_ai=True if image_id else False,
                )

                db.add(score)
                db.commit()
                db.refresh(score)

                # Update session archer total score
                session_archer.total_score += points
                session_archer.current_round = round
                db.commit()

                logger.info(
                    "score_recorded_success",
                    score_id=score.id,
                    session_archer_id=session_archer_id,
                    points=points,
                    attempt=attempt + 1,
                )

                # Emit event for real-time update (Pattern #3: WebSocket broadcast)
                publish_event(
                    EventType.SCORE_RECORDED,
                    {
                        "score_id": score.id,
                        "session_archer_id": session_archer_id,
                        "session_id": session_archer.session_id,
                        "zone": zone,
                        "points": points,
                        "round": round,
                    },
                )

                # Invalidate leaderboard cache (Pattern #13)
                invalidate_leaderboard_cache(session_archer.session_id)

                return score

            except OperationalError as e:
                last_error = e
                logger.warning(
                    "score_record_retry",
                    session_archer_id=session_archer_id,
                    attempt=attempt + 1,
                    max_retries=max_retries,
                    error=str(e),
                )

                if attempt < max_retries - 1:
                    backoff_time = base_backoff * (2 ** attempt)
                    logger.info("score_record_backoff", backoff_seconds=backoff_time)
                    time.sleep(backoff_time)

            except Exception as e:
                logger.exception(
                    "score_record_error",
                    session_archer_id=session_archer_id,
                    error=str(e),
                )
                raise

        # All retries failed
        logger.error(
            "score_record_failed_max_retries",
            session_archer_id=session_archer_id,
            max_retries=max_retries,
        )

        # Emit failure event for notification
        publish_event(
            EventType.ERROR_OCCURRED,
            {
                "error_type": "score_recording_failed",
                "session_archer_id": session_archer_id,
                "message": f"Failed to record score after {max_retries} attempts",
            },
        )

        raise OperationalError("Failed to record score after max retries", None, last_error)

    @staticmethod
    def calculate_total_score(db: Session, session_archer_id: int) -> int:
        """
        Calculate total score for an archer in a session.

        Args:
            db: Database session
            session_archer_id: SessionArcher ID

        Returns:
            Total points sum
        """
        result = db.query(func.sum(Score.points)).filter(Score.session_archer_id == session_archer_id).scalar()
        return result or 0

    @staticmethod
    def get_scores_for_archer(
        db: Session, session_archer_id: int, round: Optional[int] = None
    ) -> list[Score]:
        """
        Get scores for an archer, optionally filtered by round.

        Args:
            db: Database session
            session_archer_id: SessionArcher ID
            round: Optional round number filter

        Returns:
            List of Score objects
        """
        query = db.query(Score).filter(Score.session_archer_id == session_archer_id)

        if round:
            query = query.filter(Score.round == round)

        return query.order_by(Score.round, Score.arrow_num).all()

    @staticmethod
    def get_session_leaderboard(db: Session, session_id: int, limit: int = 100) -> list[Dict[str, Any]]:
        """
        Get leaderboard for a session (ordered by total score).

        Args:
            db: Database session
            session_id: Session ID
            limit: Maximum number of results

        Returns:
            List of leaderboard items with archer info and scores
        """
        from sqlalchemy import func

        # Query session archers ordered by total score
        archers = (
            db.query(SessionArcher)
            .filter(SessionArcher.session_id == session_id)
            .order_by(SessionArcher.total_score.desc(), SessionArcher.archer_name)
            .limit(limit)
            .all()
        )

        leaderboard = []
        for rank, archer in enumerate(archers, 1):
            leaderboard.append(
                {
                    "rank": rank,
                    "archer_id": archer.archer_id,
                    "archer_name": archer.archer_name,
                    "total_score": archer.total_score,
                    "current_round": archer.current_round,
                    "session_archer_id": archer.id,
                }
            )

        return leaderboard

    @staticmethod
    def validate_score_record(db: Session, score_id: int, validated: bool) -> Optional[Score]:
        """
        Validate or invalidate a score record.

        Args:
            db: Database session
            score_id: Score ID
            validated: True to mark as validated, False otherwise

        Returns:
            Updated Score object
        """
        score = db.query(Score).filter(Score.id == score_id).first()
        if not score:
            return None

        score.validated_by_ai = validated
        db.commit()
        db.refresh(score)

        publish_event(
            EventType.SCORE_VALIDATED,
            {"score_id": score_id, "validated": validated},
        )

        logger.info("score_validated", score_id=score_id, validated=validated)

        return score


# Import at end to avoid circular imports
from sqlalchemy import func
from typing import Tuple
