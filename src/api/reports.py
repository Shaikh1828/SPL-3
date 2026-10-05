"""
Report and Analytics API routes.

Story coverage: US-4.1 (generate tournament and session reports in multiple formats, advanced scoring analytics, cross-tournament archer longitudinal tracking)

Endpoints:
- POST /sessions/{session_id}/reports (format: pdf|csv|json)
- GET /sessions/{session_id}/reports/{report_type}
- POST /tournaments/{tournament_id}/reports (format: pdf|csv|json)
- GET /reports/analytics (tournament_id, session_id)
- GET /reports/archers/directory
- GET /reports/archers/{archer_id}/analytics
"""

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session as SQLSession
import structlog
import io

from src.database import get_db
from src.dependencies import get_current_user
from src.models.user import User
from src.models.tournament import Session, Tournament
from src.services.report_service import ReportService
from src.schemas import (
    TournamentAnalyticsResponse,
    ArcherLongitudinalAnalyticsResponse,
    ArcherDirectoryItem,
)

logger = structlog.get_logger()

router = APIRouter(tags=["reports"])


@router.get("/reports/analytics", response_model=TournamentAnalyticsResponse, status_code=status.HTTP_200_OK)
async def get_analytics(
    tournament_id: Optional[int] = Query(None, description="Optional tournament ID filter"),
    session_id: Optional[int] = Query(None, description="Optional session ID filter"),
    db: SQLSession = Depends(get_db),
):
    """
    Get aggregated real-time scoring analytics for a tournament or session.
    Calculates score distributions, end progression, lane accuracy, and AI detection metrics.
    """
    try:
        data = ReportService.get_tournament_analytics(
            db, tournament_id=tournament_id, session_id=session_id
        )
        return data
    except Exception as e:
        logger.exception("get_analytics_error", tournament_id=tournament_id, session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute analytics",
        )


@router.get("/reports/archers/directory", response_model=List[ArcherDirectoryItem], status_code=status.HTTP_200_OK)
async def list_archers_directory(
    db: SQLSession = Depends(get_db),
):
    """
    List all archers with tournament counts and career summary statistics.
    """
    try:
        return ReportService.list_archers_directory(db)
    except Exception as e:
        logger.exception("list_archers_directory_error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list archers directory",
        )


@router.get("/reports/archers/{archer_id}/analytics", response_model=ArcherLongitudinalAnalyticsResponse, status_code=status.HTTP_200_OK)
async def get_archer_longitudinal_analytics(
    archer_id: int,
    archer_name: Optional[str] = Query(None, description="Optional name override/filter"),
    db: SQLSession = Depends(get_db),
):
    """
    Get cross-tournament longitudinal analytics for a specific archer.
    Tracks progression across multiple tournaments, career averages, best ends, and consistency index.
    """
    try:
        data = ReportService.get_archer_longitudinal_analytics(
            db, archer_id=archer_id, archer_name=archer_name
        )
        return data
    except Exception as e:
        logger.exception("get_archer_analytics_error", archer_id=archer_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to compute archer analytics",
        )


@router.post("/sessions/{session_id}/reports", status_code=status.HTTP_200_OK)
async def generate_report(
    session_id: int,
    format: str = Query("pdf", regex="^(pdf|csv|json)$"),
    current_user: User = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """
    Generate a report for a session in specified format (pdf, csv, json).
    """
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        if format.lower() not in ["pdf", "csv", "json"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid format. Supported: pdf, csv, json",
            )

        report_bytes = ReportService.generate_report(db, session_id, format.lower())

        if not report_bytes:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate {format} report",
            )

        media_types = {
            "pdf": "application/pdf",
            "csv": "text/csv",
            "json": "application/json",
        }
        media_type = media_types.get(format.lower(), "application/octet-stream")
        extensions = {"pdf": ".pdf", "csv": ".csv", "json": ".json"}
        ext = extensions.get(format.lower(), "")

        logger.info(
            "report_generated",
            session_id=session_id,
            format=format,
            size_bytes=len(report_bytes),
        )

        return StreamingResponse(
            io.BytesIO(report_bytes),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename=session_{session_id}_report{ext}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("generate_report_error", session_id=session_id, format=format, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate report",
        )


@router.post("/tournaments/{tournament_id}/reports", status_code=status.HTTP_200_OK)
async def generate_tournament_report(
    tournament_id: int,
    format: str = Query("pdf", regex="^(pdf|csv|json)$"),
    current_user: User = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """
    Generate a comprehensive tournament-wide report across all sessions.
    """
    try:
        tournament = db.query(Tournament).filter(Tournament.id == tournament_id).first()
        if not tournament:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Tournament not found",
            )

        if format.lower() not in ["pdf", "csv", "json"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid format. Supported: pdf, csv, json",
            )

        report_bytes = ReportService.generate_tournament_report(db, tournament_id, format.lower())

        if not report_bytes:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate tournament {format} report",
            )

        media_types = {
            "pdf": "application/pdf",
            "csv": "text/csv",
            "json": "application/json",
        }
        media_type = media_types.get(format.lower(), "application/octet-stream")
        extensions = {"pdf": ".pdf", "csv": ".csv", "json": ".json"}
        ext = extensions.get(format.lower(), "")

        logger.info(
            "tournament_report_generated",
            tournament_id=tournament_id,
            format=format,
            size_bytes=len(report_bytes),
        )

        return StreamingResponse(
            io.BytesIO(report_bytes),
            media_type=media_type,
            headers={"Content-Disposition": f"attachment; filename=tournament_{tournament_id}_report{ext}"},
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("generate_tournament_report_error", tournament_id=tournament_id, format=format, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate tournament report",
        )


@router.get("/sessions/{session_id}/reports/{report_type}", status_code=status.HTTP_200_OK)
async def get_report(
    session_id: int,
    report_type: str,
    db: SQLSession = Depends(get_db),
):
    """
    Retrieve a previously generated report.
    """
    try:
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        if report_type.lower() not in ["pdf", "csv", "json"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid report type. Supported: pdf, csv, json",
            )

        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Report retrieval implementation pending",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("get_report_error", session_id=session_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve report",
        )

