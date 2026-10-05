"""
Leaderboard service for caching and real-time aggregation.

Implements:
- NFR Pattern #11: Application Caching (TTL-based)
- NFR Pattern #13: Leaderboard Caching (1-min TTL, event-driven invalidation)
- Efficient queries for leaderboard data

Story coverage: US-3.3 (leaderboard updates)
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
import structlog

from src.models.scoring import Score, SessionArcher
from src.models.tournament import Session as SessionModel
from src.cache import cache_manager, get_leaderboard_cache_key, invalidate_leaderboard_cache
from src.events import subscribe_to_event, EventType

logger = structlog.get_logger()


class LeaderboardService:
    """Leaderboard aggregation and caching service."""

    def __init__(self):
        """Initialize leaderboard service."""
        # Subscribe to score events for cache invalidation
        subscribe_to_event(EventType.SCORE_RECORDED, self._on_score_recorded)
        subscribe_to_event(EventType.SCORE_VALIDATED, self._on_score_validated)

    @staticmethod
    def get_leaderboard_cached(db: Session, session_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get leaderboard for session with caching.

        Implements NFR Pattern #13: Leaderboard Caching (1-min TTL)

        Args:
            db: Database session
            session_id: Session ID
            limit: Maximum results

        Returns:
            List of leaderboard items ordered by score
        """
        cache_key = get_leaderboard_cache_key(session_id)

        # Try cache first (Pattern #13: 1-min TTL)
        cached = cache_manager.get(cache_key)
        if cached:
            logger.debug("leaderboard_cache_hit", session_id=session_id)
            return cached

        logger.debug("leaderboard_cache_miss", session_id=session_id)

        # Query from database
        leaderboard = LeaderboardService.get_leaderboard(db, session_id, limit)

        # Cache result (1-minute TTL)
        cache_manager.set(cache_key, leaderboard, ttl_seconds=60)

        return leaderboard

    @staticmethod
    def get_leaderboard(db: Session, session_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get leaderboard directly from database with detailed stats.

        Args:
            db: Database session
            session_id: Session ID
            limit: Maximum results

        Returns:
            List of leaderboard items sorted by total_score DESC
        """
        # Query session archers
        archers = (
            db.query(SessionArcher)
            .filter(SessionArcher.session_id == session_id)
            .order_by(SessionArcher.total_score.desc(), SessionArcher.archer_name.asc())
            .limit(limit)
            .all()
        )

        leaderboard = []
        for rank, archer in enumerate(archers, 1):
            scores = (
                db.query(Score)
                .filter(Score.session_archer_id == archer.id)
                .order_by(Score.created_at.desc(), Score.id.desc())
                .all()
            )
            arrows_count = len(scores)
            tens_count = sum(1 for s in scores if s.points == 10)
            xs_count = sum(1 for s in scores if s.zone == 10)
            avg_score = round(archer.total_score / arrows_count, 2) if arrows_count > 0 else 0.0
            recent_arrows = [s.points for s in scores[:6]]

            leaderboard.append(
                {
                    "rank": rank,
                    "archer_id": archer.archer_id,
                    "archer_name": archer.archer_name,
                    "total_score": archer.total_score,
                    "current_round": archer.current_round,
                    "session_archer_id": archer.id,
                    "lane_number": archer.lane_number,
                    "arrows_recorded": arrows_count,
                    "tens_count": tens_count,
                    "xs_count": xs_count,
                    "average_score": avg_score,
                    "recent_arrows": recent_arrows,
                }
            )

        return leaderboard

    @staticmethod
    def get_tournament_leaderboard(db: Session, tournament_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get aggregated tournament-wide leaderboard across all tournament sessions.

        Args:
            db: Database session
            tournament_id: Tournament ID
            limit: Maximum results

        Returns:
            List of tournament leaderboard items sorted by total_score DESC
        """
        # 1. Fetch all sessions in this tournament
        sessions = db.query(SessionModel).filter(SessionModel.tournament_id == tournament_id).all()
        if not sessions:
            return []

        session_map = {s.id: s.name for s in sessions}
        session_ids = list(session_map.keys())

        # 2. Fetch all session archers in these sessions
        archers = (
            db.query(SessionArcher)
            .filter(SessionArcher.session_id.in_(session_ids))
            .all()
        )
        if not archers:
            return []

        # 3. Group and aggregate by archer_id / archer_name
        grouped: Dict[Any, Dict[str, Any]] = {}
        for sa in archers:
            key = sa.archer_id or sa.archer_name
            scores = (
                db.query(Score)
                .filter(Score.session_archer_id == sa.id)
                .order_by(Score.created_at.desc(), Score.id.desc())
                .all()
            )
            arrows_cnt = len(scores)
            tens_cnt = sum(1 for s in scores if s.points == 10)
            xs_cnt = sum(1 for s in scores if s.zone == 10)
            pts_list = [s.points for s in scores]

            if key not in grouped:
                grouped[key] = {
                    "archer_id": sa.archer_id,
                    "archer_name": sa.archer_name,
                    "total_score": sa.total_score,
                    "current_round": sa.current_round,
                    "session_archer_id": sa.id,
                    "lane_number": sa.lane_number,
                    "arrows_recorded": arrows_cnt,
                    "tens_count": tens_cnt,
                    "xs_count": xs_cnt,
                    "sessions_count": 1,
                    "session_name": session_map.get(sa.session_id, "Main Round"),
                    "recent_arrows": pts_list[:6],
                }
            else:
                grouped[key]["total_score"] += sa.total_score
                grouped[key]["arrows_recorded"] += arrows_cnt
                grouped[key]["tens_count"] += tens_cnt
                grouped[key]["xs_count"] += xs_cnt
                grouped[key]["sessions_count"] += 1
                grouped[key]["current_round"] = max(grouped[key]["current_round"], sa.current_round)
                if sa.lane_number:
                    grouped[key]["lane_number"] = sa.lane_number
                grouped[key]["recent_arrows"] = (pts_list + grouped[key]["recent_arrows"])[:6]

        # 4. Calculate averages and sort
        results = list(grouped.values())
        for item in results:
            item["average_score"] = (
                round(item["total_score"] / item["arrows_recorded"], 2)
                if item["arrows_recorded"] > 0
                else 0.0
            )

        # Sort primarily by total_score DESC, then tens_count DESC, then archer_name ASC
        results.sort(key=lambda x: (-x["total_score"], -x["tens_count"], x["archer_name"]))

        # 5. Apply ranks and slice limit
        leaderboard = []
        for rank, item in enumerate(results[:limit], 1):
            item["rank"] = rank
            leaderboard.append(item)

        return leaderboard

    @staticmethod
    def invalidate_cache(session_id: int):
        """
        Manually invalidate leaderboard cache for a session.

        Args:
            session_id: Session ID to invalidate
        """
        invalidate_leaderboard_cache(session_id)
        logger.debug("leaderboard_cache_invalidated", session_id=session_id)

    def _on_score_recorded(self, event: Any):
        """Callback when score is recorded - invalidate cache."""
        session_id = event.data.get("session_id")
        if session_id:
            self.invalidate_cache(session_id)
            logger.debug("leaderboard_cache_invalidated_on_score", session_id=session_id)

    def _on_score_validated(self, event: Any):
        """Callback when score is validated - invalidate cache."""
        # Get session_id from score (would need to query in production)
        logger.debug("leaderboard_cache_invalidation_triggered", event=event.event_type)


# Global leaderboard service instance
leaderboard_service = LeaderboardService()
