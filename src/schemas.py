"""
Pydantic request/response schemas for API endpoints.
"""

from datetime import datetime
from typing import Optional, List
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
    location: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    start_date: datetime
    end_date: datetime


class TournamentResponse(BaseModel):
    """Tournament response."""

    id: int
    name: str
    location: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    created_by_user_id: Optional[int] = None
    created_at: Optional[datetime] = None
    status: Optional[str] = "ongoing"  # "ongoing", "completed", "upcoming"
    total_sessions: Optional[int] = 0
    active_sessions: Optional[int] = 0
    completed_sessions: Optional[int] = 0
    total_archers: Optional[int] = 0
    winner_name: Optional[str] = None
    winner_score: Optional[int] = None

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
    zone: int = Field(..., ge=0)
    points: int = Field(..., ge=0)
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
    method: Optional[str] = None
    annotated_image: Optional[str] = None

    class Config:
        from_attributes = True


class ScoreValidateRequest(BaseModel):
    """Validate score request."""

    validated: Optional[bool] = None
    validated_by_ai: Optional[bool] = None


class ScoreOverrideRequest(BaseModel):
    """Score override request by admin."""

    zone: int = Field(..., ge=0)
    points: int = Field(..., ge=0)
    reason: Optional[str] = Field(None, max_length=500)



class LeaderboardItem(BaseModel):
    """Leaderboard item."""

    rank: int
    archer_id: int
    archer_name: str
    total_score: int
    current_round: int
    session_archer_id: Optional[int] = None
    lane_number: Optional[int] = None
    arrows_recorded: int = 0
    tens_count: int = 0
    xs_count: int = 0
    average_score: float = 0.0
    session_name: Optional[str] = None
    recent_arrows: List[int] = []


class TournamentLeaderboardItem(BaseModel):
    """Tournament leaderboard item."""

    rank: int
    archer_id: int
    archer_name: str
    total_score: int
    current_round: int
    session_archer_id: Optional[int] = None
    lane_number: Optional[int] = None
    arrows_recorded: int = 0
    tens_count: int = 0
    xs_count: int = 0
    average_score: float = 0.0
    sessions_count: int = 1
    session_name: Optional[str] = None
    recent_arrows: List[int] = []



# Camera Schemas
class CameraCreate(BaseModel):
    """Register camera request."""

    name: str = Field(..., min_length=1, max_length=100)
    camera_type: str = Field(..., pattern="^(USB|RTSP|HTTP)$")
    url: str = Field(..., min_length=1, max_length=500)


class CameraUpdate(BaseModel):
    """Update camera details."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    camera_type: Optional[str] = Field(None, pattern="^(USB|RTSP|HTTP)$")
    url: Optional[str] = Field(None, min_length=1, max_length=500)
    lane: Optional[int] = Field(None, ge=1)


class CameraResponse(BaseModel):
    """Camera response."""

    id: int
    name: str
    camera_type: str
    url: str
    status: str
    lane: Optional[int] = None
    last_connected_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CameraAssignRequest(BaseModel):
    """Assign camera to lane request."""

    camera_id: int
    lane: int = Field(..., ge=1)


class CameraTestRequest(BaseModel):
    """Camera stream testing request."""

    url: str
    camera_type: str = "RTSP"


class CameraTestResponse(BaseModel):
    """Camera stream testing response."""

    connected: bool
    source: str
    message: str
    resolution: Optional[str] = None
    fps: Optional[float] = None


class CameraDiscoveryItem(BaseModel):
    """Auto-discovered camera device item."""

    device_index: int
    url: str
    camera_type: str
    name: str
    resolution: Optional[str] = None


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


class BatchDirectoryRequest(BaseModel):
    """Batch directory scoring request."""

    directory_path: str = Field(..., min_length=1)
    session_archer_id: int
    round: int = Field(..., ge=1)


# Report Schemas
class ReportGenerateRequest(BaseModel):
    """Generate report request."""

    format: str = Field(..., pattern="^(pdf|csv|json)$")


# Batch AI Round Scoring & Review Schemas
class DetectedArrow(BaseModel):
    """Detected arrow model in AI round scoring."""
    arrow_num: int
    points: int = Field(..., ge=0, le=10)
    zone: str = Field(..., max_length=10)
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    is_x: bool = False
    tip_x: Optional[float] = None
    tip_y: Optional[float] = None
    is_override: bool = False
    override_reason: Optional[str] = None


class LaneDetectionResult(BaseModel):
    """Detection result for a single shooting lane in a round."""
    lane_number: int
    session_archer_id: int
    archer_name: str
    camera_id: Optional[int] = None
    camera_name: Optional[str] = None
    camera_status: str = "connected"
    status: str = "detected"
    detected_arrows: List[DetectedArrow] = []
    end_total: int = 0
    avg_confidence: float = 0.95
    method: str = "yolo11_consensus"
    annotated_image: Optional[str] = None


class AIScoreRoundRequest(BaseModel):
    """Request to score all lanes in a round via AI."""
    round: int = Field(default=1, ge=1)
    simulated: bool = False


class AIScoreRoundResponse(BaseModel):
    """Response containing AI detections across all active lanes."""
    session_id: int
    round: int
    arrows_per_round: int
    lanes: List[LaneDetectionResult]


class LaneSubmission(BaseModel):
    """Scorer-reviewed arrow submissions for a single lane."""
    session_archer_id: int
    lane_number: int
    arrows: List[DetectedArrow]


class BatchConfirmRoundRequest(BaseModel):
    """Request to confirm and commit all lane scores for a round."""
    round: int = Field(..., ge=1)
    lane_submissions: List[LaneSubmission]


class BatchConfirmRoundResponse(BaseModel):
    """Response after confirming and submitting round scores."""
    session_id: int
    round: int
    scores_recorded_count: int
    next_round: int
    updated_archers: List[SessionArcherResponse]


# Analytics Schemas
class ZoneCount(BaseModel):
    """Zone count and percentage breakdown."""
    zone: str
    count: int
    percentage: float


class EndProgressionItem(BaseModel):
    """Average score progression per end."""
    end: int
    avg_score: float
    total_arrows: int


class LaneAccuracyItem(BaseModel):
    """Shooting accuracy per lane."""
    lane: int
    avg_score: float
    arrows_shot: int
    tens_rate: float


class AIMetrics(BaseModel):
    """Computer vision and validation telemetry."""
    total_arrows: int
    ai_validated_percent: float
    avg_confidence: float
    overridden_count: int


class TournamentAnalyticsResponse(BaseModel):
    """Comprehensive tournament / session analytics."""
    tournament_id: Optional[int] = None
    tournament_name: Optional[str] = None
    session_id: Optional[int] = None
    session_name: Optional[str] = None
    total_archers: int
    total_arrows_shot: int
    total_points_scored: int
    overall_average_arrow: float
    score_distribution: List[ZoneCount]
    end_progression: List[EndProgressionItem]
    lane_accuracy: List[LaneAccuracyItem]
    ai_metrics: AIMetrics


class ArcherTournamentHistory(BaseModel):
    """Single tournament record in an archer's longitudinal history."""
    tournament_id: int
    tournament_name: str
    location: Optional[str] = None
    sessions_count: int
    arrows_shot: int
    total_points: int
    average_arrow: float
    rank: int
    tens_count: int
    xs_count: int
    best_end_score: int


class ArcherLongitudinalAnalyticsResponse(BaseModel):
    """Longitudinal performance analytics for an archer across tournaments."""
    archer_id: int
    archer_name: str
    tournaments_participated: int
    total_career_points: int
    overall_arrow_average: float
    total_tens: int
    total_xs: int
    career_high_end: int
    consistency_index: float
    tournaments: List[ArcherTournamentHistory]
    score_distribution: List[ZoneCount]
    end_progression: List[EndProgressionItem]


class ArcherDirectoryItem(BaseModel):
    """Directory summary item for archer selection."""
    archer_id: int
    archer_name: str
    tournaments_count: int
    total_score: int
    average_arrow: float


class ScoreGalleryItem(BaseModel):
    """Single item in target image gallery."""
    id: int
    score_id: int
    session_id: int
    session_name: Optional[str] = None
    tournament_id: Optional[int] = None
    tournament_name: Optional[str] = None
    session_archer_id: int
    archer_id: Optional[int] = None
    archer_name: str
    lane_number: Optional[int] = 1
    round: int
    arrow_num: int
    zone: int
    points: int
    is_x: bool = False
    confidence: float = 0.95
    method: Optional[str] = None
    image_id: Optional[str] = None
    image_url: Optional[str] = None
    annotated_image_url: Optional[str] = None
    created_at: Optional[datetime] = None


class ScoreGalleryResponse(BaseModel):
    """Paginated target image gallery response."""
    items: List[ScoreGalleryItem]
    total: int
    skip: int
    limit: int


# Error Response
class ErrorResponse(BaseModel):
    """Error response."""

    error: str
    status: int
    timestamp: Optional[datetime]


# Model Training Schemas
class TrainingStartRequest(BaseModel):
    """Request to initiate YOLO model training."""
    epochs: int = Field(default=3, ge=1, le=100, description="Number of epochs to train")
    batch_size: int = Field(default=4, ge=1, le=64, description="Batch size")
    imgsz: int = Field(default=896, ge=320, le=1280, description="Image resolution")
    device: str = Field(default="cpu", description="Device (cpu or cuda/0)")
    resume: bool = Field(default=False, description="Resume from previous checkpoint")


class DatasetInfo(BaseModel):
    """Available dataset statistics and metadata."""
    name: str = "Archery Scoring Dataset"
    path: str = "Data"
    data_yaml: str = "Data/data.yaml"
    train_images: int = 0
    val_images: int = 0
    test_images: int = 0
    total_images: int = 0
    classes: List[str] = []
    status: str = "ready"


class TrainingLossMetrics(BaseModel):
    """Training loss components."""
    box_loss: Optional[float] = None
    cls_loss: Optional[float] = None
    dfl_loss: Optional[float] = None
    total_loss: Optional[float] = None


class TrainingEvaluationMetrics(BaseModel):
    """Validation and detection accuracy metrics."""
    precision: Optional[float] = None
    recall: Optional[float] = None
    map50: Optional[float] = None
    map50_95: Optional[float] = None


class TrainingStatusResponse(BaseModel):
    """Real-time training state and progress."""
    status: str = "idle"  # idle, running, completed, failed, stopped
    progress: float = 0.0
    current_epoch: int = 0
    total_epochs: int = 0
    start_time: Optional[str] = None
    elapsed_seconds: int = 0
    eta_seconds: Optional[int] = None
    loss: Optional[TrainingLossMetrics] = None
    metrics: Optional[TrainingEvaluationMetrics] = None
    dataset: Optional[DatasetInfo] = None
    best_weights: Optional[str] = None
    last_checkpoint: Optional[str] = None
    weights_exist: bool = False
    last_trained_at: Optional[str] = None
    logs: List[str] = []
    error: Optional[str] = None


class TrainingHistoryItem(BaseModel):
    """Single epoch performance record from results.csv."""
    epoch: int
    time_seconds: Optional[float] = None
    train_box_loss: Optional[float] = None
    train_cls_loss: Optional[float] = None
    train_dfl_loss: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    map50: Optional[float] = None
    map50_95: Optional[float] = None
    val_box_loss: Optional[float] = None
    val_cls_loss: Optional[float] = None
    val_dfl_loss: Optional[float] = None


class TrainingHistoryResponse(BaseModel):
    """Epoch progression history for graphs and visualization."""
    total_epochs: int
    items: List[TrainingHistoryItem]
    best_map50: Optional[float] = None
    best_epoch: Optional[int] = None
    weights_file: Optional[str] = None
    weights_size_bytes: Optional[int] = None
    weights_last_modified: Optional[str] = None
