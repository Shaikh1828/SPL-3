# Automated Archery Scoring System

Welcome to the **Automated Archery Scoring System**! This is a complete, full-stack application designed to manage archery tournaments, track live scores using AI-assisted camera feeds, and provide real-time leaderboards to archers and spectators.

## 🏗️ System Architecture

The project is divided into two main components: a high-performance **Python Backend** and a modern, responsive **React Frontend**.

### 1. Backend (FastAPI)
The backend provides a robust REST API and WebSocket server. It is responsible for all business logic, data persistence, session management, and real-time event broadcasting.

- **Framework**: FastAPI (Python 3.11+)
- **Database**: PostgreSQL (managed via SQLAlchemy ORM and Alembic migrations)
- **Caching & Pub/Sub**: Redis (used for high-performance leaderboard caching)
- **Authentication**: JWT (JSON Web Tokens) with Role-Based Access Control (RBAC)
- **Real-Time Engine**: Native WebSockets for live camera feeds and score streaming.
- **Reporting**: Generates PDF, CSV, and JSON tournament reports.

*The backend runs on `http://localhost:8000`.*

### 2. Frontend (React + Vite)
The frontend is a visually stunning Single Page Application (SPA) designed with a "Dark Archery" aesthetic, providing an intuitive interface for tournament administrators and scorers.

- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite 5 for lightning-fast HMR and optimized builds
- **Styling**: Tailwind CSS v4 + Radix UI Primitives (Glassmorphism design, custom animations)
- **State Management**: Zustand for global state (`authStore`, `sessionStore`, `cameraStore`)
- **Data Fetching**: Axios with automatic JWT token injection and interceptors
- **Real-Time Integration**: Custom React hooks (`useWebSocket`, `useCameraPreview`, `useScoreStream`) that tie directly into the FastAPI WebSocket endpoints.
- **Data Visualization**: Recharts for score distribution and progression analytics.

*The frontend runs on `http://localhost:5173`.*

---

## ✨ Key Features

- **Tournament & Session Management**: Create tournaments, define rounds (sessions), configure lane assignments, and register archers.
- **Live AI-Assisted Scoring**: Connect physical cameras (USB/RTSP) to specific lanes. The backend processes images to detect arrows and calculate scores, while the frontend displays live previews and targeting overlays.
- **Real-Time Leaderboards**: As soon as a score is recorded, the leaderboard is recalculated in Redis and broadcasted to all connected frontend clients via WebSockets.
- **Post-Session Analytics**: Comprehensive reporting dashboard featuring score tables, zone distribution charts, and PDF/CSV export capabilities.
- **System Health Monitoring**: Built-in endpoints to monitor Database, Redis, Storage, and Threadpool health directly from the frontend dashboard.

---

## 📂 Project Structure

```text
SPL-3/
├── frontend/                # React + TypeScript Web Application
│   ├── src/
│   │   ├── api/             # Axios API clients mapped to backend routes
│   │   ├── components/      # Reusable UI and Layout components
│   │   ├── hooks/           # Custom hooks (e.g., useWebSocket)
│   │   ├── pages/           # Application screens (Dashboard, Scoring, etc.)
│   │   ├── store/           # Zustand state management
│   │   └── types/           # TypeScript interfaces matching backend models
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.ts
│
├── src/                     # FastAPI Backend Application
│   ├── api/                 # REST & WebSocket route handlers
│   ├── models/              # SQLAlchemy database models
│   ├── services/            # Core business logic and database interactions
│   ├── core/                # AI processing pipelines and camera management
│   └── main.py              # Application entry point
│
├── alembic/                 # Database migration scripts
├── tests/                   # Backend test suite (pytest)
├── scripts/                 # Utility scripts (e.g., database seeding)
├── QUICK_START.md           # Setup instructions
└── docker-compose.yml       # Docker deployment configuration
```

---

## 🚀 Getting Started

If you are setting up this project on a brand new device, please refer to the **[QUICK_START.md](QUICK_START.md)** file for a comprehensive, step-by-step installation guide covering both the frontend and backend environments.

## 📖 Documentation

For deep technical details, please refer to the following specifications located in the project root:
- `API_SPECIFICATION.md`: Exhaustive details on all 26+ REST endpoints and WebSocket channels.
- `DATABASE_SCHEMA.md`: Table structures, relationships, and indexing strategies.
- `archery_webapp_spec.md`: Detailed frontend UI/UX requirements and architecture.
- `archery_scoring_system_spec.md`: Core system architecture and AI pipeline design.
