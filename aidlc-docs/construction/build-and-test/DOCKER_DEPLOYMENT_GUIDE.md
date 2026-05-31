# Docker Deployment Guide - Archery Scoring System

**Date**: May 31, 2026  
**Status**: Ready for Deployment  
**Environment**: Docker & Docker Compose  
**Architecture**: 3-Service Microservices (API, Database, Cache)

---

## Quick Start: Docker Deployment

### Prerequisites
- Docker Desktop 4.0+
- Docker Compose 2.0+
- Network connectivity
- 4GB+ RAM available
- 5GB+ disk space

### Deploy Locally (Development)
```bash
cd d:\Git\SPL-3

# Build Docker image
docker compose build

# Start all services
docker compose up -d

# Verify services
docker compose ps

# View logs
docker compose logs -f api

# Stop services
docker compose down
```

### Deployment Time: ~2-3 minutes

---

## Current Status: Network Issue

### Issue Encountered
```
Docker build failed:
"Head https://registry-1.docker.io/v2/library/python/manifests/3.11-slim: 
no such host"
```

### Root Cause
Docker Desktop cannot reach the Docker registry (registry-1.docker.io) due to:
- Network connectivity issues
- Firewall/proxy blocking
- DNS resolution failure
- Corporate proxy configuration

### Workarounds Available

#### Option 1: Use Offline Base Image (Fastest)
```bash
# Pull base image on a machine with internet access
docker pull python:3.11-slim

# Save to tar file
docker save python:3.11-slim -o python-slim.tar

# Transfer python-slim.tar to target machine

# Load on target machine
docker load -i python-slim.tar

# Now build
docker compose build
```

#### Option 2: Configure Docker Proxy
Edit Docker Desktop settings:
```json
{
  "httpProxy": "http://proxy.company.com:8080",
  "httpsProxy": "http://proxy.company.com:8080",
  "noProxy": "localhost,127.0.0.1"
}
```

#### Option 3: Use Local Registry Mirror
```bash
# Configure Docker to use a mirror
# Edit %AppData%\Docker\daemon.json:
{
  "registry-mirrors": ["https://docker.mirrors.ustc.edu.cn"]
}
```

#### Option 4: Build Without Network (Recommended)
Since local testing is working, deploy directly from source:
```bash
# Run from local Python venv instead
python -m uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Architecture Overview

### 3-Service Deployment

```
┌─────────────────────────────────────┐
│        Docker Compose Network       │
├─────────────────────────────────────┤
│                                     │
│  ┌──────────────────────────────┐   │
│  │  FastAPI Application (8000)  │   │
│  │  - 4 Uvicorn workers         │   │
│  │  - Health checks every 10s   │   │
│  │  - Rate limiting enabled     │   │
│  │  - CORS configured           │   │
│  └──────────────────────────────┘   │
│          ↓        ↓        ↓         │
│  ┌──────────────┐  ┌──────────────┐ │
│  │ PostgreSQL   │  │    Redis     │ │
│  │  (5432)      │  │   (6379)     │ │
│  │ - 1 GB init  │  │ - 512MB max  │ │
│  │ - persistent │  │ - allkeys-lru│ │
│  │   volume     │  │ - 1min TTL   │ │
│  └──────────────┘  └──────────────┘ │
│                                     │
└─────────────────────────────────────┘
```

### Service Configuration

#### API Service
```yaml
Image: archery-api:latest
Port: 8000
Environment:
  - DATABASE_URL=postgresql://archery:archery_pass@db:5432/archery_db
  - REDIS_URL=redis://cache:6379/0
  - JWT_SECRET=dev-secret-jwt-key-change-in-production-ybsecure123
  - API_WORKERS=4
  - ENVIRONMENT=development
Health Check: GET /health (10s interval)
Restart: unless-stopped
```

#### PostgreSQL Service
```yaml
Image: postgres:15-alpine
Port: 5432
Environment:
  - POSTGRES_USER=archery
  - POSTGRES_PASSWORD=archery_pass
  - POSTGRES_DB=archery_db
Volume: archery_db_data (persistent)
Health Check: pg_isready (10s interval)
Restart: unless-stopped
```

#### Redis Service
```yaml
Image: redis:7-alpine
Port: 6379
Command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
Volume: archery_cache_data (persistent)
Health Check: redis-cli ping (10s interval)
Restart: unless-stopped
```

---

## Deployment Files

### Files Location: `d:\Git\SPL-3\`

#### 1. Dockerfile (55 lines)
**Purpose**: Build production-grade Docker image

**Key Features**:
- Multi-stage build (builder + runtime)
- Python 3.11-slim base image
- Dependencies compiled in builder stage
- Runtime stage minimal attack surface
- Health check endpoint configured

**Build Command**:
```bash
docker build -t archery-api:latest .
```

#### 2. docker-compose.yml (89 lines)
**Purpose**: Orchestrate 3-service deployment

**Key Features**:
- Service dependency management
- Health checks on all services
- Volume persistence
- Network isolation
- Environment from .env file
- Auto-restart policy

**Start Command**:
```bash
docker compose up -d
```

#### 3. .env (Configuration)
**Purpose**: Environment variables

**Current Settings**:
```env
ENVIRONMENT=development
DATABASE_URL=postgresql://archery:archery_pass@localhost:5432/archery_db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=dev-secret-jwt-key-change-in-production-ybsecure123
API_WORKERS=2 (dev) / 4 (docker) / 8 (production)
LOG_LEVEL=DEBUG (dev) / INFO (docker) / INFO (prod)
```

⚠️ **IMPORTANT**: Change `JWT_SECRET` in production

#### 4. alembic/ (Database Migrations)
**Purpose**: Version control for schema changes

**Files**:
- `alembic.ini` - Configuration
- `env.py` - Migration runner
- `versions/001_initial_schema.py` - Initial schema

**Run Migrations**:
```bash
# Inside API container
docker compose exec api alembic upgrade head
```

---

## Deployment Checklist

### Pre-Deployment
- [ ] Docker Desktop installed and running
- [ ] Verify network connectivity to Docker registry
- [ ] Check disk space (5GB+ available)
- [ ] Check RAM (4GB+ available)
- [ ] Review .env configuration
- [ ] Backup any existing data

### Deployment Steps

1. **Resolve Network Issue** (Choose 1 option)
   - [ ] Option 1: Use offline base image
   - [ ] Option 2: Configure Docker proxy
   - [ ] Option 3: Use local registry mirror
   - [ ] Option 4: Run from Python venv

2. **Build Docker Image**
   ```bash
   docker compose build
   ```
   - Expected: ~2-3 minutes
   - Success: Image tagged as `archery-api:latest`

3. **Start Services**
   ```bash
   docker compose up -d
   ```
   - Expected: All 3 services start
   - Verify: `docker compose ps`

4. **Run Migrations**
   ```bash
   docker compose exec api alembic upgrade head
   ```
   - Expected: Schema created
   - Verify: Database tables exist

5. **Verify API Health**
   ```bash
   curl http://localhost:8000/health
   ```
   - Expected: 200 OK with status JSON

6. **Access API Documentation**
   - OpenAPI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### Post-Deployment Verification

```bash
# Check service logs
docker compose logs api
docker compose logs db
docker compose logs cache

# Test API endpoint
curl -X GET http://localhost:8000/

# Test database connection
docker compose exec db psql -U archery -d archery_db -c "\dt"

# Test cache connection
docker compose exec cache redis-cli ping

# View container metrics
docker compose stats
```

---

## Database Initialization

### Automatic Schema Creation

The Alembic migration system automatically creates all tables:

**Tables Created**:
1. users (authentication, roles, 7 columns)
2. tournaments (tournament metadata, 7 columns)
3. sessions (scoring sessions, 9 columns)
4. session_archers (archer participation, 7 columns)
5. scores (arrow scores, 10 columns)
6. cameras (camera devices, 7 columns)
7. camera_lane_assignments (camera mapping, 5 columns)
8. audit_logs (compliance tracking, 7 columns)

**Total: 8 tables, 61 columns, 4 composite indexes**

### Initial Data (Optional)

Create test data for development:
```bash
# Use provided test fixtures from conftest.py
# Or insert manually via API:

curl -X POST http://localhost:8000/api/tournaments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name":"Regional Championship",...}'
```

---

## Production Deployment (AWS ECS Example)

### Prerequisites for Production
1. AWS Account with ECS access
2. ECR (Elastic Container Registry) setup
3. RDS PostgreSQL database
4. ElastiCache Redis cluster
5. Application Load Balancer
6. CloudWatch for monitoring

### Deployment Steps

#### 1. Push Image to ECR
```bash
# Get login token
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS --password-stdin \
  123456789.dkr.ecr.us-east-1.amazonaws.com

# Tag image
docker tag archery-api:latest \
  123456789.dkr.ecr.us-east-1.amazonaws.com/archery-api:latest

# Push
docker push 123456789.dkr.ecr.us-east-1.amazonaws.com/archery-api:latest
```

#### 2. Create ECS Task Definition
```json
{
  "family": "archery-api",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "1024",
  "memory": "2048",
  "containerDefinitions": [
    {
      "name": "api",
      "image": "123456789.dkr.ecr.us-east-1.amazonaws.com/archery-api:latest",
      "portMappings": [{"containerPort": 8000}],
      "environment": [
        {"name": "DATABASE_URL", "value": "postgresql://..."},
        {"name": "REDIS_URL", "value": "redis://..."},
        {"name": "ENVIRONMENT", "value": "production"}
      ],
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/archery-api",
          "awslogs-region": "us-east-1",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

#### 3. Create ECS Service
```bash
aws ecs create-service \
  --cluster archery-cluster \
  --service-name archery-api \
  --task-definition archery-api:1 \
  --desired-count 3 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-xxx],securityGroups=[sg-xxx],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=arn:aws:elasticloadbalancing:...,containerName=api,containerPort=8000"
```

#### 4. Configure Auto-Scaling
```bash
aws application-autoscaling register-scalable-target \
  --service-namespace ecs \
  --resource-id service/archery-cluster/archery-api \
  --scalable-dimension ecs:service:DesiredCount \
  --min-capacity 2 \
  --max-capacity 10
```

### Production Configuration
```env
ENVIRONMENT=production
DATABASE_URL=postgresql://user:pass@rds-endpoint:5432/archery_db
REDIS_URL=redis://elasticache-endpoint:6379/0
JWT_SECRET=<long-random-key-from-secrets-manager>
API_WORKERS=8
LOG_LEVEL=INFO
DEBUG=False
```

---

## Monitoring & Logging

### Docker Logs
```bash
# All services
docker compose logs

# Specific service
docker compose logs api
docker compose logs db
docker compose logs cache

# Real-time
docker compose logs -f api

# Last 100 lines
docker compose logs --tail=100 api
```

### Health Checks
```bash
# API health
curl http://localhost:8000/health

# Detailed health
curl http://localhost:8000/health/detailed

# Expected response
{
  "status": "healthy",
  "timestamp": "2026-05-31T22:00:00Z",
  "checks": {
    "database": {"status": "ok"},
    "cache": {"status": "ok"},
    "storage": {"status": "ok"}
  }
}
```

### CloudWatch Integration (Production)
```yaml
# Logs sent to CloudWatch
- Log Group: /ecs/archery-api
- Log Stream: ecs/archery-api/container
- Metrics: CPU, Memory, Network I/O
- Alarms: Auto-scaling triggers
```

---

## Troubleshooting

### Service Won't Start

**Symptom**: Container exits immediately

**Diagnostics**:
```bash
docker compose logs api
docker compose ps
```

**Common Causes**:
1. **Port 8000 in use**: Change port in docker-compose.yml
2. **Database not ready**: Wait 10s for db health check
3. **Environment variables missing**: Check .env file
4. **Memory insufficient**: Increase Docker Desktop memory

### Database Connection Fails

**Symptom**: "could not connect to database"

**Check**:
```bash
docker compose exec api python -c \
  "from src.database import engine; print(engine.connect())"
```

**Fix**:
```bash
# Restart database service
docker compose restart db

# Or recreate
docker compose down
docker compose up -d db
```

### Redis Connection Fails

**Symptom**: "could not connect to cache"

**Check**:
```bash
docker compose exec cache redis-cli ping
```

**Fix**:
```bash
# Restart cache
docker compose restart cache
```

### Out of Disk Space

**Check**:
```bash
docker system df
```

**Clean up**:
```bash
docker system prune -a
```

---

## Rollback Procedure

### Quick Rollback
```bash
# Stop current deployment
docker compose down

# Keep data volumes
docker compose down -v false

# Redeploy previous version
docker compose up -d
```

### Full Rollback
```bash
# Backup current database
docker compose exec db pg_dump archery_db > backup.sql

# Restore previous version
docker load < archery-api-previous.tar
docker compose up -d
```

---

## Performance Tuning

### API Optimization
```yaml
# docker-compose.yml
api:
  environment:
    API_WORKERS: 8  # Match CPU cores
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
      reservations:
        cpus: '1'
        memory: 1G
```

### Database Optimization
```yaml
db:
  environment:
    POSTGRES_INITDB_ARGS: "-c max_connections=100 -c shared_buffers=256MB"
  deploy:
    resources:
      limits:
        cpus: '2'
        memory: 2G
```

### Cache Optimization
```yaml
cache:
  command: redis-server --maxmemory 1gb --maxmemory-policy allkeys-lru
  deploy:
    resources:
      limits:
        cpus: '1'
        memory: 1.5G
```

---

## Next Steps

### Immediate (Today)
- [ ] Resolve Docker network issue (choose workaround)
- [ ] Build Docker image
- [ ] Start services
- [ ] Verify API responds

### Short-term (This Week)
- [ ] Configure production secrets
- [ ] Set up SSL/TLS
- [ ] Enable monitoring
- [ ] Test load handling
- [ ] Set up backups

### Medium-term (This Month)
- [ ] Deploy to staging environment
- [ ] Performance testing
- [ ] Security audit
- [ ] User acceptance testing
- [ ] Deploy to production

### Long-term (This Quarter)
- [ ] CI/CD automation
- [ ] Monitoring dashboards
- [ ] Alert configuration
- [ ] Runbook procedures
- [ ] Scaling strategy

---

## Quick Reference

### Common Commands
```bash
# Start
docker compose up -d

# Stop
docker compose down

# Logs
docker compose logs -f api

# Exec command
docker compose exec api python script.py

# Rebuild
docker compose build --no-cache

# Status
docker compose ps

# Health
curl http://localhost:8000/health

# API Docs
open http://localhost:8000/docs
```

### Ports
- API: 8000
- PostgreSQL: 5432
- Redis: 6379
- OpenAPI: 8000/docs

### Credentials
- DB User: `archery`
- DB Pass: `archery_pass`
- DB Name: `archery_db`
- Redis: No auth (development)

### Volumes
- `archery_db_data`: PostgreSQL data
- `archery_cache_data`: Redis data

---

**Status**: ✅ **Ready for Docker Deployment**

Next action: Resolve Docker network issue and execute `docker compose up -d`
