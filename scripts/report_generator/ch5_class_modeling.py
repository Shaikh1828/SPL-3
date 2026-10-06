"""
Chapter 5: Class-Based Modeling Module for Bull's Eye SPL-3 Final Technical Report.
Covers Analysis Class Diagram, Class Responsibility Collaborator (CRC) Cards,
and Collaboration & Interaction Matrix.
"""

def get_chapter_5():
    return r"""---

# CHAPTER 5: CLASS-BASED MODELING

## 5.1 Analysis Class Diagram

Class-based modeling formalizes the static structural taxonomy of the Bull's Eye application. In accordance with object-oriented software engineering principles, system classes are categorized into three standard archetypes:
1. **Boundary (Presentation / Interface) Classes**: Intermediaries that manage interactions between external actors, hardware devices, and internal services (e.g., `AuthController`, `ScoringController`, `WebSocketHandler`).
2. **Control (Service / Business Logic) Classes**: Orchestrators encapsulating business rules, algorithmic computer vision logic, and state transitions (e.g., `ScoringService`, `ArrowDetectionService`, `LeaderboardService`).
3. **Entity (Domain / Persistence) Classes**: Information holders representing core relational domain models mapped to the PostgreSQL database (e.g., `User`, `Tournament`, `Session`, `Score`, `Camera`, `AuditLog`).

```
+----------------------------------------------------------------------------------------------------+
|                                    ANALYSIS CLASS DIAGRAM                                          |
|                                                                                                    |
|  << Boundary >>                    << Control >>                          << Entity >>             |
|  +--------------------+            +------------------------+             +-------------------+    |
|  | AuthController     |            | AuthService            |             | User              |    |
|  |--------------------|            |------------------------|             |-------------------|    |
|  | + login()          |----------->| + authenticate_user()  |------------>| - id: UUID        |    |
|  | + register()       |            | + create_access_token()|             | - email: str      |    |
|  | + refresh_token()  |            | + hash_password()      |             | - role: str       |    |
|  +--------------------+            +------------------------+             +-------------------+    |
|                                                                                     ^              |
|  << Boundary >>                    << Control >>                                    |              |
|  +--------------------+            +------------------------+                       |              |
|  | ScoringController  |            | ScoringService         |                       |              |
|  |--------------------|            |------------------------|                       |              |
|  | + detect_arrow()   |----------->| + evaluate_score()     |                       |              |
|  | + override_score() |            | + check_line_cutter()  |                       |              |
|  | + get_scores()     |            +------------------------+                       |              |
|  +--------------------+                        |                                    |              |
|            |                                   v                                    |              |
|            |                       << Control >>                                    |              |
|            |                       +------------------------+                       |              |
|            |                       | ArrowDetectionService  |                       |              |
|            |                       |------------------------|                       |              |
|            |                       | + detect_impact()      |                       |              |
|            |                       | + morphology_detect()  |                       |              |
|            |                       | + yolo_inference()     |                       |              |
|            |                       | + consensus_voting()   |                       |              |
|            |                       +------------------------+                       |              |
|            v                                   |                                    |              |
|  << Boundary >>                                v                                    v              |
|  +--------------------+            << Entity >>                           << Entity >>             |
|  | WebSocketHandler   |            +------------------------+             +-------------------+    |
|  |--------------------|            | Score                  |             | SessionArcher     |    |
|  | + connect()        |            |------------------------|             |-------------------|    |
|  | + broadcast()      |<-----------| - id: UUID             |             | - lane_number: int|    |
|  | + disconnect()     |            | - score_value: int     |             | - target_num: str |    |
|  +--------------------+            | - is_x_ring: bool      |             +-------------------+    |
|                                    | - x_coord, y_coord     |                       ^              |
|  << Boundary >>                    | - is_override: bool    |                       |              |
|  +--------------------+            +------------------------+                       |              |
|  | CameraController   |                        |                                    |              |
|  |--------------------|                        v                                    v              |
|  | + add_camera()     |            << Entity >>                           << Entity >>             |
|  | + calibrate_cam()  |            +------------------------+             +-------------------+    |
|  | + stream_preview() |            | AuditLog               |             | Session           |    |
|  +--------------------+            |------------------------|             |-------------------|    |
|            |                       | - original_score: int  |             | - id: UUID        |    |
|            v                       | - new_score: int       |             | - status: str     |    |
|  << Control >>                     | - judge_id: UUID       |             | - current_end: int|    |
|  +--------------------+            | - override_reason: str |             +-------------------+    |
|  | CameraService      |            +------------------------+                       ^              |
|  |--------------------|                                                             |              |
|  | + compute_H_matrix |                                                             v              |
|  | + warp_frame()     |                                                   << Entity >>             |
|  | + ping_stream()    |                                                   +-------------------+    |
|  +--------------------+                                                   | Tournament        |    |
|                                                                           |-------------------|    |
|                                                                           | - name: str       |    |
|                                                                           | - target_face_type|    |
|                                                                           +-------------------+    |
+----------------------------------------------------------------------------------------------------+
```
*Figure 5.1: Bull's Eye Analysis Class Diagram*

## 5.2 Class Responsibility Collaborator (CRC) Cards

Class Responsibility Collaborator (CRC) modeling provides an effective index of responsibilities allocated across core subsystem classes and identifies their required collaborators.

### CRC-01: User & Authentication Domain
- **Class**: `AuthService`
- **Package**: `src.services.auth_service`
- **Stereotype**: Control / Service
- **Responsibilities**:
  1. Authenticate user credentials against bcrypt hashes stored in PostgreSQL.
  2. Generate cryptographically signed JSON Web Tokens (JWT) containing user ID, email, and role claims.
  3. Validate and decode inbound JWT tokens on protected REST endpoints.
  4. Enforce role-based access control (Admin, Scorer, Archer).
- **Collaborators**: `UserRepository`, `PasswordHasher`, `JWTManager`, `User`.

---

### CRC-02: ScoringEngine & ArrowDetector Domain
- **Class**: `ScoringService`
- **Package**: `src.services.scoring_service`
- **Stereotype**: Control / Service
- **Responsibilities**:
  1. Receive rectified Cartesian coordinates $(x, y)$ of arrow impact points.
  2. Compute Euclidean distance $r = \sqrt{x^2 + y^2}$ from the calibrated target origin.
  3. Map Euclidean distance against World Archery 10-ring radial boundaries.
  4. Evaluate geometric line-cutter tangency conditions using shaft diameter tolerance ($\delta = 2.5\text{ mm}$).
  5. Check Inner-10 (X-ring) criteria.
  6. Delegate physical arrow impact detection to `ArrowDetectionService`.
  7. Persist calculated scores and trigger cache invalidation.
- **Collaborators**: `ArrowDetectionService`, `Score`, `AuditLog`, `RedisCache`, `WebSocketManager`.

---

### CRC-03: ArrowDetectionService Domain
- **Class**: `ArrowDetectionService`
- **Package**: `src.services.arrow_detection_service`
- **Stereotype**: Control / Computer Vision
- **Responsibilities**:
  1. Apply perspective homography matrix $H$ to transform raw camera frames into planar target space.
  2. Execute morphological difference imaging to locate puncture holes.
  3. Solve analytical quadratic line-ellipse intersection equations.
  4. Invoke `YoloDetectionService` for deep learning shaft and nock inference.
  5. Apply adaptive HSV color segmentation as a fallback boundary check.
  6. Execute weighted consensus fusion to output the final coordinates $(x_c, y_c)$ and confidence metric.
- **Collaborators**: `YoloDetectionService`, `CameraService`, `OpenCVEngine`, `ScoringService`.

---

### CRC-04: SessionManager & TournamentDomain
- **Class**: `TournamentService`
- **Package**: `src.services.tournament_service`
- **Stereotype**: Control / Domain
- **Responsibilities**:
  1. Create and manage tournament lifecycles (Scheduled, Active, Completed).
  2. Allocate archers and cameras to physical target lanes.
  3. Advance session state end-by-end upon judicial confirmation.
  4. Ensure referential integrity across multi-lane matches.
- **Collaborators**: `Tournament`, `Session`, `SessionArcher`, `Camera`, `DatabaseSession`.

---

### CRC-05: LeaderboardManager & NotificationEngine
- **Class**: `LeaderboardService`
- **Package**: `src.services.leaderboard_service`
- **Stereotype**: Control / Real-Time
- **Responsibilities**:
  1. Aggregate total scores, 10s count, and Xs count for all archers in a tournament.
  2. Apply official World Archery tie-breaking rules (`total_score DESC`, `num_tens DESC`, `num_xs DESC`).
  3. Cache calculated standings in Redis with a 60-second TTL.
  4. Invalidate cache instantly upon `SCORE_RECORDED` or `SCORE_OVERRIDDEN` events.
  5. Publish real-time ranking payloads across WebSocket channels.
- **Collaborators**: `ScoreRepository`, `RedisCache`, `WebSocketManager`.

---

### CRC-06: AuditLogger & ComplianceEngine
- **Class**: `AuditService`
- **Package**: `src.services.audit_service`
- **Stereotype**: Control / Audit
- **Responsibilities**:
  1. Intercept manual score override requests from certified judges.
  2. Validate that mandatory justification text is present.
  3. Persist original score, overridden score, judge ID, and timestamp into `audit_logs` in an ACID transaction.
  4. Mark target score record with `is_manual_override = True`.
  5. Generate compliance reports for tournament directors and federations.
- **Collaborators**: `AuditLog`, `Score`, `UserRepository`, `DatabaseSession`.

*Table 5.1: Class Responsibility Collaborator (CRC) Specification Matrix*

| CRC ID | Class Name | Layer / Stereotype | Primary Responsibility | Primary Collaborators |
| :--- | :--- | :--- | :--- | :--- |
| **CRC-01** | `AuthService` | Application / Control | User authentication, password hashing, JWT lifecycle | `User`, `DatabaseSession` |
| **CRC-02** | `ScoringService` | Domain / Control | WA 10-ring calculation, line-cutter geometry, score award | `ArrowDetectionService`, `Score` |
| **CRC-03** | `ArrowDetectionService`| Vision / Control | Homography warp, multi-tier CV consensus, puncture detection| `YoloDetectionService`, `CameraService`|
| **CRC-04** | `TournamentService` | Domain / Control | Tournament scheduling, lane allocation, session progression | `Tournament`, `Session`, `Camera` |
| **CRC-05** | `LeaderboardService` | Application / Real-Time | Rank aggregation, WA tie-breaking, Redis caching | `Score`, `RedisCache`, `WebSocketManager`|
| **CRC-06** | `AuditService` | Governance / Control | Judicial override tracking, immutable audit trails | `AuditLog`, `Score`, `User` |

## 5.3 Collaboration and Interaction Matrix

The collaboration matrix maps the cross-domain invocation dependencies between system control classes and entities:

```
+---------------------------------------------------------------------------------------+
|                         CLASS COLLABORATION & INVOCATION MATRIX                       |
|                                                                                       |
|   Caller Class           Invoked Class           Purpose of Invocation                |
|---------------------------------------------------------------------------------------|
|   AuthController         AuthService             Verify credentials & issue JWT tokens|
|   ScoringController      ScoringService          Process raw shot or manual override  |
|   ScoringService         ArrowDetectionService   Extract impact point coordinates     |
|   ArrowDetectionService  CameraService           Fetch 3x3 homography matrix          |
|   ArrowDetectionService  YoloDetectionService    Run YOLO11 deep learning inference   |
|   ScoringService         DatabaseSession         Persist Score entity to PostgreSQL   |
|   ScoringService         RedisCache              Invalidate leaderboard cache         |
|   ScoringService         WebSocketManager        Broadcast live SCORE_RECORDED event  |
|   AuditService           DatabaseSession         Insert immutable AuditLog entry      |
|   LeaderboardService     ScoreRepository         Aggregate match standings query      |
|   ReportService          DatabaseSession         Extract session scores for PDF doc   |
+---------------------------------------------------------------------------------------+
```
"""
