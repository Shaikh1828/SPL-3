# Frontend Modules & Components Reference — Automated Archery Scoring System (SPL-3)

**Lifecycle Stage**: Inception / Reverse Engineering  
**Standard**: AIDLC Process Guidelines (`inception/reverse-engineering.md`)  
**Package Scope**: `frontend/src/` (React 18, TypeScript, Vite, Tailwind CSS, Zustand)

---

## 1. Application Entrypoint & Client Routing

### 1.1 `main.tsx`
- **Purpose**: Application root bootstrapper.
- **Implementation**:
  - Imports global CSS styles (`./index.css`).
  - Calls `ReactDOM.createRoot(document.getElementById('root')!)`.
  - Wraps root in `<React.StrictMode><App /></React.StrictMode>`.

### 1.2 `App.tsx`
- **Purpose**: Defines declarative client-side routes and route guards using `react-router-dom`.
- **Route Definitions**:
  - `/login`: Public route serving `LoginPage`.
  - `/register`: Public route serving `RegisterPage`.
  - Protected Shell Routes wrapped in `<Layout />`:
    - `/` $\to$ `DashboardPage`
    - `/tournaments` $\to$ `TournamentsPage`
    - `/scoring` $\to$ `ScoringPage`
    - `/cameras` $\to$ `CamerasPage`
    - `/reports` $\to$ `ReportsPage`
    - `/batch-testing` $\to$ `BatchTestingPage`
    - `/users` $\to$ `UsersPage` (Role gated to `admin`)
    - `/settings` $\to$ `SettingsPage`

---

## 2. Global State Stores (`frontend/src/store/`)

State management is powered by **Zustand**, providing atomic stores with zero-boilerplate hooks.

### 2.1 `authStore.ts`
- **State Interface**:
  - `token: string | null`: Current active JWT Bearer token.
  - `user: User | null`: Decoded user claims and profile.
- **Actions**:
  - `setToken(token: string | null)`: Updates token state and writes to `localStorage`.
  - `setUser(user: User | null)`: Updates user profile.
  - `login(token: string, user: User)`: Atomic login updating both token and user state.
  - `logout()`: Clears credentials and purges `localStorage`.

### 2.2 `sessionStore.ts`
- **State Interface**:
  - `activeSessionId: number | null`: Currently selected scoring session.
  - `activeTournamentId: number | null`: Active tournament ID.
- **Actions**:
  - `setActiveSessionId(id: number | null)`
  - `setActiveTournamentId(id: number | null)`

### 2.3 `cameraStore.ts`
- **State Interface**:
  - `selectedCameraId: number | null`: Selected camera for preview or calibration.
  - `activeStream: boolean`: Boolean flag indicating whether live stream is running.
- **Actions**:
  - `setSelectedCameraId(id: number | null)`
  - `setActiveStream(active: boolean)`

---

## 3. Custom React Hooks (`frontend/src/hooks/`)

### 3.1 `useWebSocket.ts`
- **Function**: `useWebSocket(options: UseWebSocketOptions)`
- **Parameters**:
  - `url: string`: Target WebSocket endpoint (resolved via `getWebSocketUrl`).
  - `onMessage?: (event: MessageEvent) => void`: Inbound frame handler.
  - `onOpen?: () => void`, `onClose?: () => void`, `onError?: (event: Event) => void`
  - `enabled?: boolean` (default `true`)
- **Behavior**:
  - Injects JWT token into connection URL (`?token=...` or `&token=...`).
  - Automatically reconnects after 3,000ms upon unexpected disconnect.
  - Returns `{ send: (data) => void, ws: React.RefObject<WebSocket | null> }`.

### 3.2 `useScoreStream.ts`
- **Function**: `useScoreStream(sessionId: number | null)`
- **Purpose**: Subscribes to live session scoring channel (`/api/ws/{session_id}`).
- **Behavior**: Parses incoming text frames as `WSEvent` JSON and returns `{ lastEvent: WSEvent | null }`.

### 3.3 `useCameraPreview.ts`
- **Function**: `useCameraPreview(cameraId: number | null, imgRef: React.RefObject<HTMLImageElement | null>)`
- **Purpose**: Subscribes to `/api/ws/camera/{cameraId}/preview` for live video frames.
- **Behavior**: Receives binary Blob frames, creates temporary object URLs via `URL.createObjectURL(blob)`, updates the `imgRef.current.src` attribute, and revokes previous object URLs to prevent browser memory leaks.

---

## 4. API Client Modules (`frontend/src/api/`)

### 4.1 `client.ts`
- **Singleton**: `apiClient = axios.create({ baseURL: '/api', timeout: 30000 })`
- **Interceptors**:
  - **Request**: Injects `Authorization: Bearer ${token}` from `authStore`.
  - **Response**: Intercepts `401 Unauthorized` responses, invokes `authStore.getState().logout()`, and redirects the browser to `/login`.

### 4.2 Endpoint Clients
- **`auth.ts`**:
  - `loginApi(credentials) -> Promise<LoginResponse>`
  - `registerApi(data) -> Promise<User>`
  - `getMeApi() -> Promise<User>`
- **`tournaments.ts`**:
  - `getTournamentsApi() -> Promise<Tournament[]>`
  - `createTournamentApi(data) -> Promise<Tournament>`
- **`sessions.ts`**:
  - `getSessionsApi(tournamentId) -> Promise<Session[]>`
  - `createSessionApi(data) -> Promise<Session>`
  - `startSessionApi(sessionId) -> Promise<Session>`
  - `completeSessionApi(sessionId) -> Promise<Session>`
  - `getSessionLeaderboardApi(sessionId) -> Promise<LeaderboardEntry[]>`
- **`scores.ts`**:
  - `detectArrowsApi(formData) -> Promise<DetectionResponse>`: Ingests multipart image files.
  - `recordScoreApi(data) -> Promise<Score>`
  - `updateScoreApi(scoreId, data) -> Promise<Score>`
  - `getSessionScoresApi(sessionId) -> Promise<Score[]>`
- **`cameras.ts`**:
  - `getCamerasApi() -> Promise<Camera[]>`
  - `createCameraApi(data) -> Promise<Camera>`
  - `testCameraApi(cameraId) -> Promise<{ connected: boolean; message: string }>`
  - `assignCameraLaneApi(cameraId, data) -> Promise<CameraLaneAssignment>`
- **`users.ts`**:
  - `getUsersApi() -> Promise<User[]>`
  - `updateUserRoleApi(userId, role) -> Promise<User>`
  - `toggleUserStatusApi(userId) -> Promise<User>`
- **`health.ts`**:
  - `getHealthApi() -> Promise<HealthResponse>`

---

## 5. Application Pages (`frontend/src/pages/`)

### 5.1 `ScoringPage.tsx`
- **Primary Business Page**: The core match scoring interface for scorers and archers.
- **Key Features**:
  - **Live Target Face Canvas**: SVG/Canvas rendering World Archery 10-ring concentric colored rings (Gold, Red, Blue, Black, White).
  - **Arrow Plotting**: Renders color-coded arrow impact dots with subpixel accuracy.
  - **Score Entry Controls**: Allows direct manual button input (`10`, `9`, ..., `M`, `X`) or auto-capture trigger from lane cameras.
  - **Running End Grid**: Shows running end totals, arrows shot, and end-by-end progress.

### 5.2 `BatchTestingPage.tsx`
- **Computer Vision Benchmark Page**: Dedicated diagnostic interface for testing algorithms against batches of test photos.
- **Key Features**:
  - Multi-file image drag-and-drop uploader.
  - Side-by-side comparison of detection methods (`yolo_subpixel`, `puncture_hole`, `line_intersection`, `color_segment`).
  - Displays detected target center coordinates, radii, bounding boxes, and arrow score confidence.

### 5.3 `DashboardPage.tsx`
- Displays active tournament statistics, number of active sessions, total arrows recorded, and live running leaderboard widget.

### 5.4 `TournamentsPage.tsx`
- Tournament management interface: creates new tournaments, configures shooting formats (indoor 18m, outdoor 70m), and launches sessions.

### 5.5 `CamerasPage.tsx`
- Hardware configuration console: registers RTSP and USB cameras, initiates connection tests, and previews live video feeds.

### 5.6 `ReportsPage.tsx`
- Analytics and export hub: renders score distribution charts via `recharts` and generates download links for certified PDF match scorecards and CSV logs.

### 5.7 `UsersPage.tsx`
- User governance page (Admin restricted): displays user lists, alters roles (`admin`, `scorer`, `spectator`, `archer`), and toggles account activation status.

---

## 6. Shared Components & Layouts (`frontend/src/components/`)

- **`Layout.tsx`**: Base template containing the navigation sidebar and top app header.
- **`Sidebar.tsx`**: Collapsible navigation bar with role-based link filtering (e.g. hides user administration from non-admins).
- **`TopBar.tsx`**: Top header displaying active tournament name, user avatar, role badge, and logout trigger.
- **`ScoreDetailsModal.tsx`**: Modal dialog showing diagnostic metadata for a specific arrow (exact coordinates, ring number, confidence percentage, and cropped arrow-tip preview).
- **`AuthenticatedImage.tsx`**: Image component fetching protected image blobs from `/api/scores/images/*` by injecting JWT bearer headers.

---

## 7. Utilities & Types

- **`frontend/src/utils/ws.ts`**:
  - `getWebSocketUrl(path: string) -> string`: Dynamic WebSocket resolver supporting Docker Nginx proxy, Vite dev proxy, and custom host configurations.
- **`frontend/src/lib/utils.ts`**:
  - `cn(...inputs: ClassValue[]) -> string`: Merges Tailwind CSS utility classes with `clsx` and `tailwind-merge`.
- **`frontend/src/types/index.ts`**:
  - TypeScript interface definitions: `User`, `Tournament`, `Session`, `SessionArcher`, `Score`, `Camera`, `DetectionResult`, `WSEvent`, `LeaderboardEntry`, `HealthResponse`.
