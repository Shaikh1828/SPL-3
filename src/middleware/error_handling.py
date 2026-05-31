"""
Error handling middleware and exception utilities.

Pattern #17: Error Handling & Recovery

Provides centralized error handling for all exceptions.
"""

from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
import structlog
from typing import Callable

logger = structlog.get_logger()


class ErrorHandlingMiddleware:
    """
    Middleware for comprehensive error handling.

    Catches and formats exceptions with appropriate HTTP status codes.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            logger.exception("unhandled_middleware_exception", error=str(exc))


async def validation_error_handler(request: Request, exc: RequestValidationError):
    """
    Handle Pydantic validation errors.

    Returns 422 Unprocessable Entity with detailed error info.
    """
    logger.warning("validation_error", path=request.url.path, errors=exc.errors())

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "Validation error",
            "status": status.HTTP_422_UNPROCESSABLE_ENTITY,
            "details": exc.errors(),
        },
    )


async def database_error_handler(request: Request, exc: SQLAlchemyError):
    """
    Handle database/SQLAlchemy errors.

    Returns 500 Internal Server Error without exposing DB details.
    """
    logger.exception("database_error", path=request.url.path, error=str(exc))

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Database error",
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    )


async def generic_error_handler(request: Request, exc: Exception):
    """
    Handle generic/unexpected exceptions.

    Returns 500 Internal Server Error.
    """
    logger.exception("generic_error", path=request.url.path, error=str(exc))

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "status": status.HTTP_500_INTERNAL_SERVER_ERROR,
        },
    )


def create_error_response(status_code: int, error: str, details: dict = None) -> JSONResponse:
    """
    Create a standardized error response.

    Args:
        status_code: HTTP status code
        error: Error message
        details: Optional additional details

    Returns:
        JSONResponse with formatted error
    """
    response = {
        "error": error,
        "status": status_code,
    }

    if details:
        response["details"] = details

    return JSONResponse(status_code=status_code, content=response)
