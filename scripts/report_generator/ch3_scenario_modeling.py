"""
Chapter 3: Scenario-Based Modeling Module for Bull's Eye SPL-3 Final Technical Report.
Covers System Actors & Boundaries, Use Case Diagram, Detailed Use Case Specifications (UC-01 to UC-08),
Level-1 & Level-2 Activity Diagrams, and Sequence Diagrams for core workflows.
"""

def get_chapter_3():
    return r"""---

# CHAPTER 3: SCENARIO-BASED MODELING

## 3.1 System Actors & Boundary Identification

Scenario-based modeling captures the functional behavior of the system from the external perspective of its human and automated actors. The boundary of Bull's Eye encompasses the application server (FastAPI backend), relational database (PostgreSQL), in-memory cache and pub/sub broker (Redis), computer vision processing workers, and web-based user interfaces.

*Table 3.1: Actor Identification and Privilege Specification Matrix*

| Actor Name | Type | Access Level | Responsibilities and System Interactions |
| :--- | :--- | :--- | :--- |
| **Tournament Administrator** | Human | Full Admin | Manages system users, configures tournaments, registers archers, manages camera hardware, initiates sessions, and oversees system health. |
| **Line Judge / Scorer** | Human | Scorer / Official | Inspects high-resolution arrow impacts, resolves disputes, executes score overrides with mandatory audit justifications, and signs off on official ends. |
| **Archer / Competitor** | Human | Archer / View-Only | Views personal live score progression, inspects arrow impact groupings, reviews historical session analytics, and verifies scorecard accuracy. |
| **Spectator / Media** | Human | Public / Unauthenticated | Views real-time tournament leaderboards, current match standings, and public video graphics via WebSocket broadcast feeds. |
| **Camera Hardware** | Automated System | Stream Producer | Generates continuous RTSP video streams or captures high-resolution stills of target faces across competition lanes. |
| **Vision & Scoring Engine**| Automated Subsystem | Internal Worker | Ingests frames, applies homography, executes multi-tier detection, evaluates WA rules, persists scores, and triggers real-time events. |

## 3.2 Comprehensive Use Case Diagram

The functional interactions between external actors and the Bull's Eye system boundaries are illustrated in Figure 3.1.

```
+----------------------------------------------------------------------------------------------------+
|                               BULL'S EYE SYSTEM USE CASE DIAGRAM                                    |
|                                                                                                    |
|   +-------------------+                                                +-----------------------+   |
|   |   Administrator   |                                                |   Camera Hardware     |   |
|   +-------------------+                                                +-----------------------+   |
|             |                                                                      |               |
|             +-----( UC-01: Authenticate & Manage Users )                           |               |
|             |                                                                      |               |
|             +-----( UC-02: Configure Tournament & Sessions )                       |               |
|             |                                                                      |               |
|             +-----( UC-03: Manage & Calibrate Target Cameras ) <-------------------+               |
|             |          |                                                           |               |
|             |          +---<< includes >>---> ( Compute 4-Point Homography )       |               |
|             |                                                                      |               |
|             +-----( UC-08: Execute Batch Image Model Evaluation )                  |               |
|                                                                                    |               |
|   +-------------------+                                                            |               |
|   |  Vision Engine    | <----------------------------------------------------------+               |
|   +-------------------+                                                            | (Stream Frames|
|             |                                                                                      |
|             +-----( UC-04: Process Arrow Shot & Auto-Score )                                       |
|                        |                                                                           |
|                        +---<< includes >>---> ( 4-Tier Consensus & Fallback )                      |
|                        |                                                                           |
|                        +---<< includes >>---> ( Apply WA Line-Cutter Geometry )                    |
|                        |                                                                           |
|                        +---<< includes >>---> ( Persist Score & Broadcast WS )                     |
|                                                                                                    |
|   +-------------------+                                                                            |
|   |    Line Judge     |                                                                            |
|   +-------------------+                                                                            |
|             |                                                                                      |
|             +-----( UC-05: Review Arrow Impact & Override Score )                                  |
|             |          |                                                                           |
|             |          +---<< includes >>---> ( Record Cryptographic Audit Trail )                 |
|             |                                                                                      |
|             +-----( Finalize End & Confirm Lane Progression )                                      |
|                                                                                                    |
|   +-------------------+                                                                            |
|   |      Archer       |                                                                            |
|   +-------------------+                                                                            |
|             |                                                                                      |
|             +-----( View Personal Live Score & Grouping Canvas )                                   |
|             |                                                                                      |
|             +-----( View Historical Session Analytics )                                            |
|                                                                                                    |
|   +-------------------+                                                                            |
|   |  Spectator/Media  |                                                                            |
|   +-------------------+                                                                            |
|             |                                                                                      |
|             +-----( UC-06: View Real-Time Live Tournament Leaderboard )                            |
|             |                                                                                      |
|             +-----( UC-07: Download Official WA Match Scorecard PDF )                              |
+----------------------------------------------------------------------------------------------------+
```
*Figure 3.1: Bull's Eye Comprehensive System Use Case Diagram*

## 3.3 Detailed Use Case Specifications

This section specifies the eight critical use cases governing core system behavior, documenting actors, triggers, preconditions, normal flows, alternative paths, exception handling, and postconditions.

### Use Case UC-01: Authenticate User & Assign Role
*Table 3.2: Detailed Use Case Specification: UC-01 Authenticate User & Assign Role*

| Attribute | Specification Details |
| :--- | :--- |
| **Use Case ID** | **UC-01** |
| **Use Case Name** | Authenticate User and Assign Role |
| **Primary Actor** | Administrator, Line Judge, Archer |
| **Preconditions** | User account exists with valid password hash in PostgreSQL `users` table; system services active. |
| **Trigger** | User navigates to the login screen and submits email and password credentials. |
| **Normal Flow** | 1. Client submits POST `/api/v1/auth/login` with email and password payload.<br>2. Backend `auth_service` retrieves user record from PostgreSQL by email.<br>3. System verifies password using bcrypt hashing algorithm.<br>4. Backend generates signed JWT Access Token containing `user_id`, `role`, and expiration timestamp.<br>5. Client stores token in local storage / Zustand auth state and transitions to role-specific dashboard. |
| **Alternative Flow** | If user requests token refresh: Client submits POST `/api/v1/auth/refresh`; backend validates existing token and issues refreshed token without re-authentication. |
| **Exception Flow** | E1. Invalid credentials: System returns HTTP 401 Unauthorized with message *"Invalid email or password"*; client displays visual error alert.<br>E2. Account deactivated: System returns HTTP 403 Forbidden with message *"Account inactive"*. |
| **Postconditions** | User is authenticated with active session; authorized JWT attached to all subsequent HTTP requests. |

---

### Use Case UC-02: Configure Tournament & Lane Session
*Table 3.3: Detailed Use Case Specification: UC-02 Configure Tournament & Lane Session*

| Attribute | Specification Details |
| :--- | :--- |
| **Use Case ID** | **UC-02** |
| **Use Case Name** | Configure Tournament and Lane Session |
| **Primary Actor** | Tournament Administrator |
| **Preconditions** | Administrator is authenticated with `role = admin`. |
| **Trigger** | Administrator selects "Create Tournament" on the Tournaments dashboard. |
| **Normal Flow** | 1. Admin inputs tournament name, discipline (Recurve/Compound), target face size (122cm/80cm), total ends (12), arrows per end (6), and date.<br>2. Admin adds archers and assigns each to a competition lane.<br>3. Admin selects target camera for each lane.<br>4. Backend validates configuration, inserts tournament and session records into database, and initializes Redis session keys.<br>5. UI displays created tournament in active state. |
| **Alternative Flow** | Admin imports archer roster from CSV file; backend parses records, validates email uniqueness, and auto-generates credentials. |
| **Exception Flow** | E1. Camera already assigned: System alerts *"Camera assigned to active Lane X"*, prompting lane reassignment.<br>E2. Database constraint violation: System rolls back transaction and returns HTTP 400. |
| **Postconditions** | Tournament and session entities persisted in DB; lane cameras linked; ready for live match scoring. |

---

### Use Case UC-03: Calibrate Camera & Compute Homography Matrix
*Table 3.4: Detailed Use Case Specification: UC-03 Calibrate Camera & Compute Homography Matrix*

| Attribute | Specification Details |
| :--- | :--- |
| **Use Case ID** | **UC-03** |
| **Use Case Name** | Calibrate Camera and Compute Homography Matrix |
| **Primary Actor** | Tournament Administrator / Line Judge |
| **Preconditions** | Camera is online and streaming; target face is positioned in field of view. |
| **Trigger** | User navigates to Camera Management and clicks "Calibrate Target". |
| **Normal Flow** | 1. System captures a high-resolution snapshot from camera stream.<br>2. UI displays target frame on interactive canvas.<br>3. User clicks four reference points on outer 1-ring perimeter (Top, Right, Bottom, Left) or target corners.<br>4. System computes $3 \times 3$ perspective homography matrix $H$ mapping pixel coordinates to normalized metric plane.<br>5. System overlays warped circular target model over camera feed for visual verification.<br>6. User clicks "Save Calibration"; backend stores matrix in `cameras.calibration_matrix`. |
| **Alternative Flow** | Automated target detection: Vision engine executes Hough circle detection; if confident ($\ge 0.95$), automatically suggests 4 reference coordinates. |
| **Exception Flow** | E1. Degenerate points (collinear or self-intersecting): System alerts *"Invalid quadrilateral geometry; points cannot be collinear"*; requests re-selection. |
| **Postconditions** | Valid homography matrix persisted; camera marked `calibrated = true`; all subsequent shots automatically rectified. |

---

### Use Case UC-04: Process Arrow Shot & Calculate Score
*Table 3.5: Detailed Use Case Specification: UC-04 Process Arrow Shot & Calculate Score*

| Attribute | Specification Details |
| :--- | :--- |
| **Use Case ID** | **UC-04** |
| **Use Case Name** | Process Arrow Shot and Calculate Score |
| **Primary Actor** | Vision & Scoring Engine (Automated) |
| **Preconditions** | Active session; lane camera calibrated; archer ready on lane. |
| **Trigger** | Arrow impacts target face; optical frame captured or uploaded via POST `/api/v1/scores/detect`. |
| **Normal Flow** | 1. Engine applies perspective homography matrix $H$ to rectify frame.<br>2. Pipeline executes 4-tier detection: morphological puncture difference, quadratic line-ellipse intersection, YOLO11 inference, HSV segmentation.<br>3. Consensus engine computes weighted centroid $(x_c, y_c)$ and confidence score $\ge 0.80$.<br>4. Scoring engine computes radial distance $r = \sqrt{x_c^2 + y_c^2}$ from target center $(0,0)$.<br>5. Engine applies WA radial zone boundaries and tests line-cutter tangency condition ($r - \delta \le R_z$).<br>6. System assigns zone score (10–1 or 0) and evaluates Inner-10 (X) flag.<br>7. Score record persisted to `scores` table.<br>8. Redis cache invalidated; WebSocket event `SCORE_RECORDED` broadcast to all lane subscribers. |
| **Alternative Flow** | Single algorithm failure: If YOLO11 detects no shaft due to shadow, puncture morphology + line-ellipse consensus proceeds with confidence $\ge 0.85$. |
| **Exception Flow** | E1. Total detection failure (confidence $< 0.40$): System creates pending score flagged `requires_manual_review = true` and alerts Line Judge via WebSocket. |
| **Postconditions** | Arrow score permanently recorded in PostgreSQL; live scoreboard and target canvas updated across all connected devices in $< 200\text{ ms}$. |

---

### Use Case UC-05: Review Arrow Impact & Override Score (Judge Audit)
*Table 3.6: Detailed Use Case Specification: UC-05 Review & Override Arrow Score (Judge Audit)*

| Attribute | Specification Details |
| :--- | :--- |
| **Use Case ID** | **UC-05** |
| **Use Case Name** | Review and Override Arrow Score (Judge Audit) |
| **Primary Actor** | Certified Line Judge |
| **Preconditions** | Judge is authenticated with `role = scorer` or `admin`; score record exists. |
| **Trigger** | Judge inspects contested shot or responds to `requires_manual_review` alert. |
| **Normal Flow** | 1. Judge opens Scoring Review console for specific lane and end.<br>2. System displays high-resolution zoomed crop of impact point with shaft diameter and dividing ring overlays.<br>3. Judge evaluates physical contact and clicks "Override Score".<br>4. Judge selects corrected score value (e.g., from 9 to 10), toggles X-ring flag, and enters mandatory justification note.<br>5. Client submits PUT `/api/v1/scores/{score_id}`.<br>6. Backend verifies Judge privileges, updates `scores` record (`is_manual_override = true`), and inserts comprehensive entry into `audit_logs` table recording original score, new score, judge user ID, timestamp, and justification.<br>7. Backend invalidates leaderboard cache and broadcasts WebSocket event `SCORE_OVERRIDDEN`. |
| **Alternative Flow** | Judge confirms algorithm was correct: Judge clicks "Verify Score"; system marks `verified_by = judge_id` without altering values. |
| **Exception Flow** | E1. Missing justification: System rejects override with HTTP 422 Unprocessable Entity (*"Justification text is required for score overrides"*). |
| **Postconditions** | Database score updated; immutable audit record saved; clients dynamically updated with judicial badge indicator. |

---

### Use Case UC-06: Broadcast Live Leaderboard & Stream Session
*Table 3.7: Detailed Use Case Specification: UC-06 Broadcast Live Leaderboard & Stream Session*

| Attribute | Specification Details |
| :--- | :--- |
| **Use Case ID** | **UC-06** |
| **Use Case Name** | Broadcast Live Leaderboard and Stream Session |
| **Primary Actor** | Spectator / Media Producer / Archer |
| **Preconditions** | Active tournament session in progress; Redis cache operational. |
| **Trigger** | Client opens Leaderboard view or connects to WebSocket `/ws/{session_id}`. |
| **Normal Flow** | 1. Client establishes WebSocket connection; server accepts and registers client in session channel.<br>2. Backend queries Redis for cached leaderboard; if cache miss, queries PostgreSQL with optimized SQL aggregating total points, 10s count, and Xs count, ordering by `total_score DESC, num_tens DESC, num_xs DESC`.<br>3. Backend sends serialized leaderboard JSON to client.<br>4. On subsequent arrow scores, Redis pub/sub pushes delta updates over WebSocket; client smoothly animates position changes. |
| **Alternative Flow** | Client requests REST fallback: GET `/api/v1/leaderboard/{tournament_id}` returns cached snapshot. |
| **Exception Flow** | E1. WebSocket connection drops: Client automatically initiates reconnect with exponential backoff; pulls latest state via REST upon reconnect. |
| **Postconditions** | Client display continuously synchronized with official match scores with sub-100 ms latency. |

---

### Use Case UC-07: Generate & Export Official Match Report (PDF)
*Table 3.8: Detailed Use Case Specification: UC-07 Generate & Export Official Match Report (PDF)*

| Attribute | Specification Details |
| :--- | :--- |
| **Use Case ID** | **UC-07** |
| **Use Case Name** | Generate and Export Official Match Report (PDF) |
| **Primary Actor** | Tournament Administrator, Archer, Judge |
| **Preconditions** | Match or tournament session has recorded scores. |
| **Trigger** | User clicks "Export PDF Scorecard" on Reports dashboard. |
| **Normal Flow** | 1. Client submits GET `/api/v1/reports/session/{session_id}/pdf`.<br>2. Backend `report_service` queries database for session details, archer profiles, complete end-by-end arrow breakdowns, and audit overrides.<br>3. ReportLab engine compiles vector layout: header with World Archery branding, athlete metadata, structured end-by-end grid, cumulative totals, 10s/Xs summary, and signature blocks.<br>4. ReportLab renders binary PDF in memory.<br>5. Backend streams PDF with header `Content-Disposition: attachment; filename="scorecard_{session_id}.pdf"`.<br>6. Browser initiates download. |
| **Alternative Flow** | Tournament-wide summary: GET `/api/v1/reports/tournament/{id}/pdf` compiles all lanes into multi-page official tournament result book. |
| **Exception Flow** | E1. No scores found: Backend returns HTTP 404 with message *"No score records available for this session"*. |
| **Postconditions** | Official, print-ready PDF document successfully generated and delivered to user. |

---

### Use Case UC-08: Execute Batch Image Model Evaluation
*Table 3.9: Detailed Use Case Specification: UC-08 Execute Batch Image Model Evaluation*

| Attribute | Specification Details |
| :--- | :--- |
| **Use Case ID** | **UC-08** |
| **Use Case Name** | Execute Batch Image Model Evaluation |
| **Primary Actor** | Tournament Administrator / CV Researcher |
| **Preconditions** | Administrator authenticated; annotated evaluation dataset uploaded to server storage. |
| **Trigger** | User initiates batch testing via POST `/api/v1/scores/batch-test`. |
| **Normal Flow** | 1. System receives batch testing configuration (model weights, confidence threshold, dataset directory).<br>2. Background worker iterates through test frames, executing computer vision pipeline for each.<br>3. System compares predicted impact coordinates and zone scores against ground-truth annotations.<br>4. Computes evaluation metrics: Mean Radial Error (mm), Intersection over Union (IoU), Precision, Recall, F1-Score, and Zone Classification Accuracy.<br>5. Returns structured JSON report and displays confusion matrix on UI. |
| **Alternative Flow** | User uploads a single ZIP file containing test images and COCO JSON annotations. |
| **Exception Flow** | E1. Invalid annotation format: System returns HTTP 422 with validation errors detailing missing fields. |
| **Postconditions** | Empirical evaluation completed and recorded; performance report available for download. |

## 3.4 Activity Diagrams

Activity diagrams model the dynamic operational workflows of Bull's Eye. Figure 3.2 illustrates the high-level tournament match execution (Level-1), Figure 3.3 details the internal Computer Vision and fallback pipeline (Level-2), and Figure 3.4 models the judicial review and score override workflow.

### 3.4.1 Level-1 Activity Diagram: Tournament End-to-End Match Workflow
```
+---------------------------------------------------------------------------------------------------+
|                        LEVEL-1 ACTIVITY DIAGRAM: TOURNAMENT MATCH WORKFLOW                        |
|                                                                                                   |
|     ( Start )                                                                                     |
|         |                                                                                         |
|         v                                                                                         |
|  [ Admin Configures Tournament & Sessions ]                                                       |
|         |                                                                                         |
|         v                                                                                         |
|  [ System Ingests Camera Feeds & Executes Homography Calibration ]                                |
|         |                                                                                         |
|         v                                                                                         |
|  [ Archers Take Firing Line; Session Commences ]                                                  |
|         |                                                                                         |
|    +--->+                                                                                         |
|    |    |                                                                                         |
|    |    v                                                                                         |
|    |  [ Archer Shoots Arrow; Optical Sensor Captures Frame ]                                      |
|    |    |                                                                                         |
|    |    v                                                                                         |
|    |  [ Computer Vision & Scoring Engine Processes Impact ]                                       |
|    |    |                                                                                         |
|    |    v                                                                                         |
|    |  [ System Persists Score & Broadcasts Live WebSocket Frame ]                                 |
|    |    |                                                                                         |
|    |    v                                                                                         |
|    |  < Any Line Judge Dispute? >                                                                 |
|    |       |                    |                                                                 |
|    |      (Yes)                (No)                                                               |
|    |       |                    |                                                                 |
|    |       v                    |                                                                 |
|    |  [ Judge Inspects Crop     |                                                                 |
|    |    & Overrides with Audit] |                                                                 |
|    |       |                    |                                                                 |
|    |       +--------->+<--------+                                                                 |
|    |                  |                                                                           |
|    |                  v                                                                           |
|    |          < End Complete (6 Arrows)? >                                                        |
|    |                  |                  |                                                        |
|    |                 (No)               (Yes)                                                     |
|    |                  |                  |                                                        |
|    +------------------+                  v                                                        |
|                                  < All Ends Complete? >                                           |
|                                          |            |                                           |
|                                         (No)         (Yes)                                        |
|                                          |            |                                           |
|                                          v            v                                           |
|                       [ Reset Target Face /     [ Finalize Official Standings &                   |
|                         Clear Arrows ]            Generate ReportLab PDF Scorecard ]              |
|                              |                        |                                           |
|                              +----------------------->|                                           |
|                                                       v                                           |
|                                                    ( End )                                        |
+---------------------------------------------------------------------------------------------------+
```
*Figure 3.2: Level-1 Activity Diagram: High-Level Tournament End-to-End Match Workflow*

### 3.4.2 Level-2 Activity Diagram: Multi-Tier Computer Vision Pipeline
```
+---------------------------------------------------------------------------------------------------+
|               LEVEL-2 ACTIVITY DIAGRAM: MULTI-TIER COMPUTER VISION & SCORING PIPELINE              |
|                                                                                                   |
|    ( Input Frame Ingestion )                                                                      |
|                |                                                                                  |
|                v                                                                                  |
|    [ Apply 3x3 Perspective Homography Warp ]                                                      |
|                |                                                                                  |
|    +-----------+-----------------------+----------------------+                                   |
|    |                                   |                      |                                   |
|    v                                   v                      v                                   |
| [ Tier 1: Puncture Morphology ]    [ Tier 2: Line-Ellipse ]  [ Tier 3: YOLO11 DL ]                |
|    |                                   |                      |                                   |
|    +-----------+-----------------------+----------------------+                                   |
|                |                                                                                  |
|                v                                                                                  |
|    [ Weighted Consensus Engine Evaluates Coordinates & Confidence ]                               |
|                |                                                                                  |
|                v                                                                                  |
|    < Consensus Confidence >= 0.70? >                                                              |
|         |                          |                                                              |
|       (Yes)                       (No)                                                            |
|         |                          |                                                              |
|         |                          v                                                              |
|         |                 [ Execute Tier 4: HSV Color Segmentation ]                              |
|         |                          |                                                              |
|         |                 < Fallback Successful? >                                                |
|         |                      |             |                                                    |
|         |                    (Yes)          (No)                                                  |
|         |                      |             |                                                    |
|         |                      |             v                                                    |
|         |                      |     [ Flag Score: requires_manual_review ]                       |
|         |                      |             |                                                    |
|         +--------------------->+<------------+                                                    |
|                                |                                                                  |
|                                v                                                                  |
|    [ Calculate Euclidean Radius r = sqrt(x^2 + y^2) from Target Center ]                          |
|                                |                                                                  |
|                                v                                                                  |
|    [ Evaluate World Archery Radial Boundaries & Line-Cutter Tangency ]                            |
|                                |                                                                  |
|                                v                                                                  |
|    [ Determine Point Value (10..0) & Inner-10 (X) Status ]                                        |
|                                |                                                                  |
|                                v                                                                  |
|    [ Persist to PostgreSQL `scores` Table ]                                                       |
|                                |                                                                  |
|                                v                                                                  |
|    [ Invalidate Redis Cache & Broadcast WebSocket Event ]                                         |
|                                |                                                                  |
|                                v                                                                  |
|                             ( Done )                                                              |
+---------------------------------------------------------------------------------------------------+
```
*Figure 3.3: Level-2 Activity Diagram: Multi-Tier Computer Vision & Fallback Scoring Pipeline*

### 3.4.3 Level-2 Activity Diagram: Judge Score Override & Audit Synchronization
```
+---------------------------------------------------------------------------------------------------+
|             LEVEL-2 ACTIVITY DIAGRAM: JUDGE SCORE OVERRIDE & AUDIT SYNCHRONIZATION                |
|                                                                                                   |
|    ( Judge Selects Contested Score )                                                              |
|                 |                                                                                 |
|                 v                                                                                 |
|    [ System Renders High-Resolution Zoom Crop with Tangency Overlays ]                            |
|                 |                                                                                 |
|                 v                                                                                 |
|    [ Judge Reviews Physical Impact vs Algorithm Decision ]                                       |
|                 |                                                                                 |
|                 v                                                                                 |
|    < Score Requires Modification? >                                                               |
|         |                         |                                                               |
|       (Yes)                      (No)                                                             |
|         |                         |                                                               |
|         |                         v                                                               |
|         |                 [ Click "Confirm Algorithm Score" ]                                     |
|         |                         |                                                               |
|         v                         v                                                               |
|    [ Select New Score Value & Toggle X-Ring ]                                                     |
|         |                                                                                         |
|         v                                                                                         |
|    [ Enter Mandatory Justification Text ]                                                         |
|         |                                                                                         |
|         v                                                                                         |
|    < Justification Provided? >                                                                    |
|         |                    |                                                                    |
|       (Yes)                 (No)                                                                  |
|         |                    |                                                                    |
|         |                    v                                                                    |
|         |         [ Display Validation Error Alert ]                                              |
|         |                    |                                                                    |
|         |                    +----> ( Return to Input )                                           |
|         v                                                                                         |
|    [ Submit PUT /api/v1/scores/{score_id} ]                                                       |
|         |                                                                                         |
|         v                                                                                         |
|    [ Backend Begins ACID Database Transaction ]                                                   |
|         |                                                                                         |
|         v                                                                                         |
|    [ Update `scores`: new value, is_manual_override=True ]                                        |
|         |                                                                                         |
|         v                                                                                         |
|    [ Insert `audit_logs`: original, new, judge_id, timestamp, reason ]                            |
|         |                                                                                         |
|         v                                                                                         |
|    [ Commit Transaction; Invalidate Redis Leaderboard Cache ]                                     |
|         |                                                                                         |
|         v                                                                                         |
|    [ Broadcast `SCORE_OVERRIDDEN` Event to Connected Clients ]                                    |
|         |                                                                                         |
|         v                                                                                         |
|      ( Done )                                                                                     |
+---------------------------------------------------------------------------------------------------+
```
*Figure 3.4: Level-2 Activity Diagram: Judge Score Override & Audit Synchronization Workflow*

## 3.5 Sequence Diagrams

Sequence diagrams illustrate the time-ordered message passing between client applications, API controllers, domain services, database connections, and cache brokers.

### 3.5.1 Sequence Diagram 1: Automated Image Ingestion and Real-Time Scoring Flow
```
+----------------------------------------------------------------------------------------------------+
|               SEQUENCE DIAGRAM 1: AUTOMATED IMAGE INGESTION & REAL-TIME SCORING FLOW               |
|                                                                                                    |
|  Camera        Client UI       FastAPI API      CV Engine      Scoring Svc    PostgreSQL    Redis  |
|    |               |                |               |               |              |          |    |
|    |--Image Frame->|                |               |               |              |          |    |
|    |               |--POST /detect->|               |               |              |          |    |
|    |               |                |--Process----->|               |              |          |    |
|    |               |                |   (Frame, H)  |               |              |          |    |
|    |               |                |               |--Detect------>|              |          |    |
|    |               |                |               |  (Shaft, Tip) |              |          |    |
|    |               |                |               |               |--Calc Score--|          |    |
|    |               |                |               |               |  (WA Rules)  |          |    |
|    |               |                |               |               |              |--INSERT->|    |
|    |               |                |               |               |              |  Score   |    |
|    |               |                |               |               |              |<-Success-|    |
|    |               |                |               |               |              |          |--Del|
|    |               |                |               |               |              |          | Cache|
|    |               |                |               |               |              |          |<-OK--|
|    |               |                |               |               |              |          |--Pub-|
|    |               |                |               |               |              |          |Event |
|    |               |                |<--Score JSON--+---------------+--------------+----------+    |
|    |               |<--HTTP 201 OK--|                                                              |
|    |               |                |                                                              |
|    |               |<======================= WS Event: SCORE_RECORDED =============================|
|    |               |  (Renders arrow pulse on target canvas & updates scoreboard in <182ms)        |
+----------------------------------------------------------------------------------------------------+
```
*Figure 3.5: Sequence Diagram 1: Automated Image Ingestion and Real-Time Scoring Flow*

### 3.5.2 Sequence Diagram 2: Manual Line Judge Override & Audit Trail Logging Flow
```
+----------------------------------------------------------------------------------------------------+
|            SEQUENCE DIAGRAM 2: MANUAL LINE JUDGE OVERRIDE & AUDIT TRAIL LOGGING FLOW               |
|                                                                                                    |
|  Line Judge UI             FastAPI Router           Audit Service          PostgreSQL       Redis  |
|        |                          |                       |                     |             |    |
|        |--PUT /api/v1/scores/{id}->|                       |                     |             |    |
|        |  {value:10, reason:"..."}|                       |                     |             |    |
|        |                          |--Verify Judge Token-->|                     |             |    |
|        |                          |--Begin Transaction--->|                     |             |    |
|        |                          |                       |--Fetch Original---->|             |    |
|        |                          |                       |<-Old Score Data-----|             |    |
|        |                          |                       |--UPDATE Score------>|             |    |
|        |                          |                       |--INSERT AuditLog--->|             |    |
|        |                          |                       |<-Commit Success-----|             |    |
|        |                          |                       |                     |--Del Cache->|    |
|        |                          |                       |                     |<-Cache Clear|    |
|        |                          |                       |                     |--Publish--->|    |
|        |                          |                       |                     |  OVERRIDE   |    |
|        |<--HTTP 200 (Updated)-----|                       |                     |             |    |
|        |                                                                                      |    |
|        |<=================== Broadcast WS: SCORE_OVERRIDDEN ===================================|    |
|        | (All connected lane displays display judicial gavel badge and updated ranking)            |
+----------------------------------------------------------------------------------------------------+
```
*Figure 3.6: Sequence Diagram 2: Manual Line Judge Override & Audit Trail Logging Flow*

### 3.5.3 Sequence Diagram 3: Tournament Session Creation & Multi-Lane Archer Assignment Flow
```
+----------------------------------------------------------------------------------------------------+
|          SEQUENCE DIAGRAM 3: TOURNAMENT SESSION CREATION & ARCHER ASSIGNMENT FLOW                  |
|                                                                                                    |
|  Admin UI              FastAPI Router         Session Service        PostgreSQL             Redis  |
|     |                         |                      |                    |                   |    |
|     |--POST /api/v1/sessions->|                      |                    |                   |    |
|     |  {tourn_id, lanes:[...]} |                      |                    |                   |    |
|     |                         |--Validate Input----->|                    |                   |    |
|     |                         |--Verify Cameras----->|                    |                   |    |
|     |                         |                      |--INSERT Session--->|                   |    |
|     |                         |                      |--INSERT Archers--->|                   |    |
|     |                         |                      |--INSERT Lane Cam-->|                   |    |
|     |                         |                      |<-Transaction OK----|                   |    |
|     |                         |                      |                    |--Init Key-------->|    |
|     |                         |                      |                    |  Session State    |    |
|     |                         |                      |                    |<-Acknowledge------|    |
|     |<--HTTP 201 Created------|                      |                    |                   |    |
|     |   (Session ID, Lanes)   |                      |                    |                   |    |
+----------------------------------------------------------------------------------------------------+
```
*Figure 3.7: Sequence Diagram 3: Tournament Session Creation & Multi-Lane Archer Assignment Flow*
"""
