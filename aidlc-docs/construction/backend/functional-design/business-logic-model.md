# Backend Functional Design — Business Logic Model

**Project**: Automated Archery Scoring System  
**Unit**: Backend  
**Date**: 2026-05-23  
**Phase**: CONSTRUCTION - Functional Design (Part 2: Artifacts)  

---

## Image Processing Pipeline

### High-Level Flow

```
User triggers scoring
    ↓
ImageCaptureComponent.capture_burst()
    ├─ Capture 3 frames from camera
    ├─ Apply focus blur metric (Laplacian variance)
    └─ Select sharpest frame
    ↓
ImagePreprocessComponent.preprocess_image()
    ├─ Convert to HSV color space
    ├─ Apply Gaussian blur (denoise)
    ├─ Adjust brightness/contrast (normalize lighting)
    └─ Output: normalized image
    ↓
RingDetectionComponent.detect_rings()
    ├─ Primary: Hough Circle Transform
    │   ├─ Convert to grayscale
    │   ├─ Apply Canny edge detection
    │   └─ HoughCircles(param1=50, param2=30, minDist=50)
    ├─ Fallback if fails: Contour Analysis
    │   ├─ Find contours via cv2.findContours()
    │   ├─ Filter by circularity
    │   └─ Sort by area (largest = outer ring)
    └─ Output: ring centers, radii, confidence
    ↓
ArrowDetectionComponent.detect_arrows()
    ├─ Hybrid approach: vote across 3 methods
    │
    ├─ Method 1: Color-based thresholding
    │   ├─ HSV thresholding (arrow color range)
    │   ├─ Find largest contour (arrow shaft)
    │   └─ Compute center of mass
    │
    ├─ Method 2: Edge detection
    │   ├─ Canny edge detection
    │   ├─ Detect straight lines (Hough line transform)
    │   └─ Find longest line (arrow shaft)
    │
    ├─ Method 3: Moment-based
    │   ├─ Compute image moments (center of mass)
    │   ├─ Weight by pixel intensity
    │   └─ Find weighted centroid
    │
    ├─ Voting: triangulate position (average of 3 methods)
    └─ Output: arrow position (x, y), confidence (0-100%)
    ↓
ScoringCalculatorComponent.calculate_scores()
    ├─ For each arrow position (x, y):
    │   ├─ Compute distance from ring center
    │   ├─ Determine zone (based on 11-zone model)
    │   └─ Map zone to points (0-10)
    ├─ Aggregate: total end score = sum of 3 arrows
    └─ Output: zones[], total_score, confidence
    ↓
ScoreRepository.bulk_create_scores()
    ├─ Create 3 Score records (one per arrow)
    ├─ Store zone, points, confidence, raw_image_path
    └─ Transaction: all-or-nothing
    ↓
Session state updated + event published
    ↓
WebSocket broadcasts to all clients (< 100ms)
```

---

## Scoring Algorithm Details

### Ring Detection (Primary: Hough Circle Transform)

**Algorithm**:
1. Convert image to grayscale
2. Apply Gaussian blur (σ=5) to denoise
3. Apply Canny edge detection (thresh1=50, thresh2=150)
4. Run HoughCircles():
   - `dp=1` (resolution)
   - `minDist=50` (minimum distance between circle centers)
   - `param1=50` (upper Canny threshold)
   - `param2=30` (threshold for center detection)
   - `minRadius=20` (outer ring minimum)
   - `maxRadius=200` (outer ring maximum)
5. Filter results: keep only concentric circles (nested)
6. Sort by radius (descending): outer, middle, inner

**Output**: Ring boundaries (3 circles: outer, middle, inner ring)

**Fallback** (if HoughCircles fails):
- Contour analysis via edge detection
- Find closed contours with circularity > 0.8
- Sort by area (largest = outer ring)

### Arrow Detection (Hybrid: 3-Method Vote)

**Method 1: Color-Based Thresholding**
- HSV range: H ∈ [arrow_hue ± 10], S > 100, V > 100
- Find largest contour (arrow shaft)
- Center of mass: `(∑x*pixel / ∑pixel, ∑y*pixel / ∑pixel)`

**Method 2: Edge Detection + Hough Lines**
- Canny edge detection (50, 150)
- HoughLinesP() for line segments
- Find longest straight line (likely arrow shaft)
- Line midpoint = arrow position

**Method 3: Moment-Based Weighted Centroid**
- Compute image moments (up to order 3)
- Weighted centroid: `(M10/M00, M01/M00)` where M = intensity moment
- More robust to irregular arrow shapes

**Voting Strategy**:
- Triangulate 3 positions: `arrow_pos = (pos1 + pos2 + pos3) / 3`
- Confidence = mean confidence of 3 methods

### Zone-to-Points Mapping (11 Zones)

Target has concentric rings: outer, middle, inner. Each ring can be divided into zones.

**Zone Model**:
```
Zone 10: Inner ring center (bullseye)
Zone 9:  Inner ring outer edge
Zone 8:  Middle ring inner edge
Zone 7:  Middle ring center
Zone 6:  Middle ring outer edge
Zone 5:  Outer ring inner edge
Zone 4:  Outer ring center
Zone 3:  Outer ring outer edge
Zone 2:  Beyond target (glance)
Zone 1:  Off target (miss)
Zone 0:  Complete miss (not on target)
```

**Point Values**:
```
Zone 10: 10 points
Zone 9:  10 points
Zone 8:   8 points
Zone 7:   7 points
Zone 6:   6 points
Zone 5:   5 points
Zone 4:   4 points
Zone 3:   3 points
Zone 2:   1 point
Zone 1:   0 points
Zone 0:   0 points (error)
```

**Calculation**:
```python
distance_from_center = euclidean(arrow_pos, ring_center)

if distance_from_center < inner_ring_radius:
    if distance_from_center < 0.3 * inner_ring_radius:
        zone = 10  # bullseye center
    else:
        zone = 9   # inner ring
elif distance_from_center < middle_ring_radius:
    if distance_from_center < 0.5 * (inner_radius + middle_radius):
        zone = 8   # middle ring inner
    else:
        zone = 7 if distance < 0.75*middle else 6  # middle ring
elif distance_from_center < outer_ring_radius:
    # Similar subdivisions for outer ring
    zone = 5, 4, or 3
else:
    zone = 2 if near_target else 0
```

---

## Confidence Score Calculation

**Confidence** = how confident is the system in the detected arrow position (0-100%)

**Inputs**:
- Ring detection confidence (0-100%): how clear are the rings?
- Arrow detection confidence (0-100%): how certain is the arrow position?
- Method agreement (if methods vote differently, confidence decreases)

**Formula**:
```python
confidence = 0.6 * ring_confidence + 0.4 * arrow_confidence

# Adjust for method agreement in arrow detection
method_agreement = 1.0 - (std_dev_of_3_methods / avg_distance)
confidence *= method_agreement
```

**Interpretation**:
- **> 90%**: High confidence, likely accurate
- **80-90%**: Good confidence, minor detection noise
- **60-80%**: Acceptable, some ambiguity (FLAG FOR REVIEW)
- **< 60%**: Low confidence, retry recommended

**Handling**:
- Confidence ≥ 80%: Return result, informational only
- 60% ≤ Confidence < 80%: **FLAG FOR MANUAL REVIEW**, but auto-accept (UI shows yellow warning)
- Confidence < 60%: User can retry or override manually

---

## Image Capture & Burst Mode

### Burst Mode Logic

**Capture Sequence**:
1. Request 3 consecutive frames from camera (50ms apart)
2. For each frame:
   - Extract and store temporarily
   - Compute sharpness metric: Laplacian variance
3. Select sharpest frame (highest Laplacian variance)
4. Use selected frame for processing
5. Discard other 2 frames

**Sharpness Metric** (Laplacian Variance):
```python
def compute_sharpness(image):
    laplacian = cv2.Laplacian(image, cv2.CV_64F)
    variance = laplacian.var()
    return variance
```

- Higher variance = sharper image
- Filters out blurry frames automatically

**Performance**:
- Capture: 200ms (3 × ~67ms per frame @ 15 fps)
- Sharpness computation: negligible (< 5ms total)

---

## Multi-Camera Concurrent Scoring

### ThreadPool Architecture

**Configuration**:
- `ThreadPoolExecutor(max_workers=4)` in ScoringService
- Each camera processed in parallel thread
- Maximum 4 simultaneous image processing pipelines

**Concurrency Pattern**:
```python
def score_end(session_id, archers_with_cameras):
    futures = []
    
    with ThreadPoolExecutor(max_workers=4) as executor:
        for archer, camera in archers_with_cameras:
            future = executor.submit(
                self._score_single_camera,
                session_id, archer, camera
            )
            futures.append(future)
    
    # Wait for all threads to complete
    results = [f.result() for f in futures]  # blocks until all done
    
    # Aggregate and persist
    self._persist_all_scores(results)
    
    return results
```

**Thread Safety**:
- Each thread gets independent camera and image
- No shared state between threads
- Database uses row locks (pessimistic locking) for session updates
- Scoring transaction is serialized at DB level

**Performance Impact**:
- With 4 cameras: ~1000ms (max latency = longest single-camera latency)
- Compared to sequential: 4×1000ms = 4000ms
- **Speedup**: 4x improvement with 4 cameras

---

## Error Handling & Retry Logic

### Ring Detection Failure

**Scenario**: HoughCircles fails (no rings detected, or nonsensical circles)

**Response**:
1. Log warning: "Ring detection failed, retrying with adjusted parameters"
2. Retry with adjusted Hough parameters:
   - Try `param2=20` (lower threshold, more sensitive)
   - Try different `minDist=30` (tighter spacing)
3. If still fails, use Contour fallback
4. If Contour also fails, log error and request user override

**User Override Path**:
- Frontend shows captured image
- User manually selects zone
- Backend stores override with reason "detection_failed"
- Audit trail logs manual intervention

### Arrow Detection Failure

**Scenario**: No arrows detected or position nonsensical

**Response**:
1. Retry with adjusted color thresholds (broaden HSV range)
2. If still no detection, try edge-based or moment-based methods
3. If all methods fail, prompt user for manual selection

### Database Concurrency

**Row-Level Locking** (Pessimistic):
```python
session = db.query(Session).with_for_update().filter(Session.id == session_id).first()
# Only one thread can hold lock at a time
# Other threads wait
session.last_score_at = now()
db.commit()
# Lock released
```

**Atomicity**:
- All 3 score inserts happen in single transaction
- Session state update included
- Event publish after commit (eventual consistency acceptable for events)

---

## Data Persistence & Storage

### Score Record Structure

```python
class Score(Base):
    __tablename__ = "scores"
    
    id: str (UUID, primary key)
    session_id: str (foreign key)
    archer_id: str (foreign key)
    end_num: int (which round, 1-10 typically)
    arrow_num: int (1-3 within end)
    zone: int (0-10)
    points: int (0-10)
    confidence: float (0-100%)
    raw_image_path: str (/storage/raw/session_{id}/end_{num}_arrow_{num}.jpg)
    annotated_image_path: str (/storage/annotated/...)
    is_override: bool (manual override flag)
    override_reason: str (if override)
    created_at: datetime
```

### Image Storage

**Strategy**: Filesystem (`/storage/raw/` and `/storage/annotated/`)

**Directory Structure**:
```
/storage/
├── raw/
│   ├── session_uuid_1/
│   │   ├── end_1_arrow_1.jpg
│   │   ├── end_1_arrow_2.jpg
│   │   ├── end_1_arrow_3.jpg
│   │   ├── end_2_arrow_1.jpg
│   │   └── ...
│   └── session_uuid_2/
├── annotated/
│   ├── session_uuid_1/
│   │   ├── end_1_arrow_1_annotated.jpg
│   │   └── ...
│   └── ...
└── quota_tracking.json
```

**Rationale**:
- Raw JPEG images (~1-5 MB each)
- 300-600 images per session (100-200 records × 3 arrows)
- = 1-3 GB per session
- **Database BLOB unsuitable** (bloats DB, slow queries)
- **Filesystem suitable** (fast I/O, easy pruning)

**Retention Policy**:
- Store for 90 days (configurable)
- Auto-archive → compress to tar.gz
- Delete old archives per storage quota (default 10 GB)
- Monitor: warn at 80%, alert at 90%

### Annotated Images

**Generation**: Always generated (after scoring)

**Content**:
- Original image with overlays:
  - Green circles for detected rings (with radii labeled)
  - Red dot for detected arrow position
  - Zone label and point value

**Purpose**:
- Debugging (verify detection accuracy)
- Audit trail (visual record of scoring)
- User review (scorers can verify manually)

---

## Performance Profiling

### Target Breakdown (1000ms total)

| Stage | Target | Budget | Implementation |
|---|---|---|---|
| Capture | 200ms | 200ms | 3 burst frames @ 67ms each |
| Preprocess | 300ms | 300ms | Gaussian blur, HSV conversion, normalization |
| Ring Detect | 200ms | 200ms | Hough + fallback contour |
| Arrow Detect | 150ms | 150ms | 3 methods, vote |
| Calculate | 50ms | 50ms | Zone mapping, distance calc |
| **Total** | | **1000ms** | |

### Performance Policy

**If stage exceeds budget**:
- Accept latency if accuracy preserved (Q14: Option D)
- Don't sacrifice detection quality for speed
- Optimize in future iterations if needed

**Optimization Targets** (post-MVP):
- GPU acceleration for image processing (CUDA/OpenCL)
- Parallel ring + arrow detection (not sequential)
- Cached Hough parameters for similar lighting
- ML-based zone classification (faster than geometric)

---

## Testing & Validation

### Unit Test Categories (60-70% target coverage)

1. **Ring Detection Tests** (10 tests)
   - Valid target image → rings detected
   - Rotated target → rings still detected
   - Low-light image → fallback method used
   - No rings → error handled

2. **Arrow Detection Tests** (12 tests)
   - Arrow in zone 10 → zone 10 detected
   - Arrow in zone 5 → zone 5 detected
   - Multiple arrow angles → position correct
   - Method voting → consensus position

3. **Zone Mapping Tests** (8 tests)
   - Distance-to-zone conversion
   - Edge cases (exactly on ring boundary)
   - Off-target arrow → zone 0-2

4. **Confidence Calculation Tests** (6 tests)
   - High-confidence inputs → high output
   - Low-confidence inputs → low output
   - Method disagreement → confidence reduced

5. **Score Persistence Tests** (8 tests)
   - 3 scores inserted atomically
   - Session state updated
   - Event published
   - Concurrent writes serialized

6. **Override Validation Tests** (4 tests)
   - Override allowed if confidence < 50%
   - Override rejected if confidence > 50%
   - Reason logged

7. **Integration Tests** (15+ tests)
   - End-to-end: capture → detect → score → persist
   - Multi-camera concurrent scoring
   - Error recovery (retry logic)
   - WebSocket broadcast

### Test Data

**Synthetic Images**:
- Generated target images (various arrow positions)
- Lighting variations (bright, dim, shadow)
- Rotations (0°, 45°, 90°)

**Real Images**:
- 20+ actual archery photos (from open-source datasets)
- Annotation: ground-truth zones for comparison

