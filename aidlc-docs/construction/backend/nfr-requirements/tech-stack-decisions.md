# Backend Unit — Tech Stack Decisions

**Project**: Automated Archery Scoring System  
**Unit**: Backend  
**Date**: 2026-05-25  

---

## Overview

This document documents technology stack decisions derived from NFR Requirements and justifies selections based on project constraints and requirements.

---

## Core Technology Stack (LOCKED from Functional Design)

| Component | Technology | Version | Rationale |
|---|---|---|---|
| **Language** | Python | 3.11+ | Rapid development, strong image processing library support (OpenCV, NumPy) |
| **Web Framework** | FastAPI | 0.110+ | Modern async support, auto-generated API docs, excellent performance |
| **Database** | PostgreSQL | 15+ | ACID transactions, row-level locking (required for concurrency), JSON support, full-text search |
| **Image Processing** | OpenCV | 4.8+ | Gold standard for computer vision, Hough Circle/Contour detection, multi-platform |
| **Dependency Mgmt** | Poetry | Latest | Lock file enforcement, deterministic builds, isolated environments |

---

## NFR-Driven Stack Decisions

### Decision 1: Web Server & Async Runtime

**Requirement**: < 1s scoring latency, < 500ms API response time, 4-6 concurrent users

**Options Considered**:
- A) Uvicorn (async ASGI)
- B) Gunicorn (sync WSGI)
- C) Hypercorn (async ASGI, alternative)

**Decision**: **Uvicorn (async ASGI)**

**Rationale**:
- FastAPI with Uvicorn handles 4-6 concurrent users with minimal overhead
- Async I/O (image reads, database queries) enables better latency
- Single-threaded event loop with worker threads for blocking operations
- Configuration: 4 workers (one per CPU core on typical 4-core VM)
- Sufficient for MVP (scales to multi-server later if needed)

**Configuration**:
```yaml
# uvicorn_config.py
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
bind = "0.0.0.0:8000"
timeout = 120  # 2 min timeout for long-running scoring
```

---

### Decision 2: Image Processing Parallelism

**Requirement**: 4-6 concurrent users, multi-lane scoring via ThreadPool

**Options Considered**:
- A) Sequential processing (one image at a time)
- B) ProcessPool (separate process per image)
- C) ThreadPool (shared memory, lower overhead)

**Decision**: **ThreadPool(max_workers=4) with row-level database locks**

**Rationale**:
- Image processing is CPU-bound (Hough Circle, contour analysis)
- ThreadPool(4) allows up to 4 concurrent image processing threads
- ThreadPool workers shared across requests (reusable, low overhead)
- Database row locks serialize updates (pessimistic locking, simple)
- GIL release during OpenCV calls (native C code)
- Configuration: `max_workers=4` (tunable, doesn't block main FastAPI loop)

**Implementation**:
```python
# Backend services.py
from concurrent.futures import ThreadPoolExecutor

class ScoringService:
    def __init__(self):
        self.image_processor_pool = ThreadPoolExecutor(max_workers=4)
    
    def score_end(self, session_id, archer_id, camera_id):
        # Submit image processing to thread pool
        future = self.image_processor_pool.submit(
            self._process_images,
            session_id, archer_id, camera_id
        )
        # Wait for result (synchronous API)
        result = future.result(timeout=1.5)
        return result
```

---

### Decision 3: Logging & Observability

**Requirement**: Application metrics (API latency, error rates, throughput), audit logging

**Options Considered**:
- A) Print statements (no structure)
- B) Standard logging (hard to parse)
- C) Structured logging (JSON, queryable)

**Decision**: **structlog (structured logging) + Prometheus metrics**

**Rationale**:
- Structured JSON output (key=value pairs)
- Human-readable in development, machine-parseable in production
- Audit trail: score overrides, user actions, errors (all events logged)
- Metrics: Custom counters and gauges for API latency, scoring throughput
- Future integration: ELK stack, Datadog, or similar monitoring platforms

**Configuration**:
```python
# logging_config.py
import structlog
import logging

structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger()

# Usage
logger.info("score_calculated", 
    session_id=session_id, 
    archer_id=archer_id, 
    points=points, 
    confidence=confidence
)

# Metrics
from prometheus_client import Counter, Histogram

scoring_counter = Counter('scoring_total', 'Total scores processed')
api_latency = Histogram('api_latency_seconds', 'API response latency')
```

---

### Decision 4: Database Connection Pooling

**Requirement**: 4-6 concurrent users, multi-session isolation, row-level locking

**Options Considered**:
- A) Raw psycopg2 (no pooling)
- B) SQLAlchemy with built-in pooling
- C) pgBouncer (external connection pooler)

**Decision**: **SQLAlchemy QueuePool with built-in pooling**

**Rationale**:
- SQLAlchemy's QueuePool handles connection lifecycle
- Pool size: 10 connections (sufficient for 4-6 users with headroom)
- Max overflow: 5 (temporary connections beyond pool)
- Timeout: 30s (acquire connection within 30s or fail)
- Handles concurrent scoring transactions (row locks)

**Configuration**:
```python
# database.py
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    f"postgresql://{user}:{password}@{host}:{port}/{database}",
    poolclass=QueuePool,
    pool_size=10,
    max_overflow=5,
    pool_timeout=30,
    pool_recycle=3600,  # Recycle connections every hour
    echo=False  # Set to True for debugging
)
```

---

### Decision 5: Real-Time Communication (WebSocket)

**Requirement**: < 500ms event latency, live score updates

**Options Considered**:
- A) Native browser WebSocket API (client handles reconnection)
- B) Socket.io (auto-reconnection, fallback)
- C) Server-Sent Events (one-way, less suitable for scoring updates)

**Decision**: **Native browser WebSocket API (FastAPI integration)**

**Rationale**:
- FastAPI has built-in WebSocket support
- Native API: no external library dependency
- Client reconnection: Implement in frontend (recommended practice)
- Low overhead: Minimal memory footprint per connection
- Scalable: Can handle many concurrent connections on single server
- Fire-and-forget: No message queueing (acceptable for soft real-time)

**Implementation**:
```python
# api/websocket_handler.py
from fastapi import WebSocket
from starlette.websocket import WebSocketState

class WebSocketManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    async def broadcast(self, message: dict):
        """Broadcast to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                disconnected.append(connection)
        
        # Remove disconnected clients
        for conn in disconnected:
            self.active_connections.remove(conn)

# Usage
manager = WebSocketManager()

@app.websocket("/ws/session/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages
    except:
        manager.active_connections.remove(websocket)
```

---

### Decision 6: Image Storage

**Requirement**: Filesystem storage (/storage/raw/), 90-day retention, 10 GB quota

**Options Considered**:
- A) Filesystem (local disk)
- B) Cloud object storage (S3, GCS)
- C) Database BLOB (excluded in functional design)

**Decision**: **Local Filesystem**

**Rationale**:
- Raw images: 1-5 MB per score, JPEG format
- Session volume: 300-3000 MB per session
- 10 GB quota: Manageable on local storage
- Access pattern: Sequential read (low random access)
- Cost: No cloud storage fees
- Path structure: `/storage/raw/session_{id}/end_{num}_arrow_{num}.jpg`

**Retention Policy**:
```python
# storage_manager.py
import os
from datetime import datetime, timedelta

STORAGE_ROOT = "/storage"
RETENTION_DAYS = 90
QUOTA_GB = 10

def cleanup_old_images():
    """Archive and delete images older than 90 days"""
    cutoff_date = datetime.now() - timedelta(days=RETENTION_DAYS)
    
    for session_dir in os.listdir(f"{STORAGE_ROOT}/raw"):
        session_path = f"{STORAGE_ROOT}/raw/{session_dir}"
        for image_file in os.listdir(session_path):
            file_path = os.path.join(session_path, image_file)
            file_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            
            if file_time < cutoff_date:
                # Archive to tar.gz
                archive_image(file_path)
                # Delete original
                os.remove(file_path)

def get_storage_usage_gb():
    """Get total storage usage in GB"""
    total_bytes = 0
    for dirpath, dirnames, filenames in os.walk(STORAGE_ROOT):
        for filename in filenames:
            total_bytes += os.path.getsize(os.path.join(dirpath, filename))
    return total_bytes / (1024**3)

def check_quota_alert():
    """Alert if usage exceeds 80% of quota"""
    usage = get_storage_usage_gb()
    if usage > (QUOTA_GB * 0.8):
        logger.warning("storage_quota_warning", usage_gb=usage, quota_gb=QUOTA_GB)
```

---

### Decision 7: Authentication & Secrets

**Requirement**: JWT tokens, secure password hashing, no plaintext secrets

**Options Considered**:
- A) JWT (stateless, scalable)
- B) Session cookies (stateful, requires session store)

**Decision**: **JWT tokens + python-jose + passlib + bcrypt**

**Rationale**:
- JWT: Stateless, user-scoped, 8-hour expiration
- Passlib + bcrypt: Industry-standard password hashing
- httpOnly cookies: Protect against XSS attacks
- python-jose: Cryptographic library for JWT signing

**Libraries**:
```python
# auth_service.py
from passlib.context import CryptContext
from datetime import datetime, timedelta
from jose import JWTError, jwt

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed: str) -> bool:
        return pwd_context.verify(plain_password, hashed)
    
    def create_access_token(self, user_id: str, role: str, expires_delta: timedelta = None):
        if expires_delta is None:
            expires_delta = timedelta(hours=8)
        
        expire = datetime.utcnow() + expires_delta
        to_encode = {"sub": user_id, "role": role, "exp": expire}
        encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
        return encoded_jwt
    
    def verify_token(self, token: str):
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            user_id: str = payload.get("sub")
            role: str = payload.get("role")
            return user_id, role
        except JWTError:
            return None, None
```

---

### Decision 8: Encryption (TLS)

**Requirement**: TLS for all HTTP/WebSocket, password hashing, no full-disk encryption

**Options Considered**:
- A) TLS 1.2+ (minimum)
- B) TLS 1.3 (preferred, faster, more secure)
- C) HTTP (no encryption, unsafe)

**Decision**: **TLS 1.2+ (preferably 1.3)**

**Rationale**:
- All endpoints: HTTPS (TLS 1.2+)
- WebSocket: wss:// (encrypted)
- Certificate: Self-signed for development, Let's Encrypt for production
- HSTS: Strict-Transport-Security header enforces TLS

**Configuration**:
```python
# main.py (FastAPI app)
from fastapi import FastAPI
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI()

# Enforce TLS in production
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*.example.com", "example.com"]
)

# Add HSTS header
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    return response

# SSL/TLS certificate configuration (via environment variable)
import os
SSL_CERT = os.getenv("SSL_CERT_PATH")
SSL_KEY = os.getenv("SSL_KEY_PATH")
```

---

### Decision 9: Database Failover (Warm Standby)

**Requirement**: Warm standby with automatic failover (streaming replication)

**Options Considered**:
- A) Single PostgreSQL instance (no failover)
- B) Warm standby with manual failover
- C) Warm standby with automatic failover (via Patroni/pgBouncer)

**Decision**: **Warm standby with automatic failover (Patroni)**

**Rationale**:
- Patroni: Manages PostgreSQL with automatic failover
- Streaming replication: Standby receives WAL logs from primary
- Automatic detection: Primary failure detected within 30s
- Failover time: < 5 minutes (cluster reconfiguration)
- RTO: < 5 minutes, RPO: < 1 minute

**Deployment**:
```yaml
# docker-compose.yml
services:
  postgres-primary:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_primary_data:/var/lib/postgresql/data
  
  postgres-standby:
    image: postgres:15
    environment:
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    depends_on:
      - postgres-primary
    command: |
      bash -c "
        pg_basebackup -h postgres-primary -D /var/lib/postgresql/data -U postgres -v -P -W
        echo 'standby_mode = on' >> /var/lib/postgresql/data/recovery.conf
        /usr/local/bin/docker-entrypoint.sh postgres
      "
    volumes:
      - postgres_standby_data:/var/lib/postgresql/data
  
  patroni-primary:
    image: patroni:latest  # Or use Patroni container
    environment:
      PATRONI_POSTGRESQL_PGPASS: /tmp/pgpass
      PATRONI_POSTGRESQL_DATA_DIR: /var/lib/postgresql/data
      PATRONI_POSTGRESQL_BIN_DIR: /usr/lib/postgresql/15/bin
```

---

### Decision 10: Monitoring & Metrics

**Requirement**: Application metrics (latency, errors, throughput), structured logs

**Stack**:
- **Logging**: structlog (structured JSON)
- **Metrics**: Prometheus-compatible format
- **Monitoring**: (Optional) Prometheus + Grafana

**Configuration**:
```python
# metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Counters
scoring_total = Counter('scoring_total', 'Total scores processed', ['status'])
api_requests = Counter('api_requests_total', 'Total API requests', ['method', 'endpoint', 'status'])
auth_failures = Counter('auth_failures_total', 'Total auth failures', ['reason'])

# Histograms
scoring_latency = Histogram('scoring_latency_seconds', 'Scoring latency', buckets=(0.2, 0.5, 1.0, 1.5, 2.0))
api_latency = Histogram('api_latency_seconds', 'API latency', buckets=(0.05, 0.1, 0.5, 1.0))

# Gauges
active_connections = Gauge('active_connections', 'Active WebSocket connections')
storage_usage_bytes = Gauge('storage_usage_bytes', 'Storage usage in bytes')
db_pool_checkedout = Gauge('db_pool_checkedout', 'Database connections checked out')
```

---

### Decision 11: CI/CD Pipeline

**Requirement**: Basic CI/CD (tests on push, manual deploy approval)

**Stack**:
- **VCS**: GitHub
- **CI**: GitHub Actions
- **Build**: Docker
- **Deploy**: Manual (scripts or UI)

**Workflow**:
```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

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
          - 5432:8432
    
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install poetry
      - run: poetry install
      - run: poetry run pytest --cov
      - run: poetry run flake8 src/
      - run: poetry run mypy src/
```

---

### Decision 12: Deployment (Docker)

**Requirement**: Docker containers, single server initially, designed for multi-server

**Approach**: Docker Compose for local development and single-server deployment

**Structure**:
```yaml
# docker-compose.yml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://user:password@postgres:5432/archery
      SECRET_KEY: ${SECRET_KEY}
    depends_on:
      - postgres
    volumes:
      - ./storage:/storage
    networks:
      - app-network

  postgres:
    image: postgres:15
    environment:
      POSTGRES_USER: archery_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
      POSTGRES_DB: archery
    volumes:
      - postgres_data:/var/lib/postgresql/data
    networks:
      - app-network

volumes:
  postgres_data:

networks:
  app-network:
```

---

## Summary: 12 Technology Decisions

| Decision | Technology | Rationale | Trade-off |
|---|---|---|---|
| Web Server | Uvicorn (async ASGI) | Handles 4-6 users, low latency | Single process, scales via multi-server |
| Parallelism | ThreadPool(4) | CPU-bound image processing, low overhead | GIL limits, fallback to ProcessPool if needed |
| Logging | structlog + Prometheus | Structured logs, queryable metrics | Adds logging overhead (acceptable) |
| Database Pooling | SQLAlchemy QueuePool | Connection lifecycle, row locks | Built-in vs external (simpler) |
| WebSocket | Native API | No external lib, built-in FastAPI | Manual reconnection (acceptable) |
| Images | Local filesystem | Simple, 10GB manageable | Not cloud-native, ~migration if needed |
| Auth | JWT + passlib/bcrypt | Stateless, scalable, secure | No session store (acceptable) |
| Encryption | TLS 1.2+ | Industry standard | Cert management (Let's Encrypt handles) |
| DB Failover | Patroni + streaming replication | Automatic failover, < 5m RTO | Added complexity (acceptable for availability) |
| Monitoring | structlog + Prometheus | Metrics, structured logs | Integration required (future) |
| CI/CD | GitHub Actions | Built-in, free for public repos | Limited to GitHub workflows |
| Deployment | Docker Compose | Single server, portable | Not Kubernetes (simpler for MVP) |

---

## Migration Path (Future Scaling)

If system needs to scale beyond single server:

1. **Load Balancing**: Add nginx (round-robin across API replicas)
2. **Database**: Dedicated PostgreSQL server (with Patroni failover)
3. **Storage**: Migrate to NFS or S3 (if on cloud)
4. **Monitoring**: Integrate Prometheus + Grafana
5. **Orchestration**: Optional Kubernetes (if 10+ servers)

All decisions support this migration path with minimal code changes.

