# Component Dependencies & Communication

**Project**: Automated Archery Scoring System  
**Date**: 2026-05-23  

---

## Component Dependency Matrix

| Component | Depends On | Purpose | Communication |
|---|---|---|---|
| **AuthHandlers** | AuthService, AuthorizationMiddleware | HTTP authentication routes | Sync |
| **AuthService** | UserRepository | JWT token management | Sync |
| **UserRepository** | Database (PostgreSQL) | User data access | Sync |
| **CameraHandlers** | CameraService, PermissionCheckDecorator | HTTP camera routes | Sync |
| **CameraService** | CameraManager, CameraRepository, EventBus | Camera orchestration | Sync + Event |
| **CameraManager** | CameraRepository, EventBus | USB/RTSP enumeration | Sync + Event |
| **CameraRepository** | Database | Camera data access | Sync |
| **TournamentHandlers** | TournamentService, PermissionCheckDecorator | HTTP tournament routes | Sync |
| **TournamentService** | TournamentRepository | Tournament orchestration | Sync |
| **TournamentRepository** | Database | Tournament data access | Sync |
| **SessionHandlers** | SessionService, PermissionCheckDecorator | HTTP session routes | Sync |
| **SessionService** | SessionRepository, ArcherRepository, SessionManager, EventBus | Session orchestration | Sync + Event |
| **SessionManager** | SessionRepository, EventBus | Session state machine | Sync + Event |
| **SessionRepository** | Database | Session data access | Sync |
| **ArcherRepository** | Database | Archer registration access | Sync |
| **ScoringHandlers** | ScoringService, PermissionCheckDecorator | HTTP scoring routes | Sync |
| **ScoringService** | ImageCapture, ImagePreprocess, RingDetection, ArrowDetection, ScoringCalculator, ScoreRepository, EventBus | Scoring orchestration | Sync + Event + ThreadPool |
| **ImageCaptureComponent** | OpenCV (camera device) | Camera frame capture | Sync |
| **ImagePreprocessComponent** | OpenCV | Image preprocessing | Sync |
| **RingDetectionComponent** | OpenCV | Ring detection | Sync |
| **ArrowDetectionComponent** | OpenCV | Arrow detection | Sync |
| **ScoringCalculatorComponent** | None | Score calculation | Sync |
| **ScoreRepository** | Database | Score data access | Sync |
| **ReportHandlers** | ReportService, PermissionCheckDecorator | HTTP report routes | Sync |
| **ReportService** | ScoreRepository, PDFGenerator, CSVGenerator, JSONGenerator | Report generation | Sync |
| **PDFReportGenerator** | WeasyPrint | PDF rendering | Sync |
| **CSVReportGenerator** | None | CSV formatting | Sync |
| **JSONReportGenerator** | None | JSON serialization | Sync |
| **PermissionCheckDecorator** | AuthorizationMiddleware, Database (roles) | Permission enforcement | Sync |
| **AuthorizationMiddleware** | AuthService | Token validation | Sync |
| **EventBus** | None | Event routing | Event |
| **WebSocketHandler** | WebSocketConnectionManager, EventBus | WebSocket routes | Async + Event |
| **WebSocketConnectionManager** | EventBus | Connection registry | Event |
| **CameraDisconnectHandler** | CameraRepository, CameraManager | Camera disconnect recovery | Event + Sync |

---

## Dependency Graph (Visual)

```
┌─────────────────────────────────────────────────────────────┐
│                      HTTP Handlers Layer                     │
│  ┌──────────────┐ ┌─────────────┐ ┌──────────────┐          │
│  │AuthHandlers  │ │CameraHandler│ │ScoringHandler│  ...     │
│  └──────────────┘ └─────────────┘ └──────────────┘          │
└─────────────────────────────────────────────────────────────┘
         │                │                │
         ↓                ↓                ↓
┌─────────────────────────────────────────────────────────────┐
│                      Services Layer                          │
│  ┌──────────────┐ ┌─────────────┐ ┌──────────────┐          │
│  │AuthService   │ │CameraService│ │ScoringService│  ...     │
│  └──────────────┘ └─────────────┘ └──────────────┘          │
└─────────────────────────────────────────────────────────────┘
         │                │                │
         ↓                ↓                ↓
┌─────────────────────────────────────────────────────────────┐
│            Specialized Components / Managers                 │
│  ┌──────────────┐ ┌─────────────┐ ┌──────────────┐          │
│  │UserRepository│ │CameraManager│ │ImageCapture  │  ...     │
│  └──────────────┘ └─────────────┘ └──────────────┘          │
└─────────────────────────────────────────────────────────────┘
         │                │                │
         ↓                ↓                ↓
┌─────────────────────────────────────────────────────────────┐
│                    Database / External                       │
│                    PostgreSQL, OpenCV                        │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│              Cross-Component Communication                   │
│  ┌──────────────┐  ┌─────────────────┐  ┌───────────────┐  │
│  │  EventBus    │  │WebSocketService │  │PermissionChk  │  │
│  │(Event-Driven)│  │  (WebSocket)    │  │  (Decorator)  │  │
│  └──────────────┘  └─────────────────┘  └───────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

---

## Communication Patterns

### Pattern 1: Synchronous Request/Response (Most Common)

```
Handler
  ↓
Service.method()
  ↓
Repository.query()
  ↓
Database
  ↓
Repository returns data
  ↓
Service processes
  ↓
Handler returns HTTP response
```

**Examples**:
- Authentication: AuthHandlers → AuthService → UserRepository
- Camera config: CameraHandlers → CameraService → CameraRepository
- Session setup: SessionHandlers → SessionService → SessionRepository
- Reporting: ReportHandlers → ReportService → ScoreRepository

**Latency**: < 100ms (query time)

---

### Pattern 2: Synchronous with Event Publication

```
Handler
  ↓
Service.method()
  ├─ Repository operations (database writes)
  └─ EventBus.publish(event)
       ↓
       WebSocketService (subscribes)
         ↓
         WebSocketConnectionManager.broadcast()
           ↓
           All connected clients receive update
  ↓
Handler returns HTTP response (before clients get update, typically)
```

**Examples**:
- Scoring: ScoringService publishes `ScoreCalculated` event
- Session start: SessionService publishes `SessionStarted` event
- Camera status: CameraManager publishes `CameraStatusChanged` event

**Latency**:
- HTTP response: 200-1000ms (scoring pipeline)
- WebSocket broadcast: < 100ms after database commit

---

### Pattern 3: Background Task (Async)

```
CameraManager.start_auto_probe() [Background]
  ↓
Runs every 30 seconds
  ↓
Probes all cameras
  ↓
Detects status changes
  ↓
EventBus.publish(CameraDisconnected)
  ↓
CameraDisconnectHandler listens
  ├─ CameraRepository.update_camera()
  └─ EventBus.publish(CameraStatusChanged)
  ↓
WebSocketService receives event
  ↓
Broadcasts to all clients
```

**Latency**: 30-60 seconds for detection; < 100ms for broadcast

---

### Pattern 4: Event-Driven (Loosely Coupled)

```
Service A publishes event
  ↓
EventBus.publish(event)
  ↓
All subscribers notified
  ↓
Handler 1: process event
Handler 2: process event
Handler 3: process event
(all run concurrently; failures don't affect others)
```

**Subscribers**:
- WebSocketService (broadcasts to clients)
- CameraDisconnectHandler (handles disconnects)
- AuditLogger (logs events)

**Latency**: In-process; < 1ms

---

### Pattern 5: Parallelism (Thread Pool)

```
ScoringService.score_end()
  ↓
ThreadPoolExecutor.submit() [max_workers=4]
  ├─ Thread 1: ImageCapture + Preprocess + RingDetect + ArrowDetect
  ├─ Thread 2: (independent, if multiple cameras)
  ├─ Thread 3: (independent, if multiple cameras)
  └─ Thread 4: (independent, if multiple cameras)
  ↓
Wait for completion (up to 1 second)
  ↓
ScoringCalculator combines results
  ↓
ScoreRepository persists
  ↓
HTTP response with results
```

**Latency**: ~1 second for complete pipeline (includes thread overhead)

---

## Data Flow Examples

### Example 1: Login and Get User Info

```
1. Client: POST /api/v1/auth/login {username, password}
   ↓
2. AuthHandlers.login()
   ↓
3. AuthService.login(username, password)
   ├─ UserRepository.find_by_username(username)
   │   ├─ DB: SELECT * FROM users WHERE username = ?
   │   └─ Returns: User object or None
   ├─ AuthService.verify_password(password, hashed)
   └─ AuthService.generate_token(user_id)
   ↓
4. Return: TokenResponse {access_token, expires_in}
   ↓
5. Client: GET /api/v1/auth/me {header: Authorization: Bearer token}
   ↓
6. AuthorizationMiddleware.get_current_user()
   ├─ Extract token from header
   ├─ AuthService.validate_token(token)
   └─ Returns: User object
   ↓
7. Return: User {id, username, role}
```

---

### Example 2: Start Scoring

```
1. Client: POST /api/v1/scoring/calculate {session_id, archer_id, end_num, camera_id}
   ↓
2. PermissionCheckDecorator.require_role(SCORER)
   ├─ AuthorizationMiddleware.get_current_user()
   └─ Check: user.role == SCORER
   ↓
3. ScoringHandlers.score_end()
   ↓
4. ScoringService.score_end()
   ├─ ThreadPoolExecutor.submit(image_pipeline)
   │  ├─ ImageCaptureComponent.capture_burst(camera_id)
   │  │  ├─ OpenCV: cv2.VideoCapture(camera_id)
   │  │  ├─ Capture 3 frames
   │  │  └─ Select sharpest
   │  ├─ ImagePreprocessComponent.preprocess_image()
   │  ├─ RingDetectionComponent.detect_rings()
   │  ├─ ArrowDetectionComponent.detect_arrows()
   │  └─ ScoringCalculatorComponent.calculate_scores()
   ├─ Wait for thread completion (~1 second)
   ├─ ScoreRepository.bulk_create_scores()
   │  └─ DB: INSERT INTO scores ...
   └─ EventBus.publish(ScoreCalculated)
      ├─ WebSocketConnectionManager.broadcast(score_update)
      │  └─ All connected clients: WS message with new scores
      └─ Event subscribers notified
   ↓
5. Return: ScoringResult {zones, scores, confidence, image_paths}
   ↓
6. Client receives response (~1 second elapsed)
   ↓
7. WebSocket clients receive broadcast (< 100ms after step 5)
```

---

### Example 3: Real-Time Score Broadcast

```
1. ScoringService publishes: EventBus.publish(ScoreCalculated)
   ↓
2. EventBus notifies all subscribers
   ├─ WebSocketService subscriber receives event
   ├─ Extracts: {score_id, archer_id, zones, total}
   └─ Formats message
   ↓
3. WebSocketConnectionManager.broadcast(message)
   ├─ Iterates all active connections
   ├─ Calls: websocket.send_json(message)
   └─ Each client receives < 100ms after publish
   ↓
4. Browser receives WebSocket message
   ↓
5. React component: update state (Zustand)
   ├─ Update leaderboard
   ├─ Update archer's score display
   └─ Re-render affected UI
   ↓
6. User sees updated scores in real-time
```

---

### Example 4: Camera Disconnect and Recovery

```
1. Background: CameraManager.auto_probe() [every 30 seconds]
   ├─ Probes all cameras via cv2.VideoCapture
   └─ Detects: Camera#2 no longer responds
   ↓
2. CameraManager.publish_camera_status_change(camera_id=2, status=DISCONNECTED)
   ↓
3. EventBus.publish(CameraDisconnected)
   ↓
4. Subscribers receive event:
   ├─ WebSocketService: broadcast to clients
   ├─ CameraDisconnectHandler: handle recovery
   │  ├─ CameraRepository.update_camera(camera_id=2, status=DISCONNECTED)
   │  ├─ Schedule retry in 30 seconds
   │  └─ Attempt reconnection
   └─ AuditLogger: log event
   ↓
5. WebSocketConnectionManager.broadcast(camera_status_update)
   ├─ All clients receive: {camera_id: 2, status: DISCONNECTED}
   ├─ UI shows red badge: "Camera 2 - Disconnected"
   └─ [Reconnect] button enabled
   ↓
6. User reconnects camera or CameraManager retries in 30s
   ↓
7. CameraManager detects: Camera#2 reconnected
   ├─ CameraRepository.update_camera(status=CONNECTED)
   └─ EventBus.publish(CameraConnected)
   ↓
8. WebSocket broadcasts reconnection event
   ├─ UI updates: green badge "Camera 2 - Connected"
   └─ Scoring immediately available
```

---

## Coupling Analysis

**Tightly Coupled** (by design, acceptable):
- ScoringService → Image processing components (performance critical)
- Services → Repositories (standard data layer pattern)
- Handlers → Middlewares (authentication/authorization required)

**Loosely Coupled** (by design, flexible):
- Services → EventBus (event-driven for WebSocket)
- EventBus → WebSocketService (independent subscribers)
- CameraManager → EventBus (status changes don't require direct handler knowledge)

**Moderately Coupled** (pragmatic):
- Services depend on each other when needed (SessionService depends on SessionManager)
- Decorators used for cross-cutting concerns (permissions, auth)
- Dependency Injection via FastAPI `Depends()` for flexibility

---

## Thread Safety

**Thread-Safe Components**:
- Database (PostgreSQL handles concurrent access via transactions)
- EventBus (in-process, single-threaded, subscribes called sequentially)
- WebSocketConnectionManager (uses dict with thread-safe operations)

**Thread Pool (ScoringService)**:
- Uses ThreadPoolExecutor with max_workers=4
- Each thread processes independent camera independently
- No shared state between threads (each gets own image)
- Results aggregated after all threads complete

**Cautions**:
- Camera probing runs in background; status updates may be slightly stale
- WebSocket broadcasts are synchronous; slow subscribers could block others

---

## Extension Points (Future Features)

**Easy to Add**:
- New report formats (extend ReportGenerator pattern)
- New event subscribers (just register with EventBus)
- New image detection methods (extend pipeline components)

**Moderate Effort**:
- Authentication methods beyond JWT (modify AuthService)
- New role types (extend permission decorator)
- Message queue instead of in-process EventBus (replace EventBus implementation)

**High Effort**:
- Splitting services into separate processes (requires messaging)
- Multi-tenant support (major schema changes)
- Distributed deployment (requires session/cache layer)

