# Component Inventory — Automated Archery Scoring System (SPL-3)

**Lifecycle Stage**: Inception / Reverse Engineering  
**Standard**: AIDLC Process Guidelines (`inception/reverse-engineering.md`)  
**Scope**: All source packages, services, frontend components, and scripts

---

## 1. Application Packages

### 1.1 Backend Core & API Layer (`src/api/`)
| Component | Type | Responsibility |
|---|---|---|
| `src.api.auth` | REST Router | Handles `/api/auth` login, registration, refresh, and profile endpoints. |
| `src.api.tournaments` | REST Router | Handles `/api/tournaments` tournament setup, listing, and round bindings. |
| `src.api.sessions` | REST Router | Handles `/api/sessions` end count, archer lane assignments, and status transitions. |
| `src.api.scores` | REST Router | Handles `/api/scores/detect`, manual recording, updates, and image retrieval. |
| `src.api.cameras` | REST Router | Handles `/api/cameras` camera CRUD, stream verification, and lane assignments. |
| `src.api.leaderboards`| REST Router | Handles `/api/leaderboards` session and tournament aggregated rankings. |
| `src.api.reports` | REST Router | Handles `/api/reports` PDF scorecard and CSV audit log generation. |
| `src.api.users` | REST Router | Handles `/api/users` user directory, active toggling, and role modification. |
| `src.api.health` | REST Router | Handles `/api/health` system health diagnostics and metrics. |
| `src.api.websocket` | WS Router | Handles `/api/ws/{session_id}` score broadcast and `/api/ws/camera/{id}/preview`. |

### 1.2 Backend Service Layer (`src/services/`)
| Component | Type | Responsibility |
|---|---|---|
| `ArrowDetectionService` | Service | Classical computer vision pipeline: Hough circle fitting, color bands, contour ellipses, puncture hole detection. |
| `YOLOArrowDetectionService` | Service | Deep learning hybrid pipeline: YOLO11 bounding box inference with subpixel edge refinement. |
| `ScoringService` | Service | Business logic for score validation, manual score entry, and session score calculations. |
| `LeaderboardService` | Service | Redis sorted set aggregation, running totals, 10s and Xs calculation. |
| `CameraService` | Service | Camera hardware registration, RTSP connection validation, frame sampling. |
| `ImageService` | Service | Image storage management, JPEG optimization, diagnostic crop creation. |
| `AuthService` | Service | Bcrypt password hashing, JWT generation, user lookup. |
| `ReportService` | Service | PDF scorecard rendering (ReportLab) and CSV exports. |
| `HealthService` | Service | Connectivity checks across PostgreSQL, Redis, ThreadPool, and storage quotas. |

### 1.3 Frontend Presentation Layer (`frontend/src/`)
| Component | Type | Responsibility |
|---|---|---|
| `DashboardPage` | React Page | High-level tournament overview, active session monitoring, quick actions. |
| `TournamentsPage` | React Page | Tournament management grid, round configurations, session launch. |
| `ScoringPage` | React Page | Interactive target face scoring interface, manual overrides, arrow tips. |
| `BatchTestingPage` | React Page | CV testing and validation harness with batch image uploads and confusion metrics. |
| `CamerasPage` | React Page | Camera registry, RTSP configuration, live video preview grid. |
| `ReportsPage` | React Page | Match scorecards, archer analytics, Recharts score distribution charts. |
| `UsersPage` | React Page | User role administration, active status toggles. |
| `SettingsPage` | React Page | Theme preferences, backend API settings. |
| `LoginPage` / `RegisterPage` | React Page | User authentication, token acquisition. |
| `Layout`, `Sidebar`, `TopBar` | Layout | Responsive navigation frame, role-filtered route links, user profile. |
| `ScoreDetailsModal` | UI Modal | Detailed arrow-level analysis dialog showing x/y coordinates and confidence. |
| `AuthenticatedImage` | UI Widget | Image loader injecting JWT Bearer tokens to fetch protected target crops. |

---

## 2. Infrastructure & Orchestration Packages

| Component | Technology | Responsibility |
|---|---|---|
| `docker-compose.yml` | Docker Compose | Multi-container specification (`frontend`, `api`, `db`, `cache`). |
| `Dockerfile` (Root) | Multi-stage Docker | Python 3.11 backend container with CPU PyTorch and OpenCV runtime. |
| `frontend/Dockerfile`| Multi-stage Docker | Node 20 builder with Nginx Alpine static serving and API reverse proxy. |
| `frontend/nginx.conf`| Nginx Configuration | Ingress routing, SPA fallback, WebSocket upgrade proxying, gzip. |
| `alembic/` | Alembic Migration | Database revision history and automatic schema generation. |
| `setup_db.py` | Python Script | Self-healing table creation and default demo user account provisioning. |

---

## 3. Shared & Utility Packages

| Component | Responsibility |
|---|---|
| `src.models` | SQLAlchemy ORM database models (`User`, `Tournament`, `Session`, `Score`, `Camera`, `AuditLog`). |
| `src.schemas` | Pydantic v2 data transfer schemas with validation rules. |
| `src.middleware` | ASGI middlewares: `RateLimitMiddleware`, `ErrorHandlingMiddleware`, `JWTValidationMiddleware`. |
| `src.utils.constants` | World Archery zone ratios, score points, colors, error codes. |
| `src.utils.image_processing` | OpenCV image transforms, resizing, normalization helpers. |
| `src.utils.storage` | Storage directory provisioning and quota monitoring. |
| `frontend.src.store` | Zustand state stores: `authStore`, `sessionStore`, `cameraStore`. |
| `frontend.src.hooks` | Reusable hooks: `useWebSocket`, `useScoreStream`, `useCameraPreview`. |
| `frontend.src.utils.ws` | Dynamic WebSocket URL resolution helper. |

---

## 4. Test Packages

| Component | Test Type | Coverage |
|---|---|---|
| `tests.test_api_endpoints` | Integration | Covers REST endpoints for auth, tournaments, sessions, scores, cameras, users. |
| `tests.test_services` | Unit | Tests `ScoringService`, `LeaderboardService`, `ArrowDetectionService`, geometry. |
| `scripts.test_docker_stack`| End-to-End | Validates complete Docker Compose multi-container stack and HTTP/WS proxying. |
| `scripts.evaluate_yolo` | Benchmark | Evaluates YOLO11 precision, recall, and mAP against the 504-image dataset. |

---

## 5. Total Component Inventory Count

- **Total Backend API Routers**: 10
- **Total Backend Domain Services**: 9
- **Total SQLAlchemy Models**: 8
- **Total Pydantic Schemas**: 35+
- **Total Frontend Pages**: 10
- **Total Frontend Components & Widgets**: 8
- **Total Frontend Stores & Hooks**: 6
- **Total Operational & Training Scripts**: 7
- **Total Docker Services**: 4 (`frontend`, `api`, `db`, `cache`)
