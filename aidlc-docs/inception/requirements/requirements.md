# Comprehensive Requirements Document — Archery Scoring System

**Project**: Automated Archery Scoring System — Web Application  
**Date**: 2026-05-23  
**Requirements Depth**: Comprehensive  
**Phase**: INCEPTION — Requirements Analysis Complete  

---

## Executive Summary

The Archery Scoring System is a **production-grade full-stack web application** that automates target scoring for competitive archery events. The system integrates real-time camera streams, computer vision-based target analysis, and automated scoring with a comprehensive web-based interface for event management and reporting.

**Key Characteristics**:
- ✅ **Complete feature set** in first release (no MVP phasing)
- ✅ **Production-ready quality** with security and testing extensions enabled
- ✅ **Parallel independent development** — Backend and Frontend agents work on clearly-defined API contracts
- ✅ **2-4 week moderate timeline** with sustainable pace
- ✅ **Single-event scale** — 4-6 concurrent users, 4 cameras, 100-200+ records per session

---

## Section 1: Intent Analysis

### Request Type
**New Project** — Full-stack system development from detailed specification

### Scope
**System-wide** — Complete application with 6+ major backend modules, 5+ frontend pages, complex database schema

### Complexity
**Complex** — High-complexity system with real-time streams, computer vision, multi-camera coordination, statistical reporting

### Requirement Answers Summary
- **Development Scope**: Complete implementation (all features, all camera types, full CV suite)
- **Deployment**: Docker containerized for dev, with PostgreSQL production-ready
- **Team**: 2 developers (Senior Frontend, Senior Backend) with independent parallel tracks
- **Quality**: Standard testing coverage (60-70%), with Security and PBT extensions enabled
- **Timeline**: 2-4 weeks moderate pace

---

## Section 2: Functional Requirements

### 2.1 System Overview

The system operates on a **client-server model**:
- **Server**: Python/FastAPI backend running on machine with physically-attached USB/IP cameras
- **Client**: React browser-based UI accessible from any device on the LAN
- **Communication**: HTTP REST API + WebSocket for live streams

### 2.2 Core Features

#### Feature 1: Camera Management
**ID**: FR-CAM-001

| Requirement | Details |
|---|---|
| **Multi-Camera Support** | Support 4+ simultaneous cameras (USB, RTSP, HTTP MJPEG) |
| **Camera Enumeration** | Auto-discover USB cameras on startup |
| **Camera Configuration** | Per-camera settings: resolution, FPS, brightness, contrast, exposure, flip, zoom |
| **Live Preview Stream** | 15 fps MJPEG via WebSocket to browser |
| **Capture Modes** | Single frame OR burst (3-frame default) with sharpness selection |
| **Status Monitoring** | Real-time status: connected/disconnected/error with auto-reconnect every 30s |
| **Camera-to-Lane Binding** | Assign each camera to a specific archer/lane during session |

**Out of Scope**: IP camera authentication (assume network is pre-authenticated)

#### Feature 2: Image Capture & Processing
**ID**: FR-IMG-001

| Requirement | Details |
|---|---|
| **Capture Resolution** | Full resolution (1920×1080 typical, configurable) |
| **Preview Resolution** | 640×480 MJPEG stream |
| **Burst Mode** | Capture 3 frames, select sharpest (Laplacian variance metric) |
| **Preprocessing** | All 7 preprocessing methods applied conditionally based on lighting |
| **Perspective Correction** | Auto-detect board corners and apply homography transform |
| **Lighting Assessment** | Classify as DARK/BRIGHT/NORMAL/UNEVEN and apply adaptive corrections |

#### Feature 3: Image Processing Pipeline (Full CV Suite)
**ID**: FR-PROC-001

| Stage | Details |
|---|---|
| **Step 1: Preprocessing** | Resize, assess lighting, apply up to 7 correction methods (CLAHE, gamma, bilateral filter, etc.) |
| **Step 2: Circle Detection** | Hough Circle Transform (primary) + Ellipse fitting (fallback if <8 rings) |
| **Step 3: Arrow Detection** | Triple-method fusion: Canny+Hough, SIFT keypoints, Morphological segmentation + NMS |
| **Step 4: Scoring** | Euclidean distance mapping, zone assignment, confidence scoring |
| **Step 5: Output** | Generate annotated PNG with overlays, save to storage, insert DB records |
| **Performance** | < 1 second end-to-end processing (balanced optimization approach) |

#### Feature 4: Scoring Engine & Confidence Scoring
**ID**: FR-SCORE-001

| Requirement | Details |
|---|---|
| **Zone Mapping** | Euclidean distance to ring center → zone (10 rings + X ring = 11 zones) |
| **Confidence Algorithm** | Composite: detection method consensus + boundary distance margin |
| **Low-Confidence Flagging** | Flag scores with confidence < 0.60, suggest manual review |
| **Validation** | Full validation enabled: flag all low-confidence, boundary cases |
| **Override Capability** | Allow Scorer+ roles to override scores with reason + note logging |
| **X Ring Bonus** | Track X count separately for tiebreakers |

#### Feature 5: Session & Tournament Management
**ID**: FR-SESSION-001

| Requirement | Details |
|---|---|
| **Tournament Hierarchy** | Tournament → Sessions → Ends → Arrows |
| **Session Setup** | Define: name, distance, end count, arrows/end, target face size |
| **Archer Registration** | Register archers, assign to sessions |
| **Camera Assignment** | Assign cameras to archers/lanes during active session |
| **Session States** | pending → active → completed (transitions logged) |
| **Multi-End Support** | Track multiple ends, calculate running totals |
| **Score Recording** | Auto-save all scores with timestamp, camera_id, archer_id, end_number |

#### Feature 6: User Management & Role-Based Access Control (Full RBAC)
**ID**: FR-USER-001

| Role | Permissions |
|---|---|
| **SYSTEM_ADMIN** | All operations, user management, camera configuration, system settings |
| **TOURNAMENT_ADMIN** | Create/manage tournaments and sessions, register archers, view all data |
| **SCORER / OPERATOR** | Trigger scoring, assign cameras, override scores (logged), view reports |
| **ARCHER** | View own scores and history, download own reports |

**Authentication**: JWT-based with refresh tokens (28800s = 8 hour expiration)

#### Feature 7: Report Generation (All Formats)
**ID**: FR-REPORT-001

| Report Type | Formats | Contents |
|---|---|---|
| **End Report** | PNG (auto) | Annotated image + per-arrow scores + end total |
| **Session Report** | PDF, CSV, JSON | Score table, charts, statistics, override log |
| **Tournament Summary** | PDF, CSV, JSON | Rankings, per-archer breakdown, top performers |
| **Comparison Report** | PDF, CSV | Side-by-side comparison of 2+ archers |

#### Feature 8: Annotated Image Generation
**ID**: FR-ANNOTATE-001

Annotated PNG must include:
- Detected rings with zone colors and labels
- Ring center crosshair
- Arrow markers (green/yellow/red based on confidence)
- Per-arrow score and confidence labels
- End total and running total
- Timestamp, archer name, session info
- Warning banner if any confidence < 0.60

#### Feature 9: Frontend User Interface
**ID**: FR-UI-001

| Page | Purpose |
|---|---|
| **Dashboard** | Live session status, camera health, leaderboard, recent ends |
| **Scoring Page** | Primary operational screen: live preview, [Calculate] buttons, results, running totals |
| **Reports** | View/download session reports in multiple formats |
| **Camera Management** | Add/edit/remove cameras, test connections, assign to lanes |
| **User Management** | Create/edit users, assign roles (admin only) |
| **Settings** | System config, camera defaults, report templates |

**Responsive Design**: Works on desktop, tablet, read-only on mobile

#### Feature 10: API Specification
**ID**: FR-API-001

All endpoints require JWT authentication (except `/auth/login`).

**Key Endpoints**:
- `POST /auth/login` — User authentication
- `GET /cameras` — List all cameras with status
- `POST /score/calculate` — Trigger single camera scoring
- `POST /score/calculate-all` — Trigger all cameras simultaneously
- `PUT /score/{id}/override` — Override arrow score
- `GET /reports/session/{id}/{format}` — Generate report (PDF/CSV/JSON)
- `GET /images/{id}/annotated` — Serve annotated image
- Plus full CRUD for sessions, tournaments, archers, users

---

## Section 3: Non-Functional Requirements

### 3.1 Performance Requirements

| Target | Details |
|---|---|
| **Scoring Speed** | < 1 second end-to-end (capture → process → result) |
| **Live Preview** | 15 fps MJPEG stream via WebSocket |
| **API Response Time** | < 200ms for standard queries, < 2s for report generation |
| **Concurrent Users** | 4-6 simultaneous users without degradation |
| **Concurrent Cameras** | 4 simultaneous capture + processing |
| **Scaling Strategy** | Optimize iteratively; no horizontal scaling required for initial release |

**Performance Approach**: **Balanced** — Prioritize scoring speed, preview quality, and concurrent user support equally; optimize iteratively based on profiling

### 3.2 Scalability Requirements

| Dimension | Target |
|---|---|
| **Concurrent Users** | 4-6 (single-event scale) |
| **Concurrent Cameras** | 4+ |
| **Historical Records** | 100-200+ scores per session |
| **Storage Quota** | 10 GB default (auto-archive at 90%) |
| **Database Size** | Single PostgreSQL instance sufficient |

**Scaling Notes**: Design for single-server deployment; horizontal scaling can be added in future phases if needed

### 3.3 Reliability & Availability

| Requirement | Target |
|---|---|
| **Uptime** | 99.5% during event hours (single server) |
| **Data Durability** | All scores, images, and metadata persisted immediately (no in-memory-only state) |
| **Camera Reconnect** | Auto-reconnect every 30s if disconnected |
| **Error Recovery** | Graceful handling of transient camera disconnects; operator can retake scoring |
| **Audit Trail** | Complete immutable log of all scores, overrides, and state changes |

### 3.4 Security Requirements

**Requirement**: Security extension **ENABLED** — All security rules are MANDATORY blocking constraints.

Key Security Controls:

| Rule | Implementation |
|---|---|
| **SECURITY-01: Encryption at Rest/Transit** | PostgreSQL with TLS, all data encrypted at rest (PG native), HTTPS enforced (reverse proxy) |
| **SECURITY-02: Network Access Logging** | Nginx reverse proxy with access logs, FastAPI request logging |
| **SECURITY-03: Application Logging** | Structured logging (structlog) with timestamp, request ID, log level; centralized logging via logs/ directory (production: ELK/CloudWatch) |
| **SECURITY-04: HTTP Security Headers** | Set CSP, HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy on all HTML responses |
| **SECURITY-05: Input Validation** | Pydantic model validation on all endpoints, max-length constraints, SQL injection prevention via ORM |
| **SECURITY-06: Least-Privilege RBAC** | Fine-grained role-based permissions, no wildcard actions |
| **SECURITY-07: Network Hardening** | Deny-by-default firewall rules, private subnets for DB, public access only on port 80/443 |
| **SECURITY-08: Application AuthZ** | Deny-by-default endpoint authorization, object-level access checks (user can only see own data), CORS restricted to trusted origins |
| **SECURITY-09: Hardening** | No default credentials, minimal base images, error responses don't leak internals, cloud storage blocking enabled |
| **SECURITY-10: Supply Chain** | Poetry lock file, dependency vulnerability scanning (bandit), no unpinned `latest` tags in Docker, SBOM generation for prod |
| **SECURITY-11: Secure Design** | Auth/AuthZ isolated in dedicated middleware, separation of concerns enforced |

### 3.5 Data Storage & Retention

| Resource | Retention | Location |
|---|---|---|
| **Raw Images** | 90 days (configurable) | `storage/raw/YYYY/MM/DD/{session_id}/` |
| **Annotated Images** | Indefinite | `storage/annotated/YYYY/MM/DD/{session_id}/` |
| **Thumbnails** | Indefinite | `storage/thumbnails/` |
| **Export Files (PDF/CSV/JSON)** | 30 days | `storage/exports/` |
| **Database Records** | Indefinite | PostgreSQL (with daily backups in prod) |
| **Storage Quota Management** | 10 GB default; warn at 80%; auto-archive at 90% | Monitored in system health |

### 3.6 Usability & Accessibility

| Requirement | Details |
|---|---|
| **Responsive Design** | Desktop (≥1280px), Tablet (768-1279px), Mobile (<768px, read-only) |
| **Accessibility** | WCAG 2.1 Level AA (keyboard navigation, screen reader support) |
| **Error Messages** | Clear, actionable error messages in toast notifications |
| **Visual Feedback** | Green/yellow/red status indicators, animated buttons during processing |
| **Offline Support** | None required (LAN-based system, always-on network assumed) |

---

## Section 4: Technical Architecture

### 4.1 Technology Stack (Locked)

**Backend**:
- **Language**: Python 3.11+
- **Framework**: FastAPI 0.110+
- **ASGI Server**: Uvicorn
- **Image Processing**: OpenCV 4.8+, NumPy, SciPy
- **Database ORM**: SQLAlchemy 2.0+
- **Database (dev)**: SQLite 3.x
- **Database (prod)**: PostgreSQL 15+
- **Task Queue**: FastAPI BackgroundTasks (simple) — NOT Celery
- **Auth**: python-jose + passlib + bcrypt
- **PDF**: WeasyPrint
- **Config**: PyYAML
- **Logging**: structlog
- **Lock File**: Poetry

**Frontend**:
- **Framework**: React 18+
- **Language**: TypeScript 5+
- **Build Tool**: Vite 5+
- **State Management**: Zustand (NOT Redux)
- **Styling**: Tailwind CSS 3+
- **UI Components**: shadcn/ui
- **HTTP Client**: Axios
- **WebSocket**: Native browser WebSocket API
- **Charts**: Recharts
- **Forms**: React Hook Form + Zod
- **Router**: React Router v6

**Infrastructure**:
- **Containers**: Docker + Docker Compose
- **Reverse Proxy**: Nginx (production)
- **Storage**: Local filesystem served via authenticated API

### 4.2 Database Schema (PostgreSQL)

**Core Entities**:
- `users` — User accounts with roles
- `tournaments` — Tournament records
- `sessions` — Sessions within tournaments
- `archers` — Archer profiles
- `cameras` — Camera configurations and status
- `ends` — Individual ends (rounds)
- `scores` — Per-arrow scoring records
- `images` — Image metadata (raw, annotated, thumbnail paths)
- `override_logs` — Score override audit trail
- `reports` — Generated reports (metadata)

### 4.3 API Architecture

**Authentication**: JWT Bearer token (issued via `/auth/login`)

**Base URL**: `http://{host}:8000/api/v1`

**Response Format**: Standard JSON with status codes (200, 400, 401, 403, 404, 500)

**Error Format**:
```json
{
  "error_code": "IMG_001",
  "message": "Ring detection failed",
  "detail": "Only 6 rings detected (minimum 8 required)"
}
```

### 4.4 WebSocket Architecture

**Endpoint**: `ws://{host}/ws/camera/{camera_id}/preview`

**Message Type**: Binary JPEG frames at 15 fps

**Message Format**: JPEG bytes (variable size, ~50-100KB per frame)

---

## Section 5: Development Approach

### 5.1 Team Structure & Collaboration

| Role | Responsibility |
|---|---|
| **Senior Backend Developer** | Camera manager, image processing pipeline, scoring engine, database layer, REST API |
| **Senior Frontend Developer** | React UI, live preview, dashboard, reports viewer, WebSocket client integration |
| **Coordination** | Clear API contracts defined upfront; parallel independent tracks |

**Collaboration Model**: **Independent Tracks**
- Backend completes API specification and core endpoints first
- Frontend builds UI against finalized API contracts
- Weekly sync to validate assumptions

### 5.2 Development Phases

**Phase 1: Setup & Infrastructure** (Days 1-2)
- Docker environment setup
- Database schema creation
- Project scaffolding (backend + frontend)
- CI/CD pipeline (basic)

**Phase 2: Core Backend** (Days 3-8)
- Camera manager + capture system
- Image processing pipeline (all 5 methods)
- Scoring engine
- Session & user management
- REST API (full endpoints)

**Phase 3: Frontend UI** (Days 5-10, parallel with Phase 2)
- Dashboard page
- Scoring page with live preview
- Report viewer
- Camera management UI
- User management

**Phase 4: Integration & Testing** (Days 9-12)
- End-to-end integration testing
- Security validation
- Performance testing
- User acceptance testing

**Phase 5: Deployment & Documentation** (Days 13-14)
- Docker production build
- Deployment guide
- User documentation
- Operations runbook

### 5.3 Quality Standards

**Testing Coverage**: **Standard** (60-70%)
- Unit tests for all core business logic
- Integration tests for API + database
- E2E tests for critical user paths (login, scoring, reports)
- Scoring engine: comprehensive unit tests (highest priority)
- Image processing: unit tests per stage (critical for accuracy)

**Testing Extensions**:
- **Security Extension**: ENABLED — All 11 security rules are mandatory blocking constraints
- **Property-Based Testing**: ENABLED — All 9 PBT rules apply to applicable components

**Key PBT Areas**:
- Scoring algorithm (invariant properties: zone assignment consistency)
- Image preprocessing (round-trip properties if applicable)
- API input validation (oracle testing against constraints)
- State management on frontend (idempotency of actions)

### 5.4 Code Quality

- **Linting**: pylint (Python), ESLint (JavaScript)
- **Formatting**: Black (Python), Prettier (JavaScript)
- **Type Checking**: Pylance (Python), TypeScript compiler (JavaScript)
- **Dependency Scanning**: bandit (Python), npm audit (JavaScript)
- **Code Review**: Peer review before merge

### 5.5 Documentation

- **API Documentation**: OpenAPI/Swagger (auto-generated from FastAPI)
- **Architecture Documentation**: Design documents in `aidlc-docs/`
- **User Guide**: Step-by-step operational guide
- **Deployment Guide**: Docker Compose, environment setup
- **Database Schema**: ER diagram + migration guide

---

## Section 6: Success Criteria

### Functional Success
✅ All cameras (USB, RTSP, HTTP MJPEG) capture and stream simultaneously  
✅ Scoring completes in < 1 second with annotated image feedback  
✅ Multi-user concurrent operations work without conflicts  
✅ All 4 report formats (PDF, CSV, JSON, PNG) generate correctly  
✅ Full RBAC enforced (4 roles, appropriate permissions)  

### Non-Functional Success
✅ 15 fps live preview quality maintained  
✅ < 200ms API response times for standard operations  
✅ < 2s for complex queries (reports)  
✅ 4-6 concurrent users without UI lag  
✅ All security rules verified and enforced  

### Quality Success
✅ 60-70% code coverage achieved  
✅ All security findings resolved (zero blocking security findings)  
✅ PBT coverage complete for scoring engine and state management  
✅ Zero critical bugs in scoring algorithm  
✅ Full test automation in CI/CD  

### Deployment Success
✅ Docker containers build and run without errors  
✅ PostgreSQL migration scripts execute cleanly  
✅ Environment variables configured correctly  
✅ Production security hardening applied  

---

## Section 7: Constraints & Assumptions

### Constraints
1. **Single-server deployment** — No horizontal scaling required for initial release
2. **LAN-based access** — Frontend accessible only from devices on same network as backend
3. **USB/IP cameras only** — No RTMP or specialized broadcast protocols
4. **One operator per session** — Scoring button press is sequential (not concurrent)
5. **4 GB minimum RAM** for backend (burst processing + image buffers)

### Assumptions
1. Network is pre-authenticated (no additional auth for IP cameras)
2. Operator has adequate training for manual override decisions
3. Target board is always 10 white rings + X ring (standard WA archery)
4. Lighting conditions are generally well-lit (natural or arena lighting)
5. Backup system: manual scoring available if system fails (not automated fallback)

---

## Section 8: Out of Scope (Phase 2+)

- Advanced computer vision (360° multi-angle capture, 3D reconstruction)
- AI-based learning/model training for camera adaptation
- Horizontal scaling (multi-server, load balancing)
- Mobile app (native iOS/Android)
- Real-time leaderboard broadcast to multiple screens
- Automated backup to cloud storage
- Video recording of full sessions
- Advanced analytics/machine learning on scoring trends
- Integration with external tournament management systems

---

## Section 9: Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Image processing accuracy < 95% | Medium | High | Full CV suite + extensive testing, manual override capability |
| Camera disconnect during scoring | Medium | Medium | Auto-reconnect logic, retake capability |
| Database corruption | Low | Critical | Daily backups, transaction logs, data recovery procedures |
| Performance degradation with 4 cameras | Low | Medium | Profiling + optimization, resource limits |
| Security vulnerabilities | Low | Critical | Security extension enabled, OWASP top 10 coverage, penetration testing |

---

## Approval & Next Steps

This comprehensive requirements document incorporates:
✅ Complete functional features (full-featured first release)  
✅ Production-ready non-functional requirements  
✅ Security extension (all 11 rules mandatory)  
✅ Property-based testing extension (all 9 rules applicable)  
✅ Clear API contracts for parallel team development  
✅ Quality standards and testing strategy  

**Ready for workflow planning and code generation.**
