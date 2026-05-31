# Backend Unit — Logical Components & Infrastructure

**Project**: Automated Archery Scoring System  
**Unit**: Backend  
**Date**: 2026-05-25  

---

## Overview

This document specifies the logical infrastructure components needed to support NFR requirements and how they integrate with the Backend application.

---

## Component Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Application                         │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  API Routers: Auth, Cameras, Sessions, Scoring, Reports   │   │
│  │  WebSocket Manager: Event broadcasting, disconnection      │   │
│  │  Error Handlers: Input validation, rate limiting          │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ↕                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │              Service Layer (Business Logic)                 │   │
│  │  AuthService, CameraService, ScoringService,              │   │
│  │  ReportService, EventBus, ArchiveService                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                              ↕                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │           Data Access & Infrastructure Layers              │   │
│  │  ┌────────────────┐  ┌──────────────┐  ┌───────────────┐  │   │
│  │  │ Repositories   │  │ Cache Manager│  │ThreadPool Mgr │  │   │
│  │  │ (User, Session,│  │ (Cameras,    │  │ (max=8)       │  │   │
│  │  │  Score, etc)   │  │ Sessions,    │  │               │  │   │
│  │  │                │  │ Leaderboard) │  │               │  │   │
│  │  └────────────────┘  └──────────────┘  └───────────────┘  │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
              ↕                    ↕                    ↕
        ┌──────────────┐   ┌──────────────┐   ┌──────────────┐
        │  PostgreSQL  │   │   Storage    │   │   Redis      │
        │  (Primary)   │   │   Filesystem │   │   Cache      │
        │              │   │   /storage/  │   │   (Queues,   │
        │  Connection  │   │              │   │   Sessions)  │
        │  Pool (5-20) │   │   - /raw/    │   │              │
        │              │   │   - /archive/│   │              │
        │ Warm Standby │   │   - /annotated│  │              │
        │ (Patroni)    │   │              │   │              │
        └──────────────┘   └──────────────┘   └──────────────┘
              ↕                                      ↕
        ┌──────────────┐                    ┌──────────────┐
        │  PostgreSQL  │                    │  Monitoring  │
        │  Standby     │                    │  (Prometheus)│
        │  (Patroni)   │                    │  (structlog) │
        └──────────────┘                    └──────────────┘
```

---

## Core Components

### Component 1: PostgreSQL Database with Connection Pooling

**Purpose**: Primary data store for all entities (users, sessions, scores, cameras, audit logs)

**Configuration**:
- **Primary Instance**: Active database server
- **Standby Instance**: Warm standby with streaming replication (Patroni)
- **Connection Pool**: SQLAlchemy QueuePool (min 5, max 20 connections, adaptive)
- **Failover**: Automatic via Patroni (< 5 minutes RTO)

**Responsibilities**:
- Store all operational data (users, tournaments, sessions, scores)
- Enforce data integrity (constraints, foreign keys)
- Provide ACID transactions for critical operations
- Row-level locking for concurrent updates

**Integration Points**:
- All repositories use engine connection
- Session model inherits from Base
- Migrations applied via manual SQL scripts

**Deployment**:
```yaml
services:
  postgres-primary:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
  
  patroni-primary:
    image: patroni:latest
    environment:
      PATRONI_POSTGRESQL_DATA_DIR: /var/lib/postgresql/data
      PATRONI_SCOPE: archery-cluster
      PATRONI_POSTGRESQL_BASEBACKUP:
        - command: "pgbasebackup -l backup"
```

---

### Component 2: Redis Distributed Cache

**Purpose**: Caching layer for hot data (cameras, sessions, leaderboards) to reduce database load

**Configuration**:
- **Memory Limit**: 512 MB (configurable)
- **Eviction Policy**: allkeys-lru (remove least recently used when full)
- **Persistence**: RDB snapshots every 60 seconds (acceptable data loss)
- **Replication**: Optional (single instance for MVP)

**Cached Data**:
- `cameras:all` → List of all cameras (TTL 5 min)
- `session:{id}` → Session details (TTL 1 min)
- `leaderboard:{session_id}` → Aggregated scores (TTL 1 min)
- Event queue for async tasks (Lists)

**Responsibilities**:
- Serve frequently-accessed data
- Reduce database query load
- Store message queues for async tasks
- Support cache invalidation on updates

**Integration Points**:
- CacheManager coordinates all cache operations
- Event-driven invalidation (when score/camera updated)
- Repositories check Redis before querying database

**Deployment**:
```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 3
```

---

### Component 3: Filesystem Storage for Images

**Purpose**: Store raw and annotated images with 90-day retention and quota management

**Path Structure**:
```
/storage/
├── raw/
│   └── session_{session_id}/
│       ├── end_1_arrow_1.jpg
│       ├── end_1_arrow_2.jpg
│       └── end_1_arrow_3.jpg
├── annotated/
│   └── session_{session_id}/
│       ├── end_1_arrow_1_annotated.jpg
│       ├── end_1_arrow_2_annotated.jpg
│       └── end_1_arrow_3_annotated.jpg
└── archives/
    └── session_{session_id}_20260425.tar.gz
```

**Responsibilities**:
- Store raw JPEG images (1-5 MB per image)
- Store annotated images with ring/arrow overlays
- Archive old images (90+ days) to tar.gz
- Monitor quota usage and alert when approaching 10 GB limit
- Clean up archived files if quota exceeded

**Configuration**:
- Quota: 10 GB (hard limit)
- Warning threshold: 8 GB (80%)
- Retention: 90 days before archival
- Compression: JPEG quality 70 (trade quality for speed)
- Cleanup: Daily automated task

**Integration Points**:
- ScoringService writes raw/annotated images
- ArchiveService monitors quota and cleans up
- ReportService reads images for PDF generation
- StorageManager tracks usage, publishes alerts

**Health Monitoring**:
- Daily cleanup task logs usage
- Quota alerts published to WebSocket (broadcast to UIs)
- Critical alert if quota exceeded

---

### Component 4: ThreadPool for Multi-Camera Parallelism

**Purpose**: Parallelize image processing across multiple camera lanes

**Configuration**:
- **Type**: concurrent.futures.ThreadPoolExecutor
- **Initial Size**: 4 workers
- **Max Size**: 8 workers (scales 4→8 if CPU > 80%)
- **Timeout**: 2 seconds per task

**Responsibilities**:
- Execute image capture, preprocessing, ring detection, arrow detection in parallel
- Each thread processes one camera's images independently
- Return results to caller (synchronous API)
- Monitor queue depth, trigger CPU-based scaling if needed

**Integration Points**:
- ScoringService submits tasks to pool
- LoadManager monitors CPU, auto-scales pool size
- Each task result returned to scoring pipeline

**Scaling Logic**:
```python
# Hybrid scaling: 4 base, 8 max
if cpu_percent > 80:
    current_pool_size = min(current_pool_size + 1, 8)
elif cpu_percent < 50:
    current_pool_size = max(current_pool_size - 1, 4)
```

**Deployment**:
```python
# In main.py
from concurrent.futures import ThreadPoolExecutor

image_processor_pool = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="image_processor"
)
```

---

### Component 5: Event Bus for Asynchronous Event Publishing

**Purpose**: Decouple components via event-driven architecture for real-time updates

**Events Published**:
1. **ScoreCalculated**: New score available
   - Payload: `{session_id, archer_id, points, confidence}`
   - Subscribers: WebSocket broadcaster, leaderboard invalidator, audit logger
   
2. **CameraConnected / CameraDisconnected**: Camera status changed
   - Payload: `{camera_id, status}`
   - Subscribers: WebSocket broadcaster, session manager
   
3. **SessionStateChanged**: Session transitioned states
   - Payload: `{session_id, from_state, to_state}`
   - Subscribers: WebSocket broadcaster, audit logger
   
4. **StorageWarning / StorageExceeded**: Quota alerts
   - Payload: `{usage_gb, quota_gb, percent}`
   - Subscribers: WebSocket broadcaster (alert UIs)

**Responsibilities**:
- Publish events when important state changes occur
- Route events to registered subscribers
- Support both synchronous and asynchronous subscribers
- Log all events for debugging

**Integration Points**:
- Services publish events (ScoringService, CameraService, etc.)
- WebSocketManager subscribes to all events
- Cache invalidators subscribe to data-change events
- Audit logger subscribes to sensitive operations

**Implementation**:
```python
# event_bus.py
class EventBus:
    def __init__(self):
        self.subscribers = defaultdict(list)  # event_type -> [handlers]
    
    def subscribe(self, event_type: str, handler):
        """Register event handler"""
        self.subscribers[event_type].append(handler)
    
    async def publish(self, event_type: str, data: dict):
        """Publish event to all subscribers"""
        for handler in self.subscribers[event_type]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(data)
                else:
                    handler(data)
            except Exception as e:
                logger.error(f"Event handler error", event_type=event_type, error=str(e))

event_bus = EventBus()
```

---

### Component 6: Cache Manager with TTL-Based Invalidation

**Purpose**: Coordinate caching of frequently-accessed data to reduce database load

**Cached Data Types**:
1. **Cameras**: All connected cameras (TTL 5 min)
2. **Sessions**: Session details (TTL 1 min)
3. **Leaderboards**: Aggregated scores by archer (TTL 1 min)

**Invalidation Triggers**:
- Camera status changed → Invalidate cameras
- Score calculated → Invalidate leaderboards
- Session state changed → Invalidate sessions

**Responsibilities**:
- Provide get() interface with fallback to database
- Implement TTL-based expiration
- Coordinate event-driven invalidation
- Track cache hit rates for monitoring

**Integration Points**:
- API endpoints use cache_manager.get() instead of direct DB queries
- Event bus handlers call cache_manager.invalidate()
- Redis backing for distributed caching

---

### Component 7: Load Manager for Adaptive Resource Scaling

**Purpose**: Monitor system load and auto-scale resources to maintain performance

**Monitored Metrics**:
- CPU usage (%)
- Memory usage (%)
- Active database connections
- WebSocket connection count
- Request queue depth

**Scaling Actions**:
- ThreadPool: Scale 4 → 8 if CPU > 80%
- Connection pool: Scale 5-20 based on utilization
- Request queueing: Queue requests if overloaded

**Responsibilities**:
- Monitor system metrics every 10 seconds
- Calculate scaling decisions based on thresholds
- Apply scaling changes (adjust pool sizes, etc.)
- Log scaling events for debugging

**Configuration**:
```python
CPU_THRESHOLD = 80  # %
MEMORY_THRESHOLD = 85  # %
THREADPOOL_MIN = 4
THREADPOOL_MAX = 8
CONNECTION_POOL_MIN = 5
CONNECTION_POOL_MAX = 20
SCALE_COOLDOWN = 60  # seconds between scaling decisions
```

---

### Component 8: Structured Logging with Audit Trail

**Purpose**: Provide visibility into system behavior and compliance audit trail

**Log Types**:
1. **Application Logs**: All significant events (scores, errors, warnings)
2. **Audit Logs**: Sensitive operations (overrides, auth failures, permission denied)
3. **Metrics**: Performance data (latency, throughput, errors)

**Logging Infrastructure**:
- **structlog**: Structured JSON logging to stdout
- **PostgreSQL**: Audit logs stored in audit_logs table
- **Prometheus**: Metrics endpoint for monitoring

**Log Destinations**:
```
Application logs (stdout)
  ↓
Container orchestration captures logs
  ↓
(Optional) Log aggregation system (ELK, Datadog)

Audit logs (database)
  ↓
Query for compliance/investigation

Metrics (Prometheus format)
  ↓
Prometheus scrapes endpoint
  ↓
(Optional) Grafana dashboards
```

**Responsibilities**:
- Log all state-changing operations
- Record user actions with context
- Track performance metrics
- Support audit investigations

---

### Component 9: WebSocket Manager for Real-Time Communication

**Purpose**: Broadcast real-time events to connected clients

**Events Broadcast**:
- Score calculated (display new result)
- Leaderboard updated (refresh rankings)
- Camera status changed (display red/green indicator)
- Session state changed (enable/disable scoring buttons)
- Storage warning (alert if quota high)

**Responsibilities**:
- Accept WebSocket connections from clients
- Track active subscriptions per session
- Broadcast events to all subscribers
- Handle disconnections (30-second grace period)
- Buffer events if client temporarily disconnected

**Integration Points**:
- Clients connect: `WebSocket /ws/session/{session_id}`
- EventBus publishes events
- WebSocketManager broadcasts to all subscribers
- Clients receive JSON messages in real-time

---

### Component 10: Health Check Endpoint

**Purpose**: Provide visibility into system health for monitoring and load balancers

**Health Status Levels**:

```python
# health.py
class HealthStatus(Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class HealthChecker:
    async def get_health(self) -> dict:
        """Return health status"""
        return {
            "status": self._overall_status(),
            "timestamp": datetime.utcnow(),
            "components": {
                "database": await self._check_database(),
                "cache": await self._check_cache(),
                "storage": await self._check_storage(),
                "threadpool": await self._check_threadpool()
            }
        }
    
    async def _check_database(self) -> dict:
        """Check database connectivity"""
        try:
            result = db.execute("SELECT 1")
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def _check_cache(self) -> dict:
        """Check Redis connectivity"""
        try:
            redis_client.ping()
            return {"status": "healthy"}
        except Exception as e:
            return {"status": "unhealthy", "error": str(e)}
    
    async def _check_storage(self) -> dict:
        """Check storage quota"""
        usage = storage_manager.get_usage_gb()
        if usage > QUOTA_GB:
            return {"status": "unhealthy", "usage_gb": usage}
        elif usage > (QUOTA_GB * 0.8):
            return {"status": "degraded", "usage_gb": usage}
        else:
            return {"status": "healthy", "usage_gb": usage}

# API endpoint
@app.get("/health")
async def health_check():
    return await health_checker.get_health()
```

**Usage**:
- Kubernetes readiness probes (for scaling decisions)
- Load balancer health checks (for routing)
- Monitoring dashboards (for operator visibility)

---

## Component Integration Flows

### Flow 1: Scoring Pipeline

```
1. Client triggers scoring (POST /api/v1/scores)
2. API validates input (Pydantic)
3. AuthService verifies token
4. ScoringService.score_end() called:
   a. Submit image processing to ThreadPool
   b. ThreadPool processes images in parallel (4 max)
   c. Ring detection (Hough + fallback)
   d. Arrow detection (3-method voting + ML fallback)
   e. Calculate score
5. Store score in database (atomic with session update)
6. EventBus publishes ScoreCalculated
7. WebSocketManager broadcasts to clients
8. CacheManager invalidates leaderboard
9. AuditLogger records event
10. Return result to client (< 1 second)
```

---

### Flow 2: Cache Hit / Miss

```
User requests GET /api/v1/cameras

1. API calls cache_manager.get("cameras:all")
2. Cache check:
   a. HIT: Return cached list (< 1ms)
   b. MISS: Query database, store in cache + Redis, return
3. Cache invalidated when:
   a. TTL expires (5 minutes)
   b. Event: CameraStatusChanged (immediate)
   c. Manual call to cache_manager.invalidate("cameras:all")
```

---

### Flow 3: Storage Quota Management

```
Background task (runs daily)
1. Calculate total storage usage
2. If > 90 days old: Archive to tar.gz, delete raw
3. Check quota:
   a. If < 80%: OK
   b. If 80-100%: Publish StorageWarning to UI
   c. If > 100%: Publish StorageExceeded, delete oldest archives
4. Log usage metrics
```

---

### Flow 4: Camera Reconnection

```
Camera disconnected (USB unplugged)

1. Auto-probe detects failure
2. Log warning: "Camera X disconnected"
3. Publish CameraDisconnected event
4. WebSocketManager broadcasts status change
5. Auto-reconnect with backoff:
   a. Retry 1: Wait 30s, attempt connect
   b. Retry 2: Wait 60s, attempt connect
   c. Retry 3: Wait 120s, attempt connect (notify user)
   d. Retry 4: Wait 240s, attempt connect
   e. Retry 5: Wait 300s, attempt connect
   f. Retry 6+: Give up, user must manually reconnect
6. On success: Reset retry count, publish CameraConnected
```

---

## Deployment Architecture

### Single Server Deployment (MVP)

```
┌─────────────────────────────────────────┐
│         Docker Host (Single Server)     │
│  ┌──────────────────────────────────┐   │
│  │  Docker Compose Services:        │   │
│  │                                  │   │
│  │  - api (Uvicorn, 4 workers)     │   │
│  │  - postgres (primary DB)        │   │
│  │  - redis (cache)                │   │
│  │  - (patroni standby optional)   │   │
│  │                                  │   │
│  │  Volumes:                        │   │
│  │  - /storage/ (images)           │   │
│  │  - postgres_data (DB)           │   │
│  │  - redis_data (cache)           │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Multi-Server Deployment (Future Scaling)

```
┌────────────────────────────────────────────────┐
│            Load Balancer (nginx)                │
│            ┌──────────────────┐                │
└────────────────────────────────────────────────┘
      ↓              ↓              ↓
┌──────────┐   ┌──────────┐   ┌──────────┐
│  API #1  │   │  API #2  │   │  API #3  │
│(Uvicorn) │   │(Uvicorn) │   │(Uvicorn) │
└──────────┘   └──────────┘   └──────────┘
      ↓              ↓              ↓
      └──────────────┬──────────────┘
                     ↓
         ┌───────────────────────┐
         │  Shared Postgres DB   │
         │  Primary + Standby    │
         │  (Patroni failover)   │
         └───────────────────────┘
                     ↕
         ┌───────────────────────┐
         │  Shared Redis Cache   │
         │  (multi-server)       │
         └───────────────────────┘
                     ↕
         ┌───────────────────────┐
         │  NFS Storage          │
         │  (/storage/ shared)   │
         └───────────────────────┘
```

---

## Monitoring & Observability

### Key Metrics to Track

| Metric | Source | Alert Threshold |
|---|---|---|
| API latency (p95) | Uvicorn | > 500ms |
| Scoring latency (p95) | ScoringService | > 1.5s |
| Error rate | structlog | > 1% |
| Database connections in use | SQLAlchemy | > 15 (80% pool) |
| Cache hit rate | CacheManager | < 50% (needs tuning) |
| Storage usage | StorageManager | > 8GB (80%) |
| ThreadPool queue depth | LoadManager | > 10 tasks |
| Active WebSocket connections | WebSocketManager | > 100 |
| Audit log volume | AuditLogger | Monitor for trends |

### Monitoring Setup

```yaml
# docker-compose.yml additions for monitoring
services:
  prometheus:
    image: prom/prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"
  
  grafana:
    image: grafana/grafana
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
```

---

## Summary: 10 Logical Components

| # | Component | Purpose | Scaling |
|---|---|---|---|
| 1 | PostgreSQL + Patroni | Data store with failover | Shared, scales to multi-server |
| 2 | Redis Cache | Hot data caching | Distributed, single instance MVP |
| 3 | Filesystem Storage | Image persistence | NFS for multi-server, local MVP |
| 4 | ThreadPool | Image processing parallelism | Adaptive 4-8 workers |
| 5 | EventBus | Async event publishing | In-process, scales with service |
| 6 | CacheManager | Coordinate caching | Application-level, Redis-backed |
| 7 | LoadManager | Auto-scaling | Monitors metrics, adjusts resources |
| 8 | Structured Logging | Audit trail + debugging | Database + stdout, aggregates optionally |
| 9 | WebSocketManager | Real-time communication | In-process, scales with connections |
| 10 | HealthChecker | System health visibility | Endpoint, used by monitoring |

