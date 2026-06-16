"""
FastAPI application factory and initialization.

Handles:
- FastAPI app creation and configuration
- Middleware setup (CORS, logging, rate limiting, error handling)
- Startup/shutdown events
- Health check endpoint
- Route inclusion
"""

from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor

import structlog
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from src.config import (
    settings,
    get_cors_origins,
    get_cors_allow_methods,
    get_cors_allow_headers,
)
from src.database import dispose_engine, verify_database_connectivity
from src.cache import cache_manager
from src.thread_pool import set_executor, shutdown_executor
from src.api import (
    auth_router,
    tournament_router,
    session_router,
    score_router,
    camera_router,
    leaderboard_router,
    report_router,
    health_router,
    user_router,
)
from src.api.websocket import router as websocket_router
from src.middleware import RateLimitMiddleware, ErrorHandlingMiddleware

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle (startup and shutdown).

    Startup:
    - Initialize database connections
    - Initialize thread pool for image processing
    - Initialize cache connections

    Shutdown:
    - Dispose database engine
    - Shutdown thread pool
    """
    # Startup
    logger.info("app_startup_starting")

    # Initialize thread pool for image processing (Pattern #10)
    executor = ThreadPoolExecutor(
        max_workers=settings.threadpool_base_workers,
        thread_name_prefix="archery-pool",
    )
    set_executor(executor)
    logger.info("thread_pool_initialized", workers=settings.threadpool_base_workers)

    # Verify cache connectivity
    cache_ok = cache_manager.ping()
    logger.info("cache_health", connected=cache_ok)

    # Verify database connectivity
    db_ok = verify_database_connectivity()
    logger.info("database_health", connected=db_ok)

    logger.info("app_startup_complete")

    yield

    # Shutdown
    logger.info("app_shutdown_starting")

    # Shutdown thread pool
    shutdown_executor()
    logger.info("thread_pool_shutdown")

    # Dispose database connections
    dispose_engine()
    logger.info("database_disposed")

    logger.info("app_shutdown_complete")


# Create FastAPI app with lifespan context
app = FastAPI(
    title=settings.api_title,
    version=settings.api_version,
    description="Real-time archery scoring and analysis system",
    lifespan=lifespan,
)

# Add CORS middleware (Pattern #20)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=get_cors_allow_methods(),
    allow_headers=get_cors_allow_headers(),
)

# Add rate limiting middleware (Pattern #17: Rate Limiting - Step 28)
app.add_middleware(RateLimitMiddleware)

# Add error handling middleware (Pattern #17: Error Handling - Step 26)
app.add_middleware(ErrorHandlingMiddleware)


# Structured logging middleware (Pattern #18)
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests and outgoing responses."""
    import time

    request_id = request.headers.get("x-request-id", "unknown")
    start_time = time.time()

    # Log incoming request
    logger.info(
        "request_received",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        client=request.client.host if request.client else "unknown",
    )

    response = await call_next(request)

    # Log outgoing response
    process_time = time.time() - start_time
    logger.info(
        "request_completed",
        request_id=request_id,
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=process_time * 1000,
    )

    return response


# Exception handlers
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle generic exceptions."""
    logger.exception("unhandled_exception", path=request.url.path, error=str(exc))

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": "Internal server error", "status": 500},
    )


# Include routers (Phase 4 - API Routes)
app.include_router(auth_router, prefix="/api", tags=["auth"])
app.include_router(tournament_router, prefix="/api", tags=["tournaments"])
app.include_router(session_router, prefix="/api", tags=["sessions"])
app.include_router(score_router, prefix="/api", tags=["scores"])
app.include_router(camera_router, prefix="/api", tags=["cameras"])
app.include_router(leaderboard_router, prefix="/api", tags=["leaderboards"])
app.include_router(report_router, prefix="/api", tags=["reports"])
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(user_router, prefix="/api", tags=["users"])
app.include_router(websocket_router, prefix="/api", tags=["websocket"])


# Root endpoint
@app.get("/", tags=["root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.api_title,
        "version": settings.api_version,
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        workers=settings.api_workers,
        reload=settings.environment == "development",
    )
