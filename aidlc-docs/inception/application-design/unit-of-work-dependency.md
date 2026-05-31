# Unit of Work Dependencies & Integration

**Project**: Automated Archery Scoring System  
**Date**: 2026-05-23  

---

## Inter-Unit Dependencies

### Dependency Matrix

| Dependency | Backend Depends On | Frontend Depends On |
|---|---|---|
| **API Contracts** | N/A | ✅ Backend API endpoints (REST) |
| **WebSocket Protocol** | N/A | ✅ Backend WebSocket server |
| **Authentication** | ✅ Token generation | ✅ Receives JWT from Backend |
| **Database** | ✅ PostgreSQL (primary owner) | ❌ Indirect (via Backend API only) |
| **Image Processing** | ✅ Own responsibility | ❌ N/A (Backend handles) |
| **Business Logic** | ✅ Own responsibility | ❌ N/A (calls Backend) |
| **UI Rendering** | ❌ N/A | ✅ Own responsibility |
| **State Management** | ❌ N/A (Backend stateless) | ✅ Zustand (own state) |
| **Type Definitions** | ✅ Pydantic (own models) | ✅ TypeScript (own types) |
| **Shared Code** | ✅ Owns shared logic | ❌ Imports via API only |

### Dependency Direction
```
Frontend ──────► Backend
         ◄──────
  (REST + WebSocket)

Backend ──────► PostgreSQL
        ◄──────
 (reads/writes)

Frontend ──────X Backend Database
          (no direct access)
```

**Key Principle**: Frontend has ONE dependency: Backend API (REST + WebSocket). Backend has NO dependencies on Frontend.

---

## Integration Points

### 1. REST API Integration

**Backend Provides**:
- Endpoints for all CRUD operations
- Request/response validation (Pydantic)
- Error responses with standardized format
- HTTP status codes (200, 400, 401, 403, 404, 500)

**Frontend Consumes**:
- HTTP requests (Axios client)
- Parses JSON responses
- Maps to TypeScript types
- Displays errors to user

**Defined Endpoints** (Backend responsibility; Frontend implements client):
```
Authentication:
  POST /api/v1/auth/login          (credentials) → {access_token, expires_in}
  POST /api/v1/auth/logout         (token) → {status}
  POST /api/v1/auth/refresh        (token) → {access_token}

Cameras:
  GET /api/v1/cameras              () → [{id, name, status, type}]
  POST /api/v1/cameras/{id}/test   ({config}) → {connected: bool}
  PUT /api/v1/cameras/{id}         ({config}) → {id, name, status}

Tournaments:
  POST /api/v1/tournaments         ({name, date}) → {id, name}
  GET /api/v1/tournaments          () → [{id, name, date}]
  PUT /api/v1/tournaments/{id}     ({...updates}) → {id, name}

Sessions:
  POST /api/v1/sessions            ({tournament_id}) → {id, tournament_id, status}
  GET /api/v1/sessions/{id}        () → {id, status, archers[]}
  POST /api/v1/sessions/{id}/start () → {id, status: STARTED}
  POST /api/v1/sessions/{id}/end   () → {id, status: COMPLETED}

Archers (in session):
  POST /api/v1/sessions/{id}/archers    ({name, bib}) → {id, name, bib}
  GET /api/v1/sessions/{id}/archers     () → [{id, name, bib}]

Scoring:
  POST /api/v1/scoring/calculate   ({session_id, archer_id, camera_id}) → {zones[], scores[], confidence}
  PUT /api/v1/scores/{id}/override ({zone, reason}) → {id, zone_override}

Reports:
  GET /api/v1/reports/session/{id}       () → {format} → [PDF|CSV|JSON]
  GET /api/v1/leaderboard/{session_id}   () → [{rank, archer, total_score}]
```

**Contract Principles**:
- Backend fully designs API (no frontend veto)
- Frontend implements exactly to spec
- Changes negotiated via API versioning (/v1/ → /v2/)
- Breaking changes require both units' preparation

---

### 2. WebSocket Integration

**Backend Provides**:
- WebSocket server listening on `WS /ws`
- Event broadcasting to all connected clients
- Event schema in JSON format
- Automatic reconnection guidance

**Frontend Consumes**:
- Connects to WebSocket endpoint
- Listens for events
- Updates Zustand store when events arrive
- Auto-reconnects on disconnect

**WebSocket Events** (Backend publishes; Frontend listens):

**Score Broadcasts** (Live leaderboard updates):
```json
{
  "type": "score_calculated",
  "data": {
    "session_id": "uuid",
    "archer_id": "uuid",
    "end_num": 1,
    "zones": [8, 9, 10],
    "total_score": 27,
    "timestamp": "2026-05-23T12:00:00Z"
  }
}
```

**Camera Status Changes**:
```json
{
  "type": "camera_status_changed",
  "data": {
    "camera_id": "uuid",
    "status": "CONNECTED" | "DISCONNECTED" | "ERROR",
    "message": "...",
    "timestamp": "2026-05-23T12:00:00Z"
  }
}
```

**Camera Preview Stream**:
```
WS /ws/camera/{camera_id}/preview
Receives: MJPEG frames (binary) at 15 fps
Frontend: Renders in <img> or canvas element
```

**Session Events**:
```json
{
  "type": "session_started" | "session_completed",
  "data": {
    "session_id": "uuid",
    "status": "STARTED" | "COMPLETED",
    "timestamp": "2026-05-23T12:00:00Z"
  }
}
```

**Backend Publishing** (via EventBus):
```python
EventBus.publish(ScoreCalculated(
    session_id=...,
    archer_id=...,
    zones=[...],
    ...
))
# → EventBus routes to WebSocketService
# → WebSocketService broadcasts to all clients
```

**Frontend Listening** (via useWebSocket hook):
```typescript
const { data } = useWebSocket('/ws');
// data = { type, data: {...} }
// store.updateScores(data) if type === 'score_calculated'
```

**Contract Principles**:
- Backend defines event types and schema
- Frontend consumes exactly as defined
- Event schema is immutable (versioning if changes needed)
- Frontend handles missing or malformed events gracefully

---

### 3. Authentication & Authorization Integration

**Backend Provides**:
- JWT token generation upon login
- Token validation on every request
- Role-based access control
- HttpOnly cookie with token

**Frontend Consumes**:
- Displays login form
- Sends credentials to Backend
- Stores token (in httpOnly cookie, set by Backend)
- Passes token in Authorization header (for certain requests)
- Stores user info in Zustand (from decoded JWT)
- Shows/hides UI based on user roles

**Auth Flow**:
```
1. Frontend: User enters credentials in login form
2. Frontend: POST /api/v1/auth/login {username, password}
3. Backend: Validates credentials
4. Backend: Generates JWT (8-hour expiration)
5. Backend: Sets httpOnly cookie "access_token=<jwt>"
6. Backend: Returns {access_token, expires_in}
7. Frontend: Stores token in Zustand (for UI logic)
8. Frontend: Browser auto-attaches httpOnly cookie on subsequent requests
9. Frontend: Redirects to dashboard
10. Backend: Middleware validates token from cookie
11. Subsequent requests: Automatic (no token passing needed in most cases)
12. Token expired: Frontend calls POST /api/v1/auth/refresh
13. Backend: Issues new token, updates cookie
14. Frontend: Continues operation
```

**Contract Principles**:
- Token format: JWT (Backend generates, Frontend doesn't parse for logic)
- Token scope: Includes user ID, roles
- Token expiration: 8 hours
- Refresh endpoint: Available to extend session
- Logout: POST /api/v1/auth/logout (clears cookie)

---

### 4. Data Type Integration

**Backend Type System** (Pydantic models → JSON):
```python
class ScoreResponse(BaseModel):
    id: str
    archer_id: str
    zones: List[int]
    total_score: int
    confidence: float
    timestamp: datetime
```

**Frontend Type System** (TypeScript):
```typescript
interface ScoreResponse {
  id: string;
  archer_id: string;
  zones: number[];
  total_score: number;
  confidence: number;
  timestamp: string;  // ISO 8601
}
```

**Type Synchronization**:
- Backend defines schema (Pydantic)
- Frontend mirrors in TypeScript (manual translation)
- No code generation (both define independently)
- Zod validation on Frontend (validates Backend responses)

**Contract Principles**:
- Types are independent (Q8 answer: A)
- Backend is source of truth for API contracts
- Frontend validates all Backend responses (defensive programming)
- Type mismatches cause runtime validation errors (caught by Zod)

---

### 5. Shared Resources

#### PostgreSQL Database
- **Owner**: Backend (schema design, migrations, writes)
- **Usage**: Backend writes all data; Frontend reads via API only
- **Access**: Frontend has NO direct database access
- **Migrations**: Backend manages via Alembic
- **Schema Changes**: Backend deploys migrations; Frontend unaffected

#### File Storage (`/storage/`)
- **Owner**: Backend (reads/writes camera images)
- **Usage**: Backend captures images; Frontend receives via API
- **Organization**: `/storage/raw/` (originals), `/storage/annotated/` (marked)
- **Access**: Frontend can request images via API endpoint
- **Cleanup**: Backend manages retention policy

#### Configuration (`/config/`)
- **Owner**: Backend (environment variables, settings)
- **Usage**: Frontend configures via environment variables
- **Shared**: Base API URL, WebSocket URL
- **Frontend Config**: Vite environment (VITE_API_URL, VITE_WS_URL)

---

### 6. Development & Testing Coordination

#### Shared Test Database
- **Setup**: Same PostgreSQL instance for both teams (local development)
- **Initialization**: Seed data for integration tests
- **Cleanup**: Each test clears data (transactions rolled back)
- **Schema**: Backend migrations create schema on startup

#### API Contract Testing
- **Backend**: Unit tests verify endpoint responses match Pydantic schemas
- **Frontend**: Integration tests verify client handles expected responses
- **Compatibility**: Both teams test against same API contract

#### Integration Tests
- **Trigger**: After both units complete their stories
- **Scope**: End-to-end user flows (login → scoring → report)
- **Coordination**: Frontend and Backend agents verify scenarios work together

---

## Dependency Management

### Backend Dependencies (Python)
```
FastAPI 0.110+
Uvicorn 0.24+
SQLAlchemy 2.0+
psycopg2-binary 2.9+
pydantic 2.0+
python-jose 3.3+
passlib 1.7+
bcrypt 4.0+
python-multipart 0.0.6+
opencv-python 4.8+
numpy 1.24+
scipy 1.10+
WeasyPrint 59.0+
PyYAML 6.0+
structlog 23.1+
aiofiles 23.1+
python-dotenv 1.0+
pytest 7.2+
pytest-asyncio 0.21+
httpx 0.24+
```

All locked via `poetry.lock` (Poetry ensures reproducible builds)

### Frontend Dependencies (npm)
```
react 18+
react-dom 18+
typescript 5+
vite 5+
axios 1.6+
zustand 4.4+
react-router-dom 6+
react-hook-form 7+
zod 3.22+
recharts 2.10+
tailwindcss 3+
shadcn/ui (via cli)
lucide-react 0.263+
pytest (vitest) 1+
```

All pinned in `package-lock.json` (npm ensures reproducible installs)

---

## Deployment Coordination

### Build & Deploy Process

**Backend Deploy**:
1. Backend agent creates Docker image (Python 3.11-slim base)
2. Image tagged with version (e.g., `backend:1.0.0`)
3. Image pushed to registry (if needed)
4. Deployed via Docker Compose or orchestrator
5. Database migrations run automatically on startup
6. API available at `http://backend:8000`
7. WebSocket available at `ws://backend:8000/ws`

**Frontend Deploy**:
1. Frontend agent builds React app (Vite production build)
2. Output: Static assets (`dist/`)
3. Nginx serves static files (single-page app routing)
4. Frontend asks Backend for API URL (from env)
5. Nginx reverse proxy routes `/api` → Backend
6. Deployed via Docker Compose or orchestrator
7. Frontend available at `http://frontend:80`

**Independent Deployments**:
- Backend version 1.1 can run with Frontend version 1.0 (API compatibility)
- Frontend version 1.1 can run with Backend version 1.0 (API consumption only)
- No strict versioning dependency
- Breaking changes require negotiation and coordinated deployment

---

## Communication & Sync Points

### Before Code Generation
- **Milestone**: After Unit Design complete
- **Sync**: API contract review
  - Backend agent presents API endpoints
  - Frontend agent verifies can consume endpoints
  - Both agree on request/response formats
  - Both agree on WebSocket event schema
  - Lock contract (no unilateral changes)

### During Code Generation
- **Frequency**: Async updates via comment in unit files
- **Format**: Agent updates docs with progress
- **Cadence**: Daily or per-story-completion
- **Trigger for Sync**: API changes, architectural issues, blockers

### After Code Generation
- **Milestone**: Before Build & Test phase
- **Sync**: Integration testing coordination
  - Backend agent: Confirms all endpoints working
  - Frontend agent: Confirms UI consuming endpoints correctly
  - Both: Verify WebSocket events flowing correctly
  - Both: Test end-to-end flows

### Before Production Deployment
- **Checkpoint**: Full integration test passing
- **Verification**: Both agents sign off on compatibility
- **Release**: Coordinated deployment (or independent if no changes)

---

## Conflict Resolution

### Scenario 1: API Schema Mismatch
**Problem**: Backend returns `snake_case` JSON; Frontend expects `camelCase`

**Resolution**:
1. Backend is authoritative (returns as-is)
2. Frontend uses Zod to validate and transform
3. Document in API contract
4. Future: Consider JSON serialization standard (FastAPI can output camelCase)

### Scenario 2: Missing API Endpoint
**Problem**: Frontend needs endpoint that Backend didn't implement

**Resolution**:
1. Frontend files issue in unit docs
2. Backend agent reviews and adds endpoint
3. If urgent: Frontend implements workaround (query existing endpoint differently)
4. Contract updated; Frontend implements final version

### Scenario 3: WebSocket Event Missed
**Problem**: Backend publishes event; Frontend didn't receive (network issue)

**Resolution**:
1. Frontend implements reconnection logic (exponential backoff)
2. Backend keeps recent events in buffer (for replay on reconnect)
3. Frontend may request state refresh from Backend (alternative: REST poll)

### Scenario 4: Performance Regression
**Problem**: Backend API suddenly slow; Frontend times out

**Resolution**:
1. Backend agent investigates query performance
2. Frontend agent increases timeout temporarily
3. Backend implements fix (indexing, caching, etc.)
4. Frontend removes temporary timeout
5. Document performance target in API contract

---

## Success Criteria for Integration

- ✅ All REST endpoints return correct responses
- ✅ All WebSocket events broadcast correctly
- ✅ Frontend correctly parses all Backend responses
- ✅ Frontend displays real-time updates from WebSocket
- ✅ Authentication flow works end-to-end
- ✅ Authorization enforced (Frontend can't access restricted endpoints)
- ✅ Error responses handled gracefully by Frontend
- ✅ Both units deploy independently without breaking API
- ✅ Load testing shows performance targets met
- ✅ Full user story scenarios working end-to-end

