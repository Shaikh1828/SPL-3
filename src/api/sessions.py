"""
Session API routes.

Story coverage: US-2.1 (create session)
Endpoints:
- GET /tournaments/{tournament_id}/sessions
- POST /tournaments/{tournament_id}/sessions
- GET /sessions/{session_id}
- PATCH /sessions/{session_id}
- POST /sessions/{session_id}/archers
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session as SQLSession
import structlog

from src.database import get_db
from src.schemas import SessionCreate, SessionResponse, SessionArcherResponse
from src.dependencies import get_current_user
from src.models.user import User
from src.models.tournament import Tournament, Session
from src.models.scoring import SessionArcher
from src.events import publish_event, EventType

logger = structlog.get_logger()

router = APIRouter(tags=["sessions"])


@router.get("/tournaments/{tournament_id}/sessions", response_model=Dict[str, Any])
async def list_sessions(
    tournament_id: int,
    db: SQLSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: Optional[str] = Query(None, alias="status"),
):
    """
    List all sessions in a tournament.

    Story: US-2.1

    Args:
        tournament_id: Tournament ID
        db: Database session
        skip: Pagination skip
        limit: Pagination limit
        status_filter: Optional filter by session status

    Returns:
        Paginated list of sessions
    """
    try:
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tournament:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tournament not found",
            )

        query = db.query(Session).filter(Session.tournament_id == tournament_id)
        if status_filter:
            query = query.filter(Session.status == status_filter)

        total = query.count()
        sessions = query.offset(skip).limit(limit).all()
        items = [SessionResponse.model_validate(s).model_dump() for s in sessions]

        logger.info("sessions_listed", tournament_id=tournament_id, count=len(items))
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("list_sessions_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list sessions",
        )


@router.post("/tournaments/{tournament_id}/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    tournament_id: int,
    session_data: SessionCreate,
    current_user: User = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """
    Create a new session in a tournament.

    Story: US-2.1

    Args:
        tournament_id: Tournament ID
        session_data: Session details
        current_user: Authenticated user
        db: Database session

    Returns:
        Created session

    Raises:
        HTTPException: 404 if tournament not found, 400 if validation fails
    """
    try:
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tournament:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tournament not found",
            )

        session = Session(
            tournament_id=tournament_id,
            name=session_data.name,
            round_number=session_data.round_number,
            num_lanes=session_data.num_lanes,
            arrows_per_round=session_data.arrows_per_round,
            status="active",
        )

        db.add(session)
        db.commit()
        db.refresh(session)

        # Emit event
        publish_event(
            EventType.SESSION_CREATED,
            {"session_id": session.id, "tournament_id": tournament_id},
        )

        logger.info("session_created", session_id=session.id, tournament_id=tournament_id)
        return session

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("create_session_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session",
        )


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: int, db: SQLSession = Depends(get_db)):
    """
    Get session by ID.

    Story: US-2.1

    Args:
        session_id: Session ID
        db: Database session

    Returns:
        Session object

    Raises:
        HTTPException: 404 if session not found
    """
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        logger.info("session_retrieved", session_id=session_id)
        return session

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_session_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve session",
        )


@router.patch("/sessions/{session_id}", response_model=SessionResponse)
async def update_session_status(
    session_id: int,
    update_data: dict,
    current_user: User = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """
    Update session status (active, paused, completed).

    Story: US-2.1

    Args:
        session_id: Session ID
        update_data: Update data with new status
        current_user: Authenticated user
        db: Database session

    Returns:
        Updated session

    Raises:
        HTTPException: 404 if session not found, 400 if status invalid
    """
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        new_status = update_data.get("status")
        if new_status not in ["active", "paused", "completed"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status. Must be active, paused, or completed",
            )

        old_status = session.status
        session.status = new_status

        from datetime import datetime
        if new_status == "active":
            session.start_time = datetime.utcnow()
        elif new_status == "completed":
            session.end_time = datetime.utcnow()

        db.commit()
        db.refresh(session)

        # Emit event
        publish_event(
            EventType.SESSION_STATE_CHANGED,
            {"session_id": session_id, "old_status": old_status, "new_status": new_status},
        )

        logger.info("session_status_updated", session_id=session_id, new_status=new_status)
        return session

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("update_session_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update session",
        )


@router.post("/sessions/{session_id}/archers", response_model=SessionArcherResponse, status_code=status.HTTP_201_CREATED)
async def add_archer_to_session(
    session_id: int,
    archer_data: dict,
    current_user: User = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """
    Add an archer to a session.

    Story: US-2.1

    Args:
        session_id: Session ID
        archer_data: Archer details (archer_id, archer_name)
        current_user: Authenticated user
        db: Database session

    Returns:
        Created session archer record

    Raises:
        HTTPException: 404 if session not found, 400 if validation fails
    """
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        archer_id = archer_data.get("archer_id")
        archer_name = archer_data.get("archer_name", f"Archer {archer_id}")
        lane_number = archer_data.get("lane_number")

        # Validate lane_number if provided
        if lane_number is not None:
            if lane_number < 1 or lane_number > session.num_lanes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid lane_number. Must be between 1 and {session.num_lanes}",
                )
            
            # Check if lane is already assigned to another archer
            lane_taken = (
                db.query(SessionArcher)
                .filter(
                    SessionArcher.session_id == session_id,
                    SessionArcher.lane_number == lane_number,
                )
                .first()
            )
            
            if lane_taken:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Lane {lane_number} is already assigned to another archer",
                )

        # Check if archer already in session
        existing = (
            db.query(SessionArcher)
            .filter(SessionArcher.session_id == session_id, SessionArcher.archer_id == archer_id)
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archer already in session",
            )

        session_archer = SessionArcher(
            session_id=session_id,
            archer_id=archer_id,
            archer_name=archer_name,
            lane_number=lane_number,
            current_round=1,
            total_score=0,
        )

        db.add(session_archer)
        db.commit()
        db.refresh(session_archer)

        logger.info("archer_added_to_session", session_id=session_id, archer_id=archer_id)
        return session_archer

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("add_archer_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add archer to session",
        )


@router.get("/sessions/{session_id}/archers", response_model=List[SessionArcherResponse])
async def list_session_archers(
    session_id: int,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all archers registered in a session."""
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        archers = db.query(SessionArcher).filter(SessionArcher.session_id == session_id).order_by(SessionArcher.lane_number.asc()).all()
        return archers
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("list_archers_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list session archers",
        )


@router.delete("/sessions/{session_id}/archers/{session_archer_id}", status_code=status.HTTP_200_OK)
async def remove_archer_from_session(
    session_id: int,
    session_archer_id: int,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Remove an archer from a session."""
    try:
        session_archer = (
            db.query(SessionArcher)
            .filter(SessionArcher.session_id == session_id, SessionArcher.id == session_archer_id)
            .first()
        )
        if not session_archer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Archer not found in this session",
            )
        db.delete(session_archer)
        db.commit()
        logger.info("archer_removed_from_session", session_id=session_id, session_archer_id=session_archer_id)
        return {"success": True, "message": "Archer successfully removed from session"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("remove_archer_error", session_id=session_id, session_archer_id=session_archer_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to remove archer from session",
        )
