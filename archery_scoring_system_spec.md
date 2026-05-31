# Automated Archery Scoring System — Full Application Specification

> **Purpose:** This document is a complete specification for developing a desktop/web application for automated archery score detection using computer vision. It covers system architecture, all features, data models, UI/UX flows, API contracts, and development guidelines. Any AI or developer should be able to use this document as the sole reference to build the full application.

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
10. [Application UI/UX Specification](#10-application-uiux-specification)
11. [REST API Specification](#11-rest-api-specification)
12. [Data Models & Database Schema](#12-data-models--database-schema)
13. [Configuration System](#13-configuration-system)
14. [Error Handling & Validation](#14-error-handling--validation)
15. [Performance Requirements](#15-performance-requirements)
16. [Security Considerations](#16-security-considerations)
17. [Testing Requirements](#17-testing-requirements)
18. [Directory Structure](#18-directory-structure)
19. [Future Enhancements](#19-future-enhancements)

---

## 1. Project Overview

### 1.1 Summary

The **Automated Archery Scoring System** is a computer application that connects to one or more cameras, captures a photograph of an archery target board on demand, and uses computer vision to automatically detect scoring rings, locate arrow impact points, and produce a precise score — all within one second per target.

The system eliminates manual scoring errors (~15% inconsistency), reduces scoring time from 5–10 minutes per target to under 1 second, and provides a verifiable photographic audit trail for every score.

### 1.2 Core User Flow

```
Camera connected → Live preview shown → User presses [Calculate] →
System captures frame → Image processed → Score computed →
Annotated result displayed → Report generated → Record saved
```

### 1.3 Primary Users

| Role | Description |
|------|-------------|
| **Archer** | Views their own scores and history |
| **Scorer / Operator** | Controls cameras, triggers scoring, manages sessions |
| **Tournament Admin** | Manages users, exports reports, views all scores |
| **System Admin** | Configures cameras, system settings, user accounts |

### 1.4 Supported Deployment Modes

- **Desktop application** (primary) — Python + PyQt6 or Electron
- **Web application** (secondary) — FastAPI backend + React frontend
- **CLI mode** — headless batch processing for automation

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        APPLICATION LAYER                        │
│   Desktop UI (PyQt6 / Electron)  or  Web UI (React)            │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP / IPC
┌───────────────────────────▼─────────────────────────────────────┐
│                         API LAYER                               │
│              FastAPI — REST endpoints + WebSocket               │
└────┬──────────────┬──────────────┬──────────────┬───────────────┘
     │              │              │              │
┌────▼────┐  ┌──────▼──────┐ ┌────▼────┐  ┌──────▼──────┐
│ Camera  │  │   Image     │ │ Scoring │  │  Report &   │
│ Manager │  │ Processing  │ │ Engine  │  │  Storage    │
│         │  │  Pipeline   │ │         │  │  Manager    │
└────┬────┘  └──────┬──────┘ └────┬────┘  └──────┬──────┘
     │              │              │              │
┌────▼──────────────▼──────────────▼──────────────▼──────────────┐
│                        DATA LAYER                               │
│        SQLite (dev) / PostgreSQL (prod)  +  File Storage        │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Component Descriptions

| Component | Responsibility |
|-----------|---------------|
| **Camera Manager** | Enumerate, connect, preview, and capture from multiple cameras |
| **Image Processing Pipeline** | Preprocessing → circle detection → arrow detection |
| **Scoring Engine** | Euclidean distance zone mapping, confidence calculation |
| **Report Manager** | Generate PDF/HTML reports, score summaries |
| **Storage Manager** | Save images, manage database records |
| **API Layer** | Expose all functions as REST endpoints + WebSocket for live preview |
| **UI Layer** | Display live feed, results, reports, user management |

### 2.3 Processing Flow (Detailed)

```
[Camera Frame]
      │
      ▼
[1. PREPROCESSING]
   ├── Grayscale conversion
   ├── Gaussian blur (noise removal)
   ├── CLAHE (contrast enhancement)
   ├── Gamma correction (brightness normalization)
   ├── Bilateral filtering (edge-preserving smoothing)
   ├── Adaptive thresholding
   └── Perspective correction (homography transform)
      │
      ▼
[2. CIRCLE DETECTION]
   ├── Hough Circle Transform (HoughCircles)
   ├── Adaptive parameter tuning
   ├── Ellipse fitting (for distorted images)
   ├── Concentric validation (common center check)
   └── Ring center coordinate computation
      │
      ▼
[3. ARROW DETECTION]
   ├── Canny edge detection
   ├── Circular Hough Transform (small circles = arrow shafts)
   ├── SIFT keypoint detection
   ├── Morphological operations (dilation + erosion)
   └── Non-Maximum Suppression (NMS) → final impact points
      │
      ▼
[4. SCORING ENGINE]
   ├── Euclidean distance: arrow point → ring center
   ├── Zone mapping: distance vs. ring radii (zones 1–10 + X)
   ├── Per-arrow confidence computation
   └── Total score aggregation
      │
      ▼
[5. OUTPUT GENERATION]
   ├── Annotated PNG (rings + score labels + confidence flags)
   ├── JSON score report
   └── Database record insertion
```

---

## 3. Technology Stack

### 3.1 Backend

| Component | Technology | Reason |
|-----------|-----------|--------|
| Language | Python 3.11+ | CV ecosystem, rapid dev |
| Web framework | FastAPI | Async, auto docs, fast |
| Image processing | OpenCV (cv2) 4.8+ | Industry standard CV |
| Numerical computing | NumPy, SciPy | Array ops, distance calc |
| Camera interface | OpenCV VideoCapture + `pyusb` | Multi-camera support |
| Database ORM | SQLAlchemy 2.0 | DB-agnostic ORM |
| Database (dev) | SQLite | Zero-config local |
| Database (prod) | PostgreSQL | Multi-user, concurrent |
| Task queue | Celery + Redis | Async batch processing |
| WebSocket | FastAPI WebSocket | Live camera preview |
| PDF generation | ReportLab or WeasyPrint | Report PDFs |
| Configuration | PyYAML | Human-readable config |
| Logging | Python logging + structlog | Structured logs |
| Testing | pytest + pytest-asyncio | Full test coverage |

### 3.2 Frontend (Desktop)

| Component | Technology |
|-----------|-----------|
| Framework | PyQt6 or PySide6 |
| Camera preview | QLabel + OpenCV frame streaming |
| Charts/graphs | matplotlib (embedded in Qt) or pyqtgraph |
| Styling | Qt stylesheets (QSS) |

### 3.3 Frontend (Web — optional)

| Component | Technology |
|-----------|-----------|
| Framework | React 18 + TypeScript |
| UI components | shadcn/ui + Tailwind CSS |
| Camera preview | WebRTC / MJPEG stream |
| Charts | Recharts |
| State management | Zustand |
| HTTP client | Axios |

### 3.4 Infrastructure

| Component | Technology |
|-----------|-----------|
| Containerization | Docker + Docker Compose |
| Reverse proxy | Nginx (production) |
| Storage | Local filesystem (organized by date/user/session) |

---

## 4. Camera Input System

### 4.1 Camera Manager Requirements

The system must support:
- **Multiple simultaneous cameras** (minimum 4 concurrent)
- **USB cameras** (via OpenCV VideoCapture)
- **IP/network cameras** (via RTSP stream URL)
- **Built-in laptop/desktop webcams**
- **Camera assignment** — each camera assigned to a specific target lane/archer

### 4.2 Camera Configuration

Each camera is configured with the following parameters (stored in YAML and database):

```yaml
cameras:
  - id: "cam_001"
    label: "Lane 1 - Target A"
    type: "usb"              # usb | rtsp | http_mjpeg
    device_index: 0          # for USB cameras
    rtsp_url: null           # for IP cameras: rtsp://192.168.1.100/stream
    resolution:
      width: 1920
      height: 1080
    fps: 30
    assigned_lane: 1
    assigned_archer_id: null  # set during session
    auto_focus: true
    brightness: 50
    contrast: 50
    exposure: -1             # -1 = auto
    flip_horizontal: false
    flip_vertical: false
    capture_delay_ms: 200    # delay after button press before capture
```

### 4.3 Camera Enumeration

On application start, the system must:
1. Scan all available USB devices (indices 0–9)
2. Scan configured RTSP/IP camera URLs
3. Display all discovered cameras in the UI
4. Allow manual camera addition via URL or device index
5. Test each camera connection and show status (connected / disconnected / error)

### 4.4 Live Preview

- Each connected camera streams a **live MJPEG preview** in the UI
- Preview runs at **10–15 fps** (low bandwidth, not full capture fps)
- Preview shows a **targeting overlay** — a circular guide to help center the target board
- Preview frame size: **640×480** in preview pane; full resolution only on capture
- **Zoom control** available per camera (digital zoom via crop + resize)

### 4.5 Capture Trigger

```
User presses [Calculate] button
      │
      ├── Capture mode: SINGLE — capture one frame immediately
      ├── Capture mode: BURST — capture 3 frames, select sharpest (Laplacian variance)
      └── Capture mode: AUTO — system detects when arrows are stationary (optional)
```

Burst mode is recommended — the sharpest frame (highest Laplacian variance score) is selected automatically.

### 4.6 Multi-Camera Simultaneous Capture

When multiple cameras are active:
- All cameras capture simultaneously on a single [Calculate] press, OR
- Each camera has its own individual [Calculate] button
- Configurable via settings: `capture_mode: simultaneous | individual`

---

## 5. Image Processing Pipeline

### 5.1 Preprocessing Module

**Input:** Raw captured frame (BGR, any resolution)
**Output:** Normalized grayscale image ready for detection

#### Step 1 — Resolution Normalization
```python
# Resize to standard working resolution
TARGET_WIDTH = 1280
scale = TARGET_WIDTH / image.width
image = cv2.resize(image, (TARGET_WIDTH, int(image.height * scale)))
```

#### Step 2 — Lighting Assessment
Compute image histogram to classify lighting condition:
- `DARK` — mean pixel value < 80
- `BRIGHT` — mean pixel value > 180
- `NORMAL` — 80 ≤ mean ≤ 180
- `UNEVEN` — high std deviation across quadrants

#### Step 3 — Adaptive Correction (7 methods)

| Method | Applied When | Operation |
|--------|-------------|-----------|
| Grayscale conversion | Always | `cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)` |
| Gaussian blur | Always | `cv2.GaussianBlur(img, (5,5), 0)` |
| CLAHE | DARK or UNEVEN | `clahe.apply(gray)` — clipLimit=2.0, tileGridSize=(8,8) |
| Gamma correction | DARK or BRIGHT | Power-law transform γ = 0.5 (dark) or 1.5 (bright) |
| Bilateral filtering | UNEVEN | Edge-preserving smoothing |
| Adaptive thresholding | LOW CONTRAST | `cv2.adaptiveThreshold(...)` |
| Histogram equalization | DARK | `cv2.equalizeHist(gray)` |

#### Step 4 — Perspective Correction
- Detect four corners of the target board (or use user-defined ROI)
- Apply homography transform to produce a front-facing square image
- If auto-detection fails, use raw image with warning flag

### 5.2 Circle Detection Module

**Input:** Preprocessed grayscale image
**Output:** List of circles `[{center_x, center_y, radius, ring_number}]` + `ring_center {x, y}`

#### Algorithm

```python
# Primary: Hough Circle Transform
circles = cv2.HoughCircles(
    image,
    cv2.HOUGH_GRADIENT,
    dp=1,
    minDist=20,
    param1=50,    # Canny upper threshold
    param2=30,    # accumulator threshold
    minRadius=10,
    maxRadius=int(min(h, w) / 2)
)
```

#### Validation Rules
- All detected circles must share a common center (within 10px tolerance)
- Ring radii must be approximately evenly spaced (±15% tolerance)
- Expected rings: 10 concentric circles (zones 1–10) + inner X ring
- If fewer than 8 rings detected → flag `LOW_RING_CONFIDENCE`
- Ellipse fitting fallback: if circles < 8, fit ellipses via `cv2.fitEllipse`

#### Ring Numbering
```
Ring index 0 (innermost) = Zone X (score: 10, bonus)
Ring index 1             = Zone 10
Ring index 2             = Zone 9
...
Ring index 10            = Zone 1 (outermost)
```

### 5.3 Arrow Detection Module

**Input:** Preprocessed image + ring center coordinates
**Output:** List of arrow impact points `[{x, y, confidence}]`

#### Method 1 — Canny + Circular Hough
```python
edges = cv2.Canny(image, threshold1=50, threshold2=150)
circles = cv2.HoughCircles(edges, cv2.HOUGH_GRADIENT, dp=1,
    minDist=15, param1=50, param2=15,
    minRadius=3, maxRadius=25)
```

#### Method 2 — SIFT Keypoints
```python
sift = cv2.SIFT_create()
keypoints, descriptors = sift.detectAndCompute(image, None)
# Filter keypoints by size (arrow holes are small, distinctive)
arrow_kps = [kp for kp in keypoints if 3 < kp.size < 20]
```

#### Method 3 — Morphological Segmentation
```python
kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
opened = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
contours, _ = cv2.findContours(opened, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
# Filter by area (arrow holes: 10–300 px²)
```

#### Fusion & NMS
- Combine all candidates from 3 methods into a single list
- Apply Non-Maximum Suppression with IoU threshold = 0.3
- Assign confidence:
  - Detected by all 3 methods → confidence = 0.98
  - Detected by 2 methods → confidence = 0.85
  - Detected by 1 method → confidence = 0.60 (flagged)

### 5.4 Scoring Engine

**Input:** Arrow impact points + ring circles + ring center
**Output:** Score report per arrow + total score

#### Zone Mapping Algorithm

```python
def assign_zone(arrow_x, arrow_y, ring_center, ring_radii):
    distance = euclidean_distance(arrow_x, arrow_y,
                                   ring_center.x, ring_center.y)
    for ring_idx, radius in enumerate(sorted(ring_radii)):
        if distance <= radius:
            zone = 10 - ring_idx  # innermost = 10
            return zone, distance, radius
    return 0, distance, None  # MISS

def euclidean_distance(x1, y1, x2, y2):
    return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
```

#### Confidence Calculation

```python
def compute_confidence(distance, inner_radius, outer_radius, detection_confidence):
    zone_width = outer_radius - inner_radius
    # How far is the arrow from the nearest boundary?
    dist_to_inner = abs(distance - inner_radius)
    dist_to_outer = abs(distance - outer_radius)
    boundary_margin = min(dist_to_inner, dist_to_outer) / zone_width
    spatial_confidence = min(boundary_margin * 2, 1.0)
    return (spatial_confidence + detection_confidence) / 2
```

#### Scoring Zones (Standard WA Archery Target)

| Zone | Score | Color |
|------|-------|-------|
| X (bullseye center) | 10 + bonus | Yellow inner |
| 10 | 10 | Yellow |
| 9 | 9 | Yellow |
| 8 | 8 | Red |
| 7 | 7 | Red |
| 6 | 6 | Blue |
| 5 | 5 | Blue |
| 4 | 4 | Black |
| 3 | 3 | Black |
| 2 | 2 | White |
| 1 | 1 | White |
| M (miss) | 0 | Outside target |

---

## 6. User & Session Management

### 6.1 User Roles & Permissions

```
SYSTEM_ADMIN
  ├── All permissions
  ├── User management (create/edit/delete)
  ├── Camera configuration
  └── System settings

TOURNAMENT_ADMIN
  ├── Create/manage tournaments and sessions
  ├── View all scores and reports
  ├── Export data
  └── Manage archers

SCORER / OPERATOR
  ├── Trigger scoring (Calculate button)
  ├── Assign cameras to archers
  ├── View and print reports
  └── Override scores (with reason logged)

ARCHER
  ├── View own scores and history
  ├── Download own reports
  └── View own annotated images
```

### 6.2 Session Management

A **Session** represents one competition round:

```
Tournament
  └── Session (e.g., "Morning Round — 70m")
        ├── Archers: [Archer 1, Archer 2, ...]
        ├── Camera assignments: [Camera 1 → Archer 1, ...]
        ├── End count: (e.g., 12 ends of 3 arrows = 36 arrows total)
        ├── Distance: (e.g., 70m, 50m, 30m)
        └── Ends: [End 1, End 2, ..., End 12]
                    └── Each End: [Arrow 1, Arrow 2, Arrow 3]
```

### 6.3 Session Flow

```
1. Admin creates Tournament
2. Admin creates Session under tournament
3. Operator assigns cameras to archers
4. Session starts → End 1 begins
5. Archers shoot 3 arrows
6. Operator presses [Calculate] (per camera or all)
7. System scores all targets
8. Results reviewed → confirmed or manually overridden
9. Next end begins
10. After all ends → session ends → final report generated
```

### 6.4 Score Override

- Any score can be manually overridden by SCORER or higher
- Override requires:
  - New score value
  - Reason (dropdown: "Detection error", "Arrow touched line", "System error", "Other")
  - Free-text note (optional)
- All overrides are logged with timestamp, user, original score, new score, and reason
- Override is visible in report (marked with ⚠ symbol)

---

## 7. Image Storage & Record System

### 7.1 Storage Structure

```
storage/
├── raw/                          # Original captured frames
│   └── YYYY/MM/DD/
│       └── {session_id}/
│           └── {camera_id}_{timestamp}.jpg
│
├── annotated/                    # Processed annotated images
│   └── YYYY/MM/DD/
│       └── {session_id}/
│           └── {arrow_set_id}_annotated.png
│
├── thumbnails/                   # Small previews for UI listing
│   └── {arrow_set_id}_thumb.jpg
│
└── exports/                      # Generated reports
    └── {session_id}/
        ├── {session_id}_report.pdf
        └── {session_id}_scores.csv
```

### 7.2 Image Record Schema

Every captured image creates a record:

```json
{
  "image_id": "uuid",
  "session_id": "uuid",
  "camera_id": "cam_001",
  "archer_id": "uuid",
  "end_number": 3,
  "captured_at": "2026-05-19T10:30:00Z",
  "raw_path": "storage/raw/2026/05/19/session_abc/cam_001_103000.jpg",
  "annotated_path": "storage/annotated/2026/05/19/session_abc/end3_annotated.png",
  "thumbnail_path": "storage/thumbnails/end3_thumb.jpg",
  "file_size_bytes": 2458600,
  "resolution": { "width": 1920, "height": 1080 },
  "capture_mode": "burst",
  "frames_captured": 3,
  "selected_frame_index": 1,
  "sharpness_score": 342.7,
  "lighting_condition": "NORMAL",
  "preprocessing_methods_applied": ["grayscale", "clahe", "gaussian_blur"],
  "processing_duration_ms": 847
}
```

### 7.3 Retention Policy

- Raw images: retained for **90 days** by default (configurable)
- Annotated images: retained **indefinitely**
- Thumbnails: retained **indefinitely**
- Export files: retained **30 days** (regeneratable on demand)
- Configurable per-tournament retention override

### 7.4 Storage Quota Management

- Default quota: **10 GB** per installation
- Warning at 80% usage
- Auto-archive (zip + move to archive folder) at 90%
- Admin dashboard shows storage usage breakdown

---

## 8. Report System

### 8.1 Report Types

#### 8.1.1 End Report (per round)
Generated after each end (set of arrows). Shows:
- Annotated target image
- Per-arrow scores with zone labels
- End total
- Running cumulative score
- Confidence flags

#### 8.1.2 Session Report (full competition round)
Generated at end of session. Shows:
- Archer name, session details, date/time
- Score table (all ends × all arrows)
- Total score and ranking
- Score distribution chart (bar chart by zone)
- Trend chart (cumulative score by end)
- All annotated images (thumbnail grid, click to enlarge)
- Override log (if any)

#### 8.1.3 Tournament Summary Report
Combines all sessions. Shows:
- Overall rankings table
- Top scores
- Per-archer score history
- Statistics: average score, highest end, grouping radius

#### 8.1.4 Comparison Report
Side-by-side comparison of two or more archers or sessions.

### 8.2 Report Display (In-App)

The report viewer must include:

```
┌────────────────────────────────────────────────────────┐
│  SESSION REPORT                    [Print] [Export PDF] │
│  Archer: Md. Shaikhul Islam        [Export CSV]        │
│  Session: Morning Round | 2026-05-19                   │
├────────────────────────────────────────────────────────┤
│                                                        │
│  SCORE SUMMARY                                         │
│  ┌─────┬───┬───┬───┬───────┬───────────────────────┐  │
│  │ End │ 1 │ 2 │ 3 │ Total │ Running Total          │  │
│  ├─────┼───┼───┼───┼───────┼───────────────────────┤  │
│  │  1  │ 9 │ X │ 8 │  27   │  27                   │  │
│  │  2  │ 7 │ 9 │ 9 │  25   │  52                   │  │
│  │ ... │   │   │   │       │                        │  │
│  └─────┴───┴───┴───┴───────┴───────────────────────┘  │
│                                                        │
│  SCORE DISTRIBUTION          CUMULATIVE TREND          │
│  [Bar chart by zone]         [Line chart by end]       │
│                                                        │
│  TARGET IMAGES                                         │
│  [End 1 thumbnail] [End 2 thumbnail] [End 3 thumbnail] │
│  Click to enlarge + see full annotation detail         │
│                                                        │
│  STATISTICS                                            │
│  Average per end: 26.4 | Highest end: 30 | X count: 4 │
│  Average grouping radius: 32px | Consistency: High     │
└────────────────────────────────────────────────────────┘
```

### 8.3 Report Export Formats

| Format | Contents |
|--------|----------|
| **PDF** | Full formatted report with images, charts, tables |
| **CSV** | Score data only (end × arrow grid) |
| **JSON** | Full machine-readable score data |
| **PNG** | Individual annotated target images |

### 8.4 Annotated Image Specification

The annotated output image must include:

- **Detected rings:** drawn as colored circles with zone labels (1–10, X)
- **Ring center:** marked with a crosshair (+) in red
- **Arrow impact points:** each marked with a filled circle
  - Color: green (high confidence ≥ 0.85), yellow (medium 0.60–0.84), red (low < 0.60)
- **Score labels:** next to each arrow point — zone number + score (e.g., "9 pts")
- **Confidence label:** small percentage below score (e.g., "97%")
- **End total:** displayed in top-right corner
- **Timestamp:** displayed in bottom-left corner
- **Session/archer info:** displayed in bottom-right corner
- **Warning overlay:** if any detection is flagged, orange "⚠ Review Recommended" banner

---

## 9. Application UI/UX Specification

### 9.1 Main Window Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  [≡ Menu]  ARCHERY SCORING SYSTEM        [User: Admin] [⚙ Settings]│
├──────────────────────────────────────────────────────────────────┤
│  SIDEBAR              │  MAIN CONTENT AREA                       │
│  ─────────────────    │  ─────────────────────────────────────── │
│  🎯 Dashboard         │                                          │
│  📷 Cameras           │   (Context-dependent content)            │
│  🏹 Scoring           │                                          │
│  📊 Reports           │                                          │
│  👥 Users             │                                          │
│  🏆 Tournaments       │                                          │
│  ⚙  Settings         │                                          │
│                       │                                          │
└──────────────────────────────────────────────────────────────────┘
```

### 9.2 Scoring Screen (Primary Screen)

This is the main operational screen used during a competition:

```
┌──────────────────────────────────────────────────────────────────┐
│  SESSION: Morning Round  |  End 3 of 12  |  Archer: Shaikhul     │
├───────────────────────────────┬──────────────────────────────────┤
│  CAMERA: Lane 1 — Live Feed   │  CAMERA: Lane 2 — Live Feed      │
│                               │                                  │
│  [Live 640×480 preview]       │  [Live 640×480 preview]          │
│                               │                                  │
│  Camera: USB Cam 1  [●LIVE]   │  Camera: IP Cam 1  [●LIVE]       │
│                               │                                  │
│  [ 📷 CALCULATE ]             │  [ 📷 CALCULATE ]                │
│                               │                                  │
├───────────────────────────────┴──────────────────────────────────┤
│  [ 📷 CALCULATE ALL CAMERAS ]    [ ↺ Retake ]    [ ✓ Confirm ]   │
├───────────────────────────────┬──────────────────────────────────┤
│  LAST RESULT — Lane 1         │  LAST RESULT — Lane 2            │
│  [Annotated image thumbnail]  │  [Annotated image thumbnail]     │
│  Scores: 9, X, 8 = 27 pts    │  Scores: 7, 9, 6 = 22 pts       │
│  Confidence: ✓ ✓ ⚠           │  Confidence: ✓ ✓ ✓              │
├───────────────────────────────┴──────────────────────────────────┤
│  RUNNING TOTALS                                                   │
│  Shaikhul: 52 pts (ends 1-2)  |  [Archer 2]: 44 pts             │
└──────────────────────────────────────────────────────────────────┘
```

### 9.3 Camera Management Screen

- Grid of all detected cameras (each shown as a live thumbnail card)
- Each card shows: camera name, device/URL, resolution, fps, status
- Add camera button (USB index or RTSP URL)
- Edit camera settings (label, resolution, capture delay, flip, zoom)
- Test connection button
- Assign to lane/archer dropdown

### 9.4 Result Detail View

When user clicks on an annotated thumbnail:

```
┌─────────────────────────────────────────────────────────┐
│  [← Back]   END 3 — Archer: Shaikhul   [🖨 Print]       │
├─────────────────────────────────────────────────────────┤
│                                                         │
│         [Full annotated image — zoomable]               │
│                                                         │
├───────────────┬─────────────────────────────────────────┤
│ Arrow | Zone  │ Score │ Confidence │ Distance px │ Note  │
│   1   │  9    │   9   │   97%      │   142px     │  ✓   │
│   2   │  X    │  10   │   99%      │    18px     │  ✓   │
│   3   │  8    │   8   │   63%      │   198px     │  ⚠   │
├───────────────┴─────────────────────────────────────────┤
│  END TOTAL: 27 points                                   │
│                                                         │
│  [✏ Override Score]  [🔁 Reprocess]  [💾 Save Image]   │
└─────────────────────────────────────────────────────────┘
```

### 9.5 Dashboard Screen

- Active session summary card
- Live score leaderboard (current session)
- Recent ends timeline
- Camera status grid (all cameras at a glance)
- System health (CPU, RAM, storage usage)
- Quick action buttons: [Start Session], [View Reports], [Export]

### 9.6 UI States & Feedback

| State | UI Behavior |
|-------|------------|
| Idle (no session) | Greyed-out Calculate button, prompt to start session |
| Camera disconnected | Red indicator, error toast, Calculate disabled for that camera |
| Processing | Calculate button → spinner "Analyzing...", progress bar |
| Success | Green flash, result pops up, audio chime (optional) |
| Low confidence | Yellow warning banner, "Review Recommended" badge |
| Error | Red toast notification, error details in log panel |

---

## 10. REST API Specification

### 10.1 Base URL

```
http://localhost:8000/api/v1
```

### 10.2 Authentication

```
POST /auth/login
Body: { "username": "string", "password": "string" }
Response: { "access_token": "jwt_token", "token_type": "bearer" }

All subsequent requests: Authorization: Bearer {token}
```

### 10.3 Camera Endpoints

```
GET    /cameras                    # List all cameras
POST   /cameras                    # Add new camera
GET    /cameras/{id}               # Get camera details
PUT    /cameras/{id}               # Update camera config
DELETE /cameras/{id}               # Remove camera
POST   /cameras/{id}/test          # Test connection
GET    /cameras/{id}/preview       # MJPEG stream (WebSocket)
POST   /cameras/{id}/capture       # Capture frame
```

### 10.4 Scoring Endpoints

```
POST   /score/calculate            # Trigger scoring for one camera
POST   /score/calculate-all        # Trigger all cameras simultaneously
POST   /score/reprocess/{image_id} # Reprocess a saved image
PUT    /score/{score_id}/override  # Override a score
GET    /score/{score_id}           # Get score details
```

**POST /score/calculate request body:**
```json
{
  "camera_id": "cam_001",
  "session_id": "uuid",
  "end_number": 3,
  "archer_id": "uuid",
  "capture_mode": "burst"
}
```

**POST /score/calculate response:**
```json
{
  "score_id": "uuid",
  "image_id": "uuid",
  "annotated_image_url": "/storage/annotated/...",
  "arrows": [
    { "id": 1, "zone": 9, "score": 9, "confidence": 0.97,
      "position": { "x": 642, "y": 318 }, "distance_px": 142 },
    { "id": 2, "zone": "X", "score": 10, "confidence": 0.99,
      "position": { "x": 648, "y": 495 }, "distance_px": 18 },
    { "id": 3, "zone": 8, "score": 8, "confidence": 0.63,
      "position": { "x": 490, "y": 512 }, "distance_px": 198,
      "flag": "LOW_CONFIDENCE" }
  ],
  "total_score": 27,
  "end_number": 3,
  "processing_time_ms": 847,
  "warnings": ["LOW_CONFIDENCE on arrow 3"]
}
```

### 10.5 Session & Tournament Endpoints

```
GET    /tournaments                # List tournaments
POST   /tournaments                # Create tournament
GET    /tournaments/{id}/sessions  # List sessions
POST   /sessions                   # Create session
POST   /sessions/{id}/start        # Start session
POST   /sessions/{id}/end          # End session
GET    /sessions/{id}/scores       # All scores in session
GET    /sessions/{id}/report       # Generate/get report
```

### 10.6 User Endpoints

```
GET    /users                      # List users (admin only)
POST   /users                      # Create user
GET    /users/{id}                 # Get user profile
PUT    /users/{id}                 # Update user
GET    /users/{id}/scores          # User score history
```

### 10.7 Report Endpoints

```
GET    /reports/session/{id}       # Session report (JSON)
GET    /reports/session/{id}/pdf   # Session report (PDF download)
GET    /reports/session/{id}/csv   # Session scores (CSV download)
GET    /reports/tournament/{id}    # Tournament summary
```

### 10.8 WebSocket Endpoints

```
WS /ws/camera/{camera_id}/preview  # Live camera preview stream
WS /ws/session/{session_id}/live   # Live score updates for a session
```

---

## 11. Data Models & Database Schema

### 11.1 Users Table

```sql
CREATE TABLE users (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username    VARCHAR(50) UNIQUE NOT NULL,
    email       VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name   VARCHAR(100) NOT NULL,
    role        VARCHAR(20) NOT NULL CHECK (role IN ('system_admin','tournament_admin','scorer','archer')),
    club        VARCHAR(100),
    national_id VARCHAR(50),
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW(),
    is_active   BOOLEAN DEFAULT TRUE
);
```

### 11.2 Cameras Table

```sql
CREATE TABLE cameras (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    label       VARCHAR(100) NOT NULL,
    type        VARCHAR(20) NOT NULL CHECK (type IN ('usb','rtsp','http_mjpeg')),
    device_index INTEGER,
    rtsp_url    VARCHAR(255),
    resolution_w INTEGER DEFAULT 1920,
    resolution_h INTEGER DEFAULT 1080,
    fps         INTEGER DEFAULT 30,
    config_json JSONB,
    is_active   BOOLEAN DEFAULT TRUE,
    last_seen_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);
```

### 11.3 Tournaments Table

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

### 11.4 Sessions Table

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

### 11.5 Images Table

```sql
CREATE TABLE images (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id      UUID REFERENCES sessions(id),
    camera_id       UUID REFERENCES cameras(id),
    archer_id       UUID REFERENCES users(id),
    end_number      INTEGER,
    raw_path        VARCHAR(500),
    annotated_path  VARCHAR(500),
    thumbnail_path  VARCHAR(500),
    captured_at     TIMESTAMPTZ NOT NULL,
    processing_ms   INTEGER,
    lighting_cond   VARCHAR(20),
    sharpness_score FLOAT,
    capture_mode    VARCHAR(20),
    metadata_json   JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### 11.6 Scores Table

```sql
CREATE TABLE scores (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    image_id        UUID REFERENCES images(id),
    session_id      UUID REFERENCES sessions(id),
    archer_id       UUID REFERENCES users(id),
    end_number      INTEGER NOT NULL,
    arrows_json     JSONB NOT NULL,
    -- arrows_json: [{id, zone, score, confidence, position_x, position_y, distance_px, flag}]
    total_score     INTEGER NOT NULL,
    arrow_count     INTEGER NOT NULL,
    x_count         INTEGER DEFAULT 0,
    warnings_json   JSONB,
    is_overridden   BOOLEAN DEFAULT FALSE,
    override_log_id UUID,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);
```

### 11.7 Override Log Table

```sql
CREATE TABLE override_logs (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    score_id        UUID REFERENCES scores(id),
    overridden_by   UUID REFERENCES users(id),
    original_score  INTEGER,
    new_score       INTEGER,
    original_arrows JSONB,
    new_arrows      JSONB,
    reason          VARCHAR(50),
    note            TEXT,
    overridden_at   TIMESTAMPTZ DEFAULT NOW()
);
```

### 11.8 Camera Assignments Table

```sql
CREATE TABLE camera_assignments (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id  UUID REFERENCES sessions(id),
    camera_id   UUID REFERENCES cameras(id),
    archer_id   UUID REFERENCES users(id),
    lane_number INTEGER,
    assigned_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(session_id, camera_id),
    UNIQUE(session_id, lane_number)
);
```

---

## 12. Configuration System

All system parameters are stored in `config.yaml`. The system reads this on startup and allows live reload via admin UI.

```yaml
# config.yaml — Full System Configuration

app:
  name: "Archery Scoring System"
  version: "1.0.0"
  debug: false
  host: "0.0.0.0"
  port: 8000
  secret_key: "CHANGE_THIS_IN_PRODUCTION"

database:
  type: "sqlite"          # sqlite | postgresql
  sqlite_path: "data/archery.db"
  postgres_url: null      # "postgresql://user:pass@localhost:5432/archery"

storage:
  base_path: "storage/"
  quota_gb: 10
  warn_at_percent: 80
  raw_retention_days: 90
  annotated_retention_days: -1   # -1 = indefinite

cameras:
  capture_mode: "burst"          # single | burst
  burst_frames: 3
  burst_select: "sharpest"       # sharpest | first | middle
  capture_delay_ms: 200
  preview_fps: 15
  preview_resolution: [640, 480]
  simultaneous_capture: true

processing:
  target_width: 1280             # working resolution
  lighting_dark_threshold: 80
  lighting_bright_threshold: 180
  hough_dp: 1
  hough_param1: 50
  hough_param2: 30
  nms_iou_threshold: 0.3
  low_confidence_threshold: 0.60
  perspective_auto_detect: true

scoring:
  target_type: "WA_10RING"       # WA_10RING | WA_6RING | custom
  ring_count: 10
  arrows_per_end: 3
  x_ring_enabled: true
  # Ring radii as fractions of image width (auto-calibrated if null)
  ring_radii_fractions: null

  # Standard WA face at 122cm — relative radii
  # [X, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
  ring_colors:
    X: "FFD700"
    10: "FFD700"
    9:  "FFD700"
    8:  "FF0000"
    7:  "FF0000"
    6:  "4169E1"
    5:  "4169E1"
    4:  "1C1C1C"
    3:  "1C1C1C"
    2:  "EEEEEE"
    1:  "EEEEEE"

reports:
  auto_generate_pdf: true
  pdf_template: "templates/report_default.html"
  include_thumbnails: true
  include_charts: true
  logo_path: null

ui:
  theme: "dark"                  # dark | light
  language: "en"
  audio_feedback: true
  show_confidence: true
  auto_advance_end: false

logging:
  level: "INFO"
  file: "logs/archery_system.log"
  max_size_mb: 50
  backup_count: 5
```

---

## 13. Error Handling & Validation

### 13.1 Error Categories

| Code | Category | Description |
|------|----------|-------------|
| `CAM_001` | Camera | Camera not connected or disconnected |
| `CAM_002` | Camera | Frame capture timeout |
| `CAM_003` | Camera | Frame is too dark/blurry to process |
| `IMG_001` | Processing | Ring detection failed (< 5 rings found) |
| `IMG_002` | Processing | No arrow holes detected |
| `IMG_003` | Processing | Perspective correction failed |
| `SCR_001` | Scoring | Arrow outside target boundary |
| `SCR_002` | Scoring | Confidence below threshold |
| `SYS_001` | System | Disk storage full |
| `SYS_002` | System | Database connection error |

### 13.2 Graceful Degradation

- If preprocessing fails: skip failed methods, proceed with raw grayscale
- If < 8 rings detected: flag `LOW_RING_CONFIDENCE`, attempt ellipse fitting
- If no arrows detected: return empty result with `NO_ARROWS_DETECTED` flag
- If confidence < 0.60 for any arrow: flag for review, do not block output
- If camera disconnects mid-session: use last captured image if available, alert operator

### 13.3 Input Validation

- Uploaded/captured image: min 640×480, max 8000×6000 pixels
- Image file size: max 20MB
- RTSP URL: validated format before save
- Score override: new score must be 0–10, reason required
- End number: must be within session's defined end_count range

---

## 14. Performance Requirements

| Metric | Requirement |
|--------|------------|
| Single image processing | < 1 second |
| 24-target batch | < 15 minutes |
| Camera preview latency | < 200ms |
| Simultaneous cameras | ≥ 4 concurrent |
| Concurrent users (web mode) | ≥ 20 |
| API response time (non-image) | < 200ms |
| Database query time | < 100ms |
| F1 score (detection accuracy) | ≥ 0.90 |
| Ring detection success rate | ≥ 95% |
| Application startup time | < 5 seconds |

---

## 15. Security Considerations

- **Authentication:** JWT tokens, 8-hour expiry, refresh token support
- **Passwords:** bcrypt hashing, minimum 8 characters
- **API rate limiting:** 100 requests/minute per user
- **File upload validation:** check MIME type + file header, not just extension
- **SQL injection:** all queries via SQLAlchemy ORM (parameterized)
- **CORS:** restrict to known origins in production
- **Stored images:** not publicly accessible, served only via authenticated API
- **Override audit log:** immutable, cannot be deleted
- **Sensitive config:** secret keys via environment variables, never in config.yaml

---

## 16. Testing Requirements

### 16.1 Test Categories

| Type | Coverage Target | Tool |
|------|---------------|------|
| Unit tests — image processing | 90%+ | pytest |
| Unit tests — scoring engine | 100% | pytest |
| Integration tests — API | 80%+ | pytest + httpx |
| Camera mock tests | All camera states | pytest + mock |
| End-to-end tests | Core user flows | Playwright (web) / pytest-qt |
| Performance tests | All perf requirements | locust |

### 16.2 Test Dataset

- Minimum 50 annotated target images with ground truth scores
- Coverage: bright, dark, glare, angled, close-up, wide
- Coverage: 1 arrow, 3 arrows, 6 arrows, near-boundary arrows
- Coverage: damaged targets, partial occlusion, overlapping arrows

---

## 17. Directory Structure

```
archery-scoring-system/
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app entry point
│   │   ├── config.py             # Config loader
│   │   ├── database.py           # DB connection + session
│   │   ├── api/
│   │   │   ├── routes/
│   │   │   │   ├── auth.py
│   │   │   │   ├── cameras.py
│   │   │   │   ├── scoring.py
│   │   │   │   ├── sessions.py
│   │   │   │   ├── reports.py
│   │   │   │   └── users.py
│   │   │   └── websocket.py
│   │   ├── core/
│   │   │   ├── camera_manager.py
│   │   │   ├── preprocessing.py
│   │   │   ├── circle_detection.py
│   │   │   ├── arrow_detection.py
│   │   │   ├── scoring_engine.py
│   │   │   ├── output_generator.py
│   │   │   └── report_generator.py
│   │   ├── models/               # SQLAlchemy models
│   │   ├── schemas/              # Pydantic schemas
│   │   ├── services/             # Business logic layer
│   │   └── utils/                # Helpers, logging
│   ├── tests/
│   ├── config.yaml
│   └── requirements.txt
│
├── frontend/                     # React web frontend (optional)
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── store/
│   │   └── api/
│   └── package.json
│
├── desktop/                      # PyQt6 desktop app
│   ├── main.py
│   ├── windows/
│   │   ├── main_window.py
│   │   ├── scoring_screen.py
│   │   ├── camera_screen.py
│   │   ├── report_screen.py
│   │   └── settings_screen.py
│   ├── widgets/
│   │   ├── camera_preview.py
│   │   ├── score_table.py
│   │   └── annotated_viewer.py
│   └── styles/
│       └── main.qss
│
├── storage/                      # Runtime image/report storage
├── logs/
├── data/                         # SQLite DB (dev)
├── templates/                    # Report HTML templates
├── tests/
│   ├── fixtures/                 # Test images with ground truth
│   ├── test_preprocessing.py
│   ├── test_circle_detection.py
│   ├── test_arrow_detection.py
│   ├── test_scoring_engine.py
│   └── test_api.py
├── docker-compose.yml
├── Dockerfile
├── config.yaml
└── README.md
```

---

## 18. Future Enhancements

| Feature | Description | Priority |
|---------|-------------|----------|
| **YOLOv8 integration** | Replace/augment Hough-based detection with trained YOLOv8 model for higher accuracy | High |
| **Auto-calibration** | Automatically detect ring radii from known target face size | Medium |
| **Mobile app** | iOS/Android companion app for viewing scores and reports | Medium |
| **Cloud sync** | Optional cloud backup for scores and images | Medium |
| **Real-time grouping analysis** | Measure arrow grouping radius, center of group, consistency metrics | High |
| **Video mode** | Process video stream to detect arrows as they land (event-triggered) | Low |
| **3D arrow angle detection** | Stereo camera or depth camera to detect arrow entry angle | Low |
| **National ranking integration** | API to push scores to World Archery or national federation systems | Medium |
| **Lane auto-assignment** | QR code on archer badge, camera reads QR to auto-assign lane | Medium |
| **Offline mobile capture** | Tablet/phone captures image offline, syncs when connected | Low |
| **Predictive analytics** | ML model to predict score trends and training recommendations | Low |

---

## Appendix A — Standard WA Archery Target Specifications

| Parameter | 122cm Face | 80cm Face | 40cm Face |
|-----------|-----------|-----------|-----------|
| Outermost ring (1) diameter | 122 cm | 80 cm | 40 cm |
| Ring width | 6.1 cm | 4.0 cm | 2.0 cm |
| Bullseye (10) diameter | 12.2 cm | 8.0 cm | 4.0 cm |
| X ring diameter | ~4.8 cm | ~3.2 cm | ~1.6 cm |
| Common distance | 70m, 60m | 50m, 30m | 18m (indoor) |

---

## Appendix B — Key Algorithm References

1. **Hough Circle Transform:** Duda, R.O., Hart, P.E. (1972). "Use of the Hough transformation to detect lines and curves in pictures." *Communications of the ACM*.

2. **SIFT:** Lowe, D.G. (2004). "Distinctive Image Features from Scale-Invariant Keypoints." *International Journal of Computer Vision*.

3. **CLAHE:** Zuiderveld, K. (1994). "Contrast Limited Adaptive Histogram Equalization." *Graphics Gems IV*.

4. **NMS:** Neubeck, A., Van Gool, L. (2006). "Efficient Non-Maximum Suppression." *18th International Conference on Pattern Recognition*.

5. **YOLOv8 (future):** Jocher, G. et al. (2023). "Ultralytics YOLOv8." Ultralytics.

6. **Related work:** S. Adam, N. A. Fitri, S. Bibi, and M. R. Sufandi, "Real-Time Arrow Detection and Scoring on Archery Targets Using YOLOv8 with Euclidean Distance-Based Zone Estimation," *JAIC*, vol. 9, no. 6, pp. 3669–3680, Dec. 2025.

---

*Document version: 1.0 | Last updated: May 2026 | System: Automated Archery Scoring System*
