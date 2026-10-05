# Backend Modules & Functions Reference — Automated Archery Scoring System (SPL-3)

**Lifecycle Stage**: Inception / Reverse Engineering  
**Standard**: AIDLC Process Guidelines (`inception/reverse-engineering.md`)  
**Package Scope**: `src/` (FastAPI, OpenCV, YOLO11, SQLAlchemy, Redis)

---

## 1. Application Factory & Lifecycle (`src/main.py`)

### Module Overview
Initializes the FastAPI application, mounts ASGI middlewares (CORS, structured logging, rate limiting, error handling), manages startup/shutdown lifespan context, and mounts all API routers.

### Functions & Handlers
- **`lifespan(app: FastAPI) -> AsyncGenerator[None, None]`**
  - **Purpose**: Manages application lifecycle. Initializes `ThreadPoolExecutor`, checks Redis ping, verifies PostgreSQL database connectivity on startup; shuts down thread pool and disposes database engine pools on shutdown.
- **`log_requests(request: Request, call_next: Callable) -> Response`**
  - **Purpose**: HTTP middleware logging incoming request method, path, client IP, generating `x-request-id`, and tracking request duration in milliseconds.
- **`generic_exception_handler(request: Request, exc: Exception) -> JSONResponse`**
  - **Purpose**: Global unhandled exception handler logging traceback and returning structured 500 JSON `{ "error": "Internal server error", "status": 500 }`.
- **`root() -> dict`**
  - **Route**: `GET /`
  - **Purpose**: Provides service metadata, version, docs path (`/docs`), and health endpoint link (`/api/health`).

---

## 2. Configuration & Settings (`src/config.py`)

### Class: `Settings(BaseSettings)`
Loads configurations from environment variables and `.env` file with defaults:
- `environment: Literal["development", "staging", "production"]` (default `"development"`)
- `log_level: str` (default `"INFO"`)
- `api_title: str`, `api_version: str`, `api_workers: int`
- `database_url: str`: PostgreSQL connection URI.
- `database_pool_min_size: int` (5), `database_pool_max_size: int` (20), `database_pool_recycle: int` (3600), `database_pool_pre_ping: bool` (True)
- `redis_url: str`, `redis_max_connections: int` (10), `redis_memory_limit_mb: int` (512)
- `jwt_secret: str`, `jwt_algorithm: str` (`"HS256"`), `jwt_expiration_hours: int` (8), `refresh_token_expiration_days: int` (30)
- `cors_origins: str`: Comma-separated allowed origins.
- `storage_path: str` (default `"/storage"`), `storage_quota_gb: int` (10)
- `yolo_model_path: str` (default `"runs/detect/archery_yolo11/weights/best.pt"`), `use_yolo: bool` (True)
- `threadpool_base_workers: int` (4), `threadpool_max_workers: int` (8)

### Functions:
- `get_database_url() -> str`: Returns current database connection string.
- `get_redis_url() -> str`: Returns configured Redis URL.
- `get_jwt_secret() -> str`: Retrieves JWT signing secret.
- `get_storage_path() -> str`: Resolves storage directory and creates subdirectories (`raw`, `annotated`, `archives`, `reports`).
- `get_cors_origins() -> List[str]`: Parses comma-separated CORS origins into a list of strings.

---

## 3. Database Engine & Session Management (`src/database.py`)

### Module Singletons
- **`engine`**: SQLAlchemy QueuePool engine configured with pool sizing, connection timeout (10s), keepalive idle (30s), and pre-ping verification.
- **`SessionLocal`**: Scoped sessionmaker factory bound to `engine`.

### Functions
- **`get_db() -> Generator[Session, None, None]`**: FastAPI dependency yielding a thread-local database session and ensuring closure on request termination.
- **`get_db_connection_with_retry(max_retries: int = 3, base_backoff: float = 1.0) -> Session`**: Obtains connection using exponential backoff ($2^n$) upon `OperationalError`.
- **`verify_database_connectivity() -> bool`**: Executes `SELECT 1` to verify health.
- **`init_db()`**: Calls `Base.metadata.create_all(bind=engine)`.
- **`dispose_engine()`**: Flushes and disposes engine connection pool.

---

## 4. In-Memory Caching & Redis Manager (`src/cache.py`)

### Class: `RedisManager`
Manages synchronous and async connections to Redis with connection pooling.
- **`connect()` / `disconnect()`**: Initializes and terminates Redis connection pools.
- **`ping() -> bool`**: Pings Redis server.
- **`get(key: str) -> Optional[str]`**: Retrieves string cached value.
- **`set(key: str, value: str, expire_seconds: Optional[int] = None) -> bool`**: Stores key-value pair with optional TTL.
- **`delete(key: str) -> bool`**: Removes cached key.
- **`zadd(key: str, mapping: Dict[str, float]) -> int`**: Adds/updates members with scores in a Redis Sorted Set (used for leaderboards).
- **`zrange(key: str, start: int, stop: int, desc: bool = False, withscores: bool = False) -> List`**: Fetches sorted set slice.
- **`zrevrank(key: str, member: str) -> Optional[int]`**: Gets 0-indexed ranking in descending score order.
- **`publish(channel: str, message: str) -> int`**: Publishes messages across Redis channels.

---

## 5. Security & Cryptography (`src/security.py`)

### Functions
- **`hash_password(password: str) -> str`**: Salts and hashes passwords via `bcrypt`.
- **`verify_password(plain_password: str, hashed_password: str) -> bool`**: Validates plaintext against stored bcrypt hash.
- **`create_jwt_token(data: dict, expires_delta: Optional[timedelta] = None) -> str`**: Signs HS256 JWT access token with user claims.
- **`decode_jwt_token(token: str) -> Optional[dict]`**: Verifies signature, expiry, and decodes claims.
- **`create_refresh_token(data: dict) -> str`**: Signs long-lived 30-day refresh token.

---

## 6. Authentication Dependencies & RBAC (`src/dependencies.py`)

### Functions
- **`get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User`**: Validates bearer token and resolves active user record. Raises 401 if invalid.
- **`get_optional_user(token: Optional[str] = Depends(...), db: Session = Depends(get_db)) -> Optional[User]`**: Resolves user if token present without throwing 401.
- **`require_role(role: str) -> Callable`**: Dependency factory enforcing RBAC (`admin`, `scorer`, `spectator`, `archer`). Note: `admin` implicitly passes any role check.

---

## 7. Event Bus & Asynchronous Decoupling (`src/events.py`)

### Classes & Types
- **`EventType(str, Enum)`**: `SCORE_RECORDED`, `SCORE_UPDATED`, `LEADERBOARD_UPDATED`, `SESSION_STATUS_CHANGED`, `ARROW_DETECTED`, `CAMERA_STATUS_CHANGED`, `TARGET_DETECTED`.
- **`Event`**: Dataclass containing `event_type`, `data: dict`, `timestamp`, `session_id`.
- **`EventBus`**: In-process pub/sub event dispatcher:
  - `subscribe(event_type: EventType, callback: Callable[[Event], None])`: Registers handler.
  - `publish(event: Event)`: Dispatches event synchronously.
  - `publish_async(event: Event)`: Dispatches event on thread pool.

---

## 8. Thread Pool Manager (`src/thread_pool.py`)

### Functions
- **`set_executor(executor: ThreadPoolExecutor)`**: Sets application-wide executor instance.
- **`get_executor() -> ThreadPoolExecutor`**: Retrieves shared executor for offloading CV inference.
- **`shutdown_executor()`**: Shuts down workers on server stop.

---

## 9. Computer Vision & ML Detection Services

### 9.1 Classical Computer Vision Engine (`src/services/arrow_detection_service.py`)
- **`TargetInfo` (Dataclass)**: `center_x`, `center_y`, `radius_outer`, `a_outer`, `b_outer`, `angle_deg`, `confidence`, `detection_method`.
- **`ArrowInfo` (Dataclass)**: `tip_x`, `tip_y`, `shaft_angle`, `score`, `ring_number`, `is_x`, `normalized_distance`, `confidence`, `detection_method`.
- **`DetectionResult` (Dataclass)**: Contains `target: TargetInfo`, `arrows: List[ArrowInfo]`, `total_score: int`, `annotated_image: Optional[np.ndarray]`.

#### Core Methods in `ArrowDetectionService`:
- `detect(image: np.ndarray, previous_image: Optional[np.ndarray] = None) -> DetectionResult`: Orchestrates preprocessing, target fitting, tip detection, and WA scoring.
- `detect_target(image: np.ndarray) -> TargetInfo`: Multi-method target face detection (combining Hough circles, concentric color band masks, and multi-ellipse fits).
- `detect_arrows(image: np.ndarray, target: TargetInfo, previous_image: Optional[np.ndarray] = None) -> List[ArrowInfo]`: Identifies all arrow shafts and tips.
- `calculate_scores(target: TargetInfo, arrows: List[ArrowInfo]) -> List[ArrowInfo]`: Evaluates Euclidean distance against World Archery zone tables (`WA_ZONE_BOUNDARIES`).
- `draw_overlay(image: np.ndarray, result: DetectionResult) -> np.ndarray`: Renders concentric colored target rings, arrow crosshairs, and score badges on image.
- `_detect_puncture_holes(gray, target) -> List[ArrowInfo]`: High-confidence dark hole centroid detection.
- `_target_by_zone_ellipses(hsv, gray) -> Optional[TargetInfo]`: Multi-color concentric ellipse fitting with consensus validation.

### 9.2 Deep Learning Pipeline (`src/services/yolo_detection_service.py`)
- **`YOLOArrowDetectionService`**:
  - `__init__(model_path: Optional[str] = None)`: Loads trained Ultralytics YOLO11 weights (`best.pt`).
  - `detect_arrows(image: np.ndarray, previous_image: Optional[np.ndarray] = None) -> DetectionResult`: Runs YOLO inference to detect target and arrows, then executes local Hough edge/line refinement inside each bounding box to locate exact subpixel tips. Falls back to `ArrowDetectionService` if YOLO fails or is disabled.

---

## 10. Domain Business Logic Services (`src/services/`)

### 10.1 `AuthService` (`src/services/auth_service.py`)
- `register(db: Session, user_create: UserCreate) -> User`: Creates new active user record with hashed password.
- `authenticate(db: Session, username: str, password: str) -> Optional[User]`: Verifies credentials.
- `create_access_token(user: User) -> str` / `create_refresh_token(user: User) -> str`.
- `refresh_access_token(db: Session, refresh_token: str) -> Optional[Token]`.

### 10.2 `ScoringService` (`src/services/scoring_service.py`)
- `record_manual_score(db, session_id, archer_id, end_number, arrow_number, score, ring, is_x, user_id) -> Score`: Validates end/arrow sequence and inserts score.
- `record_auto_score(db, session_id, archer_id, detection_result, user_id) -> List[Score]`: Batch-inserts detected scores and associates annotated image paths.
- `update_score(db, score_id, updates, user_id) -> Score`: Applies manual correction and writes audit log.
- `verify_score(db, score_id, user_id) -> Score`: Marks `is_verified = True`.
- `get_session_statistics(db, session_id) -> dict`: Computes running averages, 10s count, and X counts.

### 10.3 `LeaderboardService` (`src/services/leaderboard_service.py`)
- `recalculate_session_leaderboard(db: Session, session_id: int) -> List[LeaderboardEntry]`: Queries database, calculates running totals, ranks archers, caches in Redis, and publishes `LEADERBOARD_UPDATED` event.
- `get_session_leaderboard(db: Session, session_id: int) -> List[LeaderboardEntry]`: Fast retrieval from Redis cache with DB fallback.

### 10.4 `CameraService` (`src/services/camera_service.py`)
- `register_camera(db, camera_in) -> Camera`: Registers camera device in database.
- `assign_camera_to_lane(db, camera_id, session_id, lane_number) -> CameraLaneAssignment`: Binds camera to shooting lane.
- `test_camera_stream(stream_url: str) -> Tuple[bool, str]`: Validates RTSP feed connection via OpenCV `VideoCapture`.

### 10.5 `ImageService` (`src/services/image_service.py`)
- `save_raw_image(session_id, end_number, image_bytes) -> str`: Compresses and saves incoming raw camera frame to `/storage/raw`.
- `save_annotated_image(session_id, end_number, image_array) -> str`: Encodes diagnostic overlay to `/storage/annotated`.
- `get_image(file_path: str) -> Tuple[bytes, str]`: Reads image bytes and MIME type from storage volume.

### 10.6 `ReportService` (`src/services/report_service.py`)
- `generate_session_report_pdf(db: Session, session_id: int) -> str`: Generates World Archery certified match scorecard PDF using ReportLab.
- `generate_session_report_csv(db: Session, session_id: int) -> str`: Exports tabular arrow scores to CSV file.

### 10.7 `HealthService` (`src/services/health_service.py`)
- `check_health() -> HealthResponse`: Evaluates database, cache, filesystem storage, and thread pool health.

---

## 11. REST API Controllers (`src/api/`)

| Router File | Prefix | Key Endpoints & Handler Functions |
|---|---|---|
| `auth.py` | `/api/auth` | `register()`, `login()`, `refresh_token()`, `get_me()`, `change_password()` |
| `tournaments.py` | `/api/tournaments` | `list_tournaments()`, `create_tournament()`, `get_tournament()`, `update_tournament()` |
| `sessions.py` | `/api/sessions` | `create_session()`, `get_session()`, `start_session()`, `complete_session()`, `register_archers()` |
| `scores.py` | `/api/scores` | `detect_arrows_endpoint()`, `record_score()`, `update_score()`, `verify_score()`, `get_annotated_image()` |
| `cameras.py` | `/api/cameras` | `list_cameras()`, `register_camera()`, `test_camera()`, `assign_lane()` |
| `leaderboards.py`| `/api/leaderboards`| `get_session_leaderboard()`, `get_tournament_leaderboard()` |
| `reports.py` | `/api/reports` | `download_session_pdf()`, `download_session_csv()`, `get_archer_report()` |
| `users.py` | `/api/users` | `list_users()`, `update_user_role()`, `toggle_user_status()` |
| `health.py` | `/api/health` | `get_health()`, `ping()` |
| `websocket.py` | `/api` | `score_stream_endpoint()` (`/api/ws/{session_id}`), `camera_preview_endpoint()` (`/api/ws/camera/{camera_id}/preview`) |
