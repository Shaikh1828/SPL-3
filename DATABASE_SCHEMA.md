# Archery Scoring System - Database Schema

## Overview

PostgreSQL 15+ relational database with 8 core tables and full referential integrity through foreign keys. Optimized for real-time score recording, leaderboard queries, and archery tournament management.

**Database**: archery_db  
**User**: archery  
**Connection Pool**: QueuePool(min_size=5, max_size=20, recycle=3600s)  
**Migrations**: Alembic (versioned schema changes)

---

## Entity Relationship Diagram

```
Users (1) ──────────────┐
   ↓ (creates)          │
   └──→ Tournaments (1) ─┴─────┐
                                ├──→ Sessions (1) ──→ SessionArchers (N)
                                │        ↓ (owns)          ↓
                                │    Cameras ←────────→ CameraLaneAssignments
                                │                            ↓
                                └────────────────────────→ Scores
                                
AuditLog (references User + Entity)
```

---

## Table Schemas

### 1. users

User accounts with role-based access control.

```sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) NOT NULL UNIQUE,
  email VARCHAR(120) NOT NULL UNIQUE,
  password_hash VARCHAR(255) NOT NULL,
  role VARCHAR(20) NOT NULL,
  is_active BOOLEAN DEFAULT TRUE,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_users_username (username),
  INDEX idx_users_email (email)
);
```

**Columns**:
- `id`: Unique user identifier
- `username`: 3-32 characters, letters/numbers/underscore, unique
- `email`: Valid email format, unique
- `password_hash`: bcrypt hashed password (never stored plaintext)
- `role`: admin | scorer | spectator | archer
- `is_active`: Account status (false = disabled)
- `created_at`: Account creation timestamp (UTC)
- `updated_at`: Last modification timestamp (UTC)

**Indexes**:
- PRIMARY KEY: id
- UNIQUE: username, email
- SEARCH: idx_users_username, idx_users_email

**Sample Data**:
```sql
INSERT INTO users VALUES 
  (1, 'admin', 'admin@archery.local', '$2b$12$...', 'admin', TRUE, ...),
  (2, 'scorer_alice', 'alice@archery.local', '$2b$12$...', 'scorer', TRUE, ...),
  (3, 'spectator_bob', 'bob@archery.local', '$2b$12$...', 'spectator', TRUE, ...),
  (4, 'archer_john', 'john@archery.local', '$2b$12$...', 'archer', TRUE, ...);
```

---

### 2. tournaments

Archery tournament definitions with date range and location.

```sql
CREATE TABLE tournaments (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  location VARCHAR(200),
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  created_by INTEGER NOT NULL,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  FOREIGN KEY (created_by) REFERENCES users(id),
  INDEX idx_tournaments_created_by (created_by),
  INDEX idx_tournaments_start_date (start_date),
  CHECK (end_date >= start_date)
);
```

**Columns**:
- `id`: Unique tournament identifier
- `name`: Tournament name (e.g., "Spring Championship 2026")
- `description`: Optional tournament details
- `location`: Venue information
- `start_date`: Tournament start date (no time)
- `end_date`: Tournament end date (must be >= start_date)
- `created_by`: Foreign key to users.id (who created tournament)
- `created_at`: Creation timestamp
- `updated_at`: Last modification timestamp

**Relationships**:
- created_by → users(id): Tournament creator must exist

**Indexes**:
- PRIMARY KEY: id
- SEARCH: idx_tournaments_created_by, idx_tournaments_start_date

**Sample Data**:
```sql
INSERT INTO tournaments VALUES 
  (1, 'Spring Championship 2026', '...', 'Olympic Park', 
   '2026-06-01', '2026-06-03', 1, ...),
  (2, 'Summer Qualifier 2026', '...', 'Central Arena', 
   '2026-07-10', '2026-07-12', 1, ...);
```

---

### 3. sessions

Scoring rounds (sessions) within tournaments.

```sql
CREATE TABLE sessions (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  tournament_id INTEGER NOT NULL,
  name VARCHAR(100) NOT NULL,
  round_number INTEGER NOT NULL,
  status VARCHAR(20) DEFAULT 'active',
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  num_lanes INTEGER DEFAULT 6,
  arrows_per_round INTEGER DEFAULT 6,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  FOREIGN KEY (tournament_id) REFERENCES tournaments(id),
  INDEX idx_sessions_tournament_id (tournament_id),
  INDEX idx_sessions_status (status),
  UNIQUE KEY unique_tournament_round (tournament_id, round_number),
  CHECK (status IN ('active', 'paused', 'completed')),
  CHECK (end_time IS NULL OR end_time >= start_time)
);
```

**Columns**:
- `id`: Unique session identifier
- `tournament_id`: Foreign key to tournaments.id
- `name`: Session name (e.g., "Round 1 - Morning")
- `round_number`: Sequential round within tournament (1, 2, 3...)
- `status`: active | paused | completed
- `start_time`: Session start timestamp (UTC, nullable)
- `end_time`: Session end timestamp (UTC, nullable, must be >= start_time)
- `num_lanes`: Number of shooting lanes (default 6)
- `arrows_per_round`: Arrows per archer per round (default 6)
- `created_at`: Creation timestamp
- `updated_at`: Last modification timestamp

**Relationships**:
- tournament_id → tournaments(id): Session must belong to tournament

**Constraints**:
- UNIQUE(tournament_id, round_number): Only one round per number per tournament
- status must be one of: active, paused, completed
- end_time >= start_time (if both present)

**Indexes**:
- PRIMARY KEY: id
- SEARCH: idx_sessions_tournament_id, idx_sessions_status

**Sample Data**:
```sql
INSERT INTO sessions VALUES 
  (1, 1, 'Round 1 - Morning', 1, 'active', '2026-06-01 08:00:00', NULL, 6, 6, ...),
  (2, 1, 'Round 2 - Afternoon', 2, 'active', '2026-06-01 14:00:00', NULL, 6, 6, ...);
```

---

### 4. session_archers

Archers participating in sessions (one record per archer per session).

```sql
CREATE TABLE session_archers (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  session_id INTEGER NOT NULL,
  archer_name VARCHAR(100) NOT NULL,
  lane_number INTEGER,
  total_score INTEGER DEFAULT 0,
  registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  INDEX idx_session_archers_session_id (session_id),
  INDEX idx_session_archers_lane (lane_number),
  UNIQUE KEY unique_session_lane (session_id, lane_number)
);
```

**Columns**:
- `id`: Unique session-archer record identifier
- `session_id`: Foreign key to sessions.id
- `archer_name`: Archer's name (e.g., "John Smith")
- `lane_number`: Assigned shooting lane (1-6, typically)
- `total_score`: Accumulated score for session (computed, default 0)
- `registered_at`: Archer registration timestamp

**Relationships**:
- session_id → sessions(id): Archer must register in existing session

**Constraints**:
- UNIQUE(session_id, lane_number): Only one archer per lane per session

**Indexes**:
- PRIMARY KEY: id
- SEARCH: idx_session_archers_session_id, idx_session_archers_lane

**Sample Data**:
```sql
INSERT INTO session_archers VALUES 
  (1, 1, 'John Smith', 1, 0, ...),
  (2, 1, 'Jane Doe', 2, 0, ...),
  (3, 1, 'Bob Johnson', 3, 0, ...);
```

---

### 5. scores

Individual arrow scores with zone/points, images, and AI validation.

```sql
CREATE TABLE scores (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  session_id INTEGER NOT NULL,
  session_archer_id INTEGER NOT NULL,
  round_number INTEGER NOT NULL,
  arrow_number INTEGER NOT NULL,
  zone INTEGER NOT NULL,
  points INTEGER NOT NULL,
  image_path VARCHAR(255),
  validated_by_ai BOOLEAN DEFAULT FALSE,
  confidence FLOAT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (session_archer_id) REFERENCES session_archers(id),
  INDEX idx_scores_session_id (session_id),
  INDEX idx_scores_session_archer_id (session_archer_id),
  INDEX idx_scores_round_arrow (round_number, arrow_number),
  CHECK (zone >= 0 AND zone <= 10),
  CHECK (points >= 0 AND points <= 10),
  CHECK (confidence >= 0.0 AND confidence <= 1.0),
  CHECK (arrow_number >= 1 AND arrow_number <= 6)
);
```

**Columns**:
- `id`: Unique score record identifier
- `session_id`: Foreign key to sessions.id
- `session_archer_id`: Foreign key to session_archers.id
- `round_number`: Round number (1, 2, 3...)
- `arrow_number`: Arrow sequence (1-6 per round)
- `zone`: Target zone (0-10, center is 10)
- `points`: Points awarded (0-10, typically matches zone)
- `image_path`: Path to captured arrow image (nullable)
- `validated_by_ai`: Whether AI validated this score (boolean)
- `confidence`: AI confidence score (0.0-1.0, nullable)
- `created_at`: Score recording timestamp
- `updated_at`: Last modification timestamp

**Relationships**:
- session_id → sessions(id): Score belongs to session
- session_archer_id → session_archers(id): Score belongs to archer in session

**Constraints**:
- zone: 0-10
- points: 0-10
- confidence: 0.0-1.0 (if present)
- arrow_number: 1-6

**Indexes**:
- PRIMARY KEY: id
- SEARCH: idx_scores_session_id, idx_scores_session_archer_id
- COMPOSITE: idx_scores_round_arrow (for leaderboard queries)

**Sample Data**:
```sql
INSERT INTO scores VALUES 
  (1, 1, 1, 1, 1, 8, 8, '/storage/raw/1/arrow_001.jpg', FALSE, 0.85, ...),
  (2, 1, 1, 1, 2, 9, 9, '/storage/raw/1/arrow_002.jpg', TRUE, 0.92, ...),
  (3, 1, 1, 1, 3, 7, 7, '/storage/raw/1/arrow_003.jpg', FALSE, 0.78, ...);
```

---

### 6. cameras

Camera devices for arrow detection (USB, RTSP, HTTP).

```sql
CREATE TABLE cameras (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  camera_type VARCHAR(20) NOT NULL,
  connection_url VARCHAR(255),
  status VARCHAR(20) DEFAULT 'disconnected',
  last_heartbeat TIMESTAMP,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  
  INDEX idx_cameras_status (status),
  CHECK (camera_type IN ('USB', 'RTSP', 'HTTP')),
  CHECK (status IN ('connected', 'disconnected', 'error'))
);
```

**Columns**:
- `id`: Unique camera identifier
- `name`: Camera name (e.g., "Lane 1 Camera")
- `camera_type`: USB | RTSP | HTTP
- `connection_url`: Connection string (nullable for USB)
- `status`: connected | disconnected | error
- `last_heartbeat`: Last successful connection ping (UTC timestamp)
- `created_at`: Camera registration timestamp
- `updated_at`: Last modification timestamp

**Constraints**:
- camera_type must be: USB, RTSP, or HTTP
- status must be: connected, disconnected, or error

**Indexes**:
- PRIMARY KEY: id
- SEARCH: idx_cameras_status

**Sample Data**:
```sql
INSERT INTO cameras VALUES 
  (1, 'Lane 1 Camera', 'USB', NULL, 'connected', '2026-05-25 14:15:00', ...),
  (2, 'Lane 2 Camera', 'RTSP', 'rtsp://192.168.1.10:554/stream', 'connected', '2026-05-25 14:15:00', ...),
  (3, 'Lane 3 Camera', 'HTTP', 'http://192.168.1.11:8080/video', 'disconnected', NULL, ...);
```

---

### 7. camera_lane_assignments

Assignment of cameras to session lanes (many-to-many bridge).

```sql
CREATE TABLE camera_lane_assignments (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  session_id INTEGER NOT NULL,
  camera_id INTEGER NOT NULL,
  lane_number INTEGER NOT NULL,
  assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (camera_id) REFERENCES cameras(id),
  INDEX idx_camera_assignments_session_lane (session_id, lane_number),
  UNIQUE KEY unique_session_lane_camera (session_id, lane_number, camera_id)
);
```

**Columns**:
- `id`: Unique assignment record identifier
- `session_id`: Foreign key to sessions.id
- `camera_id`: Foreign key to cameras.id
- `lane_number`: Target lane number
- `assigned_at`: Assignment timestamp

**Relationships**:
- session_id → sessions(id): Assignment within session
- camera_id → cameras(id): Camera being assigned

**Constraints**:
- UNIQUE(session_id, lane_number, camera_id): Prevent duplicate assignments

**Indexes**:
- PRIMARY KEY: id
- SEARCH: idx_camera_assignments_session_lane

**Sample Data**:
```sql
INSERT INTO camera_lane_assignments VALUES 
  (1, 1, 1, 1, '2026-05-25 08:00:00'),
  (2, 1, 2, 2, '2026-05-25 08:00:00'),
  (3, 1, 3, 3, '2026-05-25 08:00:00');
```

---

### 8. audit_logs

Activity audit trail for compliance and debugging.

```sql
CREATE TABLE audit_logs (
  id INTEGER PRIMARY KEY AUTO_INCREMENT,
  user_id INTEGER,
  action VARCHAR(100) NOT NULL,
  entity_type VARCHAR(50) NOT NULL,
  entity_id INTEGER,
  details TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  
  FOREIGN KEY (user_id) REFERENCES users(id),
  INDEX idx_audit_logs_user_id (user_id),
  INDEX idx_audit_logs_action (action),
  INDEX idx_audit_logs_created_at (created_at)
);
```

**Columns**:
- `id`: Unique audit log record identifier
- `user_id`: Foreign key to users.id (nullable for system actions)
- `action`: Action type (e.g., "SCORE_RECORDED", "SESSION_STARTED")
- `entity_type`: Entity type (e.g., "Score", "Session", "User")
- `entity_id`: ID of affected entity (nullable for batch actions)
- `details`: Additional JSON or text details
- `created_at`: Action timestamp (UTC)

**Relationships**:
- user_id → users.id: User performing action (nullable for system)

**Indexes**:
- PRIMARY KEY: id
- SEARCH: idx_audit_logs_user_id, idx_audit_logs_action, idx_audit_logs_created_at

**Sample Data**:
```sql
INSERT INTO audit_logs VALUES 
  (1, 2, 'SCORE_RECORDED', 'Score', 1, '{"zone":8,"points":8}', '2026-05-25 14:05:00'),
  (2, 2, 'SESSION_STARTED', 'Session', 1, '{"round":1}', '2026-05-25 08:00:00'),
  (3, 1, 'USER_REGISTERED', 'User', 4, '{"role":"archer"}', '2026-05-25 10:00:00');
```

---

## Query Patterns

### Leaderboard (by total score, per session)
```sql
SELECT 
  ROW_NUMBER() OVER (ORDER BY SUM(s.points) DESC) as rank,
  sa.archer_name,
  sa.lane_number,
  SUM(s.points) as total_score,
  COUNT(*) as arrows_recorded
FROM session_archers sa
LEFT JOIN scores s ON sa.id = s.session_archer_id
WHERE sa.session_id = ?
GROUP BY sa.id, sa.archer_name, sa.lane_number
ORDER BY total_score DESC;
```

### Average Score by Round
```sql
SELECT 
  s.round_number,
  AVG(s.points) as avg_points,
  COUNT(*) as total_arrows
FROM scores s
WHERE s.session_id = ?
GROUP BY s.round_number
ORDER BY s.round_number;
```

### Active Sessions with Archer Count
```sql
SELECT 
  s.id,
  s.name,
  COUNT(DISTINCT sa.id) as archer_count,
  COUNT(DISTINCT sc.id) as score_count
FROM sessions s
LEFT JOIN session_archers sa ON s.id = sa.session_id
LEFT JOIN scores sc ON sa.id = sc.session_archer_id
WHERE s.status = 'active'
GROUP BY s.id, s.name;
```

### Audit Trail for Entity
```sql
SELECT * FROM audit_logs
WHERE entity_type = 'Score' AND entity_id = ?
ORDER BY created_at DESC;
```

---

## Indexing Strategy

**Primary Indexes** (automatically created on PRIMARY KEY):
- users.id
- tournaments.id
- sessions.id
- session_archers.id
- scores.id
- cameras.id
- camera_lane_assignments.id
- audit_logs.id

**Search Indexes** (for common queries):
- users.username, users.email
- tournaments.created_by, tournaments.start_date
- sessions.tournament_id, sessions.status
- session_archers.session_id, session_archers.lane_number
- scores.session_id, scores.session_archer_id, (round_number, arrow_number)
- cameras.status
- camera_lane_assignments.session_id + lane_number
- audit_logs.user_id, audit_logs.action, audit_logs.created_at

**Unique Constraints** (prevent duplicates):
- users.username, users.email
- tournaments.id (implicit)
- sessions.(tournament_id, round_number)
- session_archers.(session_id, lane_number)
- camera_lane_assignments.(session_id, lane_number, camera_id)

---

## Performance Considerations

- **Connection Pooling**: QueuePool(min_size=5, max_size=20) reuses connections
- **Connection Recycling**: 3600-second recycle prevents stale connections
- **Indexes**: All JOIN columns and common WHERE clauses indexed
- **Leaderboard Cache**: Redis 1-minute TTL for /leaderboard queries (avoids SELECT on every request)
- **Composite Index**: (round_number, arrow_number) for fast score lookups
- **Foreign Key Cascade**: ON DELETE CASCADE ensures orphaned records cleaned up

---

## Data Types & Constraints

- **VARCHAR(50)**: Usernames, short strings
- **VARCHAR(100)**: Names, short text
- **VARCHAR(255)**: URLs, file paths
- **TEXT**: Long descriptions, details
- **INTEGER**: IDs, counts, zones (0-10), points (0-10)
- **BOOLEAN**: Flags (is_active, validated_by_ai)
- **FLOAT**: Confidence scores (0.0-1.0)
- **DATE**: Date-only fields (tournament start/end)
- **TIMESTAMP**: All timestamps (UTC, with timezone awareness)
- **TIMESTAMP DEFAULT CURRENT_TIMESTAMP**: Auto-populated on INSERT
- **TIMESTAMP ON UPDATE CURRENT_TIMESTAMP**: Auto-populated on UPDATE

---

## Constraints Summary

```sql
-- NOT NULL constraints
tournament.start_date, tournament.end_date, tournament.created_by
sessions.tournament_id, sessions.round_number, sessions.name
session_archers.session_id, session_archers.archer_name
scores.session_id, scores.session_archer_id, scores.zone, scores.points
cameras.name, cameras.camera_type
camera_lane_assignments.session_id, camera_lane_assignments.camera_id
audit_logs.action, audit_logs.entity_type

-- UNIQUE constraints
users.username, users.email
tournaments.id
sessions.(tournament_id, round_number)
session_archers.(session_id, lane_number)
camera_lane_assignments.(session_id, lane_number, camera_id)

-- FOREIGN KEY constraints
tournaments.created_by → users.id
sessions.tournament_id → tournaments.id
session_archers.session_id → sessions.id
scores.session_id → sessions.id
scores.session_archer_id → session_archers.id
camera_lane_assignments.session_id → sessions.id
camera_lane_assignments.camera_id → cameras.id
audit_logs.user_id → users.id

-- CHECK constraints
tournament.end_date >= start_date
sessions.status IN ('active', 'paused', 'completed')
sessions.end_time >= start_time (if both present)
scores.zone IN (0-10)
scores.points IN (0-10)
scores.arrow_number IN (1-6)
scores.confidence IN (0.0-1.0) if present
cameras.camera_type IN ('USB', 'RTSP', 'HTTP')
cameras.status IN ('connected', 'disconnected', 'error')
```
