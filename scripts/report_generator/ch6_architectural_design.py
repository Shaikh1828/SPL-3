"""
Chapter 6: Architectural and High-Level Design Module for Bull's Eye SPL-3 Final Technical Report.
Covers Architectural Context Diagram (ACD), Architectural Archetypes & Design Patterns,
Top-Level Component Diagram, Layered Architecture, REST API Design & Contracts (all 27 endpoints + 2 WS),
and Docker Compose Deployment Diagram.
"""

def get_chapter_6():
    return r"""---

# CHAPTER 6: ARCHITECTURAL AND HIGH-LEVEL DESIGN

## 6.1 Architectural Context Diagram (ACD)

The Architectural Context Diagram (ACD) defines the high-level boundary of the Bull's Eye automated scoring platform and establishes its structural interfaces with external human actors, hardware peripherals, and external data storage systems.

```
+----------------------------------------------------------------------------------------------------+
|                               ARCHITECTURAL CONTEXT DIAGRAM (ACD)                                  |
|                                                                                                    |
|  +--------------------+                                                +-----------------------+   |
|  | Lane Target Cameras|                                                |   Spectator Displays  |   |
|  | (RTSP 1080p / USB) |                                                |   (Arena Video Walls) |   |
|  +--------------------+                                                +-----------------------+   |
|            |                                                                       ^               |
|            | [RTSP H.264 Video Stream]                                             | [Live WS Push]|
|            v                                                                       |               |
|  +----------------------------------------------------------------------------------+              |
|  |                                                                                  |              |
|  |                 BULL'S EYE AUTOMATED ARCHERY SCORING SYSTEM                      |              |
|  |                                                                                  |              |
|  +----------------------------------------------------------------------------------+              |
|       ^                                 ^                                       |                  |
|       | [HTTPS / JWT REST]              | [WSS Bi-Directional]                  | [PDF Downloads]  |
|       v                                 v                                       v                  |
|  +--------------------+         +--------------------+                 +-----------------------+   |
|  | Tournament Admin   |         | Certified Line     |                 | World Archery Official|   |
|  | & Range Officials  |         | Judges & Archers   |                 | Records & Archive PDF |   |
|  +--------------------+         +--------------------+                 +-----------------------+   |
+----------------------------------------------------------------------------------------------------+
```
*Figure 6.1: Architectural Context Diagram (ACD)*

As illustrated, Bull's Eye occupies the central hub:
- **Inbound Stream Interfaces**: Connect to IP-based RTSP cameras and USB capture cards at 30 fps, ingesting live target imagery.
- **Bi-Directional WebSocket Pipelines**: Continuously push real-time arrow impact telemetry, score changes, and lane progression events to line judges and archer tablets with sub-100 ms latency.
- **Public Broadcast Feeds**: Stream low-overhead JSON payloads to arena video displays, eliminating the need for manual score polling.
- **RESTful Administration Interfaces**: Provide secure, authenticated endpoints for tournament configuration, role-based user management, and calibration commands.
- **Document Output Pipelines**: Deliver official vector-rendered PDF tournament result packages conforming to World Archery documentation standards.

## 6.2 Architectural Archetypes & Design Patterns

The architecture of Bull's Eye synthesizes several proven software design patterns to achieve high modularity, testability, and operational resilience:

1. **Layered (N-Tier) Architecture**: Strictly divides system responsibilities into Presentation, Application/API, Domain Logic, and Persistence/Infrastructure tiers, preventing high-level business rules from coupling to low-level database or framework drivers.
2. **Strategy Pattern for Computer Vision Algorithms**: The `ArrowDetectionService` treats each individual localization technique (Puncture Morphology, Quadratic Line-Ellipse, YOLO11, HSV Segmentation) as an interchangeable strategy adhering to a common interface (`detect(frame) -> DetectionResult`). This facilitates runtime algorithm switching and independent benchmarking.
3. **Observer & Publish-Subscribe Pattern (Pub/Sub)**: Decouples scoring events from real-time client delivery. When `ScoringService` records a score, it publishes a message to a Redis Pub/Sub channel. The WebSocket connection manager observes the channel and pushes the event to all subscribed clients for that specific lane.
4. **Repository and Unit of Work Pattern**: Implemented via SQLAlchemy ORM sessions, abstracting raw SQL operations into transactional units of work that guarantee ACID compliance during simultaneous score insertions and audit log updates.
5. **Circuit Breaker & Exponential Backoff Pattern**: Utilized within `CameraService` to monitor external RTSP camera streams. If a camera feed drops, the service halts stream polling, initiates non-blocking reconnection attempts with exponential backoff ($1\text{s}, 2\text{s}, 4\text{s}, 8\text{s}$), and raises a graceful health warning.

## 6.3 Top-Level Component Diagram

Figure 6.2 models the primary software components comprising the Bull's Eye platform, highlighting their modular boundaries and communication protocols.

```
+----------------------------------------------------------------------------------------------------+
|                                 TOP-LEVEL COMPONENT DIAGRAM                                        |
|                                                                                                    |
|   +--------------------------------------------------------------------------------------------+   |
|   |                       FRONTEND SINGLE-PAGE APPLICATION (React 18 + Vite)                   |   |
|   |  [Target Canvas]    [Live Scoreboard]    [Judge Review UI]    [Admin Console]    [Zustand] |   |
|   +--------------------------------------------------------------------------------------------+   |
|                 | (HTTP / REST JSON)                                   | (WSS Events)              |
|                 v                                                      v                           |
|   +--------------------------------------------------------------------------------------------+   |
|   |                       BACKEND APPLICATION GATEWAY (FastAPI / Starlette)                    |   |
|   |  [CORS & Auth Middleware]   [JWT Security]   [Exception Handler]   [WebSocket Hub]         |   |
|   +--------------------------------------------------------------------------------------------+   |
|                 |                                                      |                           |
|                 v                                                      v                           |
|   +------------------------------------------+       +-----------------------------------------+   |
|   |          CORE BUSINESS SERVICES          |       |         COMPUTER VISION ENGINE          |   |
|   |  - ScoringService (WA Rules)             |       |  - Homography Transformation Engine     |   |
|   |  - TournamentService (Brackets, Sessions)|<----->|  - Puncture Difference Morphology       |   |
|   |  - LeaderboardService (Tie-Breaking)     |       |  - YOLO11 Deep Learning Shaft Detector  |   |
|   |  - AuditService (Immutable Logs)         |       |  - Quadratic Line-Ellipse Solver        |   |
|   |  - ReportService (ReportLab PDF Engine)  |       |  - Multi-Tier Consensus Evaluator       |   |
|   +------------------------------------------+       +-----------------------------------------+   |
|                 |                                                      |                           |
|                 v                                                      v                           |
|   +------------------------------------------+       +-----------------------------------------+   |
|   |       PERSISTENCE LAYER (PostgreSQL 15)  |       |        CACHE & BROKER (Redis 7)         |   |
|   |  - 3NF Relational Tables                 |       |  - In-Memory Leaderboard Snapshot Cache |   |
|   |  - ACID Transaction Pools                |       |  - Pub/Sub Channel Broadcast Engine     |   |
|   |  - SQLAlchemy ORM Declarative Models     |       |  - Ephemeral Session State Stores       |   |
|   +------------------------------------------+       +-----------------------------------------+   |
+----------------------------------------------------------------------------------------------------+
```
*Figure 6.2: Top-Level Software Component Diagram*

## 6.4 Layered Software Architecture

The software architecture is rigorously organized into four clean horizontal tiers:

```
+---------------------------------------------------------------------------------------------------+
|                                   LAYERED SOFTWARE ARCHITECTURE                                   |
|                                                                                                   |
|  [PRESENTATION LAYER]                                                                             |
|   - React 18 SPA (Vite, Tailwind CSS, Lucide Icons)                                               |
|   - Interactive SVG Target Canvas with real-time arrow pulse animations                           |
|   - Recharts visual analytics (dispersion scatter plots, end-by-end trend curves)                 |
|   - Zustand Reactive Stores: authStore, sessionStore, cameraStore                                 |
|                                                                                                   |
|  [APPLICATION / API GATEWAY LAYER]                                                                |
|   - FastAPI Asynchronous Core with Pydantic V2 request/response validation schemas                |
|   - OAuth2 Password Bearer authentication & JWT token encoding/decoding                           |
|   - Centralized HTTP Exception Handlers and structured logging middleware                         |
|   - Bi-directional WebSocket endpoint routers (/ws/{session_id}, /ws/camera/{id}/preview)         |
|                                                                                                   |
|  [DOMAIN & COMPUTER VISION LAYER]                                                                 |
|   - ScoringService: World Archery 10-ring radial boundary calculation & line-cutter geometry      |
|   - ArrowDetectionService: Multi-tier consensus fusion (Morphology, Ellipse, YOLO11, HSV)         |
|   - YoloDetectionService: Ultralytics YOLO11 deep neural network inference                        |
|   - CameraService: 4-point perspective homography calibration and stream monitoring               |
|   - LeaderboardService: WA rank aggregation, tie-breaking criteria, and Redis cache management    |
|   - AuditService: Cryptographic judicial score override logging and compliance auditing           |
|   - ReportService: ReportLab canvas drawing, WA scorecard layout, binary PDF streaming            |
|                                                                                                   |
|  [INFRASTRUCTURE & PERSISTENCE LAYER]                                                             |
|   - PostgreSQL 15 Relational Database: 8 normalized 3NF tables with foreign keys and indexes      |
|   - Redis 7 In-Memory Datastore: Cache management (60s TTL) and Pub/Sub event distribution        |
|   - SQLAlchemy 2.0 ORM with asynchronous connection pooling and Alembic migration tracking        |
|   - OpenCV 4.8 & PyTorch 2.0 accelerated computer vision runtime libraries                        |
+---------------------------------------------------------------------------------------------------+
```
*Figure 6.3: Layered Software Architecture*

## 6.5 REST API Specifications and Design Contracts

Bull's Eye exposes 27 production RESTful API endpoints alongside 2 real-time WebSocket channels. All requests and responses are strictly typed via Pydantic schemas, and endpoints adhere to standard HTTP status codes (`200 OK`, `201 Created`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`, `422 Unprocessable Entity`).

*Table 6.1: Complete REST API Endpoint Inventory and Protocol Contracts (27 Endpoints)*

| Module | Method | Endpoint Route | Request Body | Response Schema | Auth Required | Cache / TTL |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Auth** | POST | `/api/v1/auth/login` | `OAuth2PasswordRequest` | `TokenResponse (JWT, user)` | None (Public) | None |
| | POST | `/api/v1/auth/register` | `UserCreate (email, pwd, name)` | `UserResponse` | Admin only | None |
| | POST | `/api/v1/auth/refresh` | `RefreshRequest (token)` | `TokenResponse` | Authenticated | None |
| | GET | `/api/v1/auth/me` | None | `UserResponse` | Authenticated | None |
| **Users** | GET | `/api/v1/users` | Query: `role`, `skip`, `limit` | `List[UserResponse]` | Admin / Scorer | None |
| | GET | `/api/v1/users/{user_id}` | None | `UserResponse` | Authenticated | None |
| | PUT | `/api/v1/users/{user_id}` | `UserUpdate` | `UserResponse` | Admin only | None |
| | DELETE | `/api/v1/users/{user_id}` | None | `{"status": "deleted"}` | Admin only | None |
| **Tournaments**| GET | `/api/v1/tournaments` | Query: `skip`, `limit` | `List[TournamentResponse]` | Authenticated | Redis (60s) |
| | POST | `/api/v1/tournaments` | `TournamentCreate` | `TournamentResponse` | Admin only | Cache Inval |
| | GET | `/api/v1/tournaments/{id}`| None | `TournamentDetailResponse` | Authenticated | Redis (60s) |
| | PUT | `/api/v1/tournaments/{id}`| `TournamentUpdate` | `TournamentResponse` | Admin only | Cache Inval |
| | DELETE| `/api/v1/tournaments/{id}`| None | `{"status": "deleted"}` | Admin only | Cache Inval |
| **Sessions** | GET | `/api/v1/sessions` | Query: `tournament_id` | `List[SessionResponse]` | Authenticated | None |
| | POST | `/api/v1/sessions` | `SessionCreate (lanes, archers)` | `SessionResponse` | Admin only | None |
| | GET | `/api/v1/sessions/{id}` | None | `SessionDetailResponse` | Authenticated | None |
| | PUT | `/api/v1/sessions/{id}/advance`| `EndAdvanceRequest` | `SessionResponse` | Scorer / Admin| Cache Inval |
| **Scores** | POST | `/api/v1/scores/detect` | `Multipart/form-data (image, session_id, archer_id, end)` | `ScoreDetectionResponse` | Scorer / Admin| Pub/Sub Push |
| | POST | `/api/v1/scores/manual` | `ManualScoreCreate` | `ScoreResponse` | Scorer / Admin| Pub/Sub Push |
| | GET | `/api/v1/scores/session/{id}`| Query: `end_number` | `List[ScoreResponse]` | Authenticated | None |
| | PUT | `/api/v1/scores/{score_id}`| `ScoreOverrideRequest (val, reason)` | `ScoreResponse` | Scorer / Admin| Cache Inval |
| | POST | `/api/v1/scores/batch-test` | `Multipart/form-data (zip)` | `BatchTestResponse` | Admin only | None |
| **Cameras** | GET | `/api/v1/cameras` | None | `List[CameraResponse]` | Authenticated | None |
| | POST | `/api/v1/cameras` | `CameraCreate (name, url)` | `CameraResponse` | Admin only | None |
| | GET | `/api/v1/cameras/{id}` | None | `CameraDetailResponse` | Authenticated | None |
| | POST | `/api/v1/cameras/{id}/calibrate`| `CalibrationRequest (4 points)` | `CalibrationResponse (H)` | Admin / Scorer | None |
| | GET | `/api/v1/cameras/{id}/snapshot`| None | `Binary JPEG Image` | Authenticated | None |
| **Leaderboard**| GET| `/api/v1/leaderboard/{tournament_id}`| None | `LeaderboardResponse` | Public | Redis (60s) |
| **Reports** | GET | `/api/v1/reports/session/{id}/pdf` | None | `Binary Application/PDF` | Authenticated | None |
| | GET | `/api/v1/reports/tournament/{id}/pdf`| None | `Binary Application/PDF` | Authenticated | None |
| **Health** | GET | `/api/v1/health` | None | `HealthStatus (db, redis, cv)` | Public | None |

*Table 6.2: WebSocket Channel Specification and Event Payloads*

| WebSocket Endpoint | Channel Scope | Permitted Actors | Emitted Event Types | Payload Schema Summary |
| :--- | :--- | :--- | :--- | :--- |
| `/ws/{session_id}` | Match Session | All connected clients | `SCORE_RECORDED`, `SCORE_OVERRIDDEN`, `END_ADVANCED`, `SESSION_FINISHED` | `{"event": str, "score_id": str, "archer_id": str, "value": int, "is_x": bool, "x": float, "y": float, "end": int}` |
| `/ws/camera/{id}/preview`| Target Camera | Admin, Scorer | `FRAME_UPDATE`, `CAMERA_DISCONNECT`, `CALIBRATION_APPLIED` | `{"camera_id": str, "status": str, "frame_base64": str, "fps": float}` |

## 6.6 Deployment Diagram & Container Infrastructure Topology

To ensure rapid, identical deployment across local testing rigs, tournament on-premise servers, and cloud environments, Bull's Eye is packaged into four coordinated Docker containers orchestrated via `docker-compose.yml`.

```
+----------------------------------------------------------------------------------------------------+
|                         DOCKER COMPOSE MULTI-CONTAINER DEPLOYMENT TOPOLOGY                         |
|                                                                                                    |
|    +------------------------------------------------------------------------------------------+    |
|    |                             DOCKER HOST: archery_network (Bridge)                        |    |
|    |                                                                                          |    |
|    |  +----------------------------+                     +---------------------------------+  |    |
|    |  | CONTAINER: frontend        |                     | CONTAINER: api                  |  |    |
|    |  | Image: nginx:alpine        |                     | Image: python:3.11-slim         |  |    |
|    |  | Base: React 18 Production  |                     | Base: FastAPI + Uvicorn         |  |    |
|    |  | Ports: 3000:80 / 5173      |                     | Port: 8000:8000                 |  |    |
|    |  +----------------------------+                     +---------------------------------+  |    |
|    |               |                                                     |                    |    |
|    |               | (Reverse Proxy / API Requests)                      |                    |    |
|    |               +---------------------------------------------------->|                    |    |
|    |                                                                     |                    |    |
|    |                                        +----------------------------+-----------------+  |    |
|    |                                        | (PostgreSQL TCP:5432)      | (Redis TCP:6379)|  |    |
|    |                                        v                            v                 |  |    |
|    |                          +----------------------------+  +----------------------------+  |    |
|    |                          | CONTAINER: db              |  | CONTAINER: cache           |  |    |
|    |                          | Image: postgres:15-alpine  |  | Image: redis:7-alpine      |  |    |
|    |                          | Port: 5432:5432            |  | Port: 6379:6379            |  |    |
|    |                          | Volume: postgres_data      |  | Volume: redis_data         |  |    |
|    |                          +----------------------------+  +----------------------------+  |    |
|    +------------------------------------------------------------------------------------------+    |
+----------------------------------------------------------------------------------------------------+
```
*Figure 6.4: Docker Compose Multi-Container Production Deployment Diagram*

### Container Specifications:
1. **`frontend` (Web Client Tier)**:
   - Base Image: `node:18-alpine` (build stage) $\to$ `nginx:alpine` (runtime stage).
   - Serves minified React 18 SPA static assets and proxies `/api` and `/ws` traffic to the backend API container.
   - Host Port Mapping: `3000:80` (or `5173:80`).
2. **`api` (Application & Computer Vision Tier)**:
   - Base Image: `python:3.11-slim`.
   - Pre-installed runtime libraries: `libgl1-mesa-glx`, `libglib2.0-0` (for headless OpenCV execution).
   - Executes Uvicorn ASGI server hosting FastAPI on worker threads.
   - Host Port Mapping: `8000:8000`.
   - Volume Mounts: Host `./storage` mapped to container `/app/storage` for persisted PDF reports and camera calibration snapshots.
3. **`db` (Relational Persistence Tier)**:
   - Base Image: `postgres:15-alpine`.
   - Host Port Mapping: `5432:5432`.
   - Volume: `postgres_data` persistent named volume ensuring ACID persistence across container restarts.
   - Healthcheck: `pg_isready -U postgres -d archery_db` executed every 5 seconds.
4. **`cache` (In-Memory Caching & Pub/Sub Tier)**:
   - Base Image: `redis:7-alpine`.
   - Host Port Mapping: `6379:6379`.
   - Volume: `redis_data` volume configured with append-only persistence (`appendonly yes`).
   - Healthcheck: `redis-cli ping` executed every 5 seconds.
"""
