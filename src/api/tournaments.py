"""
Tournament API routes.

Story coverage: US-2.1 (create tournament and session)
Endpoints:
- GET /tournaments
- POST /tournaments
- GET /tournaments/{tournament_id}
- PUT /tournaments/{tournament_id}
- DELETE /tournaments/{tournament_id}
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import structlog

from src.database import get_db
from src.schemas import TournamentCreate, TournamentResponse
from src.dependencies import get_current_user, require_roles
from src.models.user import User
from src.models.tournament import Tournament, Session as TournamentSession
from src.models.scoring import SessionArcher

logger = structlog.get_logger()

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


def build_tournament_dict(t: Tournament, db: Session) -> dict:
    """Calculate tournament status, session counters, archer count, and aggregate winner."""
    sessions = t.sessions or []
    total_sessions = len(sessions)
    active_sessions = sum(1 for s in sessions if s.status == "active")
    completed_sessions = sum(1 for s in sessions if s.status == "completed")

    now = datetime.now(timezone.utc)
    start_dt = t.start_date
    if start_dt and start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)
    end_dt = t.end_date
    if end_dt and end_dt.tzinfo is None:
        end_dt = end_dt.replace(tzinfo=timezone.utc)

    # Dynamic status evaluation
    if total_sessions > 0 and completed_sessions == total_sessions:
        status_val = "completed"
    elif end_dt and end_dt < now and active_sessions == 0:
        status_val = "completed"
    elif start_dt and start_dt > now and active_sessions == 0 and completed_sessions == 0:
        status_val = "upcoming"
    elif active_sessions > 0 or (start_dt and start_dt <= now and (not end_dt or end_dt >= now)):
        status_val = "ongoing"
    else:
        status_val = "completed" if (end_dt and end_dt < now and active_sessions == 0) else "ongoing"

    archer_names = set()
    winner_name = None
    winner_score = None

    if sessions:
        session_ids = [s.id for s in sessions]
        archers = (
            db.query(SessionArcher)
            .filter(SessionArcher.session_id.in_(session_ids))
            .all()
        )
        for sa in archers:
            archer_names.add(sa.archer_name)

        from src.services.leaderboard_service import LeaderboardService
        t_leaderboard = LeaderboardService.get_tournament_leaderboard(db, t.id, limit=1)
        if t_leaderboard and t_leaderboard[0]["total_score"] > 0:
            winner_name = t_leaderboard[0]["archer_name"]
            winner_score = t_leaderboard[0]["total_score"]

    return {
        "id": t.id,
        "name": t.name,
        "location": t.location or "",
        "description": t.description or "",
        "start_date": t.start_date,
        "end_date": t.end_date,
        "created_by_user_id": t.created_by_user_id,
        "created_at": t.created_at,
        "status": status_val,
        "total_sessions": total_sessions,
        "active_sessions": active_sessions,
        "completed_sessions": completed_sessions,
        "total_archers": len(archer_names),
        "winner_name": winner_name,
        "winner_score": winner_score,
    }


@router.get("", response_model=Dict[str, Any])
async def list_tournaments(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    status_filter: Optional[str] = Query(None, alias="status"),
):
    """
    List all tournaments with pagination, metrics, and status filter.

    Story: US-2.1

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum records to return
        search: Optional search by name
        status_filter: Optional filter ('ongoing', 'completed', 'upcoming', 'all')

    Returns:
        List of tournaments with metrics and winner information
    """
    try:
        query = db.query(Tournament)

        if search:
            query = query.filter(Tournament.name.ilike(f"%{search}%"))

        tournaments = query.order_by(Tournament.created_at.desc()).all()

        items = [build_tournament_dict(t, db) for t in tournaments]

        if status_filter and status_filter.lower() != "all":
            items = [item for item in items if item["status"] == status_filter.lower()]

        total = len(items)
        paginated_items = items[skip : skip + limit]

        logger.info("tournaments_listed", count=len(paginated_items), total=total, filter=status_filter)
        return {"items": paginated_items, "total": total, "skip": skip, "limit": limit}

    except Exception as e:
        logger.exception("list_tournaments_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tournaments",
        )


@router.post("", response_model=TournamentResponse, status_code=status.HTTP_201_CREATED)
async def create_tournament(
    tournament_data: TournamentCreate,
    current_user: User = Depends(require_roles(["admin", "scorer"])),
    db: Session = Depends(get_db),
):
    """
    Create a new tournament.

    Story: US-2.1
    """
    try:
        if tournament_data.start_date >= tournament_data.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date",
            )

        tournament = Tournament(
            name=tournament_data.name,
            location=tournament_data.location or "",
            description=tournament_data.description,
            start_date=tournament_data.start_date,
            end_date=tournament_data.end_date,
            created_by_user_id=current_user.id,
        )

        db.add(tournament)
        db.commit()
        db.refresh(tournament)

        logger.info("tournament_created", tournament_id=tournament.id, created_by=current_user.id)
        return build_tournament_dict(tournament, db)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("create_tournament_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tournament",
        )


@router.get("/{tournament_id}", response_model=TournamentResponse)
async def get_tournament(tournament_id: int, db: Session = Depends(get_db)):
    """
    Get tournament by ID with full metrics and winner info.

    Story: US-2.1
    """
    try:
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()

        if not tournament:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tournament not found",
            )

        logger.info("tournament_retrieved", tournament_id=tournament_id)
        return build_tournament_dict(tournament, db)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_tournament_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tournament",
        )


@router.put("/{tournament_id}", response_model=TournamentResponse)
async def update_tournament(
    tournament_id: int,
    tournament_data: TournamentCreate,
    current_user: User = Depends(require_roles(["admin", "scorer"])),
    db: Session = Depends(get_db),
):
    """Update tournament details."""
    try:
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tournament:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tournament not found",
            )

        if tournament_data.start_date >= tournament_data.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date",
            )

        tournament.name = tournament_data.name
        tournament.location = tournament_data.location or ""
        tournament.description = tournament_data.description
        tournament.start_date = tournament_data.start_date
        tournament.end_date = tournament_data.end_date

        db.commit()
        db.refresh(tournament)

        logger.info("tournament_updated", tournament_id=tournament.id)
        return build_tournament_dict(tournament, db)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("update_tournament_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update tournament",
        )


@router.delete("/{tournament_id}", status_code=status.HTTP_200_OK)
async def delete_tournament(
    tournament_id: int,
    current_user: User = Depends(require_roles(["admin"])),
    db: Session = Depends(get_db),
):
    """Delete tournament and cascade-remove sessions and archers."""
    try:
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tournament:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tournament not found",
            )

        # Remove sessions
        sessions = db.query(TournamentSession).filter(TournamentSession.tournament_id == tournament_id).all()
        for s in sessions:
            db.delete(s)

        db.delete(tournament)
        db.commit()

        logger.info("tournament_deleted", tournament_id=tournament_id)
        return {"message": "Tournament deleted successfully", "id": tournament_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception("delete_tournament_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete tournament",
        )


@router.get("/{tournament_id}/stage-progression")
async def get_tournament_stage_progression(
    tournament_id: int,
    db: Session = Depends(get_db),
):
    """
    Get stage-by-stage progression, qualification cut-offs, and elimination status.
    """
    try:
        from src.services.report_service import ReportService
        return ReportService.get_stage_progression_analytics(db, tournament_id)
    except Exception as e:
        logger.exception("stage_progression_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate stage progression",
        )


@router.post("/{tournament_id}/advance-stage")
async def advance_tournament_stage(
    tournament_id: int,
    request: Dict[str, Any],
    current_user: User = Depends(require_roles(["admin", "scorer"])),
    db: Session = Depends(get_db),
):
    """
    Advance top qualifying archers from one session into the next elimination round.
    """
    try:
        from src.services.report_service import ReportService
        source_session_id = int(request.get("source_session_id", 0))
        target_session_id = int(request.get("target_session_id", 0))
        top_n = int(request.get("top_qualifiers_count", 4))
        clear_target = bool(request.get("clear_target", False))

        result = ReportService.advance_archers_to_stage(
            db=db,
            tournament_id=tournament_id,
            source_session_id=source_session_id,
            target_session_id=target_session_id,
            top_n=top_n,
            clear_target=clear_target,
        )
        return result
    except ValueError as ve:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        db.rollback()
        logger.exception("advance_stage_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to advance archers to next stage",
        )
