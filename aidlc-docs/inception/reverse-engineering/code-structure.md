# Code Structure & Design Patterns — Automated Archery Scoring System (SPL-3)

**Lifecycle Stage**: Inception / Reverse Engineering  
**Standard**: AIDLC Process Guidelines (`inception/reverse-engineering.md`)  
**Repository State**: Brownfield Complete Codebase

---

## 1. Build Systems & Toolchains

The repository is organized as a unified full-stack monorepo featuring distinct build systems for the Python backend and TypeScript/React frontend:

### Backend Toolchain:
- **Build / Packaging Tool**: `pyproject.toml` (standard PEP 518/621 specification, Poetry compatible).
- **Python Version**: 3.11+
- **Execution / Server**: `uvicorn[standard]` (ASGI web server).
- **Database Migrations**: `alembic` (revision-controlled DDL migrations).
- **Test Runner**: `pytest` with `pytest-asyncio` and `pytest-cov`.
- **Code Quality**: `black` (formatter), `ruff` (linter), `mypy` (static type checker).

### Frontend Toolchain:
- **Build System**: Vite 8.x with TypeScript 6.x and `@vitejs/plugin-react`.
- **Node Runtime**: Node.js v20+ / v22+
- **Package Manager**: `npm` (with locked dependencies in `package-lock.json`).
- **Styling Pipeline**: Tailwind CSS v4 with PostCSS.
- **Production Server**: Nginx Alpine multi-stage container.

---

## 2. Directory Layout & Module Organization

```text
SPL-3/
├── alembic/                      # Database schema migrations
│   ├── versions/                 # Individual migration revision scripts
│   └── env.py                    # Alembic migration runtime configuration
├── context/                      # Consolidated Master Reference Documentation
│   ├── 00_SYSTEM_ARCHITECTURE_AND_SCORING_ENGINE.md
│   ├── 01_API_AND_DATABASE_SPECIFICATION.md
│   ├── 02_DEPLOYMENT_AND_OPERATIONS_GUIDE.md
│   ├── 03_TESTING_VALIDATION_AND_PROJECT_REPORTS.md
│   └── INDEX.md
├── Data/                         # 504 raw training images & YOLO bboxes
├── frontend/                     # React 18 / TypeScript SPA
│   ├── public/                   # Static assets (favicons, SVG icons)
│   ├── src/
│   │   ├── api/                  # Axios HTTP client endpoints
│   │   ├── components/           # Reusable UI widgets & modal dialogs
│   │   │   ├── layout/           # Sidebar, TopBar, Main Layout shell
│   │   │   └── scores/           # Target canvas, score cards, image viewer
│   │   ├── hooks/                # Custom React hooks (WebSockets, streams)
│   │   ├── lib/                  # Styling & class merging helpers
│   │   ├── pages/                # Primary application route pages
│   │   ├── store/                # Zustand client state stores
│   │   ├── types/                # TypeScript interface contracts
│   │   └── utils/                # Dynamic WebSocket URL resolver
│   ├── Dockerfile                # Production multi-stage build (Node -> Nginx)
│   ├── nginx.conf                # Ingress & reverse proxy config
│   ├── package.json              # Frontend manifest & scripts
│   └── vite.config.ts            # Vite bundler & dev proxy config
├── runs/                         # YOLO11 trained model artifacts (best.pt)
├── scripts/                      # Operational automation & validation scripts
│   ├── evaluate_yolo.py          # Benchmark metrics script (mAP50, Precision, Recall)
│   ├── prepare_dataset.py        # Polygon annotation to YOLO bbox converter
│   ├── seed_data.py              # Database seeding script (demo tournaments & users)
│   ├── test_docker_stack.py      # End-to-end container stack integration test
│   └── train_yolo.py             # 30-epoch Ultralytics YOLO11 training script
├── src/                          # FastAPI Backend Application Source
│   ├── api/                      # REST & WebSocket API routers
│   ├── middleware/               # ASGI middlewares (auth, errors, rate limits)
│   ├── models/                   # SQLAlchemy ORM database models
│   ├── services/                 # Domain business logic & CV algorithms
│   ├── utils/                    # Common helpers, storage, image processors
│   ├── cache.py                  # Redis connection manager singleton
│   ├── config.py                 # Pydantic BaseSettings environment config
│   ├── database.py               # SQLAlchemy QueuePool engine & session maker
│   ├── dependencies.py           # FastAPI dependency injection (JWT, RBAC)
│   ├── events.py                 # In-process pub/sub EventBus
│   ├── main.py                   # App factory, lifespan handlers, CORS setup
│   ├── schemas.py                # Pydantic v2 request/response schemas
│   ├── security.py               # Bcrypt password hashing & JWT encode/decode
│   └── thread_pool.py            # Shared ThreadPoolExecutor for CV jobs
├── tests/                        # Automated backend test suite
│   ├── conftest.py               # Pytest fixtures & in-memory SQLite DB
│   ├── test_api_endpoints.py     # Route integration tests
│   └── test_services.py          # Unit & computer vision algorithm tests
├── Dockerfile                    # Multi-stage Python 3.11 backend Dockerfile
├── docker-compose.yml            # Multi-service stack definition
└── setup_db.py                   # Self-healing database initialization script
```

---

## 3. Design Patterns Applied

### 3.1 Layered Architecture & Service Layer Pattern
- **Routers (`src/api/`)**: Pure presentation/transport layer. Validate input via Pydantic schemas, inject dependencies, and invoke service methods. Do not contain raw SQL or direct DB queries.
- **Services (`src/services/`)**: Encapsulate all business rules, calculations, OpenCV pipelines, and transactions.
- **Models (`src/models/`)**: Declarative SQLAlchemy models reflecting the database tables.

### 3.2 Dependency Injection Pattern
- Leveraged extensively through FastAPI's `Depends()` framework in [src/dependencies.py](file:///c:/Users/BS01318/OneDrive%20-%20Brain%20Station%2023/Documents/GitHub/SPL-3/src/dependencies.py).
- Injects database sessions (`get_db`), validated users (`get_current_user`), and enforces role-based access checks (`require_role("admin")`).

### 3.3 Event-Driven / Observer Pattern
- Implemented in [src/events.py](file:///c:/Users/BS01318/OneDrive%20-%20Brain%20Station%2023/Documents/GitHub/SPL-3/src/events.py) using an in-memory `EventBus`.
- Allows decoupling score recording from secondary effects (such as Redis leaderboard updates, auditing, and WebSocket fan-out).

### 3.4 Multi-Worker ThreadPool Pattern
- Implemented in [src/thread_pool.py](file:///c:/Users/BS01318/OneDrive%20-%20Brain%20Station%2023/Documents/GitHub/SPL-3/src/thread_pool.py).
- Prevents CPU-heavy image processing and matrix calculations in OpenCV/YOLO from blocking the async event loop of FastAPI. Sized dynamically (4 to 8 workers) based on system load.

### 3.5 Multi-Method Computer Vision Consensus Pattern
- Implemented in [src/services/arrow_detection_service.py](file:///c:/Users/BS01318/OneDrive%20-%20Brain%20Station%2023/Documents/GitHub/SPL-3/src/services/arrow_detection_service.py).
- Employs redundant detection techniques:
  - **Target Localization**: Color band masking + Hough circle transform + multi-zone ellipse fitting.
  - **Arrow Tip Localization**: YOLO11 bounding boxes $\to$ local Canny/Hough line analysis $\to$ puncture hole detection.
  - **Confidence Hierarchy**: Prioritizes puncture holes > line-ellipse intersections > color segments.

### 3.6 Flux / Unidirectional Store Pattern
- Implemented in the frontend using **Zustand** stores ([authStore.ts](file:///c:/Users/BS01318/OneDrive%20-%20Brain%20Station%2023/Documents/GitHub/SPL-3/frontend/src/store/authStore.ts), [sessionStore.ts](file:///c:/Users/BS01318/OneDrive%20-%20Brain%20Station%2023/Documents/GitHub/SPL-3/frontend/src/store/sessionStore.ts), [cameraStore.ts](file:///c:/Users/BS01318/OneDrive%20-%20Brain%20Station%2023/Documents/GitHub/SPL-3/frontend/src/store/cameraStore.ts)).
- Decouples UI component tree rendering from authentication tokens, camera states, and active tournament session data.
