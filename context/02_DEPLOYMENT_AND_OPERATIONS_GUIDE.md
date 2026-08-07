# SPL-3: Deployment & Operations Guide Master Reference

---

## 1. Prerequisites & Environment Architecture

### Supported Platform Setup
- **Operating System**: Linux (Ubuntu 22.04 LTS), macOS, or Windows 10/11 with Docker Desktop.
- **Docker Engine**: Version 20.10+
- **Docker Compose**: Version 2.0+ (`docker compose` command syntax)
- **Python**: Version 3.11+ (if running without containers)
- **PostgreSQL**: Version 15+
- **Redis**: Version 7+

---

## 2. Docker Architecture & Container Specifications

The multi-container production stack is orchestrated via [docker-compose.yml](file:///c:/Users/BS01318/OneDrive%20-%20Brain%20Station%2023/Documents/GitHub/SPL-3/docker-compose.yml):

```yaml
version: '3.9'

services:
  api:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: archery_scoring_api
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://archery:archery_pass@db:5432/archery_db
      - REDIS_URL=redis://cache:6379/0
      - ENVIRONMENT=development
      - LOG_LEVEL=INFO
      - API_WORKERS=2
      - JWT_SECRET=${JWT_SECRET:-dev-secret-key-change-in-production}
      - STORAGE_PATH=/storage
    volumes:
      - ./src:/app/src
      - ./scripts:/app/scripts
      - ./tests:/app/tests
      - ./alembic:/app/alembic
      - ./runs:/app/runs
      - storage_volume:/storage
    depends_on:
      db:
        condition: service_healthy
      cache:
        condition: service_healthy
    networks:
      - archery_network

  db:
    image: postgres:15-alpine
    container_name: archery_scoring_db
    environment:
      - POSTGRES_USER=archery
      - POSTGRES_PASSWORD=archery_pass
      - POSTGRES_DB=archery_db
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U archery -d archery_db"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - archery_network

  cache:
    image: redis:7-alpine
    container_name: archery_scoring_cache
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - archery_network
```

### Key Docker Configurations

#### 1. Context Optimization (`.dockerignore`)
Prevents sending heavy unneeded directories (`Data.zip`, raw node_modules, `.venv`, `.git`) to the Docker build daemon:
```text
.git
.venv
__pycache__
*.pyc
.pytest_cache
.coverage
frontend/node_modules
frontend/.next
frontend/dist
Data.zip
storage/
.env
```

#### 2. CPU PyTorch Layer Pre-Installation (`Dockerfile`)
Pre-installs lightweight CPU PyTorch (`torch+cpu` / `torchvision+cpu`) to avoid pulling 1.5GB of unneeded CUDA GPU packages:
```dockerfile
# Pre-install CPU PyTorch wheels
RUN /build/.venv/bin/pip install --default-timeout=600 torch torchvision --index-url https://download.pytorch.org/whl/cpu
```

#### 3. Model Weights Volume Mount (`docker-compose.yml`)
Mounts `./runs:/app/runs` so newly trained YOLO11 model weights (`best.pt`) on the host are automatically visible inside the running API container.

---

## 3. Operational Commands & Lifecycle Management

### Container Operations

1. **Build and Start Container Stack**:
   ```powershell
   docker compose up -d --build
   ```

2. **Check Running Containers & Health Status**:
   ```powershell
   docker ps
   ```
   **Expected Output**:
   ```text
   NAMES                   STATUS                   PORTS
   archery_scoring_api     Up 2 minutes (healthy)   0.0.0.0:8000->8000/tcp
   archery_scoring_db      Up 2 minutes (healthy)   0.0.0.0:5432->5432/tcp
   archery_scoring_cache   Up 2 minutes (healthy)   0.0.0.0:6379->6379/tcp
   ```

3. **Inspect Live API Container Logs**:
   ```powershell
   docker logs archery_scoring_api --tail 50 -f
   ```

4. **Restart Container Stack**:
   ```powershell
   docker compose down; docker compose up -d
   ```

5. **Stop and Clean Containers & Volumes**:
   ```powershell
   docker compose down -v
   ```

---

## 4. System Health Checks & Telemetry

### HTTP API Health Check
- **Endpoint**: `GET http://localhost:8000/api/health`
- **Verification Command**:
  ```powershell
  python -c "import requests; r = requests.get('http://localhost:8000/api/health'); print(r.status_code, r.json())"
  ```
- **Expected Response (`200 OK`)**:
  ```json
  {
    "status": "ok",
    "timestamp": "2026-08-07T09:54:26.986307",
    "components": {
      "database": { "status": "ok", "message": "Database connected" },
      "cache": { "status": "ok", "message": "Cache connected" },
      "storage": { "status": "ok", "used_gb": 0.0, "quota_gb": 10 },
      "threadpool": { "status": "ok", "active_workers": 0, "max_workers": 4 }
    }
  }
  ```
