# SPL-3: Testing, Validation & Technical Reports Master Reference

---

## 1. System Validation & Model Benchmarks

### YOLO11 Model Benchmark Performance
- **Model Weight File**: `runs/detect/archery_yolo11/weights/best.pt`
- **Training Epochs**: 30 full epochs on 504 images (1,806 bounding boxes)
- **Validation Metric Scores**:
  - **mAP50**: **0.9781 (97.8%)**
  - **Recall**: **0.9724 (97.2%)**
  - **Precision**: **0.9398 (94.0%)**
  - **mAP50-95**: **0.8946 (89.5%)**

### Pipeline Integration Test Results
- **Target Center Detection**: Tested on live target images ➔ Ring bounding boxes (`bullseye`, `7_ring`, `6_ring`, `4_ring`, `2_ring`) detected with **92.7%–95.4%** confidence.
- **Arrow Tip Localization**: Tip positions accurately localized on target face with **88.1%–91.5%** confidence.
- **Method Verification**: Confirmed active pipeline method string `yolo11+geometric_yolo11_rings+yolo11_hybrid`.

---

## 2. Automated Test Suite (`pytest`)

### Test Coverage Overview
- **Total Test Cases**: 46+ test cases across unit and integration test suites in `tests/`.
- **Target Code Coverage**: >70% (current coverage: 74%).
- **Execution Commands**:
  ```bash
  # Run all unit and integration tests
  pytest tests/ -v

  # Run tests with HTML coverage report
  pytest --cov=src --cov-report=html

  # Run specific test file
  pytest tests/test_api_endpoints.py -v
  ```

### Key Test File Specifications

#### 1. Unit Tests (`tests/test_services.py`)
- **AuthService Tests** (8 tests): Password bcrypt hashing, JWT token creation, token expiration enforcement, invalid login handling.
- **ScoringService Tests** (6 tests): WA zone calculation boundaries, points validation (0–10), DB retry logic.
- **CameraService Tests** (3 tests): Camera CRUD, lane assignment, connection heartbeat.
- **HealthService Tests** (4 tests): Health check telemetry, database connection check, Redis cache ping.

#### 2. Integration Tests (`tests/test_api_endpoints.py`)
- **Auth API** (6 tests): `/api/auth/register`, `/api/auth/login`, `/api/auth/refresh`.
- **Tournament API** (3 tests): `/api/tournaments` CRUD endpoints.
- **Session API** (5 tests): `/api/sessions` state transitions.
- **Score API** (4 tests): `/api/sessions/{id}/scores/upload` image handling, score overrides.
- **Camera API** (4 tests): `/api/cameras` lane assignment streams.
- **Leaderboard API** (2 tests): `/api/sessions/{id}/leaderboard` Redis caching.
- **Health API** (2 tests): `/api/health` 200 OK verification.

---

## 3. SE801 Midterm Technical Report Summary

### Project Scope & Deliverables
The SE801 Midterm Technical Report documents the engineering lifecycle of the Automated Archery Scoring System:

1. **Problem Statement**: Traditional archery scoring relies on manual visual calls, leading to disputes, human error, and slow competition rounds.
2. **Proposed Solution**: An automated camera-assisted web application combining deep learning object detection (YOLO11) with computer vision geometry extrapolation.
3. **Engineering Deliverables**:
   - **Backend Layer**: 20+ Python FastAPI modules implementing 26 endpoints.
   - **Database Layer**: PostgreSQL 15 schema with 8 normalized tables and Alembic migrations.
   - **AI/ML Layer**: YOLO11 model trained on 1,806 bounding box annotations scoring **97.8% mAP50**.
   - **Deployment Layer**: Multi-stage Docker build with `.dockerignore` and PyTorch CPU optimization.
