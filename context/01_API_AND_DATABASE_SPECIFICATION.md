# SPL-3: API & Database Specification Master Reference

---

## 1. REST & WebSocket API Specification

The FastAPI backend exposes 26 endpoints across 11 route files in `src/api/` guarded by strict Role-Based Access Control (RBAC):

### Role Permission Matrix
| System Role | Tournament/Session Ops | Camera Ops | Image Upload & Scoring | Score Overrides | User Management |
|---|---|---|---|---|---|
| **`admin`** | ✅ Full Access | ✅ Full Access | ✅ Full Access | ✅ Full Access | ✅ Full Access |
| **`scorer`** | ✅ Create/Manage | ✅ Connect/Assign | ✅ Upload/Record | ✅ Allowed | ❌ Restricted |
| **`spectator`** | 👁️ Read-Only | 👁️ Read-Only | ❌ Restricted | ❌ Restricted | ❌ Restricted |
| **`archer`** | 👁️ Read-Only | 👁️ Read-Only | ❌ Restricted | ❌ Restricted | ❌ Restricted |

### 1.1 Authentication Routes (`src/api/auth.py`)

#### 1. `POST /api/auth/register`
- **Description**: Registers a new user account.
- **Access**: Public
- **Request Body** (`application/json`):
  ```json
  {
    "username": "scorer1",
    "email": "scorer1@archery.com",
    "password": "Password123!",
    "role": "scorer"
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "id": 1,
    "username": "scorer1",
    "email": "scorer1@archery.com",
    "role": "scorer",
    "is_active": true,
    "created_at": "2026-08-07T14:00:00Z"
  }
  ```

#### 2. `POST /api/auth/login`
- **Description**: Authenticates credentials and returns a JWT bearer access token.
- **Access**: Public
- **Request Body** (`application/json`):
  ```json
  {
    "username": "scorer1",
    "password": "Password123!"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1Ni...",
    "token_type": "bearer",
    "expires_in": 28800,
    "user": {
      "id": 1,
      "username": "scorer1",
      "email": "scorer1@archery.com",
      "role": "scorer"
    }
  }
  ```

#### 3. `POST /api/auth/refresh`
- **Description**: Refreshes an active JWT access token.
- **Access**: Authenticated
- **Response** (`200 OK`): TokenResponse schema.

#### 4. `POST /api/auth/reset-password`
- **Description**: Resets user password.
- **Access**: Admin or Self

---

### 1.2 Tournament Routes (`src/api/tournaments.py`)

#### 1. `GET /api/tournaments`
- **Description**: Retrieves a list of all tournaments.
- **Access**: Authenticated

#### 2. `POST /api/tournaments`
- **Description**: Creates a new tournament.
- **Access**: Admin / Scorer
- **Request Body**: `{ name, description, location, start_date, end_date }`

#### 3. `GET /api/tournaments/{tournament_id}`
- **Description**: Gets tournament details by ID.

#### 4. `GET /api/tournaments/{tournament_id}/sessions`
- **Description**: Gets all scoring sessions for a tournament.

---

### 1.3 Session Routes (`src/api/sessions.py`)

#### 1. `POST /api/sessions`
- **Description**: Creates a new scoring session.

#### 2. `GET /api/sessions/{session_id}`
- **Description**: Gets session details, status, and archer assignments.

#### 3. `POST /api/sessions/{session_id}/archers`
- **Description**: Registers an archer to a lane in the session.

---

### 1.4 Score Routes (`src/api/scores.py`)

#### 1. `POST /api/sessions/{session_id}/scores/upload`
- **Description**: Uploads a target image for automated YOLO11 arrow detection and score recording.
- **Access**: Scorer / Admin
- **Request Form Data** (`multipart/form-data`):
  - `session_archer_id`: Integer (ID of archer, or `<= 0` for dry-run preview)
  - `round`: Integer (Round number, e.g. 1)
  - `arrow_num`: Optional Integer
  - `file`: Image file (JPEG/PNG)
- **Response** (`200 OK`):
  ```json
  {
    "zone": 5,
    "points": 5,
    "confidence": 0.9131,
    "method": "yolo11+geometric_yolo11_rings+yolo11_hybrid",
    "distance_ratio": 0.4918,
    "target_center": [448.31, 383.08],
    "target_radius": 225.03,
    "arrow_tip": [511.0, 476.0],
    "arrows": [
      { "tip_x": 511.0, "tip_y": 476.0, "confidence": 0.9149, "method": "yolo11_hybrid", "zone": 5, "points": 5 },
      { "tip_x": 438.0, "tip_y": 435.0, "confidence": 0.8896, "method": "yolo11_hybrid", "zone": 8, "points": 8 },
      { "tip_x": 518.0, "tip_y": 435.0, "confidence": 0.8808, "method": "yolo11_hybrid", "zone": 7, "points": 7 }
    ],
    "image_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "annotated_image_url": "/api/scores/123/image-annotated"
  }
  ```

#### 2. `POST /api/scores/{score_id}/override`
- **Description**: Manually overrides an AI-calculated score (requires Admin or Scorer role). Logs an audit entry.

#### 3. `POST /api/scores/{score_id}/validate`
- **Description**: Validates and locks a score record.

---

### 1.5 Leaderboard Routes (`src/api/leaderboards.py`)

#### 1. `GET /api/sessions/{session_id}/leaderboard`
- **Description**: Fetches live archer standings for a session. Cached in Redis for sub-millisecond retrieval.
- **Access**: Public

---

### 1.6 Health Routes (`src/api/health.py`)

#### 1. `GET /api/health`
- **Description**: Light health check pinging DB, Redis, storage, and threadpool.
- **Response** (`200 OK`):
  ```json
  {
    "status": "ok",
    "timestamp": "2026-08-07T09:54:26.986307",
    "components": {
      "database": { "status": "ok", "message": "Database connected" },
      "cache": { "status": "ok", "message": "Cache connected" },
      "storage": { "status": "ok", "used_gb": 0.0, "quota_gb": 10 },
      "threadpool": { "status": "ok", "active_workers": 0, "max_workers": 4 }
    }
  }
  ```

#### 2. `GET /api/health/detailed`
- **Description**: Returns detailed system diagnostics, memory usage, CPU load, and thread execution telemetry.

---

### 1.7 WebSocket Real-Time Stream (`src/api/websocket.py`)

#### `WS /ws/sessions/{session_id}/scores`
- **Description**: Subscribes to real-time score updates for a session. Publishes event payloads whenever a score is recorded or updated.

---

## 2. Database Schema Reference (PostgreSQL 15)

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

### Table Definitions

#### 1. `users`
| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | Auto-increment | Unique user ID |
| `username` | String(50) | Unique, Not Null | None | Username |
| `email` | String(100) | Unique, Not Null | None | User email address |
| `password_hash` | String(255) | Not Null | None | Bcrypt password hash |
| `role` | String(20) | Not Null | `'spectator'` | `admin`, `scorer`, `spectator` |
| `is_active` | Boolean | Not Null | `True` | Active status flag |
| `created_at` | DateTime(tz) | Not Null | `now()` | Account creation time |

#### 2. `tournaments`
| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | Auto-increment | Tournament ID |
| `name` | String(200) | Not Null | None | Tournament title |
| `description` | String(500) | Nullable | None | Tournament details |
| `location` | String(200) | Not Null | None | Venue location |
| `start_date` | DateTime(tz) | Not Null | None | Tournament start |
| `end_date` | DateTime(tz) | Not Null | None | Tournament end |
| `created_by_user_id` | Integer | FK ➔ `users.id` | None | Creator user ID |

#### 3. `sessions`
| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | Auto-increment | Session ID |
| `tournament_id` | Integer | FK ➔ `tournaments.id` | None | Associated tournament |
| `name` | String(200) | Not Null | None | Session name (e.g. Qualification Round 1) |
| `round_number` | Integer | Not Null | `1` | Round index |
| `num_lanes` | Integer | Not Null | `6` | Total shooting lanes |
| `arrows_per_round` | Integer | Not Null | `6` | Arrows per end |
| `status` | String(20) | Not Null | `'active'` | `active`, `paused`, `completed` |
| `start_time` | DateTime(tz) | Nullable | None | Session start timestamp |
| `end_time` | DateTime(tz) | Nullable | None | Session completion timestamp |

#### 4. `session_archers`
| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | Auto-increment | Session archer ID |
| `session_id` | Integer | FK ➔ `sessions.id` | None | Session reference |
| `archer_id` | Integer | Not Null | None | Archer ID |
| `archer_name` | String(200) | Not Null | None | Archer full name |
| `lane_number` | Integer | Nullable | None | Assigned lane |
| `current_round` | Integer | Not Null | `1` | Current active round |
| `total_score` | Integer | Not Null | `0` | Cumulative total score |

#### 5. `scores`
| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | Auto-increment | Score ID |
| `session_id` | Integer | FK ➔ `sessions.id` | None | Session reference |
| `session_archer_id` | Integer | FK ➔ `session_archers.id` | None | Archer reference |
| `round` | Integer | Not Null | None | Round index |
| `arrow_num` | Integer | Not Null | None | Arrow number in end |
| `zone` | Integer | Not Null | None | Scored zone (0–10) |
| `points` | Integer | Not Null | None | Point value (= zone) |
| `image_id` | String(100) | Nullable | None | UUID reference to stored image |
| `confidence` | Float | Nullable | None | YOLO detection confidence |
| `validated_by_ai` | Boolean | Not Null | `False` | AI detection flag |

#### 6. `cameras`
| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | Auto-increment | Camera ID |
| `name` | String(100) | Not Null | None | Camera display name |
| `camera_type` | String(20) | Not Null | `'usb'` | `usb`, `rtsp`, `http` |
| `source_url` | String(500) | Nullable | None | RTSP/HTTP URL or USB device index |
| `status` | String(20) | Not Null | `'disconnected'` | `connected`, `disconnected`, `error` |
| `last_seen` | DateTime(tz) | Nullable | None | Last heartbeat timestamp |

#### 7. `camera_lane_assignments`
| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | Auto-increment | Assignment ID |
| `session_id` | Integer | FK ➔ `sessions.id` | None | Session reference |
| `camera_id` | Integer | FK ➔ `cameras.id` | None | Camera reference |
| `lane_number` | Integer | Not Null | None | Assigned lane number |

#### 8. `audit_logs`
| Column | Type | Constraints | Default | Description |
|---|---|---|---|---|
| `id` | Integer | Primary Key | Auto-increment | Audit log ID |
| `user_id` | Integer | FK ➔ `users.id` | None | Acting user ID |
| `action` | String(100) | Not Null | None | Action name (e.g. `SCORE_OVERRIDE`) |
| `details` | String(1000) | Nullable | None | Action payload details |
| `created_at` | DateTime(tz) | Not Null | `now()` | Timestamp |

---

## 3. Database Migrations (Alembic)

Schema migrations are managed via Alembic in `alembic/`:

```bash
# Generate a new migration script
alembic revision --autogenerate -m "migration_description"

# Apply all pending migrations
alembic upgrade head

# Rollback single migration step
alembic downgrade -1
```
