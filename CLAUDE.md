# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Automated Archery Scoring System: a FastAPI backend that runs computer-vision arrow detection on camera images and a React/Vite frontend for tournament administration and live scoring. See [README.md](README.md) for the full feature list and [QUICK_START.md](QUICK_START.md) for environment setup (Postgres, Redis, `.env`, seeding).

## Commands

### Backend (run from repo root)
```bash
poetry install                                    # install deps (or: pip install -r requirements.txt)
alembic upgrade head                              # apply DB migrations
python -m scripts.seed_data                       # seed admin/scorer users + demo tournament
uvicorn src.main:app --reload --port 8000          # run dev server -> http://localhost:8000/docs

pytest                                             # run all backend tests
pytest tests/test_services.py                      # run one test file
pytest tests/test_services.py::TestArrowDetection::test_x -v   # run one test
pytest -m unit                                     # run tests by marker (unit/integration/slow)

black src tests                                    # format
ruff check src tests                               # lint
mypy src                                           # type-check
```
Test config lives in both `pytest.ini` and `[tool.pytest.ini_options]` in `pyproject.toml` (testpaths=`tests`, `asyncio_mode=auto`). Tests use an in-memory SQLite DB (see `tests/conftest.py`), not Postgres — no running DB/Redis is required to run the suite, but `test_client`/`auth_headers` fixtures hit real app routes via `TestClient`.

### Frontend (run from `frontend/`)
```bash
npm install
npm run dev        # Vite dev server -> http://localhost:5173
npm run build      # tsc && vite build
npm run preview
```

### Docker (Postgres + Redis + API)
```bash
docker-compose up -d db cache   # just the datastores, for local backend dev
docker-compose up               # full stack
```

## Architecture

### Backend layering (`src/`)
Requests flow `api/` (routers) → `services/` (business logic) → `models/` (SQLAlchemy ORM). Routers do not talk to the DB directly; they call into a service which owns the transaction and any caching/event logic.

- `main.py` — app factory; registers routers under `/api`, lifespan startup/shutdown (thread pool, cache ping, DB connectivity check), global exception handler, structured request logging middleware.
- `config.py` — single `Settings` (pydantic-settings) object read from `.env`; all tunables (DB pool size, JWT, CORS, rate limits, image processing, websocket batching, thread pool sizing) live here — don't hardcode values that already have a settings field.
- `database.py` / `cache.py` — SQLAlchemy engine/session and Redis client singletons.
- `dependencies.py` — `get_current_user` / `get_optional_user` (JWT-based) and `require_role(role)` factory for RBAC; `admin` implicitly satisfies any role check.
- `security.py` — password hashing (bcrypt) and JWT encode/decode helpers.
- `events.py` — in-process `EventType` enum + pub/sub event bus (fire-and-forget; not a message queue) used to decouple e.g. score recording from leaderboard/websocket broadcast.
- `thread_pool.py` — shared `ThreadPoolExecutor` for offloading blocking image-processing work from async request handlers; sized via `threadpool_*` settings.
- `middleware/` — `RateLimitMiddleware`, `ErrorHandlingMiddleware`, JWT validation middleware, applied as ASGI middleware in `main.py`.
- `models/` — `User`, `Tournament`, `Session` (a tournament round), `SessionArcher`, `Score`, `Camera`, `CameraLaneAssignment`, `AuditLog`. Import the aggregate from `src.models` (`Session` is re-exported there to disambiguate from other "session" concepts).
- `services/arrow_detection_service.py` — the core CV pipeline (OpenCV, optional import — degrades gracefully with `OPENCV_AVAILABLE=False` if `cv2` isn't installed). Multi-stage pipeline per docstring: preprocessing → target-face detection (Hough/color/contour/multi-method voting) → arrow-tip detection (color/Hough/Canny/puncture-hole, multiple independent methods reconciled by confidence) → zone calculation against World Archery 10-ring proportions (`WA_ZONE_BOUNDARIES`) → confidence scoring. When touching scoring logic, the WA zone boundary table and the method-confidence hierarchy (puncture_hole > line_intersection > color_segment) are the two things most likely to silently break.
- `services/scoring_service.py`, `leaderboard_service.py`, `camera_service.py`, `image_service.py`, `report_service.py`, `auth_service.py`, `health_service.py` — one service per domain area; leaderboard is Redis-cached and recalculated on score writes, then broadcast over WebSocket.
- `api/websocket.py` — WS endpoints for live camera previews and score streaming; message batching governed by `websocket_message_batch_window_ms` / `websocket_message_batch_max_events`.

### Frontend (`frontend/src/`)
- `api/` — Axios clients (one file per backend resource: `auth`, `cameras`, `scores`, `sessions`, `tournaments`, `users`, `health`), all routed through `client.ts` which injects the JWT and handles refresh/interceptors.
- `store/` — Zustand stores: `authStore`, `cameraStore`, `sessionStore`. Cross-cutting state (auth, active session, camera connections) lives here rather than in component state.
- `hooks/` — `useWebSocket` (low-level connection), `useCameraPreview`, `useScoreStream` (built on top of `useWebSocket`) for live data.
- `pages/` — one component per route (Dashboard, Tournaments, Scoring, Cameras, Reports, Users, Settings, Login/Register, BatchTesting).
- `types/index.ts` — TypeScript interfaces mirrored from the backend Pydantic schemas/models; keep in sync when changing API response shapes.

### Cross-cutting notes
- Auth: JWT bearer tokens, role-based (`admin`, `scorer`, `spectator`, `archer`); enforce via `require_role()` in route dependencies, not ad-hoc checks in handlers.
- Real-time: score writes → `events.py` publish → leaderboard recompute (Redis) → WebSocket broadcast to subscribed clients. If a score-related change doesn't show up live, check this chain rather than just the REST handler.
- Seed/test credentials: `admin` / `admin123!`, `scorer` / `scorer123!` (see `scripts/seed_data.py`); test fixtures in `tests/conftest.py` create their own users (`testuser` / `TestPassword123!`).
- Deeper reference docs exist at the repo root: `API_SPECIFICATION.md` (endpoints/WS channels), `DATABASE_SCHEMA.md` (schema/indexes), `archery_webapp_spec.md` (frontend spec), `archery_scoring_system_spec.md` (system/AI pipeline spec).

## AI-DLC workflow files

`.github/copilot-instructions.md` and `.aidlc-rule-details/` define an external, opt-in "AI-DLC" multi-phase workflow (Inception → Construction → Operations) with mandatory audit logging to `aidlc-docs/audit.md` and phase-completion approval gates. This only applies if the user explicitly invokes that workflow; it is not a requirement for ordinary edits to this repo.
