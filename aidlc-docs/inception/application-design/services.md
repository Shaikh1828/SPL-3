# Service Layer Design

**Project**: Automated Archery Scoring System  
**Date**: 2026-05-23  
**Architecture**: Functional Services (8 core services)

---

## Service Layer Overview

The service layer consists of **~8 functional services** organized by feature area:

```
┌────────────────────────────────────────────────────────────────┐
│                        HTTP API Handlers                        │
│        (Authentication, Camera, Tournament, Session, etc.)      │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                        SERVICE LAYER                            │
│  ┌─────────────┐ ┌─────────────┐ ┌──────────────┐              │
│  │AuthService  │ │CameraService│ │ScoringService│    ...       │
│  │(JWT, Users) │ │(USB, RTSP)  │ │(CV Pipeline) │              │
│  └─────────────┘ └─────────────┘ └──────────────┘              │
│       ↓               ↓                  ↓                      │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                  REPOSITORY PATTERN (Data Access)               │
│  UserRepository, CameraRepository, ScoreRepository, ...         │
└────────────────────────────────────────────────────────────────┘
                              ↓
┌────────────────────────────────────────────────────────────────┐
│                  PostgreSQL Database                            │
└────────────────────────────────────────────────────────────────┘
```

---

## Core Services (8 Total)

### 1. AuthService

**Responsibility**: Handle user authentication, JWT tokens, session management

**Scope**:
- User login/logout
- Token generation (8-hour expiration)
- Token validation and refresh
- Password hashing/verification
- HttpOnly cookie management

**Methods**:
- `login(username, password) → TokenResponse`
- `validate_token(token) → TokenPayload`
- `refresh_token(token) → TokenResponse`
- `logout(user_id) → bool`

**Dependencies**:
- UserRepository (read/write users)
- AuthorizationMiddleware (token validation)

**Communication Pattern**:
- Synchronous (HTTP handler calls service, waits for response)
- Returns Token with 8-hour expiration

**Error Handling**:
- Throws `AuthenticationError` if credentials invalid
- Throws `TokenInvalidError` if token expired/invalid

**Threading**: Single-threaded; no parallelism needed

---

### 2. CameraService

**Responsibility**: Enumerate, configure, and manage cameras

**Scope**:
- USB camera discovery via OpenCV
- RTSP/HTTP camera configuration
- Camera connection testing
- Camera assignment to lanes
- Real-time status monitoring

**Methods**:
- `get_available_cameras() → List[Camera]`
- `configure_camera(camera_id, config) → Camera`
- `test_camera_connection(camera_id) → ConnectionTestResult`
- `assign_camera_to_lane(session_id, lane_num, camera_id) → LaneAssignment`

**Delegates To**:
- CameraManager (USB enumeration, auto-probe)
- CameraRepository (persistence)

**Dependencies**:
- CameraManager (device enumeration)
- CameraRepository (database access)
- EventBus (publish status changes)

**Communication Pattern**:
- Synchronous API calls
- Asynchronous background tasks (camera probing)
- Event-driven status broadcasts via WebSocket

**Error Handling**:
- Throws `CameraNotFoundError` if camera missing
- Throws `ConnectionError` if cannot connect

**Threading**:
- Auto-probe runs in background task (every 30 seconds)
- Camera operations are non-blocking

---

### 3. TournamentService

**Responsibility**: Create and manage tournaments

**Scope**:
- Create tournaments
- Update tournament settings
- List tournaments
- Query tournament details

**Methods**:
- `create_tournament(data) → Tournament`
- `update_tournament(id, data) → Tournament`
- `list_tournaments() → List[Tournament]`
- `get_tournament(id) → Tournament`

**Dependencies**:
- TournamentRepository (database access)
- AuthorizationMiddleware (permission check: TOURNAMENT_ADMIN only)

**Communication Pattern**:
- Synchronous HTTP calls
- Database persistence

**Error Handling**:
- Throws `TournamentNotFoundError`
- Throws `UnauthorizedError` if user not TOURNAMENT_ADMIN

**Threading**: Single-threaded

---

### 4. SessionService

**Responsibility**: Create, manage, and orchestrate tournament sessions

**Scope**:
- Create sessions
- Register archers in session
- Start/complete sessions
- Manage session state transitions
- Validate session readiness

**Methods**:
- `create_session(tournament_id, data) → Session`
- `add_archer_to_session(session_id, archer_data) → SessionArcher`
- `start_session(session_id) → Session` (delegates to SessionManager)
- `complete_session(session_id) → Session` (delegates to SessionManager)
- `get_session(session_id) → Session`
- `list_session_archers(session_id) → List[SessionArcher]`

**Delegates To**:
- SessionManager (state transitions, validation)

**Dependencies**:
- SessionRepository (persistence)
- ArcherRepository (archer registration)
- SessionManager (state machine)
- EventBus (publish session events)

**Communication Pattern**:
- Synchronous HTTP calls
- Event-driven status broadcasts

**Error Handling**:
- Throws `SessionNotFoundError`
- Throws `ValidationError` if start session without cameras

**Threading**: Single-threaded

---

### 5. ScoringService

**Responsibility**: Orchestrate image processing pipeline and score calculations

**Scope**:
- Capture images from camera (burst mode)
- Preprocess images
- Detect target rings
- Detect arrows
- Calculate scores
- Manage score overrides
- Publish results via WebSocket

**Key Characteristics**:
- **Thread Pool**: Uses ThreadPoolExecutor for multi-camera parallelism
- **Synchronous HTTP Response**: Caller waits for complete result (200-1000ms)
- **Component Orchestration**: Coordinates specialized components

**Methods**:
- `score_end(session_id, archer_id, end_num, camera_id) → ScoringResult` (main entry point)
- `override_arrow_score(score_id, new_zone, reason) → Score`
- `override_end_score(session_id, archer_id, end_num, zones) → List[Score]`
- `get_scoring_result(score_id) → ScoringResult`

**Delegates To**:
- ImageCaptureComponent (camera capture)
- ImagePreprocessComponent (image preprocessing)
- RingDetectionComponent (ring detection)
- ArrowDetectionComponent (arrow detection)
- ScoringCalculatorComponent (score calculation)

**Dependencies**:
- All image processing components
- ScoreRepository (persistence)
- EventBus (publish scoring results)

**Communication Pattern**:
- Synchronous request/response (UI shows loading spinner)
- Thread pool handles parallelism internally
- WebSocket broadcasts results to all clients

**Error Handling**:
- Throws `ScoringError` if any stage fails
- Throws `CameraError` if camera not connected
- Throws `DetectionError` if rings not detected

**Threading**:
- Uses ThreadPoolExecutor to process multiple cameras concurrently
- max_workers = 4 (supports 4+ simultaneous cameras)
- Each camera scoring runs in separate thread

**Performance Targets**:
- Complete scoring within 1 second
- Breakdown: Capture 200ms + Preprocess 300ms + Ring Detect 200ms + Arrow Detect 150ms + Score Calc 50ms

---

### 6. ReportService

**Responsibility**: Generate reports in multiple formats

**Scope**:
- Query session scores and statistics
- Generate reports (PDF, CSV, JSON)
- Generate leaderboards and rankings
- Export data for analysis

**Methods**:
- `generate_session_report(session_id, format) → Report`
- `generate_leaderboard(session_id) → Leaderboard`
- `get_archer_scores(session_id, archer_id) → List[Score]`

**Delegates To**:
- PDFReportGenerator (PDF generation)
- CSVReportGenerator (CSV generation)
- JSONReportGenerator (JSON generation)

**Dependencies**:
- ScoreRepository (query scores)
- Report Generators (format-specific output)
- AuthorizationMiddleware (permission check)

**Communication Pattern**:
- Synchronous HTTP requests
- Returns file content or data structure

**Error Handling**:
- Throws `SessionNotFoundError`
- Throws `UnauthorizedError` if archer tries to view other's data

**Threading**: Single-threaded

---

### 7. EventBus (Service + Infrastructure)

**Responsibility**: Publish and subscribe to domain events

**Scope**:
- Publish events from other services (ScoreCalculated, SessionStarted, etc.)
- Route events to WebSocket connections
- Manage event subscriptions
- Enable loose coupling between services

**Methods**:
- `publish(event: DomainEvent) → None`
- `subscribe(event_type: str, handler: Callable) → Unsubscribe`

**Events Published**:
- `ScoreCalculated(session_id, archer_id, end_num, zones, confidence)`
- `ScoreOverridden(score_id, old_zone, new_zone, reason)`
- `SessionStarted(session_id)`
- `SessionCompleted(session_id)`
- `CameraConnected(camera_id)`
- `CameraDisconnected(camera_id)`
- `CameraStatusChanged(camera_id, new_status)`

**Subscribers**:
- WebSocketConnectionManager (receives events, broadcasts to clients)
- CameraDisconnectHandler (listens to CameraDisconnected event)

**Communication Pattern**:
- Event-driven (fire-and-forget)
- Asynchronous from caller's perspective
- Synchronous delivery to subscribers (in-process)

**Threading**: In-process event bus; no multi-threaded complexity

**Error Handling**:
- Silently ignores exceptions in subscribers (prevents one subscriber from blocking others)

---

### 8. WebSocketService (WebSocket + Real-Time)

**Responsibility**: Manage WebSocket connections and broadcast real-time updates

**Scope**:
- Accept WebSocket connections from clients
- Maintain connection registry
- Broadcast messages from EventBus to connected clients
- Route camera preview streams
- Handle disconnections gracefully

**Components**:
- WebSocketConnectionManager (connection registry)
- WebSocketHandler (FastAPI WebSocket route)

**Methods**:
- `connect(websocket, connection_id) → None`
- `disconnect(connection_id) → None`
- `broadcast(message) → None`
- `send_to(connection_id, message) → None`

**Connections**:
- `WS /ws` — Main connection for score broadcasts
- `WS /ws/camera_preview/{camera_id}` — Camera preview streams

**Communication Pattern**:
- Event-driven (listens to EventBus)
- Push-based for score broadcasts (< 100ms delivery)
- Hybrid for camera preview (push + pull on-demand)

**Error Handling**:
- Gracefully handles client disconnections
- Automatically removes disconnected connections from registry

**Threading**: Async (uses asyncio for WebSocket handling)

---

## Service Interaction Patterns

### Scenario 1: User Logs In
```
HTTP POST /api/v1/auth/login
  ↓
AuthHandlers.login()
  ↓
AuthService.login()
  ├─ UserRepository.find_by_username()
  ├─ AuthService.verify_password()
  └─ AuthService.hash_token()
  ↓
HTTP Response: TokenResponse (200 OK)
```

### Scenario 2: Scorer Triggers Scoring
```
HTTP POST /api/v1/scoring/calculate
  ↓
PermissionCheckDecorator.require_role(SCORER)
  ↓
ScoringHandlers.score_end()
  ↓
ScoringService.score_end()
  ├─ ThreadPool[0]: ImageCaptureComponent.capture_burst()
  ├─ ThreadPool[0]: ImagePreprocessComponent.preprocess_image()
  ├─ ThreadPool[0]: RingDetectionComponent.detect_rings()
  ├─ ThreadPool[0]: ArrowDetectionComponent.detect_arrows()
  ├─ ThreadPool[0]: ScoringCalculatorComponent.calculate_scores()
  ├─ ScoreRepository.bulk_create_scores()
  └─ EventBus.publish(ScoreCalculated)
  ↓
EventBus → WebSocketService
  ↓
WebSocketConnectionManager.broadcast(score_update)
  ↓
All connected clients receive update (< 100ms)
  ↓
HTTP Response: ScoringResult (200 OK) after ~500-1000ms
```

### Scenario 3: Camera Disconnects (Background)
```
CameraManager.start_auto_probe() [Background Task]
  ↓
Detects: camera_id no longer responds
  ↓
CameraManager.publish_camera_status_change()
  ↓
EventBus.publish(CameraDisconnected)
  ↓
CameraDisconnectHandler.on_camera_disconnect()
  ├─ CameraRepository.update_camera(status=DISCONNECTED)
  └─ CameraDisconnectHandler.attempt_reconnection() [retry after 30s]
  ↓
EventBus → WebSocketService
  ↓
WebSocketConnectionManager.broadcast(camera_status_update)
  ↓
All clients receive status update
```

---

## Service Dependencies Summary

| Service | Depends On | Publishes | Listens To |
|---|---|---|---|
| **AuthService** | UserRepository | — | — |
| **CameraService** | CameraManager, CameraRepository, EventBus | CameraStatusChanged | — |
| **TournamentService** | TournamentRepository | — | — |
| **SessionService** | SessionRepository, ArcherRepository, SessionManager, EventBus | SessionStarted, SessionCompleted | — |
| **ScoringService** | All Image Processors, ScoreRepository, EventBus | ScoreCalculated, ScoreOverridden | — |
| **ReportService** | ScoreRepository, Report Generators | — | — |
| **EventBus** | — | All events | — |
| **WebSocketService** | WebSocketConnectionManager, EventBus | — | All events |

---

## Cross-Service Communication

### Synchronous (Request/Response)
- AuthService → UserRepository
- CameraService → CameraRepository
- ScoringService → ScoreRepository
- ReportService → ScoreRepository

### Asynchronous (Event-Driven)
- ScoringService → EventBus (ScoreCalculated)
- CameraService → EventBus (CameraStatusChanged)
- SessionService → EventBus (SessionStarted)
- EventBus → WebSocketService (all events)

### Parallelism
- ScoringService uses ThreadPool (4 workers max) for multi-camera scoring

---

## Error Handling Strategy

**Service Layer Throws Domain Exceptions**:
- `AuthenticationError` — Invalid credentials
- `TokenInvalidError` — Invalid/expired token
- `CameraError` — Camera not connected
- `DetectionError` — Ring detection failed
- `ScoringError` — Scoring pipeline failed
- `ValidationError` — Business rule violated
- `UnauthorizedError` — User lacks permission

**Handler Layer Catches and Converts to HTTP**:
- `try: service_method() except AuthenticationError: return 401`
- `try: service_method() except UnauthorizedError: return 403`
- `try: service_method() except ScoringError: return 400`

**WebSocket Handles Gracefully**:
- Silently handles client disconnections
- Continues broadcasting to remaining clients

---

## Service Lifecycle

### Startup
1. Initialize repositories and database connections
2. Start CameraManager (begin auto-probe in background)
3. Subscribe EventBus handlers to WebSocket

### Runtime
- Services receive HTTP requests and route to handlers
- Services delegate to repositories and specialized components
- Services publish events; EventBus routes to WebSocket
- Background tasks (camera probing) run independently

### Shutdown
- Gracefully close database connections
- Stop background tasks (camera probing)
- Disconnect all WebSocket clients

