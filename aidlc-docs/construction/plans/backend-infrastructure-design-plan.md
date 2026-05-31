# Backend Unit — Infrastructure Design Planning

**Project**: Automated Archery Scoring System  
**Unit**: Backend  
**Date**: 2026-05-25  

---

## Infrastructure Design Assessment Plan

**Objective**: Map logical components from NFR Design to actual infrastructure (cloud provider, compute, storage, networking) for deployment environments (development, staging, production).

**Status**: PLANNING

---

## Context from Previous Stages

**Functional Design**:
- FastAPI backend, PostgreSQL database, image processing via OpenCV
- ThreadPool concurrency (4 base, 8 max)
- Real-time WebSocket events

**NFR Design (Logical Components)**:
- PostgreSQL + Patroni failover (warm standby)
- Redis distributed cache
- Filesystem storage (/storage/, 10GB quota)
- ThreadPool for image processing
- EventBus, CacheManager, LoadManager, WebSocketManager
- Structured logging (structlog + audit database table)
- Health checker endpoint

**Tech Stack Locked**:
- Language: Python 3.11+
- Framework: FastAPI + Uvicorn
- Database: PostgreSQL 15+ with Patroni
- Cache: Redis 7
- Container: Docker
- Messaging: Native Python (EventBus in-process)
- Monitoring: structlog + Prometheus-compatible metrics

**Questions**: How to deploy and scale these components across development/staging/production?

---

## Assessment Checkboxes

- [x] Step 1: Analyze deployment environment choices
- [x] Step 2: Analyze compute infrastructure options
- [x] Step 3: Analyze storage infrastructure options
- [x] Step 4: Analyze messaging/async infrastructure
- [x] Step 5: Analyze networking and load balancing
- [x] Step 6: Analyze monitoring and logging infrastructure
- [x] Step 7: Analyze shared infrastructure strategy
- [x] Step 8: Review all answers for ambiguities
- [x] Step 9: Generate final infrastructure artifacts

---

## Deployment Environment Questions

### Q1: Cloud Provider or On-Premise?

**Context**: Archery tournaments may be regional (local infrastructure) or national (cloud infrastructure).

**Question**: Primary deployment target?
- **A)** On-premise (local server at tournament venue, no cloud)
- **B)** AWS (Amazon Web Services, most mature)
- **C)** Azure (Microsoft, good for enterprise)
- **D)** GCP (Google Cloud Platform, good for data/ML)
- **E)** Hybrid (local for MVP, cloud for scaling)

[Answer]: **E** - Hybrid (local Docker Compose MVP, AWS scaling path) 

---

### Q2: Multi-Environment Setup

**Context**: Typical deployment needs development, staging, testing, and production environments.

**Question**: How many environments should be supported?
- **A)** Single environment (development only, MVP)
- **B)** Two environments (development + production)
- **C)** Three environments (dev + staging + production)
- **D)** Four+ environments (dev + test + staging + prod + disaster recovery)
- **E)** Not needed (local development only)

[Answer]: **C** - Three environments (dev + staging + production) 

---

### Q3: Infrastructure as Code (IaC)

**Context**: Managing infrastructure via code (Terraform, CloudFormation) enables reproducibility and version control.

**Question**: Should infrastructure be defined as code?
- **A)** No (manual setup, simple)
- **B)** Basic IaC (Docker Compose for local, manual cloud setup)
- **C)** Full IaC (Terraform for all infrastructure)
- **D)** Advanced IaC (Terraform + Ansible for configuration management)
- **E)** Platform-specific (CloudFormation for AWS, ARM for Azure, etc.)

[Answer]: **B** - Basic IaC (Docker Compose + AWS manual/Terraform) 

---

### Q4: Containerization Strategy

**Context**: Docker containers enable portability across environments.

**Question**: How should containerization be approached?
- **A)** Single monolithic container (all services in one image)
- **B)** Multi-container Docker Compose (local dev, single server prod)
- **C)** Microservices containers (separate API, worker, scheduler services)
- **D)** Serverless functions (AWS Lambda, Azure Functions for scaling)
- **E)** Not using containers (direct Python installation)

[Answer]: **B** - Multi-container Docker Compose (aligns with NFR design) 

---

## Compute Infrastructure Questions

### Q5: API Server Sizing

**Context**: Uvicorn runs with 4 workers by default. Sizing depends on expected load.

**Question**: API server compute requirements?
- **A)** Small (t3.small / 1-2 vCPU, 2GB RAM, sufficient for 4-6 users)
- **B)** Medium (t3.medium / 2 vCPU, 4GB RAM, headroom for growth)
- **C)** Large (t3.large / 2-4 vCPU, 8GB RAM, supports 10+ users)
- **D)** Burstable (auto-scale based on demand, start small scale large)
- **E)** Not specified (use defaults, tune later)

[Answer]: **B** - Medium (t3.medium, 2vCPU/4GB, headroom for 4-6 users) 

---

### Q6: Horizontal Scaling Strategy

**Context**: As load grows, system may need multiple API server replicas.

**Question**: How should horizontal scaling be handled?
- **A)** No scaling (single server always)
- **B)** Manual scaling (operator adds more servers when needed)
- **C)** Auto-scaling (cloud provider scales based on metrics)
- **D)** Orchestration (Kubernetes for automatic pod management)
- **E)** Hybrid (local single server, cloud auto-scaling if deployed)

[Answer]: **C** - Auto-scaling (AWS ECS ASG, CPU-based 2-5 instances) 

---

### Q7: Load Balancing

**Context**: Multiple API servers need a load balancer to distribute traffic.

**Question**: How should traffic be load balanced?
- **A)** No load balancer (single server only)
- **B)** nginx/HAProxy (simple reverse proxy, manual setup)
- **C)** Cloud load balancer (AWS ELB, Azure LB, GCP Load Balancer)
- **D)** DNS round-robin (simple but no health checks)
- **E)** Service mesh (Istio for advanced routing)

[Answer]: **C** - Cloud ALB (AWS Application Load Balancer, multi-AZ) 

---

### Q8: Worker Processes for Async Tasks

**Context**: Some tasks (report generation, image archival) are async and can run in background workers.

**Question**: Should background workers be separate processes?
- **A)** No workers (all tasks synchronous, run in main API)
- **B)** In-process workers (FastAPI BackgroundTasks, same server)
- **C)** Separate worker processes (Celery + RabbitMQ/Redis)
- **D)** Serverless workers (AWS Lambda for async tasks)
- **E)** Hybrid (in-process for MVP, separate workers if needed)

[Answer]: **E** - Hybrid (in-process for MVP, SQS workers for scaling) 

---

## Storage Infrastructure Questions

### Q9: Database Service Choice

**Context**: PostgreSQL on local server vs. managed cloud database (RDS, Azure Database).

**Question**: How should PostgreSQL be deployed?
- **A)** Self-managed (PostgreSQL container on same server)
- **B)** Managed service (AWS RDS, Azure Database for PostgreSQL)
- **C)** Cloud native (Aurora PostgreSQL on AWS for better availability)
- **D)** On-premise dedicated server (separate physical/VM)
- **E)** Hybrid (local for dev, cloud RDS for production)

[Answer]: **E** - Hybrid (local Docker for dev, AWS RDS staging, Aurora prod) 

---

### Q10: Database Backup Strategy

**Context**: Daily backups required for disaster recovery (RPO 24 hours, RTO 1 day).

**Question**: How should database backups be managed?
- **A)** Manual backups (operator runs backup script daily)
- **B)** Automated snapshots (cloud provider snapshot tool)
- **C)** Managed backups (AWS RDS automated backup, 35-day retention)
- **D)** Cross-region replication (backup to different region/provider)
- **E)** No backups (accept data loss risk)

[Answer]: **C** - Managed RDS backups (35-day retention, meets RPO/RTO) 

---

### Q11: Failover Configuration

**Context**: NFR design specifies warm standby with streaming replication (Patroni).

**Question**: How should database failover be implemented?
- **A)** No failover (single database instance only)
- **B)** Manual failover (backup database, manual promotion)
- **C)** Patroni (automatic failover, warm standby)
- **D)** Managed failover (AWS RDS multi-AZ, automatic failover)
- **E)** Hybrid (Patroni for on-premise, RDS multi-AZ for cloud)

[Answer]: **E** - Hybrid (Patroni for local, RDS multi-AZ for cloud) 

---

### Q12: Cache Deployment

**Context**: Redis cache needed for performance (cameras, leaderboards, sessions).

**Question**: How should Redis be deployed?
- **A)** In-memory cache (Python dict/LRU, no Redis needed)
- **B)** Redis container (Docker, same server as API)
- **C)** Managed Redis (AWS ElastiCache, Azure Redis Cache)
- **D)** Redis cluster (distributed Redis for high availability)
- **E)** Multi-region Redis (Redis replication across regions)

[Answer]: **C** - Managed Redis (AWS ElastiCache, scaling ready) 

---

### Q13: Image Storage Solution

**Context**: Store scoring images (1-5 MB per score), ~10 GB quota, 90-day retention, archive to tar.gz.

**Question**: How should image storage be handled?
- **A)** Local filesystem (server disk, manual backup)
- **B)** Network filesystem (NFS mount, shared across servers)
- **C)** Object storage (AWS S3, Azure Blob, GCP Cloud Storage)
- **D)** Hybrid (local SSD fast, S3 archive old)
- **E)** Not needed (store images in database BLOB)

[Answer]: **D** - Hybrid (local SSD for dev/staging, S3 for prod archive) 

---

### Q14: Database Size Growth

**Context**: Scores, sessions, images grow over time. Quota management and cleanup needed.

**Question**: How should storage growth be managed?
- **A)** No planning (assume unlimited space)
- **B)** Manual cleanup (operator deletes old data)
- **C)** Automated archival (90-day rotation, compress old data)
- **D)** Auto-expansion (cloud storage scales automatically)
- **E)** Tiered storage (hot SSD, cold HDD, archive cloud)

[Answer]: **E** - Tiered storage (S3 Intelligent-Tiering, Glacier for 90d+) 

---

## Messaging & Async Infrastructure Questions

### Q15: Event Publishing

**Context**: Events (ScoreCalculated, CameraConnected) published by services, subscribed by handlers.

**Question**: How should events be published?
- **A)** In-process EventBus (Python, single server only)
- **B)** Message queue (Redis Pub/Sub, simple)
- **C)** Message broker (RabbitMQ, more reliable)
- **D)** Cloud messaging (AWS SNS/SQS, Azure Service Bus)
- **E)** Kafka (event streaming, complex but scalable)

[Answer]: **A** - In-process for MVP (Redis for multi-server scaling later) 

---

### Q16: Async Task Processing

**Context**: Long-running tasks (report generation, image archival) should be async.

**Question**: How should async tasks be executed?
- **A)** No async (all synchronous, user waits)
- **B)** Background threads (in-process, same server)
- **C)** Message queue + workers (Redis + Rq, or RabbitMQ + Celery)
- **D)** Serverless (AWS Lambda, runs on-demand)
- **E)** Hybrid (in-process for MVP, queue-based for scaling)

[Answer]: **E** - Hybrid (in-process for MVP, SQS workers for prod) 

---

### Q17: WebSocket Real-Time Communication

**Context**: WebSocket broadcasts real-time events (scores, leaderboards, camera status).

**Question**: How should WebSocket infrastructure scale?
- **A)** In-process (WebSocketManager on single server only)
- **B)** Redis Pub/Sub (WebSocket servers subscribe to Redis channels)
- **C)** Message broker (RabbitMQ for cross-server WebSocket coordination)
- **D)** Cloud services (AWS AppSync, Azure SignalR Service)
- **E)** Hybrid (in-process for single server, Redis for multi-server)

[Answer]: **E** - Hybrid (in-process for MVP, Redis coordination for scaling) 

---

## Networking Infrastructure Questions

### Q18: API Exposure

**Context**: How should Backend API be exposed to Frontend?

**Question**: How should the API be exposed?
- **A)** Direct (localhost:8000, development only)
- **B)** HTTP (plain http://api.example.com, no encryption)
- **C)** HTTPS (https://api.example.com, TLS certificates)
- **D)** API Gateway (AWS API Gateway, Azure API Management for routing/auth)
- **E)** Service mesh (Istio/Linkerd for advanced routing)

[Answer]: **C** - HTTPS (TLS 1.2+ for all connections) 

---

### Q19: SSL/TLS Certificates

**Context**: HTTPS requires certificates (self-signed for dev, Let's Encrypt/purchased for prod).

**Question**: How should SSL/TLS certificates be managed?
- **A)** Self-signed (development only, not suitable for production)
- **B)** Let's Encrypt (free, automated certificate renewal)
- **C)** AWS Certificate Manager (managed certificates for AWS users)
- **D)** Purchased certificates (from certificate authority, manual renewal)
- **E)** Hybrid (Let's Encrypt for dev/staging, purchased for production)

[Answer]: **B** - Let's Encrypt (free, auto-renewal, production-ready) 

---

### Q20: Network Security (Firewall, VPC)

**Context**: Restrict network access to prevent unauthorized access.

**Question**: How should network security be implemented?
- **A)** No restrictions (open to internet, not recommended)
- **B)** Firewall rules (only needed ports open: 443 for HTTPS, 22 for SSH)
- **C)** VPC isolation (private subnet for database, public for API)
- **D)** Security groups/NSG (cloud provider network security)
- **E)** Zero trust network (VPN required, IP whitelisting, strict segmentation)

[Answer]: **D** - AWS Security Groups (VPC, least privilege) 

---

## Monitoring Infrastructure Questions

### Q21: Logging Aggregation

**Context**: structlog outputs JSON logs to stdout. Need centralized logging for debugging.

**Question**: How should logs be aggregated?
- **A)** No aggregation (view logs locally only)
- **B)** File logging (write logs to file, rotate manually)
- **C)** Cloud logging (CloudWatch, Azure Monitor, Cloud Logging)
- **D)** ELK stack (Elasticsearch, Logstash, Kibana, self-hosted)
- **E)** Hybrid (file locally, cloud in production)

[Answer]: **C** - CloudWatch Logs (AWS native, 7-day staging, 30-day prod) 

---

### Q22: Metrics Collection

**Context**: Prometheus-compatible metrics endpoint for monitoring latency, errors, throughput.

**Question**: How should metrics be collected?
- **A)** No metrics (no monitoring)
- **B)** Manual monitoring (check /metrics endpoint manually)
- **C)** Prometheus (time-series database, scrape metrics endpoint)
- **D)** Cloud monitoring (CloudWatch, Azure Monitor, Cloud Monitoring)
- **E)** SaaS monitoring (Datadog, New Relic for full observability)

[Answer]: **C** - Prometheus + CloudWatch (supports structlog integration) 

---

### Q23: Alerting Strategy

**Context**: Alert operators when issues occur (high latency, errors, quota exceeded).

**Question**: How should alerting work?
- **A)** No alerting (manual checking only)
- **B)** Email alerts (issues sent to operators via email)
- **C)** Slack/Teams (notifications to team chat)
- **D)** PagerDuty (incident management, on-call escalation)
- **E)** Cloud native (AWS SNS, Azure Alerts for notifications)

[Answer]: **E** - AWS SNS/CloudWatch Alarms (Slack + PagerDuty in prod) 

---

### Q24: Distributed Tracing

**Context**: Track requests across service boundaries for debugging complex interactions.

**Question**: Should distributed tracing be implemented?
- **A)** No (not needed for monolithic backend)
- **B)** Basic tracing (request ID in logs, manual correlation)
- **C)** OpenTelemetry (standardized tracing, optional backend)
- **D)** Jaeger (self-hosted distributed tracing)
- **E)** SaaS tracing (Datadog APM, Lightstep, Honeycomb)

[Answer]: **B** - Basic tracing (request IDs in structlog logs, MVP) 

---

## Shared Infrastructure Questions

### Q25: Infrastructure Sharing Strategy

**Context**: Backend is one of potentially multiple units (Frontend, Admin API, etc.). Decide whether to share infrastructure.

**Question**: How should infrastructure be shared?
- **A)** Isolated (separate database, cache, storage for each unit)
- **B)** Shared database, isolated compute (shared PostgreSQL, separate API servers)
- **C)** Fully shared (all units share database, cache, networking)
- **D)** Tenant isolation (separate database per tournament/tenant)
- **E)** Not applicable (single unit only)

[Answer]: **B** - Shared database, isolated compute (API, Admin API separate) 

---

### Q26: Disaster Recovery Plan

**Context**: What happens if primary infrastructure fails? RTO 1 day, RPO 24 hours.

**Question**: How should disaster recovery be implemented?
- **A)** No plan (accept data loss and downtime)
- **B)** Backup only (daily backups, manual restoration)
- **C)** Warm standby (duplicate infrastructure, automatic failover)
- **D)** Multi-region (active-active or active-passive across regions)
- **E)** Hybrid (backup for data, warm standby for compute)

[Answer]: **E** - Hybrid (RDS backups + S3 cross-region replication) 

---

## Summary

**Total Questions**: 26 across 7 categories

| Category | Count | Topics |
|---|---|---|
| **Deployment Environment** | 4 | Cloud/on-premise, multi-env, IaC, containerization |
| **Compute Infrastructure** | 4 | Sizing, auto-scaling, load balancing, workers |
| **Storage Infrastructure** | 6 | Database, backups, failover, cache, images, growth |
| **Messaging & Async** | 3 | Event publishing, async tasks, WebSocket |
| **Networking** | 3 | API exposure, SSL/TLS, network security |
| **Monitoring** | 4 | Logging, metrics, alerting, tracing |
| **Shared Infrastructure** | 2 | Sharing strategy, disaster recovery |

---

## Proposed Answers Summary

**Status**: All 26 questions answered with pragmatic infrastructure choices aligned with NFR Design.

**Infrastructure Design Artifacts Generated**:
1. `infrastructure-design.md` - Overall architecture, environments, decisions, cost estimation
2. `deployment-architecture.md` - Detailed deployment specs, Docker Compose, AWS setup, CI/CD pipeline

**Key Decisions**:
- Hybrid deployment: Local MVP + AWS cloud scaling
- Three environments: Dev (Docker) + Staging (ECS 1 instance) + Prod (ECS auto-scaling 2-5)
- AWS services: RDS, ElastiCache, S3, CloudWatch, ALB
- Cost: ~$0 dev, ~$110/month staging, ~$285/month production

**Ready for Approval**: Infrastructure Design complete, awaiting user review and approval.

