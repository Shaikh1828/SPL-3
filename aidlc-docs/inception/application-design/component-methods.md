# Component Methods & Signatures

**Project**: Automated Archery Scoring System  
**Date**: 2026-05-23  
**Note**: Detailed business logic (validation rules, scoring algorithm) defined in Functional Design (per-unit, CONSTRUCTION phase)

---

## AuthService Methods

```python
class AuthService:
    def login(self, username: str, password: str) -> TokenResponse:
        """
        Authenticate user and generate JWT token.
        Returns: TokenResponse with access_token, token_type, expires_in
        Raises: AuthenticationError if credentials invalid
        """
        pass
    
    def logout(self, user_id: UUID) -> bool:
        """
        Invalidate user session.
        Returns: True if successful
        """
        pass
    
    def validate_token(self, token: str) -> TokenPayload:
        """
        Validate JWT token and extract claims.
        Returns: TokenPayload with user_id, roles, exp
        Raises: TokenInvalidError if token invalid/expired
        """
        pass
    
    def refresh_token(self, token: str) -> TokenResponse:
        """
        Refresh expired token.
        Returns: New TokenResponse with extended expiration
        Raises: TokenInvalidError if cannot refresh
        """
        pass
    
    def hash_password(self, password: str) -> str:
        """
        Hash password using bcrypt.
        Returns: Hashed password string
        """
        pass
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """
        Verify plain password against hash.
        Returns: True if password matches
        """
        pass
```

---

## UserRepository Methods

```python
class UserRepository:
    def find_by_username(self, username: str) -> Optional[User]:
        """Query user by username. Returns: User or None"""
        pass
    
    def find_by_id(self, user_id: UUID) -> Optional[User]:
        """Query user by ID. Returns: User or None"""
        pass
    
    def find_by_role(self, role: str) -> List[User]:
        """Query all users with specific role. Returns: List[User]"""
        pass
    
    def find_all(self) -> List[User]:
        """Query all users. Returns: List[User]"""
        pass
    
    def create_user(self, user_data: CreateUserRequest) -> User:
        """Create new user record. Returns: Created User"""
        pass
    
    def update_user(self, user_id: UUID, data: UpdateUserRequest) -> User:
        """Update user record. Returns: Updated User"""
        pass
    
    def delete_user(self, user_id: UUID) -> bool:
        """Delete user record. Returns: True if successful"""
        pass
```

---

## CameraManager Methods

```python
class CameraManager:
    def enumerate_usb_cameras(self) -> List[CameraInfo]:
        """
        Enumerate all USB cameras connected.
        Uses: cv2.VideoCapture on indices 0-9
        Returns: List[CameraInfo] with device info
        """
        pass
    
    def probe_camera(self, camera_id: UUID) -> CameraStatus:
        """
        Test camera connection.
        Returns: CameraStatus with connected/disconnected status
        """
        pass
    
    def start_auto_probe(self, interval_seconds: int) -> None:
        """
        Start background task to probe all cameras periodically.
        Publishes status changes via EventBus.
        """
        pass
    
    def publish_camera_status_change(self, camera_id: UUID, new_status: str) -> None:
        """Publish camera status change event to EventBus"""
        pass
```

---

## CameraRepository Methods

```python
class CameraRepository:
    def find_by_id(self, camera_id: UUID) -> Optional[Camera]:
        """Query camera by ID. Returns: Camera or None"""
        pass
    
    def find_all(self) -> List[Camera]:
        """Query all cameras. Returns: List[Camera]"""
        pass
    
    def find_by_status(self, status: str) -> List[Camera]:
        """Query cameras by status. Returns: List[Camera]"""
        pass
    
    def create_camera(self, camera_data: CreateCameraRequest) -> Camera:
        """Create new camera record. Returns: Created Camera"""
        pass
    
    def update_camera(self, camera_id: UUID, data: UpdateCameraRequest) -> Camera:
        """Update camera record. Returns: Updated Camera"""
        pass
    
    def delete_camera(self, camera_id: UUID) -> bool:
        """Delete camera record. Returns: True if successful"""
        pass
```

---

## CameraService Methods

```python
class CameraService:
    def get_available_cameras(self) -> List[Camera]:
        """
        Get all connected cameras.
        Returns: List[Camera] with status = CONNECTED
        """
        pass
    
    def configure_camera(self, camera_id: UUID, config: CameraConfig) -> Camera:
        """
        Configure camera settings (resolution, FPS, etc).
        Persists to database.
        Returns: Updated Camera
        """
        pass
    
    def test_camera_connection(self, camera_id: UUID) -> ConnectionTestResult:
        """
        Test camera connectivity.
        Returns: ConnectionTestResult with success/failure + diagnostics
        """
        pass
    
    def assign_camera_to_lane(self, session_id: UUID, lane_num: int, camera_id: UUID) -> LaneAssignment:
        """
        Bind camera to lane in session.
        Returns: LaneAssignment record
        """
        pass
```

---

## TournamentRepository Methods

```python
class TournamentRepository:
    def find_by_id(self, tournament_id: UUID) -> Optional[Tournament]:
        """Query tournament by ID. Returns: Tournament or None"""
        pass
    
    def find_all(self) -> List[Tournament]:
        """Query all tournaments. Returns: List[Tournament]"""
        pass
    
    def create_tournament(self, data: CreateTournamentRequest) -> Tournament:
        """Create new tournament. Returns: Created Tournament"""
        pass
    
    def update_tournament(self, tournament_id: UUID, data: UpdateTournamentRequest) -> Tournament:
        """Update tournament. Returns: Updated Tournament"""
        pass
```

---

## SessionRepository Methods

```python
class SessionRepository:
    def find_by_id(self, session_id: UUID) -> Optional[Session]:
        """Query session by ID. Returns: Session or None"""
        pass
    
    def find_by_tournament(self, tournament_id: UUID) -> List[Session]:
        """Query all sessions in tournament. Returns: List[Session]"""
        pass
    
    def find_by_status(self, status: str) -> List[Session]:
        """Query sessions by status. Returns: List[Session]"""
        pass
    
    def create_session(self, data: CreateSessionRequest) -> Session:
        """Create new session. Returns: Created Session"""
        pass
    
    def update_session(self, session_id: UUID, data: UpdateSessionRequest) -> Session:
        """Update session. Returns: Updated Session"""
        pass
```

---

## SessionManager Methods

```python
class SessionManager:
    def start_session(self, session_id: UUID) -> Session:
        """
        Transition session from pending to active.
        Validates cameras assigned.
        Publishes event via EventBus.
        Returns: Updated Session with status=ACTIVE
        Raises: ValidationError if cameras not assigned
        """
        pass
    
    def complete_session(self, session_id: UUID) -> Session:
        """
        Transition session from active to completed.
        Locks session for further scoring.
        Returns: Updated Session with status=COMPLETED
        """
        pass
    
    def get_session_state(self, session_id: UUID) -> SessionState:
        """
        Query current session state.
        Returns: SessionState with status, archers, scores
        """
        pass
```

---

## ArcherRepository Methods

```python
class ArcherRepository:
    def find_by_session(self, session_id: UUID) -> List[SessionArcher]:
        """Query all archers registered in session. Returns: List[SessionArcher]"""
        pass
    
    def add_archer_to_session(self, session_id: UUID, archer_data: AddArcherRequest) -> SessionArcher:
        """Register archer in session. Returns: Created SessionArcher"""
        pass
    
    def remove_archer_from_session(self, session_archer_id: UUID) -> bool:
        """Remove archer from session. Returns: True if successful"""
        pass
    
    def find_by_id(self, session_archer_id: UUID) -> Optional[SessionArcher]:
        """Query archer registration. Returns: SessionArcher or None"""
        pass
```

---

## ImageCaptureComponent Methods

```python
class ImageCaptureComponent:
    def capture_burst(self, camera_id: UUID) -> ImageBurst:
        """
        Capture burst of 3 frames from camera.
        Uses OpenCV cv2.VideoCapture.read().
        Returns: ImageBurst with 3 Image objects
        Raises: CameraError if camera not connected
        """
        pass
    
    def select_sharpest_frame(self, images: List[Image]) -> Image:
        """
        Select sharpest image from burst.
        Uses Laplacian variance metric.
        Returns: Image with highest sharpness score
        """
        pass
    
    def save_raw_image(self, image: Image, session_id: UUID, archer_id: UUID, end_num: int) -> str:
        """
        Save raw image to disk.
        Path: storage/raw/{session_id}/{archer_id}/{end_num}_raw.jpg
        Returns: Path to saved image
        """
        pass
```

---

## ImagePreprocessComponent Methods

```python
class ImagePreprocessComponent:
    def preprocess_image(self, image: Image) -> ProcessedImage:
        """
        Apply all preprocessing steps.
        Returns: ProcessedImage ready for detection
        """
        pass
    
    def normalize_lighting(self, image: Image) -> Image:
        """
        Normalize image lighting/contrast.
        Uses histogram equalization or similar.
        Returns: Image with normalized lighting
        """
        pass
    
    def apply_detection_filters(self, image: Image) -> Image:
        """
        Apply filters optimized for ring/arrow detection.
        Returns: Filtered Image
        """
        pass
```

---

## RingDetectionComponent Methods

```python
class RingDetectionComponent:
    def detect_rings(self, image: ProcessedImage) -> RingDetectionResult:
        """
        Detect target rings in image.
        Uses OpenCV contour detection or Hough circles.
        Returns: RingDetectionResult with ring boundaries and center
        Raises: DetectionError if no rings detected
        """
        pass
    
    def get_ring_boundaries(self) -> List[RingBoundary]:
        """
        Get pixel boundaries for each scoring zone (X, 10, 9, ..., 1).
        Returns: List[RingBoundary] with pixel radii
        """
        pass
    
    def pixel_to_zone(self, pixel_x: float, pixel_y: float) -> Union[int, str]:
        """
        Map pixel coordinates to scoring zone.
        Returns: Zone (X, 10, 9, ..., 1) or M for miss
        """
        pass
```

---

## ArrowDetectionComponent Methods

```python
class ArrowDetectionComponent:
    def detect_arrows(self, image: ProcessedImage, rings: RingDetectionResult) -> List[ArrowDetection]:
        """
        Detect individual arrows in image.
        Uses OpenCV contour/edge detection.
        Returns: List[ArrowDetection] with locations and confidence
        """
        pass
    
    def calculate_confidence(self, arrow_detection: ArrowDetection) -> float:
        """
        Calculate confidence score for arrow detection.
        Returns: Confidence 0.0-1.0 (0.6 threshold for flagging)
        """
        pass
```

---

## ScoringCalculatorComponent Methods

```python
class ScoringCalculatorComponent:
    def calculate_scores(self, arrow_detections: List[ArrowDetection]) -> ScoringResult:
        """
        Calculate final scores from arrow detections.
        Returns: ScoringResult with zones, scores, end total
        """
        pass
    
    def apply_scoring_rules(self, zone: Union[int, str]) -> int:
        """
        Apply WA standard scoring rules.
        X zone → 10 points (or 11 if applicable)
        Returns: Score points
        """
        pass
    
    def generate_confidence_summary(self, arrows: List[ArrowDetection]) -> ConfidenceSummary:
        """
        Summarize confidence across all arrows.
        Flags end if any arrow has confidence < 0.60.
        Returns: ConfidenceSummary
        """
        pass
```

---

## ScoringService Methods

```python
class ScoringService:
    def score_end(self, session_id: UUID, archer_id: UUID, end_num: int, camera_id: UUID) -> ScoringResult:
        """
        Orchestrate complete scoring pipeline for one end.
        Delegates to: ImageCapture → Preprocess → RingDetect → ArrowDetect → Calculate
        Uses thread pool for multi-camera parallelism.
        Returns: ScoringResult with zones, scores, confidence, image paths
        Raises: ScoringError if any stage fails
        Publishes: ScoreCalculated event to EventBus
        """
        pass
    
    def override_arrow_score(self, score_id: UUID, new_zone: Union[int, str], reason: str, note: Optional[str]) -> Score:
        """
        Override single arrow score.
        Updates Score.zone, marks is_overridden=True.
        Stores original_zone for audit.
        Returns: Updated Score
        Publishes: ScoreOverridden event to EventBus
        """
        pass
    
    def override_end_score(self, session_id: UUID, archer_id: UUID, end_num: int, zones: List[Union[int, str]]) -> List[Score]:
        """
        Override entire end (all 3 arrows).
        Creates override audit entries.
        Returns: List[Updated Score] for all 3 arrows
        Publishes: EndOverridden event to EventBus
        """
        pass
    
    def get_scoring_result(self, score_id: UUID) -> ScoringResult:
        """Query scoring result. Returns: ScoringResult"""
        pass
```

---

## ScoreRepository Methods

```python
class ScoreRepository:
    def find_by_id(self, score_id: UUID) -> Optional[Score]:
        """Query score by ID. Returns: Score or None"""
        pass
    
    def find_by_session_archer(self, session_id: UUID, archer_id: UUID) -> List[Score]:
        """Query all scores for archer in session. Returns: List[Score]"""
        pass
    
    def find_by_end(self, session_id: UUID, archer_id: UUID, end_number: int) -> List[Score]:
        """Query scores for specific end. Returns: List[Score] (3 arrows)"""
        pass
    
    def create_score(self, score_data: CreateScoreRequest) -> Score:
        """Create new score record. Returns: Created Score"""
        pass
    
    def update_score(self, score_id: UUID, data: UpdateScoreRequest) -> Score:
        """Update score record. Returns: Updated Score"""
        pass
    
    def bulk_create_scores(self, scores_data: List[CreateScoreRequest]) -> List[Score]:
        """Create multiple score records atomically. Returns: List[Score]"""
        pass
```

---

## ReportService Methods

```python
class ReportService:
    def generate_session_report(self, session_id: UUID, format: str) -> Report:
        """
        Generate session report in requested format.
        Delegates to: PDFGenerator | CSVGenerator | JSONGenerator.
        Returns: Report object with content + metadata
        Params: format in ['pdf', 'csv', 'json']
        """
        pass
    
    def generate_leaderboard(self, session_id: UUID) -> Leaderboard:
        """
        Generate leaderboard ranking.
        Queries all archer scores, calculates totals, ranks.
        Returns: Leaderboard with ranked archers
        """
        pass
    
    def get_archer_scores(self, session_id: UUID, archer_id: UUID) -> List[Score]:
        """Query all scores for archer in session. Returns: List[Score]"""
        pass
```

---

## Report Generator Methods

```python
class PDFReportGenerator:
    def generate_pdf(self, report_data: ReportData) -> bytes:
        """
        Generate PDF using WeasyPrint.
        Includes: score tables, charts, images.
        Returns: PDF bytes
        """
        pass
    
    def create_score_table(self, archer_scores: List) -> str:
        """Generate HTML table for scores. Returns: HTML string"""
        pass
    
    def render_images(self, images: List[str]) -> str:
        """Generate HTML image elements. Returns: HTML string"""
        pass

class CSVReportGenerator:
    def generate_csv(self, report_data: ReportData) -> str:
        """
        Generate CSV format.
        Returns: CSV string
        """
        pass

class JSONReportGenerator:
    def generate_json(self, report_data: ReportData) -> dict:
        """
        Generate JSON format.
        Returns: JSON-serializable dict
        """
        pass
```

---

## EventBus Methods

```python
class EventBus:
    def publish(self, event: DomainEvent) -> None:
        """
        Publish domain event.
        Routes to all subscribed handlers.
        Events: ScoreCalculated, ScoreOverridden, SessionStarted, CameraDisconnected, etc.
        """
        pass
    
    def subscribe(self, event_type: str, handler: Callable) -> Callable:
        """
        Subscribe to event type.
        Returns: Unsubscribe function
        """
        pass
```

---

## WebSocketConnectionManager Methods

```python
class WebSocketConnectionManager:
    def connect(self, websocket: WebSocket, connection_id: str) -> None:
        """Register new WebSocket connection"""
        pass
    
    def disconnect(self, connection_id: str) -> None:
        """Unregister WebSocket connection"""
        pass
    
    def broadcast(self, message: dict) -> None:
        """Send message to all connected clients"""
        pass
    
    def send_to(self, connection_id: str, message: dict) -> None:
        """Send message to specific client"""
        pass
```

---

## Permission Check Decorator Methods

```python
class PermissionCheckDecorator:
    def require_role(self, required_roles: List[str]) -> Callable:
        """
        FastAPI dependency decorator for role checking.
        Returns: Decorated function that checks role before executing handler
        Usage: @app.get("/admin"
        
        Depends(require_role([SYSTEM_ADMIN]))
        """
        pass
    
    def check_role(self, user: User, required_roles: List[str]) -> bool:
        """
        Check if user has required role.
        Returns: True if user.role in required_roles
        """
        pass
    
    def check_object_access(self, user: User, resource_type: str, resource_id: UUID) -> bool:
        """
        Check object-level permissions (e.g., archer can only see own data).
        Returns: True if user can access resource
        """
        pass
```

---

## CameraDisconnectHandler Methods

```python
class CameraDisconnectHandler:
    def on_camera_disconnect(self, camera_id: UUID) -> None:
        """
        Handle camera disconnection event.
        Updates camera status, publishes event to EventBus.
        """
        pass
    
    def attempt_reconnection(self, camera_id: UUID) -> bool:
        """
        Attempt to reconnect camera.
        Returns: True if reconnection successful
        """
        pass
```

---

## AuthorizationMiddleware Methods

```python
class AuthorizationMiddleware:
    def get_current_user(self) -> User:
        """
        Extract current user from request context (JWT token).
        FastAPI dependency.
        Returns: User object
        Raises: AuthenticationError if token invalid
        """
        pass
    
    def get_user_from_token(self, token: str) -> User:
        """
        Validate JWT token and return User.
        Returns: User object
        Raises: TokenInvalidError if invalid
        """
        pass
```

---

## Summary

Total method count: **~80 methods** across all components

Key characteristics:
- **Synchronous** responses (no async/await in signatures, but thread pool used internally for parallelism)
- **Exception-based** error handling (services throw domain exceptions)
- **Repository pattern** for data access (explicit data layer)
- **Event-driven** for WebSocket communication (EventBus publish/subscribe)
- **Role-based** permission checking (decorators and middleware)
- **Functional** service organization (~8 services)

