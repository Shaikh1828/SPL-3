# Backend Unit — NFR Requirements Specification

**Project**: Automated Archery Scoring System  
**Unit**: Backend  
**Date**: 2026-05-25  

---

## Overview

This document specifies all non-functional requirements (Performance, Security, Scalability, Reliability, Availability, Maintainability) that will drive the NFR Design and Infrastructure Design phases.

---

## Performance Requirements

### PR-001: Scoring End-to-End Latency

**Target**: < 1 second end-to-end (capture → preprocess → detect → calculate)

**Strictness**: Best-effort goal — optimize for < 1s, but acceptable if occasional results exceed 1-1.5s with degradation warning

**Breakdown** (from functional design):
- Image capture: 200ms
- Preprocessing: 300ms
- Ring detection: 200ms
- Arrow detection: 150ms
- Calculation: 50ms
- **Total**: 900ms target (allows 100ms buffer for I/O variance)

**Monitoring**: Track p50, p95, p99 latencies per scoring operation. Alert if p95 exceeds 1.2s consistently.

**Implementation**: 
- ThreadPool(max_workers=4) for multi-camera parallelism
- Row-level database locking (minimal lock hold time)
- In-memory caching for camera metadata
- Async image I/O where possible

---

### PR-002: API Response Time (Non-Scoring)

**Target**: < 500ms for most endpoints, endpoint-dependent

**Breakdown**:
- Login/Auth: < 200ms
- Camera list: < 100ms
- Session operations: < 200ms
- Report generation: < 30s (background job, user notified when ready)

**Exceptions**: 
- Report generation runs async (background task)
- Large reports may take longer; user polls for completion

---

### PR-003: Live Preview Performance

**Target**: Best-effort real-time, no specific fps target

**Behavior**:
- 5-15 fps acceptable
- Degrade gracefully if camera cannot sustain
- Preview is low-priority vs. scoring accuracy

**Implementation**: 
- Stream frames on-demand from camera
- Client controls refresh rate (not server-driven)

---

### PR-004: WebSocket Event Latency

**Target**: < 500ms for real-time event delivery

**Strictness**: Soft real-time — aim for responsive, but network variance acceptable

**Events Covered**:
- ScoreCalculated (new score available)
- CameraStatusChanged (camera connected/disconnected)
- SessionStateChanged (session started/completed)
- ArcherStatusChanged (archer scored/completed)

**Implementation**:
- EventBus publishes to WebSocket subscribers
- No queueing (fire-and-forget)
- Subscriber broadcasts to all connected clients

---

## Scalability Requirements

### SR-001: Concurrent Users per Session

**Design Target**: 4-6 concurrent users typical, scale to 10+ for spikes

**Roles**:
- 1 TOURNAMENT_ADMIN (session controller)
- 1-2 SCORERS (triggering scoring)
- 2-5 SPECTATORS/ARCHERS (viewing live updates)

**Implementation**:
- Database connection pool: 10 connections + 5 overflow (sufficient for 10+ users)
- API server threads: auto-scaled based on framework (FastAPI/Uvicorn)
- WebSocket: broadcast to all subscribers

---

### SR-002: Concurrent Cameras per Session

**Design Target**: Sequential user actions, but multiple cameras score in parallel via ThreadPool

**Model**:
- SCORER triggers camera lane N
- ThreadPool internally parallelizes processing for multi-lane setup
- Caller waits for ThreadPool completion (synchronous)
- Each camera's result independent

**Implementation**:
- ThreadPool(max_workers=4) for up to 4 concurrent images
- Row locks on Session table (serializes updates)
- Fail fast if ThreadPool oversubscribed (unlikely in 4-6 user scenario)

---

### SR-003: Concurrent Sessions

**Design Target**: 2-3 sessions typical (small regional events)

**Behavior**:
- System supports multiple tournaments running in parallel
- Each session isolated (separate database transactions)
- Shared infrastructure (database, file storage)

**Implementation**:
- Database: PostgreSQL handles multi-session isolation (row-level locking)
- Storage: `/storage/raw/session_{id}/` namespacing

---

### SR-004: Data Volume & Storage Quota

**Design Target**: Archive/delete after 90 days (stay within 10 GB quota)

**Calculation**:
- ~1-5 MB per score (raw + annotated JPEG images)
- ~300-600 scores per session (3 arrows per archer × 100-200 archers)
- ~300-3000 MB per session

**Quota Management**:
- Hard limit: 10 GB
- Warning threshold: 80% (8 GB)
- Cleanup strategy:
  - Archive to tar.gz after 90 days (compress)
  - Delete archived files if quota exceeded
  - Admin alerts when approaching limit

---

## Security Requirements

### SEC-001: Security Baseline Rules (MANDATORY)

**Constraint**: ALL 11 Security Baseline rules are MANDATORY — non-compliance blocks deployment

**Rules**:
1. Input validation (all user inputs sanitized)
2. Authentication (JWT tokens, httpOnly cookies)
3. Authorization (4-role RBAC + hybrid permissions)
4. Encryption (TLS in-transit, password hashing)
5. Audit logging (scoreoverrides, user actions)
6. Secure configuration (secrets in environment variables)
7. Error handling (no sensitive data in error messages)
8. API security (rate limiting, CORS validation)
9. Data protection (sensitive field encryption)
10. Dependency security (regularly updated libraries)
11. Secure communication (HTTPS, secure WebSocket)

---

### SEC-002: Encryption Scope

**In-Transit**: TLS 1.2+ for all HTTP/WebSocket connections (HTTPS, wss://)

**At-Rest**:
- Passwords: bcrypt hashing (salted, no plaintext storage)
- API tokens: Stored securely (not logged)
- Database: Default PostgreSQL encryption (no full-disk encryption required)
- Images: Stored plaintext (low sensitivity, access controlled)

---

### SEC-003: Authentication & Tokens

**Model**: JWT tokens, user-scoped, 8-hour expiration

**Implementation**:
- Token claims: user_id, role, issued_at, expires_at
- Transport: httpOnly cookie (secure, sameSite=strict) + response body
- Refresh: POST /auth/refresh extends expiration
- Hardening: As-is (no additional measures like rotation or binding)

---

### SEC-004: Audit Logging

**Scope**: Scoring, camera, and session actions

**Logged Events**:
- User login/logout
- Score triggered, calculated, overridden (with reason)
- Camera connected/disconnected/status changes
- Session created, started, completed
- Permission denied/denied requests

**Retention**: Same as data retention (90 days, then archive)

---

### SEC-005: Compliance

**Target**: Best-effort (general security practices, no specific compliance framework)

**Approach**:
- Follow OWASP Top 10 guidance
- Data protection: User access control (ARCHER only sees own scores)
- Encryption: HTTPS + password hashing
- Audit: Logging of sensitive operations

---

## Reliability Requirements

### REL-001: Error Recovery

**Scope**: Image processing + camera disconnect auto-reconnect

**Strategies**:
1. **Ring Detection Failure**:
   - Retry with adjusted Hough parameters
   - Fallback to Contour Analysis
   - User can override manually

2. **Arrow Detection Failure**:
   - Retry with adjusted parameters
   - User override if both methods fail

3. **Camera Disconnect**:
   - Log warning
   - Auto-retry reconnection (30s, 60s, 120s, 300s exponential backoff)
   - Publish CameraDisconnected event
   - User can manually reconnect

**No Recovery**:
- API errors, database errors → return 500, alert user
- Overload → accept slowdown (no active queue/rejection)

---

### REL-002: System Resilience Under Overload

**Target**: Auto-scale resources (phased approach)

**Short-Term** (single server):
- Accept scoring requests, process FIFO
- Risk: Scoring latency may exceed 1s during peaks
- Monitoring: Alert if latency degrades

**Long-Term** (if overload occurs):
- Transition to multiple servers
- Load balancer (nginx, HAProxy)
- Auto-scaling based on CPU/memory metrics

---

### REL-003: Database Failover

**Target**: Warm standby with automatic failover (streaming replication)

**Model**:
- Primary PostgreSQL instance (active)
- Standby instance with streaming replication (warm)
- Failover trigger: Primary becomes unreachable (automated via patroni/pgBouncer)
- RTO: < 5 minutes (automatic detection + failover)

---

## Availability Requirements

### AVL-001: Uptime SLA

**Target**: Best-effort (acceptable downtime during maintenance)

**Expectation**:
- ~99.0% uptime (acceptable ~7 hours downtime/year)
- Maintenance windows: scheduled, announced in advance
- No SLA penalties

---

### AVL-002: Disaster Recovery

**RTO**: < 1 day (time to restore operation)  
**RPO**: ~24 hours (acceptable data loss up to 1 day)

**Strategy**:
- Daily backups of PostgreSQL database (automated)
- Image storage: Local filesystem (no remote backup required for MVP)
- Recovery: Manual restore from backup + replay transaction logs
- Testing: Quarterly backup restore drills

---

## Maintainability Requirements

### MNT-001: Code Quality Standards

**Target**: Basic standards (PEP 8, type hints, docstrings)

**Enforcement**:
- Linting: pylint/flake8 (warnings, not blocking)
- Type hints: Encouraged for complex functions
- Docstrings: Required for public methods
- Code reviews: GitHub pull requests

---

### MNT-002: Testing

**Target**: Unit tests + integration tests, 60-70% code coverage

**Scope**:
- Unit tests: Image processing algorithms, business logic, database operations
- Integration tests: API endpoints, database interactions, event publishing
- No e2e or load testing in initial release

**Coverage**: Aim for 60-70% line coverage (acceptable, not 100%)

---

### MNT-003: Documentation

**Target**: Comprehensive (README + API docs + design docs + runbook)

**Artifacts**:
- README.md: Setup, running locally, deployment
- API docs: OpenAPI/Swagger auto-generated from FastAPI
- Design docs: Architecture decisions (stored in aidlc-docs/)
- Operations guide: How to monitor, scale, troubleshoot in production
- Troubleshooting guide: Common issues and solutions

---

## Tech Stack & Deployment

### TSD-001: Deployment Model

**Target**: Docker containers on single server initially, designed for multi-server later

**Architecture**:
- **Phase 1**: Single server with Docker containers
  - API server container (FastAPI + Uvicorn)
  - PostgreSQL container (database)
  - Shared volume: `/storage/` (images)
  - Network: Internal Docker network

- **Phase 2** (if scaling needed):
  - Multiple API server replicas
  - Load balancer (nginx)
  - Dedicated PostgreSQL server
  - NFS or distributed storage for images

---

### TSD-002: Monitoring & Observability

**Target**: Application metrics (API latency, error rates, scoring throughput)

**Metrics Tracked**:
- API latency (p50, p95, p99)
- Scoring throughput (scores/sec)
- Error rates (5xx errors)
- Database connection pool usage
- Camera status (connected/disconnected)
- Image storage quota usage
- WebSocket connection count

**Tools**:
- Application logging: structlog (structured JSON logs)
- Metrics: Prometheus-compatible format (can integrate with monitoring stack)
- Alerting: Configure thresholds (e.g., error rate > 5%, latency > 1.2s)

---

### TSD-003: CI/CD Pipeline

**Target**: Basic CI/CD (run tests on push, manual deploy approval)

**Pipeline**:
1. **Commit push**: Run linting, type checking, unit tests
2. **Pull Request**: Report coverage, require review approval
3. **Merge to main**: Automatically deploy to staging
4. **Manual promotion**: Ops team approves production deploy
5. **Monitoring**: Post-deploy health checks

---

### TSD-004: Load Balancing & Horizontal Scaling

**Target**: Single server initially, designed for multi-server deployment

**Current**:
- No load balancer (single API server)
- All requests go to single instance
- Docker containers all on same host

**Future** (if needed):
- nginx load balancer (round-robin across API replicas)
- Auto-scaling triggers: CPU > 80%, memory > 85%
- Kubernetes optional (may be overkill for this project)

---

## Property-Based Testing (MANDATORY)

**Constraint**: All 9 Property-Based Testing rules are MANDATORY

**Coverage Areas**:
1. Image processing pipeline (ring/arrow detection)
2. Scoring calculation (zone → points mapping)
3. Session state transitions
4. Permission checks (role-based access)
5. Database transactions (atomicity)
6. Concurrency (row locks, parallel scoring)
7. Error handling (retry logic)
8. Data validation (input bounds)
9. API endpoints (request/response contracts)

---

## Summary: 26 Requirements Across 7 Categories

| Category | Count | Key Requirements |
|---|---|---|
| **Performance** | 4 | < 1s scoring (best-effort), < 500ms API, best-effort preview, < 500ms WebSocket |
| **Scalability** | 4 | 4-6 concurrent users (10+ spikes), sequential user actions (parallel cameras), 2-3 sessions, archive after 90 days |
| **Security** | 5 | All 11 baseline rules mandatory, TLS + password hashing, JWT 8h, audit logging, best-effort compliance |
| **Reliability** | 3 | Auto-recovery (ring/arrow/camera), accept slowdown under load, warm standby DB failover |
| **Availability** | 2 | Best-effort uptime (~99%), RPO 24h RTO 1 day |
| **Maintainability** | 3 | Basic code standards, 60-70% coverage, comprehensive docs |
| **Tech Stack** | 3 | Docker (single → multi-server ready), metrics monitoring, basic CI/CD |
| **PBT** | 1 | All 9 PBT rules mandatory |

---

## Design Impact

**Architecture Changes from NFR Requirements**:
1. **Database Failover**: Adds streaming replication (standby server)
2. **Monitoring**: Adds structlog + metrics collection
3. **Docker**: Adds Dockerfile, docker-compose.yml, container orchestration
4. **CI/CD**: Adds GitHub Actions workflow, automated testing
5. **Encryption**: Already planned (TLS, bcrypt passwords)
6. **Audit Logging**: Design for audit trail in database
7. **Error Recovery**: Already specified in functional design (retry logic)
8. **Documentation**: Requires comprehensive API + design + ops docs

**No Major Architectural Changes**: All NFR decisions align with existing functional design.

