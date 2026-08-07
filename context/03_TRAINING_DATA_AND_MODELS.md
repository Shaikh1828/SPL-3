# Training Data & Model Context

## Dataset Overview
**Source**: Roboflow (archery-scoring/archery-scoring v8)
**License**: CC BY 4.0
**Export Date**: June 4, 2026
**Format**: YOLOv8

## Dataset Statistics
| Split      | Images | Purpose                    |
|-----------|--------|----------------------------|
| Train     | 353    | Model training              |
| Validation| 76     | Hyperparameter tuning       |
| Test      | 75     | Final evaluation            |
| **Total** | **504**| Complete dataset            |

## Pre-processing Applied
- Auto-orientation of pixel data (EXIF-orientation stripping)
- Resize to **896×896** (Stretch)
- No augmentation applied

## Object Classes (6 total)
| Class Index | Class Name  | Description                          |
|------------|-------------|--------------------------------------|
| 0          | `2_ring`    | Zone 2 ring (white outer area)       |
| 1          | `4_ring`    | Zone 4 ring (black inner area)       |
| 2          | `6_ring`    | Zone 6 ring (blue inner area)        |
| 3          | `7_ring`    | Zone 7 ring (red outer area)         |
| 4          | `arrow`     | Arrow shaft/tip                       |
| 5          | `bullseye`  | Bullseye/center (gold/yellow area)   |

## data.yaml Configuration
```yaml
train: ../train/images
val: ../valid/images
test: ../test/images

nc: 6
names: ['2_ring', '4_ring', '6_ring', '7_ring', 'arrow', 'bullseye']
```

## Label Format (YOLOv8)
Each image has a corresponding `.txt` file in the `labels/` directory:
```
<class_id> <x_center> <y_center> <width> <height>
```
- All values normalized to [0, 1]
- One line per detected object
- Bounding box coordinates relative to image dimensions

## Directory Structure
```
Data/
├── data.yaml                # Dataset config
├── README.dataset.txt       # Dataset info
├── README.roboflow.txt      # Roboflow export info
├── train/
│   ├── images/              # 353 training images
│   └── labels/              # 353 label files (.txt)
├── valid/
│   ├── images/              # 76 validation images
│   └── labels/              # 76 label files
└── test/
    ├── images/              # 75 test images
    └── labels/              # 75 label files
```

---

## Current State: No ML Model Trained

### What's Currently Being Used Instead
The system uses **pure Computer Vision (OpenCV)** algorithms:
- Color segmentation (HSV/LAB color spaces)
- Hough Circle/Line transforms
- Morphological operations (blackhat, gradient)
- Contour analysis (aspect ratio, circularity)
- SIFT keypoint detection
- Manual geometric calculations

### Why This is a Problem
1. **Hardcoded thresholds**: Color ranges, size limits, confidence thresholds are all manually tuned — won't generalize
2. **No learning**: System can't improve from more data
3. **Lighting sensitivity**: HSV-based detection breaks under different lighting
4. **No arrow bounding box**: System tries to infer arrow tip from shaft lines — error-prone
5. **Old hole confusion**: System can't distinguish fresh arrow holes from old ones reliably

---

## What Needs to Be Done: Train YOLOv8 Model

### Step 1: Set Up Training Environment
```bash
pip install ultralytics
```

### Step 2: Train YOLOv8 Model
```python
from ultralytics import YOLO

# Load pretrained model
model = YOLO('yolov8n.pt')  # or yolov8s.pt for better accuracy

# Train on archery dataset
results = model.train(
    data='Data/data.yaml',
    epochs=100,
    imgsz=896,
    batch=16,
    name='archery_scoring',
    patience=20,
    augment=True,
)
```

### Step 3: Evaluate Model
```python
# Validate
metrics = model.val(data='Data/data.yaml')
print(f"mAP50: {metrics.box.map50}")
print(f"mAP50-95: {metrics.box.map}")

# Test on specific image
results = model.predict('path/to/test/image.jpg', save=True)
```

### Step 4: Integrate with Backend
Replace the pure-CV ArrowDetectionService with YOLO inference:
```python
class YOLOArrowDetectionService:
    def __init__(self, model_path='runs/detect/archery_scoring/weights/best.pt'):
        self.model = YOLO(model_path)
    
    def detect(self, image_data):
        results = self.model.predict(image_data)
        # Extract arrow bounding boxes
        # Extract ring bounding boxes
        # Calculate arrow tip from bbox
        # Map tip to zone using ring geometry
```

### Step 5: Fine-Tune for Edge Cases
- Add more images with different lighting conditions
- Add images with multiple arrows
- Add images from different angles/distances
- Use data augmentation (rotation, brightness, blur, etc.)

---

## Recommended Training Strategy

### Phase 1: Object Detection (YOLOv8)
- Train to detect: arrows, bullseye, rings
- This gives reliable bounding boxes for arrows and target components

### Phase 2: Keypoint Detection (Optional)
- Train a keypoint model for arrow tip position
- More precise than bounding box center

### Phase 3: Integration
- Use YOLO detections to locate target center from ring/bullseye bboxes
- Use arrow bbox to approximate tip location (endpoint closest to center)
- Fall back to current CV pipeline if YOLO detection fails

### Phase 4: Custom Post-Processing
- Use ring detections to calibrate WA zone boundaries
- Use arrow tip + ring geometry for accurate zone scoring
- Maintain current zone calculation logic (well-designed)
