# Unit of Work Definitions

**Project**: Automated Archery Scoring System  
**Date**: 2026-05-23  
**Phase**: Units Generation - Part 2: Artifacts  

---

## Unit Decomposition

### System: 2 Independent Units

```
┌─────────────────────────────────────────────────────────────┐
│              AUTOMATED ARCHERY SCORING SYSTEM                │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────┐          ┌──────────────────────┐ │
│  │   BACKEND UNIT       │◄────────►│   FRONTEND UNIT      │ │
│  │  (Python/FastAPI)    │   REST   │  (React/TypeScript)  │ │
│  │                      │  +  WS   │                      │ │
│  └──────────────────────┘          └──────────────────────┘ │
│           │                                    │              │
│           └────────┬───────────────────────────┘              │
│                    │                                           │
│            ┌───────▼────────┐                                 │
│            │  PostgreSQL    │                                 │
│            │   Database     │                                 │
│            └────────────────┘                                 │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

---

## Unit 1: Backend Unit

### Overview
**Name**: Backend Unit  
**Technology Stack**: Python 3.11+, FastAPI 0.110+, PostgreSQL 15+  
**Team**: Senior Backend Developer Agent  

### Responsibility
Implement all server-side logic, image processing pipeline, data persistence, and API/WebSocket endpoints. The Backend is the **system of record** for all business logic, validation, and scoring calculations.

### Key Responsibilities
1. **Authentication & Authorization**
   - JWT token generation and validation
   - Role-based access control (4 roles: SYSTEM_ADMIN, TOURNAMENT_ADMIN, SCORER, ARCHER)
   - HttpOnly cookie management
   - Password hashing and verification

2. **Camera Management**
   - USB camera enumeration and auto-discovery
   - RTSP/HTTP MJPEG camera configuration
   - Connection testing and auto-reconnect logic
   - Real-time camera status monitoring

3. **Tournament & Session Management**
   - Create and manage tournaments
   - Create sessions within tournaments
   - Register archers in sessions
   - Manage session state transitions (created, started, completed)
   - Validate session readiness

4. **Image Processing & Scoring Pipeline**
   - Capture images from cameras (burst mode)
   - Image preprocessing (normalization, filtering)
   - Ring/target detection via OpenCV
   - Arrow detection and localization
   - Score calculation (zone-to-points mapping)
   - Score override and audit trail
   - Multi-camera parallel processing (ThreadPool, 4 workers max)

5. **Reporting**
   - Query session scores and statistics
   - Generate reports (PDF, CSV, JSON formats)
   - Leaderboards and archer rankings
   - Data export for analysis

6. **Real-Time Communication**
   - WebSocket server for live updates
   - Score broadcast to connected clients
   - Camera preview streaming (MJPEG over WebSocket, 15 fps)
   - Event publishing (ScoreCalculated, CameraDisconnected, etc.)

7. **Data Persistence**
   - PostgreSQL schema design and migrations
   - User data, camera configs, tournament/session info
   - Score records with audit trail
   - Immutable historical data

### Scope & Boundaries
**Includes**:
- All API endpoints (REST + WebSocket)
- All business logic (scoring, validation, authorization)
- Image processing (OpenCV pipeline)
- Database schema and persistence
- Event publishing
- Error handling and logging

**Excludes** (Frontend responsibility):
- User interface rendering
- Client-side state management
- Browser DOM manipulation
- Client-side form validation
- Client-side routing

### Services & Components (from Application Design)
- **AuthService** — JWT and user authentication
- **CameraService** — Camera enumeration and management
- **TournamentService** — Tournament lifecycle
- **SessionService** — Session orchestration
- **ScoringService** — Image processing pipeline (main orchestrator)
- **ReportService** — Report generation
- **EventBus** — Event-driven communication
- **WebSocketService** — Real-time connections

- **Repositories**: UserRepository, CameraRepository, TournamentRepository, SessionRepository, ArcherRepository, ScoreRepository
- **Image Processing Components**: ImageCaptureComponent, ImagePreprocessComponent, RingDetectionComponent, ArrowDetectionComponent, ScoringCalculatorComponent
- **Report Generators**: PDFReportGenerator, CSVReportGenerator, JSONReportGenerator

### Directory Structure (Feature-Based)
```
backend/
├── main.py                      # FastAPI app entry point
├── config.py                    # Configuration (DB, logging, settings)
├── requirements.txt             # Python dependencies
├── pyproject.toml              # Poetry configuration
│
├── core/                        # Shared infrastructure
│   ├── __init__.py
│   ├── database.py              # SQLAlchemy setup, connection pooling
│   ├── logger.py                # Structured logging (structlog)
│   ├── security.py              # JWT, password hashing
│   └── exceptions.py            # Domain exceptions
│
├── features/                    # Feature-based modules
│   ├── authentication/
│   │   ├── routes.py            # Auth endpoints (login, logout, refresh)
│   │   ├── services.py          # AuthService
│   │   ├── models.py            # User model
│   │   └── schemas.py           # Pydantic schemas (LoginRequest, TokenResponse)
│   │
│   ├── cameras/
│   │   ├── routes.py            # Camera endpoints
│   │   ├── services.py          # CameraService
│   │   ├── manager.py           # CameraManager (enumeration, auto-probe)
│   │   ├── models.py            # Camera model
│   │   └── schemas.py           # Pydantic schemas
│   │
│   ├── tournaments/
│   │   ├── routes.py
│   │   ├── services.py          # TournamentService
│   │   ├── models.py
│   │   └── schemas.py
│   │
│   ├── sessions/
│   │   ├── routes.py
│   │   ├── services.py          # SessionService
│   │   ├── manager.py           # SessionManager (state machine)
│   │   ├── models.py
│   │   └── schemas.py
│   │
│   ├── scoring/
│   │   ├── routes.py            # Scoring endpoints
│   │   ├── services.py          # ScoringService (orchestrator)
│   │   ├── components/
│   │   │   ├── capture.py       # ImageCaptureComponent
│   │   │   ├── preprocess.py    # ImagePreprocessComponent
│   │   │   ├── ring_detection.py # RingDetectionComponent
│   │   │   ├── arrow_detection.py # ArrowDetectionComponent
│   │   │   └── calculator.py    # ScoringCalculatorComponent
│   │   ├── models.py
│   │   └── schemas.py
│   │
│   ├── reports/
│   │   ├── routes.py
│   │   ├── services.py          # ReportService
│   │   ├── generators/
│   │   │   ├── pdf_generator.py
│   │   │   ├── csv_generator.py
│   │   │   └── json_generator.py
│   │   ├── models.py
│   │   └── schemas.py
│   │
│   ├── permissions/
│   │   ├── roles.py             # Role enum, permission constants
│   │   ├── decorators.py        # @require_role decorator
│   │   └── policies.py          # Authorization policies
│   │
│   └── realtime/
│       ├── websocket.py         # WebSocket handler
│       ├── connection_mgr.py    # WebSocketConnectionManager
│       ├── events.py            # DomainEvent classes
│       └── event_bus.py         # EventBus implementation
│
├── repositories/                # Data access layer
│   ├── __init__.py
│   ├── base.py                  # BaseRepository
│   ├── user.py                  # UserRepository
│   ├── camera.py                # CameraRepository
│   ├── tournament.py            # TournamentRepository
│   ├── session.py               # SessionRepository
│   ├── archer.py                # ArcherRepository
│   └── score.py                 # ScoreRepository
│
├── models/                      # SQLAlchemy domain models
│   ├── __init__.py
│   ├── user.py                  # User model
│   ├── camera.py                # Camera model
│   ├── tournament.py            # Tournament model
│   ├── session.py               # Session model
│   ├── session_archer.py        # SessionArcher association
│   └── score.py                 # Score model
│
├── schemas/                     # Pydantic request/response schemas
│   ├── __init__.py
│   ├── auth.py
│   ├── camera.py
│   ├── tournament.py
│   ├── session.py
│   ├── scoring.py
│   └── report.py
│
├── middleware/                  # Custom middleware
│   ├── __init__.py
│   ├── auth.py                  # AuthorizationMiddleware (token extraction)
│   ├── logging.py               # Request/response logging
│   └── error.py                 # Error handling middleware
│
├── storage/                     # Local filesystem storage
│   ├── raw/                     # Raw camera images
│   └── annotated/               # Annotated images (rings/arrows marked)
│
├── tests/                       # Unit and integration tests
│   ├── __init__.py
│   ├── conftest.py              # Pytest fixtures
│   ├── test_auth.py
│   ├── test_scoring.py
│   ├── test_reports.py
│   └── ...
│
├── migrations/                  # Alembic database migrations
│   └── ...
│
├── docker/                      # Docker configuration
│   └── Dockerfile
│
└── .env.example                 # Environment variables template
```

### API Endpoints (Summary)
- **Authentication**: `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, `POST /api/v1/auth/refresh`
- **Cameras**: `GET /api/v1/cameras`, `POST /api/v1/cameras/{id}/test`, `PUT /api/v1/cameras/{id}`
- **Tournaments**: `POST /api/v1/tournaments`, `GET /api/v1/tournaments`, `PUT /api/v1/tournaments/{id}`
- **Sessions**: `POST /api/v1/sessions`, `POST /api/v1/sessions/{id}/start`, `POST /api/v1/sessions/{id}/complete`
- **Scoring**: `POST /api/v1/scoring/calculate`, `PUT /api/v1/scores/{id}/override`
- **Reports**: `GET /api/v1/reports/session/{id}`, `GET /api/v1/leaderboard/{id}`
- **WebSocket**: `WS /ws` (scores), `WS /ws/camera/{id}/preview` (camera preview)

### Performance Targets
- **Scoring**: < 1 second end-to-end
- **API Response**: < 200ms for standard queries
- **WebSocket Broadcast**: < 100ms delivery
- **Concurrent Cameras**: 4+ simultaneous with ThreadPool

### Database
- **Primary**: PostgreSQL 15+
- **Development**: SQLite alternative available
- **Migrations**: Alembic for schema versioning
- **Connection Pool**: SQLAlchemy with pooling

### Deployment
- **Container**: Docker image (Python 3.11-slim base)
- **Server**: Uvicorn ASGI server (port 8000 internal)
- **Behind**: Nginx reverse proxy (production)
- **Storage**: Local filesystem (`/storage/raw/`, `/storage/annotated/`)
- **Logging**: Structured logs via structlog
- **Health**: Liveness/readiness endpoints

---

## Unit 2: Frontend Unit

### Overview
**Name**: Frontend Unit  
**Technology Stack**: React 18+, TypeScript 5+, Vite 5+, Tailwind CSS 3+  
**Team**: Senior Frontend Developer Agent  

### Responsibility
Implement all user interface, client-side state management, real-time communication, and user interactions. The Frontend is the **primary user interaction point** for all archery system features.

### Key Responsibilities
1. **User Authentication UI**
   - Login form
   - Session management (display current user, logout)
   - Token refresh handling
   - Permission-aware UI (show/hide features by role)

2. **Camera Management UI**
   - Camera discovery and enumeration display
   - Camera status indicators (connected, disconnected, error)
   - Lane assignment UI
   - Camera preview feeds (live 15 fps MJPEG streams)
   - Connection troubleshooting UI

3. **Tournament & Session UI**
   - Tournament creation and management forms
   - Session setup and archer registration
   - Session state display (created, started, completed)
   - Archer roster and participation tracking

4. **Scoring UI**
   - Scoring interface (camera preview, trigger scoring button)
   - Score display and confirmation
   - Real-time score updates via WebSocket
   - Score history and audit trail
   - Score override forms (with reasons)

5. **Reporting & Leaderboard UI**
   - Leaderboard display with rankings
   - Report generation forms (PDF, CSV, JSON)
   - Report download/export
   - Data visualization and charts (via Recharts)

6. **Real-Time Features**
   - WebSocket connection management
   - Live score broadcasts (automatic UI updates)
   - Live camera status updates
   - Connection state indicators (online/offline)
   - Error notifications and recovery

7. **User Experience**
   - Responsive design (works on desktop, tablet, mobile)
   - Accessibility (WCAG compliance)
   - Error messages and user guidance
   - Loading states and spinners
   - Toast notifications for feedback

### Scope & Boundaries
**Includes**:
- React components and pages
- Client-side state management (Zustand)
- WebSocket client
- Form validation (React Hook Form + Zod)
- Routing (React Router v6)
- Styling (Tailwind CSS)
- UI components (shadcn/ui)
- HTTP client (Axios)
- Error handling and recovery

**Excludes** (Backend responsibility):
- Business logic (validation, scoring calculations)
- Database operations
- User authentication (JWT generation)
- Image processing
- Report generation
- WebSocket server

### Components & Features (Feature-Based)
- **Authentication**: Login page, logout, session indicators
- **Cameras**: Camera list, preview feeds, status indicators, lane assignment
- **Tournaments**: Tournament list, create tournament form, tournament details
- **Sessions**: Session setup, archer registration, session state display
- **Scoring**: Scoring interface, score display, score overrides, history
- **Reports**: Report generation form, leaderboard display, export
- **Layout**: Navigation bar, sidebar, responsive layout
- **Common**: Loading spinners, error boundaries, notifications, modals

### Directory Structure (Feature-Based)
```
frontend/
├── index.html                   # HTML entry point
├── package.json                 # npm dependencies, scripts
├── tsconfig.json                # TypeScript configuration
├── vite.config.ts               # Vite configuration
├── tailwind.config.js           # Tailwind configuration
├── postcss.config.js            # PostCSS configuration
│
├── src/
│   ├── main.tsx                 # React app entry point
│   ├── App.tsx                  # Root component
│   ├── App.css                  # Global styles
│   │
│   ├── types/                   # TypeScript type definitions
│   │   ├── index.ts             # Common types
│   │   ├── api.ts               # API response types (from Backend)
│   │   ├── domain.ts            # Domain types (Score, Archer, etc.)
│   │   └── websocket.ts         # WebSocket event types
│   │
│   ├── services/                # API clients and WebSocket
│   │   ├── api-client.ts        # Axios instance, base config
│   │   ├── auth.ts              # Auth API calls
│   │   ├── cameras.ts           # Camera API calls
│   │   ├── tournaments.ts       # Tournament API calls
│   │   ├── sessions.ts          # Session API calls
│   │   ├── scoring.ts           # Scoring API calls
│   │   ├── reports.ts           # Report API calls
│   │   └── websocket.ts         # WebSocket connection handler
│   │
│   ├── hooks/                   # Custom React hooks
│   │   ├── useAuth.ts           # Auth context hook
│   │   ├── useWebSocket.ts      # WebSocket connection hook
│   │   ├── useCamera.ts         # Camera state hook
│   │   ├── useScoring.ts        # Scoring state hook
│   │   └── ...
│   │
│   ├── store/                   # Zustand state management
│   │   ├── index.ts             # Store configuration
│   │   ├── authStore.ts         # Auth state (user, token, roles)
│   │   ├── cameraStore.ts       # Camera state (list, status, preview)
│   │   ├── sessionStore.ts      # Session state (current session, archers)
│   │   ├── scoringStore.ts      # Scoring state (current scores, history)
│   │   ├── tournamentStore.ts   # Tournament state
│   │   └── notificationStore.ts # Notification/toast state
│   │
│   ├── components/              # Reusable React components
│   │   ├── Layout/
│   │   │   ├── Navbar.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   └── Footer.tsx
│   │   │
│   │   ├── Common/
│   │   │   ├── LoadingSpinner.tsx
│   │   │   ├── ErrorBoundary.tsx
│   │   │   ├── Toast.tsx
│   │   │   ├── Modal.tsx
│   │   │   └── Button.tsx
│   │   │
│   │   ├── Auth/
│   │   │   ├── LoginForm.tsx
│   │   │   ├── LogoutButton.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   │
│   │   ├── Camera/
│   │   │   ├── CameraList.tsx
│   │   │   ├── CameraPreview.tsx
│   │   │   ├── CameraStatus.tsx
│   │   │   └── LaneAssignment.tsx
│   │   │
│   │   ├── Tournament/
│   │   │   ├── TournamentList.tsx
│   │   │   ├── TournamentForm.tsx
│   │   │   └── TournamentDetails.tsx
│   │   │
│   │   ├── Session/
│   │   │   ├── SessionSetup.tsx
│   │   │   ├── ArcherRegistration.tsx
│   │   │   ├── SessionState.tsx
│   │   │   └── SessionList.tsx
│   │   │
│   │   ├── Scoring/
│   │   │   ├── ScoringInterface.tsx
│   │   │   ├── ScoreDisplay.tsx
│   │   │   ├── ScoreOverrideForm.tsx
│   │   │   ├── ScoreHistory.tsx
│   │   │   └── ConfirmScore.tsx
│   │   │
│   │   ├── Report/
│   │   │   ├── ReportGenerator.tsx
│   │   │   ├── Leaderboard.tsx
│   │   │   ├── LeaderboardTable.tsx
│   │   │   ├── DataVisualization.tsx
│   │   │   └── ExportButton.tsx
│   │   │
│   │   └── UI/                  # shadcn/ui imported components
│   │       ├── Button.tsx
│   │       ├── Input.tsx
│   │       ├── Card.tsx
│   │       ├── Dialog.tsx
│   │       └── ... (other shadcn components)
│   │
│   ├── pages/                   # Page-level components
│   │   ├── Dashboard.tsx        # Home/dashboard page
│   │   ├── LoginPage.tsx        # Login page
│   │   ├── TournamentPage.tsx   # Tournament management
│   │   ├── SessionPage.tsx      # Session management
│   │   ├── ScoringPage.tsx      # Scoring interface
│   │   ├── ReportPage.tsx       # Reports and leaderboard
│   │   ├── SettingsPage.tsx     # User settings
│   │   └── NotFoundPage.tsx     # 404 page
│   │
│   ├── router/                  # React Router configuration
│   │   ├── index.tsx            # Route definitions
│   │   └── protectedRoutes.tsx  # Role-based route protection
│   │
│   ├── utils/                   # Utility functions
│   │   ├── api-errors.ts        # API error handling
│   │   ├── validators.ts        # Client-side validation
│   │   ├── formatters.ts        # Data formatting (dates, scores)
│   │   └── constants.ts         # App constants
│   │
│   ├── styles/                  # Global styles
│   │   ├── globals.css          # Global CSS
│   │   ├── variables.css        # CSS variables
│   │   └── tailwind.css         # Tailwind imports
│   │
│   └── assets/                  # Static assets
│       ├── images/
│       ├── icons/
│       └── logos/
│
├── public/                      # Public assets (served as-is)
│   ├── favicon.ico
│   └── logo.png
│
├── tests/                       # Unit and integration tests
│   ├── __setup__.ts
│   ├── components/
│   ├── hooks/
│   ├── store/
│   ├── services/
│   └── ...
│
├── docker/                      # Docker configuration
│   └── Dockerfile
│
├── .env.example                 # Environment variables template
├── .eslintrc.cjs               # ESLint configuration
└── .prettierrc                  # Prettier configuration
```

### Pages (User Flows)
- **Dashboard** — Overview, quick actions, current session
- **Login** — Authentication entry point
- **Tournaments** — Create, list, manage tournaments
- **Sessions** — Setup sessions, register archers
- **Scoring** — Main interface for scorers (camera preview, trigger scoring, view scores)
- **Reports** — Leaderboard, data visualization, export options
- **Settings** — User preferences, camera configuration

### State Management (Zustand Stores)
- **authStore** — Current user, roles, token, login/logout
- **cameraStore** — Available cameras, current preview, status
- **sessionStore** — Current session, archers, state
- **scoringStore** — Current scores, history, overrides
- **tournamentStore** — Current tournament, metadata
- **notificationStore** — Toast messages, error alerts

### Real-Time Features (WebSocket)
- **Score Broadcasts** — Auto-update leaderboard, archer scores
- **Camera Status** — Live connection status changes
- **Camera Preview** — 15 fps MJPEG stream
- **Session Events** — Session started, completed, etc.

### HTTP Client (Axios)
- Base URL configuration (from environment)
- Default headers (Content-Type, Accept)
- Request/response interceptors (token injection, error handling)
- Error message extraction and display

### Form Validation
- React Hook Form for form state
- Zod for schema validation
- Client-side validation for UX
- Server-side errors displayed in UI

### Responsive Design
- Mobile-first Tailwind CSS
- Breakpoints: sm, md, lg, xl, 2xl
- Mobile navigation (hamburger menu)
- Touch-friendly buttons and inputs

### Performance Optimization
- Code splitting (React Router lazy loading)
- Image optimization (camera preview streaming)
- State batching (Zustand)
- Memoization where needed (React.memo, useMemo)

### Accessibility
- ARIA labels on interactive elements
- Keyboard navigation (Tab, Enter)
- Color contrast (WCAG AA minimum)
- Screen reader support via shadcn/ui

---

## Unit Boundaries & Integration

### Data Flow: Backend → Frontend
- Backend API returns JSON (Pydantic models → JSON)
- Frontend receives JSON (Axios) → TypeScript types (Zod validation)
- Frontend stores in Zustand
- Components consume from store

### Real-Time Flow: Backend → Frontend
- Backend publishes event via EventBus
- WebSocket service broadcasts to all clients
- Frontend WebSocket hook receives message
- Zustand store updated
- Components re-render (React)

### User Input Flow: Frontend → Backend
- User fills form (React Hook Form)
- Client-side validation (Zod)
- Submit → Axios POST to API
- Backend validates (Pydantic)
- Backend executes business logic
- Response returned
- Frontend updates store, displays result

### Authentication Flow
- Frontend: Login form → POST /auth/login
- Backend: Validate credentials → Return JWT
- Frontend: Store in httpOnly cookie (sent automatically)
- Frontend: Set Zustand authStore
- Frontend: Redirect to dashboard
- Subsequent requests: Cookie auto-attached by browser
- Backend: Middleware validates token from Cookie/Header
- All endpoints protected via role-based decorators

---

## Deployment Model

### Development
- **Backend**: `python main.py` (Uvicorn dev server, port 8000)
- **Frontend**: `npm run dev` (Vite dev server, port 5173)
- **Database**: Docker PostgreSQL (port 5432)
- **Docker Compose**: Local development stack (optional)

### Production
- **Backend Container**: Python image, Uvicorn, port 8000
- **Frontend Container**: Node build → static assets, Nginx serving, port 80
- **Nginx Reverse Proxy**: Routes `/api` to Backend, `/` to Frontend
- **Database**: PostgreSQL in separate container or managed service
- **Deployment**: Docker Compose or orchestrator (Kubernetes)

### Independent Deployments
- Backend can be deployed without Frontend (API versioning)
- Frontend can be deployed without Backend (API already stable)
- Both share single PostgreSQL database
- Schema migrations handled via Alembic (Backend responsibility)

---

## Success Criteria

### Backend Unit Success
- ✅ All 21 stories implemented and passing tests
- ✅ Image processing pipeline < 1 second end-to-end
- ✅ API responses < 200ms for standard queries
- ✅ WebSocket broadcasts < 100ms delivery
- ✅ 4+ simultaneous cameras with parallel processing
- ✅ All security baseline rules implemented
- ✅ All PBT rules implemented
- ✅ 60-70% code coverage (unit + integration tests)
- ✅ PostgreSQL schema designed and migrated
- ✅ Docker image builds and runs

### Frontend Unit Success
- ✅ All 21 stories implemented with UI components
- ✅ Responsive design (mobile, tablet, desktop)
- ✅ Real-time updates via WebSocket (< 100ms)
- ✅ Login flow working end-to-end
- ✅ Scoring interface fully functional
- ✅ Reports and leaderboard displaying correctly
- ✅ All forms validated (client + server)
- ✅ Error handling and recovery
- ✅ Accessibility (WCAG AA)
- ✅ Docker image builds and runs

### Integration Success
- ✅ Frontend and Backend communicate via REST + WebSocket
- ✅ API contracts match (requests/responses)
- ✅ WebSocket event schemas aligned
- ✅ Database schema works with both units
- ✅ End-to-end scoring flow (capture → display)
- ✅ Real-time updates flowing from Backend → Frontend
- ✅ Authentication and authorization enforced
- ✅ Error messages displayed correctly in UI
- ✅ Both units deploy independently
- ✅ Full system integration testing passes

