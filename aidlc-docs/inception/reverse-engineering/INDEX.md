# Reverse Engineering Master Documentation Suite (AIDLC)

**System**: Automated Archery Scoring System (SPL-3)  
**Lifecycle Stage**: Inception / Reverse Engineering (Brownfield Analysis)  
**Generated Date**: 2026-10-02  
**Target Coverage**: Full System (Backend, Frontend, ML/CV Pipeline, Database, Orchestration)

---

## 🧭 Documentation Navigator

This documentation suite reverse-engineers the entire codebase into structured AIDLC architectural and code-level specifications. Every module, class, method, function, API route, and state store is catalogued.

| Document | Purpose | Key Artifacts & Coverage |
|---|---|---|
| 📋 **[Business Overview](business-overview.md)** | Core domain model & transactions | World Archery 10-ring scoring rules, user personas, tournament lifecycle, business glossary |
| 🏛️ **[Architecture](architecture.md)** | System topology & interactions | Container network, service boundaries, WebSocket pub/sub flow, database ERD |
| 📁 **[Code Structure](code-structure.md)** | Directory hierarchy & patterns | Module layouts, build systems, design patterns (Repository, Factory, EventBus, Observer) |
| 🔌 **[API Documentation](api-documentation.md)** | REST & WebSocket contract | 25+ REST endpoints, 2 WebSocket streaming channels, payload schemas, auth & status codes |
| 📦 **[Component Inventory](component-inventory.md)** | Package catalog & boundaries | Backend services, API routers, middleware, utilities, frontend pages, hooks, stores |
| 🛠️ **[Technology Stack](technology-stack.md)** | Languages, runtimes & libraries | Python 3.11+, FastAPI, PyTorch CPU, OpenCV 4.8, YOLO11, React 18, Vite, Nginx, PostgreSQL, Redis |
| 🔗 **[Dependencies](dependencies.md)** | Internal & external dependencies | Python package ecosystem, Node dependencies, inter-module call graph, licenses |
| 🔍 **[Code Quality Assessment](code-quality-assessment.md)** | Test coverage & technical debt | Pytest suite (57+ tests), TypeScript strictness, linting, error handling, optimization areas |
| 🐍 **[Backend Modules Reference](backend-modules-reference.md)** | Complete Python API Reference | **Every** backend module, class, method, function, parameter, return type, and docstring |
| ⚛️ **[Frontend Modules Reference](frontend-modules-reference.md)** | Complete React API Reference | **Every** frontend page, component, hook, Zustand store, Axios client, utility, and type |

---

## 🎯 Quick System Overview

```text
Automated Archery Scoring System
├── Web Client (React 18 + Vite + Tailwind CSS + Zustand) -> Port 3000 / 5173
│   ├── Interactive Live Scoring Canvas & Target Overlay
│   ├── Real-time Leaderboards & WebSocket Feeds
│   ├── Camera Setup, RTSP Stream & Lane Assignments
│   └── Batch Testing Suite for Computer Vision Validation
├── Reverse Proxy & Static Host (Nginx Alpine)
│   ├── SPA Route Handling (/tournaments, /cameras, /scoring)
│   └── Reverse Proxy (/api -> FastAPI:8000, /api/ws -> WebSockets)
├── Backend Application (FastAPI + Python 3.11) -> Port 8000
│   ├── AI/CV Engine: Hybrid YOLO11 + Multi-Method OpenCV (Hough, Ellipse, Puncture Hole)
│   ├── Real-Time EventBus & Redis Pub/Sub Broadcast
│   └── Multi-Worker ThreadPool for Non-Blocking Computer Vision Processing
└── Data & Caching Tier
    ├── PostgreSQL 15 (Relational DB for Users, Tournaments, Sessions, Scores, Cameras, Audits)
    └── Redis 7 (Caching, Leaderboard Sorted Sets, WebSocket Message Fan-Out)
```
