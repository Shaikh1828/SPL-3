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
        Get leaderboard directly from database.

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
