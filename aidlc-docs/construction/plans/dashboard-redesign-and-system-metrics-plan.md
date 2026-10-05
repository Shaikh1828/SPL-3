# Plan: Dashboard Redesign & System Diagnostics Isolation (AIDLC)

**Lifecycle Stage**: Construction / Planning  
**Standard**: AIDLC Process Guidelines (`construction/plans/`)  
**Objective**: Transform Dashboard into an interactive, high-impact tournament command center and extract system health/storage into a dedicated diagnostics module.

---

## 1. Requirements & Intent Analysis

- **Interactive Metric Cards**:
  - Clicking **Tournaments**: Opens modal showing all tournaments with dates, status, sessions, and shortcuts.
  - Clicking **Active Sessions**: Opens modal showing all active rounds with lane count, target sizes, and instant launch.
  - Clicking **Total Archers**: Opens modal showing archer roster with lane numbers, scores, and accuracy.
- **Relocation of Health & Storage**:
  - Remove System Health & Storage from the main Dashboard view.
  - Create a dedicated **System Status & Diagnostics** page/tab (`/system`) with real-time CPU, RAM, Disk Storage, AI Inference Engine (YOLO11), Database Pool, and Redis metrics.
- **Enhanced Championship-Grade Dashboard**:
  - Multi-session switcher directly on the dashboard.
  - Top 3 Podium presentation (Gold, Silver, Bronze badges) for live leaderboards.
  - Real-time WebSocket activity feed (recent arrow detections, ends completed).
  - Live Shooting Lane Matrix (visual lane-by-lane status).
  - Quick Action Command Bar.

---

## 2. Technical Architecture & Steps

```text
Step 1: Backend System Metrics API & Health Enrichment
  - Extend `HealthService` and `/api/health` with comprehensive CPU load, RAM usage, Disk Storage, ThreadPool, and AI engine status.
  - Add `/api/scores/recent` for live activity feed stream.

Step 2: Frontend Navigation & Route Setup
  - Add `/system` route in `App.tsx` and Navigation item in `Sidebar.tsx`.

Step 3: Build System Status Page (`frontend/src/pages/SystemStatusPage.tsx`)
  - Gauges & metrics for CPU, Memory, Storage, YOLO11 engine, Postgres, Redis.

Step 4: Build Interactive Modals
  - `TournamentsModal.tsx`: Enrolled tournaments view.
  - `SessionsModal.tsx`: Ongoing/active sessions view.
  - `ArchersModal.tsx`: Enrolled archers roster view.
  - `ArcherScorecardModal.tsx`: Individual archer end-by-end summary.

Step 5: Redesign Dashboard (`frontend/src/pages/DashboardPage.tsx`)
  - Interactive KPI cards with click triggers.
  - Top-3 Podium + Live Leaderboard with session selector.
  - Live Lane Grid Visualizer.
  - Real-time WebSocket Activity Feed.
  - Quick Action Hub.

Step 6: Build, Test & Docker Verification
  - Validate TypeScript compilation (`npm run build`).
  - Verify endpoints with Python test script.
  - Test UI in browser.
```
