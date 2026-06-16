"""
Tournament API routes.

Story coverage: US-2.1 (create tournament and session)
Endpoints:
- GET /tournaments
- POST /tournaments
- GET /tournaments/{tournament_id}
"""

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
import structlog

from src.database import get_db
from src.schemas import TournamentCreate, TournamentResponse
from src.dependencies import get_current_user, require_role
from src.models.user import User
from src.models.tournament import Tournament

logger = structlog.get_logger()

router = APIRouter(prefix="/tournaments", tags=["tournaments"])


@router.get("", response_model=Dict[str, Any])
async def list_tournaments(
    db: Session = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = None,
):
    """
    List all tournaments with pagination.

    Story: US-2.1

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum records to return
        search: Optional search by name

    Returns:
        List of tournaments
    """
    try:
        query = db.query(Tournament)

        if search:
            query = query.filter(Tournament.name.contains(search))

        total = query.count()
        tournaments = query.order_by(Tournament.created_at.desc()).offset(skip).limit(limit).all()

        # Serialize manually to get list of dicts
        items = [TournamentResponse.model_validate(t).model_dump() for t in tournaments]

        logger.info("tournaments_listed", count=len(items))
        return {"items": items, "total": total, "skip": skip, "limit": limit}

    except Exception as e:
        logger.exception("list_tournaments_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list tournaments",
        )


@router.post("", response_model=TournamentResponse, status_code=status.HTTP_201_CREATED)
async def create_tournament(
    tournament_data: TournamentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Create a new tournament.

    Story: US-2.1

    Requires authentication.

    Args:
        tournament_data: Tournament details
        current_user: Authenticated user
        db: Database session

    Returns:
        Created tournament

    Raises:
        HTTPException: 400 if validation fails
    """
    try:
        if tournament_data.start_date >= tournament_data.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Start date must be before end date",
            )

        tournament = Tournament(
            name=tournament_data.name,
            location=tournament_data.location,
            start_date=tournament_data.start_date,
            end_date=tournament_data.end_date,
            created_by_user_id=current_user.id,
        )

        db.add(tournament)
        db.commit()
        db.refresh(tournament)

        logger.info("tournament_created", tournament_id=tournament.id, created_by=current_user.id)
        return tournament

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
    Get tournament by ID.

    Story: US-2.1

    Args:
        tournament_id: Tournament ID
        db: Database session

    Returns:
        Tournament object

    Raises:
        HTTPException: 404 if tournament not found
    """
    try:
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()

        if not tournament:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tournament not found",
            )

        logger.info("tournament_retrieved", tournament_id=tournament_id)
        return tournament

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_tournament_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve tournament",
        )
