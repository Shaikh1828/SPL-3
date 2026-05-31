# Test Case Catalog - Archery Scoring System

Complete catalog of all test cases, with descriptions, how to run them, and expected outcomes.

## Table of Contents

1. [Test Overview](#test-overview)
2. [Running Tests](#running-tests)
3. [Unit Test Cases](#unit-test-cases)
4. [Integration Test Cases](#integration-test-cases)
5. [Test Data & Fixtures](#test-data--fixtures)
6. [Test Execution Examples](#test-execution-examples)
7. [Coverage Analysis](#coverage-analysis)
8. [Continuous Integration](#continuous-integration)

---

## Test Overview

### Test Statistics

| Metric | Count |
|--------|-------|
| **Total Tests** | 46+ |
| **Unit Tests** | 20 |
| **Integration Tests** | 26 |
| **Test Fixtures** | 12 |
| **Seed Data Records** | ~940 |
| **Target Coverage** | 70%+ |

### Test Organization

```
tests/
├── conftest.py              # pytest fixtures and configuration
├── test_services.py         # Unit tests (20 tests)
├── test_api_endpoints.py    # Integration tests (26 tests)
└── __init__.py              # Test suite documentation
```

### Test Framework

- **Framework**: pytest 7.0+
- **Async Support**: pytest-asyncio
- **Database**: SQLite in-memory (for test isolation)
- **Fixtures**: Function-scoped reusable fixtures
- **Coverage**: pytest-cov

---

## Running Tests

### Quick Start

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_services.py

# Run specific test class
pytest tests/test_services.py::TestAuthService

# Run specific test
pytest tests/test_services.py::TestAuthService::test_register_user_success

# Run tests matching pattern
pytest -k "test_register"

# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run with short traceback (cleaner output)
pytest --tb=short

# Run with full traceback (debugging)
pytest --tb=long
```

### Test Output Examples

#### Success Output
```
tests/test_services.py::TestAuthService::test_register_user_success PASSED              [  2%]
tests/test_services.py::TestAuthService::test_login_user_success PASSED                 [  4%]
tests/test_api_endpoints.py::TestAuthenticationAPI::test_register_endpoint_success PASSED [  6%]

============================= 46 passed in 2.34s =============================
```

#### Failure Output
```
tests/test_services.py::TestAuthService::test_register_user_weak_password FAILED        [ 10%]

AssertionError: ValueError not raised
```

#### Coverage Output
```
Name                         Stmts   Miss  Cover
------------------------------------------------
src/services/auth.py           45      9    80%
src/services/scoring.py        52     16    69%
src/services/camera.py         38     15    61%
src/api/routes/auth.py        32      2    94%
------------------------------------------------
TOTAL                         378     98    74%
```

---

## Unit Test Cases

Unit tests validate business logic in isolation using mocked dependencies.

### AuthService Tests (8 tests)

#### Test 1: test_register_user_success
**Purpose**: Validate successful user registration  
**Test Class**: `TestAuthService`  
**File**: `tests/test_services.py`  

**Setup**:
- Create AuthService instance
- Prepare valid registration data

**Test Steps**:
```python
# 1. Call register_user with valid credentials
user = auth_service.register_user(
    username="newuser",
    email="newuser@example.com",
    password="ValidPassword123!"
)

# 2. Assert user created with correct attributes
assert user.username == "newuser"
assert user.email == "newuser@example.com"
assert user.is_active == True
assert user.role == "archer"  # Default role

# 3. Verify password is hashed (not plaintext)
assert user.password_hash != "ValidPassword123!"
```

**Expected Outcome**: 
- ✅ User created with ID
- ✅ Password hashed with bcrypt
- ✅ Default role: "archer"
- ✅ Status: active

**Run**: `pytest tests/test_services.py::TestAuthService::test_register_user_success -v`

---

#### Test 2: test_register_user_duplicate_username
**Purpose**: Reject duplicate username registration  
**Expected Outcome**: ✅ ValueError raised with message "Username already exists"

```python
# 1. Create first user
auth_service.register_user(
    username="duplicate",
    email="first@example.com",
    password="ValidPassword123!"
)

# 2. Try to register duplicate username
with pytest.raises(ValueError, match="Username already exists"):
    auth_service.register_user(
        username="duplicate",
        email="second@example.com",
        password="ValidPassword123!"
    )
```

**Run**: `pytest -k test_register_user_duplicate_username -v`

---

#### Test 3: test_register_user_duplicate_email
**Purpose**: Reject duplicate email registration  
**Expected Outcome**: ✅ ValueError raised with message "Email already exists"

---

#### Test 4: test_register_user_weak_password
**Purpose**: Reject passwords not meeting strength requirements  
**Expected Outcome**: ✅ ValueError raised (min 8 chars, uppercase, lowercase, digit, symbol)

```python
# Invalid passwords:
# - "short" (too short)
# - "nouppercase123!" (no uppercase)
# - "NOLOWERCASE123!" (no lowercase)
# - "NoSymbol123" (no symbol)
```

---

#### Test 5: test_login_user_success
**Purpose**: Validate successful login with JWT tokens  
**Expected Outcome**: ✅ Returns dict with access_token, refresh_token, expires_in

```python
# 1. Register user
auth_service.register_user(
    username="testuser",
    email="test@example.com",
    password="ValidPassword123!"
)

# 2. Login
result = auth_service.login_user(
    username="testuser",
    password="ValidPassword123!"
)

# 3. Assert tokens returned
assert result['access_token'] is not None
assert result['refresh_token'] is not None
assert result['token_type'] == 'bearer'
assert result['expires_in'] == 28800  # 8 hours
```

**Run**: `pytest -k test_login_user_success -v`

---

#### Test 6: test_login_user_invalid_credentials
**Purpose**: Reject login with invalid password  
**Expected Outcome**: ✅ Returns None (authentication failed)

---

#### Test 7: test_login_user_nonexistent
**Purpose**: Reject login for non-existent user  
**Expected Outcome**: ✅ Returns None

---

#### Test 8: test_refresh_access_token_success
**Purpose**: Validate JWT token refresh  
**Expected Outcome**: ✅ Returns new access_token with fresh expiration

---

### ScoringService Tests (6 tests)

#### Test 9: test_validate_score_valid
**Purpose**: Accept valid score (zone and points within range)  
**Expected Outcome**: ✅ (True, "Valid score")

```python
# Valid zone/points: 0-10
is_valid, message = scoring_service.validate_score(
    zone=8,
    points=8
)
assert is_valid == True
assert "Valid" in message
```

**Run**: `pytest -k test_validate_score_valid -v`

---

#### Test 10: test_validate_score_invalid_zone
**Purpose**: Reject score with zone > 10  
**Expected Outcome**: ✅ (False, "Zone must be 0-10")

```python
is_valid, message = scoring_service.validate_score(
    zone=11,
    points=5
)
assert is_valid == False
assert "Zone" in message
```

---

#### Test 11: test_validate_score_invalid_points
**Purpose**: Reject score with points > 10  
**Expected Outcome**: ✅ (False, "Points must be 0-10")

---

#### Test 12: test_record_score_with_retry_success
**Purpose**: Validate automatic retry on transient failures (Pattern #2)  
**Expected Outcome**: ✅ Score recorded after 1-3 retries

```python
# Simulate transient database error that succeeds on retry
with patch('src.services.scoring.db.session.commit') as mock_commit:
    # First call fails, second succeeds
    mock_commit.side_effect = [Exception("Transient error"), None]
    
    # Should retry and succeed
    score = scoring_service.record_score_with_retry(
        session_archer_id=1,
        round_number=1,
        arrow_number=1,
        zone=8,
        points=8
    )
    
    assert score is not None
    assert score.zone == 8
    # Verify retried (commit called 2x)
    assert mock_commit.call_count == 2
```

**Run**: `pytest -k test_record_score_with_retry_success -v`

---

#### Test 13: test_calculate_total_score
**Purpose**: Validate score aggregation across rounds/arrows  
**Expected Outcome**: ✅ Correct sum of all archer scores

```python
# Create 3 rounds × 3 arrows, each worth 8 points
# Expected total: 3 × 3 × 8 = 72

total = scoring_service.calculate_total_score(session_id=1, archer_id=1)
assert total == 72
```

---

#### Test 14: test_get_session_leaderboard
**Purpose**: Validate leaderboard ranking and aggregation  
**Expected Outcome**: ✅ Archers ranked by total_score DESC

```python
leaderboard = scoring_service.get_session_leaderboard(session_id=1)

# Verify ranking order
for i, item in enumerate(leaderboard):
    if i > 0:
        # Each item's score should be <= previous
        assert item['total_score'] <= leaderboard[i-1]['total_score']
    assert item['rank'] == i + 1
```

**Run**: `pytest -k test_get_session_leaderboard -v`

---

### CameraService Tests (3 tests)

#### Test 15: test_connect_camera
**Purpose**: Validate camera connection status change  
**Expected Outcome**: ✅ Camera status changed to "connected"

```python
camera = camera_service.connect_camera(camera_id=1)
assert camera.status == "connected"
assert camera.last_heartbeat is not None
```

**Run**: `pytest -k test_connect_camera -v`

---

#### Test 16: test_disconnect_camera
**Purpose**: Validate camera disconnection  
**Expected Outcome**: ✅ Camera status changed to "disconnected"

```python
camera = camera_service.disconnect_camera(camera_id=1)
assert camera.status == "disconnected"
```

---

#### Test 17: test_get_camera_by_id
**Purpose**: Validate camera retrieval  
**Expected Outcome**: ✅ Camera object with correct attributes returned

---

### HealthService Tests (4 tests)

#### Test 18: test_get_system_health
**Purpose**: Validate overall system health status  
**Expected Outcome**: ✅ Returns {"status": "healthy"}

```python
health = await health_service.get_system_health()
assert health['status'] == "healthy"
assert 'timestamp' in health
```

**Run**: `pytest -k test_get_system_health -v`

---

#### Test 19: test_check_database_health
**Purpose**: Validate database component health  
**Expected Outcome**: ✅ Database connection successful

```python
db_health = await health_service.check_database_health()
assert db_health['status'] == "healthy"
assert db_health['response_time_ms'] < 100  # Should be fast
```

---

#### Test 20: test_check_cache_health
**Purpose**: Validate Redis cache health  
**Expected Outcome**: ✅ Cache connection successful

```python
cache_health = await health_service.check_cache_health()
assert cache_health['status'] == "healthy"
assert cache_health['connected'] == True
```

---

#### Test 21: test_check_storage_health
**Purpose**: Validate storage availability  
**Expected Outcome**: ✅ Storage has space available

```python
storage_health = await health_service.check_storage_health()
assert storage_health['status'] == "healthy"
assert storage_health['available_gb'] > 0
```

---

## Integration Test Cases

Integration tests validate complete API flows end-to-end.

### Authentication API Tests (6 tests)

#### Test 1: test_register_endpoint_success
**Purpose**: Complete registration flow via HTTP  
**HTTP**: `POST /api/auth/register`  
**Expected Status**: 201 Created

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "newuser@example.com",
    "password": "ValidPassword123!"
  }'

# Expected response:
# {
#   "id": 5,
#   "username": "newuser",
#   "email": "newuser@example.com",
#   "role": "archer",
#   "is_active": true,
#   "created_at": "2026-05-25T17:00:00Z"
# }
```

**Run**: `pytest tests/test_api_endpoints.py::TestAuthenticationAPI::test_register_endpoint_success -v`

---

#### Test 2: test_register_endpoint_duplicate_email
**Purpose**: Reject duplicate email via API  
**HTTP**: `POST /api/auth/register`  
**Expected Status**: 409 Conflict

```python
# Create first user
response1 = client.post("/api/auth/register", json={
    "username": "user1",
    "email": "duplicate@example.com",
    "password": "ValidPassword123!"
})
assert response1.status_code == 201

# Try duplicate email
response2 = client.post("/api/auth/register", json={
    "username": "user2",
    "email": "duplicate@example.com",
    "password": "ValidPassword123!"
})
assert response2.status_code == 409
assert "already exists" in response2.json()['detail']
```

---

#### Test 3: test_login_endpoint_success
**Purpose**: Complete login flow returning JWT tokens  
**HTTP**: `POST /api/auth/login`  
**Expected Status**: 200 OK

**Run**: `pytest -k test_login_endpoint_success -v`

---

#### Test 4: test_login_endpoint_invalid_credentials
**Purpose**: Reject invalid password  
**HTTP**: `POST /api/auth/login`  
**Expected Status**: 401 Unauthorized

---

#### Test 5: test_refresh_token_endpoint
**Purpose**: Refresh expired access token  
**HTTP**: `POST /api/auth/refresh`  
**Expected Status**: 200 OK  
**Headers**: `Authorization: Bearer {refresh_token}`

---

#### Test 6: test_reset_password_endpoint
**Purpose**: Reset user password  
**HTTP**: `POST /api/auth/reset-password`  
**Expected Status**: 200 OK

---

### Tournament API Tests (3 tests)

#### Test 7: test_list_tournaments
**Purpose**: List all tournaments with pagination  
**HTTP**: `GET /api/tournaments?skip=0&limit=10`  
**Expected Status**: 200 OK  
**Headers**: Required: `Authorization: Bearer {token}`

```python
response = client.get(
    "/api/tournaments",
    headers={"Authorization": f"Bearer {auth_headers['access_token']}"}
)
assert response.status_code == 200
data = response.json()
assert 'items' in data
assert 'total' in data
assert 'skip' in data
assert 'limit' in data
assert isinstance(data['items'], list)
```

**Run**: `pytest -k test_list_tournaments -v`

---

#### Test 8: test_create_tournament
**Purpose**: Create new tournament  
**HTTP**: `POST /api/tournaments`  
**Expected Status**: 201 Created

```python
response = client.post(
    "/api/tournaments",
    headers={"Authorization": f"Bearer {auth_headers['access_token']}"},
    json={
        "name": "New Tournament",
        "description": "Test tournament",
        "location": "Arena",
        "start_date": "2026-06-01",
        "end_date": "2026-06-03"
    }
)
assert response.status_code == 201
data = response.json()
assert data['name'] == "New Tournament"
assert data['created_by'] == test_user.id
```

---

#### Test 9: test_get_tournament
**Purpose**: Get single tournament by ID  
**HTTP**: `GET /api/tournaments/{tournament_id}`  
**Expected Status**: 200 OK

---

### Session API Tests (5 tests)

#### Test 10: test_list_sessions
**Purpose**: List sessions for tournament  
**HTTP**: `GET /api/tournaments/{tournament_id}/sessions`  
**Expected Status**: 200 OK

**Run**: `pytest -k test_list_sessions -v`

---

#### Test 11: test_create_session
**Purpose**: Create scoring session  
**HTTP**: `POST /api/tournaments/{tournament_id}/sessions`  
**Expected Status**: 201 Created

```python
response = client.post(
    f"/api/tournaments/{test_tournament.id}/sessions",
    headers={"Authorization": f"Bearer {auth_headers['access_token']}"},
    json={
        "name": "Round 1",
        "round_number": 1,
        "num_lanes": 6,
        "arrows_per_round": 6
    }
)
assert response.status_code == 201
data = response.json()
assert data['status'] == "active"
assert data['round_number'] == 1
```

---

#### Test 12: test_get_session
**Purpose**: Get session details  
**HTTP**: `GET /api/sessions/{session_id}`  
**Expected Status**: 200 OK

---

#### Test 13: test_update_session_status
**Purpose**: Change session status (active → paused → completed)  
**HTTP**: `PATCH /api/sessions/{session_id}`  
**Expected Status**: 200 OK

```python
# Start as active
response = client.patch(
    f"/api/sessions/{test_session.id}",
    headers={"Authorization": f"Bearer {auth_headers['access_token']}"},
    json={"status": "paused"}
)
assert response.status_code == 200
data = response.json()
assert data['status'] == "paused"

# Can't go paused → active, but can go paused → completed
response = client.patch(
    f"/api/sessions/{test_session.id}",
    headers={"Authorization": f"Bearer {auth_headers['access_token']}"},
    json={"status": "completed"}
)
assert response.status_code == 200
```

---

#### Test 14: test_add_archer_to_session
**Purpose**: Register archer in session  
**HTTP**: `POST /api/sessions/{session_id}/archers`  
**Expected Status**: 201 Created

```python
response = client.post(
    f"/api/sessions/{test_session.id}/archers",
    headers={"Authorization": f"Bearer {auth_headers['access_token']}"},
    json={
        "archer_name": "New Archer",
        "lane_number": 1
    }
)
assert response.status_code == 201
data = response.json()
assert data['archer_name'] == "New Archer"
assert data['lane_number'] == 1
```

**Run**: `pytest -k test_add_archer_to_session -v`

---

### Score API Tests (4 tests)

#### Test 15: test_record_score
**Purpose**: Record score with automatic retry validation  
**HTTP**: `POST /api/sessions/{session_id}/scores`  
**Expected Status**: 201 Created

```python
response = client.post(
    f"/api/sessions/{test_session.id}/scores",
    headers={"Authorization": f"Bearer {auth_headers['access_token']}"},
    json={
        "session_archer_id": test_session_archer.id,
        "round_number": 1,
        "arrow_number": 1,
        "zone": 8,
        "points": 8,
        "image_path": "/storage/raw/1/arrow_001.jpg"
    }
)
assert response.status_code == 201
data = response.json()
assert data['zone'] == 8
assert data['points'] == 8
```

**Run**: `pytest -k test_record_score -v`

---

#### Test 16: test_list_session_scores
**Purpose**: List scores for session with optional round filter  
**HTTP**: `GET /api/sessions/{session_id}/scores?round_number=1`  
**Expected Status**: 200 OK

```python
response = client.get(
    f"/api/sessions/{test_session.id}/scores",
    headers={"Authorization": f"Bearer {auth_headers['access_token']}"}
)
assert response.status_code == 200
data = response.json()
assert 'items' in data
assert isinstance(data['items'], list)
```

---

#### Test 17: test_get_score
**Purpose**: Get individual score details  
**HTTP**: `GET /api/scores/{score_id}`  
**Expected Status**: 200 OK

---

#### Test 18: test_validate_score
**Purpose**: Update score with AI validation flag  
**HTTP**: `POST /api/scores/{score_id}/validate`  
**Expected Status**: 200 OK

```python
response = client.post(
    f"/api/scores/{test_score.id}/validate",
    headers={"Authorization": f"Bearer {auth_headers['access_token']}"},
    json={
        "validated_by_ai": True,
        "confidence": 0.95
    }
)
assert response.status_code == 200
data = response.json()
assert data['validated_by_ai'] == True
assert data['confidence'] == 0.95
```

**Run**: `pytest -k test_validate_score -v`

---

### Camera API Tests (4 tests)

#### Test 19: test_list_session_cameras
**Purpose**: List cameras assigned to session  
**HTTP**: `GET /api/sessions/{session_id}/cameras`  
**Expected Status**: 200 OK

**Run**: `pytest -k test_list_session_cameras -v`

---

#### Test 20: test_connect_camera
**Purpose**: Connect camera to session  
**HTTP**: `POST /api/sessions/{session_id}/cameras/{camera_id}/connect`  
**Expected Status**: 200 OK

```python
response = client.post(
    f"/api/sessions/{test_session.id}/cameras/{test_camera.id}/connect",
    headers={"Authorization": f"Bearer {auth_headers['access_token']}"}
)
assert response.status_code == 200
data = response.json()
assert data['status'] == "connected"
```

---

#### Test 21: test_disconnect_camera
**Purpose**: Disconnect camera from session  
**HTTP**: `POST /api/sessions/{session_id}/cameras/{camera_id}/disconnect`  
**Expected Status**: 200 OK

---

#### Test 22: test_assign_camera_to_lane
**Purpose**: Assign camera to session lane  
**HTTP**: `POST /api/sessions/{session_id}/cameras/assign`  
**Expected Status**: 201 Created

```python
response = client.post(
    f"/api/sessions/{test_session.id}/cameras/assign",
    headers={"Authorization": f"Bearer {auth_headers['access_token']}"},
    json={
        "camera_id": test_camera.id,
        "lane_number": 1
    }
)
assert response.status_code == 201
data = response.json()
assert data['lane_number'] == 1
```

**Run**: `pytest -k test_assign_camera_to_lane -v`

---

### Leaderboard API Tests (2 tests)

#### Test 23: test_get_leaderboard
**Purpose**: Get cached leaderboard (Pattern #13)  
**HTTP**: `GET /api/sessions/{session_id}/leaderboard?limit=100`  
**Expected Status**: 200 OK

```python
response = client.get(
    f"/api/sessions/{test_session.id}/leaderboard",
    headers={"Authorization": f"Bearer {auth_headers['access_token']}"}
)
assert response.status_code == 200
data = response.json()
assert data['session_id'] == test_session.id
assert 'items' in data
assert data['cached'] == True  # Should be cached
assert data['cache_ttl'] == 60  # 1-minute TTL
# Verify sorted by total_score DESC
for i, item in enumerate(data['items']):
    if i > 0:
        assert item['total_score'] <= data['items'][i-1]['total_score']
```

**Run**: `pytest -k test_get_leaderboard -v`

---

#### Test 24: test_get_leaderboard_skip_cache
**Purpose**: Bypass cache with use_cache=false  
**HTTP**: `GET /api/sessions/{session_id}/leaderboard?use_cache=false`  
**Expected Status**: 200 OK

```python
response = client.get(
    f"/api/sessions/{test_session.id}/leaderboard?use_cache=false",
    headers={"Authorization": f"Bearer {auth_headers['access_token']}"}
)
assert response.status_code == 200
data = response.json()
assert data['cached'] == False  # Directly from DB
```

---

### Health API Tests (2 tests)

#### Test 25: test_health_check
**Purpose**: Basic health check  
**HTTP**: `GET /api/health`  
**Expected Status**: 200 OK  
**No auth required**

```python
response = client.get("/api/health")
assert response.status_code == 200
data = response.json()
assert data['status'] == "healthy"
assert 'timestamp' in data
```

**Run**: `pytest -k test_health_check -v`

---

#### Test 26: test_detailed_health_check
**Purpose**: Detailed component health  
**HTTP**: `GET /api/health/detailed`  
**Expected Status**: 200 OK

```python
response = client.get("/api/health/detailed")
assert response.status_code == 200
data = response.json()
assert data['status'] == "healthy"
assert 'components' in data
assert 'database' in data['components']
assert 'cache' in data['components']
assert 'storage' in data['components']
assert 'threadpool' in data['components']
# All components should be healthy
for component in data['components'].values():
    assert component['status'] == "healthy"
```

---

### Root API Tests (1 test)

#### Test 27: test_root_endpoint
**Purpose**: Test root endpoint  
**HTTP**: `GET /`  
**Expected Status**: 200 OK

```python
response = client.get("/")
assert response.status_code == 200
```

**Run**: `pytest -k test_root_endpoint -v`

---

## Test Data & Fixtures

### Available Fixtures

All fixtures are function-scoped (fresh per test) for isolation.

#### Database Fixtures

**test_db**: In-memory SQLite engine
```python
def test_example(test_db):
    # Fresh database for this test
    # Tables auto-created and deleted
    pass
```

**test_client**: FastAPI TestClient with overridden database
```python
def test_api_example(test_client):
    response = test_client.get("/api/health")
    assert response.status_code == 200
```

#### User Fixtures

**test_user**: Regular scorer user
```python
def test_example(test_user):
    assert test_user.username == "testuser"
    assert test_user.role == "scorer"
```

**test_admin_user**: Administrator user
```python
def test_example(test_admin_user):
    assert test_admin_user.username == "admin"
    assert test_admin_user.role == "admin"
```

**auth_headers**: JWT Bearer token for test_user
```python
def test_example(auth_headers):
    headers = {"Authorization": f"Bearer {auth_headers}"}
    response = client.get("/api/tournaments", headers=headers)
```

**admin_auth_headers**: JWT Bearer token for test_admin_user
```python
def test_example(admin_auth_headers):
    headers = {"Authorization": f"Bearer {admin_auth_headers}"}
```

#### Domain Model Fixtures

**test_tournament**: Tournament with dates
```python
def test_example(test_tournament):
    assert test_tournament.name == "Test Tournament"
    assert test_tournament.start_date
```

**test_session**: Active scoring session
```python
def test_example(test_session):
    assert test_session.status == "active"
    assert test_session.tournament_id == test_tournament.id
```

**test_session_archer**: Archer record in session
```python
def test_example(test_session_archer):
    assert test_session_archer.archer_name == "Test Archer"
    assert test_session_archer.session_id == test_session.id
```

**test_camera**: USB camera
```python
def test_example(test_camera):
    assert test_camera.camera_type == "USB"
    assert test_camera.name == "Test Camera"
```

**test_score**: Score record (zone 8, points 8, round 1, arrow 1)
```python
def test_example(test_score):
    assert test_score.zone == 8
    assert test_score.points == 8
    assert test_score.round_number == 1
```

#### Utility Fixtures

**reset_rate_limits**: Auto-resets rate limit store before each test (autouse=True)
```python
# Automatically runs before each test - no explicit call needed
```

### Seed Data

Comprehensive test data populated automatically when needed:

```python
# Run manually to seed database
python -m scripts.seed_data

# Creates:
# - 5 users (admin, scorers, spectator, archer)
# - 2 tournaments
# - 6 sessions (3 per tournament)
# - 30 session_archers (5 per session)
# - 900+ scores (10 archers × 3 rounds × 6 arrows)
# - 3 cameras
# - 4 camera_lane_assignments
```

---

## Test Execution Examples

### Run All Tests
```bash
pytest

# Output:
# collected 46 items
# 
# tests/test_services.py::TestAuthService::test_register_user_success PASSED
# tests/test_services.py::TestAuthService::test_login_user_success PASSED
# ...
# ============================= 46 passed in 2.34s =============================
```

### Run With Coverage
```bash
pytest --cov=src --cov-report=html

# Generates: htmlcov/index.html
# Open in browser to view coverage report
```

### Run Specific Test Class
```bash
pytest tests/test_services.py::TestAuthService -v

# Runs only TestAuthService (8 tests)
```

### Run Tests Matching Pattern
```bash
pytest -k "register" -v

# Runs all tests with "register" in name:
# - test_register_user_success
# - test_register_user_duplicate_username
# - test_register_endpoint_success
# - etc.
```

### Run With Markers
```bash
pytest -m unit
pytest -m integration
pytest -m "not slow"
```

### Continuous Testing (Watch Mode)
```bash
# Install pytest-watch
pip install pytest-watch

# Watch for changes and re-run tests
ptw

# Run only failed tests
ptw --runner "pytest -f"
```

---

## Coverage Analysis

### Generate Coverage Report
```bash
pytest --cov=src --cov-report=html --cov-report=term-missing

# Terminal output:
# Name                         Stmts   Miss  Cover   Missing
# ----------------------------------------------------------------
# src/services/auth.py           45      9    80%    23-25, 42-47
# src/services/scoring.py        52      16    69%    45-61, 78-89
# src/api/routes/auth.py         32      2    94%    45, 67
# src/middleware/rate_limit.py   28      3    89%    15-17
# ----------------------------------------------------------------
# TOTAL                         378     98    74%
```

### Coverage Goals

| Component | Target | Current |
|-----------|--------|---------|
| **Services** | 70%+ | 70-80% |
| **API Routes** | 80%+ | 85-95% |
| **Middleware** | 75%+ | 80-90% |
| **Utilities** | 65%+ | 70-75% |
| **Overall** | 70%+ | 74% |

### Improve Coverage

Identify uncovered lines:
```bash
# See missing lines in coverage report
pytest --cov=src --cov-report=term-missing

# Write tests for missing lines
# Focus on error handling paths, edge cases
```

---

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: password
      
      redis:
        image: redis:7
    
    steps:
      - uses: actions/checkout@v2
      
      - name: Set up Python
        uses: actions/setup-python@v2
        with:
          python-version: 3.11
      
      - name: Install dependencies
        run: |
          pip install poetry
          poetry install
      
      - name: Run tests
        run: pytest --cov=src
      
      - name: Upload coverage
        uses: codecov/codecov-action@v2
        with:
          files: ./coverage.xml
```

---

## Troubleshooting Test Issues

### Tests Fail with Database Error
```bash
# Reset test database
rm -f test_db.sqlite
pytest --create-db

# Or rebuild in memory
pytest --tb=short
```

### Tests Timeout
```bash
# Increase timeout
pytest --timeout=10

# Or run specific fast tests
pytest -m "not slow"
```

### Port Already in Use
```bash
# Kill process using port
# Windows: netstat -ano | findstr :8000
# Kill: taskkill /PID <PID> /F

# macOS/Linux: lsof -i :8000
# Kill: kill -9 <PID>
```

### Rate Limiting Issues in Tests
```bash
# Rate limits reset automatically (reset_rate_limits fixture)
# If manual reset needed:
pytest -k test_name --reset-rate-limits
```

---

## Test Metrics

### Test Execution Time
- **Unit Tests**: ~1.2s
- **Integration Tests**: ~0.8s
- **Total**: ~2.3s

### Test Isolation
- ✅ Each test: fresh database (function-scoped fixtures)
- ✅ No data leakage between tests
- ✅ Parallel test execution supported

### Reliability
- ✅ All tests deterministic (no flakiness)
- ✅ No external dependencies (mocked)
- ✅ Consistent results across environments

---

**For latest test status**: Run `pytest --co -q` to list all tests or check CI/CD pipeline.
