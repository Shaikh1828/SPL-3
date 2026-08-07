# Scoring System Problems & Improvement Plan

## ⚠️ Critical Issues Identified

### Issue 1: No ML Model — Pure CV Pipeline
**Severity**: 🔴 Critical
**Impact**: Low accuracy, unreliable in varied conditions

**Current State**: 
- 2665 lines of hardcoded OpenCV rules in `arrow_detection_service.py`
- ~9 different HSV/LAB color ranges for arrow detection
- ~4 different HSV ranges for target ring colors
- All thresholds manually tuned to specific test images

**Problem**:
- Color ranges break under different lighting (outdoor sun, indoor fluorescent, overcast)
- Aspect ratio thresholds (>3 for arrows, >2 for holes) are arbitrary
- Confidence scores are computed from formulas, not learned distributions
- No way to improve without manual code changes

**Solution**: Train YOLOv8 model on the 504 annotated images in `Data/` folder

---

### Issue 2: Target Detection Failures
**Severity**: 🔴 Critical

**Failure Modes**:
1. **Yellow extrapolation explosion**: Yellow bullseye is 19.2% of target → 5.2x amplification → small mask error → huge radius error → rings drawn over grass/sky
2. **Wooden stand bleed**: `_target_by_dark_ring_boundary` saturation mask includes the dark wooden stand below target → ellipse fit too large
3. **Sky/grass color confusion**: Blue sky matches blue ring HSV range, green grass can trigger green arrow detection
4. **Close-up shots**: Only partial rings visible → ratio extrapolation from one ring is unreliable
5. **Multiple targets**: If multiple targets in frame, picks wrong one

---

### Issue 3: Arrow Detection False Positives
**Severity**: 🟡 High

**False Positive Sources**:
1. **Old puncture holes**: Hundreds of old holes on well-used targets → puncture_hole method fires on old ones
2. **Printed numerals/gridlines**: SIFT detects printed zone numbers as "features"
3. **Shadow lines**: HoughLinesP picks up shadow edges as arrow shafts
4. **Ring boundaries**: Color transitions between target rings → contour method sees as elongated features
5. **Stand/support structure**: Wooden posts, metal clips → detected as arrow shafts

---

### Issue 4: Arrow-on-Same-Color-Ring Problem
**Severity**: 🟡 High

When arrow color matches the ring it's on (red arrow on red ring, blue arrow on blue ring):
- Color segmentation fails completely (arrow merges with ring)
- Only HoughLinesP and contour methods can detect (edges still visible)
- Confidence drops significantly
- Zone calculation may be wrong if arrow is partially detected

---

### Issue 5: Multi-Arrow Confusion
**Severity**: 🟡 High

When multiple arrows are close together:
- NMS merges arrows that are < 35px apart (may merge distinct arrows)
- Shaft lines cross → HoughLinesP may connect wrong endpoints
- Puncture holes cluster → hard to distinguish individual hits
- Arrow numbering becomes arbitrary

---

### Issue 6: Confidence Calibration
**Severity**: 🟡 Medium

Current confidence scores are **not calibrated**:
- A confidence of 0.80 doesn't mean the detection is correct 80% of the time
- Puncture holes get high confidence even when detecting old holes
- Multi-method consensus boost can inflate confidence on false positives
- No confusion matrix or precision/recall analysis has been done

---

## 📋 Improvement Roadmap

### Phase 1: Train YOLOv8 Object Detection Model
```bash
# Install
pip install ultralytics

# Train
yolo detect train data=Data/data.yaml model=yolov8s.pt epochs=100 imgsz=896

# Evaluate
yolo detect val data=Data/data.yaml model=runs/detect/train/weights/best.pt

# Export for inference
yolo export model=runs/detect/train/weights/best.pt format=onnx
```

**Expected output**: Model that detects bounding boxes for:
- `arrow` (location + size)
- `bullseye` (center reference)
- `2_ring`, `4_ring`, `6_ring`, `7_ring` (target geometry)

### Phase 2: Integrate YOLO with Scoring Pipeline
Replace/supplement `ArrowDetectionService`:

```python
class HybridDetectionService:
    def __init__(self):
        self.yolo = YOLO('best.pt')
        self.cv_fallback = ArrowDetectionService()
    
    def detect(self, image_data):
        # Try YOLO first
        results = self.yolo.predict(image_data, conf=0.25)
        
        if self._has_valid_detections(results):
            return self._process_yolo_results(results)
        
        # Fall back to CV pipeline
        return self.cv_fallback.detect(image_data=image_data)
```

### Phase 3: Data Augmentation & Expansion
Current 504 images may not be enough. Augment with:
- **Brightness variation**: ±30%
- **Rotation**: ±15°
- **Gaussian blur**: σ=1-3
- **Color jitter**: HSV ±10%
- **Crop/zoom**: 80-120%
- **Add noise**: Salt & pepper

### Phase 4: Arrow Tip Keypoint Model
For more precise tip detection:
1. Annotate arrow tips as keypoints
2. Train YOLOv8-pose variant
3. Direct tip coordinate prediction

### Phase 5: Confidence Calibration
1. Run model on test set
2. Compute precision/recall per confidence threshold
3. Apply Platt scaling or isotonic regression
4. Map raw confidence → calibrated probability

---

## File Impact Map
When improving the scoring system, these files will be modified:

| File | Change Required |
|------|----------------|
| `src/services/arrow_detection_service.py` | Add YOLO inference path, keep CV fallback |
| `src/services/image_service.py` | Update detector initialization |
| `src/config.py` | Add YOLO model path config |
| `Data/data.yaml` | May need path adjustments |
| `pyproject.toml` | Add `ultralytics` dependency |
| `Dockerfile` | Include model weights in image |
| New: `src/services/yolo_detection_service.py` | YOLO-based detection service |
| New: `scripts/train_model.py` | Training script |
| New: `scripts/evaluate_model.py` | Evaluation script |
