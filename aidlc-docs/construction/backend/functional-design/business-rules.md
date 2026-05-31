# Backend Functional Design — Business Rules

**Project**: Automated Archery Scoring System  
**Unit**: Backend  
**Date**: 2026-05-23  

---

## Overview

This document specifies all business rules, validation logic, constraints, and policies that guide system behavior.

---

## Authentication & Authorization Rules

### Rule AUTH-001: User Login

**Trigger**: User submits credentials (username, password)

**Validation**:
1. Username exists in users table
2. Password matches stored hash (bcrypt comparison)
3. User account is not locked/suspended

**Success**:
- Generate JWT token with:
  - `user_id` (UUID)
  - `role` (SYSTEM_ADMIN | TOURNAMENT_ADMIN | SCORER | ARCHER)
  - `issued_at` (current timestamp)
  - `expires_at` (current + 8 hours)
- Set httpOnly cookie: `Set-Cookie: access_token=<jwt>; HttpOnly; Secure; SameSite=Strict`
- Return token in response body (for client backup)

**Failure**:
- Return 401 Unauthorized
- Do NOT reveal whether username or password wrong (generic message)

**Token Scope**: User-scoped (not session-scoped)
- Valid for 8 hours across all sessions user is enrolled in
- User can switch between sessions without re-auth
- Token refresh: POST /auth/refresh extends expiration

---

### Rule AUTH-002: Token Validation

**Trigger**: Request arrives with Authorization header or httpOnly cookie

**Validation**:
1. Token exists (cookie OR Authorization header)
2. Token format is valid JWT
3. Token signature verifies (secret key match)
4. Token not expired (current_time < expires_at)

**Success**:
- Extract user_id, role from token
- Proceed with request

**Failure**:
- Return 401 Unauthorized
- Clear httpOnly cookie if present
- Suggest re-login

---

### Rule AUTH-003: Role-Based Access Control

**4 Roles with Permissions**:

| Role | Permissions | Typical Users |
|---|---|---|
| **SYSTEM_ADMIN** | Create users, manage system settings, view audit logs | Tournament organizers, IT staff |
| **TOURNAMENT_ADMIN** | Create/edit tournaments, create/start sessions, manage cameras | Tournament directors |
| **SCORER** | Trigger scoring, override scores, view results | Scorers, judges |
| **ARCHER** | View own scores, view leaderboard | Competitors |

**Hybrid Permissions Model**:
- Predefined roles (4 above)
- SYSTEM_ADMIN can assign custom permissions to roles
- Example: TOURNAMENT_ADMIN might also have SCORER permissions (allow full session control)

**Permission Validation**:
```python
@require_role(TOURNAMENT_ADMIN, SCORER)
def trigger_scoring():
    # Only TOURNAMENT_ADMIN and SCORER can access
    pass
```

---

### Rule AUTH-004: Archer Permissions (Own Data Only)

**Constraint**: ARCHER user can only access their own scores

**Enforcement**: API endpoint filter (defense-in-depth tier 1)
- Handler filters response: remove scores where archer_id ≠ current_user_id
- Database query NOT filtered (performance, simplicity)
- Service layer NOT filtered (stateless)

**Example**:
```python
# Request: GET /api/v1/scores/session/{session_id}
# User: ARCHER (archer_id=123)

scores = db.query(Score).filter(Score.session_id == session_id).all()

# Filter by current user
if current_user.role == "ARCHER":
    scores = [s for s in scores if s.archer_id == current_user.id]

return scores  # Only current archer's scores
```

---

## Tournament & Session Rules

### Rule TOUR-001: Tournament Creation

**Who**: TOURNAMENT_ADMIN or SYSTEM_ADMIN

**Required Fields**:
- Name (string, required)
- Date (datetime, required)
- Location (string, optional)
- Description (text, optional)

**Validation**:
- Tournament name must be unique within 30 days of date
- Date must be in future (cannot schedule past tournaments)

**After Creation**:
- Status = CREATED
- Owner = current user

---

### Rule SES-001: Session State Transitions

**Valid State Machine** (Q7 clarification: 4 states):

```
CREATED → STARTED → IN_PROGRESS → COMPLETED
   ↓         ↓            ↓            ↓
(initial) (ready)   (scoring)     (final)
```

**Transitions**:
- CREATED → STARTED: Allowed (when archers registered)
- STARTED → IN_PROGRESS: Automatic (first scoring triggered) or manual
- IN_PROGRESS → COMPLETED: Allowed (tournament director decision)
- Cannot revert (no backward transitions)

**State-Specific Behaviors**:
- **CREATED**: Can add/remove archers, configure cameras
- **STARTED**: Cannot modify archers or cameras, scoring enabled
- **IN_PROGRESS**: Actively scoring
- **COMPLETED**: Read-only, cannot trigger new scoring

---

### Rule SES-002: Archer Registration

**Who**: TOURNAMENT_ADMIN

**Required per Archer**:
- Name (string)
- Bib Number (integer or string)
- Handicap/Skill Level (optional)

**Validation**:
- Bib number must be unique within session
- Name non-empty

**After Registration**:
- Archer added to session_archers table
- Ready for scoring when session starts

---

## Camera Management Rules

### Rule CAM-001: Camera Discovery

**Trigger**: System startup or manual refresh

**Discovery Process**:
1. Enumerate USB cameras via OpenCV (cv2.VideoCapture for device IDs 0-10)
2. Probe RTSP URLs from configuration
3. Test each camera: attempt frame capture (timeout 2 seconds)
4. Update camera status (CONNECTED / DISCONNECTED)

**Automatic Probing**:
- Background task runs every 30 seconds
- Detects disconnected cameras
- Publishes CameraDisconnected event (handled by error recovery)

---

### Rule CAM-002: Camera Lane Assignment

**Constraint**: Each lane must have exactly one camera (exclusive assignment)

**When**: During session setup (CREATED state)

**Validation**:
- Selected camera must be connected (status = CONNECTED)
- Camera can be assigned to only one lane
- All lanes must have cameras before session can start (STARTED state)

**Implications**:
- Cannot have redundant cameras (only primary assigned)
- Cannot have cameraless lanes
- Session requires N cameras for N lanes

---

### Rule CAM-003: Camera Disconnect Handling

**Trigger**: Auto-probe detects camera no longer responds

**Response** (Q15: Retry with adjusted parameters):
1. Log warning: "Camera {id} disconnected"
2. Update camera status to DISCONNECTED
3. Publish CameraDisconnected event
4. Schedule reconnection retry (30s, 60s, 120s, 300s backoff)
5. Attempt reconnection in background

**User Impact**:
- WebSocket broadcasts camera status
- UI shows camera status badge (red for disconnected)
- Scoring disabled for that camera
- User can manually reconnect or wait for auto-retry

---

## Scoring Rules

### Rule SCORE-001: Trigger Scoring

**Who**: SCORER role

**Prerequisites**:
- Session status = STARTED or IN_PROGRESS
- Archer enrolled in session
- Camera assigned and connected
- Archer not already scoring (prevent double-scoring)

**Process**:
1. Capture images from assigned camera
2. Run image processing pipeline
3. Store 3 Score records (one per arrow)
4. Update session state to IN_PROGRESS (if first scoring)
5. Publish ScoreCalculated event
6. Return result to client

**Performance**: < 1 second end-to-end

---

### Rule SCORE-002: Confidence Thresholding

**Scoring Result Classification**:

| Confidence | Status | Action |
|---|---|---|
| ≥ 80% | Accepted | Auto-accept, store result |
| 60-80% | Flagged | Store result, FLAG FOR MANUAL REVIEW (UI shows yellow warning) |
| < 60% | Low | User prompted to retry or override |

**UI Behavior**:
- Confidence ≥ 80%: Green checkmark (accepted)
- 60-80%: Yellow warning (review suggested)
- < 60%: Red error (retry recommended)

---

### Rule SCORE-003: Score Override Validation

**Who**: SCORER role (with optional TOURNAMENT_ADMIN approval for audit)

**When**: Manual override of auto-detected score

**Constraint**: Only if original confidence < 50% (Q9 answer: B)

**Validation**:
- Override only allowed if confidence < 50% (low confidence detection)
- Required field: reason (explanation for override)
- Reason logged in audit trail
- Original and override both stored (immutable history)

**Example Reasons**:
- "Detection failed, arrow clearly in zone 8"
- "Ring detection error, manually corrected"
- "Camera angle issue, adjusted based on slow-motion review"

---

### Rule SCORE-004: Score Immutability

**Once Stored**: Scores never updated, only overridden

**Override Process**:
1. Create new Score record with is_override = true
2. Store original_score_id reference
3. Subsequent queries return override (not original)
4. Audit trail shows both original and override

---

## Concurrency & Database Rules

### Rule CONC-001: Multi-Camera Scoring Locking

**Conflict**: Multiple archers scoring simultaneously on different cameras

**Resolution** (Q16 answer: E - Row locks):
- Use pessimistic row-level locking
- `SELECT ... FOR UPDATE` on Session record before updating
- Only one scoring thread can hold lock
- Others wait (max wait 5 seconds, then timeout)

**Transaction Scope** (Q11 answer: C):
- Atomic: Score inserts + Session state update + Event publish
- All-or-nothing: If any insert fails, entire transaction rolled back

---

### Rule CONC-002: Database Connections

**Connection Pool**:
- SQLAlchemy connection pooling
- Pool size: 10 connections
- Max overflow: 5 (temporary connections beyond pool)
- Timeout: 30 seconds to acquire connection

**Implications**:
- Can handle 4+ concurrent image processing threads
- Database won't be bottleneck for scoring

---

## Image Storage Rules

### Rule IMG-001: Raw Image Storage

**Location**: Filesystem `/storage/raw/`

**Naming Convention**:
- `session_{session_id}/end_{end_num}_arrow_{arrow_num}.jpg`
- Example: `session_abc123/end_1_arrow_1.jpg`

**Format**: JPEG (lossy compression, ~2-5 MB per image depending on resolution)

**Retention**:
- Store for 90 days (configurable)
- After 90 days: archive (compress to tar.gz)
- Archive retention: until 10 GB quota exceeded
- Then: delete oldest archives

**Quota Monitoring**:
- Default: 10 GB
- Warning threshold: 80% (8 GB)
- Alert threshold: 90% (9 GB)
- Admin can configure quota

---

### Rule IMG-002: Annotated Image Generation

**Trigger**: After every scoring (confidence ≥ 60%)

**Content**: Original image + overlays:
- Green circles for detected rings (with radius labels)
- Red dot for detected arrow position
- Zone label + point value text
- Confidence score

**Location**: `/storage/annotated/session_{id}/end_{num}_arrow_{num}_annotated.jpg`

**Purpose**:
- Debugging (verify detection)
- Audit trail (visual record)
- User review

---

## Error Recovery Rules

### Rule ERR-001: Ring Detection Failure

**Scenario**: HoughCircles unable to detect rings (returns empty or nonsensical)

**Recovery** (Q15 answer: B - Retry with adjusted parameters):
1. Log warning
2. Retry #1: Adjust Hough parameters (param2=20, less strict)
3. Retry #2: Try Contour Analysis fallback
4. Failure: Return error, prompt user
5. User option: override manually or retry (same camera/archer)

---

### Rule ERR-002: Camera Disconnect During Scoring

**Scenario**: Camera disconnects mid-pipeline

**Recovery**:
1. Catch exception in image capture
2. Return 500 error to client
3. Publish CameraDisconnected event
4. User retry: capture auto-reconnection, then re-trigger scoring

---

## Authorization Rules (Role-Specific)

### Rule AUTHZ-001: SYSTEM_ADMIN Capabilities

- Create/delete users
- Assign roles to users
- View system audit logs
- Configure system settings (storage quota, retention policy, camera probe interval)
- Override any tournament/session decisions

### Rule AUTHZ-002: TOURNAMENT_ADMIN Capabilities

- Create tournaments
- Create/start sessions within tournament
- Assign cameras to lanes
- Register archers in session
- Override scores (with reason)
- View session reports
- **Cannot**: User management, system settings

### Rule AUTHZ-003: SCORER Capabilities

- Trigger scoring
- Override low-confidence scores (< 50%)
- View scores for current session
- View camera status
- **Cannot**: Create tournaments/sessions, manage users, view across sessions

### Rule AUTHZ-004: ARCHER Capabilities

- View own scores in enrolled sessions
- View leaderboard (current standings)
- **Cannot**: View other archer scores, trigger scoring, create sessions

---

## Data Persistence Rules

### Rule PERSIST-001: Manual SQL Migrations

**Approach** (Q19 answer: A):
- Manual SQL scripts in `/migrations/` directory
- Named: `001_initial_schema.sql`, `002_add_constraints.sql`, etc.
- Run before deployment (admin responsibility)
- No auto-migration (safe, explicit)

**Script Template**:
```sql
-- Migration 001: Initial schema
CREATE TABLE users (
    id UUID PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE cameras (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    camera_type VARCHAR(50),
    status VARCHAR(50) DEFAULT 'DISCONNECTED',
    created_at TIMESTAMP DEFAULT NOW()
);

-- ... more tables
```

---

### Rule PERSIST-002: Testing Database

**Approach** (Q20 answer: B - PostgreSQL test container):
- Use PostgreSQL test container (Docker)
- Closest to production environment
- Schema created from migrations on startup
- Tests run in transactions (rollback after)

**Test Setup**:
```python
@pytest.fixture
def test_db():
    # Start PostgreSQL container
    # Run migrations
    # Create empty database
    yield db
    # Teardown: stop container
```

---

## Summary: 24 Business Rules

| Category | Rules | Key Points |
|---|---|---|
| **Authentication** | AUTH-001 to 004 | JWT tokens, 8h expiration, role-based access |
| **Tournament/Session** | TOUR-001, SES-001/002 | 4-state session machine, archer registration |
| **Cameras** | CAM-001 to 003 | Discovery, lane assignment (1:1), disconnect recovery |
| **Scoring** | SCORE-001 to 004 | Trigger, confidence thresholding, overrides, immutability |
| **Concurrency** | CONC-001/002 | Row locks, atomic transactions, connection pooling |
| **Images** | IMG-001/002 | Filesystem storage, 90-day retention, always annotate |
| **Error Recovery** | ERR-001/002 | Retry ring detection, handle camera disconnect |
| **Authorization** | AUTHZ-001 to 004 | 4-role permissions matrix |
| **Data Persistence** | PERSIST-001/002 | Manual SQL migrations, PostgreSQL tests |

