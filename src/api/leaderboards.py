"""
Leaderboard API routes.

Story coverage: US-3.3 (real-time leaderboard updates)

Endpoints:
- GET /sessions/{session_id}/leaderboard
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session as SQLSession
import structlog

from src.database import get_db
from src.schemas import LeaderboardItem, TournamentLeaderboardItem
from src.models.tournament import Session, Tournament
from src.services.leaderboard_service import LeaderboardService

logger = structlog.get_logger()

router = APIRouter(tags=["leaderboards"])


@router.get("/tournaments/{tournament_id}/leaderboard", response_model=List[TournamentLeaderboardItem])
async def get_tournament_leaderboard(
    tournament_id: int,
    db: SQLSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
):
    """
    Get consolidated tournament-wide leaderboard aggregating archers across all sessions.

    Args:
        tournament_id: Tournament ID
        db: Database session
        limit: Maximum records to return

    Returns:
        List of tournament leaderboard items sorted by total_score DESC
    """
    try:
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tournament:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tournament not found",
            )

        leaderboard = LeaderboardService.get_tournament_leaderboard(db, tournament_id, limit=limit)
        return leaderboard
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_tournament_leaderboard_error", tournament_id=tournament_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tournament leaderboard",
        )


@router.get("/sessions/{session_id}/leaderboard", response_model=List[LeaderboardItem])
async def get_leaderboard(
    session_id: int,
    db: SQLSession = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    use_cache: bool = Query(True),
):
    """
    Get leaderboard for a session with caching.

    Story: US-3.3

    Implements Pattern #13: Leaderboard Caching with 1-minute TTL and event-driven invalidation.

    Args:
        session_id: Session ID
        db: Database session
        limit: Maximum records to return
        use_cache: Whether to use cache (default: True)

    Returns:
        List of leaderboard items sorted by total_score DESC

    Raises:
        HTTPException: 404 if session not found
    """
    try:
        # Verify session exists
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Get leaderboard with optional caching (Pattern #13)
        if use_cache:
            leaderboard = LeaderboardService.get_leaderboard_cached(db, session_id, limit=limit)
        else:
            leaderboard = LeaderboardService.get_leaderboard(db, session_id, limit=limit)

        logger.info(
            "leaderboard_retrieved",
            session_id=session_id,
            count=len(leaderboard),
            cached=use_cache,
        )

        return leaderboard

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_leaderboard_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve leaderboard",
        )
