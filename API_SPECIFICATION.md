# Archery Scoring System - API Specification

## Overview

Complete REST API specification for the Archery Scoring System backend. FastAPI provides interactive Swagger UI at `/docs` and ReDoc at `/redoc`.

**Base URL**: `http://localhost:8000/api`  
**API Version**: 1.0.0  
**Authentication**: JWT Bearer Token (8-hour expiration, 30-day refresh tokens)

---

## Authentication Endpoints

### POST /auth/register
Register a new user account.

**Request:**
```json
{
  "username": "archer_john",
  "email": "john@example.com",
  "password": "SecurePassword123!"
}
```

**Response** (201 Created):
```json
{
  "id": 1,
  "username": "archer_john",
  "email": "john@example.com",
  "role": "archer",
  "is_active": true,
  "created_at": "2026-05-25T10:30:00Z"
}
```

**Error Responses**:
- 400: Weak password / Invalid email
- 409: Username or email already exists
- 422: Validation error

---

### POST /auth/login
Authenticate and receive JWT tokens.

**Request:**
```json
{
  "username": "archer_john",
  "password": "SecurePassword123!"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 28800
}
```

**Error Responses**:
- 401: Invalid credentials
- 404: User not found

---

### POST /auth/refresh
Refresh expired access token using refresh token.

**Headers:**
```
Authorization: Bearer {refresh_token}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 28800
}
```

**Error Responses**:
- 401: Invalid or expired refresh token

---

### POST /auth/reset-password
Reset user password.

**Request:**
```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewPassword123!"
}
```

**Response** (200 OK):
```json
{
  "success": true,
  "message": "Password reset successfully"
}
```

**Error Responses**:
- 400: Weak new password
- 401: Invalid current password

---

## Tournament Endpoints

### GET /tournaments
List all tournaments with pagination and search.

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Records per page (default: 10, max: 100)
- `search`: Search by tournament name or location
- `sort_by`: created_at | start_date | name (default: created_at)

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": 1,
      "name": "Spring Championship 2026",
      "description": "Annual spring archery championship",
      "location": "Olympic Park",
      "start_date": "2026-06-01",
      "end_date": "2026-06-03",
      "created_by": 1,
      "created_at": "2026-05-25T10:30:00Z",
      "updated_at": "2026-05-25T10:30:00Z"
    }
  ],
  "total": 15,
  "skip": 0,
  "limit": 10
}
```

---

### POST /tournaments
Create a new tournament.

**Request:**
```json
{
  "name": "Summer Qualifier 2026",
  "description": "Regional summer qualifying round",
  "location": "Central Arena",
  "start_date": "2026-07-10",
  "end_date": "2026-07-12"
}
```

**Response** (201 Created):
```json
{
  "id": 2,
  "name": "Summer Qualifier 2026",
  "description": "Regional summer qualifying round",
  "location": "Central Arena",
  "start_date": "2026-07-10",
  "end_date": "2026-07-12",
  "created_by": 1,
  "created_at": "2026-05-25T11:00:00Z",
  "updated_at": "2026-05-25T11:00:00Z"
}
```

**Error Responses**:
- 400: Invalid date range (end_date before start_date)
- 401: Unauthorized
- 422: Validation error

---

### GET /tournaments/{tournament_id}
Get tournament details.

**Response** (200 OK):
```json
{
  "id": 1,
  "name": "Spring Championship 2026",
  "description": "Annual spring archery championship",
  "location": "Olympic Park",
  "start_date": "2026-06-01",
  "end_date": "2026-06-03",
  "created_by": 1,
  "created_at": "2026-05-25T10:30:00Z",
  "updated_at": "2026-05-25T10:30:00Z"
}
```

**Error Responses**:
- 404: Tournament not found

---

## Session Endpoints

### GET /tournaments/{tournament_id}/sessions
List all sessions (scoring rounds) for a tournament.

**Query Parameters:**
- `skip`: Number of records to skip (default: 0)
- `limit`: Records per page (default: 20, max: 100)
- `status`: active | paused | completed

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": 1,
      "tournament_id": 1,
      "name": "Round 1 - Morning",
      "round_number": 1,
      "status": "active",
      "start_time": "2026-06-01T08:00:00Z",
      "end_time": null,
      "num_lanes": 6,
      "arrows_per_round": 6,
      "created_at": "2026-05-25T12:00:00Z",
      "updated_at": "2026-05-25T12:00:00Z"
    }
  ],
  "total": 3,
  "skip": 0,
  "limit": 20
}
```

---

### POST /tournaments/{tournament_id}/sessions
Create a new scoring session.

**Request:**
```json
{
  "name": "Round 2 - Afternoon",
  "round_number": 2,
  "num_lanes": 6,
  "arrows_per_round": 6
}
```

**Response** (201 Created):
```json
{
  "id": 2,
  "tournament_id": 1,
  "name": "Round 2 - Afternoon",
  "round_number": 2,
  "status": "active",
  "start_time": "2026-06-01T14:00:00Z",
  "end_time": null,
  "num_lanes": 6,
  "arrows_per_round": 6,
  "created_at": "2026-05-25T13:00:00Z",
  "updated_at": "2026-05-25T13:00:00Z"
}
```

**Error Responses**:
- 404: Tournament not found
- 409: Duplicate round number in tournament

---

### GET /sessions/{session_id}
Get session details.

**Response** (200 OK):
```json
{
  "id": 1,
  "tournament_id": 1,
  "name": "Round 1 - Morning",
  "round_number": 1,
  "status": "active",
  "start_time": "2026-06-01T08:00:00Z",
  "end_time": null,
  "num_lanes": 6,
  "arrows_per_round": 6,
  "archers_count": 24,
  "scores_count": 864,
  "created_at": "2026-05-25T12:00:00Z",
  "updated_at": "2026-05-25T12:00:00Z"
}
```

---

### PATCH /sessions/{session_id}
Update session status (start, pause, complete).

**Request:**
```json
{
  "status": "paused"
}
```

**Response** (200 OK):
```json
{
  "id": 1,
  "tournament_id": 1,
  "name": "Round 1 - Morning",
  "round_number": 1,
  "status": "paused",
  "start_time": "2026-06-01T08:00:00Z",
  "end_time": null,
  "num_lanes": 6,
  "arrows_per_round": 6,
  "created_at": "2026-05-25T12:00:00Z",
  "updated_at": "2026-05-25T14:30:00Z"
}
```

**Valid Transitions**:
- active → paused
- paused → active
- active → completed
- paused → completed

**Error Responses**:
- 400: Invalid status transition
- 404: Session not found

---

### POST /sessions/{session_id}/archers
Register an archer in a session.

**Request:**
```json
{
  "archer_name": "John Smith",
  "lane_number": 3
}
```

**Response** (201 Created):
```json
{
  "id": 15,
  "session_id": 1,
  "archer_name": "John Smith",
  "lane_number": 3,
  "total_score": 0,
  "registered_at": "2026-05-25T14:00:00Z"
}
```

**Error Responses**:
- 400: Lane already assigned to another archer
- 404: Session not found

---

## Score Endpoints

### POST /sessions/{session_id}/scores
Record a new score with automatic retry on database failures.

**Request:**
```json
{
  "session_archer_id": 15,
  "round_number": 1,
  "arrow_number": 1,
  "zone": 8,
  "points": 8,
  "image_path": "/storage/raw/1/arrow_20260601_001.jpg"
}
```

**Response** (201 Created):
```json
{
  "id": 456,
  "session_id": 1,
  "session_archer_id": 15,
  "round_number": 1,
  "arrow_number": 1,
  "zone": 8,
  "points": 8,
  "image_path": "/storage/raw/1/arrow_20260601_001.jpg",
  "validated_by_ai": false,
  "confidence": 0.85,
  "created_at": "2026-05-25T14:05:00Z",
  "updated_at": "2026-05-25T14:05:00Z"
}
```

**Features**:
- Automatic exponential backoff retry (Pattern #2): max 3 retries with 100ms-1000ms delay
- Async score recording with event publishing

**Error Responses**:
- 400: Invalid zone or points
- 503: Database failure after max retries

---

### GET /sessions/{session_id}/scores
List scores for a session with optional round filter.

**Query Parameters:**
- `round_number`: Filter by specific round (optional)
- `skip`: Number of records to skip (default: 0)
- `limit`: Records per page (default: 100, max: 500)

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": 456,
      "session_id": 1,
      "session_archer_id": 15,
      "round_number": 1,
      "arrow_number": 1,
      "zone": 8,
      "points": 8,
      "image_path": "/storage/raw/1/arrow_20260601_001.jpg",
      "validated_by_ai": false,
      "confidence": 0.85,
      "created_at": "2026-05-25T14:05:00Z",
      "updated_at": "2026-05-25T14:05:00Z"
    }
  ],
  "total": 864,
  "skip": 0,
  "limit": 100
}
```

---

### GET /scores/{score_id}
Get individual score details.

**Response** (200 OK):
```json
{
  "id": 456,
  "session_id": 1,
  "session_archer_id": 15,
  "round_number": 1,
  "arrow_number": 1,
  "zone": 8,
  "points": 8,
  "image_path": "/storage/raw/1/arrow_20260601_001.jpg",
  "validated_by_ai": false,
  "confidence": 0.85,
  "created_at": "2026-05-25T14:05:00Z",
  "updated_at": "2026-05-25T14:05:00Z"
}
```

---

### POST /scores/{score_id}/validate
Validate or re-evaluate a score (AI validation flag).

**Request:**
```json
{
  "validated_by_ai": true,
  "confidence": 0.92
}
```

**Response** (200 OK):
```json
{
  "id": 456,
  "session_id": 1,
  "session_archer_id": 15,
  "round_number": 1,
  "arrow_number": 1,
  "zone": 8,
  "points": 8,
  "image_path": "/storage/raw/1/arrow_20260601_001.jpg",
  "validated_by_ai": true,
  "confidence": 0.92,
  "created_at": "2026-05-25T14:05:00Z",
  "updated_at": "2026-05-25T14:10:00Z"
}
```

---

## Camera Endpoints

### GET /sessions/{session_id}/cameras
List cameras assigned to a session.

**Response** (200 OK):
```json
{
  "items": [
    {
      "id": 1,
      "name": "Lane 1 Camera",
      "camera_type": "USB",
      "connection_url": null,
      "status": "connected",
      "last_heartbeat": "2026-05-25T14:09:00Z",
      "created_at": "2026-05-20T10:00:00Z",
      "updated_at": "2026-05-25T14:09:00Z"
    }
  ],
  "total": 3
}
```

---

### POST /sessions/{session_id}/cameras/{camera_id}/connect
Connect a camera to a session.

**Response** (200 OK):
```json
{
  "id": 1,
  "name": "Lane 1 Camera",
  "camera_type": "USB",
  "connection_url": null,
  "status": "connected",
  "last_heartbeat": "2026-05-25T14:10:00Z",
  "created_at": "2026-05-20T10:00:00Z",
  "updated_at": "2026-05-25T14:10:00Z"
}
```

---

### POST /sessions/{session_id}/cameras/{camera_id}/disconnect
Disconnect a camera from a session.

**Response** (200 OK):
```json
{
  "id": 1,
  "name": "Lane 1 Camera",
  "camera_type": "USB",
  "connection_url": null,
  "status": "disconnected",
  "last_heartbeat": "2026-05-25T14:10:00Z",
  "created_at": "2026-05-20T10:00:00Z",
  "updated_at": "2026-05-25T14:10:00Z"
}
```

---

### POST /cameras/{camera_id}/reconnect
Reconnect camera with exponential backoff retry and notification.

**Response** (200 OK):
```json
{
  "camera_id": 1,
  "status": "connected",
  "retry_count": 0,
  "last_attempt": "2026-05-25T14:11:00Z",
  "message": "Camera reconnected successfully"
}
```

**Features** (Pattern #5):
- Exponential backoff: 1s → 2s → 4s → 8s max
- User notification on reconnection
- Automatic retry every 30 seconds if disconnected

---

### POST /sessions/{session_id}/cameras/assign
Assign camera to a session lane.

**Request:**
```json
{
  "camera_id": 1,
  "lane_number": 3
}
```

**Response** (201 Created):
```json
{
  "id": 4,
  "session_id": 1,
  "camera_id": 1,
  "lane_number": 3,
  "assigned_at": "2026-05-25T14:12:00Z"
}
```

**Error Responses**:
- 400: Lane already assigned
- 404: Camera or session not found

---

## Leaderboard Endpoints

### GET /sessions/{session_id}/leaderboard
Get real-time leaderboard with Redis caching (1-minute TTL).

**Query Parameters:**
- `limit`: Max results to return (1-1000, default: 1000)
- `use_cache`: Use cached results if available (default: true)

**Response** (200 OK):
```json
{
  "session_id": 1,
  "total_archers": 24,
  "items": [
    {
      "rank": 1,
      "archer_id": 15,
      "archer_name": "John Smith",
      "lane_number": 3,
      "total_score": 480,
      "round_1_score": 160,
      "round_2_score": 160,
      "round_3_score": 160,
      "arrows_recorded": 18
    },
    {
      "rank": 2,
      "archer_id": 12,
      "archer_name": "Jane Doe",
      "lane_number": 1,
      "total_score": 475,
      "round_1_score": 158,
      "round_2_score": 160,
      "round_3_score": 157,
      "arrows_recorded": 18
    }
  ],
  "cached": true,
  "cache_ttl": 60,
  "last_updated": "2026-05-25T14:10:00Z"
}
```

**Cache Invalidation**:
- Automatically invalidated on events: SCORE_RECORDED, SCORE_VALIDATED
- Manual bypass with `use_cache=false`

---

## Report Endpoints

### POST /sessions/{session_id}/reports
Generate a report in specified format (pdf | csv | json).

**Query Parameters:**
- `format`: pdf | csv | json (default: pdf)

**Response** (200 OK - File Download):
```
Content-Type: application/pdf
Content-Disposition: attachment; filename="session_1_report_20260525.pdf"
```

**Report Contents**:
- Tournament and session information
- Complete leaderboard (all archers, all scores)
- Summary statistics
- Per-archer score breakdown by round

**Error Responses**:
- 400: Invalid format
- 404: Session not found

---

### GET /sessions/{session_id}/reports/{report_type}
Retrieve pre-generated report by type.

**Supported Types**:
- summary: Quick leaderboard snapshot
- detailed: Full score details
- pdf: PDF export
- csv: CSV export
- json: JSON export

---

## Health & Status Endpoints

### GET /health
Basic system health check.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2026-05-25T14:15:00Z",
  "environment": "development"
}
```

---

### GET /health/detailed
Detailed component health check.

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2026-05-25T14:15:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "response_time_ms": 12,
      "pool_size": 5,
      "active_connections": 2
    },
    "cache": {
      "status": "healthy",
      "response_time_ms": 3,
      "memory_usage_mb": 45,
      "connected": true
    },
    "storage": {
      "status": "healthy",
      "available_gb": 8.5,
      "quota_gb": 10,
      "usage_percent": 15
    },
    "threadpool": {
      "status": "healthy",
      "active_threads": 2,
      "max_threads": 8,
      "queue_size": 0
    }
  }
}
```

---

## WebSocket Endpoint

### WebSocket /ws/{session_id}
Real-time event streaming for live session updates.

**Connection:**
```
ws://localhost:8000/api/ws/{session_id}
Authorization: Bearer {access_token}
```

**Subscribed Events**:
- `SCORE_RECORDED`: New score added
- `SCORE_VALIDATED`: Score validated by AI
- `SESSION_STATE_CHANGED`: Session status changed
- `LEADERBOARD_UPDATED`: Leaderboard changed
- `CAMERA_CONNECTED`: Camera connected
- `CAMERA_DISCONNECTED`: Camera disconnected
- `SESSION_CREATED`: New session created

**Message Format:**
```json
{
  "event_type": "SCORE_RECORDED",
  "timestamp": "2026-05-25T14:16:30Z",
  "data": {
    "score_id": 456,
    "session_archer_id": 15,
    "points": 8,
    "zone": 8,
    "round_number": 1,
    "arrow_number": 1
  }
}
```

**Features** (Patterns #3, #6):
- Pattern #3: 30-second grace period for disconnected clients
- Pattern #6: Message batching (100ms window, 10 event max)
- Active connection tracking per session
- Broadcast to all connected clients

**Error Response:**
- 401: Invalid or missing token
- 404: Session not found

---

## Error Response Format

All error responses follow standard format:

```json
{
  "detail": "User not found",
  "status": 404,
  "timestamp": "2026-05-25T14:17:00Z"
}
```

**Standard HTTP Status Codes**:
- 200: OK - Request successful
- 201: Created - Resource created
- 400: Bad Request - Invalid request body/params
- 401: Unauthorized - Missing/invalid authentication
- 403: Forbidden - Insufficient permissions
- 404: Not Found - Resource not found
- 409: Conflict - Resource already exists / state conflict
- 422: Unprocessable Entity - Validation error
- 429: Too Many Requests - Rate limit exceeded (1000 req/min)
- 500: Internal Server Error - Server error
- 501: Not Implemented - Feature not available

---

## Rate Limiting

All endpoints are rate-limited to **1000 requests per minute per IP address**.

**Rate Limit Headers**:
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1653491820
```

**When Exceeded**: Returns 429 Too Many Requests

---

## Authentication

All endpoints except `/auth/register` and `/auth/login` require JWT Bearer token in `Authorization` header:

```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Token Details**:
- Algorithm: HS256
- Expiration: 8 hours (access), 30 days (refresh)
- Issued at: `/auth/login`
- Refresh at: `/auth/refresh`

---

## Security

- **HTTPS Required**: All production endpoints use HTTPS
- **CORS**: Configured for local development (3000, 8080, 5173)
- **Password**: Minimum 8 characters, uppercase + lowercase + digit + symbol
- **Rate Limiting**: 1000 requests/minute per IP
- **JWT Secret**: HS256 with 32+ byte key (set via environment)

---

## Summary Statistics

- **Total REST Endpoints**: 25
- **WebSocket Endpoints**: 1
- **Request Methods**: GET, POST, PATCH, DELETE
- **Authentication Methods**: JWT Bearer
- **Rate Limit**: 1000 req/min per IP
- **Cache**: Redis with 1-minute TTL for leaderboards
- **Database**: PostgreSQL with Alembic migrations
