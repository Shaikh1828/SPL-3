# SPL-3: Archery Scoring System — System Architecture & Scoring Engine Master Reference

---

## 1. Executive System Overview & Architecture

### System Description
এটি একটি **Real-time Archery Scoring System** যা Deep Learning (YOLO11) এবং Computer Vision (CV) ব্যবহার করে archery target এর ছবি থেকে automatically target face geometry detect করে এবং arrow tip position অনুযায়ী World Archery (WA) standard অনুযায়ী score calculate করে। পুরো system টি একটি web application হিসাবে কাজ করে — FastAPI backend + React (Vite+TypeScript) frontend।

### High-Level System Architecture Diagram
```
┌──────────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (React 18 + Vite 5)                     │
│                                                                          │
│  Pages (10): Dashboard, Scoring, Tournaments, BatchTesting, Cameras,     │
│              Reports, Users, Login, Register, NotFound                   │
│  State: Zustand stores (authStore, sessionStore, cameraStore)            │
│  Tech: TypeScript, Tailwind CSS v4, Radix UI, Recharts, Axios            │
└────────────────────────────────────┬─────────────────────────────────────┘
                                     │ HTTP REST + WebSockets
                                     ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                         BACKEND (FastAPI 0.110+)                         │
│                                                                          │
│  ┌───────────────────────┐ ┌──────────────────────┐ ┌──────────────────┐ │
│  │   API Routes (11)     │ │   Middleware Layer   │ │   Event System   │ │
│  │   auth, tournaments,  │ │   CORS Whitelist,    │ │   In-Process     │ │
│  │   sessions, scores,   │ │   SlowAPI RateLimit, │ │   PubSub         │ │
│  │   cameras, users,     │ │   Request Tracing,   │ │   Event Bus      │ │
│  │   leaderboard, etc.   │ │   Error Handlers     │ │   (events.py)    │ │
│  └───────────┬───────────┘ └──────────────────────┘ └──────────────────┘ │
│              │                                                           │
│  ┌───────────▼────────────────────────────────────────────────────────┐  │
│  │                   SERVICES LAYER (`src/services/`)                 │  │
│  │                                                                    │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │  YOLOArrowDetectionService (PRIMARY ENGINE)                   │  │  │
│  │  │  Ultralytics YOLO11 Model + Hybrid Bbox Crop Refinement      │  │  │
│  │  │  (yolo_detection_service.py) -> >91% Confidence Detections   │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  │  ┌──────────────────────────────────────────────────────────────┐  │  │
│  │  │  ArrowDetectionService (CV FALLBACK ENGINE)                   │  │  │
│  │  │  2,665-line Multi-method OpenCV Fallback Pipeline            │  │  │
│  │  └──────────────────────────────────────────────────────────────┘  │  │
│  │  ┌────────────────────────┐ ┌───────────────────────────────────┐ │  │
│  │  │ ScoringService (324L)  │ │ ImageService (547L)               │ │  │
│  │  │ DB Write Retry, WA     │ │ Preprocessing, Quota Management,  │ │  │
│  │  │ Zone Validation        │ │ Annotated Image Generation        │ │  │
│  │  └────────────────────────┘ └───────────────────────────────────┘ │  │
│  │  ┌────────────────────────┐ ┌───────────────────────────────────┐ │  │
│  │  │ AuthService (218L)     │ │ CameraService (260L)              │ │  │
│  │  └────────────────────────┘ └───────────────────────────────────┘ │  │
│  └───────────────────────────────────┬────────────────────────────────┘  │
│                                      │                                   │
│  ┌───────────────────────────────────▼────────────────────────────────┐  │
│  │                   DATABASE & CACHE LAYER                           │  │
│  │                                                                    │  │
│  │  ┌─────────────────────────────────┐ ┌──────────────────────────┐  │  │
│  │  │ PostgreSQL 15 (SQLAlchemy ORM)   │ │ Redis 7 Cache            │  │  │
│  │  │ Alembic Migrations (8 Tables)   │ │ Leaderboard Cache        │  │  │
│  │  └─────────────────────────────────┘ └──────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Trained YOLO11 Model & Benchmark Metrics

### Model Details
- **Architecture**: Ultralytics YOLO11 (`yolo11n.pt`)
- **Training Epochs**: 30 full epochs
- **Input Resolution**: `896x896` pixels
- **Weight File Location**: `runs/detect/archery_yolo11/weights/best.pt`

### Benchmark Metric Table
| Metric | Score | Percentage | Description |
|---|---|---|---|
| **mAP50** | **0.9781** | **97.8%** | Mean Average Precision at IoU threshold 0.50 |
| **Recall** | **0.9724** | **97.2%** | True Positive Rate across all classes |
| **Precision** | **0.9398** | **94.0%** | Ratio of true positives to all positive predictions |
| **mAP50-95** | **0.8946** | **89.5%** | Mean Average Precision averaged across IoU 0.50:0.95 |

### Class Index Mapping (6 Classes)
| Class Index | Class Name | Description | Color Code / Ring Region |
|---|---|---|---|
| `0` | `2_ring` | Zone 2 Ring | Outer white ring boundary |
| `1` | `4_ring` | Zone 4 Ring | Inner black ring boundary |
| `2` | `6_ring` | Zone 6 Ring | Inner blue ring boundary |
| `3` | `7_ring` | Zone 7 Ring | Outer red ring boundary |
| `4` | `arrow` | Arrow Shaft & Tip | Physical arrow object on target face |
| `5` | `bullseye` | Bullseye Center | Gold / Yellow center area (Zone 10 / X) |

### Preprocessing & Training Scripts
1. **Dataset Converter (`scripts/prepare_dataset.py`)**:
   Standardizes 1,806 multi-point polygon annotations across train (353), valid (76), and test (75) split text files into 5-token YOLO normalized bounding box format (`cls xc yc w h`).
2. **Trainer Script (`scripts/train_yolo.py`)**:
   Executes 30-epoch training on `Data/data.yaml` at image resolution `896x896` and exports the best weights to `runs/detect/archery_yolo11/weights/best.pt`.
3. **Evaluation Script (`scripts/evaluate_yolo.py`)**:
   Runs inference validation over the test split and outputs mAP, precision, and recall metrics.

---

## 3. Core Detection & Scoring Pipeline Deep-Dive

### Pipeline Stages

#### STAGE 1: Preprocessing & Image Normalization
- Accepts raw image input (bytes, file path, or NumPy ndarray).
- Resizes image to maximum dimension `1024px` while preserving aspect ratio.
- Normalizes lighting across images:
  - **Gamma Correction**: Adjusts dark or overexposed images dynamically.
  - **CLAHE (Contrast Limited Adaptive Histogram Equalization)**: Applied on LAB color space L-channel.
  - **Gray-World White Balance**: Corrects color casts from indoor fluorescent or outdoor sunlight.
  - **Bilateral Filtering**: Reduces high-frequency noise while preserving edge boundaries.

#### STAGE 2: Target Center & Ring Geometry Extrapolation
- Executed by `_detect_target_from_yolo()` in [src/services/yolo_detection_service.py](file:///c:/Users/BS01318/OneDrive%20-%20Brain%20Station%2023/Documents/GitHub/SPL-3/src/services/yolo_detection_service.py).
- Extracts bounding box center coordinates `(xc, yc)` and dimensions `(w, h)` for ring predictions (`bullseye`, `7_ring`, `6_ring`, `4_ring`, `2_ring`).
- Computes target center `(cx, cy)` as the weighted consensus of ring centers.
- Extrapolates concentric semi-major axis `a_outer` and semi-minor axis `b_outer` based on World Archery relative ring ratios:
  - `bullseye` radius = `0.192 * outer_radius`
  - `7_ring` radius = `0.384 * outer_radius`
  - `6_ring` radius = `0.480 * outer_radius`
  - `4_ring` radius = `0.672 * outer_radius`
  - `2_ring` radius = `0.864 * outer_radius`

#### STAGE 3: Arrow Bbox Crop Refinement & Proximity Tip Mapping
- Executed by `_detect_arrows_hybrid()` and `_refine_arrow_tip_locally()`.
- For each YOLO detected `arrow` bounding box (`cls 4`):
  1. Crops region `[y1:y2, x1:x2]` from bilateral enhanced image.
  2. Applies Canny edge detection (`threshold1=30`, `threshold2=110`).
  3. Detects candidate shaft lines using `cv2.HoughLinesP`.
  4. Merges collinear line segments and selects the longest shaft line `(lx1, ly1, lx2, ly2)`.
  5. If lines are not found, falls back to `cv2.findContours` aspect ratio filtering (`aspect > 2.0`) and fits a line using `cv2.fitLine`.
  6. Executes `_shaft_line_to_tip(x1, y1, x2, y2, target)`:
     - Calculates Euclidean distances `d1 = hypot(x1-cx, y1-cy)` and `d2 = hypot(x2-cx, y2-cy)`.
     - Picks the endpoint closest to `(cx, cy)` as the exact arrow entry tip `(tip_x, tip_y)`.

#### STAGE 4: Adaptive Tip NMS Deduplication
- Executed by `_deduplicate_arrows()`.
- Sorts candidate arrows in descending order of confidence score.
- Computes an adaptive distance merge threshold: `tip_thresh = max(15.0, 25.0 * target_scale)`.
- Eliminates duplicate candidate tips falling within `tip_thresh` pixels of an already selected arrow tip.

#### STAGE 5: World Archery (WA) Zone & Score Calculation
- Computes ellipse-normalized distance `norm_dist` from arrow tip `(tip_x, tip_y)` to target center `(cx, cy)`:
  $$\Delta x = \text{tip\_x} - cx, \quad \Delta y = \text{tip\_y} - cy$$
  $$\text{norm\_dist} = \sqrt{\left(\frac{\Delta x}{a\_outer}\right)^2 + \left(\frac{\Delta y}{b\_outer}\right)^2}$$

- Maps `norm_dist` to World Archery standard zones:
  - **Zone 10 (X Ring)**: `0.000` to `0.048` (`10` points, inner bullseye)
  - **Zone 10**: `0.048` to `0.096` (`10` points)
  - **Zone 9**: `0.096` to `0.192` (`9` points)
  - **Zone 8**: `0.192` to `0.288` (`8` points)
  - **Zone 7**: `0.288` to `0.384` (`7` points)
  - **Zone 6**: `0.384` to `0.480` (`6` points)
  - **Zone 5**: `0.480` to `0.576` (`5` points)
  - **Zone 4**: `0.576` to `0.672` (`4` points)
  - **Zone 3**: `0.672` to `0.768` (`3` points)
  - **Zone 2**: `0.768` to `0.864` (`2` points)
  - **Zone 1**: `0.864` to `0.960` (`1` point)
  - **Miss**: `> 0.960` (`0` points)

---

## 4. Backend Service Modules & Primary Classes

### `YOLOArrowDetectionService`
- **Location**: [src/services/yolo_detection_service.py](file:///c:/Users/BS01318/OneDrive%20-%20Brain%20Station%2023/Documents/GitHub/SPL-3/src/services/yolo_detection_service.py) (451 lines)
- **Role**: Primary ML detection service loading `runs/detect/archery_yolo11/weights/best.pt`.
- **Outputs**: `DetectionResult` containing `target` (`TargetInfo`), `arrows` (`List[ArrowInfo]`), and method string `yolo11+geometric_yolo11_rings+yolo11_hybrid`.

### `ArrowDetectionService`
- **Location**: `src/services/arrow_detection_service.py` (2,665 lines)
- **Role**: Legacy pure CV multi-method pipeline (Zone Ellipses, Color Segmentation, HoughCircles, Puncture Hole detection). Serves as automatic fallback if YOLO loading is disabled or fails.

### `ImageService`
- **Location**: `src/services/image_service.py` (547 lines)
- **Role**: Directs detection requests to `YOLOArrowDetectionService` when `settings.use_yolo=True`, compresses images, checks storage quotas (10GB), archives images after 90 days, and renders annotated visual images with target ring ellipses, arrow tips, crosshairs, and score overlays.

### `ScoringService`
- **Location**: `src/services/scoring_service.py` (324 lines)
- **Role**: Validates points (0–10), writes score records to PostgreSQL with exponential backoff retries, calculates archer total scores, and invalidates Redis leaderboard cache.

---

## 5. Non-Functional Requirement (NFR) Design Patterns

| Pattern # | Pattern Name | Technical Implementation |
|---|---|---|
| **#1** | DB Connection Resilience | Exponential backoff retry on database connect (`database.py`) |
| **#2** | Scoring Failure Recovery | Auto-retry score recording on failure (`scoring_service.py`) |
| **#4** | Image Fallback Chain | Multi-method detection fallback (`image_service.py`) |
| **#9** | Storage Management | 90-day image archival with tar.gz rotation & 10GB quota enforcement |
| **#10** | Thread Pool Scaling | Configurable `ThreadPoolExecutor` for image processing |
| **#12** | Image Compression | JPEG quality 70 compression for fast network transmission |
| **#13** | Cache Invalidation | Redis-based leaderboard caching with automatic invalidation on score writes |
| **#14** | Connection Pool Tuning | SQLAlchemy `QueuePool` with `pre_ping=True` |
| **#17** | Rate Limiting | SlowAPI per-endpoint request throttling (1,000 req/min) |
| **#18** | Structured Logging | `structlog` JSON formatted logs with unique request correlation IDs |
| **#20** | CORS Security | Configurable origin whitelist middleware |
