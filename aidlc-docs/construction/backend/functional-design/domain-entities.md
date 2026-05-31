# Backend Functional Design — Domain Entities

**Project**: Automated Archery Scoring System  
**Unit**: Backend  
**Date**: 2026-05-23  

---

## Entity Relationship Diagram

```
User
  ├─ has many → Tournament (created_by)
  └─ has many → SessionArcher (registered in sessions)

Tournament
  ├─ belongs to → User (created_by)
  ├─ has many → Session
  └─ has many → Camera (assigned to tournament)

Session
  ├─ belongs to → Tournament
  ├─ has many → SessionArcher (archers in session)
  ├─ has many → Score (scores from session)
  ├─ has many → CameraLaneAssignment (cameras used)
  └─ status ∈ {CREATED, STARTED, IN_PROGRESS, COMPLETED}

SessionArcher (join table)
  ├─ belongs to → Session
  ├─ belongs to → User (archer)
  └─ has many → Score (archer's scores in session)

Score
  ├─ belongs to → Session
  ├─ belongs to → User (archer)
  ├─ belongs to → Camera (captured from)
  └─ may reference → Score (if override, links to original)

Camera
  ├─ has many → CameraLaneAssignment
  └─ status ∈ {CONNECTED, DISCONNECTED, ERROR}

CameraLaneAssignment
  ├─ belongs to → Camera
  └─ belongs to → Session
```

---

## Core Entities

### Entity 1: User

**Purpose**: Authentication and role-based access

**Fields**:
| Field | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | UUID | PK | Unique identifier |
| `username` | VARCHAR(255) | UNIQUE, NOT NULL | Login credential |
| `password_hash` | VARCHAR(255) | NOT NULL | Bcrypt-hashed password |
| `role` | ENUM | NOT NULL, default=ARCHER | Permission level (SYSTEM_ADMIN, TOURNAMENT_ADMIN, SCORER, ARCHER) |
| `full_name` | VARCHAR(255) | Optional | Display name |
| `email` | VARCHAR(255) | Optional | Contact |
| `is_active` | BOOLEAN | default=true | Account status |
| `created_at` | TIMESTAMP | NOT NULL | Registration date |
| `updated_at` | TIMESTAMP | NOT NULL | Last update |

**Relationships**:
- Created Tournaments (User → Tournament via created_by)
- Registered in Sessions (User → SessionArcher)
- Scores (User → Score as archer)

**Queries**:
- Find user by username (login)
- List all users with role X
- List archers in tournament

---

### Entity 2: Tournament

**Purpose**: Organize competitive events

**Fields**:
| Field | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | UUID | PK | Unique identifier |
| `name` | VARCHAR(255) | NOT NULL | Tournament name |
| `date` | DATE | NOT NULL | Event date |
| `location` | VARCHAR(255) | Optional | Venue |
| `description` | TEXT | Optional | Event details |
| `created_by_user_id` | UUID | FK (User), NOT NULL | Tournament organizer |
| `status` | ENUM | default=CREATED | (CREATED, IN_PROGRESS, COMPLETED) |
| `created_at` | TIMESTAMP | NOT NULL | Creation date |
| `updated_at` | TIMESTAMP | NOT NULL | Last update |

**Relationships**:
- Sessions (Tournament → Session)
- Created by User
- Cameras (Tournament → Camera)

**Queries**:
- List tournaments by date range
- Get tournament details with sessions

---

### Entity 3: Session

**Purpose**: Organize archers within a tournament into a scoring round

**Fields**:
| Field | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | UUID | PK | Unique identifier |
| `tournament_id` | UUID | FK (Tournament), NOT NULL | Parent tournament |
| `name` | VARCHAR(255) | Optional | Session name (e.g., "Round 1 Novice") |
| `status` | VARCHAR(50) | NOT NULL, default=CREATED | **4 states: CREATED, STARTED, IN_PROGRESS, COMPLETED** |
| `started_at` | TIMESTAMP | Optional | When session started |
| `completed_at` | TIMESTAMP | Optional | When session finished |
| `created_at` | TIMESTAMP | NOT NULL | Creation date |
| `updated_at` | TIMESTAMP | NOT NULL | Last update |
| `last_score_at` | TIMESTAMP | Optional | Timestamp of most recent score (for query optimization) |

**Relationships**:
- Archers (Session ← SessionArcher)
- Scores (Session ← Score)
- Cameras (Session ← CameraLaneAssignment)

**State Transitions**:
```
CREATED ──→ STARTED ──→ IN_PROGRESS ──→ COMPLETED
  (setup)    (ready)     (scoring)      (final)
```

**Queries**:
- Get session details with archers and scores
- List all scores in session
- Get session by tournament + status

---

### Entity 4: SessionArcher (Join Table)

**Purpose**: Track archer participation in sessions

**Fields**:
| Field | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | UUID | PK | Unique identifier |
| `session_id` | UUID | FK (Session), NOT NULL | Session |
| `archer_id` | UUID | FK (User), NOT NULL | Archer user |
| `bib_number` | VARCHAR(50) | NOT NULL, UNIQUE per session | Identification number |
| `registered_at` | TIMESTAMP | NOT NULL | Registration date |
| `status` | VARCHAR(50) | default=READY | (READY, SCORING, SCORED, COMPLETED) |

**Relationships**:
- Scores (SessionArcher ← Score via session + archer)
- User (SessionArcher → User)
- Session (SessionArcher → Session)

**Queries**:
- Get all archers in session
- Get specific archer's status in session
- List archers by bib number

---

### Entity 5: Score

**Purpose**: Store individual arrow scoring results

**Fields**:
| Field | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | UUID | PK | Unique identifier |
| `session_id` | UUID | FK (Session), NOT NULL | Session context |
| `archer_id` | UUID | FK (User), NOT NULL | Archer who shot arrow |
| `camera_id` | UUID | FK (Camera), NOT NULL | Camera used for capture |
| `end_num` | INT | NOT NULL | Round/end number (1, 2, 3, ...) |
| `arrow_num` | INT | NOT NULL (1-3) | Arrow within end (1, 2, or 3) |
| `zone` | INT | NOT NULL (0-10) | Detected zone (11-zone model) |
| `points` | INT | NOT NULL (0-10) | Points awarded |
| `confidence` | FLOAT | NOT NULL (0-100) | Detection confidence (%) |
| `raw_image_path` | VARCHAR(500) | NOT NULL | Path to raw image |
| `annotated_image_path` | VARCHAR(500) | Optional | Path to annotated image |
| `is_override` | BOOLEAN | default=false | Manual override flag |
| `override_reason` | TEXT | Optional | Why overridden |
| `original_score_id` | UUID | Optional | References original if this is override |
| `created_at` | TIMESTAMP | NOT NULL | Scoring timestamp |

**Relationship**:
- If is_override=true: links to previous Score record (self-reference)
- Session, Archer, Camera foreign keys

**Special Queries**:
- Get end score (3 arrows): `SELECT * WHERE session_id=X AND archer_id=Y AND end_num=Z`
- Get archer's total score: `SELECT SUM(points) WHERE session_id=X AND archer_id=Y AND is_override=false`
- Get low-confidence scores: `SELECT * WHERE confidence < 80 AND is_override=false`

**Immutability**: Once inserted, Score records never updated (only overridden with new record)

---

### Entity 6: Camera

**Purpose**: Track physical camera devices

**Fields**:
| Field | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | UUID | PK | Unique identifier |
| `name` | VARCHAR(255) | NOT NULL, UNIQUE | User-friendly name (e.g., "USB Camera 1") |
| `camera_type` | VARCHAR(50) | NOT NULL | USB, RTSP, HTTP_MJPEG |
| `device_id` | VARCHAR(255) | Optional | USB device path or RTSP URL |
| `status` | VARCHAR(50) | default=DISCONNECTED | CONNECTED, DISCONNECTED, ERROR |
| `last_heartbeat` | TIMESTAMP | Optional | Last successful probe |
| `resolution` | VARCHAR(50) | Optional | e.g., "1920x1080" |
| `fps` | FLOAT | Optional | Frames per second capability |
| `created_at` | TIMESTAMP | NOT NULL | Registration date |
| `updated_at` | TIMESTAMP | NOT NULL | Last update |

**Relationships**:
- Assigned to Sessions (Camera ← CameraLaneAssignment)
- Associated with Scores

**Queries**:
- List connected cameras
- Get camera status
- Find camera by device_id

---

### Entity 7: CameraLaneAssignment

**Purpose**: Map cameras to lanes within sessions (1:1 exclusive)

**Fields**:
| Field | Type | Constraints | Purpose |
|---|---|---|---|
| `id` | UUID | PK | Unique identifier |
| `session_id` | UUID | FK (Session), NOT NULL | Session context |
| `lane_number` | INT | NOT NULL | Lane identifier (1-N) |
| `camera_id` | UUID | FK (Camera), NOT NULL, UNIQUE per session | Assigned camera |
| `assigned_at` | TIMESTAMP | NOT NULL | Assignment date |

**Constraint**: One camera per lane (exclusive assignment)
- UNIQUE(session_id, lane_number)
- UNIQUE(session_id, camera_id)

**Relationships**:
- Camera (CameraLaneAssignment → Camera)
- Session (CameraLaneAssignment → Session)

**Queries**:
- Get camera for lane X in session Y
- Get all cameras in session
- Check if camera available (not assigned to other lane in session)

---

## Aggregate Example: SessionWithArchers

**Aggregate**: Session + all related data

```python
class SessionAggregate:
    session: Session
    tournament: Tournament
    archers: List[SessionArcher]  # all archers in session
    scores: List[Score]            # all scores from session
    cameras: List[Camera]          # cameras assigned to lanes
    
    # Computed properties
    @property
    def end_summary(self) -> Dict[int, Dict[str, int]]:
        """Group scores by end"""
        return {
            1: {"archer_1": 25, "archer_2": 28, ...},
            2: {"archer_1": 24, "archer_2": 22, ...},
        }
    
    @property
    def leaderboard(self) -> List[Tuple[str, int]]:
        """Archer rankings by total score"""
        return [("archer_name", 100), ("other_archer", 98), ...]
```

---

## Index Strategy (Performance Optimization)

**Critical Indexes**:
| Table | Index | Purpose |
|---|---|---|
| User | username | Fast login lookup |
| Tournament | created_by_user_id | List user's tournaments |
| Session | tournament_id, status | Filter sessions |
| SessionArcher | session_id, archer_id | Find archer in session |
| Score | session_id, archer_id, end_num | Get archer's end scores |
| Score | created_at | Time-range queries |
| Camera | device_id | Find camera by hardware ID |
| CameraLaneAssignment | session_id, lane_number | Lane lookup |

---

## Validation Constraints

### User
- username length: 3-50 characters
- password length: 8+ characters
- role: must be valid enum value

### Tournament
- name length: 1-255 characters
- date: must be in future (or today)
- created_by_user_id: user must exist

### Session
- tournament_id: tournament must exist
- status: must be valid state
- No state reversions (once COMPLETED, cannot go back)

### SessionArcher
- bib_number: unique within session
- archer_id: user must exist, cannot register same archer twice
- status: valid enum value

### Score
- zone: 0-10 (11 zones)
- points: 0-10 (matches zone)
- arrow_num: 1-3
- end_num: 1-100 (reasonable upper limit)
- confidence: 0-100
- image paths: not empty

### Camera
- camera_type: USB | RTSP | HTTP_MJPEG
- name: unique and non-empty

### CameraLaneAssignment
- camera_id: must be connected
- lane_number: positive integer
- session_id: session must exist

---

## Data Types & Ranges

| Type | Python | SQL | Example |
|---|---|---|---|
| UUID | UUID4 | UUID | `550e8400-e29b-41d4-a716-446655440000` |
| Zone | int | INT | 0-10 |
| Points | int | INT | 0-10 |
| Confidence | float | FLOAT | 0.0-100.0 |
| Status | str (enum) | VARCHAR(50) | "CREATED", "STARTED", etc. |
| DateTime | datetime | TIMESTAMP | 2026-05-23 12:34:56 UTC |
| FilePath | str | VARCHAR(500) | `/storage/raw/session_abc/end_1_arrow_1.jpg` |

---

## Summary: 7 Core Entities

| Entity | Purpose | Primary Key | Key Relations |
|---|---|---|---|
| **User** | Authentication, roles | id (UUID) | Created tournaments, SessionArcher, Score |
| **Tournament** | Event container | id (UUID) | Sessions, Cameras, Created by User |
| **Session** | Scoring round | id (UUID) | SessionArcher, Score, Cameras |
| **SessionArcher** | Archer participation | id (UUID) | Session, User, Score |
| **Score** | Arrow result | id (UUID) | Session, Archer, Camera, (self-ref if override) |
| **Camera** | Hardware device | id (UUID) | CameraLaneAssignment, Score |
| **CameraLaneAssignment** | Lane mapping | id (UUID) | Camera, Session |

