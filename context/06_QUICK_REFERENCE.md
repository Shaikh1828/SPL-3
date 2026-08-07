# Quick Reference — File Map & Key Functions

## Core Scoring Pipeline — Call Hierarchy

```
API: POST /sessions/{id}/scores/upload
│
├─ src/api/scores.py :: upload_score_image()
│   │
│   ├─ ImageService.detect_arrow_in_image(file_bytes)
│   │   └─ ArrowDetectionService.detect()
│   │       │
│   │       ├─ _load_image()                    # bytes → cv2 ndarray
│   │       ├─ _preprocess()                    # resize, denoise, enhance
│   │       │   └─ _normalize_lighting()        # gamma, CLAHE, white balance
│   │       │
│   │       ├─ _detect_target()                 # STAGE 2
│   │       │   ├─ _target_by_zone_ellipses()   # PRIMARY (color → ellipse → ratio)
│   │       │   ├─ _target_by_color_bands()     # Yellow bullseye → extrapolate
│   │       │   ├─ _target_by_dark_ring_boundary() # Saturation blob → ellipse
│   │       │   ├─ _target_by_hough()           # HoughCircles fallback
│   │       │   ├─ _target_by_concentric_contours() # Canny → cluster
│   │       │   ├─ _ring_color_agreement()      # Validate fit vs pixel colors
│   │       │   └─ _refine_target_radial()      # Ray-trace refinement
│   │       │
│   │       ├─ _detect_arrows()                 # STAGE 3
│   │       │   ├─ _detect_puncture_holes()     # Blackhat → elongated dark spots
│   │       │   ├─ _arrows_by_color()           # Color masks → elongated contours
│   │       │   ├─ _arrows_by_hough_lines()     # HoughLinesP → shaft verify
│   │       │   ├─ _arrows_by_contour()         # Edge contours → aspect filter
│   │       │   ├─ _arrows_by_sift()            # SIFT keypoints (corroboration)
│   │       │   ├─ _refine_tip_subpixel()       # cornerSubPix + gradient scan
│   │       │   └─ NMS (deduplication)           # Shaft-overlap merge
│   │       │
│   │       ├─ _calculate_zone()                # STAGE 4 (norm distance → zone)
│   │       │   └─ _get_normalized_distance()   # Ellipse-normalized distance
│   │       │
│   │       └─ _line_ellipse_intersection()     # Geometric tip calculation
│   │           └─ _shaft_line_to_tip()         # Wrapper with fallback
│   │
│   ├─ ImageService.save_image()
│   ├─ ImageService.save_annotated_image()
│   │   └─ ImageService.generate_annotated_image()
│   │
│   └─ ScoringService.record_score_with_retry()
│       ├─ validate_score()
│       ├─ Create Score record → commit
│       ├─ Update SessionArcher.total_score
│       ├─ publish_event(SCORE_RECORDED)
│       └─ invalidate_leaderboard_cache()
```

## File Size & Complexity

| File                           | Lines | Key Role                          |
|-------------------------------|-------|----------------------------------|
| `arrow_detection_service.py`  | 2665  | Core CV pipeline (largest file)  |
| `scores.py` (API)             | 825   | Score endpoints (most complex API)|
| `image_service.py`            | 547   | Image save/annotate/compress     |
| `scoring_service.py`          | 324   | DB score CRUD + retry logic      |
| `image_processing.py` (utils) | 311   | Legacy CV utilities (superseded) |
| `constants.py`                | 268   | App constants + validators       |
| `camera_service.py`           | 260   | Camera management                |
| `sessions.py` (API)           | 407   | Session management endpoints     |
| `websocket.py`                | 405   | Real-time WebSocket streaming    |
| `users.py` (API)              | 248   | User management                  |
| `health_service.py`           | 230   | System health checks             |
| `config.py`                   | 151   | Pydantic settings                |
| `database.py`                 | 146   | SQLAlchemy engine + retry        |
| `events.py`                   | 174   | In-process event bus             |
| `security.py`                 | 145   | JWT + bcrypt                     |
| `cache.py`                    | 170   | Redis cache manager              |

## Key Data Classes

### TargetInfo (target detection result)
```python
@dataclass
class TargetInfo:
    center_x: float      # Target center X (pixels)
    center_y: float      # Target center Y (pixels)
    outer_radius: float  # Average outer radius (pixels)
    confidence: float    # Detection confidence [0-1]
    detected_rings: int  # Number of ring colors found
    method: str          # Detection method name
    a_outer: float       # Semi-major axis (ellipse)
    b_outer: float       # Semi-minor axis (ellipse)
    angle: float         # Rotation angle (degrees)
```

### ArrowInfo (arrow detection result)
```python
@dataclass
class ArrowInfo:
    tip_x: float             # Arrow tip X (pixels)
    tip_y: float             # Arrow tip Y (pixels)
    confidence: float        # Detection confidence [0-1]
    method: str              # Detection method name
    shaft_angle: float       # Shaft direction (degrees)
    zone: Optional[int]      # Scored zone (0-10)
    points: Optional[int]    # Points (= zone)
```

### DetectionResult (complete result)
```python
@dataclass
class DetectionResult:
    zone: Optional[int]           # Primary arrow zone
    points: Optional[int]         # Primary arrow points
    confidence: float             # Combined confidence
    method: str                   # Combined method string
    target: Optional[TargetInfo]  # Target detection info
    arrow: Optional[ArrowInfo]    # Primary arrow info
    distance_ratio: Optional[float]  # Normalized distance
    arrows: List[ArrowInfo]       # All detected arrows
```

## Important Constants

### WA Zone Boundaries (normalized radial distance)
```python
WA_ZONE_BOUNDARIES = [
    0.048,  # Zone 10 inner (X ring)
    0.096,  # Zone 10 outer
    0.192,  # Zone 9
    0.288,  # Zone 8
    0.384,  # Zone 7
    0.480,  # Zone 6
    0.576,  # Zone 5
    0.672,  # Zone 4
    0.768,  # Zone 3
    0.864,  # Zone 2
    0.960,  # Zone 1
]
```

### Target Color Bands (HSV)
```python
Yellow: H[15-40], S[80-255], V[130-255]
Red:    H[0-12]+[168-180], S[120-255], V[100-255]
Blue:   H[95-135], S[80-255], V[80-255]
Black:  H[0-180], S[0-255], V[0-55]
```

### Arrow Color Ranges (HSV)
```python
Red:     H[0-12]+[168-180], S[120-255], V[100-255]
Blue:    H[95-135], S[80-255], V[80-255]
Black:   H[0-180], S[0-255], V[0-55]
Yellow:  H[15-40], S[80-255], V[130-255]
White:   H[0-180], S[0-40], V[190-255]
Green:   H[50-85], S[80-255], V[80-255]
Navy:    H[100-140], S[50-255], V[50-200]
Gray:    H[0-180], S[0-50], V[60-180]
```
