# Unit of Work Story Map

**Project**: Automated Archery Scoring System  
**Date**: 2026-05-23  

---

## Story Assignment Strategy

**Principle**: Stories are assigned to the unit with the critical path (Backend-heavy for hybrid stories).

**Mapping**:
- **Backend Stories**: Stories where primary implementation is Backend (services, database, API)
- **Frontend Stories**: Stories where primary implementation is Frontend (UI, state, forms)
- **Cross-Unit Stories**: Stories that require both units; marked with cross-unit dependencies

---

## Phase 1: Essential Stories (18 total)

### Authentication Feature (3 stories)

| Story ID | Title | Description | Primary Unit | Secondary Unit | Dependencies | Phase |
|---|---|---|---|---|---|---|
| USR-001 | User Login | User logs in with credentials | **Backend** | Frontend | None | Phase 1 |
| USR-002 | User Logout | User logs out and clears session | **Backend** | Frontend | USR-001 | Phase 1 |
| USR-003 | Session Refresh | Session auto-refreshes before expiration | **Backend** | Frontend | USR-001 | Phase 1 |

**Backend Responsibilities**:
- Validate credentials
- Generate JWT tokens (8-hour expiration)
- Implement refresh endpoint
- Set httpOnly cookies
- Store user roles in token

**Frontend Responsibilities**:
- Render login form
- Handle login submission
- Display login errors
- Redirect after successful login
- Store user info in Zustand

**Cross-Unit Dependency**: USR-001 requires Backend API and Frontend UI both ready before testing

---

### Camera Management Feature (3 stories)

| Story ID | Title | Description | Primary Unit | Secondary Unit | Dependencies | Phase |
|---|---|---|---|---|---|---|
| CAM-001 | Camera Discovery | System auto-discovers USB/RTSP cameras | **Backend** | Frontend | USR-001 | Phase 1 |
| CAM-002 | Camera Configuration | Admin configures camera settings (RTSP URL, resolution) | **Backend** | Frontend | CAM-001 | Phase 1 |
| CAM-003 | Live Preview | Live camera feed displays in UI (15 fps MJPEG) | **Frontend** | Backend | CAM-001 | Phase 1 |

**Backend Responsibilities**:
- Enumerate USB cameras via OpenCV
- Probe RTSP URLs for connectivity
- Store camera configuration in DB
- Start auto-discovery in background (30s polling)
- Publish camera status events

**Frontend Responsibilities**:
- Display list of discovered cameras
- Show camera configuration form
- Render live preview (MJPEG over WebSocket)
- Show connection status (green/red indicator)
- Handle camera disconnection gracefully

**Cross-Unit Dependency**: CAM-003 requires both WebSocket implementation and Frontend preview component ready together

---

### Tournament & Session Management (4 stories)

| Story ID | Title | Description | Primary Unit | Secondary Unit | Dependencies | Phase |
|---|---|---|---|---|---|---|
| TOUR-001 | Create Tournament | TOURNAMENT_ADMIN creates a tournament | **Backend** | Frontend | USR-001 | Phase 1 |
| TOUR-002 | Manage Sessions | Admin creates and manages sessions within tournament | **Backend** | Frontend | TOUR-001 | Phase 1 |
| SES-001 | Register Archers | Archers register for session (name, bib number) | **Frontend** | Backend | TOUR-002 | Phase 1 |
| SES-002 | Start Session | TOURNAMENT_ADMIN starts session (enables scoring) | **Backend** | Frontend | SES-001 | Phase 1 |

**Backend Responsibilities**:
- Create tournament records (name, date, metadata)
- Create session records (tournament reference, status tracking)
- Register archer records (name, bib, session reference)
- Implement state machine (session: created → started → completed)
- Publish session events (started, completed)

**Frontend Responsibilities**:
- Display tournament creation form
- Display tournament list
- Display session creation form
- Display archer registration form
- Show current session state
- Handle session transitions (UI feedback)

**Cross-Unit Dependency**: SES-001 requires frontend form + backend archer registration endpoint both ready

---

### Core Scoring Feature (6 stories)

| Story ID | Title | Description | Primary Unit | Secondary Unit | Dependencies | Phase |
|---|---|---|---|---|---|---|
| SCORE-001 | Trigger Scoring | Scorer captures images and triggers scoring pipeline | **Backend** | Frontend | CAM-001 + SES-002 | Phase 1 |
| SCORE-002 | Display Scores | Scores display in real-time on leaderboard | **Frontend** | Backend | SCORE-001 | Phase 1 |
| SCORE-003 | Override Scores | Scorer manually overrides specific arrow scores with reason | **Backend** | Frontend | SCORE-001 | Phase 1 |
| SCORE-004 | Score History | Archer can view their score history (all ends/rounds) | **Frontend** | Backend | SCORE-001 | Phase 1 |
| SCORE-005 | Confidence Display | Scoring pipeline shows confidence scores for detected arrows | **Backend** | Frontend | SCORE-001 | Phase 1 |
| SCORE-006 | Multi-Camera Scoring | System handles 4+ simultaneous cameras (parallel processing) | **Backend** | Frontend | SCORE-001 | Phase 1 |

**Backend Responsibilities**:
- Implement image processing pipeline (capture → preprocess → detect → score)
- Use ThreadPool for multi-camera parallelism
- Implement all detection methods (5 ring detection, arrow detection)
- Calculate scores (zone-to-points mapping)
- Implement override endpoint with reason audit trail
- Publish score events (real-time broadcast)
- Target: < 1 second end-to-end

**Frontend Responsibilities**:
- Display scoring interface (camera preview + trigger button)
- Show score confirmation (zones, total)
- Display live leaderboard (real-time updates via WebSocket)
- Show confidence scores
- Implement score override form
- Show score history for selected archer
- Display multi-camera status indicators

**Cross-Unit Dependencies**:
- SCORE-001 critical: Image processing pipeline must be performant
- SCORE-002 critical: WebSocket event broadcasting must be real-time
- SCORE-003 requires API endpoint + form components

---

### Reporting Feature (2 stories)

| Story ID | Title | Description | Primary Unit | Secondary Unit | Dependencies | Phase |
|---|---|---|---|---|---|---|
| RPT-001 | Generate Reports | Reports in PDF, CSV, JSON formats | **Backend** | Frontend | SCORE-001 | Phase 1 |
| RPT-002 | Leaderboard | Display final leaderboard with rankings | **Frontend** | Backend | SCORE-001 | Phase 1 |

**Backend Responsibilities**:
- Query session scores and calculations
- Generate PDF reports (via WeasyPrint)
- Generate CSV exports
- Generate JSON data exports
- Implement leaderboard query (rankings, scores)
- Target: < 2 seconds for report generation

**Frontend Responsibilities**:
- Display report generation form (format selection)
- Handle report download
- Display leaderboard table with rankings
- Sort/filter leaderboard
- Implement data visualization (Recharts)

**Cross-Unit Dependency**: Report data must be queryable; frontend must handle download/display

---

### Real-Time Features (1 story - spans both)

| Story ID | Title | Description | Primary Unit | Secondary Unit | Dependencies | Phase |
|---|---|---|---|---|---|---|
| RT-001 | Real-Time Updates | Live score broadcasts, camera status, session events | **Backend** | Frontend | SCORE-001 + CAM-001 | Phase 1 |

**Backend Responsibilities**:
- Implement EventBus (publish/subscribe)
- Publish domain events (ScoreCalculated, CameraDisconnected, SessionStarted)
- Implement WebSocket server
- Broadcast events to connected clients
- Target: < 100ms delivery

**Frontend Responsibilities**:
- Connect to WebSocket
- Listen for events
- Update Zustand store on event
- Trigger component re-renders
- Handle WebSocket reconnection

**Cross-Unit Dependency**: Critical integration point; both units must be ready simultaneously

---

### Permissions & Authorization (1 story)

| Story ID | Title | Description | Primary Unit | Secondary Unit | Dependencies | Phase |
|---|---|---|---|---|---|---|
| PERM-001 | Role-Based Access | Users see features based on role (4 roles) | **Backend** | Frontend | USR-001 | Phase 1 |

**Backend Responsibilities**:
- Implement 4-role RBAC (SYSTEM_ADMIN, TOURNAMENT_ADMIN, SCORER, ARCHER)
- Add role-based decorators to all endpoints
- Implement object-level permission checks (archer sees own scores only)
- Return 403 Forbidden for unauthorized requests

**Frontend Responsibilities**:
- Show/hide UI elements based on user role
- Disable buttons for users without permission
- Display permission denied messages
- Redirect to appropriate pages based on role

**Cross-Unit Dependency**: Backend enforces permissions (primary); Frontend respects (secondary)

---

### Error Recovery (1 story)

| Story ID | Title | Description | Primary Unit | Secondary Unit | Dependencies | Phase |
|---|---|---|---|---|---|---|
| ERR-001 | Camera Disconnect Recovery | Auto-reconnect when camera disconnects | **Backend** | Frontend | CAM-001 | Phase 1 |

**Backend Responsibilities**:
- Detect camera disconnections (auto-probe fails)
- Implement retry logic (exponential backoff)
- Update camera status in DB
- Publish CameraDisconnected event
- Attempt reconnection in background

**Frontend Responsibilities**:
- Listen for CameraDisconnected event
- Show red badge "Reconnecting..."
- Disable scoring if camera essential
- Notify user of reconnection

**Cross-Unit Dependency**: Event-driven flow requires both units ready

---

### Performance Optimization (1 story)

| Story ID | Title | Description | Primary Unit | Secondary Unit | Dependencies | Phase |
|---|---|---|---|---|---|---|
| PERF-001 | Scoring Performance | Scoring pipeline completes in < 1 second | **Backend** | Frontend | SCORE-001 | Phase 1 |

**Backend Responsibilities**:
- Optimize image processing algorithms
- Use threading for multi-camera parallelism
- Monitor query performance (< 200ms API calls)
- Implement caching where appropriate
- Profile and optimize bottlenecks

**Frontend Responsibilities**:
- Show loading spinner during scoring (user expects ~1s wait)
- Implement request timeout (if > 3s, show error)
- Optimize component rendering (memoization, lazy loading)

**Cross-Unit Dependency**: Frontend UI responsiveness depends on Backend performance

---

### Data Retention (1 story)

| Story ID | Title | Description | Primary Unit | Secondary Unit | Dependencies | Phase |
|---|---|---|---|---|---|---|
| DATA-001 | Retention & Archive | Auto-archive data > 90 days; 10 GB quota | **Backend** | Frontend | SCORE-001 | Phase 1 |

**Backend Responsibilities**:
- Monitor storage usage (warning at 80%, alert at 90%)
- Archive data > 90 days (compress, move to separate storage)
- Delete images when quota exceeded
- Log retention actions (audit trail)
- Implement quota enforcement

**Frontend Responsibilities**:
- Display storage usage indicator
- Show warnings/alerts to admin
- Display archive status

**Cross-Unit Dependency**: Backend implements policy; Frontend shows status

---

## Phase 2: Desirable Stories (3 total)

### Enhancements

| Story ID | Title | Description | Primary Unit | Secondary Unit | Dependencies | Phase |
|---|---|---|---|---|---|---|
| ENH-001 | Advanced Analytics | Trend analysis, performance metrics | **Frontend** | Backend | RPT-001 | Phase 2 |
| ENH-002 | Export to External Systems | Push scores to tournament management system | **Backend** | Frontend | RPT-001 | Phase 2 |
| ENH-003 | Custom Scoring Zones | Admin defines custom zone mappings | **Backend** | Frontend | SCORE-001 | Phase 2 |

These stories are marked **Desirable** (not essential for first release). Implementation starts after Phase 1 completion if time permits.

---

## Story Count by Unit

| Unit | Phase 1 | Phase 2 | Total |
|---|---|---|---|
| **Backend** | 11 | 2 | 13 |
| **Frontend** | 7 | 1 | 8 |
| **Total** | 18 | 3 | 21 |

**Note**: Story counts reflect primary unit assignment. Many stories require both units' collaboration (cross-unit dependencies).

---

## Story Dependencies & Sequencing

### Dependency Graph (Simplified)

```
USR-001 (Login)
  ├─ CAM-001 (Camera Discovery)
  │   ├─ CAM-002 (Camera Config)
  │   ├─ CAM-003 (Live Preview)
  │   └─ ERR-001 (Camera Recovery)
  ├─ TOUR-001 (Create Tournament)
  │   ├─ TOUR-002 (Manage Sessions)
  │   │   ├─ SES-001 (Register Archers)
  │   │   └─ SES-002 (Start Session)
  │   │       ├─ SCORE-001 (Trigger Scoring)
  │   │       │   ├─ SCORE-002 (Display Scores)
  │   │       │   ├─ SCORE-003 (Override Scores)
  │   │       │   ├─ SCORE-004 (Score History)
  │   │       │   ├─ SCORE-005 (Confidence Display)
  │   │       │   ├─ SCORE-006 (Multi-Camera)
  │   │       │   ├─ RPT-001 (Reports)
  │   │       │   ├─ RPT-002 (Leaderboard)
  │   │       │   ├─ RT-001 (Real-Time Updates)
  │   │       │   ├─ PERF-001 (Scoring Performance)
  │   │       │   └─ DATA-001 (Data Retention)
  ├─ PERM-001 (Role-Based Access)
  └─ USR-002 (Logout)
      └─ USR-003 (Session Refresh)
```

### Execution Order (Recommended)

**Week 1**:
1. USR-001 (Login) — Foundation; both units depend on
2. TOUR-001 (Tournament creation) — Core domain
3. PERM-001 (RBAC) — Security foundation

**Week 2**:
4. CAM-001 (Camera discovery) — Hardware integration
5. CAM-002 (Camera config) — Setup
6. CAM-003 (Live preview) — Real-time first step
7. TOUR-002 (Session management) — Domain continuation

**Week 3**:
8. SES-001 (Archer registration) → SES-002 (Start session)
9. SCORE-001 (Trigger scoring) — Main value delivery
10. SCORE-002 (Display scores) — Real-time leaderboard
11. RT-001 (Real-time updates) — Integrate WebSocket

**Week 4**:
12. SCORE-003 (Override) → SCORE-004 (History)
13. SCORE-005 (Confidence) → SCORE-006 (Multi-camera)
14. RPT-001 (Reports) → RPT-002 (Leaderboard)

**Week 5** (if time):
15. ERR-001 (Camera recovery) — Error handling
16. PERF-001 (Performance) — Optimization
17. DATA-001 (Retention) — Operations
18. Phase 2 stories (if applicable)

---

## Test Scenarios by Unit

### Backend Test Scenarios
- ✅ Login with valid/invalid credentials
- ✅ Token refresh before expiration
- ✅ Camera enumeration and connection testing
- ✅ Image processing pipeline (< 1s)
- ✅ Score calculation accuracy
- ✅ Multi-camera parallel processing
- ✅ Score override with audit trail
- ✅ Real-time event broadcasting
- ✅ Permission enforcement (403 on unauthorized)
- ✅ Data retention and archival

### Frontend Test Scenarios
- ✅ Login flow (form submit, error display, redirect)
- ✅ Camera preview displays live feed
- ✅ Scoring interface shows results
- ✅ Real-time leaderboard updates on new scores
- ✅ Score history displays all archer ends
- ✅ Report download works (PDF, CSV, JSON)
- ✅ Role-based UI (features hidden for unauthorized roles)
- ✅ Error messages display correctly
- ✅ WebSocket reconnection on network failure
- ✅ Storage quota warning displays

### Integration Test Scenarios
- ✅ User logs in → sees tournament list → creates session
- ✅ Cameras discovered → session started → scoring triggered → scores broadcast
- ✅ Score overridden → event published → leaderboard updates
- ✅ Camera disconnected → event published → UI shows status
- ✅ End-to-end: Login → Scoring → Report generation
- ✅ Multi-user: 4+ concurrent users scoring simultaneously
- ✅ Real-time: Score broadcast < 100ms to all clients
- ✅ Performance: Scoring completes < 1 second with 4 cameras

---

## Cross-Unit Integration Checkpoints

### Checkpoint 1: API Contract Review (Before Code Generation)
- Backend agent presents all REST endpoints
- Frontend agent verifies can implement consumers
- Both agree on request/response schemas
- WebSocket event types locked

### Checkpoint 2: Mid-Sprint Sync (Week 2-3)
- Backend: Camera discovery working
- Frontend: Can display camera list
- Verify API contract working as expected
- Adjust if issues found

### Checkpoint 3: Real-Time Integration (Week 3)
- Backend: EventBus publishing ScoreCalculated
- Frontend: Receiving events via WebSocket
- Both: Verify < 100ms delivery
- Debug any latency or connection issues

### Checkpoint 4: Performance Testing (Week 4)
- Backend: Measure image processing time
- Frontend: Measure UI responsiveness
- Both: Verify < 1s end-to-end scoring
- Profile and optimize bottlenecks

### Checkpoint 5: Full Integration Test (Before Build & Test)
- All 18 Phase 1 stories implemented
- End-to-end user flows tested
- Both agents verify compatibility
- Sign off before Build & Test phase

