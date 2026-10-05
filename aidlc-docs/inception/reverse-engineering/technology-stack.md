# Technology Stack Specification — Automated Archery Scoring System (SPL-3)

**Lifecycle Stage**: Inception / Reverse Engineering  
**Standard**: AIDLC Process Guidelines (`inception/reverse-engineering.md`)

---

## 1. Programming Languages & Runtimes

| Technology | Version | Usage | Justification & Role |
|---|---|---|---|
| **Python** | 3.11+ | Backend Application & ML Pipelines | Native support for PyTorch, OpenCV, high-performance async I/O via FastAPI. |
| **TypeScript** | ~6.0.2 | Frontend Web Client | Type-safe React components, mirrored API interfaces from backend Pydantic models. |
| **JavaScript / Node.js**| 20+ / 22+ | Build Pipeline & Tooling | Fast Vite bundling and npm dependency management. |
| **SQL** | PostgreSQL Dialect | Persistent Storage | Complex joins, transactional consistency for tournament scoring records. |

---

## 2. Core Frameworks & Application Libraries

### 2.1 Backend Ecosystem
- **FastAPI (v0.110.0)**: Modern, high-performance async Python web framework using Starlette and Pydantic. Provides automatic OpenAPI docs at `/docs`.
- **Uvicorn (v0.27.0)**: Lightning-fast ASGI server implementation using `uvloop` and `httptools`.
- **SQLAlchemy (v2.0.23)**: Enterprise ORM utilizing `QueuePool` connection management.
- **Pydantic (v2.5.3) & Pydantic-Settings (v2.1.0)**: Strict data parsing, validation, and `.env` configuration management.
- **Alembic (v1.12.0)**: Database migration tool supporting online schema evolution.
- **Structlog (v24.1.0)**: Structured JSON logging with request tracing identifiers.

### 2.2 Machine Learning & Computer Vision Ecosystem
- **Ultralytics YOLO11 (v8.3.241)**: State-of-the-art object detection engine trained on 504 target face images with 1,806 bounding boxes (`best.pt`).
- **PyTorch (v2.x CPU Wheels)**: Deep learning tensor framework. Optimized with CPU-only wheels to reduce Docker image size by 1.5GB.
- **OpenCV Python (v4.8.1.78 - headless)**: Industrial computer vision library powering edge detection, Hough transforms, contour moments, and subpixel refinement.
- **NumPy (v1.24.3)**: High-speed vectorized array operations for coordinate transformations and Euclidean distance calculations.

### 2.3 Frontend Ecosystem
- **React (v18.x / 19.x compatible)**: Declarative UI component library.
- **Vite (v8.0.x)**: Next-generation frontend build tool with instantaneous Hot Module Replacement (HMR).
- **Tailwind CSS (v4.x)**: Utility-first styling framework with dynamic theme tokens and responsive layouts.
- **Zustand (v5.0.x)**: Minimalist, scalable client state management with zero boilerplate.
- **Recharts (v3.8.x)**: Composable SVG charting library for archer performance visualization.
- **Lucide React (v1.17.x)**: Modern icon library.
- **Axios (v1.17.x)**: Promise-based HTTP client with request/response JWT interceptors.

---

## 3. Infrastructure & Datastores

| System | Version | Deployment Model | Functionality |
|---|---|---|---|
| **PostgreSQL** | 15 Alpine | Docker Container (`db`) | Primary relational data store. ACID compliant with automated health checks. |
| **Redis** | 7 Alpine | Docker Container (`cache`) | High-speed cache and sorted sets for live leaderboards. Memory limited to 512MB with `allkeys-lru`. |
| **Nginx** | Alpine | Docker Container (`frontend`)| Reverse proxy, SPA routing fallback, WebSocket upgrading, and static asset delivery. |
| **Docker Compose** | v2.x / v5.x | Orchestrator | Single-command deployment (`docker compose up -d --build`). |

---

## 4. Testing & Quality Assurance Toolchain

- **Pytest (v7.4.3)**: Standard test framework for Python unit and integration testing.
- **Pytest-Asyncio (v0.23.2)**: Async test fixture support for FastAPI endpoints.
- **Pytest-Cov (v4.1.0)**: Code coverage reporting.
- **AIOSqlite (v0.19.0)**: In-memory SQLite testing backend used in `tests/conftest.py` for rapid test execution without requiring Postgres.
