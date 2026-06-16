"""
Pydantic request/response schemas for API endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, EmailStr, validator


# Auth Schemas
class UserCreate(BaseModel):
    """User registration request."""

    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8)
    password_confirm: str = Field(..., min_length=8)

    @validator("password_confirm")
    def passwords_match(cls, v, values):
        if "password" in values and v != values["password"]:
            raise ValueError("Passwords do not match")
        return v


class UserResponse(BaseModel):
    """User response."""

    id: int
    username: str
    email: str
    role: str
    is_active: bool
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    """Login request."""

    username: str
    password: str


class LoginResponse(BaseModel):
    """Login response with tokens."""

    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int


class RefreshRequest(BaseModel):
    """Refresh token request."""

    refresh_token: str


class PasswordResetRequest(BaseModel):
    """Password reset request."""

    old_password: str
    new_password: str = Field(..., min_length=8)


# Tournament/Session Schemas
class TournamentCreate(BaseModel):
    """Create tournament request."""

    name: str = Field(..., max_length=200)
    location: str = Field(..., max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    start_date: datetime
    end_date: datetime


class TournamentResponse(BaseModel):
    """Tournament response."""

    id: int
    name: str
    location: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    created_by_user_id: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class SessionCreate(BaseModel):
    """Create session request."""

    name: str = Field(..., max_length=200)
    round_number: int = Field(..., ge=1)
    num_lanes: int = Field(default=6, ge=1, le=12)
    arrows_per_round: int = Field(default=6, ge=1, le=12)


class SessionResponse(BaseModel):
    """Session response."""

    id: int
    tournament_id: int
    name: str
    round_number: int
    num_lanes: int
    arrows_per_round: int
    status: str
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    created_at: Optional[datetime]
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


class SessionArcherResponse(BaseModel):
    """Session archer response."""

    id: int
    session_id: int
    archer_id: int
    archer_name: str
    lane_number: Optional[int]
    current_round: int
    total_score: int
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


# Scoring Schemas
class ScoreCreate(BaseModel):
    """Create score request."""

    session_archer_id: int
    round: int = Field(..., ge=1)
    arrow_num: int = Field(..., ge=1)
    zone: int = Field(..., ge=0, le=10)
    points: int = Field(..., ge=0, le=10)
    image_id: Optional[str] = None


class ScoreResponse(BaseModel):
    """Score response."""

    id: int
    session_id: int
    session_archer_id: int
    round: int
    arrow_num: int
    zone: int
    points: int
    image_id: Optional[str]
    confidence: Optional[float]
    validated_by_ai: bool
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class ScoreValidateRequest(BaseModel):
    """Validate score request."""

    validated_by_ai: bool


class LeaderboardItem(BaseModel):
    """Leaderboard item."""

    rank: int
    archer_id: int
    archer_name: str
    total_score: int
    current_round: int
    session_archer_id: int
    lane_number: Optional[int] = None
    arrows_recorded: int = 0



# Camera Schemas
class CameraCreate(BaseModel):
    """Register camera request."""

    name: str = Field(..., min_length=1, max_length=100)
    camera_type: str = Field(..., pattern="^(USB|RTSP|HTTP)$")
    url: str = Field(..., min_length=1, max_length=500)


class CameraResponse(BaseModel):
    """Camera response."""

    id: int
    name: str
    camera_type: str
    url: str
    status: str
    last_connected_at: Optional[datetime]
    created_at: Optional[datetime]

    class Config:
        from_attributes = True


class CameraAssignRequest(BaseModel):
    """Assign camera to lane request."""

    camera_id: int
    lane: int = Field(..., ge=1)


class CameraAssignmentResponse(BaseModel):
    """Camera assignment response."""

    id: int
    camera_id: int
    session_id: int
    lane: int
    assigned_at: Optional[datetime]

    class Config:
        from_attributes = True


# Image Detection Schemas
class ImageDetectionResponse(BaseModel):
    """Image detection response."""

    image_id: str
    zone: Optional[int]
    confidence: float
    method: str


# Report Schemas
class ReportGenerateRequest(BaseModel):
    """Generate report request."""

    format: str = Field(..., pattern="^(pdf|csv|json)$")


# Error Response
class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    status: int
    timestamp: Optional[datetime]
