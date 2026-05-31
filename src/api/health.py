"""
Health check API routes.

Story coverage: US-6.2 (database resilience and health monitoring)

Endpoints:
- GET /health
- GET /health/detailed
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as SQLSession
import structlog

from src.database import get_db
from src.services.health_service import HealthService

logger = structlog.get_logger()

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.

    Story: US-6.2

    Returns overall system status and timestamp.

    Returns:
        dict with status (ok|degraded|down) and timestamp
    """
    try:
        health_status = await HealthService.get_system_health()
        logger.info("health_check_requested", status=health_status.get("status"))
        return health_status

    except Exception as e:
        logger.exception("health_check_error", error=str(e))
        return {
            "status": "down",
            "message": "Health check failed",
            "error": str(e),
        }


@router.get("/health/detailed")
async def detailed_health_check(db: SQLSession = Depends(get_db)):
    """
    Detailed health check with component-level status.

    Story: US-6.2

    Returns detailed status for all system components:
    - Database connectivity and health
    - Cache (Redis) connectivity and health
    - Storage usage and quota
    - ThreadPool utilization

    Args:
        db: Database session

    Returns:
        dict with overall status and component details
    """
    try:
        health_status = await HealthService.get_system_health()

        # Add component details
        detailed_response = {
            "overall_status": health_status.get("status"),
            "timestamp": health_status.get("timestamp"),
            "components": health_status.get("components", {}),
        }

        logger.info(
            "detailed_health_check_requested",
            status=detailed_response["overall_status"],
        )

        return detailed_response

    except Exception as e:
        logger.exception("detailed_health_check_error", error=str(e))
        return {
            "overall_status": "down",
            "message": "Detailed health check failed",
            "error": str(e),
            "components": {},
        }
