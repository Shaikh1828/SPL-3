# Backend Module-wise Context

## Module 1: API Layer (`src/api/`)

### Files & Responsibilities
| File               | Lines | Endpoints                         | Story Coverage  |
|--------------------|-------|----------------------------------|----------------|
| `auth.py`          | 189   | Login, Register, Token refresh   | US-1.1         |
| `cameras.py`       | 489   | Camera CRUD, assignments         | US-5.1, US-5.2 |
| `health.py`        | 81    | Health check (DB, Redis, system) | NFR            |
| `leaderboards.py`  | 80    | Session leaderboard              | US-3.3         |
| `reports.py`       | 177   | CSV/JSON score reports           | US-4.1         |
| `scores.py`        | 825   | Score CRUD, upload, batch, override | US-2.2, US-3.1, US-3.2 |
| `sessions.py`      | 407   | Session CRUD, state management   | US-2.1         |
| `tournaments.py`   | 148   | Tournament CRUD                  | US-2.1         |
| `users.py`         | 248   | User management (admin)          | US-1.1         |
| `websocket.py`     | 405   | Real-time score streaming        | US-3.1         |

### Key API: Score Upload (`POST /sessions/{id}/scores/upload`)
```
1. Accept multipart form: {session_archer_id, round, arrow_num?, file}
2. Run ArrowDetectionService.detect() in ThreadPool
3. Extract all detected arrows and their zones
4. If dry-run (archer_id <= 0): return preview only
5. Save raw image → save annotated image → record each arrow score
6. Return aggregated score + annotated image (base64)
```

---

## Module 2: Database Models (`src/models/`)

### Entity Relationship
```
User (1) ──────> (N) Tournament
                      │
                      ▼
                 Session (N) ──> (N) CameraLaneAssignment
                      │                     │
                      ▼                     ▼
              SessionArcher (N)         Camera
                      │
                      ▼
                  Score (N)

User (1) ──> (N) AuditLog
```

### Table: `users`
| Column        | Type         | Constraints        |
|--------------|--------------|-------------------|
| id           | Integer (PK) | auto-increment    |
| username     | String(50)   | unique, not null  |
| email        | String(100)  | unique, not null  |
| password_hash| String(255)  | not null          |
| role         | String(20)   | default=spectator |
| is_active    | Boolean      | default=True      |
| created_at   | DateTime(tz) | default=now()     |

### Table: `tournaments`
| Column           | Type         | Constraints      |
|-----------------|--------------|-----------------|
| id              | Integer (PK) |                 |
| name            | String(200)  | not null        |
| description     | String(500)  | nullable        |
| location        | String(200)  | not null        |
| start_date      | DateTime(tz) | not null        |
| end_date        | DateTime(tz) | not null        |
| created_by_user_id | Integer(FK)| → users.id      |

### Table: `sessions`
| Column           | Type         | Constraints      |
|-----------------|--------------|-----------------|
| id              | Integer (PK) |                 |
| tournament_id   | Integer (FK) | → tournaments.id|
| name            | String(200)  | not null        |
| round_number    | Integer      | not null        |
| num_lanes       | Integer      | default=6       |
| arrows_per_round| Integer      | default=6       |
| status          | String(20)   | active/paused/completed |
| start_time      | DateTime(tz) | nullable        |
| end_time        | DateTime(tz) | nullable        |

### Table: `session_archers`
| Column        | Type         | Constraints        |
|--------------|--------------|-------------------|
| id           | Integer (PK) |                   |
| session_id   | Integer (FK) | → sessions.id     |
| archer_id    | Integer      | not null          |
| archer_name  | String(200)  | not null          |
| lane_number  | Integer      | nullable          |
| current_round| Integer      | default=1         |
| total_score  | Integer      | default=0         |

### Table: `scores`
| Column           | Type         | Constraints        |
|-----------------|--------------|-------------------|
| id              | Integer (PK) |                   |
| session_id      | Integer (FK) | → sessions.id     |
| session_archer_id| Integer (FK)| → session_archers.id |
| round           | Integer      | not null          |
| arrow_num       | Integer      | not null          |
| zone            | Integer      | 0-10, not null    |
| points          | Integer      | 0-10, not null    |
| image_id        | String(100)  | nullable (UUID)   |
| confidence      | Float        | nullable          |
| validated_by_ai | Boolean      | default=False     |

---

## Module 3: Services (`src/services/`)

### ArrowDetectionService (CORE)
**File**: `arrow_detection_service.py` (2665 lines)
- See `02_SCORING_SYSTEM_DEEP_DIVE.md` for complete documentation
- Pure CV pipeline, no ML model
- Multi-method target + arrow detection
- WA standard zone calculation

### ScoringService
**File**: `scoring_service.py` (324 lines)
- `validate_score()` — zone/points range check (0-10)
- `record_score_with_retry()` — DB write with exponential backoff
- `calculate_total_score()` — SUM of archer's points
- `get_session_leaderboard()` — ranked archer list
- `validate_score_record()` — AI validation flag toggle

### ImageService
**File**: `image_service.py` (547 lines)
- `detect_arrow_in_image()` — delegates to ArrowDetectionService
- `preprocess_image()` — resize + JPEG compress (quality 70)
- `save_image()` — UUID naming, storage quota check (10GB)
- `archive_old_images()` — 90-day tar.gz rotation
- `generate_annotated_image()` — draw rings + arrows + metadata overlay
- `save_annotated_image()` — save annotated version

### AuthService
**File**: `auth_service.py` (218 lines)
- bcrypt password hashing
- JWT token creation/verification (HS256, 8h expiry)
- User registration with role assignment
- Login with credential validation

### CameraService
**File**: `camera_service.py` (260 lines)
- Camera CRUD operations
- Lane assignment management
- Connection status tracking (heartbeat)
- Camera types: USB, RTSP, HTTP

### HealthService
**File**: `health_service.py` (230 lines)
- Database connectivity check
- Redis connectivity check
- System metrics (CPU, memory, disk)
- Component-level health status

### LeaderboardService
**File**: `leaderboard_service.py` (150 lines)
- Session leaderboard with Redis caching
- Cache invalidation on score updates
- Ranked archer list by total_score

### ReportService
**File**: `report_service.py` (285 lines)
- CSV report generation
- JSON export
- Session summary statistics
- PDF generation (placeholder)

---

## Module 4: Configuration & Infrastructure

### Config (`src/config.py`)
Pydantic BaseSettings with .env file support:
```python
database_url = "postgresql://postgres:postgres@localhost:5432/archery"
redis_url = "redis://localhost:6379/0"
jwt_secret = "your-secret-key"
storage_path = "/storage"
image_jpeg_quality = 70
threadpool_base_workers = 4
rate_limit_requests_per_minute = 1000
```

### Database (`src/database.py`)
- SQLAlchemy engine with QueuePool
- Pool size: 5-20 connections, recycle every 3600s
- Pre-ping enabled (detect stale connections)
- Connection retry with exponential backoff (3 retries)
- PostgreSQL connect_args: keepalive settings

### Events (`src/events.py`)
In-process publish/subscribe event bus:
```
EventTypes:
  SCORE_RECORDED → WebSocket broadcast + cache invalidation
  SCORE_VALIDATED → WebSocket notification
  SESSION_STATE_CHANGED → WebSocket broadcast
  CAMERA_CONNECTED → Status update
  ERROR_OCCURRED → Error notification
```

### Cache (`src/cache.py`)
- Redis-based with in-memory fallback
- Leaderboard caching with TTL
- Cache invalidation on score updates

### Middleware (`src/middleware/`)
1. **RateLimitMiddleware**: Per-IP request throttling (1000/min)
2. **ErrorHandlingMiddleware**: Structured error responses
3. **JWT Validation**: Token authentication for protected routes

---

## Module 5: Frontend (`frontend/src/`)

### Pages (10 total)
| Page                 | File                  | Description                      |
|---------------------|----------------------|----------------------------------|
| Dashboard           | DashboardPage.tsx     | Overview, recent scores, stats   |
| Scoring             | ScoringPage.tsx       | Image upload, live scoring       |
| Batch Testing       | BatchTestingPage.tsx  | Score entire folder of images    |
| Tournaments         | TournamentsPage.tsx   | Tournament CRUD                  |
| Cameras             | CamerasPage.tsx       | Camera management, lane assign   |
| Reports             | ReportsPage.tsx       | Score reports, exports           |
| Users               | UsersPage.tsx         | User management (admin)          |
| Settings            | SettingsPage.tsx      | System settings                  |
| Login               | LoginPage.tsx         | Authentication                   |
| Register            | RegisterPage.tsx      | User registration                |

### Tech Stack
- **Framework**: React 18 with TypeScript
- **Build**: Vite
- **Styling**: TailwindCSS
- **Routing**: React Router
- **State**: Custom hooks + context
- **API Client**: Fetch-based with TypeScript types

---

## Module 6: Utilities (`src/utils/`)

### Constants (`constants.py`)
```python
ARROW_ZONES = [0..10]
ARROW_POINTS = [0..10]
MAX_ARROWS_PER_ROUND = 6
MAX_ROUND = 20
CAMERA_TYPES = ["USB", "RTSP", "HTTP"]
SESSION_STATUSES = ["active", "paused", "completed"]
USER_ROLES = ["admin", "scorer", "spectator", "archer"]
```

### Image Processing (`image_processing.py`)
Legacy utilities (superseded by ArrowDetectionService):
- `preprocess_image()` — resize + compress
- `detect_arrow_color()` — HSV color detection
- `detect_arrow_edge()` — Canny edge detection
- `detect_arrow_ml()` — ML placeholder (returns None)
- `detect_arrow()` — fallback chain (color → edge → ML)
- `enhance_image_for_display()` — CLAHE enhancement

### Storage (`storage.py`)
- File storage management
- UUID-based image naming
- Directory organization by session
- Quota enforcement
