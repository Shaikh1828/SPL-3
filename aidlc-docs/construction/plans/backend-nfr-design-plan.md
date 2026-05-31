# Backend Unit — NFR Design Planning

**Project**: Automated Archery Scoring System  
**Unit**: Backend  
**Date**: 2026-05-25  

---

## NFR Design Assessment Plan

**Objective**: Incorporate NFR requirements into Backend design using patterns and logical components for Performance, Security, Scalability, Reliability, and Availability.

**Status**: PLANNING

---

## Context from NFR Requirements

The Backend NFR assessment has established:
- Performance: < 1s scoring (best-effort), < 500ms API, < 500ms WebSocket
- Scalability: 4-6 concurrent users (design for 10+), 2-3 concurrent sessions, sequential user actions (ThreadPool parallelizes)
- Security: All 11 baseline rules mandatory, TLS, password hashing, JWT, audit logging
- Reliability: Auto-recovery (ring/arrow, camera), warm standby DB failover, accept slowdown under load
- Availability: Best-effort uptime, RPO 24h RTO 1 day
- Tech Stack: Uvicorn, ThreadPool(4), PostgreSQL, structlog, native WebSocket, Patroni failover

**Questions**: How to translate these requirements into concrete design patterns and infrastructure components?

---

## Assessment Checkboxes

- [ ] Step 1: Analyze resilience patterns
- [ ] Step 2: Analyze scalability patterns
- [ ] Step 3: Analyze performance optimization patterns
- [ ] Step 4: Analyze security design patterns
- [ ] Step 5: Analyze logical components and infrastructure
- [ ] Step 6: Review all answers for ambiguities
- [ ] Step 7: Generate final NFR design artifacts
- [ ] Step 8: Present for approval

---

## Resilience Patterns Questions

### Q1: Database Connection Resilience

**Context**: PostgreSQL is critical to all operations. Connection pool can be exhausted or database can become unavailable.

**Question**: How should connection failures be handled?
- **A)** Fail fast (return 500 error immediately if connection unavailable)
- **B)** Retry with exponential backoff (retry up to 3 times, then fail)
- **C)** Queue request (wait for connection to become available, timeout after 30s)
- **D)** Circuit breaker pattern (stop attempting if failure rate exceeds threshold)
- **E)** Hybrid (retry immediately, switch to circuit breaker if repeated failures)

[Answer]: B

---

### Q2: Scoring Request Failure Recovery

**Context**: During scoring, multiple components interact (image capture, processing, database insert, event publish). Failure at any stage should be recoverable.

**Question**: If scoring fails mid-pipeline (e.g., database insert fails after image processing):
- **A)** Rollback entire transaction (undo image processing, no side effects)
- **B)** Partial success (log error, notify user, user can retry)
- **C)** Automatic retry (immediate retry, exponential backoff for second attempt)
- **D)** Manual intervention (fail, alert operator, wait for manual recovery)
- **E)** Log and continue (best-effort, move on even if partial failure)

[Answer]: C

---

### Q3: WebSocket Connection Resilience

**Context**: WebSocket connections may drop (network interruption, server restart, browser tab close).

**Question**: How should disconnected clients be handled?
- **A)** Remove immediately (client responsible for reconnecting)
- **B)** Wait before removing (grace period 30s, then remove)
- **C)** Store message queue (queue events while disconnected, deliver on reconnect)
- **D)** Persistent subscriptions (maintain subscription state, re-deliver missed events on reconnect)
- **E)** Best-effort broadcast (fire-and-forget, no guarantee of delivery)

[Answer]: B

---

### Q4: Image Processing Fallback Chain

**Context**: Ring detection can fail (no rings detected). Current design has Hough → Contour fallback → user override.

**Question**: Should arrow detection have similar fallback chain?
- **A)** No (single method, user override if fails)
- **B)** Yes (implement same 2-method fallback as ring detection)
- **C)** Yes, but add manual box selection (user can select bounding box if auto-detection fails)
- **D)** Yes, plus ML-based fallback (train ML model as 3rd fallback option)
- **E)** Depends on confidence (only fallback if confidence < 50%)

[Answer]: D

---

### Q5: Camera Reconnection Backoff

**Context**: Camera disconnects. Current design specifies exponential backoff (30s, 60s, 120s, 300s).

**Question**: Maximum retry attempts for camera reconnection?
- **A)** Unlimited (keep retrying indefinitely)
- **B)** Limited to 5 retries (then give up, require manual intervention)
- **C)** Time-limited (retry for 24 hours, then stop)
- **D)** Adaptive (retry based on success rate, back off if pattern persistent)
- **E)** No limit, but notify user after 3 failures (continue retrying, alert user)

[Answer]: B

---

## Scalability Patterns Questions

### Q6: Session Management Under Load

**Context**: System supports 2-3 concurrent sessions. As sessions grow, need to ensure isolation and prevent cross-session data leaks.

**Question**: How should sessions be isolated to prevent interference?
- **A)** By database schema (each session in separate schema)
- **B)** By database rows (session_id filtering, relying on application logic)
- **C)** By separate database instances (one DB per session, not practical)
- **D)** By row-level security (PostgreSQL RLS policies enforce isolation at database level)
- **E)** No explicit isolation (rely on application logic, assume users follow procedures)

[Answer]: B

---

### Q7: API Request Queueing Strategy

**Context**: If API receives requests faster than Uvicorn can process (e.g., many users triggering scoring simultaneously).

**Question**: How should request overload be handled?
- **A)** Accept all (increase processing latency, accept slowdown)
- **B)** Queue with timeout (queue up to 100 requests, reject if queue full)
- **C)** Rate limiting (limit scoring requests to N per second per user)
- **D)** Adaptive throttling (auto-scale based on server utilization)
- **E)** Fail fast (return 429 Too Many Requests immediately)

[Answer]: D

---

### Q8: Database Query Optimization Under Load

**Context**: As number of sessions and scores grow, queries may become slower.

**Question**: How should query performance be optimized?
- **A)** No optimization (assume queries fast enough)
- **B)** Indexes (create indexes on frequently queried columns)
- **C)** Caching (cache results in memory for hot queries)
- **D)** Query optimization (rewrite queries to be more efficient)
- **E)** All of above (indexes + caching + optimization)

[Answer]: E

---

### Q9: Storage Scaling Strategy

**Context**: System stores images in `/storage/raw/`, 10 GB quota. After 90 days, archive to tar.gz.

**Question**: If storage needs to scale beyond 10 GB:
- **A)** Expand quota (single server with more disk space)
- **B)** Distribute across servers (NFS mount or S3 for distributed storage)
- **C)** Compression (more aggressive JPEG compression, reduce image size)
- **D)** Tiered storage (hot: recent images on SSD, cold: archived on slower disk)
- **E)** Plan for cleanup (ensure 90-day rotation keeps quota under 10 GB)

[Answer]: E

---

### Q10: ThreadPool Scaling

**Context**: ThreadPool(max_workers=4) handles multi-lane scoring. As concurrency increases, need adaptive scaling.

**Question**: Should ThreadPool size be configurable or static?
- **A)** Static at 4 (locked, never changes)
- **B)** Configurable via environment variable (admin can adjust at startup)
- **C)** Adaptive (scale based on CPU usage, queue depth)
- **D)** Hybrid (start at 4, scale to max 8 if CPU > 80%)
- **E)** Not a concern (4 is sufficient for expected load)

[Answer]: D

---

## Performance Optimization Patterns Questions

### Q11: Caching Strategy

**Context**: API serves camera list, session details, leaderboard data. These change infrequently.

**Question**: How aggressively should caching be applied?
- **A)** No caching (always query database, simplest)
- **B)** HTTP caching (use Cache-Control headers, browser/CDN caches)
- **C)** Application-level caching (in-memory cache for hot data)
- **D)** Invalidation strategy (cache with time-to-live, invalidate on updates)
- **E)** Advanced caching (multi-tier: L1 in-memory, L2 Redis, L3 database)

[Answer]: C

---

### Q12: Image Processing Optimization

**Context**: Ring/arrow detection is CPU-bound (200ms each for typical image). Can be optimized.

**Question**: What optimization approach should be used?
- **A)** Current approach (no optimization, accept 400-350ms for detection)
- **B)** Algorithm optimization (faster Hough implementation, parameter tuning)
- **C)** Parallel processing (process multiple images in parallel via GPU)
- **D)** Image compression (smaller images before processing, trade quality for speed)
- **E)** Hybrid (optimize algorithm + use multi-core parallelism)

[Answer]: D

---

### Q13: API Response Caching

**Context**: Leaderboard queries are expensive (aggregate scores by archer, sort).

**Question**: How should leaderboard caching work?
- **A)** No cache (query on every request)
- **B)** Simple TTL cache (cache for 1 minute, then refresh)
- **C)** Invalidation-based cache (cache indefinitely, invalidate on score update)
- **D)** Incremental update (cache leaderboard, update only on new scores)
- **E)** Not needed (performance acceptable without caching)

[Answer]: B

---

### Q14: Database Connection Pool Tuning

**Context**: SQLAlchemy pool configured at pool_size=10, max_overflow=5.

**Question**: Should pool size be adjusted based on load?
- **A)** Fixed at current settings (10+5 sufficient for expected load)
- **B)** Increase slightly (20+5 to accommodate growth)
- **C)** Decrease (5+2, minimize connections if low traffic)
- **D)** Configurable (adjust via environment variable)
- **E)** Adaptive (scale based on active connections)

[Answer]: E

---

### Q15: WebSocket Message Batching

**Context**: Multiple scores calculated in rapid succession → multiple ScoreCalculated events broadcast.

**Question**: Should WebSocket messages be batched?
- **A)** No batching (send immediately, one message per event)
- **B)** Time-based batching (batch events within 100ms window)
- **C)** Count-based batching (batch up to 10 events, send if batch full)
- **D)** Hybrid (batch within 100ms or 10 events, whichever comes first)
- **E)** Not needed (fire-and-forget is acceptable)

[Answer]: D

---

## Security Design Patterns Questions

### Q16: Input Validation Approach

**Context**: All NFR requirements mandate input validation (Security Baseline Rule #1).

**Question**: How comprehensive should input validation be?
- **A)** Minimal (validate type and length only)
- **B)** Standard (type, length, format, SQL injection prevention)
- **C)** Strict (standard + business rule validation)
- **D)** Maximum (strict + allow-list approach, reject unknown inputs)
- **E)** Depends on endpoint (critical endpoints: strict, non-critical: minimal)

[Answer]: B

---

### Q17: Rate Limiting Enforcement

**Context**: Protect API from abuse (many requests from single user/IP).

**Question**: Should rate limiting be implemented?
- **A)** No (assume internal/trusted users)
- **B)** Per-user (e.g., 100 API requests per minute per user)
- **C)** Per-IP (e.g., 1000 requests per minute per IP)
- **D)** Per-endpoint (e.g., scoring: 10 per minute, leaderboard: 100 per minute)
- **E)** Not needed (expected load doesn't justify complexity)

[Answer]: C

---

### Q18: Audit Trail Storage

**Context**: Audit logging requirement: score overrides, camera status, session changes.

**Question**: Where should audit logs be stored?
- **A)** Database (same PostgreSQL, efficient queries)
- **B)** Separate audit database (isolation, can't be tampered with main DB)
- **C)** Immutable log (append-only file, no updates/deletes)
- **D)** Log aggregation system (ELK, Datadog, etc.)
- **E)** Multiple destinations (database + immutable file for compliance)

[Answer]: A

---

### Q19: Secret Management

**Context**: Database password, JWT secret key, API tokens need secure storage.

**Question**: How should secrets be managed?
- **A)** Environment variables (read from .env file, not checked into git)
- **B)** Configuration files (encrypted config file, separate from code)
- **C)** Secret manager (AWS Secrets Manager, HashiCorp Vault, etc.)
- **D)** Container secrets (Docker/K8s secret mounts)
- **E)** Hybrid (environment variables for development, secret manager for production)

[Answer]: A

---

### Q20: CORS & API Security Headers

**Context**: Frontend (different origin) needs to call Backend API.

**Question**: How should CORS and security headers be configured?
- **A)** Allow all origins (CORS: *)
- **B)** Whitelist origins (CORS: only specific frontend URL)
- **C)** Same-origin only (CORS: same domain)
- **D)** No CORS needed (same domain deployment)
- **E)** Security headers + strict CORS (whitelisted origins + HSTS + CSP headers)

[Answer]: A

---

## Logical Components & Infrastructure Questions

### Q21: Message Queue Implementation

**Context**: Asynchronous tasks (report generation, image cleanup, event broadcasting) could use message queue.

**Question**: Should Backend implement a message queue?
- **A)** No queue (use FastAPI BackgroundTasks for async work)
- **B)** Simple queue (in-memory queue using asyncio.Queue)
- **C)** Dedicated queue (Redis or RabbitMQ)
- **D)** Database-backed queue (use PostgreSQL LISTEN/NOTIFY)
- **E)** Not needed (all work synchronous, latency acceptable)

[Answer]: A

---

### Q22: Caching Infrastructure

**Context**: Leaderboard, session data, camera list are frequently read, infrequently updated.

**Question**: Should Backend use a caching layer?
- **A)** No cache (all data from database)
- **B)** In-memory cache (Python dict/LRU, single server)
- **C)** Distributed cache (Redis, shared across multiple servers)
- **D)** Hybrid (in-memory for single server, Redis for multi-server)
- **E)** Not needed (database queries fast enough)

[Answer]: C

---

### Q23: Circuit Breaker Pattern

**Context**: Backend calls camera API, fetches external resources. If external service down, prevent cascading failures.

**Question**: Should circuit breaker pattern be implemented?
- **A)** No (assume external services reliable)
- **B)** Simple timeout (set timeout, fail if exceeds)
- **C)** Circuit breaker (track failures, stop calling if failure rate high)
- **D)** Fallback + circuit breaker (circuit breaker + fallback behavior)
- **E)** Not applicable (no external service dependencies)

[Answer]: A

---

### Q24: API Gateway / Load Balancer

**Context**: Single server now, but might scale to multiple later.

**Question**: Should API Gateway be implemented?
- **A)** No (single server, direct access to API)
- **B)** Later (single server now, add when scaling)
- **C)** Now with nginx (prepare for scaling from beginning)
- **D)** Advanced gateway (API versioning, request transformation, etc.)
- **E)** Not needed (FastAPI server sufficient)

[Answer]: B

---

### Q25: Monitoring & Observability Components

**Context**: Need visibility into performance, errors, health.

**Question**: What monitoring components should be implemented?
- **A)** Logging only (structlog to stdout)
- **B)** Logging + health endpoint (GET /health returns status)
- **C)** Logging + metrics (structlog + Prometheus-compatible metrics)
- **D)** Full observability (logs + metrics + distributed tracing)
- **E)** Advanced monitoring (observability + alerting + dashboard)

[Answer]: B

---

### Q26: Storage Component Strategy

**Context**: Images stored in `/storage/raw/`, need reliable access and backup.

**Question**: How should storage be managed?
- **A)** Local filesystem (single server, backup via file sync)
- **B)** Network filesystem (NFS, shared across servers)
- **C)** Object storage (S3, cloud-native approach)
- **D)** Hybrid (local fast, NFS for backup)
- **E)** Current approach (local filesystem, sufficient)

[Answer]: B

---

## Summary

**Total Questions**: 26 across 5 categories

| Category | Count | Topics |
|---|---|---|
| **Resilience** | 5 | DB connection, scoring failure, WebSocket, fallback chains, camera reconnect |
| **Scalability** | 5 | Session isolation, request queueing, query optimization, storage scaling, ThreadPool scaling |
| **Performance** | 5 | Caching strategy, image optimization, API caching, connection pool tuning, message batching |
| **Security** | 5 | Input validation, rate limiting, audit trail, secret management, CORS |
| **Logical Components** | 6 | Message queue, caching, circuit breaker, API gateway, monitoring, storage strategy |

---

## Next Steps

1. Please complete all 26 [Answer]: tags with your responses
2. System will analyze answers for ambiguities and ask follow-up questions if needed
3. Once all answers are validated, generate final NFR Design artifacts
4. Present for approval with standard 2-option format

