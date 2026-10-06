"""
Chapter 8: Component-Level Design & Code Implementation Module for Bull's Eye SPL-3 Final Technical Report.
Covers Backend Component Architecture, Detailed Backend Service Implementations & Critical Code Walkthroughs,
Frontend Architecture (React 18 + Zustand), and Real-Time WebSocket Communication Pipeline.
"""

def get_chapter_8():
    return r"""---

# CHAPTER 8: COMPONENT-LEVEL DESIGN & CODE IMPLEMENTATION

## 8.1 Backend Component Architecture & Core Bootstrap

The Bull's Eye backend is engineered using **FastAPI** (Python 3.11), leveraging asynchronous coroutines (`async`/`await`) to deliver high concurrent request throughput while offloading CPU-intensive computer vision algorithms to dedicated execution threads via `asyncio.to_thread`.

```
+----------------------------------------------------------------------------------------------------+
|                         BACKEND SERVICE-ORIENTED COMPONENT ARCHITECTURE                            |
|                                                                                                    |
|  [main.py]                                                                                         |
|   - Lifespan Manager: Initializes Database Pools & Redis Connections                               |
|   - Global Middleware: CORS Policy, Structured JSON Access Logging, Timing Headers                |
|   - API Routers: /auth, /tournaments, /sessions, /scores, /cameras, /leaderboard, /reports         |
|         |                                                                                          |
|         +------------------------------------------------------------------+                       |
|         |                                                                  |                       |
|         v                                                                  v                       |
|  [src.core]                                                         [src.services]                 |
|   - config.py: Pydantic BaseSettings (.env loader)                   - arrow_detection_service.py  |
|   - database.py: SQLAlchemy async_sessionmaker & engine              - yolo_detection_service.py   |
|   - redis.py: Redis AsyncClient connection pool                      - scoring_service.py          |
|   - security.py: Passlib bcrypt & python-jose JWT utils              - leaderboard_service.py      |
|   - exceptions.py: Custom domain HTTPException subclasses            - camera_service.py           |
|                                                                      - report_service.py           |
|                                                                      - auth_service.py             |
+----------------------------------------------------------------------------------------------------+
```
*Figure 8.1: Backend Service-Oriented Component Architecture*

### Technology Stack and Selection Rationale:
*Table 8.1: System Technology Stack and Architectural Rationale*

| Technology / Component | Version | Architectural Role | Selection Rationale |
| :--- | :--- | :--- | :--- |
| **FastAPI** | `^0.110.0` | Asynchronous API Framework | Native async coroutines; automated OpenAPI/Swagger generation; high throughput. |
| **Python** | `3.11.x` | Core Backend Runtime | Up to 25% faster than Python 3.10; extensive computer vision and ML library support. |
| **PostgreSQL** | `15.4` | Relational Database | ACID compliance; robust JSONB support for camera calibration matrices; strong indexing. |
| **Redis** | `7.2` | Cache & Pub/Sub Broker | Sub-millisecond response for leaderboard caching; native Pub/Sub for WebSockets. |
| **SQLAlchemy** | `2.0.28` | ORM & Query Builder | Modern 2.0 type-hinted syntax; reliable connection pooling; migration support via Alembic. |
| **OpenCV** | `4.8.1` | Computer Vision Library | Fast C++ optimized image processing; morphological filtering; homography rectification. |
| **Ultralytics YOLO11** | `8.3.x` | Deep Learning Inference | State-of-the-art small-object detection; efficient C3k2 backbone; sub-50ms CPU inference. |
| **ReportLab** | `4.1.0` | PDF Generation Engine | High-resolution vector graphics; precise layout control for official WA scorecards. |
| **React** | `18.2.0` | Frontend Web Framework | Declarative UI rendering; component reusability; high performance virtual DOM. |
| **Zustand** | `4.5.2` | Client State Management | Minimal boilerplate; non-invasive reactive state updates; zero unnecessary re-renders. |
| **Tailwind CSS** | `3.4.1` | Utility-First CSS | Clean styling; responsive layouts; dark/light mode theming support. |
| **Docker Compose** | `2.24.x` | Container Orchestration | Isolated multi-container environments; single-command deployment across platforms. |

## 8.2 Detailed Backend Service Implementations & Critical Code Walkthroughs

### 8.2.1 Arrow Detection Service (`src/services/arrow_detection_service.py`)
The `ArrowDetectionService` orchestrates the multi-method computer vision detection pipeline:

```python
class ArrowDetectionService:
    def __init__(self, yolo_service: YoloDetectionService):
        self.yolo_service = yolo_service
        self.weights = {
            "morphology": 0.40,
            "line_ellipse": 0.30,
            "yolo": 0.20,
            "hsv": 0.10
        }

    def detect_impact_point(self, current_frame: np.ndarray, 
                            reference_frame: Optional[np.ndarray], 
                            homography_matrix: Optional[np.ndarray]) -> DetectionResult:
        # Step 1: Perspective Homography Warp
        if homography_matrix is not None:
            warped = cv2.warpPerspective(current_frame, homography_matrix, (1000, 1000))
            ref_warped = cv2.warpPerspective(reference_frame, homography_matrix, (1000, 1000)) if reference_frame is not None else None
        else:
            warped = current_frame
            ref_warped = reference_frame

        candidates = []
        
        # Step 2: Tier 1 - Morphological Puncture Difference
        if ref_warped is not None:
            morph_res = self._detect_puncture_morphology(warped, ref_warped)
            if morph_res.is_valid:
                candidates.append(("morphology", morph_res.point, morph_res.confidence))

        # Step 3: Tier 2 - Quadratic Line-Ellipse Intersection
        ellipse_res = self._detect_line_ellipse(warped)
        if ellipse_res.is_valid:
            candidates.append(("line_ellipse", ellipse_res.point, ellipse_res.confidence))

        # Step 4: Tier 3 - YOLO11 Deep Learning Detection
        yolo_res = self.yolo_service.detect_arrow(warped)
        if yolo_res.is_valid:
            candidates.append(("yolo", yolo_res.point, yolo_res.confidence))

        # Step 5: Consensus Arbitration
        final_coord, final_conf, method_used = self._compute_consensus(candidates, warped)
        return DetectionResult(x=final_coord[0], y=final_coord[1], 
                               confidence=final_conf, method=method_used)
```

### 8.2.2 World Archery Scoring Engine (`src/services/scoring_service.py`)
The `ScoringService` evaluates rectified Cartesian coordinates against World Archery rules:

```python
class ScoringService:
    # Normalized World Archery 10-Ring Radial Thresholds (R_target = 1.0)
    WA_ZONES = [
        (0.048, 10, True),   # Inner-10 (X-Ring)
        (0.096, 10, False),  # Ring 10
        (0.192, 9,  False),  # Ring 9
        (0.288, 8,  False),  # Ring 8
        (0.384, 7,  False),  # Ring 7
        (0.480, 6,  False),  # Ring 6
        (0.576, 5,  False),  # Ring 5
        (0.672, 4,  False),  # Ring 4
        (0.768, 3,  False),  # Ring 3
        (0.864, 2,  False),  # Ring 2
        (0.960, 1,  False),  # Ring 1
    ]
    NORMALIZED_SHAFT_RADIUS = 0.0041  # 2.5mm shaft on 610mm target radius

    def calculate_score(self, x: float, y: float, target_radius_px: float = 500.0) -> ScoreEvaluation:
        # Compute normalized radial distance from center (0, 0)
        norm_x = x / target_radius_px
        norm_y = y / target_radius_px
        r = math.sqrt(norm_x**2 + norm_y**2)

        # Check line-cutter tangency: r - delta <= R_z
        effective_r = max(0.0, r - self.NORMALIZED_SHAFT_RADIUS)

        for boundary_radius, score_val, is_x in self.WA_ZONES:
            if effective_r <= boundary_radius:
                return ScoreEvaluation(
                    score_value=score_val,
                    is_x_ring=is_x,
                    radial_distance=r,
                    is_line_cutter=(r > boundary_radius and effective_r <= boundary_radius)
                )

        # Arrow falls outside Zone 1 outer dividing line
        return ScoreEvaluation(score_value=0, is_x_ring=False, radial_distance=r, is_line_cutter=False)
```

### 8.2.3 Leaderboard and Tie-Breaking Service (`src/services/leaderboard_service.py`)
Computes official tournament rankings with sub-millisecond Redis caching:

```python
class LeaderboardService:
    def __init__(self, db: AsyncSession, redis: Redis):
        self.db = db
        self.redis = redis

    async def get_tournament_leaderboard(self, tournament_id: UUID) -> List[ArcherStanding]:
        cache_key = f"leaderboard:{tournament_id}"
        cached = await self.redis.get(cache_key)
        if cached:
            return [ArcherStanding.parse_raw(row) for row in json.loads(cached)]

        # Optimized SQL aggregation grouping by archer
        query = (
            select(
                User.id.label("archer_id"),
                User.full_name,
                func.coalesce(func.sum(Score.score_value), 0).label("total_score"),
                func.count(case((Score.score_value == 10, 1))).label("num_tens"),
                func.count(case((Score.is_x_ring == True, 1))).label("num_xs"),
                func.count(Score.id).label("arrows_shot")
            )
            .join(SessionArcher, SessionArcher.user_id == User.id)
            .join(Session, Session.id == SessionArcher.session_id)
            .outerjoin(Score, and_(Score.session_id == Session.id, Score.archer_id == User.id))
            .where(Session.tournament_id == tournament_id)
            .group_by(User.id, User.full_name)
            .order_by(
                desc("total_score"),
                desc("num_tens"),
                desc("num_xs")
            )
        )
        result = await self.db.execute(query)
        standings = [ArcherStanding.from_orm(row) for row in result.all()]

        # Cache standings in Redis with 60-second TTL
        await self.redis.setex(cache_key, 60, json.dumps([s.dict() for s in standings]))
        return standings
```

### 8.2.4 Multi-Lane AI Round Scoring & Batch Confirmation Pipeline
To enable synchronized multi-lane tournament scoring, Bull's Eye implements the automated round execution cycle (`POST /api/sessions/{id}/ai-score-round` and `POST /api/sessions/{id}/scores/batch-confirm-round`):

```python
@router.post("/{session_id}/ai-score-round")
async def ai_score_round(session_id: UUID, round_data: RoundScoreRequest, 
                         db: AsyncSession = Depends(get_db)):
    # Executes multi-lane AI scoring cycle for all active lanes in an end.
    session = await db.get(Session, session_id)
    lane_assignments = await db.execute(
        select(CameraLaneAssignment).where(CameraLaneAssignment.session_id == session_id)
    )
    
    scored_lanes = []
    for assignment in lane_assignments.scalars().all():
        # Fetch current frame from lane camera stream
        frame = camera_service.get_latest_frame(assignment.camera_id)
        homography = assignment.camera.calibration_matrix
        
        # Detect all arrows shot in this end
        detection = arrow_detection_service.detect_end_arrows(frame, homography)
        
        lane_summary = {
            "lane_number": assignment.lane_number,
            "archer_id": str(assignment.archer_id),
            "detected_arrows": detection.arrows,
            "end_total": sum(a.points for a in detection.arrows),
            "avg_confidence": detection.mean_confidence,
            "annotated_image": detection.base64_preview
        }
        scored_lanes.append(lane_summary)
        
    return {"session_id": str(session_id), "round": round_data.round, "lanes": scored_lanes}
```

Judges review the detected arrows across all lanes simultaneously. If an arrow is contested, they toggle `is_override = True` and submit `batch-confirm-round`, which commits all arrow scores across all lanes within a single database transaction.

### 8.2.5 Database Connection Pooling & Concurrency Architecture
Under high concurrent loads (e.g., 32 lanes capturing arrows simultaneously), database connection starvation is prevented via fine-tuned SQLAlchemy asynchronous connection pooling:
- `pool_size = 20`: Baseline persistent database connections maintained in the pool.
- `max_overflow = 10`: Burst connection buffer accommodating simultaneous round-end spikes.
- `pool_recycle = 3600`: Recycles idle TCP connections every hour to avoid firewall timeouts.
- `pool_pre_ping = True`: Issues `SELECT 1;` healthcheck before leasing a connection to coroutines.

### 8.2.6 Vector PDF Scorecard Compilation (`src/services/report_service.py`)
Generates World Archery standard scorecards using ReportLab vector graphics:

```python
class ReportService:
    def generate_session_pdf(self, session: Session, archer: User, scores: List[Score]) -> io.BytesIO:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
        elements = []
        
        # Add official header and branding
        elements.append(Paragraph("WORLD ARCHERY OFFICIAL MATCH SCORECARD", styles['Heading1']))
        elements.append(Paragraph(f"Athlete: {archer.full_name} | Target: WA-122CM | Session: {session.id}", styles['Normal']))
        
        # Build 12-End scoring grid table
        table_data = [["End", "A1", "A2", "A3", "A4", "A5", "A6", "Subtotal", "Total", "10s", "Xs"]]
        for end_num in range(1, session.total_ends + 1):
            end_scores = [s for s in scores if s.end_number == end_num]
            # Populate scores, calculate subtotals, highlight overrides
            row = [str(end_num)] + [str(s.score_value) for s in end_scores] + [...]
            table_data.append(row)
            
        t = Table(table_data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.navy),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey)
        ]))
        elements.append(t)
        doc.build(elements)
        buffer.seek(0)
        return buffer
```

## 8.3 Frontend Component Architecture & Zustand State Management

The client interface is built as a Single-Page Application (SPA) using React 18, Vite, and Tailwind CSS. State management is organized into modular Zustand stores, preventing redundant re-renders and ensuring high responsiveness during rapid arrow impacts.

```
+----------------------------------------------------------------------------------------------------+
|                         FRONTEND REACT 18 COMPONENT & STORE HIERARCHY                              |
|                                                                                                    |
|    [App.tsx]                                                                                       |
|     - BrowserRouter, Role Guards, Layout Header & Sidebar Navigation                               |
|         |                                                                                          |
|         +---> [authStore.ts]    : Token, Active User, User Role, Login/Logout Actions               |
|         +---> [sessionStore.ts] : Current Match, Lane Archers, Scores Array, Current End           |
|         +---> [cameraStore.ts]  : Active Cameras, RTSP Health Status, Homography Calibration       |
|                                                                                                    |
|    [Primary Views]                                                                                 |
|     |-- Dashboard.tsx       : Tournament overview, quick stats, active lane monitoring             |
|     |-- Scoring.tsx         : Live target canvas, arrow placement pulse, manual judge override     |
|     |-- Tournaments.tsx     : Tournament builder, lane assignment matrix, status transitions       |
|     |-- Cameras.tsx         : Camera preview, 4-point calibration canvas, health indicators        |
|     |-- Reports.tsx         : Scorecards, PDF export buttons, historical end tables                |
|     |-- BatchTesting.tsx    : Model evaluation, confusion matrix, metric charts                    |
|     +-- SystemStatus.tsx    : Health probes (Postgres, Redis, CV engine), latency graphs           |
+----------------------------------------------------------------------------------------------------+
```
*Figure 8.2: Frontend React 18 Component Hierarchy and Zustand Store Dataflow*

### Reactive Zustand Store Implementation:
```typescript
interface SessionState {
  currentSessionId: string | null;
  activeEnd: number;
  scores: ScoreItem[];
  addScore: (score: ScoreItem) => void;
  updateScoreOverride: (scoreId: string, newValue: number, isX: boolean) => void;
  setScores: (scores: ScoreItem[]) => void;
}

export const useSessionStore = create<SessionState>((set) => ({
  currentSessionId: null,
  activeEnd: 1,
  scores: [],
  addScore: (score) => set((state) => ({ scores: [...state.scores, score] })),
  updateScoreOverride: (scoreId, newValue, isX) =>
    set((state) => ({
      scores: state.scores.map((s) =>
        s.id === scoreId
          ? { ...s, score_value: newValue, is_x_ring: isX, is_manual_override: true }
          : s
      ),
    })),
  setScores: (scores) => set({ scores }),
}));
```

## 8.4 Real-Time WebSocket Communication Pipeline

To satisfy the sub-100 ms synchronization requirement, Bull's Eye bypasses HTTP polling via persistent WebSockets:

```
+----------------------------------------------------------------------------------------------------+
|                       WEBSOCKET BI-DIRECTIONAL EVENT SYNCHRONIZATION LIFECYCLE                     |
|                                                                                                    |
|  Client Browser                 FastAPI WebSocket Manager                     Redis Pub/Sub Channel|
|        |                                    |                                          |           |
|        |--Connect ws://.../ws/{session_id}->|                                          |           |
|        |<-101 Switching Protocols----------|                                          |           |
|        |                                    |--Subscribe: session:{id}:channel-------->|           |
|        |                                    |                                          |           |
|        |                                    |               [Arrow Detected on Lane]   |           |
|        |                                    |                                          |           |
|        |                                    |<--Receive Event: SCORE_RECORDED----------|           |
|        |<-Send JSON Payload: SCORE_RECORDED-|                                          |           |
|        |  (Renders arrow pulse & score)     |                                          |           |
|        |                                    |                                          |           |
|        |--Ping (Heartbeat every 15s)------->|                                          |           |
|        |<-Pong------------------------------|                                          |           |
+----------------------------------------------------------------------------------------------------+
```
*Figure 8.3: WebSocket Bi-Directional Event Synchronization Lifecycle*

```python
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id].append(websocket)

    def disconnect(self, websocket: WebSocket, session_id: str):
        if websocket in self.active_connections[session_id]:
            self.active_connections[session_id].remove(websocket)

    async def broadcast_to_session(self, session_id: str, message: dict):
        for connection in self.active_connections.get(session_id, []):
            try:
                await connection.send_json(message)
            except Exception:
                pass  # Handle client disconnect gracefully
```
"""
