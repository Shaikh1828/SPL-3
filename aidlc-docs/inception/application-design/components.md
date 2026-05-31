# Application Components

**Project**: Automated Archery Scoring System  
**Architecture Style**: Feature-Based Organization with Layered Services  
**Date**: 2026-05-23  

---

## Component Overview

Components are organized by **feature area** with **functional services** orchestrating business logic. Each feature has:
- **Domain Models** — Data structures (ORM entities)
- **Repository** — Data access layer
- **Service** — Business logic orchestrator
- **API Handlers** — HTTP route handlers and WebSocket connections

---

## Core Domain Components

### 1. Authentication & User Management Feature

#### 1.1 User Domain Model
```
Component: User
Responsibilities:
  - Represent user identity and credentials
  - Store role information (SYSTEM_ADMIN, TOURNAMENT_ADMIN, SCORER, ARCHER)
  - Track user status (active, inactive)

Properties:
  - id: UUID
  - username: str (unique)
  - email: str (unique)
  - hashed_password: str
  - role: Enum(SYSTEM_ADMIN | TOURNAMENT_ADMIN | SCORER | ARCHER)
  - is_active: bool
  - created_at: datetime
  - last_login: datetime
```

#### 1.2 UserRepository
```
Component: UserRepository
Responsibilities:
  - Database access for User entities
  - Query users by username, email, role
  - Create, update, delete user records

Methods (defined in component-methods.md):
  - find_by_username(username: str) → Optional[User]
  - find_by_id(user_id: UUID) → Optional[User]
  - find_by_role(role: str) → List[User]
  - create_user(user_data: CreateUserRequest) → User
  - update_user(user_id: UUID, data: UpdateUserRequest) → User
  - delete_user(user_id: UUID) → bool
```

#### 1.3 AuthService
```
Component: AuthService
Responsibilities:
  - Handle user authentication (login/logout)
  - Generate and validate JWT tokens
  - Manage token expiration and refresh
  - Enforce 8-hour token lifetime
  - Store tokens in httpOnly cookies

Methods (defined in component-methods.md):
  - login(username: str, password: str) → TokenResponse
  - logout(user_id: UUID) → bool
  - validate_token(token: str) → TokenPayload
  - refresh_token(token: str) → TokenResponse
  - hash_password(password: str) → str
```

#### 1.4 User API Handlers (routes/auth.py)
```
Component: AuthHandlers
Responsibilities:
  - HTTP endpoints for authentication
  - Token management endpoints

Routes:
  - POST /api/v1/auth/login
  - POST /api/v1/auth/logout
  - POST /api/v1/auth/refresh
  - GET /api/v1/auth/me
```

---

### 2. Camera Management Feature

#### 2.1 Camera Domain Model
```
Component: Camera
Responsibilities:
  - Represent physical/virtual camera devices
  - Store camera configuration (resolution, FPS, type)
  - Track connection status and last update

Properties:
  - id: UUID
  - name: str
  - camera_type: Enum(USB | RTSP | HTTP_MJPEG)
  - status: Enum(CONNECTED | DISCONNECTED | RECONNECTING)
  - resolution: str (e.g., "1920x1080")
  - fps: int
  - url: Optional[str] (for RTSP/HTTP cameras)
  - last_updated: datetime
  - connected_at: Optional[datetime]
```

#### 2.2 CameraRepository
```
Component: CameraRepository
Responsibilities:
  - Database access for Camera entities
  - Query camera by ID, status, type

Methods (defined in component-methods.md):
  - find_by_id(camera_id: UUID) → Optional[Camera]
  - find_all() → List[Camera]
  - find_by_status(status: str) → List[Camera]
  - create_camera(camera_data: CreateCameraRequest) → Camera
  - update_camera(camera_id: UUID, data: UpdateCameraRequest) → Camera
  - delete_camera(camera_id: UUID) → bool
```

#### 2.3 CameraManager
```
Component: CameraManager
Responsibilities:
  - Enumerate USB and network cameras
  - Probe camera connectivity
  - Manage camera lifecycle (connect, disconnect, reconnect)
  - Track camera status in real-time
  - Publish camera status changes to WebSocket via EventBus

Methods (defined in component-methods.md):
  - enumerate_usb_cameras() → List[CameraInfo]
  - probe_camera(camera_id: UUID) → CameraStatus
  - start_auto_probe(interval_seconds: int) → None
  - publish_camera_status_change(camera_id: UUID, new_status: str) → None
```

#### 2.4 CameraService
```
Component: CameraService
Responsibilities:
  - High-level camera operations
  - Delegate to CameraManager for enumeration/probing
  - Delegate to CameraRepository for persistence
  - Coordinate camera assignment to lanes

Methods (defined in component-methods.md):
  - get_available_cameras() → List[Camera]
  - configure_camera(camera_id: UUID, config: CameraConfig) → Camera
  - test_camera_connection(camera_id: UUID) → ConnectionTestResult
  - assign_camera_to_lane(session_id: UUID, lane_num: int, camera_id: UUID) → LaneAssignment
```

#### 2.5 Camera API Handlers (routes/cameras.py)
```
Component: CameraHandlers
Responsibilities:
  - HTTP endpoints for camera operations

Routes:
  - GET /api/v1/cameras
  - GET /api/v1/cameras/{camera_id}
  - PUT /api/v1/cameras/{camera_id}
  - POST /api/v1/cameras/{camera_id}/test_connection
  - WS /ws/camera_preview/{camera_id}
```

---

### 3. Tournament & Session Management Feature

#### 3.1 Tournament Domain Model
```
Component: Tournament
Responsibilities:
  - Represent competitive event
  - Store tournament metadata

Properties:
  - id: UUID
  - name: str
  - date: date
  - location: str
  - target_type: str (e.g., "70m standard")
  - scoring_method: str (default: "WA standard")
  - max_archers: int
  - created_by: UUID (admin user)
  - created_at: datetime
```

#### 3.2 Session Domain Model
```
Component: Session
Responsibilities:
  - Represent single competition round
  - Store session configuration (end count, arrows per end)
  - Track session state (pending, active, completed)

Properties:
  - id: UUID
  - tournament_id: UUID
  - name: str
  - distance: int (meters)
  - end_count: int (e.g., 6)
  - arrows_per_end: int (e.g., 3)
  - target_face_cm: int (e.g., 80)
  - status: Enum(PENDING | ACTIVE | COMPLETED)
  - started_at: Optional[datetime]
  - completed_at: Optional[datetime]
```

#### 3.3 Archer Domain Model (Session Registration)
```
Component: SessionArcher
Responsibilities:
  - Link Archer to Session (many-to-many)
  - Store archer ranking within session

Properties:
  - id: UUID
  - session_id: UUID
  - archer_id: UUID (or archer_name if unregistered)
  - club: Optional[str]
  - division: Optional[str]
  - ranking: int (derived from scores)
```

#### 3.4 TournamentRepository, SessionRepository, ArcherRepository
```
Component: TournamentRepository
Methods (defined in component-methods.md):
  - find_by_id(tournament_id: UUID) → Optional[Tournament]
  - find_all() → List[Tournament]
  - create_tournament(data: CreateTournamentRequest) → Tournament
  - update_tournament(id: UUID, data: UpdateTournamentRequest) → Tournament

Component: SessionRepository
Methods (defined in component-methods.md):
  - find_by_id(session_id: UUID) → Optional[Session]
  - find_by_tournament(tournament_id: UUID) → List[Session]
  - create_session(data: CreateSessionRequest) → Session
  - update_session(id: UUID, data: UpdateSessionRequest) → Session

Component: ArcherRepository
Methods (defined in component-methods.md):
  - find_by_session(session_id: UUID) → List[SessionArcher]
  - add_archer_to_session(session_id: UUID, archer_data: AddArcherRequest) → SessionArcher
  - remove_archer_from_session(session_archer_id: UUID) → bool
```

#### 3.5 SessionManager
```
Component: SessionManager
Responsibilities:
  - Manage session lifecycle (create, start, complete)
  - Validate session state transitions
  - Database-backed session state (stored in Session.status)
  - Publish session state changes via EventBus

Methods (defined in component-methods.md):
  - start_session(session_id: UUID) → Session
  - complete_session(session_id: UUID) → Session
  - get_session_state(session_id: UUID) → SessionState
```

#### 3.6 Tournament & Session API Handlers (routes/tournaments.py, routes/sessions.py)
```
Component: TournamentHandlers
Routes:
  - POST /api/v1/tournaments
  - GET /api/v1/tournaments
  - GET /api/v1/tournaments/{tournament_id}
  - PUT /api/v1/tournaments/{tournament_id}

Component: SessionHandlers
Routes:
  - POST /api/v1/sessions
  - GET /api/v1/sessions/{session_id}
  - POST /api/v1/sessions/{session_id}/start
  - POST /api/v1/sessions/{session_id}/archers
  - GET /api/v1/sessions/{session_id}/archers
```

---

### 4. Scoring Feature

#### 4.1 Score Domain Model
```
Component: Score
Responsibilities:
  - Represent single arrow score record
  - Store zone, confidence, override information

Properties:
  - id: UUID
  - session_id: UUID
  - archer_id: UUID
  - end_number: int
  - arrow_number: int
  - zone: int or str (0-10, X, M)
  - confidence: float (0.0-1.0)
  - is_overridden: bool
  - original_zone: Optional[int or str] (if overridden)
  - override_reason: Optional[str]
  - override_note: Optional[str]
  - override_by: Optional[UUID] (scorer user)
  - created_at: datetime
  - updated_at: datetime
  - image_path: Optional[str] (path to stored image)
  - annotated_image_path: Optional[str] (path to annotated image)
```

#### 4.2 ScoreRepository
```
Component: ScoreRepository
Methods (defined in component-methods.md):
  - find_by_id(score_id: UUID) → Optional[Score]
  - find_by_session_archer(session_id: UUID, archer_id: UUID) → List[Score]
  - find_by_end(session_id: UUID, archer_id: UUID, end_number: int) → List[Score]
  - create_score(score_data: CreateScoreRequest) → Score
  - update_score(score_id: UUID, data: UpdateScoreRequest) → Score
```

#### 4.3 ImageCaptureComponent
```
Component: ImageCaptureComponent
Responsibilities:
  - Capture frames from camera
  - Implement burst mode (capture 3 frames, select sharpest)
  - Handle camera disconnections gracefully

Methods (defined in component-methods.md):
  - capture_burst(camera_id: UUID) → ImageBurst
  - select_sharpest_frame(images: List[Image]) → Image
  - save_raw_image(image: Image, session_id: UUID, archer_id: UUID, end_num: int) → str (path)
```

#### 4.4 ImagePreprocessComponent
```
Component: ImagePreprocessComponent
Responsibilities:
  - Preprocess captured image
  - Normalize resolution/lighting
  - Apply filters for detection

Methods (defined in component-methods.md):
  - preprocess_image(image: Image) → ProcessedImage
  - normalize_lighting(image: Image) → Image
  - apply_detection_filters(image: Image) → Image
```

#### 4.5 RingDetectionComponent
```
Component: RingDetectionComponent
Responsibilities:
  - Detect target rings in image
  - Identify ring boundaries
  - Map pixel coordinates to scoring zones

Methods (defined in component-methods.md):
  - detect_rings(image: ProcessedImage) → RingDetectionResult
  - get_ring_boundaries() → List[RingBoundary]
  - pixel_to_zone(pixel_x: float, pixel_y: float) → int or str (zone)
```

#### 4.6 ArrowDetectionComponent
```
Component: ArrowDetectionComponent
Responsibilities:
  - Detect individual arrows in image
  - Determine arrow location and zone
  - Calculate confidence for each detection

Methods (defined in component-methods.md):
  - detect_arrows(image: ProcessedImage, rings: RingDetectionResult) → List[ArrowDetection]
  - calculate_confidence(arrow_detection: ArrowDetection) → float
```

#### 4.7 ScoringCalculatorComponent
```
Component: ScoringCalculatorComponent
Responsibilities:
  - Calculate final score from zone information
  - Apply WA standard scoring rules
  - Generate confidence summary

Methods (defined in component-methods.md):
  - calculate_scores(arrow_detections: List[ArrowDetection]) → ScoringResult
  - apply_scoring_rules(zone: int or str) → int (score)
  - generate_confidence_summary(arrows: List[ArrowDetection]) → ConfidenceSummary
```

#### 4.8 ScoringService (Hybrid Orchestrator)
```
Component: ScoringService
Responsibilities:
  - Orchestrate entire scoring pipeline
  - Delegate to specialized components for each stage
  - Manage thread pool for parallel multi-camera processing
  - Publish scoring results via EventBus

Methods (defined in component-methods.md):
  - score_end(session_id: UUID, archer_id: UUID, end_num: int, camera_id: UUID) → ScoringResult
  - override_arrow_score(score_id: UUID, new_zone: int or str, reason: str, note: Optional[str]) → Score
  - override_end_score(session_id: UUID, archer_id: UUID, end_num: int, zones: List[int or str]) → List[Score]
  - get_scoring_result(score_id: UUID) → ScoringResult
```

#### 4.9 Scoring API Handlers (routes/scoring.py)
```
Component: ScoringHandlers
Routes:
  - POST /api/v1/scoring/calculate
  - GET /api/v1/scoring/results/{session_id}/{archer_id}
  - PUT /api/v1/scores/{score_id}/override
  - POST /api/v1/scores/{score_id}/confirm
```

---

### 5. Permissions & Authorization

#### 5.1 PermissionCheckDecorator
```
Component: PermissionCheckDecorator
Responsibilities:
  - FastAPI dependency for role-based access control
  - Check if user has required role
  - Used in route handlers to enforce permissions

Methods (defined in component-methods.md):
  - require_role(required_roles: List[str]) → Callable
  - check_role(user: User, required_roles: List[str]) → bool
  - check_object_access(user: User, resource_type: str, resource_id: UUID) → bool
```

#### 5.2 AuthorizationMiddleware
```
Component: AuthorizationMiddleware
Responsibilities:
  - Extract user from JWT token
  - Inject user into request context
  - Used by route handlers and services

Methods (defined in component-methods.md):
  - get_current_user() → User
  - get_user_from_token(token: str) → User
```

---

### 6. Reports & Leaderboard

#### 6.1 ReportDataModel
```
Component: ReportData
Responsibilities:
  - Aggregate score data for reports
  - Calculate statistics (avg, best, consistency)

Properties:
  - session_id: UUID
  - archer_scores: List[ArcherScoreData]
  - end_totals: List[int]
  - grand_total: int
  - statistics: ReportStatistics
```

#### 6.2 PDFReportGenerator
```
Component: PDFReportGenerator
Responsibilities:
  - Generate PDF reports using WeasyPrint
  - Include images, charts, tables

Methods (defined in component-methods.md):
  - generate_pdf(report_data: ReportData) → bytes
  - create_score_table(archer_scores: List) → Table
  - render_images(images: List[str]) → List[PDFImage]
```

#### 6.3 CSVReportGenerator
```
Component: CSVReportGenerator
Responsibilities:
  - Generate CSV reports

Methods (defined in component-methods.md):
  - generate_csv(report_data: ReportData) → str
```

#### 6.4 JSONReportGenerator
```
Component: JSONReportGenerator
Responsibilities:
  - Generate JSON reports

Methods (defined in component-methods.md):
  - generate_json(report_data: ReportData) → dict
```

#### 6.5 ReportService
```
Component: ReportService
Responsibilities:
  - Query scores for session
  - Delegate to specific report generators
  - Return report in requested format

Methods (defined in component-methods.md):
  - generate_session_report(session_id: UUID, format: str) → Report
  - generate_leaderboard(session_id: UUID) → Leaderboard
  - get_archer_scores(session_id: UUID, archer_id: UUID) → List[Score]
```

#### 6.6 Reports API Handlers (routes/reports.py)
```
Component: ReportHandlers
Routes:
  - GET /api/v1/sessions/{session_id}/reports
  - GET /api/v1/sessions/{session_id}/leaderboard
  - GET /api/v1/sessions/{session_id}/export/{format}
  - GET /api/v1/archers/{archer_id}/scores
```

---

### 7. Real-Time Features (WebSocket & Events)

#### 7.1 EventBus
```
Component: EventBus
Responsibilities:
  - Publish events from services
  - Manage event subscriptions
  - Route events to WebSocket handlers

Methods (defined in component-methods.md):
  - publish(event: DomainEvent) → None
  - subscribe(event_type: str, handler: Callable) → Unsubscribe
```

#### 7.2 WebSocketConnectionManager
```
Component: WebSocketConnectionManager
Responsibilities:
  - Manage active WebSocket connections
  - Route messages to subscribers
  - Handle connection/disconnection

Methods (defined in component-methods.md):
  - connect(websocket: WebSocket, connection_id: str) → None
  - disconnect(connection_id: str) → None
  - broadcast(message: dict) → None
  - send_to(connection_id: str, message: dict) → None
```

#### 7.3 WebSocketHandler (routes/websocket.py)
```
Component: WebSocketHandler
Responsibilities:
  - Accept WebSocket connections
  - Forward events from EventBus to connected clients

Routes:
  - WS /ws
  - WS /ws/camera_preview/{camera_id}
```

---

### 8. Error Recovery

#### 8.1 CameraDisconnectHandler
```
Component: CameraDisconnectHandler
Responsibilities:
  - Detect camera disconnections
  - Publish disconnection events
  - Trigger reconnection attempts

Methods (defined in component-methods.md):
  - on_camera_disconnect(camera_id: UUID) → None
  - attempt_reconnection(camera_id: UUID) → bool
```

---

### 9. Data Persistence

#### 9.1 Database (PostgreSQL)
```
Component: Database
Responsibilities:
  - Persist all domain models
  - Handle transactions
  - Connection pooling

Tables:
  - users
  - cameras
  - tournaments
  - sessions
  - session_archers
  - scores
  - audit_logs
```

#### 9.2 SessionFactory / ConnectionPool
```
Component: DatabaseSession
Responsibilities:
  - Manage database connections
  - Handle transaction lifecycle
```

---

## Summary of All Components

| Feature Area | Service | Components | Repositories |
|---|---|---|---|
| **Auth** | AuthService | User, AuthService, AuthHandlers | UserRepository |
| **Cameras** | CameraService | Camera, CameraManager, CameraService, CameraHandlers | CameraRepository |
| **Tournaments** | TournamentService | Tournament, SessionManager, TournamentHandlers | TournamentRepository, SessionRepository |
| **Sessions** | SessionService | Session, SessionArcher, SessionHandlers | SessionRepository, ArcherRepository |
| **Scoring** | ScoringService | Score, ImageCapture, ImagePreprocess, RingDetection, ArrowDetection, ScoringCalculator, ScoringService, ScoringHandlers | ScoreRepository |
| **Permissions** | AuthorizationService | PermissionCheckDecorator, AuthorizationMiddleware | — |
| **Reports** | ReportService | ReportData, PDFGenerator, CSVGenerator, JSONGenerator, ReportService, ReportHandlers | — |
| **Real-Time** | EventBus, WebSocketService | EventBus, WebSocketConnectionManager, WebSocketHandler | — |
| **Errors** | ErrorRecoveryService | CameraDisconnectHandler | — |

---

## Total Component Count

- **Domain Models**: 8 (User, Camera, Tournament, Session, SessionArcher, Score, ReportData)
- **Services**: 8 (AuthService, CameraService, TournamentService, SessionService, ScoringService, ReportService, EventBus, WebSocketService)
- **Repositories**: 5 (UserRepository, CameraRepository, TournamentRepository, SessionRepository, ArcherRepository, ScoreRepository)
- **API Handlers**: 6 (AuthHandlers, CameraHandlers, TournamentHandlers, SessionHandlers, ScoringHandlers, ReportHandlers)
- **Specialized Components**: 7 (ImageCapture, ImagePreprocess, RingDetection, ArrowDetection, ScoringCalculator, Report Generators, WebSocket)
- **Infrastructure**: Database, EventBus, ConnectionPool, AuthMiddleware, PermissionDecorator

**Total**: ~34 distinct components organized in feature-based structure

