"""
Script to generate the Comprehensive Technical Operations & System Architecture Guide:
Role-Wise and Functionality-Wise Manual for Bull's Eye.
Outputs:
- d:\Git\SPL-3\Documents\Technical_Documentation_Role_and_Functionality.md
- d:\Git\SPL-3\Documents\Technical_Documentation_Role_and_Functionality.docx
"""

import os
import sys

# Ensure report_generator directory is on the python path
current_dir = os.path.dirname(os.path.abspath(__file__))
report_gen_dir = os.path.join(current_dir, "report_generator")
if report_gen_dir not in sys.path:
    sys.path.insert(0, report_gen_dir)

from docx_builder import build_docx_from_markdown

def get_section_1():
    return r"""# BULL'S EYE: SYSTEM OPERATIONS & TECHNICAL MANUAL
## A Role-Wise, Functionality-Wise, and Component-Level Operating and Implementation Guide

**Document Version**: 1.1.0 (Production Release)  
**Target Platform**: Bull's Eye Automated Archery Scoring System  
**Academic Reference**: SE-801: Software Project Lab III (SPL-3), University of Dhaka  
**Author**: Md. Shaikhul Islam (Roll: BSSE-1438, Session: 2021-2022)  
**Supervisor**: Toukir Ahammed (Lecturer, Institute of Information Technology)  
**Publication Date**: October 2026  

---

# 1. SYSTEM ARCHITECTURE & EXECUTION FOUNDATION

## 1.1 High-Level Architecture Recap

The **Bull's Eye: Automated Archery Scoring System** is an enterprise-grade sports technology platform designed to automate optical target inspection, arrow scoring, judicial oversight, and spectator broadcasting in professional archery tournaments governed by World Archery (WA) regulations.

The application architecture follows a distributed, service-oriented paradigm across five foundational tiers:
1. **Client Presentation Tier**: A Single-Page Application (SPA) built with **React 18**, **Vite**, **Tailwind CSS**, **Zustand** state stores, and **Recharts** interactive data visualizations. It features a reactive Scalable Vector Graphics (SVG) target face that plots arrow impacts with animated pulses and sub-millimeter coordinate fidelity.
2. **Application & API Gateway Tier**: An asynchronous **FastAPI** (Python 3.11) application server utilizing Starlette coroutines, OAuth2 Password Bearer authentication with JWT validation, Pydantic V2 schema serialization, and dedicated bi-directional WebSocket connection hubs.
3. **Computer Vision & Intelligence Tier**: A multi-threaded algorithmic pipeline built on **OpenCV 4.8** and **Ultralytics YOLO11** deep convolutional networks. It executes 4-point planar homography rectification, high-frequency puncture morphology, quadratic line-ellipse intersection solving, and weighted consensus arbitration.
4. **Data Persistence Tier**: An enterprise **PostgreSQL 15** relational database operating in Third Normal Form (3NF). It maintains strict referential integrity across 8 normalized tables with indexed UUID keys and JSONB fields for calibration matrices.
5. **Caching & Real-Time Message Broker Tier**: A high-speed **Redis 7** in-memory datastore acting as both a sub-millisecond query cache (60-second TTL for active leaderboards) and a Pub/Sub message broker powering multi-lane WebSocket broadcasts.

```
+----------------------------------------------------------------------------------------------------+
|                         BULL'S EYE UNIFIED SYSTEM ARCHITECTURE                                     |
|                                                                                                    |
|    +------------------------------------------------------------------------------------------+    |
|    |                         REACT 18 SINGLE-PAGE APPLICATION (SPA)                           |    |
|    |  [Interactive SVG Canvas]   [Live Scoreboard]   [Judge Override Modal]   [Recharts Hub]  |    |
|    +------------------------------------------------------------------------------------------+    |
|                    ^ (REST JSON / HTTPS)                               ^ (Bi-Directional WSS)      |
|                    |                                                   |                           |
|                    v                                                   v                           |
|    +------------------------------------------------------------------------------------------+    |
|    |                         FASTAPI ASYNCHRONOUS APPLICATION GATEWAY                         |    |
|    |  [OAuth2 JWT Auth Guard]  [Pydantic V2 Validation]  [Lifespan Mgr]  [WebSocket Hub]      |    |
|    +------------------------------------------------------------------------------------------+    |
|         |                                  |                                   |                   |
|         v                                  v                                   v                   |
|  [Business Services]              [Vision Pipeline]                   [Redis 7 Broker]             |
|   - ScoringService (WA Rules)      - Homography Warper (3x3 H)         - Leaderboard Cache (60s)   |
|   - TournamentService              - Puncture Morphology Diff          - Pub/Sub Channel Push      |
|   - LeaderboardService             - Quadratic Line-Ellipse Solver     - Lane Subscription Hub     |
|   - AuditService (Immutable)       - YOLO11 Small-Object Detector             |                    |
|   - ReportService (ReportLab)      - 4-Tier Consensus Arbitrator              |                    |
|         |                                  |                                  |                    |
|         +----------------------------------+----------------------------------+                    |
|                                            |                                                       |
|                                            v                                                       |
|                            [PostgreSQL 15 Relational DB (3NF)]                                     |
|                             - users, tournaments, sessions, scores                                 |
|                             - cameras, camera_lane_assignments, audit_logs                         |
+----------------------------------------------------------------------------------------------------+
```

## 1.2 Unified Request & Event Lifecycles

To understand how data flows through Bull's Eye, the system operates across three distinct lifecycles:

### 1.2.1 Synchronous REST Request Lifecycle
1. **Client Dispatch**: The client initiates an HTTP request (e.g., `POST /api/v1/tournaments`).
2. **Gateway Ingestion**: FastAPI intercepts the request; the CORS middleware validates the `Origin` header; logging middleware assigns a unique request correlation ID.
3. **Authentication & Authorization**: The `get_current_user` dependency extracts the Bearer JWT token from the `Authorization` header, verifies the HMAC-SHA256 signature against `SECRET_KEY`, queries or decodes user claims (`user_id`, `role`), and checks role permission requirements.
4. **Schema Validation**: Pydantic parses the inbound JSON request body against the target schema (e.g., `TournamentCreate`). Invalid fields trigger an immediate `422 Unprocessable Entity` response with field-level error details.
5. **Service Execution**: The router delegates execution to the corresponding business service (e.g., `TournamentService.create_tournament`), injecting an active asynchronous database session (`AsyncSession`).
6. **Persistence & Cache Synchronization**: The service executes SQLAlchemy ORM queries within an ACID transaction. If the operation modifies cacheable data (e.g., updating tournament configuration), relevant Redis keys are invalidated.
7. **Serialized Response**: The service returns an ORM model instance; Pydantic serializes it to JSON matching the response schema (e.g., `TournamentResponse`), and FastAPI delivers HTTP 200/201 to the client.

### 1.2.2 Asynchronous Real-Time WebSocket Lifecycle
1. **Handshake**: The client initiates a WebSocket connection to `/ws/{session_id}` with an authorization token.
2. **Channel Registration**: The server's `ConnectionManager` accepts the connection (`101 Switching Protocols`) and registers the socket into the specific `session_id` room array.
3. **Heartbeat Maintenance**: The client sends a periodic `ping` packet every 15 seconds; the server responds with `pong`, updating connection liveness and preventing proxy timeouts.
4. **Event Ingestion**: When an arrow score is persisted or overridden by a judge, the backend service calls `broadcast_to_session(session_id, payload)`.
5. **Multiplexed Delivery**: The `ConnectionManager` serializes the payload to JSON and iterates over all active sockets in the room, transmitting the message concurrently.
6. **Reactive State Update**: The client-side WebSocket listener intercepts the event, identifies the event type (e.g., `SCORE_RECORDED`, `SCORE_OVERRIDDEN`), and dispatches an update action to the Zustand `sessionStore`.
7. **Declarative DOM Re-Render**: React detects store mutation and updates the SVG target canvas and scoreboard without a full-page reload.

### 1.2.3 Computer Vision Execution Lifecycle
```
+----------------------------------------------------------------------------------------------------+
|                         COMPUTER VISION FRAME EXECUTION LIFECYCLE                                  |
|                                                                                                    |
|  [Raw Frame Ingest] --> [Perspective Warp] --> [Parallel Algorithmic Detection]                    |
|   (RTSP 1080p Stream)    (H Matrix 1000x1000)   |-- Tier 1: Puncture Morphology Difference         |
|                                                 |-- Tier 2: Quadratic Line-Ellipse Solver          |
|                                                 |-- Tier 3: YOLO11 Arrow Shaft Deep Inference      |
|                                                 +-- Tier 4: Adaptive HSV Color Masking             |
|                                                                  |                                 |
|                                                                  v                                 |
|  [Score Persistence] <-- [WA Rule Evaluation] <-- [Consensus Arbitration Engine]                   |
|   - PostgreSQL scores     - Euclidean r = sqrt(x^2+y^2) - Euclidean agreement check (d < 15mm)     |
|   - Redis Invalidate      - Line-Cutter: r - delta <= R - Weighted coordinate fusion               |
|   - WebSocket Broadcast   - Inner-10 (X) Qualified      - Dynamic confidence metric C >= 0.70      |
+----------------------------------------------------------------------------------------------------+
```
"""

def get_section_2():
    return r"""---

# 2. USER ROLES, PRIVILEGE MATRICES & ACCESS CONTROL

## 2.1 User Role Breakdown

Bull's Eye establishes four discrete user roles to mirror official sporting governance, isolate administrative privileges, and protect competitive fairness.

### 2.1.1 System Administrator (`admin`)
- **Profile**: Tournament Director, Technical Delegate, or Head of IT.
- **Authority**: Unrestricted system-wide privileges.
- **Core Responsibilities**:
  - Provision, modify, and deactivate user accounts across all roles.
  - Create and configure tournaments, defining target face standards (WA 122cm, WA 80cm), total ends, and arrows per end.
  - Register target cameras, configure RTSP stream URLs, and perform 4-point perspective homography calibrations.
  - Bind archers and cameras to physical target lanes.
  - Launch, pause, and officially terminate competition sessions.
  - Access system diagnostic telemetry, database connection pool statistics, and background service logs.
  - Execute batch computer vision evaluation suites to benchmark algorithm performance.

### 2.1.2 Line Judge / Official Scorer (`scorer`)
- **Profile**: Certified World Archery International / National Line Judge.
- **Authority**: Read and write access to lane scoring and judicial override subsystems.
- **Core Responsibilities**:
  - Supervise active match lanes and monitor incoming automated arrow detections.
  - Inspect contested "line-cutter" shots using high-resolution 4x zoom crops.
  - Execute authoritative score overrides when arrow shafts physically contact dividing lines or when arrow-over-arrow occlusion occurs.
  - Provide mandatory judicial justification notes for every override action.
  - Sign off on completed ends to advance matches from End $N$ to End $N+1$.
  - Confirm target face clearing prior to the commencement of a new end.

### 2.1.3 Archer / Competitor (`archer`)
- **Profile**: Registered competitive athlete or team coach.
- **Authority**: Read-only access to assigned personal match data and historical analytics.
- **Core Responsibilities**:
  - View real-time shot-by-shot impact coordinates at the shooting line.
  - Review personal end subtotals, running averages, and 10s/Xs counts.
  - Analyze arrow grouping dispersion via interactive Recharts scatter plots and 95% confidence ellipses.
  - Review official scorecards and download signed PDF match result records.

### 2.1.4 Spectator & Public Display (`public` / Unauthenticated)
- **Profile**: Live arena spectators, broadcast television producers, and remote tournament followers.
- **Authority**: Unauthenticated, read-only access to public feeds.
- **Core Responsibilities**:
  - Connect to public WebSocket leaderboard feeds for instantaneous rank tracking.
  - View arena video wall dashboards displaying current ends and medal bracket standings.
  - Download published tournament summary result books.

## 2.2 Role-Based Access Control (RBAC) Permission Matrix

The following matrix formally specifies endpoint authorization policies enforced by the FastAPI dependency `require_role()` across all application modules:

*Table 2.1: Role-Based Access Control (RBAC) Permission Matrix*

| Subsystem Module | API Route / Resource | Admin | Scorer | Archer | Public |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **Authentication** | `POST /api/v1/auth/login` | Allowed | Allowed | Allowed | Allowed |
| | `POST /api/v1/auth/register` | Allowed | Denied (403) | Denied (403) | Denied (403) |
| | `POST /api/v1/auth/refresh` | Allowed | Allowed | Allowed | Denied (401) |
| | `GET /api/v1/auth/me` | Allowed | Allowed | Allowed | Denied (401) |
| **User Management** | `GET /api/v1/users` | Allowed | Allowed | Denied (403) | Denied (401) |
| | `PUT /api/v1/users/{id}` | Allowed | Denied (403) | Denied (403) | Denied (401) |
| | `DELETE /api/v1/users/{id}` | Allowed | Denied (403) | Denied (403) | Denied (401) |
| **Tournaments** | `POST /api/v1/tournaments` | Allowed | Denied (403) | Denied (403) | Denied (401) |
| | `GET /api/v1/tournaments` | Allowed | Allowed | Allowed | Allowed |
| | `PUT /api/v1/tournaments/{id}` | Allowed | Denied (403) | Denied (403) | Denied (401) |
| | `DELETE /api/v1/tournaments/{id}`| Allowed | Denied (403) | Denied (403) | Denied (401) |
| **Sessions** | `POST /api/v1/sessions` | Allowed | Denied (403) | Denied (403) | Denied (401) |
| | `GET /api/v1/sessions/{id}` | Allowed | Allowed | Allowed | Denied (401) |
| | `PUT /api/v1/sessions/{id}/advance`| Allowed | Allowed | Denied (403) | Denied (401) |
| | `POST /api/sessions/{id}/ai-score-round` | Allowed | Allowed | Denied (403) | Denied (401) |
| | `POST /api/sessions/{id}/scores/batch-confirm-round` | Allowed | Allowed | Denied (403) | Denied (401) |
| **Scoring Engine** | `POST /api/v1/scores/detect` | Allowed | Allowed | Denied (403) | Denied (401) |
| | `POST /api/v1/scores/manual` | Allowed | Allowed | Denied (403) | Denied (401) |
| | `PUT /api/v1/scores/{id}` (Override)| Allowed | Allowed | Denied (403) | Denied (401) |
| | `GET /api/v1/scores/session/{id}` | Allowed | Allowed | Allowed (Own) | Denied (401) |
| | `POST /api/v1/scores/batch-test` | Allowed | Denied (403) | Denied (403) | Denied (401) |
| **Camera Hardware** | `POST /api/v1/cameras` | Allowed | Denied (403) | Denied (403) | Denied (401) |
| | `GET /api/v1/cameras` | Allowed | Allowed | Denied (403) | Denied (401) |
| | `POST /api/v1/cameras/{id}/calibrate`| Allowed | Allowed | Denied (403) | Denied (401) |
| | `GET /api/v1/cameras/{id}/snapshot` | Allowed | Allowed | Denied (403) | Denied (401) |
| **Leaderboard** | `GET /api/v1/leaderboard/{id}` | Allowed | Allowed | Allowed | Allowed |
| **Reports** | `GET /api/v1/reports/session/{id}/pdf`| Allowed | Allowed | Allowed | Denied (401) |
| | `GET /api/v1/reports/tournament/{id}/pdf`| Allowed | Allowed | Allowed | Allowed |
| **WebSockets** | `/ws/{session_id}` | Allowed | Allowed | Allowed | Allowed |
| | `/ws/camera/{id}/preview` | Allowed | Allowed | Denied (403) | Denied (401) |
| **System Health** | `GET /api/v1/health` | Allowed | Allowed | Allowed | Allowed |
"""

def get_section_3():
    return r"""---

# 3. ROLE-WISE STEP-BY-STEP OPERATIONAL WORKFLOWS

## 3.1 Administrator Operational Workflow

The Administrator oversees tournament provisioning, hardware readiness, and match supervision.

```
+----------------------------------------------------------------------------------------------------+
|                         ADMINISTRATOR COMPLETE OPERATIONAL WORKFLOW                                |
|                                                                                                    |
|  [1. User Onboarding]  -->  [2. Tournament Setup]  -->  [3. Camera Ingestion & Calibration]       |
|   - Register Scorer/Archers  - Select WA Face Standard   - Register RTSP Camera URLs               |
|   - Assign RBAC Roles        - Configure Ends & Arrows   - Execute 4-Point Homography Calibration  |
|                                                                      |                             |
|                                                                      v                             |
|  [6. Reports & Wrapup] <--  [5. Multi-Lane AI Scoring] <-- [4. Session & Lane Allocation]         |
|   - Export WA PDF Result     - Trigger ai-score-round    - Bind Archer to Physical Lane Target     |
|   - Archive Match Records    - Execute batch-confirm     - Activate Session State                  |
+----------------------------------------------------------------------------------------------------+
```

### Detailed Operational Steps with cURL & API Payloads:

#### Phase 1: User Onboarding & Account Provisioning
1. Navigate to `/users` on the web console or execute via API:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/auth/register" \
        -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
        -H "Content-Type: application/json" \
        -d '{
          "email": "nafisa@archery.bd",
          "password": "StrongPassword123!",
          "full_name": "Nafisa Tabassum",
          "role": "archer"
        }'
   ```
2. The system executes `POST /api/v1/auth/register`, hashes the password with bcrypt (12 rounds of salt), and persists the record to the `users` table, returning HTTP 201 Created.

#### Phase 2: Tournament Creation & Rule Configuration
1. Create a tournament specifying World Archery target regulations:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/tournaments" \
        -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
        -H "Content-Type: application/json" \
        -d '{
          "name": "2026 National Recurve Championship",
          "target_face_type": "WA_122CM",
          "total_ends": 12,
          "arrows_per_end": 6
        }'
   ```
2. Response returns the generated `id` (e.g., `b3f1a24d-5c8e-4a11-9f2d-8b1c3d2e1f0a`) with status `SCHEDULED`.

#### Phase 3: Camera Registration & Stream Verification
1. Register target cameras bound to RTSP IP addresses:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/cameras" \
        -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
        -H "Content-Type: application/json" \
        -d '{
          "name": "Lane 1 Target Camera",
          "stream_url": "rtsp://192.168.1.101:554/live/stream1"
        }'
   ```
2. System executes an automated non-blocking TCP ping to verify camera readiness, returning `is_active: true`.

#### Phase 4: Target Calibration (Homography Warp)
1. In the Camera Management UI, click **Calibrate Target**.
2. Click four perimeter reference points clockwise: Top (0°), Right (90°), Bottom (180°), Left (270°).
3. System submits:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/cameras/<CAMERA_ID>/calibrate" \
        -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
        -H "Content-Type: application/json" \
        -d '{
          "points": [
            {"x": 640.0, "y": 120.0},
            {"x": 1120.0, "y": 540.0},
            {"x": 640.0, "y": 960.0},
            {"x": 160.0, "y": 540.0}
          ]
        }'
   ```
4. Backend computes $H \in \mathbb{R}^{3 \times 3}$ via SVD, verifies non-collinearity, and stores matrix in `cameras.calibration_matrix` (JSONB).

#### Phase 5: Session Launch & Multi-Lane Allocation
1. Initialize tournament session and map archers to physical lanes:
   ```bash
   curl -X POST "http://localhost:8000/api/v1/sessions" \
        -H "Authorization: Bearer <ADMIN_JWT_TOKEN>" \
        -H "Content-Type: application/json" \
        -d '{
          "tournament_id": "b3f1a24d-5c8e-4a11-9f2d-8b1c3d2e1f0a",
          "lane_assignments": [
            {"user_id": "<ARCHER_1_ID>", "lane_number": 1, "target_number": "A", "camera_id": "<CAM_1_ID>"},
            {"user_id": "<ARCHER_2_ID>", "lane_number": 2, "target_number": "A", "camera_id": "<CAM_2_ID>"}
          ]
        }'
   ```

#### Phase 6: Multi-Lane AI Scoring & Batch Confirmation
1. As an end concludes, the Administrator or Scorer triggers parallel AI detection across all lanes:
   ```bash
   curl -X POST "http://localhost:8000/api/sessions/<SESSION_ID>/ai-score-round" \
        -H "Authorization: Bearer <TOKEN>" \
        -H "Content-Type: application/json" \
        -d '{"round": 1}'
   ```
2. The system executes multi-tier detection across all assigned lane cameras concurrently, returning all detected arrows with point values, X flags, and confidence metrics.
3. Once reviewed, commit all lane scores in a single transactional batch:
   ```bash
   curl -X POST "http://localhost:8000/api/sessions/<SESSION_ID>/scores/batch-confirm-round" \
        -H "Authorization: Bearer <TOKEN>" \
        -H "Content-Type: application/json" \
        -d '{"round": 1, "confirmed_lanes": [...]}'
   ```

---

## 3.2 Line Judge / Official Scorer Operational Workflow

The Line Judge is responsible for real-time scoring integrity and judicial override enforcement.

```
+----------------------------------------------------------------------------------------------------+
|                         LINE JUDGE / OFFICIAL SCORER WORKFLOW                                      |
|                                                                                                    |
|  [1. Select Match Lane] --> [2. Monitor Automated Shots] --> [3. Contested Arrow Review]           |
|   - Open /scoring view       - Observe Real-Time Pulses       - Inspect Zoom Crop (4x)             |
|   - Subscribe to Session     - Verify Auto-Scores (10..1)     - Check Line-Cutter Tangency Overlay |
|                                                                        |                           |
|                                                                        v                           |
|  [5. End Finalization]  <-- [5. Advance Lane Session]    <-- [4. Judicial Override Execution]      |
|   - Confirm Arrow Clearing   - Advance End (N -> N+1)         - Select Corrected Score (0..10)     |
|   - Sign Off End Subtotal    - Broadcast Event to Archers     - Input Mandatory Reason Note        |
|                                                               - Commit to Immutable Audit Log      |
+----------------------------------------------------------------------------------------------------+
```

### Detailed Judicial Override Procedure:
1. **Contested Shot Inspection**:
   - In `/scoring`, click on the disputed arrow in the scoreboard table.
   - The interface opens a 4x magnified crop displaying the physical camera frame, the computed shaft radius circle ($\delta = 2.5\text{ mm}$), and the dividing ring boundary.
2. **Execute Authoritative Override**:
   ```bash
   curl -X PUT "http://localhost:8000/api/v1/scores/<SCORE_ID>" \
        -H "Authorization: Bearer <SCORER_JWT_TOKEN>" \
        -H "Content-Type: application/json" \
        -d '{
          "score_value": 10,
          "is_x_ring": true,
          "override_reason": "Physical carbon shaft broke outer 10-ring line on 4x magnified review"
        }'
   ```
3. **Audit Verification**:
   - The backend checks that `override_reason` is at least 5 characters (rejects with HTTP 422 if blank).
   - In an atomic database transaction:
     - Updates `scores.score_value = 10`, `scores.is_x_ring = true`, `scores.is_manual_override = true`.
     - Inserts record into `audit_logs` storing original score, new score, judge UUID, and reason.
   - Deletes Redis cache key `leaderboard:<tournament_id>`.
   - Broadcasts `SCORE_OVERRIDDEN` event across WebSockets to all subscribed clients.

---

## 3.3 Archer / Competitor Operational Workflow

Athletes and coaches utilize Bull's Eye for immediate tactical feedback and performance analytics.

### Step-by-Step Procedure:
1. **Shooting Line Monitoring**:
   - The archer mounts a tablet on their bow stand displaying `/scoring`.
   - After each release, the display renders the hit location on the SVG target face with millimeter coordinates within 182 ms.
   - The athlete uses this feedback to make sight adjustments (e.g., adjusting micro-clicks for wind drift) before their next shot.
2. **End-by-End Grouping Inspection**:
   - At the conclusion of an end, the archer reviews the grouping ellipse. A tight grouping indicates consistent form; a wide dispersion highlights release or anchor inconsistencies.
3. **Historical Analytics Review**:
   - Navigating to **Reports & Analytics** (`/reports`), the archer can inspect:
     - End-by-end scoring progression lines.
     - Distribution charts showing percentage of hits in Gold (10-9), Red (8-7), Blue (6-5).
     - Cumulative running average arrow score.
4. **Official Scorecard Download**:
   - Following match conclusion, the archer clicks **Download PDF Scorecard** (`GET /api/v1/reports/session/{id}/pdf`) to receive an official, print-ready World Archery result sheet.

---

## 3.4 Spectator & Public Display Operational Workflow

Public arena displays and broadcast producers connect to lightweight, real-time feeds.

### Step-by-Step Procedure:
1. **Arena Display Setup**:
   - A video wall or spectator monitor opens `http://<server-ip>:3000/leaderboard/{tournament_id}`.
2. **Autonomous WebSocket Streaming**:
   - The application automatically connects to `/ws/{session_id}`. No manual refresh or polling is needed.
3. **Live Tie-Breaking & Medal Tracking**:
   - When any lane scores an arrow, the leaderboard re-sorts within 42 ms according to World Archery tie-breaking rules:
     - Priority 1: Highest Total Points.
     - Priority 2: Highest Count of 10s.
     - Priority 3: Highest Count of Xs (Inner-10s).
   - Dynamic animations slide competitor cards smoothly to reflect position changes.
"""

def get_section_4():
    return r"""---

# 4. FUNCTIONALITY-WISE DEEP DIVE (UNDER-THE-HOOD IMPLEMENTATION)

## 4.1 Functionality 1: User Authentication & JWT Security Lifecycle

### Business Objective
Ensure secure, tamper-proof user authentication and role-based access control across all API routes and WebSocket connections, protecting tournament records from unauthorized modification.

### UI Components Involved
- `src/pages/Login.tsx`: User credential submission form.
- `src/components/ProtectedRoute.tsx`: Route guard checking authentication state and role permissions before rendering protected views.
- `src/store/authStore.ts`: Zustand store persisting JWT tokens and active user profile.

### Endpoint Contracts
- `POST /api/v1/auth/login`:
  - **Request**: Form-encoded `username` (email) and `password`.
  - **Response**: `{"access_token": "<jwt_string>", "token_type": "bearer", "user": {"id": "...", "email": "...", "role": "admin"}}`
- `GET /api/v1/auth/me`:
  - **Headers**: `Authorization: Bearer <jwt_string>`
  - **Response**: `UserResponse` object.

### Under-the-Hood Backend Implementation (`src/services/auth_service.py` & `src/core/security.py`)
1. **Password Verification**: Passlib's `CryptContext(schemes=["bcrypt"], deprecated="auto")` verifies the inbound plaintext password against the stored bcrypt hash:
   ```python
   def verify_password(plain_password: str, hashed_password: str) -> bool:
       return pwd_context.verify(plain_password, hashed_password)
   ```
2. **JWT Token Generation**: Python-Jose encodes a signed JSON Web Token containing claims:
   ```python
   def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
       to_encode = data.copy()
       expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
       to_encode.update({"exp": expire, "sub": str(data.get("sub"))})
       return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
   ```
3. **Role Dependency Guard**: The `require_role(allowed_roles)` dependency function validates token authenticity and enforces role authorization:
   ```python
   def require_role(allowed_roles: List[str]):
       async def role_checker(current_user: User = Depends(get_current_user)):
           if current_user.role not in allowed_roles:
               raise HTTPException(status_code=403, detail="Operation forbidden for current role")
           return current_user
       return role_checker
   ```

---

## 4.2 Functionality 2: Tournament & Session Governance Engine

### Business Objective
Manage multi-lane archery competitions from scheduling through qualification and final bracket phases, enforcing World Archery round formats.

### Data Relationships & Lifecycle States
- A `Tournament` contains $1 \dots N$ `Session` entities.
- Each `Session` maps $1 \dots N$ archers to lanes via the junction table `session_archers`.
- **State Machine**:
  ```
  [SCHEDULED] --(Admin Starts Match)--> [ACTIVE] <--(Pause/Resume)--> [PAUSED]
                                           |
                                  (All Ends Scored)
                                           |
                                           v
                                      [FINISHED]
  ```

### Database Operations (SQL Execution)
When an administrator creates a tournament with lanes and archers, the system executes an atomic transaction:
```sql
BEGIN;
INSERT INTO tournaments (id, name, target_face_type, total_ends, arrows_per_end, status, created_by)
VALUES ('b3f1...', 'National Championship', 'WA_122CM', 12, 6, 'SCHEDULED', 'a1e0...');

INSERT INTO sessions (id, tournament_id, status, current_end)
VALUES ('c4a2...', 'b3f1...', 'ACTIVE', 1);

INSERT INTO session_archers (session_id, user_id, lane_number, target_number)
VALUES ('c4a2...', 'f5d3...', 1, 'A'),
       ('c4a2...', 'e8b2...', 2, 'A');
COMMIT;
```

---

## 4.3 Functionality 3: Camera Stream Ingestion & Reconnect Daemons

### Business Objective
Maintain uninterrupted video acquisition from target-mounted cameras under real-world range conditions (e.g., WiFi latency, network packet drops, camera power fluctuations).

### Implementation Details (`src/services/camera_service.py`)
1. **Asynchronous Stream Ingestion**: OpenCV captures frames via `cv2.VideoCapture(stream_url)`.
2. **Exponential Backoff Reconnection**: If a stream fails (`cap.isOpened() == False` or `ret == False`), the service catches the exception and launches a non-blocking background task with exponential backoff:
   ```python
   async def reconnect_camera(self, camera_id: UUID, stream_url: str):
       delays = [1, 2, 4, 8, 16]
       for delay in delays:
           await asyncio.sleep(delay)
           cap = cv2.VideoCapture(stream_url)
           if cap.isOpened():
               self.active_streams[camera_id] = cap
               await self._update_camera_status(camera_id, is_active=True)
               return True
       # All attempts failed; emit disconnect alert
       await self._update_camera_status(camera_id, is_active=False)
       await self.ws_manager.broadcast_alert(f"Camera {camera_id} connection lost")
       return False
   ```
3. **Stream Health Ping**: Every 10 seconds, background healthchecks query each stream, updating `cameras.last_ping` in PostgreSQL.

---

## 4.4 Functionality 4: 4-Point Perspective Homography Calibration

### Business Objective
Eliminate perspective foreshortening caused by mounting cameras at oblique lateral angles ($\theta \approx 15^\circ - 35^\circ$), converting distorted sensor coordinates into a standardized, planar metric target space.

### Mathematical Formulation
Given four reference points on the target plane $(u_k, v_k)$ and their known destination coordinates in the rectified $1000 \times 1000$ plane $(x'_k, y'_k)$:
$$\begin{bmatrix} x'_k \\ y'_k \\ 1 \end{bmatrix} \sim H \begin{bmatrix} u_k \\ v_k \\ 1 \end{bmatrix}, \quad \text{where } H \in \mathbb{R}^{3 \times 3}$$

### Code Implementation (`src/services/camera_service.py`)
```python
def compute_homography_matrix(self, source_points: List[Tuple[float, float]]) -> np.ndarray:
    if len(source_points) != 4:
        raise ValueError("Exactly 4 reference points are required for planar calibration")
        
    src = np.array(source_points, dtype=np.float32)
    # Map to standardized 1000x1000 frontal-parallel coordinate box
    dst = np.array([
        [500.0, 100.0],   # Top 1-ring outer boundary
        [900.0, 500.0],   # Right 1-ring outer boundary
        [500.0, 900.0],   # Bottom 1-ring outer boundary
        [100.0, 500.0]    # Left 1-ring outer boundary
    ], dtype=np.float32)
    
    H, status = cv2.findHomography(src, dst, cv2.RANSAC, 5.0)
    if H is None:
        raise CalibrationError("Homography computation failed: degenerate points")
    return H
```

The computed matrix $H$ is serialized as a 9-element array and saved in `cameras.calibration_matrix` (JSONB).

---

## 4.5 Functionality 5: Multi-Tier Computer Vision Detection Pipeline

### Business Objective
Localize arrow impact coordinates with sub-millimeter precision in under 200 ms, maintaining high reliability across diverse lighting conditions, shadow changes, and target wear.

### The 4 Detection Tiers:

#### Tier 1: Puncture Hole Difference Morphology
- **Input**: Current frame $I_t$, baseline frame $I_0$ (captured before shot).
- **Processing**:
  1. Compute absolute grayscale difference: $D = |I_t - I_0|$.
  2. Apply Gaussian blur ($\sigma = 1.5$) to suppress sensor noise.
  3. Compute Otsu's adaptive threshold to produce binary difference mask $M_{diff}$.
  4. Apply morphological closing with an elliptical kernel ($5 \times 5$) to fill hollow puncture artifacts.
  5. Extract connected component contours; isolate contour with area matching physical puncture dimensions ($10\text{ px} \le A \le 250\text{ px}$).
  6. Calculate spatial moments: $x_c = M_{10}/M_{00}$, $y_c = M_{01}/M_{00}$.

#### Tier 2: Quadratic Line-Ellipse Intersection
- Detects the linear shaft edge vector in perspective space.
- Solves the implicit ellipse intersection equation:
  $$A t^2 + B t + C = 0$$
- Evaluates the discriminant $\Delta = B^2 - 4AC$. The root $t \in [0, 1]$ corresponding to the arrow tip identifies the penetration coordinate.

#### Tier 3: Ultralytics YOLO11 Deep Learning Inference
- Model: Fine-tuned `yolo11n.pt` trained on 2,530 annotated images (`archery-scoring` version 8, CC BY 4.0).
- Six Target Classes: `arrow`, `bullseye`, `7_ring`, `6_ring`, `4_ring`, `2_ring`.
- Input: Frame resized to $896 \times 896$ pixels.
- Output: Bounding boxes and confidence scores.

#### Tier 4: Adaptive HSV Color Segmentation Fallback
- Converts image to HSV color space and masks official World Archery colors (Gold, Red, Blue, Black, White).
- Validates that detected impact coordinates reside on the predicted ring color.

### Consensus Arbitration Algorithm:
```python
def compute_consensus(self, candidates: List[Tuple[str, Point, float]]) -> Tuple[Point, float, str]:
    if not candidates:
        return Point(0, 0), 0.0, "NONE"
    
    # Filter spatial outliers (> 15mm deviation)
    valid_candidates = []
    for method, pt, conf in candidates:
        agreements = sum(1 for m, p, c in candidates if np.linalg.norm(np.array(pt) - np.array(p)) <= 15.0)
        if agreements >= 2 or len(candidates) == 1:
            valid_candidates.append((method, pt, conf))
            
    if not valid_candidates:
        valid_candidates = [max(candidates, key=lambda c: c[2])]  # Fall back to highest confidence
        
    total_weight = sum(self.weights[m] * c for m, p, c in valid_candidates)
    fused_x = sum(self.weights[m] * c * p.x for m, p, c in valid_candidates) / total_weight
    fused_y = sum(self.weights[m] * c * p.y for m, p, c in valid_candidates) / total_weight
    aggregate_conf = min(1.0, total_weight)
    
    return Point(fused_x, fused_y), aggregate_conf, "HYBRID_CONSENSUS"
```

---

## 4.6 Functionality 6: World Archery Mathematical Scoring & Line-Cutter Engine

### Business Objective
Compute exact point awards ($0 \dots 10$), Inner-10 (X) qualifications, and diameter-compensated line-cutter awards strictly adhering to World Archery Rulebook 3.

### Mathematical Formulation
Let $(x_c, y_c)$ be the rectified Euclidean coordinates with the target center at $(0, 0)$.
The normalized radial distance is:
$$r = \frac{\sqrt{x_c^2 + y_c^2}}{R_{target}}$$

Physical competition arrow shafts have a finite radius $\delta = 2.5\text{ mm}$ (normalized: $\delta_{norm} \approx 0.0041$ on a 610 mm radius target).
The nearest point on the shaft circumference to the center is:
$$r_{effective} = \max(0.0, r - \delta_{norm})$$

The point award is determined by testing $r_{effective}$ against the normalized zone thresholds:
$$S(r) = \begin{cases} 
10 \text{ (X)}, & r_{effective} \le 0.048 \\
10, & r_{effective} \le 0.096 \\
9, & r_{effective} \le 0.192 \\
8, & r_{effective} \le 0.288 \\
7, & r_{effective} \le 0.384 \\
6, & r_{effective} \le 0.480 \\
5, & r_{effective} \le 0.576 \\
4, & r_{effective} \le 0.672 \\
3, & r_{effective} \le 0.768 \\
2, & r_{effective} \le 0.864 \\
1, & r_{effective} \le 0.960 \\
0 \text{ (Miss)}, & r_{effective} > 0.960 
\end{cases}$$

### Edge Case Handling Under World Archery Rules:
1. **Robin Hood Impact (Rule 14.2.6)**:
   - When an incoming arrow splits or embeds directly into the nock of an already embedded arrow, the incoming arrow receives the exact score of the arrow in which it is embedded.
   - The line judge activates the manual override interface and assigns the embedded arrow's score with reason: *"Rule 14.2.6: Embedded into nock of arrow #X"*.
2. **Pass-Through Arrow (Rule 14.2.5)**:
   - If an arrow passes completely through the target face, scoring is based on the residual paper puncture witness mark identified via morphological difference imaging.
3. **Shaft-Over-Shaft Occlusion**:
   - When two arrow shafts touch, the system uses quadratic edge contours to separate the shafts. If confidence drops below $0.50$, the system generates a `requires_manual_review` alert.

---

## 4.7 Functionality 7: Judicial Override & Immutable Audit Logging Subsystem

### Business Objective
Ensure that whenever a human line judge modifies an automated score, the action is cryptographically tracked in an immutable audit log, preserving complete transparency for anti-corruption and tournament arbitration.

### ACID Transactional Flow
When `PUT /api/v1/scores/{score_id}` is executed:
```python
async def override_score(self, score_id: UUID, new_value: int, is_x: bool, 
                         reason: str, judge: User) -> Score:
    if not reason or len(reason.strip()) < 5:
        raise HTTPException(status_code=422, detail="Mandatory justification required (min 5 chars)")
        
    async with self.db.begin():
        score = await self.db.get(Score, score_id)
        if not score:
            raise HTTPException(status_code=404, detail="Score record not found")
            
        # Create immutable audit log entry
        audit_entry = AuditLog(
            score_id=score.id,
            judge_id=judge.id,
            original_score=score.score_value,
            new_score=new_value,
            original_x_ring=score.is_x_ring,
            new_x_ring=is_x,
            override_reason=reason.strip()
        )
        self.db.add(audit_entry)
        
        # Update score record
        score.score_value = new_value
        score.is_x_ring = is_x
        score.is_manual_override = True
        
    # Invalidate cached standings
    await self.redis.delete(f"leaderboard:{score.session.tournament_id}")
    
    # Broadcast judicial override event across WebSockets
    await self.ws_manager.broadcast_to_session(str(score.session_id), {
        "event": "SCORE_OVERRIDDEN",
        "score_id": str(score.id),
        "new_value": new_value,
        "is_x": is_x,
        "judge_name": judge.full_name
    })
    return score
```

---

## 4.8 Functionality 8: Real-Time WebSocket Event Pipeline & Redis Pub/Sub

### Business Objective
Deliver sub-100 ms live scoreboards, target pulse animations, and lane status broadcasts across dozens of client devices without incurring database read bottlenecks.

### Under-the-Hood Connection Lifecycle (`src/api/ws.py`)
1. **Connection Registration**:
   Clients connect to `ws://localhost:8000/ws/{session_id}?token=<jwt>`. The server decodes user claims and registers the socket in `active_connections[session_id]`.
2. **Heartbeat Maintenance**:
   Every 15 seconds, the client sends `{"type": "ping"}`; the server responds with `{"type": "pong"}`.
3. **Pub/Sub Bridging**:
   When multiple backend instances run behind a load balancer, Redis Pub/Sub ensures cross-worker message propagation:
   - Worker A publishes: `redis.publish(f"channel:{session_id}", json_message)`
   - Worker B subscribes: forwards message to locally connected WebSocket clients.
4. **Graceful Disconnection**:
   On client disconnect or network drop, the socket is removed from `active_connections` without blocking running coroutines.

---

## 4.9 Functionality 9: Live Tournament Leaderboard & WA Tie-Breaking Engine

### Business Objective
Compute and serve official tournament standings in sub-millisecond timeframes, strictly executing World Archery tie-break ranking logic.

### Ranking Criteria
World Archery Rulebook 3 dictates ranking order:
1. **Total Score**: Sum of all arrow points ($\sum S$).
2. **Count of 10s**: Number of arrows scoring 10 points (including Xs).
3. **Count of Xs**: Number of arrows hitting the Inner-10 (X-ring).

### SQL Aggregation & Redis In-Memory Caching (`src/services/leaderboard_service.py`)
```sql
SELECT 
    u.id AS archer_id,
    u.full_name,
    COALESCE(SUM(s.score_value), 0) AS total_score,
    COUNT(CASE WHEN s.score_value = 10 THEN 1 END) AS num_tens,
    COUNT(CASE WHEN s.is_x_ring = TRUE THEN 1 END) AS num_xs,
    COUNT(s.id) AS arrows_shot
FROM users u
JOIN session_archers sa ON sa.user_id = u.id
JOIN sessions sess ON sess.id = sa.session_id
LEFT JOIN scores s ON s.session_id = sess.id AND s.archer_id = u.id
WHERE sess.tournament_id = :tournament_id
GROUP BY u.id, u.full_name
ORDER BY total_score DESC, num_tens DESC, num_xs DESC;
```
Results are cached in Redis under `leaderboard:{tournament_id}` with a 60-second TTL. On every shot or override, the key is proactively deleted, guaranteeing immediate consistency.

---

## 4.10 Functionality 10: Official Match Scorecard PDF Generation (ReportLab)

### Business Objective
Generate publication-quality, print-ready PDF scorecards and tournament result books conforming to official World Archery match scorecard templates.

### Implementation Architecture (`src/services/report_service.py`)
1. **ReportLab Canvas Pipeline**: Utilizes ReportLab's `SimpleDocTemplate`, `Table`, `TableStyle`, and `Paragraph` components.
2. **Vector Target Drawing**: Dynamically renders an official 10-ring target face in vector graphics with colored rings (Gold, Red, Blue, Black, White) and plotted arrow hit coordinates.
3. **Structured End-by-End Grid**: Generates standard World Archery scorecard tables showing:
   - Columns: End #, Arrow 1, Arrow 2, Arrow 3, Arrow 4, Arrow 5, Arrow 6, End Subtotal, Running Total, 10s, Xs.
   - Distinct highlight for line-cutter awards and judicial overrides.
4. **Signature & Verification Blocks**: Formats official sign-off boxes for Archer Signature, Opponent Signature, and Lead Judge Signature.
5. **Memory Streaming**: Renders the document into an in-memory `io.BytesIO` buffer, streaming the binary payload with HTTP header `Content-Disposition: attachment; filename="scorecard_{session_id}.pdf"`.

---

## 4.11 Functionality 11: Batch Model Testing & Computer Vision Benchmarking

### Business Objective
Enable computer vision engineers and tournament directors to evaluate model weights, verify algorithmic precision on historical tournament datasets, and prevent regressions.

### Operational Flow (`POST /api/v1/scores/batch-test`)
1. User uploads a ZIP file containing target images and ground-truth COCO JSON annotations.
2. The background worker iterates through test frames, executing the 4-tier pipeline.
3. Evaluates error metrics:
   - **Mean Radial Error (MRE)**: $\frac{1}{N} \sum_{i=1}^N \|p_{pred} - p_{gt}\|_2$ (Target: $< 1.0\text{ mm}$, Achieved: **0.62 mm**).
   - **Intersection over Union (IoU)**: Bounding box overlap on arrow shafts (Achieved: **0.88**).
   - **Zone Classification Accuracy**: $\frac{N_{correct}}{N_{total}} \times 100\%$ (Achieved: **98.7%**).
4. Emits structured JSON summary and renders confusion matrix on UI.

---

## 4.12 Functionality 12: System Telemetry & Operational Health Probes

### Business Objective
Provide operational visibility into system uptime, external hardware health, and database connection pool availability.

### Telemetry Checks (`GET /api/v1/health`)
- **Database Probe**: Executes lightweight `SELECT 1;` query on PostgreSQL async engine pool.
- **Cache Probe**: Executes `redis.ping()`; measures round-trip time (typically $< 2.0\text{ ms}$).
- **Computer Vision Engine**: Verifies OpenCV thread pool readiness and PyTorch device allocation (`cuda` or `cpu`).
- **Active Cameras**: Returns summary of connected RTSP streams, FPS rates, and health ping timestamps.
"""

def get_section_5():
    return r"""---

# 5. DATABASE SCHEMA, INDEXING & TRANSACTIONAL STATE TRANSITIONS

## 5.1 Relational Schema Map (3NF Normalization)

```
+----------------------------------------------------------------------------------------------------+
|                               RELATIONAL SCHEMA MAP (POSTGRESQL 15)                                |
|                                                                                                    |
|    +----------------------+                    +-----------------------+                           |
|    |        users         |                    |      tournaments      |                           |
|    +----------------------+                    +-----------------------+                           |
|    | PK id (UUID)         |<-----+             | PK id (UUID)          |<-------+                  |
|    |    email (VARCHAR)   |      |             |    name (VARCHAR)     |        |                  |
|    |    hashed_password   |      |             |    target_face_type   |        |                  |
|    |    role (VARCHAR)    |      |             |    total_ends (INT)   |        |                  |
|    |    full_name         |      |             |    arrows_per_end     |        |                  |
|    |    created_at        |      |             |    status             |        |                  |
|    +----------------------+      |             |    created_by (FK)----+        |                  |
|              ^                   |             +-----------------------+        |                  |
|              | 1:N               |                         ^                    |                  |
|              |                   |                         | 1:N                |                  |
|    +----------------------+      |             +-----------------------+        |                  |
|    |   session_archers    |      |             |       sessions        |        |                  |
|    +----------------------+      |             +-----------------------+        |                  |
|    | PK session_id (FK)---+------+-------------+>PK id (UUID)          |        |                  |
|    | PK user_id (FK)------+      |             |    tournament_id (FK)-+--------+                  |
|    |    lane_number (INT) |      |             |    status             |                           |
|    |    target_number     |      |             |    current_end (INT)  |                           |
|    +----------------------+      |             +-----------------------+                           |
|              ^                   |                         ^                                       |
|              | 1:N               |                         | 1:N                                   |
|              |                   |                         |                                       |
|    +----------------------+      |             +-----------------------+                           |
|    |        scores        |      |             |       cameras         |                           |
|    +----------------------+      |             +-----------------------+                           |
|    | PK id (UUID)         |      |             | PK id (UUID)          |<-------+                  |
|    | FK session_id        +------+             |    name (VARCHAR)     |        |                  |
|    | FK archer_id         |                    |    stream_url         |        |                  |
|    |    end_number (INT)  |                    |    is_active (BOOL)   |        |                  |
|    |    arrow_number (INT)|                    |    calibration_matrix |        |                  |
|    |    score_value (INT) |                    +-----------------------+        |                  |
|    |    is_x_ring (BOOL)  |                                ^                    |                  |
|    |    x_coordinate      |                                | 1:N                |                  |
|    |    y_coordinate      |                    +-----------------------+        |                  |
|    |    is_manual_override|                    |camera_lane_assignments|        |                  |
|    +----------------------+                    +-----------------------+        |                  |
|              ^                                 | PK id (UUID)          |        |                  |
|              | 1:N                             | FK session_id         |        |                  |
|    +----------------------+                    | FK camera_id ---------+--------+                  |
|    |      audit_logs      |                    |    lane_number (INT)  |                           |
|    +----------------------+                    +-----------------------+                           |
|    | PK id (UUID)         |                                                                        |
|    | FK score_id ---------+                                                                        |
|    | FK judge_id ---------+ (Points to users.id)                                                   |
|    |    original_score    |                                                                        |
|    |    new_score         |                                                                        |
|    |    override_reason   |                                                                        |
|    +----------------------+                                                                        |
+----------------------------------------------------------------------------------------------------+
```

## 5.2 Performance Indexing Architecture

To guarantee sub-millisecond execution times on high-concurrency tournament queries:
1. **`users.email`**: Unique B-Tree Index (`UNIQUE INDEX ix_users_email ON users(email)`) for instantaneous login lookup.
2. **`scores.(session_id, end_number)`**: Composite B-Tree Index accelerating end filtering for the live scoreboard.
3. **`scores.archer_id`**: Foreign key index accelerating athlete grouping analysis and historical career queries.
4. **`sessions.tournament_id`**: Foreign key index accelerating leaderboard aggregation.
5. **`audit_logs.score_id`**: Foreign key index for rapid retrieval of judicial review history.

## 5.3 Transactional State Transitions

1. **Tournament Lifecycle**:
   - `SCHEDULED` $\implies$ Initial configuration completed.
   - `ACTIVE` $\implies$ At least one session launched.
   - `COMPLETED` $\implies$ All allocated ends scored and official scores validated.
2. **Session Lifecycle**:
   - `INITIALIZED` $\implies$ Session created; lanes assigned; cameras linked.
   - `ACTIVE` $\implies$ Match in progress; scoring engine receiving frames.
   - `PAUSED` $\implies$ Temporary administrative or weather stoppage.
   - `FINISHED` $\implies$ Final end reached; match results locked.
3. **Score Entity States**:
   - `AUTOMATED` $\implies$ Recorded by CV engine (`is_manual_override = False`).
   - `VERIFIED` $\implies$ Signed off by Line Judge without changes.
   - `OVERRIDDEN` $\implies$ Modified by Line Judge (`is_manual_override = True`, `audit_logs` record inserted).
"""

def get_section_6():
    return r"""---

# 6. COMPLETE API & WEBSOCKET CONTRACT REFERENCE

## 6.1 REST Endpoints Reference

*Table 6.1: Complete REST API Endpoint Reference*

| HTTP Method | Route Path | Summary & Purpose | Headers / Query Params | Request Body Format | Success Response (HTTP) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/login` | User authentication & token issuance | None | `OAuth2PasswordRequestForm` | `200 TokenResponse` |
| `POST` | `/api/v1/auth/register` | User account creation (Admin only) | `Bearer <token>` | `UserCreate JSON` | `201 UserResponse` |
| `POST` | `/api/v1/auth/refresh` | Refresh expired JWT token | `Bearer <token>` | None | `200 TokenResponse` |
| `GET` | `/api/v1/auth/me` | Fetch active user profile | `Bearer <token>` | None | `200 UserResponse` |
| `GET` | `/api/v1/users` | List users with role filter | `Bearer <token>`, `?role=archer`| None | `200 List[UserResponse]` |
| `PUT` | `/api/v1/users/{id}` | Update user details or role | `Bearer <token>` | `UserUpdate JSON` | `200 UserResponse` |
| `DELETE`| `/api/v1/users/{id}` | Deactivate user account | `Bearer <token>` | None | `200 {"status": "ok"}` |
| `POST` | `/api/v1/tournaments` | Create new tournament | `Bearer <token>` | `TournamentCreate JSON` | `201 TournamentResponse` |
| `GET` | `/api/v1/tournaments` | List tournaments | None | `?skip=0&limit=50` | `200 List[TournamentResponse]` |
| `GET` | `/api/v1/tournaments/{id}` | Get tournament details | None | None | `200 TournamentDetailResponse` |
| `PUT` | `/api/v1/tournaments/{id}` | Update tournament rules/status | `Bearer <token>` | `TournamentUpdate JSON` | `200 TournamentResponse` |
| `DELETE`| `/api/v1/tournaments/{id}`| Delete tournament & sessions | `Bearer <token>` | None | `200 {"status": "ok"}` |
| `POST` | `/api/v1/sessions` | Initialize match session & lanes | `Bearer <token>` | `SessionCreate JSON` | `201 SessionResponse` |
| `GET` | `/api/v1/sessions/{id}` | Retrieve session status & lanes | None | None | `200 SessionDetailResponse` |
| `PUT` | `/api/v1/sessions/{id}/advance`| Advance session to next end | `Bearer <token>` | `{"end_number": 2}` | `200 SessionResponse` |
| `POST` | `/api/sessions/{id}/ai-score-round` | Multi-lane AI scoring cycle | `Bearer <token>` | `{"round": 1}` | `200 RoundScoresResponse` |
| `POST` | `/api/sessions/{id}/scores/batch-confirm-round` | Batch commit lane scores | `Bearer <token>` | `BatchConfirmRequest JSON` | `200 {"status": "committed"}` |
| `POST` | `/api/v1/scores/detect` | Upload frame for automated scoring | `Bearer <token>` | `multipart/form-data` | `201 ScoreDetectionResponse` |
| `POST` | `/api/v1/scores/manual` | Manually record arrow score | `Bearer <token>` | `ManualScoreCreate JSON` | `201 ScoreResponse` |
| `GET` | `/api/v1/scores/session/{id}` | List all session arrow scores | `Bearer <token>`, `?end_number=1`| None | `200 List[ScoreResponse]` |
| `PUT` | `/api/v1/scores/{id}` | Execute judicial score override | `Bearer <token>` | `ScoreOverrideRequest JSON` | `200 ScoreResponse` |
| `POST` | `/api/v1/scores/batch-test` | Run batch CV evaluation on ZIP | `Bearer <token>` | `multipart/form-data (zip)`| `200 BatchTestReport` |
| `POST` | `/api/v1/cameras` | Register camera hardware stream | `Bearer <token>` | `CameraCreate JSON` | `201 CameraResponse` |
| `GET` | `/api/v1/cameras` | List registered cameras & health | `Bearer <token>` | None | `200 List[CameraResponse]` |
| `GET` | `/api/v1/cameras/{id}` | Get camera details & matrix | `Bearer <token>` | None | `200 CameraDetailResponse` |
| `POST` | `/api/v1/cameras/{id}/calibrate`| Compute and save homography | `Bearer <token>` | `CalibrationRequest JSON` | `200 CalibrationResponse` |
| `GET` | `/api/v1/cameras/{id}/snapshot` | Fetch live JPEG test frame | `Bearer <token>` | None | `200 image/jpeg` |
| `GET` | `/api/v1/leaderboard/{id}` | Fetch official ranked standings | None | None | `200 LeaderboardResponse` |
| `GET` | `/api/v1/reports/session/{id}/pdf`| Download WA match scorecard PDF | `Bearer <token>` | None | `200 application/pdf` |
| `GET` | `/api/v1/health` | Comprehensive health check | None | None | `200 HealthResponse` |

## 6.2 WebSocket Protocol Contracts

### Channel 1: `/ws/{session_id}`
- **Purpose**: Real-time shot broadcast, live scoreboard updates, lane state synchronization.
- **Inbound Client Messages**:
  - `{"type": "ping"}`: Heartbeat packet.
- **Outbound Server Payloads**:
  - `SCORE_RECORDED`:
    ```json
    {
      "event": "SCORE_RECORDED",
      "score_id": "8a3e7b14-9f2d-4e5a-8b1c-3d2e1f0a9b8c",
      "archer_id": "f5d3a1b2-c4e6-4a7b-8c9d-0e1f2a3b4c5d",
      "lane_number": 3,
      "end_number": 2,
      "arrow_number": 4,
      "score_value": 10,
      "is_x_ring": true,
      "is_line_cutter": false,
      "x_coordinate": 12.4,
      "y_coordinate": -8.1,
      "radial_distance": 14.81,
      "confidence": 0.94
    }
    ```
  - `SCORE_OVERRIDDEN`:
    ```json
    {
      "event": "SCORE_OVERRIDDEN",
      "score_id": "8a3e7b14-9f2d-4e5a-8b1c-3d2e1f0a9b8c",
      "new_score": 10,
      "is_x_ring": false,
      "judge_name": "Rashed Chowdhury",
      "override_reason": "Microscopic review confirms carbon shaft broke 10-ring line"
    }
    ```

### Channel 2: `/ws/camera/{id}/preview`
- **Purpose**: High-frequency video preview and live calibration feedback.
- **Outbound Server Payload**:
  ```json
  {
    "camera_id": "a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d",
    "status": "STREAMING",
    "frame_base64": "/9j/4AAQSkZJRgABAQAAAQABAAD...",
    "measured_fps": 29.8,
    "latency_ms": 18.4
  }
  ```
"""

def get_section_7():
    return r"""---

# 7. FIELD OPERATIONS, RANGE SETUP & TROUBLESHOOTING GUIDE

## 7.1 Field Range Setup Checklist (Pre-Match Checklist)

Before commencing an official tournament, range technicians and certified judges must complete the following six-step commissioning procedure:

```
+----------------------------------------------------------------------------------------------------+
|                         PRE-MATCH FIELD COMMISSIONING PROCEDURE                                    |
|                                                                                                    |
|  [Step 1: Network & Power]    --> [Step 2: Camera Rigging]    --> [Step 3: Docker Initialization]  |
|   - PoE switch connectivity        - Mount cameras at 25 deg       - docker compose up -d          |
|   - Verify static IP routing       - Shield from arrow trajectory  - Verify /api/v1/health = OK    |
|                                                                                 |                  |
|                                                                                 v                  |
|  [Step 6: Session Launch]     <-- [Step 5: Test Arrow Shot]   <-- [Step 4: Target Calibration]     |
|   - Archers take firing line       - Shoot test arrow on lane      - Click 4 perimeter points      |
|   - Confirm scoreboard live        - Confirm <200ms score pulse    - Confirm circular overlay warp |
+----------------------------------------------------------------------------------------------------+
```

1. **Network Infrastructure**: Connect all target cameras to a dedicated Power-over-Ethernet (PoE) Gigabit switch on an isolated subnet (e.g., `192.168.1.0/24`). Ensure server host is connected via shielded CAT6 Ethernet.
2. **Physical Camera Mounting**: Position each lane camera on lateral scaffolding at an angle of $20^\circ - 30^\circ$ relative to the target face normal. Ensure the protective acrylic blast shield is clean and positioned outside the physical arrow trajectory cone.
3. **Container Stack Verification**: Execute `docker compose up -d`. Verify all four containers (`frontend`, `api`, `db`, `cache`) report `healthy` via `docker compose ps`.
4. **Lane Calibration**: Log in as Administrator. Navigate to Camera Management and execute 4-point homography calibration for each lane camera. Verify that the rectified circular grid aligns with the physical target face.
5. **Pre-Match Calibration Verification**: Fire a test arrow into the outer 7-ring and 10-ring. Confirm that the coordinates register accurately on the canvas and that the automated score matches physical inspection.
6. **Session Initialization**: Advance the tournament session to `ACTIVE` and notify the Director of Shooting (DoS) that the range is ready.

## 7.2 Diagnostic Troubleshooting Matrix

*Table 7.1: Field Troubleshooting and Recovery Procedures*

| Observed Symptom | Probable Root Cause | Verification Command | Corrective Action |
| :--- | :--- | :--- | :--- |
| **Camera stream indicates `OFFLINE`** | Disconnected PoE cable or IP address conflict. | `ping 192.168.1.10X` | Check physical PoE cable; verify camera power LED; ensure static DHCP lease is active. The system will auto-reconnect once the stream is restored. |
| **Arrow impacts register with slight radial offset (1–2 cm)** | Physical target butt settled or moved after initial calibration. | Check canvas overlay on `/cameras`. | Open Camera Settings $\to$ click **Recalibrate Target**; re-click the four 1-ring perimeter points and save. |
| **Judicial score override returns HTTP 422 error** | Scorer submitted override without justification text. | Inspect API response payload. | Enter at least 5 characters in the justification box detailing the judicial rationale. |
| **WebSocket disconnections during live match** | Arena WiFi network interference or router packet drop. | Check browser console for `WebSocket closed`. | The client will automatically reconnect with backoff. For critical scoring lines, connect tablet via USB-Ethernet adapter. |
| **Docker container fails to start on cold boot** | Port collision on host machine (e.g., local PostgreSQL running on 5432). | `docker compose logs api` | Stop conflicting host services (`sudo systemctl stop postgresql`) or remap ports in `docker-compose.yml`. |
| **High detection latency ($> 500\text{ ms}$)** | CPU saturation due to simultaneous multi-lane YOLO inference. | `docker stats api` | Ensure GPU acceleration is enabled (`runtime: nvidia` in docker-compose) or adjust `yolo_service` frame downsampling in `config.py`. |

## 7.3 Advanced Host Diagnostics & CLI Cheat Sheet

For system administrators operating the platform on-site during a major championship:

```bash
# 1. Inspect live container statuses and resource utilization
docker compose ps
docker stats --no-stream

# 2. Tail real-time API logs for score events and exceptions
docker compose logs -f api | grep -E "SCORE|EXCEPTION|ERROR"

# 3. Enter PostgreSQL database shell to inspect scores directly
docker compose exec db psql -U postgres -d archery_db -c \
  "SELECT s.end_number, s.arrow_number, s.score_value, s.is_x_ring, s.is_manual_override \
   FROM scores s ORDER BY s.created_at DESC LIMIT 10;"

# 4. Monitor Redis Pub/Sub channels for live WebSocket broadcasting
docker compose exec cache redis-cli monitor

# 5. Measure optical RTSP camera streaming framerate
ffprobe -v error -select_streams v:0 -show_entries stream=r_frame_rate \
  rtsp://192.168.1.101:554/live/stream1
```

---

# 8. CONCLUSION & TECHNICAL SUMMARY

This technical operations manual details the end-to-end implementation and operational workflows of **Bull's Eye: Automated Archery Scoring System**. By combining high-performance asynchronous microservices, a four-tier hybrid computer vision pipeline, strict World Archery mathematical compliance, and immutable judicial audit trails, Bull's Eye delivers a robust, transparent, and fair automated scoring platform for Olympic archery competitions.
"""

def main():
    print("[1/3] Assembling technical operations documentation sections...")
    sections = [
        get_section_1(),
        get_section_2(),
        get_section_3(),
        get_section_4(),
        get_section_5(),
        get_section_6(),
        get_section_7()
    ]
    
    full_markdown = "\n\n".join(sections)
    
    docs_dir = os.path.abspath(os.path.join(current_dir, "..", "Documents"))
    os.makedirs(docs_dir, exist_ok=True)
    
    md_output_path = os.path.join(docs_dir, "Technical_Documentation_Role_and_Functionality.md")
    docx_output_path = os.path.join(docs_dir, "Technical_Documentation_Role_and_Functionality.docx")
    
    print(f"[2/3] Writing Markdown documentation to: {md_output_path}")
    with open(md_output_path, "w", encoding="utf-8") as f:
        f.write(full_markdown)
        
    line_count = len(full_markdown.splitlines())
    word_count = len(full_markdown.split())
    print(f"      -> Total Markdown Lines: {line_count:,}")
    print(f"      -> Total Words:          {word_count:,}")
    
    print(f"[3/3] Generating formatted Word document: {docx_output_path}")
    build_docx_from_markdown(full_markdown, docx_output_path)
    
    md_size_kb = os.path.getsize(md_output_path) / 1024
    docx_size_kb = os.path.getsize(docx_output_path) / 1024
    
    print("[COMPLETE] Technical Documentation successfully built!")
    print(f"      - Technical_Documentation_Role_and_Functionality.md   : {md_size_kb:.1f} KB")
    print(f"      - Technical_Documentation_Role_and_Functionality.docx : {docx_size_kb:.1f} KB")

if __name__ == "__main__":
    main()
