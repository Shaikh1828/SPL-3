# Scoring System — Complete Technical Deep-Dive

## Overview
Scoring system এই project এর **সবচেয়ে গুরুত্বপূর্ণ অংশ**। এটি একটি multi-stage Computer Vision (CV) pipeline যা archery target এর ছবি থেকে automatically arrow position detect করে World Archery (WA) standard অনুযায়ী score calculate করে।

## ⚠️ Known Problems & Issues
> **Scoring system এ অনেক problem আছে। Model গুলোকে fine-tuning এবং re-training করতে হবে।**
> Current system pure CV (OpenCV) based — কোনো ML/DL model trained করা হয়নি।
> Data folder এ YOLOv8 format এ 504 annotated images আছে training এর জন্য।

### Current Problems:
1. **No trained ML model**: সবকিছু hardcoded CV rules দিয়ে করা হয়েছে — কোনো YOLOv8/YOLO model train করা হয়নি
2. **Target detection unreliable**: বিভিন্ন lighting condition, angle, distance এ target ঠিকমত detect হয় না
3. **Arrow detection inaccurate**: Arrow shaft ও tip ভুল জায়গায় detect হয়, especially:
   - Arrow color target ring color এর সাথে match করলে (red arrow on red ring)
   - Multiple arrows close together থাকলে
   - Old puncture holes কে new arrow হিসাবে detect করে
4. **Circle/Ellipse detection**: HoughCircles অনেক সময় ভুল circle detect করে, বিশেষ করে noisy background এ
5. **Zone calculation errors**: Target center/radius ভুল detect হলে zone calculation ও ভুল হয়
6. **False positives**: Background elements (wooden stand, shadows, grass) কে target/arrow হিসাবে detect করে

---

## Full Pipeline Architecture

```
Image Input (bytes/path/array)
        │
        ▼
┌─────────────────────────────────────┐
│  STAGE 1: PREPROCESSING             │
│                                      │
│  1. Resize (max 1024px)             │
│  2. Lighting normalization           │
│     - Gamma correction (dark/bright)│
│     - Contrast stretch              │
│     - CLAHE on LAB L-channel        │
│     - Gray-world white balance      │
│  3. Color space conversions          │
│     - Gray, HSV, LAB                │
│  4. Bilateral filter (denoise)       │
│  5. Gaussian blur (for Hough)        │
│  6. CLAHE enhanced versions          │
│  7. Morphological gradient           │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  STAGE 2: TARGET DETECTION           │
│                                      │
│  5 methods tried in priority order:  │
│                                      │
│  ① Zone Ellipses (PRIMARY)           │
│     Color masks → ellipse fit →      │
│     ratio extrapolation → consensus  │
│                                      │
│  ② Color Bands (yellow bullseye)     │
│     Yellow HSV+LAB mask → fit →      │
│     extrapolate (÷0.192)             │
│                                      │
│  ③ Dark Ring Boundary                │
│     Saturation mask → largest blob → │
│     ellipse fit (radius ~77%)        │
│                                      │
│  ④ HoughCircles (fallback)           │
│     Gaussian blur → cv2.HoughCircles│
│                                      │
│  ⑤ Concentric Contours (fallback)    │
│     Canny edges → cluster centroids  │
│                                      │
│  + Radial Refinement                 │
│    Trace ray outward from center →   │
│    color sequence validation →       │
│    ellipse re-fit                    │
│                                      │
│  Output: TargetInfo                  │
│    (center_x, center_y,             │
│     outer_radius, confidence,        │
│     a_outer, b_outer, angle)         │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  STAGE 3: ARROW DETECTION            │
│                                      │
│  5 methods run in parallel:          │
│                                      │
│  Ⓐ Color Segmentation               │
│     Arrow color HSV masks →          │
│     elongated contours →             │
│     fitLine → shaft direction →      │
│     LINE-ELLIPSE INTERSECTION →tip   │
│                                      │
│  Ⓑ HoughLinesP                      │
│     Multi-channel Canny edges →      │
│     Hough lines → radial check →     │
│     shaft continuity verify →        │
│     LINE-ELLIPSE INTERSECTION →tip   │
│                                      │
│  Ⓒ Contour Aspect Ratio             │
│     Edge detection → elongated       │
│     contours (aspect>4) →            │
│     fitLine → direction verify →     │
│     LINE-ELLIPSE INTERSECTION →tip   │
│                                      │
│  Ⓓ Puncture Hole Detection          │
│     Morphological blackhat →         │
│     dark components → elongated →    │
│     radial alignment check →         │
│     centroid as tip                   │
│     ★ HIGHEST CONFIDENCE             │
│                                      │
│  Ⓔ SIFT Keypoints (corroboration)   │
│     SIFT feature detect →            │
│     small keypoints inside target →  │
│     dark-spot verification →         │
│     only used if corroborates above  │
│                                      │
│  + Multi-method confidence boost     │
│    2+ methods agree → +0.06-0.12     │
│                                      │
│  + Subpixel refinement               │
│    cornerSubPix + gradient profile   │
│                                      │
│  + NMS (shaft-overlap dedup)         │
│    Merge overlapping detections      │
│                                      │
│  Output: List[ArrowInfo]             │
│    (tip_x, tip_y, confidence,        │
│     method, shaft_angle,             │
│     zone, points)                    │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  STAGE 4: ZONE CALCULATION           │
│  (World Archery Standard)            │
│                                      │
│  1. Ellipse-normalized distance:     │
│     dx = tip_x - center_x           │
│     dy = tip_y - center_y           │
│     Rotate by -angle                 │
│     norm = √((rx/a)² + (ry/b)²)    │
│                                      │
│  2. WA Zone boundaries:              │
│     Zone 10 (X): 0 – 4.8%          │
│     Zone 10:     4.8 – 9.6%        │
│     Zone  9:     9.6 – 19.2%       │
│     Zone  8:    19.2 – 28.8%       │
│     Zone  7:    28.8 – 38.4%       │
│     Zone  6:    38.4 – 48.0%       │
│     Zone  5:    48.0 – 57.6%       │
│     Zone  4:    57.6 – 67.2%       │
│     Zone  3:    67.2 – 76.8%       │
│     Zone  2:    76.8 – 86.4%       │
│     Zone  1:    86.4 – 96.0%       │
│     Miss (0):    > 96.0%            │
│                                      │
│  3. Score = Zone number (0-10)       │
└──────────┬──────────────────────────┘
           │
           ▼
┌─────────────────────────────────────┐
│  STAGE 5: CONFIDENCE SCORING         │
│                                      │
│  confidence = √(target_conf ×       │
│                  arrow_conf)         │
│                                      │
│  Method priority hierarchy:          │
│  puncture_hole > sift >              │
│  hough_lines > color_segment >       │
│  contour_aspect                      │
│                                      │
│  Fallback penalty: ×0.65 (dark_     │
│  cluster), ×0.25 (pure geometric)    │
└──────────┬──────────────────────────┘
           │
           ▼
     DetectionResult
     {zone, points, confidence,
      method, target, arrow, arrows}
```

---

## Stage 2 Deep-Dive: Target Detection

### Method ① Zone Ellipses (Most Reliable)
**File**: `arrow_detection_service.py:946-1178`

কিভাবে কাজ করে:
1. **Color Masks তৈরি**:
   - **Yellow**: HSV `[13,70,100]-[45,255,255]` + LAB b-channel `>143`
   - **Red**: HSV `[0,90,70]-[14,255,255]` + `[163,90,70]-[180,255,255]` + LAB a `>140` (yellow excluded)
   - **Blue**: HSV `[85,90,60]-[140,255,255]` (yellow+red excluded)
   - **Black**: Value `[15]-[110]` (all others excluded)

2. **প্রতিটি color band এর জন্য**:
   - Morphological close (9×9) + open (5×5)
   - Find contours → filter by area (>0.5% image, <30% image)
   - Score: circularity × proximity-to-center × log(area)
   - Merge nearby fragments (same ring split by arrows)
   - Fit ellipse → extrapolate to full target using WA ratios

3. **WA Ratio Extrapolation**:
   - Yellow outer boundary = 19.2% of target radius → divide by 0.192
   - Red outer boundary = 38.4% → divide by 0.384
   - Blue outer boundary = 57.6% → divide by 0.576
   - Black outer boundary = 76.8% → divide by 0.768

4. **Consensus**: Weighted average of center/axes from agreeing zones (within 15% radius tolerance)

5. **Fit weights**: Blue (2.5) > Black (1.8) > Red (1.5) > Yellow (0.8) — because larger bands have less amplification error

### Method ② Color Bands (Yellow Bullseye)
**File**: `arrow_detection_service.py:1180-1273`

- Finds yellow region only (HSV + LAB b-channel)
- Fits ellipse to yellow area
- Extrapolates: `a_outer = a_yellow / 0.192`, `b_outer = b_yellow / 0.192`
- **⚠️ Problem**: 5.2x amplification means even small segmentation errors make the predicted target radius wildly wrong

### Method ③ Dark Ring Boundary
**File**: `arrow_detection_service.py:786-944`

- Outside-in approach: finds ALL colored pixels (saturation > 35)
- Morphological close → largest blob → fit ellipse
- **⚠️ Problem**: Only measures colored+black region (~77% of true radius), needs correction factor
- **⚠️ Problem**: Often bleeds into wooden stand below target

### Radial Refinement
**File**: `arrow_detection_service.py:645-784`

- Casts 180 rays outward from center
- Classifies each pixel: yellow → red → blue → black → white
- Records each color transition boundary
- Scales each boundary by 1/ratio → all points should land on same outer ellipse
- Fits ellipse to combined point cloud
- Iterates 4 times for convergence
- **Ring Color Agreement**: Validates fit by sampling ring midpoints and checking pixel color matches expected WA color

---

## Stage 3 Deep-Dive: Arrow Detection

### Method Ⓐ Color Segmentation
**File**: `arrow_detection_service.py:1953-2073`

Arrow color ranges detected (HSV):
| Color       | H range      | S range    | V range    |
|-------------|-------------|------------|------------|
| Red         | 0-12, 168-180| 120-255   | 100-255    |
| Blue        | 95-135      | 80-255     | 80-255     |
| Black       | 0-180       | 0-255      | 0-55       |
| Yellow/Gold | 15-40       | 80-255     | 130-255    |
| White       | 0-180       | 0-40       | 190-255    |
| Green       | 50-85       | 80-255     | 80-255     |
| Dark blue   | 100-140     | 50-255     | 50-200     |
| Gray/Silver | 0-180       | 0-50       | 60-180     |

Process:
1. Combined mask from all color ranges
2. Restrict to target ROI (108% of outer radius)
3. Morphological cleanup (3×3 rect)
4. Find contours → filter by aspect ratio (>3)
5. `cv2.fitLine` → shaft direction
6. Radial check: shaft must point toward center (cos > 0.93)
7. Project contour points onto shaft → find endpoints
8. **Line-Ellipse Intersection** → accurate tip position

### Method Ⓑ HoughLinesP
**File**: `arrow_detection_service.py:2075-2183`

1. Multi-channel Canny: enhanced_bilateral + saturation + morph_grad
2. Dilate edges (2×2)
3. Mask to target face ellipse
4. `cv2.HoughLinesP(threshold=35, minLineLength=40, maxLineGap=25)`
5. Merge collinear segments (angle < 7°, perpendicular distance < 12px)
6. Filter: length > 35px, not horizontal/vertical (grid lines)
7. Radial angle check in ellipse-normalized coordinates (cos > 0.90)
8. Shaft continuity verification (valley/ridge profile)
9. **Line-Ellipse Intersection** → tip

### Method Ⓒ Contour Aspect Ratio
**File**: `arrow_detection_service.py:2185-2300`

- Similar to Ⓑ but uses contour-level analysis
- Aspect ratio threshold > 4.0 (stricter)
- Solidity check > 0.30
- Same radial/continuity/intersection pipeline

### Method Ⓓ Puncture Hole Detection (Highest Confidence)
**File**: `arrow_detection_service.py:1553-1699`

1. **Blackhat morphology**: `morphologyEx(BLACKHAT, kernel=31×31)` — highlights dark features smaller than kernel
2. **OTSU thresholding**: +20% to reject faint old holes
3. Connected component analysis:
   - Area: 50-3000 px² (rejects tiny pinholes and large blobs)
   - **Elongation**: aspect ratio > 2.0 (fresh holes are oblong)
   - **Radial alignment**: hole long axis points toward center (cos > 0.65)
4. **Depth score**: mean blackhat intensity → darker = fresher hole
5. Confidence formula: `0.35 + depth*0.45 + aspect*0.02 + radial*0.08`
6. Returns top 6 candidates sorted by confidence

### Method Ⓔ SIFT Keypoints
**File**: `arrow_detection_service.py:1900-1951`

- `cv2.SIFT_create(nfeatures=200, contrastThreshold=0.03, edgeThreshold=15)`
- Filter: size 3-25px, inside target (nd < 0.97)
- **Dark spot verification**: only accept if keypoint is darker than surrounding ring (rejects printed numerals, gridlines)
- **Corroboration only**: standalone SIFT hits are discarded unless another method found something within 20px
- Low confidence cap: max 0.62

### NMS (Non-Maximum Suppression)
**File**: `arrow_detection_service.py:1792-1867`

Deduplication strategy:
- Sort by confidence (descending)
- For each candidate, check against existing merged arrows:
  - **Tip distance** < 35-45px (scaled by target size)
  - **Perpendicular distance** < 18-25px (shaft-based)
  - **Angular similarity** < 15°
- Keep higher-priority method's position
- Method priority: puncture_hole(5) > sift(4) > hough_lines(3) > color_segment(2) > contour_aspect(1)
- Final filter: remove detections with normalized distance > 1.0

---

## Line-Ellipse Intersection Algorithm
**File**: `arrow_detection_service.py:1445-1507`

এটি scoring accuracy র জন্য **সবচেয়ে গুরুত্বপূর্ণ algorithm**:

```
Input: Line segment (x1,y1)-(x2,y2), Ellipse (cx,cy,a,b,angle)

1. Rotate line to ellipse coordinate frame (angle=0):
   - dx,dy = point - center
   - rx = dx*cos(-angle) - dy*sin(-angle)
   - ry = dx*sin(-angle) + dy*cos(-angle)

2. Parametric line: P(t) = start + t*(end-start)

3. Substitute into ellipse equation: (x/a)² + (y/b)² = 1
   → Quadratic in t: At² + Bt + C = 0

4. Solve for t, filter valid intersections (t ∈ [-0.1, 1.1])

5. Take smallest valid t → entry point (where shaft enters target)

6. Rotate intersection back to image coordinates
```

---

## Zone Calculation Details
**File**: `arrow_detection_service.py:2451-2461, 2552-2571`

```python
def _get_normalized_distance(self, x, y, target):
    # Transform to ellipse-aligned coordinates
    dx = x - target.center_x
    dy = y - target.center_y
    rad = -radians(target.angle)
    rx = dx * cos(rad) - dy * sin(rad)
    ry = dx * sin(rad) + dy * cos(rad)
    
    # Normalize by semi-axes
    a = target.a_outer or target.outer_radius
    b = target.b_outer or target.outer_radius
    return hypot(rx/a, ry/b)  # 0=center, 1=edge
```

Zone lookup table (cumulative boundaries):
```
norm ≤ 0.048 → Zone 10 (X ring, inner gold)
norm ≤ 0.096 → Zone 10 (outer gold)
norm ≤ 0.192 → Zone 9  (yellow)
norm ≤ 0.288 → Zone 8  (red inner)
norm ≤ 0.384 → Zone 7  (red outer)
norm ≤ 0.480 → Zone 6  (blue inner)
norm ≤ 0.576 → Zone 5  (blue outer)
norm ≤ 0.672 → Zone 4  (black inner)
norm ≤ 0.768 → Zone 3  (black outer)
norm ≤ 0.864 → Zone 2  (white inner)
norm ≤ 0.960 → Zone 1  (white outer)
norm > 0.960 → Zone 0  (miss)
```

---

## Scoring Service (Database Layer)
**File**: `src/services/scoring_service.py`

### Score Recording (with retry)
```
validate_score(zone, points) → check 0-10 range
↓
record_score_with_retry(max_retries=2, base_backoff=1.0)
  ├─ Attempt 1: Create Score record → commit
  ├─ Attempt 2: 1s backoff → retry
  └─ Attempt 3: 2s backoff → retry
      └─ All failed → emit ERROR_OCCURRED event
```

### Score Record Fields
| Field              | Type    | Description                |
|-------------------|---------|----------------------------|
| session_id        | int     | Session reference           |
| session_archer_id | int     | Archer in session           |
| round             | int     | Round number (1-20)        |
| arrow_num         | int     | Arrow number in round (1-6)|
| zone              | int     | Detected zone (0-10)       |
| points            | int     | Points awarded (0-10)      |
| image_id          | string  | UUID of saved image        |
| confidence        | float   | AI detection confidence     |
| validated_by_ai   | bool    | Whether AI validated       |

---

## Image Processing Flow
**File**: `src/services/image_service.py`

```
Upload Image (API endpoint)
    │
    ├─ detect_arrow_in_image(file_bytes)
    │   └─ ArrowDetectionService.detect() ← Full CV pipeline
    │      └─ Returns: {zone, points, confidence, method,
    │                    target_center, arrows[], ...}
    │
    ├─ save_image(file_bytes, session_id, round, arrow_num)
    │   └─ Preprocess: resize to 1024×1024, JPEG quality 70
    │   └─ Save to: /storage/raw/{session_id}/{uuid}.jpg
    │   └─ Check storage quota (10GB limit)
    │
    ├─ generate_annotated_image(file_bytes, detection)
    │   └─ Draw WA rings (perspective-correct ellipses)
    │   └─ Draw arrow tip crosshairs (color by confidence)
    │   └─ Draw center-to-tip lines
    │   └─ Add score/confidence overlay text
    │   └─ Save to: /storage/annotated/{session_id}/{uuid}.jpg
    │
    └─ ScoringService.record_score_with_retry()
        └─ Save to database + emit events
```

### Annotated Image Features
- **Concentric elliptical rings**: Gold, Red, Blue, Black, White (perspective-correct)
- **Arrow tip markers**: Green (conf≥0.85), Yellow (conf≥0.60), Red (conf<0.60)
- **Crosshair + number label**: Arrow index + zone score
- **Center-to-tip line**: Orange dashed line
- **Warning banner**: "⚠ Review Recommended" for low confidence
- **Score overlay**: Total points, arrow count, avg confidence, method name

---

## API Endpoints for Scoring
**File**: `src/api/scores.py`

| Endpoint                                    | Method | Description                          |
|--------------------------------------------|--------|--------------------------------------|
| `/sessions/{id}/scores`                     | POST   | Record score (manual)                |
| `/sessions/{id}/scores/upload`              | POST   | Upload image → auto-detect → score  |
| `/sessions/{id}/scores/batch-directory`     | POST   | Score all images in a folder         |
| `/sessions/{id}/scores`                     | GET    | List session scores                  |
| `/scores/{id}`                              | GET    | Get specific score                   |
| `/scores/{id}/validate`                     | POST   | Validate/invalidate score            |
| `/scores/{id}/image`                        | GET    | Get raw image                        |
| `/scores/{id}/image-annotated`              | GET    | Get annotated image                  |
| `/scores/{id}/override`                     | PUT    | Admin score override                 |

### Upload Flow (Most Important)
```
POST /sessions/{id}/scores/upload
Body: multipart/form-data {session_archer_id, round, arrow_num?, file}

1. Read uploaded image bytes
2. Run CV detection in ThreadPool (non-blocking)
3. Extract zone/points/confidence from each detected arrow
4. If session_archer_id <= 0: DRY RUN → return preview only
5. Else: save image → save annotated → record score for each arrow
6. Return aggregated score response with annotated image (base64)
```

---

## Confidence Scoring System

| Scenario                          | Confidence Range | Notes                        |
|----------------------------------|-----------------|------------------------------|
| Puncture hole (fresh, deep)       | 0.60 - 0.95    | Most reliable                 |
| HoughLines + continuity verified  | 0.35 - 0.85    | Reliable for clear shafts     |
| Color segment (high aspect)       | 0.35 - 0.75    | Moderate                      |
| SIFT (corroborated)              | 0.40 - 0.62    | Supporting evidence only      |
| Contour aspect                    | 0.30 - 0.72    | Weakest primary method        |
| Multi-method boost (+2 agree)     | +0.06          | Cross-validation bonus        |
| Multi-method boost (+3 agree)     | +0.12          | Strong consensus bonus        |
| Fallback (dark cluster)           | ×0.65          | Target-only, no shaft found   |
| Pure geometric fallback           | ×0.25          | Neither target nor shaft      |
