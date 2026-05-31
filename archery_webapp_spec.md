# Automated Archery Scoring System — Web Application Specification

> **Purpose:** This document is a complete specification for building the Automated Archery Scoring System as a full-stack web application. The backend runs on a server-connected machine (with cameras physically attached), while the frontend is a browser-based interface accessible from any device on the same network. Any AI assistant or developer should be able to use this document as the sole reference to build the complete system from scratch.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Camera Input System](#4-camera-input-system)
5. [Image Processing Pipeline](#5-image-processing-pipeline)
6. [Scoring Engine](#6-scoring-engine)
7. [User & Session Management](#7-user--session-management)
8. [Image Storage & Record System](#8-image-storage--record-system)
9. [Report System](#9-report-system)
10. [Frontend UI/UX Specification](#10-frontend-uiux-specification)
11. [REST API Specification](#11-rest-api-specification)
12. [WebSocket Specification](#12-websocket-specification)
13. [Database Schema](#13-database-schema)
14. [Configuration System](#14-configuration-system)
15. [Error Handling & Validation](#15-error-handling--validation)
16. [Performance Requirements](#16-performance-requirements)
17. [Security](#17-security)
18. [Testing Requirements](#18-testing-requirements)
19. [Project Directory Structure](#19-project-directory-structure)
20. [Deployment Guide](#20-deployment-guide)
21. [Future Enhancements](#21-future-enhancements)

---

## 1. Project Overview

### 1.1 Summary

The **Automated Archery Scoring System** is a web application that connects to one or more cameras (physically attached to the server machine), streams live video to the browser, and — on a single **[Calculate]** button press — captures a frame, processes it using computer vision, detects arrow positions on the target board, and returns a precise score within one second. All results, annotated images, and reports are displayed in the browser and stored permanently.

The system eliminates manual scoring errors (~15% inconsistency in manual scoring), reduces scoring time from 5–10 minutes per target to under 1 second, and provides a full verifiable photographic audit trail for every score.

### 1.2 Deployment Model

```
[USB / IP Cameras]
       │ physically connected
       ▼
[Backend Server — Python/FastAPI]   ← runs on same machine as cameras
       │ HTTP + WebSocket
       ▼
[Browser — React Frontend]          ← accessible from any device on LAN
```

The backend server handles all camera I/O, image processing, and database operations. The frontend is a browser UI served by the same backend (or a separate static host). Multiple users can access the web interface simultaneously from different devices.

### 1.3 Core User Flow

```
1. Operator opens browser → logs in
2. Selects active session and lane
3. Live camera preview streams in browser via WebSocket/MJPEG
4. Archer shoots arrows
5. Operator presses [Calculate] button
6. Server captures frame, processes it, returns score + annotated image
7. Score and annotated image displayed instantly in browser
8. Report updates live with running totals
9. All records saved automatically
```

### 1.4 User Roles

| Role | Access Level |
|------|-------------|
| **System Admin** | Full access — cameras, users, settings, all data |
| **Tournament Admin** | Create/manage tournaments, sessions, archers, view all scores |
| **Scorer / Operator** | Trigger scoring, confirm/override scores, view reports |
| **Archer** | View own scores, reports, and annotated images only |

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌──────────────────────────────────────────────────────────────────────┐
│                         BROWSER (Any Device)                         │
│                                                                      │
│   React 18 + TypeScript + Tailwind CSS + shadcn/ui                  │
│   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│   │Dashboard │ │ Scoring  │ │ Reports  │ │ Cameras  │ │ Settings │ │
│   │  Page    │ │  Page    │ │  Page    │ │  Page    │ │  Page    │ │
│   └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ │
│        │            │            │            │            │        │
│   Axios (REST API) + WebSocket client (live preview + live scores)  │
└────────────────────────────┬─────────────────────────────────────────┘
                             │ HTTP/S + WebSocket (LAN or localhost)
┌────────────────────────────▼─────────────────────────────────────────┐
│                      BACKEND SERVER (FastAPI / Python)               │
│                                                                      │
│  ┌─────────────┐  ┌──────────────┐  ┌─────────────┐  ┌───────────┐ │
│  │   Camera    │  │    Image     │  │   Scoring   │  │  Report   │ │
│  │  Manager   │  │  Processing  │  │   Engine    │  │ Generator │ │
│  │(OpenCV cap)│  │  Pipeline    │  │(Euclidean)  │  │(PDF/JSON) │ │
│  └──────┬──────┘  └──────┬───────┘  └──────┬──────┘  └─────┬─────┘ │
│         │                │                  │               │       │
│  ┌──────▼──────────────────▼──────────────────▼───────────────▼─────┐│
│  │                     Service Layer                                 ││
│  │         (business logic, orchestration, auth middleware)          ││
│  └──────────────────────────────┬────────────────────────────────────┘│
│                                 │                                    │
│  ┌──────────────────────────────▼────────────────────────────────────┐│
│  │                       Data Layer                                  ││
│  │    SQLAlchemy ORM  ──►  SQLite (dev) / PostgreSQL (prod)          ││
│  │    File System     ──►  storage/ (images, reports, exports)       ││
│  └───────────────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────────┘
        │
[USB Cameras / IP Cameras / Webcams] — physically attached to server
```

### 2.2 Component Responsibilities

| Component | Responsibility |
|-----------|---------------|
| **Camera Manager** | Enumerate USB/IP cameras, stream MJPEG to WebSocket, capture full-res frames on demand |
| **Image Processing Pipeline** | Preprocess frame → detect rings → detect arrows |
| **Scoring Engine** | Map arrow positions to zones using Euclidean distance, compute confidence |
| **Report Generator** | Build PDF/CSV/JSON reports from score records |
| **Service Layer** | Business logic: session flow, overrides, user permissions, data orchestration |
| **REST API** | Expose all operations as HTTP endpoints (auth, cameras, scoring, sessions, reports) |
| **WebSocket Server** | Stream live camera previews and live score updates to connected browsers |
| **React Frontend** | Browser UI — camera preview, score display, reports, user management |

### 2.3 Full Processing Flow

```
Browser: [Calculate] clicked
       │
       ▼ POST /api/v1/score/calculate
Backend: Camera Manager
       ├── Trigger capture on assigned camera
       ├── Burst mode: capture 3 frames, select sharpest (Laplacian variance)
       └── Raw frame → Image Processing Pipeline
              │
              ▼
       [1. PREPROCESSING]
          ├── Resize to 1280px width
          ├── Assess lighting (DARK / BRIGHT / NORMAL / UNEVEN)
          ├── Apply adaptive corrections:
          │     Grayscale, Gaussian blur, CLAHE, Gamma correction,
          │     Bilateral filter, Adaptive threshold, Histogram EQ
          └── Perspective correction (homography)
              │
              ▼
       [2. CIRCLE DETECTION]
          ├── Hough Circle Transform → detect 10 rings
          ├── Ellipse fitting (fallback if < 8 circles found)
          ├── Validate concentric alignment (±10px tolerance)
          └── Output: ring list + ring_center {x, y}
              │
              ▼
       [3. ARROW DETECTION]
          ├── Canny + Circular Hough → arrow hole candidates
          ├── SIFT keypoints → additional candidates
          ├── Morphological segmentation → additional candidates
          ├── Fuse all candidates
          └── NMS (IoU threshold=0.3) → final impact points + confidence
              │
              ▼
       [4. SCORING ENGINE]
          ├── Euclidean distance: each arrow → ring center
          ├── Zone assignment: innermost ring containing the arrow
          ├── Confidence = f(boundary distance, detection confidence)
          └── Aggregate total score
              │
              ▼
       [5. OUTPUT GENERATION]
          ├── Draw annotated PNG (rings, arrow markers, score labels)
          ├── Save raw + annotated images to storage/
          ├── Insert score record into database
          └── Return JSON response to browser
              │
              ▼
Browser: Display annotated image + score table + running total
```

---

## 3. Technology Stack

### 3.1 Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.11+ |
| Web framework | FastAPI | 0.110+ |
| ASGI server | Uvicorn | latest |
| Image processing | OpenCV (cv2) | 4.8+ |
| Numerical computing | NumPy | 1.26+ |
| Scientific computing | SciPy | 1.12+ |
| Camera interface | OpenCV VideoCapture | (bundled) |
| Database ORM | SQLAlchemy | 2.0+ |
| Database (dev) | SQLite | 3.x |
| Database (prod) | PostgreSQL | 15+ |
| Background tasks | FastAPI BackgroundTasks (simple) or Celery + Redis (heavy load) |
| PDF generation | WeasyPrint | latest |
| JWT auth | python-jose + passlib | latest |
| Password hashing | bcrypt (via passlib) | latest |
| Configuration | PyYAML | latest |
| Logging | structlog | latest |
| CORS | FastAPI CORSMiddleware | built-in |
| Static file serving | FastAPI StaticFiles | built-in |

### 3.2 Frontend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | React | 18+ |
| Language | TypeScript | 5+ |
| Build tool | Vite | 5+ |
| UI components | shadcn/ui | latest |
| Styling | Tailwind CSS | 3+ |
| HTTP client | Axios | latest |
| WebSocket | native browser WebSocket API | — |
| Charts | Recharts | latest |
| State management | Zustand | latest |
| Routing | React Router v6 | latest |
| Forms | React Hook Form + Zod | latest |
| Image viewer | react-medium-image-zoom | latest |
| Notifications | react-hot-toast | latest |
| Icons | Lucide React | latest |

### 3.3 Infrastructure

| Component | Technology |
|-----------|-----------|
| Containerization | Docker + Docker Compose |
| Reverse proxy | Nginx (production) |
| Storage | Local filesystem (`storage/`) served via authenticated API |
| Environment config | `.env` file (never committed) |

---

## 4. Camera Input System

### 4.1 Camera Manager Requirements

The backend Camera Manager must support:
- **Multiple simultaneous cameras** — minimum 4 concurrent feeds
- **USB/webcam cameras** — via `cv2.VideoCapture(device_index)`
- **IP/network cameras** — via RTSP stream URL `cv2.VideoCapture("rtsp://...")`
- **HTTP MJPEG streams** — `cv2.VideoCapture("http://...")`
- **Camera-to-lane assignment** — each camera is assigned to a specific archery lane and archer for the duration of a session

### 4.2 Camera Configuration

Camera settings are persisted in the database and YAML config. Each camera record:

```yaml
cameras:
  - id: "cam_001"
    label: "Lane 1 — Target A"
    type: "usb"                    # usb | rtsp | http_mjpeg
    device_index: 0                # USB only
    stream_url: null               # RTSP/HTTP only: "rtsp://192.168.1.10/stream"
    capture_resolution:
      width: 1920
      height: 1080
    preview_resolution:
      width: 640
      height: 480
    fps: 30
    auto_focus: true
    brightness: 50
    contrast: 50
    exposure: -1                   # -1 = auto
    flip_horizontal: false
    flip_vertical: false
    capture_delay_ms: 200          # wait N ms after button press before capturing
    capture_mode: "burst"          # single | burst
    burst_frames: 3
```

### 4.3 Camera Enumeration on Startup

When the backend starts, the Camera Manager must:
1. Probe USB indices 0–9 using `cv2.VideoCapture(i)` and record all that open successfully
2. Attempt connection to all saved RTSP/HTTP URLs from the database
3. Store each camera's status: `connected | disconnected | error`
4. Re-probe disconnected cameras every 30 seconds (background thread)
5. Broadcast status changes to all connected browsers via WebSocket

### 4.4 Live Preview Streaming (Browser)

The browser receives a live camera preview via WebSocket:

- **WebSocket endpoint:** `ws://{host}/ws/camera/{camera_id}/preview`
- Backend sends JPEG-encoded frames at **15 fps**
- Frame is encoded as binary (JPEG bytes) sent as WebSocket binary message
- Frontend renders frames into an `<img>` tag or `<canvas>` element by creating object URLs
- Preview shows a **circular targeting overlay** (CSS or canvas overlay) to help center the target
- **Digital zoom:** frontend crops and scales the stream client-side (no server load)

### 4.5 Capture Trigger — [Calculate] Button

When the user presses **[Calculate]**:

```
Browser: POST /api/v1/score/calculate  { camera_id, session_id, end_number, archer_id }
Server:
  1. Pause preview stream briefly (optional, avoids frame conflict)
  2. Camera capture:
     - Burst mode: capture 3 full-resolution frames (200ms apart)
     - Select sharpest frame: highest Laplacian variance score
     - Single mode: capture 1 frame immediately after capture_delay_ms
  3. Pass selected frame to Image Processing Pipeline
  4. Return result as JSON (score + annotated_image_url)
Browser: Display result immediately
```

### 4.6 Multi-Camera Simultaneous Capture

- **Simultaneous:** POST `/api/v1/score/calculate-all` triggers all active cameras in parallel (uses `asyncio.gather` or threading)
- **Individual:** Each camera card on the scoring page has its own **[Calculate]** button
- Setting `capture_mode: simultaneous | individual` configures default behavior

---

## 5. Image Processing Pipeline

### 5.1 Preprocessing Module

**Input:** Raw BGR frame from camera capture (any resolution)
**Output:** Normalized grayscale image ready for detection

#### Step 1 — Resolution Normalization
```python
TARGET_WIDTH = 1280
scale = TARGET_WIDTH / frame.shape[1]
frame = cv2.resize(frame, (TARGET_WIDTH, int(frame.shape[0] * scale)))
```

#### Step 2 — Lighting Assessment
```python
gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
mean_brightness = np.mean(gray)
std_quadrant = compute_quadrant_std(gray)  # measure unevenness

if mean_brightness < 80:
    condition = "DARK"
elif mean_brightness > 180:
    condition = "BRIGHT"
elif std_quadrant > 40:
    condition = "UNEVEN"
else:
    condition = "NORMAL"
```

#### Step 3 — Adaptive Correction (7 methods applied conditionally)

| # | Method | Condition | OpenCV Call |
|---|--------|-----------|-------------|
| 1 | Grayscale conversion | Always | `cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)` |
| 2 | Gaussian blur | Always | `cv2.GaussianBlur(img, (5,5), 0)` |
| 3 | CLAHE | DARK or UNEVEN | `clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8)); clahe.apply(gray)` |
| 4 | Gamma correction | DARK or BRIGHT | `output = 255 * (input/255) ** gamma` where γ=0.5 (dark), γ=1.5 (bright) |
| 5 | Bilateral filter | UNEVEN | `cv2.bilateralFilter(img, 9, 75, 75)` |
| 6 | Adaptive threshold | LOW CONTRAST | `cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2)` |
| 7 | Histogram equalization | DARK | `cv2.equalizeHist(gray)` |

#### Step 4 — Perspective Correction
```python
# Auto-detect four corners of target board using contour analysis
# Apply homography transform to rectify perspective
M = cv2.getPerspectiveTransform(src_pts, dst_pts)
corrected = cv2.warpPerspective(image, M, (target_w, target_h))
# If auto-detection fails: use raw image + set flag perspective_corrected=False
```

### 5.2 Circle Detection Module

**Input:** Preprocessed grayscale image
**Output:** `ring_center {x, y}`, `rings [{center_x, center_y, radius, zone_number}]`

```python
# Primary method: Hough Circle Transform
circles = cv2.HoughCircles(
    image, cv2.HOUGH_GRADIENT,
    dp=1, minDist=20,
    param1=50, param2=30,
    minRadius=10, maxRadius=int(min(h, w) / 2)
)

# Validation
# 1. All circles must share center within 10px tolerance
# 2. Radii must be approximately evenly spaced (±15%)
# 3. Expected: 10 rings + X ring

# Fallback if < 8 rings found:
#   Use cv2.fitEllipse on detected contours
```

**Ring zone mapping (innermost to outermost):**
```
Ring index 0  → Zone X  (score: 10, bonus flag)
Ring index 1  → Zone 10
Ring index 2  → Zone 9
...
Ring index 10 → Zone 1
```

**Flags:**
- `LOW_RING_CONFIDENCE` — fewer than 8 rings detected
- `ELLIPSE_FALLBACK` — ellipse fitting used instead of circles
- `CENTER_OFFSET` — detected center is offset from image center by more than 20%

### 5.3 Arrow Detection Module

**Input:** Preprocessed image + ring center
**Output:** `[{x, y, confidence, detection_methods[]}]`

#### Method 1 — Canny + Circular Hough Transform
```python
edges = cv2.Canny(image, threshold1=50, threshold2=150)
circles = cv2.HoughCircles(
    edges, cv2.HOUGH_GRADIENT, dp=1, minDist=15,
    param1=50, param2=15, minRadius=3, maxRadius=25
)
```

#### Method 2 — SIFT Keypoint Detection
```python
sift = cv2.SIFT_create()
keypoints, _ = sift.detectAndCompute(image, None)
# Arrow holes: small (3–20px), high contrast keypoints
arrow_kps = [kp for kp in keypoints if 3 < kp.size < 20]
```

#### Method 3 — Morphological Segmentation
```python
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
# Keep contours with area 10–300 px² (arrow holes)
```

#### Fusion & Non-Maximum Suppression
```python
# Merge all candidates from 3 methods
# Apply NMS: IoU threshold = 0.3, suppress weaker overlapping detections

# Confidence assignment:
# Detected by all 3 methods  → confidence = 0.98
# Detected by 2 methods      → confidence = 0.85
# Detected by 1 method only  → confidence = 0.60  [FLAG: LOW_CONFIDENCE]
```

### 5.4 Scoring Engine

**Input:** Arrow points `[{x, y, confidence}]` + ring center + ring radii
**Output:** Per-arrow scores + total

```python
import math

def assign_zone(arrow_x, arrow_y, ring_center_x, ring_center_y, ring_radii_sorted):
    """
    ring_radii_sorted: list of radii from smallest (X ring) to largest (zone 1)
    """
    distance = math.sqrt((arrow_x - ring_center_x)**2 + (arrow_y - ring_center_y)**2)
    for idx, radius in enumerate(ring_radii_sorted):
        if distance <= radius:
            zone_score = 10 - idx   # idx 0 = X/10, idx 9 = zone 1
            is_x = (idx == 0)
            return zone_score, is_x, distance
    return 0, False, distance       # MISS — outside all rings

def compute_confidence(distance, inner_r, outer_r, detection_conf):
    zone_width = outer_r - inner_r
    margin = min(abs(distance - inner_r), abs(distance - outer_r)) / zone_width
    spatial_conf = min(margin * 2, 1.0)
    return round((spatial_conf + detection_conf) / 2, 3)
```

#### Standard WA Archery Target Zones

| Zone | Score | Ring Color | Notes |
|------|-------|-----------|-------|
| X | 10 | Gold (inner) | Bonus flag, tiebreaker |
| 10 | 10 | Gold | |
| 9 | 9 | Gold | |
| 8 | 8 | Red | |
| 7 | 7 | Red | |
| 6 | 6 | Blue | |
| 5 | 5 | Blue | |
| 4 | 4 | Black | |
| 3 | 3 | Black | |
| 2 | 2 | White | |
| 1 | 1 | White | |
| M | 0 | Outside | MISS |

---

## 6. User & Session Management

### 6.1 User Roles & Permissions

```
SYSTEM_ADMIN
  ├── All permissions
  ├── Create/delete/edit users
  ├── Configure cameras
  └── Manage system settings

TOURNAMENT_ADMIN
  ├── Create/manage tournaments and sessions
  ├── Register archers
  ├── View all scores, all reports
  └── Export all data

SCORER / OPERATOR
  ├── Trigger scoring (Calculate button)
  ├── Assign cameras to archers in a session
  ├── Override scores (logged)
  ├── View/print reports
  └── Cannot manage users or cameras

ARCHER
  ├── View own scores and history only
  ├── Download own PDF report
  └── View own annotated images
```

### 6.2 Session Hierarchy

```
Tournament
  └── Session  (e.g. "Morning Round — 70m")
        ├── name, distance, end_count, arrows_per_end, target_face_cm
        ├── status: pending | active | completed
        ├── Camera assignments: [cam_id → archer_id, lane_number]
        └── Ends: [End 1, End 2, ..., End N]
                   └── Each End: [Arrow 1, Arrow 2, Arrow 3]
                                  └── {zone, score, confidence, position}
```

### 6.3 Session Operational Flow

```
1.  Admin creates Tournament
2.  Admin creates Session (sets end_count, arrows_per_end, distance)
3.  Admin registers archers and assigns them to the session
4.  Operator assigns cameras to lanes/archers on the Scoring page
5.  Admin starts session → status becomes "active"
6.  End 1 begins — archers shoot their arrows
7.  Operator presses [Calculate] for each camera (or [Calculate All])
8.  System processes and returns scores for all targets
9.  Operator reviews results — confirms or overrides
10. [Next End] advances to End 2
11. Steps 6–10 repeat for all ends
12. After final end → Admin clicks [End Session]
13. Final session report auto-generated
```

### 6.4 Score Override

Any SCORER or higher can override a computed score:
- Select an arrow result → click **[Override]**
- Enter new score (0–10 or X)
- Select reason: `"Detection error"` | `"Arrow touched line"` | `"System error"` | `"Other"`
- Optional free-text note
- Override is saved to `override_logs` table
- Original score retained; override score used in all report calculations
- Report displays overridden arrows with ⚠ symbol and reason

---

## 7. Image Storage & Record System

### 7.1 Storage Directory Structure

```
storage/
├── raw/
│   └── YYYY/MM/DD/{session_id}/
│       └── {camera_id}_{timestamp_ms}.jpg       ← original capture
│
├── annotated/
│   └── YYYY/MM/DD/{session_id}/
│       └── {score_id}_annotated.png             ← processed with overlays
│
├── thumbnails/
│   └── {score_id}_thumb.jpg                     ← 200×200 preview
│
└── exports/
    └── {session_id}/
        ├── {session_id}_report.pdf
        ├── {session_id}_scores.csv
        └── {session_id}_scores.json
```

All storage paths are served via authenticated API endpoints — never as public static files.

### 7.2 Image Record (database)

```json
{
  "image_id": "uuid",
  "session_id": "uuid",
  "camera_id": "cam_001",
  "archer_id": "uuid",
  "end_number": 3,
  "captured_at": "2026-05-19T10:30:00Z",
  "raw_path": "storage/raw/2026/05/19/{session_id}/cam_001_103000.jpg",
  "annotated_path": "storage/annotated/2026/05/19/{session_id}/{score_id}_annotated.png",
  "thumbnail_path": "storage/thumbnails/{score_id}_thumb.jpg",
  "resolution": { "width": 1920, "height": 1080 },
  "capture_mode": "burst",
  "burst_frames_captured": 3,
  "selected_frame_sharpness": 342.7,
  "lighting_condition": "NORMAL",
  "preprocessing_applied": ["grayscale", "clahe", "gaussian_blur"],
  "perspective_corrected": true,
  "processing_duration_ms": 847
}
```

### 7.3 Annotated Image Specification

The annotated PNG output must contain:

| Element | Description |
|---------|-------------|
| Detected rings | Colored circles matching WA zone colors (gold/red/blue/black/white) with zone number labels |
| Ring center | Red crosshair (+) at computed center |
| Arrow markers | Filled circle at each impact point — green (≥0.85 conf), yellow (0.60–0.84), red (<0.60) |
| Score labels | Zone + score next to each arrow: `"9 pts"` |
| Confidence label | Small text below score: `"97%"` |
| End total | Top-right corner: `"End Total: 27"` |
| Timestamp | Bottom-left: `"2026-05-19 10:30:15"` |
| Archer + session | Bottom-right: `"Shaikhul — End 3"` |
| Warning banner | Orange banner at top: `"⚠ Review Recommended"` if any confidence < 0.60 |

### 7.4 Retention & Quota

- Raw images: **90 days** (configurable)
- Annotated images: **indefinite**
- Thumbnails: **indefinite**
- Export files: **30 days** (regeneratable on demand)
- Default storage quota: **10 GB**
- Warning notification in UI at 80% usage
- Auto-archive to `storage/archive/` at 90%

---

## 8. Report System

### 8.1 Report Types

#### End Report
Generated automatically after each end. Contains:
- Annotated image for that end
- Per-arrow scores, zones, confidence values
- End total and running cumulative total

#### Session Report
Generated at session completion (or on demand). Contains:
- Archer info, session details, date/time
- Full score table: `End × Arrow → score` grid with row totals and running total column
- Score distribution chart (bar chart: count per zone)
- Cumulative score trend chart (line chart: total by end)
- Thumbnail grid of all end images (click to enlarge)
- Statistics: average per end, highest end, X count, consistency rating
- Override log (if any overrides occurred)

#### Tournament Summary Report
- Rankings table (archer → total score, X count, rank)
- Per-archer score breakdown
- Top performer statistics
- Export as PDF or CSV

#### Comparison Report
- Side-by-side score comparison of 2+ archers or sessions
- Overlaid trend charts

### 8.2 Report Viewer (In-Browser)

The browser report page renders:

```
┌────────────────────────────────────────────────────────────────┐
│  📊 SESSION REPORT                   [🖨 Print] [⬇ PDF] [⬇ CSV]│
│  Archer: Md. Shaikhul Islam  |  Morning Round  |  2026-05-19  │
├────────────────────────────────────────────────────────────────┤
│  SCORE TABLE                                                   │
│  ┌─────┬──────┬──────┬──────┬───────┬───────────────────────┐ │
│  │ End │  A1  │  A2  │  A3  │ Total │ Running Total         │ │
│  ├─────┼──────┼──────┼──────┼───────┼───────────────────────┤ │
│  │  1  │  9   │  X   │  8   │  27   │  27                   │ │
│  │  2  │  7   │  9   │  9   │  25   │  52                   │ │
│  │  3  │ 10   │ 10   │  8⚠  │  28   │  80                   │ │
│  └─────┴──────┴──────┴──────┴───────┴───────────────────────┘ │
│                                                                │
│  CHARTS                                                        │
│  [Score Distribution — bar chart]  [Trend — line chart]       │
│                                                                │
│  STATISTICS                                                    │
│  Avg/end: 26.7  |  Best end: 28  |  X count: 1  |  ⚠ : 1    │
│                                                                │
│  TARGET IMAGES                                                 │
│  [End 1 🖼] [End 2 🖼] [End 3 🖼] ... (click to enlarge)      │
└────────────────────────────────────────────────────────────────┘
```

### 8.3 Export Formats

| Format | Contents | Endpoint |
|--------|----------|----------|
| **PDF** | Full report with images, charts, tables | `GET /api/v1/reports/session/{id}/pdf` |
| **CSV** | Score grid (end × arrow) | `GET /api/v1/reports/session/{id}/csv` |
| **JSON** | Full machine-readable score data | `GET /api/v1/reports/session/{id}/json` |
| **PNG** | Individual annotated images | `GET /api/v1/images/{image_id}/annotated` |

---

## 10. Frontend UI/UX Specification

### 10.1 Overall Layout

```
┌─────────────────────────────────────────────────────────────────┐
│ 🎯 ArScoreWeb         [Session: Morning Round]   [👤 Admin] [⚙] │
├──────────┬──────────────────────────────────────────────────────┤
│ SIDEBAR  │  MAIN CONTENT AREA                                   │
│          │                                                      │
│ 🏠 Home  │  (page content renders here based on sidebar nav)   │
│ 📷 Score │                                                      │
│ 📊 Reports│                                                     │
│ 🎥 Cameras│                                                     │
│ 👥 Users │                                                      │
│ 🏆 Events│                                                      │
│ ⚙ Settings│                                                     │
└──────────┴──────────────────────────────────────────────────────┘
```

The sidebar collapses to icons-only on narrow screens (tablet/mobile). The app is fully responsive.

### 10.2 Scoring Page (Primary Operational Screen)

This is the main screen used by the operator during a competition:

```
┌─────────────────────────────────────────────────────────────────────┐
│ SESSION: Morning Round  |  End 3 / 12  |  Archer: Shaikhul         │
│ [◀ Prev End]  [End: 3 ▼]  [Next End ▶]              [⏹ End Session]│
├──────────────────────────────┬──────────────────────────────────────┤
│  LANE 1                      │  LANE 2                              │
│  Cam: USB Cam 1  [● LIVE]    │  Cam: IP Cam 1  [● LIVE]            │
│  Archer: Shaikhul            │  Archer: [Select Archer ▼]           │
│                              │                                      │
│  ┌────────────────────────┐  │  ┌────────────────────────┐         │
│  │                        │  │  │                        │         │
│  │   Live camera feed     │  │  │   Live camera feed     │         │
│  │   (640×480 MJPEG       │  │  │   (640×480 MJPEG       │         │
│  │    via WebSocket)      │  │  │    via WebSocket)      │         │
│  │   ◯ targeting overlay  │  │  │   ◯ targeting overlay  │         │
│  │                        │  │  │                        │         │
│  └────────────────────────┘  │  └────────────────────────┘         │
│                              │                                      │
│  [ 📸 CALCULATE ]            │  [ 📸 CALCULATE ]                   │
│                              │                                      │
│  Last Result: 9, X, 8 = 27  │  Last Result: — — — = —             │
│  [View Annotated Image]      │                                      │
├──────────────────────────────┴──────────────────────────────────────┤
│  [ 📸 CALCULATE ALL CAMERAS ]      [ ↺ Retake Last ]  [✓ Confirm All]│
├─────────────────────────────────────────────────────────────────────┤
│  RUNNING TOTALS                                                     │
│  Shaikhul: End 1: 27  End 2: 25  End 3: —   TOTAL: 52             │
│  Archer 2: End 1: 24  End 2: 22  End 3: —   TOTAL: 46             │
└─────────────────────────────────────────────────────────────────────┘
```

**[Calculate] button behavior:**
- Button text changes to `⏳ Analyzing...` with a spinner while processing
- On success: green flash animation, result displays instantly
- On error: red toast notification with error code and guidance

### 10.3 Result Detail Modal

When the operator clicks "View Annotated Image":

```
┌──────────────────────────────────────────────────────────────┐
│  [✕]  END 3 RESULT — Shaikhul Islam          [🖨] [⬇ Image] │
├───────────────────────────────┬──────────────────────────────┤
│                               │  ARROW SCORES                │
│  [Full annotated image —      │  ┌──────┬──────┬─────┬────┐ │
│   zoomable, pannable]         │  │Arrow │ Zone │Score│Conf│ │
│                               │  ├──────┼──────┼─────┼────┤ │
│  Click image to zoom          │  │  1   │  9   │  9  │97% │ │
│                               │  │  2   │  X   │ 10  │99% │ │
│                               │  │  3   │  8   │  8  │63%⚠│ │
│                               │  └──────┴──────┴─────┴────┘ │
│                               │                              │
│                               │  END TOTAL: 27 pts          │
│                               │                              │
│                               │  [✏ Override Score]         │
│                               │  [🔁 Reprocess Image]       │
└───────────────────────────────┴──────────────────────────────┘
```

### 10.4 Camera Management Page

- Grid of camera cards (one per camera)
- Each card shows: live thumbnail, label, type, status indicator, lane assignment
- **[+ Add Camera]** button — form: label, type (USB/RTSP/HTTP), device index or URL, resolution
- **[Test Connection]** button on each card
- **[Edit]** → inline settings form (brightness, contrast, flip, zoom, capture delay)
- **[Remove]** with confirmation dialog
- Status badges: `● Connected` (green) | `● Disconnected` (red) | `⟳ Reconnecting` (amber)

### 10.5 Dashboard Page

```
┌─────────────────────────────────────────────────────────────┐
│  ACTIVE SESSION                    CAMERA STATUS            │
│  Morning Round — 70m               [cam1 ●] [cam2 ●]       │
│  End 3 / 12  |  4 archers          [cam3 ✕] [cam4 ●]       │
│  [▶ Go to Scoring]                                          │
├───────────────────────┬─────────────────────────────────────┤
│  LIVE LEADERBOARD     │  RECENT ENDS                        │
│  1. Shaikhul  52 pts  │  End 3 — Shaikhul: 27 pts  [View]  │
│  2. Archer 2  46 pts  │  End 2 — Shaikhul: 25 pts  [View]  │
│  3. Archer 3  41 pts  │  End 2 — Archer 2: 22 pts  [View]  │
│  4. Archer 4  38 pts  │                                     │
├───────────────────────┴─────────────────────────────────────┤
│  SYSTEM HEALTH                                              │
│  Storage: 2.1 GB / 10 GB  [████░░░░░░] 21%                 │
│  Active cameras: 3 / 4  |  Processing queue: 0 pending     │
└─────────────────────────────────────────────────────────────┘
```

### 10.6 UI States Reference

| State | Behavior |
|-------|----------|
| No active session | Scoring page shows prompt: "No active session. Start a session first." |
| Camera disconnected | Red badge on camera card; Calculate button disabled for that lane |
| Processing | Button → `⏳ Analyzing...` + spinner; UI not blocked (async) |
| Success (high confidence) | Green flash; result card slides in |
| Success (low confidence) | Yellow flash; `⚠ Review Recommended` banner on result |
| Processing error | Red toast: error code + message (e.g., `IMG_001: Ring detection failed`) |
| Session ended | Scoring buttons disabled; "View Final Report" banner shown |

### 10.7 Responsive Behavior

- **Desktop (≥1280px):** Full two-column scoring layout with sidebars
- **Tablet (768–1279px):** Single column, cameras stacked vertically
- **Mobile (< 768px):** Read-only — archers can view scores and reports; scoring not available on mobile

---

## 11. REST API Specification

### 11.1 Base URL and Authentication

```
Base URL: http://{host}:8000/api/v1

Authentication: Bearer JWT token
Header: Authorization: Bearer {access_token}

POST /auth/login
Body:    { "username": "string", "password": "string" }
Returns: { "access_token": "jwt", "token_type": "bearer", "expires_in": 28800, "user": {...} }

POST /auth/refresh
POST /auth/logout
```

### 11.2 Camera Endpoints

```http
GET    /cameras                       # List all cameras with status
POST   /cameras                       # Add new camera (admin only)
GET    /cameras/{id}                  # Get camera config + status
PUT    /cameras/{id}                  # Update camera settings
DELETE /cameras/{id}                  # Remove camera (admin only)
POST   /cameras/{id}/test             # Test camera connection → { connected: bool, error?: str }
POST   /cameras/{id}/capture          # Capture single test frame → { image_url: str }
```

### 11.3 Scoring Endpoints

```http
POST   /score/calculate               # Trigger scoring for one camera
POST   /score/calculate-all           # Trigger all cameras simultaneously
POST   /score/reprocess/{image_id}    # Reprocess an existing image
PUT    /score/{score_id}/override     # Override arrow score (scorer+)
GET    /score/{score_id}              # Get full score record
```

**POST /score/calculate — Request:**
```json
{
  "camera_id": "cam_001",
  "session_id": "uuid",
  "end_number": 3,
  "archer_id": "uuid",
  "capture_mode": "burst"
}
```

**POST /score/calculate — Response:**
```json
{
  "score_id": "uuid",
  "image_id": "uuid",
  "annotated_image_url": "/api/v1/images/uuid/annotated",
  "thumbnail_url": "/api/v1/images/uuid/thumbnail",
  "end_number": 3,
  "arrows": [
    {
      "id": 1,
      "zone": "9",
      "score": 9,
      "confidence": 0.97,
      "position": { "x": 642, "y": 318 },
      "distance_px": 142,
      "flag": null
    },
    {
      "id": 2,
      "zone": "X",
      "score": 10,
      "confidence": 0.99,
      "position": { "x": 648, "y": 495 },
      "distance_px": 18,
      "flag": null
    },
    {
      "id": 3,
      "zone": "8",
      "score": 8,
      "confidence": 0.63,
      "position": { "x": 490, "y": 512 },
      "distance_px": 198,
      "flag": "LOW_CONFIDENCE"
    }
  ],
  "total_score": 27,
  "x_count": 1,
  "processing_time_ms": 847,
  "lighting_condition": "NORMAL",
  "rings_detected": 10,
  "warnings": ["LOW_CONFIDENCE on arrow 3"],
  "captured_at": "2026-05-19T10:30:15Z"
}
```

**PUT /score/{id}/override — Request:**
```json
{
  "arrow_index": 2,
  "new_zone": "9",
  "new_score": 9,
  "reason": "Arrow touched line",
  "note": "Clearly in zone 9 on physical inspection"
}
```

### 11.4 Image Endpoints

```http
GET    /images/{id}/raw               # Serve original captured image (auth required)
GET    /images/{id}/annotated         # Serve annotated image (auth required)
GET    /images/{id}/thumbnail         # Serve 200×200 thumbnail
GET    /images/{id}/metadata          # Get image record JSON
DELETE /images/{id}                   # Delete image + record (admin only)
```

### 11.5 Session & Tournament Endpoints

```http
GET    /tournaments                   # List all tournaments
POST   /tournaments                   # Create tournament
GET    /tournaments/{id}              # Get tournament detail
PUT    /tournaments/{id}              # Update tournament
DELETE /tournaments/{id}              # Delete tournament (admin)

GET    /sessions                      # List sessions (filterable by tournament_id, status)
POST   /sessions                      # Create session
GET    /sessions/{id}                 # Get session detail
PUT    /sessions/{id}                 # Update session
POST   /sessions/{id}/start           # Start session (set status → active)
POST   /sessions/{id}/end             # End session (set status → completed)
GET    /sessions/{id}/scores          # All scores in session (grouped by archer + end)
GET    /sessions/{id}/leaderboard     # Live rankings for session
POST   /sessions/{id}/assign-camera   # Assign camera to archer/lane in this session
DELETE /sessions/{id}/assign-camera/{camera_id}  # Unassign camera
```

### 11.6 User Endpoints

```http
GET    /users                         # List all users (admin)
POST   /users                         # Create user (admin)
GET    /users/{id}                    # Get user profile
PUT    /users/{id}                    # Update user
DELETE /users/{id}                    # Deactivate user (admin)
GET    /users/{id}/scores             # User score history (paginated)
PUT    /users/me/password             # Change own password
```

### 11.7 Report Endpoints

```http
GET    /reports/session/{id}          # Session report JSON
GET    /reports/session/{id}/pdf      # Session report PDF (download)
GET    /reports/session/{id}/csv      # Session scores CSV (download)
GET    /reports/tournament/{id}       # Tournament summary JSON
GET    /reports/tournament/{id}/pdf   # Tournament summary PDF
GET    /reports/comparison            # Compare sessions/archers (query params)
```

### 11.8 System Endpoints

```http
GET    /system/health                 # Server health (CPU, RAM, storage)
GET    /system/storage                # Storage usage breakdown
POST   /system/cameras/scan           # Trigger camera re-enumeration
GET    /system/config                 # Get current config (admin)
PUT    /system/config                 # Update config (admin)
```

---

## 12. WebSocket Specification

### 12.1 Live Camera Preview

**Endpoint:** `ws://{host}:8000/ws/camera/{camera_id}/preview`

**Authentication:** Pass JWT token as query param: `?token={access_token}`

**Server → Client messages:**
- Binary frame: JPEG-encoded frame bytes at 15 fps
- Text frame (JSON): status updates
  ```json
  { "type": "status", "camera_id": "cam_001", "status": "connected" }
  { "type": "status", "camera_id": "cam_001", "status": "capturing" }
  { "type": "error",  "camera_id": "cam_001", "code": "CAM_001", "message": "Camera disconnected" }
  ```

**Client renders frames:**
```javascript
const ws = new WebSocket(`ws://host/ws/camera/${cameraId}/preview?token=${token}`);
ws.binaryType = 'blob';
ws.onmessage = (event) => {
  if (event.data instanceof Blob) {
    const url = URL.createObjectURL(event.data);
    imgElement.src = url;
    // Revoke previous URL to free memory
  }
};
```

### 12.2 Live Score Updates

**Endpoint:** `ws://{host}:8000/ws/session/{session_id}/scores`

**Authentication:** `?token={access_token}`

**Server → Client messages (JSON):**
```json
{ "type": "score_update",
  "score_id": "uuid",
  "archer_id": "uuid",
  "archer_name": "Shaikhul",
  "end_number": 3,
  "total_score": 27,
  "running_total": 80,
  "annotated_thumbnail_url": "/api/v1/images/uuid/thumbnail"
}

{ "type": "session_status", "status": "active", "current_end": 3 }
{ "type": "camera_status", "camera_id": "cam_001", "status": "disconnected" }
{ "type": "leaderboard_update", "rankings": [{ "archer_id": "...", "name": "...", "total": 80, "rank": 1 }] }
```

---

## 13. Database Schema

### users
```sql
CREATE TABLE users (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username      VARCHAR(50) UNIQUE NOT NULL,
    email         VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(100) NOT NULL,
    role          VARCHAR(20) NOT NULL
                  CHECK (role IN ('system_admin','tournament_admin','scorer','archer')),
    club          VARCHAR(100),
    is_active     BOOLEAN DEFAULT TRUE,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### cameras
```sql
CREATE TABLE cameras (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label         VARCHAR(100) NOT NULL,
    type          VARCHAR(20) NOT NULL CHECK (type IN ('usb','rtsp','http_mjpeg')),
    device_index  INTEGER,
    stream_url    VARCHAR(255),
    config_json   JSONB,              -- resolution, fps, flip, etc.
    is_active     BOOLEAN DEFAULT TRUE,
    last_seen_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### tournaments
```sql
CREATE TABLE tournaments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(200) NOT NULL,
    location    VARCHAR(200),
    start_date  DATE,
    end_date    DATE,
    admin_id    UUID REFERENCES users(id),
    status      VARCHAR(20) DEFAULT 'upcoming'
                CHECK (status IN ('upcoming','active','completed')),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### sessions
```sql
CREATE TABLE sessions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tournament_id   UUID REFERENCES tournaments(id),
    name            VARCHAR(200) NOT NULL,
    distance_m      INTEGER,
    end_count       INTEGER DEFAULT 12,
    arrows_per_end  INTEGER DEFAULT 3,
    target_face_cm  INTEGER DEFAULT 122,
    status          VARCHAR(20) DEFAULT 'pending'
                    CHECK (status IN ('pending','active','completed')),
    started_at      TIMESTAMPTZ,
    ended_at        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### session_archers
```sql
CREATE TABLE session_archers (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID REFERENCES sessions(id),
    archer_id   UUID REFERENCES users(id),
    lane_number INTEGER,
    UNIQUE(session_id, archer_id),
    UNIQUE(session_id, lane_number)
);
```

### camera_assignments
```sql
CREATE TABLE camera_assignments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID REFERENCES sessions(id),
    camera_id   UUID REFERENCES cameras(id),
    archer_id   UUID REFERENCES users(id),
    lane_number INTEGER,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(session_id, camera_id)
);
```

### images
```sql
CREATE TABLE images (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id          UUID REFERENCES sessions(id),
    camera_id           UUID REFERENCES cameras(id),
    archer_id           UUID REFERENCES users(id),
    end_number          INTEGER NOT NULL,
    raw_path            VARCHAR(500),
    annotated_path      VARCHAR(500),
    thumbnail_path      VARCHAR(500),
    captured_at         TIMESTAMPTZ NOT NULL,
    processing_ms       INTEGER,
    lighting_condition  VARCHAR(20),
    sharpness_score     FLOAT,
    capture_mode        VARCHAR(20),
    burst_frames        INTEGER,
    perspective_corrected BOOLEAN DEFAULT FALSE,
    preprocessing_json  JSONB,        -- list of methods applied
    created_at          TIMESTAMPTZ DEFAULT NOW()
);
```

### scores
```sql
CREATE TABLE scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id        UUID REFERENCES images(id),
    session_id      UUID REFERENCES sessions(id),
    archer_id       UUID REFERENCES users(id),
    end_number      INTEGER NOT NULL,
    arrows_json     JSONB NOT NULL,
    -- [{id, zone, score, confidence, position_x, position_y, distance_px, flag}]
    total_score     INTEGER NOT NULL,
    arrow_count     INTEGER NOT NULL,
    x_count         INTEGER DEFAULT 0,
    rings_detected  INTEGER,
    warnings_json   JSONB,
    is_overridden   BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### override_logs
```sql
CREATE TABLE override_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    score_id        UUID REFERENCES scores(id),
    overridden_by   UUID REFERENCES users(id),
    original_arrows JSONB,
    new_arrows      JSONB,
    original_total  INTEGER,
    new_total       INTEGER,
    reason          VARCHAR(50) NOT NULL,
    note            TEXT,
    overridden_at   TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 14. Configuration System

All parameters stored in `config.yaml`. Loaded on startup; hot-reload available via admin API.

```yaml
app:
  name: "Archery Scoring System"
  version: "1.0.0"
  debug: false
  host: "0.0.0.0"
  port: 8000
  frontend_origin: "http://localhost:5173"   # CORS allowed origin

database:
  type: "sqlite"                 # sqlite | postgresql
  sqlite_path: "data/archery.db"
  postgres_url: null             # set via DATABASE_URL env var in production

storage:
  base_path: "storage/"
  serve_path: "/api/v1/images"   # URL prefix for image serving
  quota_gb: 10
  warn_at_percent: 80
  raw_retention_days: 90
  annotated_retention_days: -1   # indefinite

cameras:
  capture_mode: "burst"          # single | burst
  burst_frames: 3
  burst_select: "sharpest"
  capture_delay_ms: 200
  preview_fps: 15
  preview_width: 640
  preview_height: 480
  simultaneous_capture: true
  reconnect_interval_sec: 30

processing:
  target_width: 1280
  dark_threshold: 80
  bright_threshold: 180
  hough_dp: 1
  hough_param1: 50
  hough_param2: 30
  nms_iou_threshold: 0.3
  low_confidence_threshold: 0.60
  min_rings_required: 8
  perspective_auto_detect: true

scoring:
  target_type: "WA_10RING"       # WA_10RING | WA_6RING | custom
  ring_count: 10
  x_ring_enabled: true
  arrows_per_end: 3

auth:
  secret_key: "REPLACE_WITH_RANDOM_SECRET"  # use env var in production
  algorithm: "HS256"
  token_expire_hours: 8

logging:
  level: "INFO"
  file: "logs/archery.log"
  max_size_mb: 50
  backup_count: 5
```

**Environment variables (production overrides):**
```bash
DATABASE_URL=postgresql://user:pass@localhost:5432/archery
SECRET_KEY=your-random-secret-key-here
STORAGE_PATH=/var/archery/storage
```

---

## 15. Error Handling & Validation

### 15.1 Error Code Reference

| Code | Category | Description | User-Facing Message |
|------|----------|-------------|-------------------|
| `CAM_001` | Camera | Camera not connected | "Camera disconnected. Check USB connection." |
| `CAM_002` | Camera | Frame capture timeout | "Camera not responding. Retrying..." |
| `CAM_003` | Camera | Frame too dark/blurry | "Image too dark or blurry. Adjust camera." |
| `IMG_001` | Processing | Ring detection failed (< 5 rings) | "Could not detect target rings. Reposition camera." |
| `IMG_002` | Processing | No arrows detected | "No arrows detected. Ensure arrows are in target." |
| `IMG_003` | Processing | Perspective correction failed | "Using uncorrected image. Results may vary." |
| `SCR_001` | Scoring | Arrow outside all rings | "Arrow detected outside target — scored as miss." |
| `SCR_002` | Scoring | Low confidence detection | "Low confidence on arrow N — review recommended." |
| `SYS_001` | System | Storage quota exceeded | "Storage full. Contact administrator." |
| `SYS_002` | System | Database error | "Database error. Please retry." |
| `AUTH_001` | Auth | Invalid credentials | "Incorrect username or password." |
| `AUTH_002` | Auth | Token expired | "Session expired. Please log in again." |

### 15.2 Graceful Degradation

- **Preprocessing failure:** Skip failed methods, proceed with grayscale
- **< 8 rings detected:** Flag `LOW_RING_CONFIDENCE`, attempt ellipse fitting, continue
- **No arrows detected:** Return empty arrows array with `NO_ARROWS_DETECTED` warning; do not block
- **Confidence < 0.60:** Flag arrow for review; include in output with warning
- **Camera disconnects mid-session:** Alert via WebSocket; disable Calculate for that lane; retain last image

### 15.3 Input Validation (API)

- Image dimensions: min 640×480, max 8000×6000 px
- Image file size: max 20 MB
- RTSP/HTTP URL: validated format before save
- Score override: new score 0–10, reason required (not empty)
- End number: must be within `1..session.end_count`
- `arrows_per_end`: must be 3 or 6 for standard sessions

---

## 16. Performance Requirements

| Metric | Requirement |
|--------|------------|
| Single image processing (full pipeline) | < 1 second |
| 24-target batch session | < 15 minutes total |
| Camera preview latency (browser) | < 200 ms |
| Simultaneous camera feeds | ≥ 4 concurrent |
| Concurrent browser users | ≥ 20 |
| REST API response (non-image) | < 200 ms |
| Database query | < 100 ms |
| F1 score (detection accuracy) | ≥ 0.90 |
| Ring detection success rate | ≥ 95% |
| Backend server startup time | < 10 seconds |
| Score update WebSocket broadcast | < 100 ms after processing |

---

## 17. Security

- **JWT authentication** on all API endpoints except `/auth/login` and static frontend assets
- **Token expiry:** 8 hours; refresh token support
- **Passwords:** bcrypt hashed, minimum 8 characters, enforced by API
- **Role-based access control (RBAC):** enforced at service layer, not just frontend
- **CORS:** restrict `allow_origins` to known frontend URL in production
- **Rate limiting:** 100 requests/minute per authenticated user; 10/minute for `/auth/login`
- **Image serving:** all images served via authenticated `/api/v1/images/{id}/...` endpoints; never exposed as public static files
- **SQL injection:** all queries via SQLAlchemy ORM with parameterized statements
- **Override audit log:** immutable — no DELETE endpoint exists for override_logs
- **Sensitive config:** `SECRET_KEY`, `DATABASE_URL` via environment variables only
- **HTTPS:** use TLS termination at Nginx reverse proxy in production
- **WebSocket auth:** JWT passed as query param `?token=` on WS upgrade

---

## 18. Testing Requirements

### 18.1 Backend Tests

| Type | Tool | Coverage Target |
|------|------|----------------|
| Unit — preprocessing | pytest | 90%+ |
| Unit — circle detection | pytest | 90%+ |
| Unit — arrow detection | pytest | 90%+ |
| Unit — scoring engine | pytest | 100% |
| Integration — API endpoints | pytest + httpx | 80%+ |
| Camera mock tests | pytest + `unittest.mock` | All states |
| WebSocket tests | pytest + websockets | Preview + score stream |
| Performance tests | locust | All perf requirements |

### 18.2 Frontend Tests

| Type | Tool |
|------|------|
| Unit — components | Vitest + React Testing Library |
| E2E — scoring flow | Playwright |
| E2E — report generation | Playwright |

### 18.3 Test Dataset

- Minimum 50 annotated archery target images with ground truth scores
- Coverage must include:
  - Lighting: bright sun, indoor dim, uneven shadow, glare
  - Angles: straight-on, 10°, 20°, 30° off-axis
  - Arrow counts: 1, 3, 6 arrows
  - Edge cases: near-boundary arrows, overlapping arrows, damaged target face

---

## 19. Project Directory Structure

```
archery-scoring-system/
│
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app factory, router registration
│   │   ├── config.py                  # Config loader (YAML + env vars)
│   │   ├── database.py                # SQLAlchemy engine + session factory
│   │   │
│   │   ├── api/
│   │   │   ├── deps.py                # FastAPI dependencies (get_db, get_current_user)
│   │   │   ├── routes/
│   │   │   │   ├── auth.py            # /auth/login, /auth/refresh, /auth/logout
│   │   │   │   ├── cameras.py         # /cameras CRUD + /test + /capture
│   │   │   │   ├── scoring.py         # /score/calculate, /score/calculate-all, /override
│   │   │   │   ├── images.py          # /images/{id}/raw, /annotated, /thumbnail
│   │   │   │   ├── sessions.py        # /sessions CRUD + /start + /end + /assign-camera
│   │   │   │   ├── tournaments.py     # /tournaments CRUD
│   │   │   │   ├── users.py           # /users CRUD
│   │   │   │   ├── reports.py         # /reports/session + /tournament + /pdf + /csv
│   │   │   │   └── system.py          # /system/health + /storage + /config
│   │   │   └── websocket.py           # WS /ws/camera/{id}/preview + /ws/session/{id}/scores
│   │   │
│   │   ├── core/
│   │   │   ├── camera_manager.py      # CameraManager: enumerate, stream, capture
│   │   │   ├── preprocessing.py       # Preprocess pipeline (7 methods)
│   │   │   ├── circle_detection.py    # Hough + ellipse fallback
│   │   │   ├── arrow_detection.py     # Canny + SIFT + Morphological + NMS
│   │   │   ├── scoring_engine.py      # Zone mapping, confidence calculation
│   │   │   ├── output_generator.py    # Draw annotated image, generate JSON report
│   │   │   └── report_generator.py    # PDF/CSV/JSON report generation (WeasyPrint)
│   │   │
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── camera.py
│   │   │   ├── tournament.py
│   │   │   ├── session.py
│   │   │   ├── image.py
│   │   │   ├── score.py
│   │   │   └── override_log.py
│   │   │
│   │   ├── schemas/                   # Pydantic request/response models
│   │   │   ├── auth.py
│   │   │   ├── camera.py
│   │   │   ├── scoring.py
│   │   │   ├── session.py
│   │   │   ├── report.py
│   │   │   └── user.py
│   │   │
│   │   ├── services/                  # Business logic layer
│   │   │   ├── auth_service.py
│   │   │   ├── camera_service.py
│   │   │   ├── scoring_service.py     # Orchestrates: capture → pipeline → store → return
│   │   │   ├── session_service.py
│   │   │   ├── report_service.py
│   │   │   └── storage_service.py
│   │   │
│   │   └── utils/
│   │       ├── image_utils.py         # Resize, encode, save helpers
│   │       ├── auth_utils.py          # JWT encode/decode, password hash
│   │       └── logger.py              # structlog setup
│   │
│   ├── tests/
│   │   ├── fixtures/                  # Ground truth annotated images
│   │   ├── test_preprocessing.py
│   │   ├── test_circle_detection.py
│   │   ├── test_arrow_detection.py
│   │   ├── test_scoring_engine.py
│   │   ├── test_api_auth.py
│   │   ├── test_api_scoring.py
│   │   └── test_api_reports.py
│   │
│   ├── alembic/                       # Database migrations
│   │   └── versions/
│   ├── config.yaml
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── main.tsx                   # React entry point
│   │   ├── App.tsx                    # Router setup
│   │   │
│   │   ├── pages/
│   │   │   ├── LoginPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── ScoringPage.tsx        # Main operational page
│   │   │   ├── ReportsPage.tsx
│   │   │   ├── CamerasPage.tsx
│   │   │   ├── UsersPage.tsx
│   │   │   ├── TournamentsPage.tsx
│   │   │   └── SettingsPage.tsx
│   │   │
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── TopBar.tsx
│   │   │   │   └── Layout.tsx
│   │   │   ├── scoring/
│   │   │   │   ├── CameraFeed.tsx     # Live MJPEG preview via WebSocket
│   │   │   │   ├── CalculateButton.tsx
│   │   │   │   ├── ScoreResultCard.tsx
│   │   │   │   ├── ResultModal.tsx    # Annotated image + arrow table
│   │   │   │   ├── OverrideForm.tsx
│   │   │   │   └── RunningTotals.tsx
│   │   │   ├── reports/
│   │   │   │   ├── ScoreTable.tsx
│   │   │   │   ├── DistributionChart.tsx
│   │   │   │   ├── TrendChart.tsx
│   │   │   │   └── ImageGallery.tsx
│   │   │   ├── cameras/
│   │   │   │   ├── CameraCard.tsx
│   │   │   │   └── AddCameraForm.tsx
│   │   │   └── ui/                    # shadcn/ui components
│   │   │
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts        # Generic WS hook
│   │   │   ├── useCameraPreview.ts    # Camera stream hook
│   │   │   ├── useScoreStream.ts      # Live score update hook
│   │   │   └── useAuth.ts
│   │   │
│   │   ├── store/
│   │   │   ├── authStore.ts           # Zustand: user, token
│   │   │   ├── sessionStore.ts        # Zustand: active session, current end
│   │   │   └── cameraStore.ts         # Zustand: camera list, statuses
│   │   │
│   │   ├── api/
│   │   │   ├── client.ts              # Axios instance with auth interceptor
│   │   │   ├── auth.ts
│   │   │   ├── cameras.ts
│   │   │   ├── scoring.ts
│   │   │   ├── sessions.ts
│   │   │   └── reports.ts
│   │   │
│   │   └── types/
│   │       ├── score.ts
│   │       ├── session.ts
│   │       ├── camera.ts
│   │       └── user.ts
│   │
│   ├── public/
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── package.json
│   └── Dockerfile
│
├── storage/                           # Runtime image/report storage (gitignored)
├── logs/                              # Application logs (gitignored)
├── data/                              # SQLite file for development (gitignored)
├── templates/
│   └── report.html                    # WeasyPrint PDF template
├── docker-compose.yml
├── docker-compose.prod.yml
├── nginx.conf                         # Production reverse proxy config
├── .env.example                       # Template for environment variables
├── config.yaml
└── README.md
```

---

## 20. Deployment Guide

### 20.1 Development Setup

```bash
# 1. Clone repository
git clone https://github.com/your-org/archery-scoring-system.git
cd archery-scoring-system

# 2. Backend setup
cd backend
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 3. Copy and configure environment
cp .env.example .env
# Edit .env: set SECRET_KEY, DATABASE_URL if using PostgreSQL

# 4. Initialize database
alembic upgrade head

# 5. Start backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 6. Frontend setup (separate terminal)
cd frontend
npm install
npm run dev                       # Starts on http://localhost:5173

# Open browser: http://localhost:5173
# API docs: http://localhost:8000/docs
```

### 20.2 Production Deployment (Docker)

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d --build

# Services started:
#   - backend:  FastAPI (port 8000, internal)
#   - frontend: Nginx serving built React app (port 80/443, external)
#   - db:       PostgreSQL (port 5432, internal)
#   - redis:    Redis for task queue (port 6379, internal)
```

**docker-compose.yml (development):**
```yaml
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./storage:/app/storage
      - ./logs:/app/logs
      - ./data:/app/data
      - /dev/video0:/dev/video0    # USB camera passthrough
      - /dev/video1:/dev/video1
    devices:
      - /dev/video0
      - /dev/video1
    environment:
      - CONFIG_PATH=/app/config.yaml
    env_file:
      - .env

  frontend:
    build: ./frontend
    ports:
      - "5173:5173"
    environment:
      - VITE_API_URL=http://localhost:8000
```

**Camera device passthrough** is required when running in Docker — add `/dev/videoN` devices to the backend container.

### 20.3 Nginx Configuration (Production)

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Serve React frontend
    location / {
        root /var/www/archery/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    # Proxy API to FastAPI backend
    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    # Proxy WebSocket connections
    location /ws/ {
        proxy_pass http://backend:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "Upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;    # Keep WS connections alive
    }
}
```

---

## 21. Future Enhancements

| Feature | Description | Priority |
|---------|-------------|----------|
| **YOLOv8 detection** | Replace Hough-based arrow detection with trained YOLOv8 model for higher accuracy in difficult conditions | High |
| **Auto-calibration** | Detect ring radii automatically from known target face size via QR code or fiducial markers | High |
| **Arrow grouping analysis** | Measure grouping radius, group center, consistency score per end | High |
| **Mobile view** | Full scoring capability on tablet/phone via PWA (progressive web app) | Medium |
| **Cloud backup** | Optional S3/GCS sync for images and database backup | Medium |
| **National ranking API** | Push scores to World Archery or national federation endpoints | Medium |
| **Lane QR auto-assign** | Camera reads QR code on archer badge to auto-assign lane | Medium |
| **Video mode** | Process RTSP video stream and detect arrow landing events automatically | Low |
| **Predictive analytics** | ML trend analysis: predict score, identify weaknesses, recommend training | Low |
| **Multi-site** | Centralized cloud backend supporting multiple physical archery ranges | Low |

---

## Appendix A — Standard WA Target Face Specifications

| Parameter | 122 cm face | 80 cm face | 40 cm face |
|-----------|------------|-----------|-----------|
| Outermost ring (1) diameter | 122 cm | 80 cm | 40 cm |
| Ring width | 6.1 cm | 4.0 cm | 2.0 cm |
| Zone 10 (yellow) diameter | 12.2 cm | 8.0 cm | 4.0 cm |
| X ring diameter | ~4.8 cm | ~3.2 cm | ~1.6 cm |
| Common shooting distances | 70 m, 60 m | 50 m, 30 m | 18 m (indoor) |

---

## Appendix B — Algorithm References

1. **Hough Circle Transform:** Duda, R.O., Hart, P.E. (1972). "Use of the Hough transformation to detect lines and curves in pictures." *Communications of the ACM*.
2. **SIFT:** Lowe, D.G. (2004). "Distinctive Image Features from Scale-Invariant Keypoints." *International Journal of Computer Vision*.
3. **CLAHE:** Zuiderveld, K. (1994). "Contrast Limited Adaptive Histogram Equalization." *Graphics Gems IV*.
4. **NMS:** Neubeck, A., Van Gool, L. (2006). "Efficient Non-Maximum Suppression." *18th ICPR*.
5. **YOLOv8 (future):** Jocher, G. et al. (2023). "Ultralytics YOLOv8." Ultralytics.
6. **Related work:** S. Adam, N. A. Fitri, S. Bibi, and M. R. Sufandi, "Real-Time Arrow Detection and Scoring on Archery Targets Using YOLOv8 with Euclidean Distance-Based Zone Estimation," *JAIC*, vol. 9, no. 6, pp. 3669–3680, Dec. 2025.

---

*Document version: 2.0 (Web App) | Last updated: May 2026 | System: Automated Archery Scoring System*
