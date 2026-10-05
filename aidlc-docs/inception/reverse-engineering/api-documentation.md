# API Specification & Contracts — Automated Archery Scoring System (SPL-3)

**Lifecycle Stage**: Inception / Reverse Engineering  
**Standard**: AIDLC Process Guidelines (`inception/reverse-engineering.md`)  
**Base URL**: `/api` (or direct backend: `http://localhost:8000/api`)  
**Authentication**: Bearer Token (`Authorization: Bearer <JWT>`)

---

## 1. Authentication & User Management APIs (`/api/auth`, `/api/users`)

### 1.1 POST `/api/auth/register`
- **Purpose**: Registers a new archer or spectator account.
- **Access**: Public.
- **Request Body**:
  ```json
  {
    "username": "archer_jane",
    "email": "jane@archery.local",
    "password": "Password123!",
    "role": "archer"
  }
  ```
- **Response** (`201 Created`):
  ```json
  {
    "id": 5,
    "username": "archer_jane",
    "email": "jane@archery.local",
    "role": "archer",
    "is_active": true,
    "created_at": "2026-10-02T00:00:00"
  }
  ```

### 1.2 POST `/api/auth/login`
- **Purpose**: Authenticates credentials and returns JWT tokens.
- **Access**: Public.
- **Request Body**:
  ```json
  {
    "username": "admin",
    "password": "admin123!"
  }
  ```
- **Response** (`200 OK`):
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "refresh_token": "eyJhbGciOi...",
    "token_type": "Bearer",
    "expires_in": 28800
  }
  ```

### 1.3 GET `/api/auth/me`
- **Purpose**: Retrieves current authenticated user profile.
- **Access**: Authenticated (`admin`, `scorer`, `spectator`, `archer`).
- **Response** (`200 OK`): `UserResponse` schema.

### 1.4 GET `/api/users`
- **Purpose**: Lists registered users with optional role filtering.
- **Access**: `admin` only.
- **Query Params**: `role` (optional), `skip` (default 0), `limit` (default 50).
- **Response** (`200 OK`): Array of `UserResponse`.

---

## 2. Tournament & Session Management APIs (`/api/tournaments`, `/api/sessions`)

### 2.1 GET `/api/tournaments`
- **Purpose**: Lists all tournaments.
- **Access**: Authenticated.
- **Response** (`200 OK`): Array of `TournamentResponse`.

### 2.2 POST `/api/tournaments`
- **Purpose**: Creates a new tournament.
- **Access**: `admin` only.
- **Request Body**:
  ```json
  {
    "name": "National Indoor Championship 2026",
    "description": "Annual 18m indoor tournament",
    "start_date": "2026-11-01T09:00:00",
    "end_date": "2026-11-03T18:00:00"
  }
  ```

### 2.3 POST `/api/sessions`
- **Purpose**: Creates a shooting session round within a tournament.
- **Access**: `admin` or `scorer`.
- **Request Body**:
  ```json
  {
    "tournament_id": 1,
    "name": "Qualification Round 1",
    "target_face_size": 40,
    "total_ends": 10,
    "arrows_per_end": 3
  }
  ```

### 2.4 POST `/api/sessions/{id}/start`
- **Purpose**: Transitions session status from `PENDING` to `IN_PROGRESS`.
- **Access**: `admin` or `scorer`.

### 2.5 POST `/api/sessions/{id}/complete`
- **Purpose**: Finalizes session, marks status as `COMPLETED`.
- **Access**: `admin` or `scorer`.

---

## 3. Scoring & Arrow Detection APIs (`/api/scores`)

### 3.1 POST `/api/scores/detect`
- **Purpose**: Primary AI vision endpoint. Accepts raw target face image file, runs YOLO11 + OpenCV edge analysis, computes arrow ring scores, and generates annotated overlay image.
- **Access**: `admin` or `scorer`.
- **Request**: `multipart/form-data` with `file: UploadFile` and optional `session_id: int`, `end_number: int`.
- **Response** (`200 OK`):
  ```json
  {
    "success": true,
    "target": {
      "center_x": 512.4,
      "center_y": 508.1,
      "radius_outer": 490.2,
      "confidence": 0.96
    },
    "arrows": [
      {
        "arrow_number": 1,
        "x": 515.2,
        "y": 505.0,
        "score": 10,
        "is_x": true,
        "normalized_distance": 0.012,
        "confidence": 0.94,
        "method": "yolo_subpixel"
      },
      {
        "arrow_number": 2,
        "x": 620.1,
        "y": 510.4,
        "score": 8,
        "is_x": false,
        "normalized_distance": 0.221,
        "confidence": 0.91,
        "method": "puncture_hole"
      }
    ],
    "total_score": 18,
    "annotated_image_url": "/api/scores/images/annotated_10492.jpg"
  }
  ```

### 3.2 POST `/api/scores/record`
- **Purpose**: Records or confirms an individual arrow score into the database.
- **Access**: `admin` or `scorer`.
- **Request Body**:
  ```json
  {
    "session_id": 1,
    "session_archer_id": 2,
    "end_number": 1,
    "arrow_number": 1,
    "score": 10,
    "ring_number": 10,
    "is_x": true,
    "x_coordinate": 515.2,
    "y_coordinate": 505.0,
    "normalized_distance": 0.012,
    "confidence": 0.94,
    "detection_method": "yolo_subpixel",
    "is_verified": true
  }
  ```

### 3.3 PUT `/api/scores/{id}`
- **Purpose**: Updates or corrects an existing score record (manual override).
- **Access**: `admin` or `scorer`.

---

## 4. Hardware Camera & Preview APIs (`/api/cameras`)

### 4.1 POST `/api/cameras`
- **Purpose**: Registers a new network camera device.
- **Access**: `admin`.
- **Request Body**:
  ```json
  {
    "name": "Lane 1 Target Camera",
    "stream_url": "rtsp://admin:pass@192.168.1.101:554/stream1",
    "camera_type": "RTSP",
    "resolution": {"width": 1920, "height": 1080}
  }
  ```

### 4.2 POST `/api/cameras/{id}/assign`
- **Purpose**: Assigns a camera device to a specific shooting lane and session.
- **Access**: `admin` or `scorer`.

---

## 5. Real-Time WebSocket Channels (`/api/ws`)

### 5.1 WS `/api/ws/{session_id}?token={jwt}`
- **Purpose**: Live score streaming channel for tournament displays and scoreboards.
- **Protocol**: Text WebSocket JSON Frames.
- **Broadcast Events**:
  - `SCORE_RECORDED`: Emitted whenever an arrow score is saved.
  - `LEADERBOARD_UPDATED`: Emitted with top archers, running totals, and rank deltas.
  - `END_COMPLETED`: Emitted when an archer finishes shooting an end.
- **Payload Example**:
  ```json
  {
    "event": "SCORE_RECORDED",
    "session_id": 1,
    "session_archer_id": 2,
    "end_number": 1,
    "arrow_number": 1,
    "score": 10,
    "is_x": true,
    "timestamp": "2026-10-02T00:05:00Z"
  }
  ```

### 5.2 WS `/api/ws/camera/{camera_id}/preview?token={jwt}`
- **Purpose**: Low-latency video preview stream.
- **Protocol**: Binary WebSocket Blob Frames (MIME: `image/jpeg`).
- **Behavior**: Streams ~15–30 FPS downsampled camera frames or mock target face frames directly to the frontend HTML `<img />` tag via `URL.createObjectURL(blob)`.

---

## 6. Reports & System Health APIs (`/api/reports`, `/api/health`)

### 6.1 GET `/api/reports/session/{session_id}/pdf`
- **Purpose**: Generates and downloads a World Archery certified match scorecard in PDF format.
- **Access**: Authenticated.

### 6.2 GET `/api/health`
- **Purpose**: Validates system component connectivity.
- **Access**: Public.
- **Response** (`200 OK`):
  ```json
  {
    "status": "ok",
    "components": {
      "database": {"status": "ok", "message": "Database connected"},
      "cache": {"status": "ok", "message": "Cache connected"},
      "storage": {"status": "ok", "used_gb": 0.0, "quota_gb": 10},
      "threadpool": {"status": "ok", "active_workers": 0, "max_workers": 4}
    }
  }
  ```
