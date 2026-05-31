# Backend Unit — Infrastructure Design

**Project**: Automated Archery Scoring System  
**Unit**: Backend  
**Date**: 2026-05-25  

---

## Overview

This document specifies the infrastructure deployment architecture for the Backend unit across development, staging, and production environments.

---

## Infrastructure Decisions (Proposed)

Based on NFR Design and tech stack requirements, the following infrastructure choices are proposed:

| Category | Decision | Rationale |
|---|---|---|
| **Deployment Model** | Hybrid: Local MVP + Cloud Scaling | Docker Compose locally, AWS for scaling |
| **Environments** | Three (Dev + Staging + Production) | Standard enterprise practice |
| **IaC** | Docker Compose + Cloud IaC | Terraform for AWS, manual cloud setup |
| **Containers** | Multi-container Docker Compose | Aligns with NFR design (API, DB, Cache, Redis) |
| **API Compute** | Medium (2 vCPU, 4GB RAM, auto-scaling) | Headroom for 4-6 users, scales to 10+ |
| **Scaling** | Cloud auto-scaling groups | EC2 ASGs or similar, scale 1-3 instances |
| **Load Balancing** | AWS/Cloud load balancer | Distributes traffic across API replicas |
| **Database** | Hybrid (local dev, AWS RDS prod) | Managed service for reliability |
| **Database Failover** | Patroni locally, RDS multi-AZ cloud | Automatic failover in both cases |
| **Backups** | AWS automated RDS backups | 35-day retention, cross-AZ |
| **Cache** | AWS ElastiCache Redis | Managed, scales with demand |
| **Image Storage** | Hybrid (local SSD + S3 archive) | Cost-effective: fast local, cheap archive |
| **Events** | In-process for MVP, Redis for scaling | Gradual migration path |
| **Async Tasks** | In-process for MVP, SQS/workers later | Simple initially, extensible |
| **WebSocket** | In-process locally, Redis for multi-server | Scales transparently |
| **API Exposure** | HTTPS (TLS 1.2+) | Secure by default |
| **Certificates** | Let's Encrypt (auto-renewal) | Free, automated, production-ready |
| **Network Security** | AWS Security Groups/VPC | Cloud-native, least privilege |
| **Logging** | CloudWatch (AWS) or equivalent | Managed, searchable, retention policies |
| **Metrics** | Prometheus + CloudWatch | structlog exports to CloudWatch |
| **Alerting** | AWS SNS/CloudWatch Alarms | Email/SMS/Slack notifications |
| **Tracing** | Request IDs + structlog correlation | Simple, sufficient for MVP |
| **Shared Infrastructure** | Shared database, isolated compute | Backend shares DB with Admin API later |
| **Disaster Recovery** | RDS automated backups + warm standby | RPO 24h, RTO 1 day met |

---

## Deployment Architecture

### Development Environment (Local)

```
┌─────────────────────────────────────────────────────┐
│         Developer Laptop / Local Server             │
│                                                     │
│  Docker Compose Services:                          │
│  ┌─────────────────────────────────────────────┐   │
│  │  - api (FastAPI, Uvicorn, 4 workers)       │   │
│  │  - postgres (PostgreSQL 15)                 │   │
│  │  - redis (Redis cache)                      │   │
│  │  - (patroni optional for testing)           │   │
│  │                                              │   │
│  │  Volumes:                                    │   │
│  │  - ./src (API code)                         │   │
│  │  - postgres_data (database)                 │   │
│  │  - redis_data (cache)                       │   │
│  │  - ./storage (images /storage/)             │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  Access:                                            │
│  - API: http://localhost:8000 (HTTP for dev)      │
│  - Docs: http://localhost:8000/docs (Swagger)     │
│  - Database: localhost:5432 (postgres:password)   │
│  - Redis: localhost:6379                          │
│                                                     │
│  Logging:                                           │
│  - structlog → stdout (view with `docker logs`)   │
│  - Optional: Write to file for persistence        │
│                                                     │
│  Metrics:                                           │
│  - GET /metrics (Prometheus format)               │
│  - Manual inspection via curl                      │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Docker Compose Configuration** (`docker-compose.yml`):

```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: archery_api
    environment:
      DATABASE_URL: postgresql://archery_user:password@postgres:5432/archery_dev
      REDIS_URL: redis://redis:6379/0
      ENVIRONMENT: development
      JWT_SECRET: ${JWT_SECRET_DEV}
      DEBUG: "true"
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
    volumes:
      - ./src:/app/src
      - ./storage:/storage
    networks:
      - archery-network
    command: python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

  postgres:
    image: postgres:15-alpine
    container_name: archery_db
    environment:
      POSTGRES_USER: archery_user
      POSTGRES_PASSWORD: password
      POSTGRES_DB: archery_dev
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    networks:
      - archery-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U archery_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: archery_cache
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - archery-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:

networks:
  archery-network:
    driver: bridge
```

---

### Staging Environment (Cloud - AWS)

```
┌────────────────────────────────────────────────────────────┐
│                      AWS Account                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │                   VPC (us-east-1)                   │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │          Public Subnet (ECS/ALB)             │   │   │
│  │  │  ┌────────────────────────────────────────┐  │   │   │
│  │  │  │  Application Load Balancer (ALB)       │  │   │   │
│  │  │  │  - 443 (HTTPS) → API:8000             │  │   │   │
│  │  │  │  - Self-signed cert (staging)         │  │   │   │
│  │  │  └────────────────────────────────────────┘  │   │   │
│  │  │         ↓                                      │   │   │
│  │  │  ┌────────────────────────────────────────┐  │   │   │
│  │  │  │  ECS Cluster (archery-staging)         │  │   │   │
│  │  │  │  - Task: archery-api:latest            │  │   │   │
│  │  │  │  - 1 instance (t3.medium: 2vCPU/4GB)  │  │   │   │
│  │  │  │  - CPU: 1024 (1vCPU), Memory: 2048MB   │  │   │   │
│  │  │  │  - Port: 8000                          │  │   │   │
│  │  │  └────────────────────────────────────────┘  │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  │         ↓                                            │   │
│  │  ┌──────────────────────────────────────────────┐   │   │
│  │  │       Private Subnet (RDS/ElastiCache)       │   │   │
│  │  │  ┌────────────────────────────────────────┐  │   │   │
│  │  │  │  RDS PostgreSQL (Multi-AZ)             │  │   │   │
│  │  │  │  - db.t3.small (1vCPU, 2GB RAM)       │  │   │   │
│  │  │  │  - PostgreSQL 15.2                      │  │   │   │
│  │  │  │  - Multi-AZ failover (automatic)        │  │   │   │
│  │  │  │  - Automated backups (35 days)         │  │   │   │
│  │  │  │  - Encrypted (AWS managed keys)        │  │   │   │
│  │  │  │  - Performance Insights enabled        │  │   │   │
│  │  │  └────────────────────────────────────────┘  │   │   │
│  │  │         ↓                                      │   │   │
│  │  │  ┌────────────────────────────────────────┐  │   │   │
│  │  │  │  ElastiCache Redis (cache.t3.micro)   │  │   │   │
│  │  │  │  - Single node (0.5GB)                 │  │   │   │
│  │  │  │  - Redis 7.0, encrypted in-transit     │  │   │   │
│  │  │  │  - Automatic failover optional         │  │   │   │
│  │  │  │  - CloudWatch monitoring               │  │   │   │
│  │  │  └────────────────────────────────────────┘  │   │   │
│  │  │         ↓                                      │   │   │
│  │  │  ┌────────────────────────────────────────┐  │   │   │
│  │  │  │  S3 Bucket (archery-staging-images)   │  │   │   │
│  │  │  │  - /raw/ (current images)              │  │   │   │
│  │  │  │  - /archive/ (compressed, 90d+)       │  │   │   │
│  │  │  │  - Versioning: disabled                │  │   │   │
│  │  │  │  - Lifecycle: delete after 1 year      │  │   │   │
│  │  │  │  - Server-side encryption (AES-256)    │  │   │   │
│  │  │  │  - Block public access: enabled        │  │   │   │
│  │  │  └────────────────────────────────────────┘  │   │   │
│  │  └──────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │             Monitoring & Logging                     │   │
│  │  ┌────────────────────────────────────────────────┐ │   │
│  │  │  CloudWatch Logs (/aws/ecs/archery-api)      │ │   │
│  │  │  - structlog JSON logs aggregated            │ │   │
│  │  │  - Log retention: 7 days (staging)           │ │   │
│  │  │  - Searchable, filterable, alertable         │ │   │
│  │  └────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────┐ │   │
│  │  │  CloudWatch Metrics                           │ │   │
│  │  │  - API latency (p50, p95, p99)               │ │   │
│  │  │  - Error rate (5xx errors)                    │ │   │
│  │  │  - RDS CPU, database connections             │ │   │
│  │  │  - ElastiCache CPU, evictions                │ │   │
│  │  │  - ECS task CPU, memory usage                │ │   │
│  │  └────────────────────────────────────────────────┘ │   │
│  │  ┌────────────────────────────────────────────────┐ │   │
│  │  │  CloudWatch Alarms                            │ │   │
│  │  │  - API latency > 500ms → SNS → Email          │ │   │
│  │  │  - Error rate > 1% → SNS → Slack             │ │   │
│  │  │  - RDS CPU > 80% → SNS → Email               │ │   │
│  │  │  - Storage quota > 80% → SNS → Alert         │ │   │
│  │  └────────────────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

**AWS Infrastructure Components**:

| Component | Service | Size/Config |
|---|---|---|
| **Compute** | ECS (EC2) | t3.medium (2vCPU, 4GB), 1 task |
| **Load Balancer** | ALB | Single instance, HTTPS |
| **Database** | RDS PostgreSQL | db.t3.small (1vCPU, 2GB), Multi-AZ |
| **Cache** | ElastiCache Redis | cache.t3.micro (0.5GB) |
| **Storage** | S3 | Standard tier, Intelligent-Tiering |
| **Networking** | VPC | Private RDS/ElastiCache, Public ALB/ECS |
| **Secrets** | Secrets Manager | JWT secret, database password |
| **Logging** | CloudWatch Logs | 7-day retention |
| **Monitoring** | CloudWatch Metrics | Dashboards + Alarms |

---

### Production Environment (Cloud - AWS)

```
┌───────────────────────────────────────────────────────────────┐
│                    AWS Account - Production                    │
│  ┌──────────────────────────────────────────────────────────┐ │
│  │                  VPC (us-east-1)                         │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │          Public Subnet (ALB, NAT)                   │ │ │
│  │  │  ┌───────────────────────────────────────────────┐  │ │ │
│  │  │  │  Application Load Balancer (ALB)              │  │ │ │
│  │  │  │  - 443 (HTTPS) → API:8000                     │  │ │ │
│  │  │  │  - Let's Encrypt certificate (auto-renew)    │  │ │ │
│  │  │  │  - Multi-AZ (us-east-1a, us-east-1b)        │  │ │ │
│  │  │  │  - Access logs to S3                          │  │ │ │
│  │  │  │  - WAF rules (optional): rate limit, OWASP   │  │ │ │
│  │  │  └───────────────────────────────────────────────┘  │ │ │
│  │  │         ↓                                            │ │ │
│  │  │  ┌───────────────────────────────────────────────┐  │ │ │
│  │  │  │  Auto-Scaling Group (archery-api-asg)       │  │ │ │
│  │  │  │  - Launch template: archery-api:latest       │  │ │ │
│  │  │  │  - Min: 2, Desired: 2, Max: 5 instances     │  │ │ │
│  │  │  │  - Instance type: t3.medium (2vCPU, 4GB)    │  │ │ │
│  │  │  │  - Scaling policy: CPU > 70% (+1), < 30% (-1) │ │ │ │
│  │  │  │  - Health check: ELB (30s interval)          │  │ │ │
│  │  │  │  - Multi-AZ (us-east-1a, us-east-1b)        │  │ │ │
│  │  │  │                                              │  │ │ │
│  │  │  │  ┌─────────────┐  ┌─────────────┐           │  │ │ │
│  │  │  │  │ API Task 1  │  │ API Task 2  │           │  │ │ │
│  │  │  │  │ (EC2 AZ-1a) │  │ (EC2 AZ-1b) │           │  │ │ │
│  │  │  │  └─────────────┘  └─────────────┘           │  │ │ │
│  │  │  └───────────────────────────────────────────────┘  │ │ │
│  │  │         ↓                                            │ │ │
│  │  │  ┌───────────────────────────────────────────────┐  │ │ │
│  │  │  │   Private Subnet (RDS, ElastiCache, Secrets)  │  │ │ │
│  │  │  │  ┌───────────────────────────────────────┐   │  │ │ │
│  │  │  │  │  RDS Aurora PostgreSQL (HA)          │   │  │ │ │
│  │  │  │  │  - db.t3.medium (2vCPU, 4GB RAM)    │   │  │ │ │
│  │  │  │  │  - PostgreSQL 15 compatible         │   │  │ │ │
│  │  │  │  │  - Multi-AZ with read replicas      │   │  │ │ │
│  │  │  │  │  - Automated failover (< 30s)       │   │  │ │ │
│  │  │  │  │  - Automated backups (35 days)      │   │  │ │ │
│  │  │  │  │  - Encrypted (AWS KMS)              │   │  │ │ │
│  │  │  │  │  - Performance Insights + Monitoring │   │  │ │ │
│  │  │  │  │  - Enhanced monitoring enabled      │   │  │ │ │
│  │  │  │  └───────────────────────────────────────┘   │  │ │ │
│  │  │  │         ↓                                      │  │ │ │
│  │  │  │  ┌───────────────────────────────────────┐   │  │ │ │
│  │  │  │  │  ElastiCache Redis Cluster          │   │  │ │ │
│  │  │  │  │  - cache.r7g.large (2 nodes)        │   │  │ │ │
│  │  │  │  │  - Automatic failover enabled       │   │  │ │ │
│  │  │  │  │  - Redis 7.0 with encryption        │   │  │ │ │
│  │  │  │  │  - 4GB total (2GB per node)         │   │  │ │ │
│  │  │  │  │  - Enhanced monitoring, read replica  │   │  │ │ │
│  │  │  │  └───────────────────────────────────────┘   │  │ │ │
│  │  │  │         ↓                                      │  │ │ │
│  │  │  │  ┌───────────────────────────────────────┐   │  │ │ │
│  │  │  │  │  S3 Bucket (archery-prod-images)    │   │  │ │ │
│  │  │  │  │  - /raw/ (current, SSD)              │   │  │ │ │
│  │  │  │  │  - /archive/ (Glacier, 90d+)        │   │  │ │ │
│  │  │  │  │  - Versioning: enabled               │   │  │ │ │
│  │  │  │  │  - Lifecycle: Intelligent-Tiering   │   │  │ │ │
│  │  │  │  │  - Encryption: KMS                   │   │  │ │ │
│  │  │  │  │  - Replication: cross-region (DR)   │   │  │ │ │
│  │  │  │  │  - Access logging enabled            │   │  │ │ │
│  │  │  │  └───────────────────────────────────────┘   │  │ │ │
│  │  │  │         ↓                                      │  │ │ │
│  │  │  │  ┌───────────────────────────────────────┐   │  │ │ │
│  │  │  │  │  Secrets Manager                      │   │  │ │ │
│  │  │  │  │  - JWT_SECRET (rotated monthly)      │   │  │ │ │
│  │  │  │  │  - RDS password (rotated quarterly)  │   │  │ │ │
│  │  │  │  │  - Redis password                     │   │  │ │ │
│  │  │  │  └───────────────────────────────────────┘   │  │ │ │
│  │  │  └───────────────────────────────────────────────┘  │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │                                                          │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │          Disaster Recovery (us-west-2)             │ │ │
│  │  │  - S3 Cross-Region Replication to us-west-2       │ │ │
│  │  │  - RDS backup snapshots replicated (weekly)        │ │ │
│  │  │  - Failover runbook documented                     │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │                                                          │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │         Monitoring & Observability                  │ │ │
│  │  │  ┌───────────────────────────────────────────────┐  │ │ │
│  │  │  │  CloudWatch Logs (/aws/ecs/archery-api)      │  │ │ │
│  │  │  │  - structlog JSON logs for all instances      │  │ │ │
│  │  │  │  - Log retention: 30 days (production)        │  │ │ │
│  │  │  │  - Log Insights queries for debugging         │  │ │ │
│  │  │  │  - Encryption: KMS                           │  │ │ │
│  │  │  └───────────────────────────────────────────────┘  │ │ │
│  │  │  ┌───────────────────────────────────────────────┐  │ │ │
│  │  │  │  CloudWatch Dashboards                        │  │ │ │
│  │  │  │  - API latency (p50, p95, p99)               │  │ │ │
│  │  │  │  - Error rate, 5xx count                      │  │ │ │
│  │  │  │  - RDS CPU, connections, replication lag      │  │ │ │
│  │  │  │  - ElastiCache CPU, memory, evictions         │  │ │ │
│  │  │  │  - ASG desired/running count, scaling events  │  │ │ │
│  │  │  │  - ALB request count, target health           │  │ │ │
│  │  │  │  - Storage usage (S3 bucket size)             │  │ │ │
│  │  │  └───────────────────────────────────────────────┘  │ │ │
│  │  │  ┌───────────────────────────────────────────────┐  │ │ │
│  │  │  │  CloudWatch Alarms (with escalation)          │  │ │ │
│  │  │  │  - API latency > 500ms → SNS → Slack         │  │ │ │
│  │  │  │  - Error rate > 1% → SNS → PagerDuty         │  │ │ │
│  │  │  │  - RDS CPU > 80% → SNS → Slack + page       │  │ │ │
│  │  │  │  - RDS replication lag > 1s → escalate       │  │ │ │
│  │  │  │  - Storage quota > 90% → SNS → alert         │  │ │ │
│  │  │  │  - ElastiCache evictions > 0 → SNS → alert  │  │ │ │
│  │  │  │  - ASG scaling > 3 events/hour → investigate │  │ │ │
│  │  │  └───────────────────────────────────────────────┘  │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │                                                          │ │
│  │  ┌─────────────────────────────────────────────────────┐ │ │
│  │  │         Security & Compliance                        │ │ │
│  │  │  - VPC with security groups (least privilege)       │ │ │
│  │  │  - RDS encryption at rest + in transit (TLS)       │ │ │
│  │  │  - Redis encryption in transit (TLS)               │ │ │
│  │  │  - S3 server-side encryption (KMS)                 │ │ │
│  │  │  - Secrets Manager with rotation policies          │ │ │
│  │  │  - ALB access logs to S3 (30-day retention)        │ │ │
│  │  │  - RDS audit logs (CloudTrail)                     │ │ │
│  │  │  - VPC Flow Logs (security monitoring)             │ │ │
│  │  └─────────────────────────────────────────────────────┘ │ │
│  │                                                          │ │
│  └──────────────────────────────────────────────────────────┘ │
│                                                               │
└───────────────────────────────────────────────────────────────┘
```

**AWS Production Infrastructure**:

| Component | Service | Size/Config |
|---|---|---|
| **Compute** | ECS Auto Scaling | t3.medium, 2-5 instances, CPU-based scaling |
| **Load Balancer** | ALB | Multi-AZ (us-east-1a, us-east-1b), HTTPS |
| **Database** | Amazon Aurora PostgreSQL | db.t3.medium (2vCPU, 4GB), Multi-AZ, read replicas |
| **Cache** | ElastiCache Redis Cluster | cache.r7g.large (2 nodes, 4GB total), auto-failover |
| **Storage** | S3 + Intelligent-Tiering | Standard → Glacier lifecycle |
| **Networking** | VPC + Security Groups | Private DB/Cache, public ALB/ECS |
| **Secrets** | AWS Secrets Manager | Rotated JWT (monthly), DB password (quarterly) |
| **Logging** | CloudWatch Logs | 30-day retention, KMS encrypted |
| **Monitoring** | CloudWatch Dashboards + Alarms | Real-time dashboards, escalation to PagerDuty |
| **Disaster Recovery** | S3 Cross-Region Replication | Images replicated to us-west-2 |

---

## Environment Comparison

| Aspect | Development | Staging | Production |
|---|---|---|---|
| **Location** | Local machine | AWS (us-east-1) | AWS (us-east-1) with DR (us-west-2) |
| **Compute** | Docker (1 container) | ECS (1 instance) | ECS (2-5 instances, auto-scaling) |
| **Database** | PostgreSQL container | RDS (db.t3.small) | Aurora PostgreSQL (db.t3.medium) |
| **Cache** | Redis container | ElastiCache (micro) | ElastiCache (large, 2 nodes) |
| **Storage** | Local filesystem | S3 Standard | S3 Standard + Glacier (lifecycle) |
| **HTTPS** | Not required (localhost) | Self-signed | Let's Encrypt (auto-renew) |
| **Load Balancing** | None (direct:8000) | ALB | ALB (Multi-AZ) |
| **Failover** | N/A | RDS multi-AZ only | RDS multi-AZ + read replicas |
| **Backups** | Manual | AWS automated (7 days) | AWS automated (35 days) + cross-region |
| **Monitoring** | Local logs | CloudWatch (basic) | CloudWatch (full) + PagerDuty |
| **Scaling** | Manual | Manual | Automatic (CPU-based) |
| **Cost** | ~$0 (local) | ~$100-200/month | ~$300-500/month |
| **Uptime SLA** | Best-effort | 99% | 99.9% |

---

## Infrastructure Components Mapping

### Functional Design → Infrastructure

| Logical Component | Dev Implementation | Staging Implementation | Production Implementation |
|---|---|---|---|
| **API Server** | Uvicorn container | ECS task (1) | ECS ASG (2-5 tasks) |
| **PostgreSQL DB** | Docker container | RDS db.t3.small | Aurora PostgreSQL db.t3.medium |
| **Patroni Failover** | None (single DB) | Multi-AZ failover | Multi-AZ failover + read replicas |
| **Redis Cache** | Docker container | ElastiCache (micro) | ElastiCache Cluster (r7g.large) |
| **EventBus** | In-process | In-process | In-process (with Redis for scaling) |
| **ThreadPool** | Python Executor (4 workers) | ECS task resources (1vCPU) | ECS task resources (1vCPU per task × 2-5) |
| **Image Storage** | Local filesystem | S3 standard | S3 standard + Glacier |
| **WebSocketManager** | In-process | In-process + optional Redis | In-process (Redis coordination) |
| **Structured Logging** | stdout (docker logs) | CloudWatch Logs | CloudWatch Logs (KMS encrypted) |
| **Metrics** | /metrics endpoint | CloudWatch Metrics | CloudWatch Metrics + custom dashboards |
| **Health Check** | GET /health (manual) | GET /health (ALB probes) | GET /health (ALB probes) |

---

## Deployment Automation

### CI/CD Pipeline

```
Code Push (GitHub)
    ↓
GitHub Actions (Tests)
    ├─ Run unit tests
    ├─ Run integration tests
    ├─ Linting + type checking
    ├─ Build Docker image
    └─ Push to ECR (staging-only)
    ↓
Manual Approval (operator)
    ↓
Deploy to Staging (ECS)
    ├─ Pull image from ECR
    ├─ Stop old task
    ├─ Start new task
    ├─ Health check
    └─ Smoke tests
    ↓
Manual Approval (operator + testing team)
    ↓
Deploy to Production (ECS)
    ├─ Create new task definition (blue/green)
    ├─ Route 10% traffic → new (canary)
    ├─ Monitor metrics (5 min)
    ├─ Route remaining traffic if healthy
    ├─ Monitor (15 min)
    └─ Cleanup old task
    ↓
Success
    ├─ Post to Slack (#deploys)
    └─ Update status dashboard
```

**GitHub Actions Workflow** (`.github/workflows/deploy.yml`):

```yaml
name: Build & Deploy

on:
  push:
    branches: [main, staging]

env:
  AWS_REGION: us-east-1
  ECR_REGISTRY: ${{ secrets.AWS_ACCOUNT_ID }}.dkr.ecr.${{ env.AWS_REGION }}.amazonaws.com

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432
      
      redis:
        image: redis:7
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 6379:6379
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      
      - name: Run tests
        run: poetry run pytest --cov=src --cov-report=xml
      
      - name: Run linting
        run: |
          poetry run flake8 src/ --max-line-length=120
          poetry run mypy src/
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}
      
      - name: Login to ECR
        run: aws ecr get-login-password | docker login --username AWS --password-stdin ${{ env.ECR_REGISTRY }}
      
      - name: Build Docker image
        run: |
          docker build -t ${{ env.ECR_REGISTRY }}/archery-api:${{ github.sha }} .
          docker tag ${{ env.ECR_REGISTRY }}/archery-api:${{ github.sha }} ${{ env.ECR_REGISTRY }}/archery-api:latest
      
      - name: Push image to ECR
        run: |
          docker push ${{ env.ECR_REGISTRY }}/archery-api:${{ github.sha }}
          docker push ${{ env.ECR_REGISTRY }}/archery-api:latest
      
      - name: Deploy to Staging (if staging branch)
        if: github.ref == 'refs/heads/staging'
        run: |
          aws ecs update-service \
            --cluster archery-staging \
            --service archery-api \
            --force-new-deployment \
            --region ${{ env.AWS_REGION }}
      
      - name: Post to Slack
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Build ${{ job.status }} for ${{ github.ref }}'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

## Cost Estimation

### Development (Local)
- **Compute**: $0 (laptop)
- **Cloud services**: $0
- **Total**: $0/month

### Staging (AWS)
- **ECS EC2 (t3.medium, 1 instance)**: ~$30/month
- **RDS PostgreSQL (db.t3.small)**: ~$50/month
- **ElastiCache Redis (cache.t3.micro)**: ~$20/month
- **S3 (10GB standard + 1GB glacier)**: ~$5/month
- **Data transfer**: ~$5/month
- **Total**: ~$110/month

### Production (AWS)
- **ECS EC2 (t3.medium, 2 instances)**: ~$60/month (avg)
- **RDS Aurora PostgreSQL (db.t3.medium)**: ~$100/month
- **ElastiCache Redis Cluster (r7g.large)**: ~$80/month
- **S3 (50GB standard + 20GB glacier)**: ~$15/month
- **Data transfer + ALB**: ~$20/month
- **Monitoring, logging, secrets**: ~$10/month
- **Total**: ~$285/month

---

## Security Considerations

### Network Security
- **VPC**: Private subnets for database/cache, public for ALB/ECS
- **Security Groups**: 
  - ALB: Inbound 443 (HTTPS), outbound to ECS
  - ECS: Inbound from ALB, outbound to RDS/Redis/S3
  - RDS: Inbound from ECS only
  - Redis: Inbound from ECS only

### Data Security
- **Encryption in Transit**: TLS 1.2+ for all connections
- **Encryption at Rest**: KMS for RDS, S3, CloudWatch Logs
- **Secrets Management**: AWS Secrets Manager (no hardcoded credentials)
- **Access Control**: IAM roles + resource-based policies

### Compliance
- **Audit Logging**: RDS query logging, CloudTrail for API calls
- **Data Retention**: 30-day production logs, 90-day images
- **Backup Strategy**: 35-day retention, cross-region replication
- **Incident Response**: PagerDuty escalation, runbooks documented

---

## Summary: Infrastructure Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Deployment Model | Hybrid: Local MVP + Cloud ASG | Pragmatic: start simple, scale when needed |
| Cloud Provider | AWS (recommended) | Mature, cost-effective, good for this workload |
| Environments | Dev (Local) + Staging (AWS) + Prod (AWS) | Standard enterprise practice |
| Compute | ECS (EC2) with ASG | Managed Kubernetes alternative, cost-effective |
| Database | RDS PostgreSQL (prod: Aurora) | Managed service, reduces ops burden |
| Cache | ElastiCache Redis | AWS native, scales seamlessly |
| Storage | S3 + Glacier lifecycle | Cost-effective, durable, lifecycle management |
| Logging | CloudWatch Logs | AWS native, integrates with metrics/alarms |
| Monitoring | CloudWatch Metrics + Alarms | AWS native, sufficient for MVP |
| Secrets | AWS Secrets Manager | AWS native, auto-rotation support |
| Load Balancing | ALB (production only) | Multi-AZ, health checks, TLS termination |
| CI/CD | GitHub Actions + ECR | Simple, AWS-native container registry |
| Disaster Recovery | RDS + S3 cross-region | Meets RPO 24h, RTO 1 day requirements |

