# System Architecture — Automated Archery Scoring System (SPL-3)

**Lifecycle Stage**: Inception / Reverse Engineering  
**Standard**: AIDLC Process Guidelines (`inception/reverse-engineering.md`)  
**Topology**: Containerized Microservices Stack (Docker Compose)

---

## 1. System Overview

The system is engineered as a modern, decoupled client-server platform optimized for high-performance image processing, sub-second scoring latency, and real-time event streaming across local-area network (LAN) shooting ranges.

```mermaid
graph TB
    subgraph Client_Tier["Client Presentation Tier"]
        Browser["Modern Web Browsers (Chrome / Firefox / Safari)"]
        Tablet["Range Scorer Tablets (Touch-optimized)"]
    end

    subgraph Ingress_Tier["Ingress & Static Serving Tier (Port 3000 / 5173)"]
        NginxProxy["Nginx Reverse Proxy & SPA Host<br/>- Serves Vite React distribution<br/>- Proxies /api/ to FastAPI<br/>- Upgrades /api/ws/ to WebSockets"]
    end

    subgraph Application_Tier["Application & AI Processing Tier (Port 8000)"]
        FastAPI["FastAPI ASGI Application<br/>- Security Middleware (JWT, Rate Limiting, CORS)<br/>- 9 REST API Routers<br/>- 2 WebSocket Endpoints"]
        ThreadPool["Adaptive ThreadPoolExecutor<br/>- Sized 4–8 workers<br/>- Offloads heavy CPU-bound CV tasks"]
        
        subgraph Detection_Engine["Hybrid ML/CV Vision Engine"]
            YOLO["Ultralytics YOLO11 Neural Network<br/>(best.pt weights, mAP50=97.8%)"]
            OpenCV["OpenCV Multi-Method Pipeline<br/>(Hough, Color Bands, Contour Ellipses, Puncture Holes)"]
        end
    end

    subgraph Persistence_Tier["Persistence & In-Memory Data Tier"]
        Postgres["PostgreSQL 15 Database (Port 5432)<br/>- Relational storage for users, tournaments, sessions, scores, cameras, audits"]
        Redis["Redis 7 In-Memory Cache (Port 6379)<br/>- Sorted sets for instant leaderboard ranks<br/>- Event bus messaging"]
        FileStorage["Docker Volume: /storage<br/>- /storage/raw: Original camera captures<br/>- /storage/annotated: Diagnostic overlays<br/>- /storage/reports: Generated PDF/CSV match cards"]
    end

    Browser -->|HTTP & WebSockets| NginxProxy
    Tablet -->|HTTP & WebSockets| NginxProxy
    NginxProxy -->|HTTP REST: /api/| FastAPI
    NginxProxy -->|WS Upgrade: /api/ws/| FastAPI
    FastAPI -->|Offload image compute| ThreadPool
    ThreadPool --> Detection_Engine
    FastAPI -->|SQLAlchemy ORM (QueuePool)| Postgres
    FastAPI -->|Sorted Sets & Caching| Redis
    FastAPI -->|Persist images & reports| FileStorage
```

---

## 2. End-to-End Scoring Data Flow

The following sequence diagram captures the core business loop: capturing an arrow impact, running hybrid YOLO11/OpenCV inference, persisting the score, updating leaderboards, and broadcasting real-time updates to all connected displays.

```mermaid
sequenceDiagram
    autonumber
    actor Scorer as Scorer / Tablet
    participant FE as Frontend UI (React)
    participant Proxy as Nginx Proxy
    participant API as FastAPI Backend
    participant TP as ThreadPool Executor
    participant CV as Arrow Detection Engine (YOLO11/OpenCV)
    participant DB as PostgreSQL
    participant Cache as Redis Cache
    participant WS as WebSocket Clients

    Scorer->>FE: Click "Capture & Score" or Upload Photo
    FE->>Proxy: POST /api/scores/detect (Multipart Image)
    Proxy->>API: Forward POST /api/scores/detect
    API->>TP: submit(_run_detection_job, image_bytes)
    
    rect rgb(240, 248, 255)
        Note over TP,CV: Async Non-Blocking Vision Pipeline
        TP->>CV: Stage 1: Normalize & Preprocess Image
        TP->>CV: Stage 2: Fit Target Center & Outer Ring (Hough + Color + Ellipses)
        TP->>CV: Stage 3: Detect Arrow Tips (YOLO11 bboxes + Puncture Holes + Hough Lines)
        TP->>CV: Stage 4: Compute Normalized Radius ($d/R$) & Map to WA Zones (0–10, X)
        TP->>CV: Stage 5: Render Annotated Diagnostic Overlay
    end

    CV-->>API: Return DetectionResult (scores, coordinates, confidence, annotated_image)
    API->>DB: INSERT into scores table (score, ring, x, y, is_x, confidence)
    API->>Cache: ZADD tournament_leaderboard (increment score, update X-count)
    API->>WS: Broadcast Event: SCORE_RECORDED & LEADERBOARD_UPDATED
    API-->>Proxy: HTTP 200 OK + Score Payload & Image URL
    Proxy-->>FE: Return JSON Response
    FE-->>Scorer: Display Detected Arrows & Updated Running Total
    WS-->>Scorer: Live UI Widget Updates via WebSocket
```

---

## 3. Database Entity-Relationship Architecture

The relational schema is normalized in third normal form (3NF) and managed via SQLAlchemy ORM models:

```mermaid
erDiagram
    User ||--o{ Tournament : organizes
    User ||--o{ SessionArcher : competes
    User ||--o{ Score : records
    User ||--o{ AuditLog : triggers

    Tournament ||--o{ Session : contains
    Session ||--o{ SessionArcher : registers
    Session ||--o{ Score : logs
    
    Camera ||--o{ CameraLaneAssignment : assigned_to
    Session ||--o{ CameraLaneAssignment : monitors
    
    SessionArcher ||--o{ Score : achieves

    User {
        int id PK
        string username UK
        string email UK
        string password_hash
        string role "admin | scorer | spectator | archer"
        boolean is_active
        timestamp created_at
    }

    Tournament {
        int id PK
        string name
        text description
        datetime start_date
        datetime end_date
        string status "UPCOMING | ACTIVE | COMPLETED"
        int organizer_id FK
    }

    Session {
        int id PK
        int tournament_id FK
        string name
        int target_face_size "40 | 80 | 122"
        int total_ends
        int arrows_per_end
        string status "PENDING | IN_PROGRESS | COMPLETED"
    }

    SessionArcher {
        int id PK
        int session_id FK
        int archer_id FK
        int lane_number
        string target_identifier
    }

    Score {
        int id PK
        int session_id FK
        int session_archer_id FK
        int end_number
        int arrow_number
        int score "0-10"
        int ring_number "0-10"
        boolean is_x
        float x_coordinate
        float y_coordinate
        float normalized_distance
        float confidence
        string detection_method "yolo | puncture_hole | line_intersection | manual"
        boolean is_verified
        string raw_image_path
        string annotated_image_path
    }

    Camera {
        int id PK
        string name
        string stream_url "rtsp://..."
        string camera_type "RTSP | USB | MOCK"
        boolean is_active
        json resolution
    }

    CameraLaneAssignment {
        int id PK
        int camera_id FK
        int session_id FK
        int lane_number
        boolean is_active
    }

    AuditLog {
        int id PK
        int user_id FK
        string action
        string entity_type
        int entity_id
        json changes
        string ip_address
        timestamp timestamp
    }
```

---

## 4. Integration Points & Protocols

| Integration Boundary | Protocol / Driver | Serialization | Purpose |
|---|---|---|---|
| **Frontend $\leftrightarrow$ Nginx** | HTTP/1.1 & WebSocket | HTML / JS / JSON / Binary Blob | Static application delivery and single endpoint ingress. |
| **Nginx $\leftrightarrow$ FastAPI** | HTTP/1.1 (Reverse Proxy) | REST JSON & WebSocket Frames | Forwards `/api/*` and `/api/ws/*` traffic to backend services. |
| **FastAPI $\leftrightarrow$ PostgreSQL** | TCP / `psycopg2-binary` | SQL Queries & Binary Protocol | ACID transactional persistence for tournament, scoring, and user state. |
| **FastAPI $\leftrightarrow$ Redis** | TCP / `redis-py` (async/sync) | In-Memory Key-Value & Sorted Sets | Fast leaderboard aggregation, cache TTL invalidation, event pub/sub. |
| **FastAPI $\leftrightarrow$ RTSP Cameras** | RTSP / OpenCV VideoCapture | H.264 / MJPEG Video Frames | Pulls live video frames from on-range target cameras for live preview and scoring. |
| **FastAPI $\leftrightarrow$ Storage Volume** | POSIX Filesystem | JPEG Images & PDF/CSV Files | Local storage volume for raw photos, annotated crops, and generated reports. |

---

## 5. Security & Isolation Architecture

1. **Role-Based Access Control (RBAC)**:
   - Enforced through FastAPI route dependencies (`get_current_user`, `require_role`).
   - Four distinct permission tiers:
     - `admin`: Full administrative access (user management, tournament deletion, hardware configuration).
     - `scorer`: Tournament scoring operations, camera previews, score approvals, end completion.
     - `archer`: Personal scorecard viewing, history retrieval.
     - `spectator`: Read-only access to leaderboards and active session broadcasts.
2. **Network Isolation**:
   - Internal services (`db`, `cache`, `api`) communicate across the dedicated Docker bridge network `archery_network`.
   - Only HTTP port 3000/5173 (Frontend/Nginx) and port 8000 (Backend API) are published to the host machine.
   - Nginx handles ingress sanitization and CORS header resolution.
