# Backend Unit — NFR Requirements Planning

**Project**: Automated Archery Scoring System  
**Unit**: Backend  
**Date**: 2026-05-24  

---

## NFR Requirements Assessment Plan

**Objective**: Clarify non-functional requirements (Performance, Security, Scalability, Reliability, Availability, Maintainability) to guide NFR Design and Infrastructure Design phases.

**Status**: PLANNING

---

## Context from Functional Design

The Backend functional design has established:
- Image processing pipeline: < 1 second end-to-end target
- Multi-camera concurrency: ThreadPool(max_workers=4)
- Database: PostgreSQL with row locks
- Real-time communication: WebSocket events
- Image storage: Filesystem (/storage/raw/, 90-day retention, 10 GB quota)
- Security: Role-based access control (4 roles) + hybrid permissions

**Questions**: While these decisions provide a strong foundation, several NFR dimensions need explicit clarification to guide infrastructure and operational design.

---

## Assessment Checkboxes

- [ ] Step 1: Analyze performance requirements
- [ ] Step 2: Analyze security and compliance requirements  
- [ ] Step 3: Analyze scalability and capacity requirements
- [ ] Step 4: Analyze availability and reliability requirements
- [ ] Step 5: Analyze tech stack and deployment requirements
- [ ] Step 6: Analyze monitoring, logging, and observability requirements
- [ ] Step 7: Review all answers and identify ambiguities
- [ ] Step 8: Generate final NFR artifacts
- [ ] Step 9: Present for approval

---

## Performance Requirements Questions

### Q1: Scoring Latency Requirements

**Context**: Functional design targets < 1 second for image capture → scoring result. This drives architecture decisions (ThreadPool concurrency, image processing approach, database transaction strategy).

**Question**: Is the < 1 second target:
- **A)** Hard requirement (must not exceed 1s, scoring unusable above 1s)
- **B)** Desired target (aim for < 1s, acceptable up to 1.5s with degradation warning)
- **C)** Best-effort (minimize latency, but no hard deadline)
- **D)** 95th percentile (95% of scores < 1s, 5% allowed above)
- **E)** Per-component (target different stages: capture 200ms, detect 350ms, calculate 50ms max)

[Answer]: C

---

### Q2: Preview/Live View Performance

**Context**: The system shows live camera feed before scoring. The functional design mentions 15 fps preview capability.

**Question**: What are the live preview requirements?
- **A)** 15 fps required at all times (hard target)
- **B)** 15 fps when possible, degrade to 10 fps if camera can't sustain
- **C)** Real-time / "best effort" (no specific fps target)
- **D)** Not a requirement (preview can be ~5 fps or delayed)
- **E)** Variable: show full 15 fps during setup, can drop to 5 fps during active scoring

[Answer]: D

---

### Q3: API Response Time Targets

**Context**: Frontend consumes REST API for non-scoring operations (login, camera list, session management, reports).

**Question**: What are acceptable API response times (excluding scoring)?
- **A)** < 100 ms (snappy, real-time feel)
- **B)** < 200 ms (responsive)
- **C)** < 500 ms (acceptable)
- **D)** < 1 second (standard web app)
- **E)** No specific target (depends on endpoint, report generation can be slower)

[Answer]: E

---

### Q4: Report Generation Performance

**Context**: System generates session reports (leaderboards, summary statistics) after scoring.

**Question**: Acceptable report generation latency?
- **A)** < 1 second (immediate)
- **B)** < 5 seconds (acceptable)
- **C)** < 30 seconds (long-running background task)
- **D)** Async background job (no latency requirement, user notified when ready)
- **E)** No target (can be deferred indefinitely)

[Answer]: D

---

### Q5: WebSocket Event Delivery Latency

**Context**: Real-time events (score calculated, camera status changed) broadcast via WebSocket to connected clients.

**Question**: Maximum acceptable latency for WebSocket events?
- **A)** < 50 ms (very low latency, critical for user experience)
- **B)** < 100 ms (< 100ms as mentioned in requirements)
- **C)** < 500 ms (soft real-time)
- **D)** < 1 second (near real-time)
- **E)** No specific target (fire-and-forget)

[Answer]: E

---

## Scalability Requirements Questions

### Q6: Concurrent Users per Session

**Context**: Functional design mentions 4-6 concurrent users as expected load. This affects database connection pool, API server threads, and WebSocket server capacity.

**Question**: Peak concurrent users in a single session?
- **A)** 4 users (lock to this — no scaling needed)
- **B)** 4-6 users typical, but design for 10+ to handle spikes
- **C)** 6-10 users expected, design for 20+ (2-3x buffer)
- **D)** Unbounded (should handle 50+ users per session)
- **E)** No specific limit (auto-scale based on demand)

[Answer]: B

---

### Q7: Concurrent Cameras per Session

**Context**: Functional design uses ThreadPool(max_workers=4). Is this a hard limit or should we support more?

**Question**: Maximum concurrent cameras per session?
- **A)** 4 cameras (hard limit, do not support more)
- **B)** 4 cameras typical, but design for 8+ to allow growth
- **C)** 8+ cameras (large tournaments with multiple lanes)
- **D)** Unbounded (support as many as hardware allows)
- **E)** Not a concern (sequential scoring one camera at a time)

[Answer]: E

---

### Q8: Concurrent Sessions

**Context**: Multiple tournaments/sessions can run in parallel.

**Question**: Expected concurrent sessions on single system?
- **A)** 1 session at a time (single-tournament mode)
- **B)** 2-3 sessions (small regional events)
- **C)** 10+ sessions (large system, multiple tournaments)
- **D)** Unbounded (should support many tournaments in parallel)
- **E)** Not a concern (sequential tournaments, one after another)

[Answer]: B

---

### Q9: Data Volume & Growth

**Context**: System stores images (~1-5 MB per score), scores, and metadata. 10 GB quota mentioned.

**Question**: Acceptable data growth over time?
- **A)** Archive/delete after 90 days (stay within 10 GB always)
- **B)** Archive to secondary storage after 90 days (primary stays within quota)
- **C)** Expand storage as needed (10 GB is starting point, can grow)
- **D)** No cleanup needed (assume unlimited storage available)
- **E)** Depends on tournament size (some tournaments purge, some archive)

[Answer]: A

---

## Security Requirements Questions

### Q10: Security Baseline Implementation

**Context**: The copilot-instructions.md specifies **11 mandatory Security Baseline rules** and **9 mandatory Property-Based Testing rules**. These are hard constraints.

**Question**: How strictly should security baselines be enforced?
- **A)** All 11 rules mandatory, blocking deployment if any violated
- **B)** All 11 rules mandatory, but can document exceptions with approval
- **C)** Core rules mandatory (encryption, auth), others best-effort
- **D)** Assess each rule for applicability (some may not apply)
- **E)** Other (please specify in [Answer])

[Answer]: C

---

### Q11: Encryption Requirements

**Context**: The system handles user credentials, session tokens, and potentially sensitive scoring data.

**Question**: Encryption scope?
- **A)** TLS in-transit only (HTTPS, secure WebSocket)
- **B)** TLS in-transit + encrypted storage for sensitive fields (passwords, tokens)
- **C)** TLS in-transit + full database encryption (all data encrypted at rest)
- **D)** TLS in-transit + encrypted images and full DB encryption (maximum security)
- **E)** No encryption (internal network, not exposed to internet)

[Answer]: B

---

### Q12: Authentication Token Hardening

**Context**: Functional design uses JWT tokens (8-hour expiration, user-scoped, httpOnly cookies).

**Question**: Additional token security measures?
- **A)** JWT as-is (8 hours, httpOnly cookies, sufficient)
- **B)** Add refresh token mechanism (short-lived access token + long-lived refresh token)
- **C)** Add token rotation (issue new token after each request)
- **D)** Add token binding (bind token to IP/device, prevent theft)
- **E)** Add multi-factor authentication (TOTP or email OTP before scoring)

[Answer]: A

---

### Q13: Audit Logging Depth

**Context**: System needs to track score overrides, user actions for compliance and debugging.

**Question**: Audit logging scope?
- **A)** Score overrides and permission-denied events only
- **B)** All scoring, camera, and session actions
- **C)** All user actions (logins, API calls, scoring, overrides)
- **D)** Full audit trail including request/response payloads
- **E)** No audit logging (log only errors)

[Answer]: B

---

### Q14: Compliance Requirements

**Context**: System stores personal data (user names, scores, competitive results).

**Question**: Compliance frameworks?
- **A)** None (internal system, no compliance required)
- **B)** GDPR (user data rights: access, delete, portability)
- **C)** HIPAA or similar (highly regulated, full audit, encryption, access controls)
- **D)** Custom compliance (document specific requirements)
- **E)** Best-effort (follow general security practices)

[Answer]: E

---

## Reliability & Error Handling Questions

### Q15: Error Recovery Strategy

**Context**: Functional design specifies ring detection retry with parameter adjustment, then fallback to contour analysis, then user override. Similar for arrow detection.

**Question**: Scope of auto-recovery?
- **A)** Image processing only (ring/arrow detection retries), other failures = user override
- **B)** Image processing + camera disconnect auto-reconnect (retry up to 3 times)
- **C)** All failures auto-retry with backoff (exponential backoff, max 5 retries)
- **D)** All failures auto-retry + auto-failover (switch camera if one fails)
- **E)** Minimal recovery (fail fast, user manually recovers)

[Answer]: B

---

### Q16: System Resilience Under Load

**Context**: If many sessions run concurrently or scoring is triggered rapidly, system might become overloaded.

**Question**: Behavior under overload?
- **A)** Queue scoring requests, process FIFO (built-in backpressure)
- **B)** Accept all scoring requests, risk slowdown if overloaded
- **C)** Reject new scoring requests once queue exceeds limit (fast fail)
- **D)** Auto-scale resources (spin up more workers/servers)
- **E)** No concern (never overloaded in practice)

[Answer]: D

---

### Q17: Database Failover

**Context**: PostgreSQL database is single point of failure.

**Question**: Database redundancy?
- **A)** Single database instance (no failover)
- **B)** Backup database with manual failover
- **C)** Warm standby with automatic failover (streaming replication)
- **D)** Multi-region replication (high availability)
- **E)** Not a concern (local development only)

[Answer]: C

---

## Availability Requirements Questions

### Q18: Uptime Expectations

**Context**: Tournament/scoring is time-sensitive. Downtime during active sessions is disruptive.

**Question**: Required uptime SLA?
- **A)** Best-effort (acceptable downtime during maintenance)
- **B)** 99% (acceptable ~7 hours downtime/year)
- **C)** 99.9% (acceptable ~8 hours downtime/year)
- **D)** 99.99% (high availability, < 1 hour downtime/year)
- **E)** No SLA (development/testing environment)

[Answer]: A

---

### Q19: Disaster Recovery

**Context**: Data loss would require re-scoring entire tournament.

**Question**: RTO/RPO requirements?
- **A)** No recovery plan (accept data loss)
- **B)** RPO 24 hours (can lose up to 1 day of data), RTO 1 day
- **C)** RPO < 1 hour, RTO 4 hours
- **D)** RPO < 5 minutes, RTO < 30 minutes (high availability)
- **E)** RPO = 0 (no data loss acceptable), RTO < 5 minutes

[Answer]: B

---

## Tech Stack & Deployment Questions

### Q20: Deployment Model

**Context**: Functional design specifies FastAPI, PostgreSQL, Python. Deployment approach affects architecture.

**Question**: Deployment target?
- **A)** Single server (all components on one machine)
- **B)** Docker containers (single or multiple servers)
- **C)** Kubernetes (cloud-native, auto-scaling)
- **D)** Serverless (AWS Lambda, Azure Functions)
- **E)** Not decided yet (depends on other factors)

[Answer]: B

---

### Q21: Monitoring & Observability

**Context**: Production systems need visibility into performance, errors, and health.

**Question**: Monitoring depth?
- **A)** Basic health checks (system up/down)
- **B)** Application metrics (API latency, error rates, scoring throughput)
- **C)** Full observability (metrics + structured logs + distributed tracing)
- **D)** Advanced (full observability + anomaly detection + alerting)
- **E)** No monitoring (log only errors to file)

[Answer]: B

---

### Q22: CI/CD Requirements

**Context**: Speeds up development iteration and ensures code quality.

**Question**: Deployment automation?
- **A)** Manual deployment (admin runs scripts)
- **B)** Basic CI/CD (run tests on push, manual deploy approval)
- **C)** Full CI/CD (automatic deploy to staging, manual promote to production)
- **D)** Advanced CI/CD (automatic deploy to production with rollback capability)
- **E)** Not needed (internal development only)

[Answer]: B

---

### Q23: Load Balancing & Horizontal Scaling

**Context**: If scaling to multiple servers, need load balancer.

**Question**: Scaling architecture?
- **A)** Single server (no load balancing needed)
- **B)** Multiple servers behind load balancer (active-active)
- **C)** Active-passive failover (warm standby)
- **D)** Auto-scaling group (scale based on metrics)
- **E)** No scaling expected (static configuration)

[Answer]: A

---

## Maintainability Questions

### Q24: Code Quality Standards

**Context**: Affects long-term maintainability and bug rates.

**Question**: Code quality requirements?
- **A)** No specific standards (best-effort)
- **B)** Basic standards (PEP 8, type hints, docstrings)
- **C)** Strict standards (linting, formatting, type checking as gates)
- **D)** Extreme standards (mutation testing, coverage > 80%)
- **E)** Minimal standards (must work, documentation optional)

[Answer]: B

---

### Q25: Testing Requirements

**Context**: Functional design mentions 60-70% code coverage target. This drives testing depth and effort.

**Question**: Testing scope and coverage?
- **A)** Unit tests only, 60-70% coverage (as planned)
- **B)** Unit + integration tests, 70-80% coverage
- **C)** Unit + integration + e2e tests, > 85% coverage
- **D)** Full test suite including contract tests, load tests, security tests
- **E)** Minimal testing (happy path only, no specific coverage target)

[Answer]: A

---

### Q26: Documentation Requirements

**Context**: Affects ability to maintain and extend system in future.

**Question**: Documentation scope?
- **A)** README and inline code comments
- **B)** README + API documentation (OpenAPI/Swagger)
- **C)** README + API docs + design documentation (architecture, decisions)
- **D)** Full documentation (all above + runbook, troubleshooting, operations guide)
- **E)** No documentation (self-documenting code assumed)

[Answer]: D

---

## Summary

**Total Questions**: 26 across 7 categories

| Category | Count | Topics |
|---|---|---|
| Performance | 5 | Scoring latency, preview fps, API response, reports, WebSocket |
| Scalability | 4 | Concurrent users, cameras, sessions, data volume |
| Security | 5 | Baseline enforcement, encryption, tokens, audit logging, compliance |
| Reliability | 3 | Error recovery, overload handling, DB failover |
| Availability | 2 | Uptime SLA, disaster recovery |
| Tech Stack | 3 | Deployment model, monitoring, CI/CD, scaling |
| Maintainability | 3 | Code quality, testing coverage, documentation |

---

## Next Steps

1. Please complete all 26 [Answer]: tags with your responses
2. System will analyze answers for ambiguities and ask follow-up questions if needed
3. Once all answers are validated, generate final NFR Requirements artifacts
4. Present for approval with standard 2-option format

