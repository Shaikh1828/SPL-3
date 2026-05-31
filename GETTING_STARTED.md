# Getting Started - Archery Scoring System

Complete guide to set up, run, and use the Archery Scoring System backend.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Installation & Setup](#installation--setup)
3. [Running the System](#running-the-system)
4. [Verifying Installation](#verifying-installation)
5. [Basic API Usage](#basic-api-usage)
6. [Common Workflows](#common-workflows)
7. [Stopping & Cleanup](#stopping--cleanup)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Docker Setup (Recommended)
- **Docker**: 20.10 or higher
- **Docker Compose**: 2.0 or higher
- **RAM**: 4GB minimum (2GB for containers, 2GB for host)
- **Disk Space**: 5GB available
- **OS**: Windows 10+, macOS 10.15+, or Linux (any modern distribution)

### Local Development Setup
- **Python**: 3.11 or higher
- **PostgreSQL**: 15+ (if not using Docker)
- **Redis**: 7+ (if not using Docker)
- **RAM**: 4GB minimum
- **Disk Space**: 3GB available

### Optional Tools
- **curl** or **Postman**: For API testing
- **Git**: For repository management
- **VS Code**: For development (recommended)

---

## Installation & Setup

### Option 1: Docker Setup (Recommended)

#### Step 1: Clone Repository
```bash
# Using HTTPS
git clone https://github.com/your-org/SPL-3.git
cd SPL-3

# Or using SSH
git clone git@github.com:your-org/SPL-3.git
cd SPL-3
```

#### Step 2: Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Review .env file (defaults are suitable for development)
cat .env
```

**Key Environment Variables (Development Defaults):**
```
ENVIRONMENT=development
DATABASE_URL=postgresql://archery:archery_pass@localhost:5432/archery_db
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=dev-secret-key-change-in-production
API_WORKERS=2
LOG_LEVEL=DEBUG
```

#### Step 3: Build Docker Image
```bash
# Build the multi-stage Docker image
docker-compose build

# Expected output:
# Building api
# ... (compilation steps)
# Successfully tagged spl-3-api:latest
```

#### Step 4: Start Services
```bash
# Start all services in background
docker-compose up -d

# Monitor startup (wait for all services to be healthy)
docker-compose ps

# Expected output:
# NAME                    STATUS          PORTS
# archery_scoring_api     Up (healthy)    0.0.0.0:8000->8000/tcp
# archery_scoring_db      Up (healthy)    0.0.0.0:5432->5432/tcp
# archery_scoring_cache   Up (healthy)    0.0.0.0:6379->6379/tcp
```

#### Step 5: Verify Startup
```bash
# Check logs for any errors
docker-compose logs --tail=20

# All services should show:
# api: Application startup complete
# db: database system is ready to accept connections
# cache: Ready to accept connections
```

**Troubleshooting Common Docker Startup Issues:**
```bash
# If containers don't start, check logs
docker-compose logs api      # API logs
docker-compose logs db       # Database logs
docker-compose logs cache    # Redis logs

# If ports are in use
# Windows: netstat -ano | findstr :8000
# macOS/Linux: lsof -i :8000
# Kill process: kill -9 <PID>

# If database doesn't initialize
docker-compose down -v       # Remove volumes
docker-compose up -d         # Start fresh
```

---

### Option 2: Local Development Setup (Without Docker)

#### Step 1: Create Virtual Environment
```bash
# Using Python venv
python3.11 -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

#### Step 2: Install Dependencies
```bash
# Install Poetry package manager
pip install poetry

# Install project dependencies
poetry install

# Verify installation
poetry show | head -10
```

#### Step 3: Start External Services (Docker only)
```bash
# Start only database and cache containers
docker-compose up -d db cache

# Verify services started
docker-compose ps db cache
```

#### Step 4: Initialize Database
```bash
# Run Alembic migrations
alembic upgrade head

# Expected output:
# INFO [alembic.runtime.migration] Running upgrade -> 001_initial_schema
# INFO [alembic.runtime.migration] Done

# Seed test data
python -m scripts.seed_data

# Expected output:
# ✅ Seeded 5 users
# ✅ Seeded 2 tournaments
# ✅ Seeded 6 sessions
# ✅ Seeded 30 session_archers
# ✅ Seeded 924 scores
# ✅ Seeded 3 cameras
# ✅ Seeded 4 camera_lane_assignments
# Total records created: ~940
```

#### Step 5: Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with local settings
# KEY settings for local development:
ENVIRONMENT=development
DATABASE_URL=postgresql://archery:archery_pass@localhost:5432/archery_db
REDIS_URL=redis://localhost:6379/0
API_WORKERS=1
LOG_LEVEL=DEBUG
```

#### Step 6: Start API Server
```bash
# Run with auto-reload for development
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# Expected output:
# INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
# INFO:     Started server process [12345]
# INFO:     Waiting for application startup...
# INFO:     Application startup complete
```

---

## Running the System

### Starting All Services

#### Docker Compose (Recommended)
```bash
# Start in background
docker-compose up -d

# Or start with logs visible
docker-compose up

# Press Ctrl+C to stop logs (services continue running)
```

#### Check Service Status
```bash
docker-compose ps

# Should show all services as "Up (healthy)"
```

### API Access Points

Once running, access the system via:

| Component | URL | Purpose |
|-----------|-----|---------|
| **Swagger UI** | http://localhost:8000/docs | Interactive API documentation |
| **ReDoc** | http://localhost:8000/redoc | Alternative API documentation |
| **Health Check** | http://localhost:8000/api/health | Basic system health |
| **Detailed Health** | http://localhost:8000/api/health/detailed | Component-level health |
| **API Base** | http://localhost:8000/api | API endpoint prefix |

---

## Verifying Installation

### 1. Health Check Endpoint
```bash
# Test basic health
curl http://localhost:8000/api/health

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2026-05-25T16:30:00Z",
#   "environment": "development"
# }
```

### 2. Detailed Health Check
```bash
curl http://localhost:8000/api/health/detailed

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2026-05-25T16:30:00Z",
#   "components": {
#     "database": {
#       "status": "healthy",
#       "response_time_ms": 12,
#       "pool_size": 5,
#       "active_connections": 1
#     },
#     "cache": {
#       "status": "healthy",
#       "response_time_ms": 2,
#       "memory_usage_mb": 45,
#       "connected": true
#     },
#     "storage": {
#       "status": "healthy",
#       "available_gb": 8.5,
#       "quota_gb": 10,
#       "usage_percent": 15
#     },
#     "threadpool": {
#       "status": "healthy",
#       "active_threads": 0,
#       "max_threads": 8,
#       "queue_size": 0
#     }
#   }
# }
```

### 3. List Available Endpoints
```bash
# Get API documentation JSON
curl http://localhost:8000/openapi.json | python -m json.tool

# Or visit Swagger UI: http://localhost:8000/docs
```

### 4. Test Database Connection
```bash
# Using Docker
docker-compose exec api psql $DATABASE_URL -c "SELECT 1 as test"

# Or using local postgres
psql postgresql://archery:archery_pass@localhost:5432/archery_db -c "SELECT 1 as test"

# Expected output:
# test
# ------
#    1
```

### 5. Test Redis Connection
```bash
# Using Docker
docker-compose exec cache redis-cli ping

# Or using local redis
redis-cli ping

# Expected output:
# PONG
```

---

## Basic API Usage

### 1. User Registration
```bash
# Register a new user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "new_scorer",
    "email": "scorer@archery.local",
    "password": "SecurePassword123!"
  }'

# Expected response (201):
# {
#   "id": 5,
#   "username": "new_scorer",
#   "email": "scorer@archery.local",
#   "role": "archer",
#   "is_active": true,
#   "created_at": "2026-05-25T16:35:00Z"
# }
```

### 2. User Login
```bash
# Login to get JWT token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "new_scorer",
    "password": "SecurePassword123!"
  }'

# Expected response (200):
# {
#   "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
#   "token_type": "bearer",
#   "expires_in": 28800
# }

# Save token for next requests
export TOKEN="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3. Create Tournament
```bash
# Create a new tournament
curl -X POST http://localhost:8000/api/tournaments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Regional Championship 2026",
    "description": "Regional qualifying tournament",
    "location": "Central Arena",
    "start_date": "2026-06-15",
    "end_date": "2026-06-17"
  }'

# Expected response (201):
# {
#   "id": 3,
#   "name": "Regional Championship 2026",
#   "description": "Regional qualifying tournament",
#   "location": "Central Arena",
#   "start_date": "2026-06-15",
#   "end_date": "2026-06-17",
#   "created_by": 5,
#   "created_at": "2026-05-25T16:40:00Z",
#   "updated_at": "2026-05-25T16:40:00Z"
# }

# Save tournament ID
export TOURNAMENT_ID="3"
```

### 4. Create Session
```bash
# Create scoring session
curl -X POST http://localhost:8000/api/tournaments/$TOURNAMENT_ID/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Round 1 - Morning",
    "round_number": 1,
    "num_lanes": 6,
    "arrows_per_round": 6
  }'

# Expected response (201):
# {
#   "id": 7,
#   "tournament_id": 3,
#   "name": "Round 1 - Morning",
#   "round_number": 1,
#   "status": "active",
#   "start_time": "2026-05-25T16:45:00Z",
#   "end_time": null,
#   "num_lanes": 6,
#   "arrows_per_round": 6,
#   "created_at": "2026-05-25T16:45:00Z",
#   "updated_at": "2026-05-25T16:45:00Z"
# }

export SESSION_ID="7"
```

### 5. Register Archer in Session
```bash
# Add archer to session
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/archers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "archer_name": "John Smith",
    "lane_number": 1
  }'

# Expected response (201):
# {
#   "id": 31,
#   "session_id": 7,
#   "archer_name": "John Smith",
#   "lane_number": 1,
#   "total_score": 0,
#   "registered_at": "2026-05-25T16:50:00Z"
# }

export SESSION_ARCHER_ID="31"
```

### 6. Record Score
```bash
# Record arrow score
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/scores \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "session_archer_id": 31,
    "round_number": 1,
    "arrow_number": 1,
    "zone": 8,
    "points": 8,
    "image_path": "/storage/raw/7/arrow_001.jpg"
  }'

# Expected response (201):
# {
#   "id": 925,
#   "session_id": 7,
#   "session_archer_id": 31,
#   "round_number": 1,
#   "arrow_number": 1,
#   "zone": 8,
#   "points": 8,
#   "image_path": "/storage/raw/7/arrow_001.jpg",
#   "validated_by_ai": false,
#   "confidence": 0.85,
#   "created_at": "2026-05-25T16:55:00Z",
#   "updated_at": "2026-05-25T16:55:00Z"
# }
```

### 7. Get Leaderboard
```bash
# Retrieve live leaderboard
curl -X GET "http://localhost:8000/api/sessions/$SESSION_ID/leaderboard?limit=100" \
  -H "Authorization: Bearer $TOKEN"

# Expected response (200):
# {
#   "session_id": 7,
#   "total_archers": 31,
#   "items": [
#     {
#       "rank": 1,
#       "archer_id": 31,
#       "archer_name": "John Smith",
#       "lane_number": 1,
#       "total_score": 8,
#       "round_1_score": 8,
#       "round_2_score": 0,
#       "round_3_score": 0,
#       "arrows_recorded": 1
#     },
#     ...
#   ],
#   "cached": true,
#   "cache_ttl": 60,
#   "last_updated": "2026-05-25T16:55:00Z"
# }
```

### 8. Generate Report
```bash
# Generate PDF report
curl -X POST "http://localhost:8000/api/sessions/$SESSION_ID/reports?format=pdf" \
  -H "Authorization: Bearer $TOKEN" \
  -o session_report.pdf

# File saved as session_report.pdf

# Or generate CSV
curl -X POST "http://localhost:8000/api/sessions/$SESSION_ID/reports?format=csv" \
  -H "Authorization: Bearer $TOKEN" \
  -o session_report.csv
```

---

## Common Workflows

### Workflow 1: Complete Scoring Session
```bash
# 1. Register as scorer
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"AdminPassword123!"}' \
  | jq -r '.access_token')

# 2. Create tournament
TOURNAMENT=$(curl -s -X POST http://localhost:8000/api/tournaments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Quick Tournament",
    "location": "Arena",
    "start_date": "2026-05-25",
    "end_date": "2026-05-25"
  }')
TOURNAMENT_ID=$(echo $TOURNAMENT | jq -r '.id')

# 3. Create session
SESSION=$(curl -s -X POST http://localhost:8000/api/tournaments/$TOURNAMENT_ID/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "name": "Round 1",
    "round_number": 1,
    "num_lanes": 2,
    "arrows_per_round": 3
  }')
SESSION_ID=$(echo $SESSION | jq -r '.id')

# 4. Register 2 archers
ARCHER1=$(curl -s -X POST http://localhost:8000/api/sessions/$SESSION_ID/archers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"archer_name":"Archer One","lane_number":1}')
ARCHER1_ID=$(echo $ARCHER1 | jq -r '.id')

ARCHER2=$(curl -s -X POST http://localhost:8000/api/sessions/$SESSION_ID/archers \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"archer_name":"Archer Two","lane_number":2}')
ARCHER2_ID=$(echo $ARCHER2 | jq -r '.id')

# 5. Record scores (6 arrows per archer, 2 rounds)
for ROUND in 1 2; do
  for ARROW in 1 2 3; do
    ZONE=$((RANDOM % 10 + 1))  # Random zone 1-10
    curl -s -X POST http://localhost:8000/api/sessions/$SESSION_ID/scores \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d "{
        \"session_archer_id\": $ARCHER1_ID,
        \"round_number\": $ROUND,
        \"arrow_number\": $ARROW,
        \"zone\": $ZONE,
        \"points\": $ZONE
      }" > /dev/null
    
    ZONE=$((RANDOM % 10 + 1))
    curl -s -X POST http://localhost:8000/api/sessions/$SESSION_ID/scores \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer $TOKEN" \
      -d "{
        \"session_archer_id\": $ARCHER2_ID,
        \"round_number\": $ROUND,
        \"arrow_number\": $ARROW,
        \"zone\": $ZONE,
        \"points\": $ZONE
      }" > /dev/null
  done
done

# 6. Get final leaderboard
curl -s -X GET http://localhost:8000/api/sessions/$SESSION_ID/leaderboard \
  -H "Authorization: Bearer $TOKEN" | jq '.items | sort_by(.rank)[]'

# 7. Generate final report
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/reports?format=pdf \
  -H "Authorization: Bearer $TOKEN" \
  -o tournament_final_report.pdf
```

### Workflow 2: Camera Setup and Connection
```bash
# 1. Get available cameras
curl -X GET http://localhost:8000/api/sessions/$SESSION_ID/cameras \
  -H "Authorization: Bearer $TOKEN"

# 2. Connect camera
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/cameras/1/connect \
  -H "Authorization: Bearer $TOKEN"

# 3. Assign camera to lane
curl -X POST http://localhost:8000/api/sessions/$SESSION_ID/cameras/assign \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "camera_id": 1,
    "lane_number": 1
  }'

# 4. Check camera status
curl -X GET http://localhost:8000/api/sessions/$SESSION_ID/cameras \
  -H "Authorization: Bearer $TOKEN" | jq '.items[] | {id, name, status}'
```

---

## Stopping & Cleanup

### Stop Services (Keep Data)
```bash
# Stop all running containers
docker-compose stop

# Expected output:
# Stopping archery_scoring_api...
# Stopping archery_scoring_db...
# Stopping archery_scoring_cache...
```

### Stop and Remove Containers (Keep Data)
```bash
docker-compose down

# Expected output:
# Removing archery_scoring_api...
# Removing archery_scoring_db...
# Removing archery_scoring_cache...
# Removing network spl-3_archery_network...
```

### Full Cleanup (Remove All Data)
```bash
# Remove containers and volumes (DELETES DATABASE!)
docker-compose down -v

# Expected output:
# Removing volumes...
# postgres_data
# redis_data
# storage_volume
```

### Clean Local Development
```bash
# Deactivate virtual environment
deactivate

# Remove venv
rm -rf venv

# Or using conda
conda deactivate
conda env remove -n archery_scoring
```

---

## Troubleshooting

### Port Already in Use
```bash
# Windows: Find process using port 8000
netstat -ano | findstr :8000
# Kill process: taskkill /PID <PID> /F

# macOS/Linux: Find process
lsof -i :8000
# Kill process: kill -9 <PID>

# Change port in docker-compose.yml
# Change: "8000:8000" to "8001:8000"
docker-compose up -d
```

### Database Connection Failed
```bash
# Check PostgreSQL container
docker-compose ps db

# Check logs
docker-compose logs db

# Restart database
docker-compose restart db

# If still failing, rebuild from scratch
docker-compose down -v
docker-compose up -d
```

### Redis Connection Failed
```bash
# Check Redis container
docker-compose ps cache

# Test connection
docker-compose exec cache redis-cli ping

# Should return: PONG

# If failing, restart
docker-compose restart cache
```

### API Service Crashes
```bash
# Check logs for error
docker-compose logs -f api

# Common issues:
# - DATABASE_URL incorrect
# - Port 8000 already in use
# - Insufficient memory (4GB minimum)

# Restart API service
docker-compose restart api
```

### High Memory Usage
```bash
# Check container resource usage
docker-compose stats

# If Redis using too much memory:
# Edit docker-compose.yml
# Change: redis-server --appendonly yes --maxmemory 512mb
# To: redis-server --appendonly yes --maxmemory 256mb

# Restart
docker-compose restart cache
```

### Tests Failing
```bash
# Run tests with verbose output
pytest -v

# Run specific test
pytest tests/test_services.py::TestAuthService::test_register_user_success -v

# Reset test database
pytest --reset

# See full error traces
pytest -vv --tb=long
```

### Rate Limiting Issues
```bash
# If getting 429 errors:
# Current limit: 1000 requests/minute per IP

# Reset rate limit (development only)
curl -X POST http://localhost:8000/api/internal/reset-rate-limits

# Check current rate limit stats
curl -X GET http://localhost:8000/api/internal/rate-limit-stats
```

---

## Next Steps

1. **Review API Documentation**: Visit http://localhost:8000/docs
2. **Read API Specification**: See [API_SPECIFICATION.md](API_SPECIFICATION.md)
3. **Run Tests**: Execute `pytest` to validate system
4. **Deploy to Staging**: See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
5. **Monitor System**: Check health endpoints regularly

---

**For additional help**: Check [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for staging/production setup and [README.md](README.md) for architecture overview.
