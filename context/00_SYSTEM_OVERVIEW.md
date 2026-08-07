# SPL-3: Archery Scoring System — Full System Overview

## Project Description
এটি একটি **Real-time Archery Scoring System** যা Computer Vision (CV) ব্যবহার করে archery target এর image থেকে automatically arrow position detect করে score calculate করে। পুরো system টি একটি web application হিসাবে কাজ করে — FastAPI backend + React (Vite+TypeScript) frontend।

## Architecture Summary

```
┌─────────────────────────────────────────────────────────┐
│                    FRONTEND (React + Vite)               │
│  Pages: Dashboard, Scoring, Tournaments, BatchTesting,  │
│         Cameras, Reports, Users, Login, Register        │
│  Tech: TypeScript, TailwindCSS, React Router            │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP REST + WebSocket
                       ▼
┌─────────────────────────────────────────────────────────┐
│                   BACKEND (FastAPI)                       │
│                                                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │  API      │  │Middleware│  │ Events   │              │
│  │  Routes   │  │(CORS,    │  │ (PubSub  │              │
│  │          │  │RateLimit,│  │  EventBus)│              │
│  │          │  │ErrorHndl)│  │          │              │
│  └────┬─────┘  └──────────┘  └──────────┘              │
│       │                                                  │
│  ┌────▼─────────────────────────────────────┐           │
│  │           SERVICES LAYER                  │           │
│  │                                           │           │
│  │  ┌─────────────────────────────────────┐ │           │
│  │  │  ArrowDetectionService (2665 lines) │ │  ← CORE  │
│  │  │  Multi-stage CV Pipeline            │ │           │
│  │  └─────────────────────────────────────┘ │           │
│  │  ┌──────────────┐ ┌──────────────────┐  │           │
│  │  │ScoringService│ │  ImageService    │  │           │
│  │  │(DB write/    │ │  (save/annotate/ │  │           │
│  │  │ validate)    │ │   compress)      │  │           │
│  │  └──────────────┘ └──────────────────┘  │           │
│  │  ┌──────────────┐ ┌──────────────────┐  │           │
│  │  │AuthService   │ │  CameraService   │  │           │
│  │  └──────────────┘ └──────────────────┘  │           │
│  │  ┌──────────────┐ ┌──────────────────┐  │           │
│  │  │LeaderboardSvc│ │  ReportService   │  │           │
│  │  └──────────────┘ └──────────────────┘  │           │
│  └───────────────────────────────────────────┘           │
│       │                                                  │
│  ┌────▼─────────────────────────────────────┐           │
│  │           DATABASE LAYER                  │           │
│  │  SQLAlchemy ORM + Alembic Migrations     │           │
│  │  PostgreSQL (prod) / SQLite (dev)         │           │
│  │                                           │           │
│  │  Tables: users, tournaments, sessions,    │           │
│  │    session_archers, scores, cameras,      │           │
│  │    camera_lane_assignments, audit_logs    │           │
│  └───────────────────────────────────────────┘           │
│       │                                                  │
│  ┌────▼──────┐  ┌────────────┐                          │
│  │ Redis     │  │ File       │                          │
│  │ Cache     │  │ Storage    │                          │
│  │ (optional)│  │ (images)   │                          │
│  └───────────┘  └────────────┘                          │
└─────────────────────────────────────────────────────────┘
```

## Tech Stack
| Layer       | Technology                                 |
|-------------|-------------------------------------------|
| Frontend    | React 18, TypeScript, Vite, TailwindCSS   |
| Backend     | Python 3.11+, FastAPI, Uvicorn            |
| Database    | PostgreSQL (Alembic migrations)           |
| Cache       | Redis (optional, in-memory fallback)       |
| CV Engine   | OpenCV (cv2), NumPy                        |
| Auth        | JWT (HS256), bcrypt password hashing      |
| Deployment  | Docker, Docker Compose                     |
| Data Format | YOLOv8 (Roboflow dataset)                 |

## Directory Structure
```
SPL-3/
├── alembic/              # Database migration scripts
├── Data/                 # YOLOv8 training dataset (504 images)
│   ├── train/            # 353 training images + labels
│   ├── valid/            # 76 validation images + labels
│   ├── test/             # 75 test images + labels
│   └── data.yaml         # Dataset config (6 classes)
├── frontend/             # React+Vite frontend
│   └── src/
│       ├── pages/        # 10 page components
│       ├── components/   # Reusable UI components
│       ├── api/          # API client functions
│       ├── hooks/        # Custom React hooks
│       ├── store/        # State management
│       └── types/        # TypeScript type definitions
├── src/                  # Python backend
│   ├── api/              # FastAPI route handlers (11 files)
│   ├── models/           # SQLAlchemy ORM models (6 files)
│   ├── services/         # Business logic (8 files)
│   ├── middleware/        # CORS, rate limit, error handling
│   ├── utils/            # Constants, image utils, storage
│   ├── main.py           # FastAPI app factory
│   ├── config.py         # Pydantic settings
│   ├── database.py       # SQLAlchemy engine/session
│   ├── events.py         # In-process pub/sub event bus
│   ├── schemas.py        # Pydantic request/response models
│   ├── security.py       # JWT + password hashing
│   └── cache.py          # Redis cache manager
├── scripts/              # DB init, seed data
├── tests/                # Unit + integration tests
├── alembic.ini           # Alembic configuration
├── pyproject.toml        # Python project config
├── Dockerfile            # Container build
└── docker-compose.yml    # Multi-container setup
```

## Key Design Patterns (NFR Patterns)
| Pattern # | Name                    | Implementation                     |
|-----------|------------------------|-----------------------------------|
| #1        | DB Connection Resilience| Exponential backoff retry (database.py) |
| #2        | Scoring Failure Recovery| Auto-retry score recording (scoring_service.py) |
| #4        | Image Fallback Chain   | Multi-method arrow detection pipeline |
| #9        | Storage Management     | 90-day image archival + quota      |
| #10       | Thread Pool Scaling    | Configurable ThreadPoolExecutor    |
| #12       | Image Compression      | JPEG quality 70 for latency        |
| #13       | Cache Invalidation     | Redis-based leaderboard cache      |
| #14       | Connection Pool Tuning | QueuePool with pre_ping            |
| #17       | Rate Limiting          | Per-endpoint request throttling    |
| #18       | Structured Logging     | structlog with request tracing     |
| #20       | CORS Security          | Configurable origin whitelist      |

## User Roles
- **admin**: Full system access, score overrides
- **scorer**: Record scores, manage sessions
- **spectator**: Read-only access to leaderboards
- **archer**: View personal scores (future)
