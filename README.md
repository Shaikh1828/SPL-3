# Automated Archery Scoring System (SPL-3)

Welcome to the **Automated Archery Scoring System**! This is a complete, full-stack application designed to manage archery tournaments, track live scores using AI/Deep Learning (YOLO11) assisted camera feeds, and provide real-time leaderboards.

---

## 🎯 YOLO11 Deep Learning Engine
- **Primary Detector**: Ultralytics YOLO11 (`runs/detect/archery_yolo11/weights/best.pt`)
- **Validation Accuracy**: **mAP50 = 97.8%**, **Recall = 97.2%**, **Precision = 94.0%**, **mAP50-95 = 89.5%**
- **Live Output Confidence**: **>91%**
- **Target & Tip Localization**: Extrapolates concentric target ring geometry (`bullseye`, `7_ring`, `6_ring`, `4_ring`, `2_ring`) and refines arrow tips inside crops using local Hough line analysis and contour aspect filtering.

---

## 🏗️ System Architecture

- **Backend**: FastAPI (Python 3.11+), PyTorch (CPU), OpenCV, SQLAlchemy, PostgreSQL 15, Redis 7.
- **Frontend**: React 18, TypeScript, Vite, Tailwind CSS, Zustand, Recharts.
- **Deployment**: Docker & Docker Compose with multi-stage build, `.dockerignore`, CPU PyTorch optimization, and `./runs:/app/runs` volume mount.

---

## 📂 Project Structure

```text
SPL-3/
├── context/                 # Consolidated Master Documentation Suite (4 Master Files + Index)
├── Data/                    # YOLO11 Dataset (504 images, 1,806 bboxes)
├── frontend/                # React + TypeScript Web Application
├── runs/                    # Trained YOLO11 model weights (`best.pt`)
├── scripts/
│   ├── prepare_dataset.py   # Polygon-to-YOLO bounding box converter
│   ├── train_yolo.py        # 30-epoch YOLO11 trainer script
│   └── evaluate_yolo.py     # Model evaluation benchmark script
├── src/                     # FastAPI Backend Application
├── alembic/                 # Database migration scripts
├── tests/                   # Backend test suite (pytest)
├── .dockerignore            # Build context exclusions
├── Dockerfile               # Multi-stage Docker build
├── docker-compose.yml       # Container stack setup (api, db, cache)
└── README.md                # Repository Homepage & Documentation Index
```

---

## 📖 Master Documentation Suite (`context/`)

All documentation, specifications, reports, and deployment guides are consolidated into **`context/`**:

- 📋 **[Documentation Index](context/INDEX.md)**
- 🏗️ **[00: System Architecture & Scoring Engine Master Reference](context/00_SYSTEM_ARCHITECTURE_AND_SCORING_ENGINE.md)**
- 🔌 **[01: API & Database Specification Master Reference](context/01_API_AND_DATABASE_SPECIFICATION.md)**
- 🐳 **[02: Deployment & Operations Guide Master Reference](context/02_DEPLOYMENT_AND_OPERATIONS_GUIDE.md)**
- ✅ **[03: Testing, Validation & Reports Master Reference](context/03_TESTING_VALIDATION_AND_PROJECT_REPORTS.md)**

---

## 🚀 Quick Commands

### 1. Dataset Preprocessing & Model Training
```bash
python scripts/prepare_dataset.py
python scripts/train_yolo.py 30
python scripts/evaluate_yolo.py
```

### 2. Start Full-Stack Docker Containers
```powershell
docker compose up -d --build
docker ps
```

Once running, the entire application stack is live:
- 🌐 **Frontend Web App**: [http://localhost:3000](http://localhost:3000) (alias: [http://localhost:5173](http://localhost:5173))
- ⚡ **Backend API**: [http://localhost:8000](http://localhost:8000)
- 📚 **Interactive Swagger API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)
- 🏥 **Health Check Endpoint**: [http://localhost:3000/api/health](http://localhost:3000/api/health)

#### Default Demo Accounts
| Role | Username | Password |
|---|---|---|
| **Admin** | `admin` | `admin123!` |
| **Scorer** | `scorer` | `scorer123!` |
| **Spectator** | `spectator1` | `Spectator123!` |

### 3. Check System Health
```powershell
python scripts/test_docker_stack.py
```
