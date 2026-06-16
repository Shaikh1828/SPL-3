"""
API routes initialization.
"""

from src.api.auth import router as auth_router
from src.api.tournaments import router as tournament_router
from src.api.sessions import router as session_router
from src.api.scores import router as score_router
from src.api.cameras import router as camera_router
from src.api.leaderboards import router as leaderboard_router
from src.api.reports import router as report_router
from src.api.health import router as health_router
from src.api.users import router as user_router

__all__ = [
    "auth_router",
    "tournament_router",
    "session_router",
    "score_router",
    "camera_router",
    "leaderboard_router",
    "report_router",
    "health_router",
    "user_router",
]

