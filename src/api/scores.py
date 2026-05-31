"""
Scoring API routes.

Story coverage: US-2.2 (apply scoring rules), US-3.1 (real-time score updates),
US-3.2 (arrow detection), US-3.3 (leaderboard updates)

Endpoints:
- POST /sessions/{session_id}/scores
- GET /sessions/{session_id}/scores
- GET /scores/{score_id}
- POST /scores/{score_id}/validate
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session as SQLSession
import structlog

from src.database import get_db
from src.schemas import ScoreCreate, ScoreResponse, ScoreValidateRequest
from src.dependencies import get_current_user
from src.models.user import User
from src.models.scoring import Score, SessionArcher
from src.models.tournament import Session
from src.services.scoring_service import ScoringService
from src.events import publish_event, EventType

logger = structlog.get_logger()

router = APIRouter(prefix="/sessions", tags=["scores"])


@router.post("/{session_id}/scores", response_model=ScoreResponse, status_code=status.HTTP_201_CREATED)
async def record_score(
    session_id: int,
    score_data: ScoreCreate,
    current_user: User = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """
    Record a score for an archer in a session.

    Story: US-2.2, US-3.1, US-3.2

    Includes automatic retry logic for database failures (Pattern #2).

    Args:
        session_id: Session ID
        score_data: Score details
        current_user: Authenticated user
        db: Database session

    Returns:
        Created score record

    Raises:
        HTTPException: 404 if session/archer not found, 400 if validation fails
    """
    try:
        # Verify session exists
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Verify session archer exists
        session_archer = (
            db.query(SessionArcher)
            .filter(SessionArcher.session_id == session_id, SessionArcher.id == score_data.session_archer_id)
            .first()
        )
        if not session_archer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archer not found in session",
            )

        # Validate score with business logic
        is_valid, error_msg = ScoringService.validate_score(score_data.zone, score_data.points)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=error_msg,
            )

        # Record score with automatic retry logic (Pattern #2)
        score = ScoringService.record_score_with_retry(
            db,
            score_data.session_archer_id,
            score_data.round,
            score_data.arrow_num,
            score_data.zone,
            score_data.points,
            score_data.image_id,
            max_retries=2,
            base_backoff=1.0,
        )

        logger.info(
            "score_recorded_via_api",
            session_id=session_id,
            archer_id=session_archer.archer_id,
            points=score_data.points,
        )

        return score

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("record_score_error", session_id=session_id, error=str(e))
        publish_event(
            EventType.ERROR_OCCURRED,
            {"error_type": "score_recording", "message": str(e)},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to record score",
        )


@router.get("/{session_id}/scores", response_model=List[ScoreResponse])
async def list_session_scores(
    session_id: int,
    db: SQLSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    round: Optional[int] = None,
):
    """
    List all scores in a session.

    Story: US-3.1

    Args:
        session_id: Session ID
        db: Database session
        skip: Pagination offset
        limit: Pagination limit
        round: Optional filter by round

    Returns:
        List of scores

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

        query = db.query(Score).filter(Score.session_id == session_id)

        if round is not None:
            query = query.filter(Score.round == round)

        scores = query.order_by(Score.created_at.desc()).offset(skip).limit(limit).all()

        logger.info("session_scores_listed", session_id=session_id, count=len(scores))
        return scores

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("list_scores_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list scores",
        )


@router.get("/scores/{score_id}", response_model=ScoreResponse)
async def get_score(score_id: int, db: SQLSession = Depends(get_db)):
    """
    Get a specific score by ID.

    Story: US-3.1

    Args:
        score_id: Score ID
        db: Database session

    Returns:
        Score object

    Raises:
        HTTPException: 404 if score not found
    """
    try:
        score = db.query(Score).filter(Score.id == score_id).first()
        if not score:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Score not found",
            )

        logger.info("score_retrieved", score_id=score_id)
        return score

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_score_error", score_id=score_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve score",
        )


@router.post("/scores/{score_id}/validate", response_model=ScoreResponse)
async def validate_score_record(
    score_id: int,
    validate_data: ScoreValidateRequest,
    current_user: User = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """
    Validate a score as processed by AI or manual verification.

    Story: US-3.2

    Args:
        score_id: Score ID
        validate_data: Validation flag
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated score record

    Raises:
        HTTPException: 404 if score not found
    """
    try:
        score = db.query(Score).filter(Score.id == score_id).first()
        if not score:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Score not found",
            )

        score.validated_by_ai = validate_data.validated

        db.commit()
        db.refresh(score)

        # Emit event
        publish_event(
            EventType.SCORE_VALIDATED,
            {"score_id": score_id, "validated": validate_data.validated},
        )

        logger.info("score_validated_via_api", score_id=score_id, validated=validate_data.validated)

        return score

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("validate_score_error", score_id=score_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to validate score",
        )
