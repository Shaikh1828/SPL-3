"""
Report API routes.

Story coverage: US-4.1 (generate tournament reports in multiple formats)

Endpoints:
- POST /sessions/{session_id}/reports (format: pdf|csv|json)
- GET /reports/{report_id}
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session as SQLSession
import structlog
import io

from src.database import get_db
from src.dependencies import get_current_user
from src.models.user import User
from src.models.tournament import Session
from src.services.report_service import ReportService

logger = structlog.get_logger()

router = APIRouter(prefix="/sessions", tags=["reports"])


@router.post("/{session_id}/reports", status_code=status.HTTP_200_OK)
async def generate_report(
    session_id: int,
    format: str = Query("pdf", regex="^(pdf|csv|json)$"),
    current_user: User = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    """
    Generate a report for a session in specified format.

    Story: US-4.1

    Supports multiple export formats: PDF, CSV, JSON.

    Args:
        session_id: Session ID
        format: Report format (pdf, csv, json)
        current_user: Authenticated user
        db: Database session

    Returns:
        File download response

    Raises:
        HTTPException: 404 if session not found, 400 if format invalid
    """
    try:
        # Verify session exists
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Validate format
        if format.lower() not in ["pdf", "csv", "json"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid format. Supported: pdf, csv, json",
            )

        # Generate report
        report_bytes = ReportService.generate_report(db, session_id, format.lower())

        if not report_bytes:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to generate {format} report",
            )

        # Save report to storage
        report_path = ReportService.save_report(report_bytes, session_id, format.lower())

        # Determine media type
        media_types = {
            "pdf": "application/pdf",
            "csv": "text/csv",
            "json": "application/json",
        }

        media_type = media_types.get(format.lower(), "application/octet-stream")

        # Determine file extension
        extensions = {"pdf": ".pdf", "csv": ".csv", "json": ".json"}
        ext = extensions.get(format.lower(), "")

        # Return file as download
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


@router.get("/{session_id}/reports/{report_type}", status_code=status.HTTP_200_OK)
async def get_report(
    session_id: int,
    report_type: str,
    db: SQLSession = Depends(get_db),
):
    """
    Retrieve a previously generated report.

    Story: US-4.1

    Args:
        session_id: Session ID
        report_type: Type of report (pdf|csv|json)
        db: Database session

    Returns:
        File download response

    Raises:
        HTTPException: 404 if session or report not found
    """
    try:
        # Verify session exists
        session = db.query(Session).filter(Session.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )

        # Validate report type
        if report_type.lower() not in ["pdf", "csv", "json"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid report type. Supported: pdf, csv, json",
            )

        # Determine media type
        media_types = {
            "pdf": "application/pdf",
            "csv": "text/csv",
            "json": "application/json",
        }

        media_type = media_types.get(report_type.lower(), "application/octet-stream")

        logger.info("report_retrieved", session_id=session_id, report_type=report_type)

        # In production, would retrieve from storage service
        # This is a placeholder for the actual implementation

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
