# 📋 DOCUMENTATION INDEX & MASTER REFERENCE

All documentation for the Archery Scoring System (SPL-3) has been consolidated into 4 unified master files in the `context/` directory:

---

## 📚 Master Documentation Suite

| # | Document | Description |
|---|---|---|
| **00** | **[00_SYSTEM_ARCHITECTURE_AND_SCORING_ENGINE.md](00_SYSTEM_ARCHITECTURE_AND_SCORING_ENGINE.md)** | Full System Architecture, YOLO11 Model Benchmarks (**97.8% mAP50**), Deep-Dive Scoring Pipeline & Service Modules |
| **01** | **[01_API_AND_DATABASE_SPECIFICATION.md](01_API_AND_DATABASE_SPECIFICATION.md)** | REST & WebSocket API Specification, Database ER Diagrams, Table Schemas & Alembic Migrations |
| **02** | **[02_DEPLOYMENT_AND_OPERATIONS_GUIDE.md](02_DEPLOYMENT_AND_OPERATIONS_GUIDE.md)** | Multi-container Docker Setup, CPU PyTorch Optimization, Volume Mounting & Health Checks |
| **03** | **[03_TESTING_VALIDATION_AND_PROJECT_REPORTS.md](03_TESTING_VALIDATION_AND_PROJECT_REPORTS.md)** | System Validation, Model Metrics, Automated Test Suite Specifications & Technical Midterm Report |

---

## ⚡ Quick Commands

### 1. Model Training & Evaluation
```bash
python scripts/prepare_dataset.py
python scripts/train_yolo.py 30
python scripts/evaluate_yolo.py
```

### 2. Docker Container Operations
```powershell
docker compose up -d --build
docker ps
docker logs archery_scoring_api --tail 50
```

### 3. API Health Check
```powershell
python -c "import requests; r = requests.get('http://localhost:8000/api/health'); print(r.status_code, r.json())"
```
