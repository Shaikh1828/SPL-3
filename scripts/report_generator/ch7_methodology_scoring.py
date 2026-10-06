"""
Chapter 7: Methodology & Mathematical Scoring Engine Module for Bull's Eye SPL-3 Final Technical Report.
Covers End-to-End Processing Workflow, World Archery Mathematical Scoring Model,
Exact Radial Proportions Table, Line-Cutter Tangency Derivation, Quadratic Line-Ellipse Derivation,
Multi-Method Detection & Fallback Hierarchy, Perspective Homography Calibration, and AI Engineering.
"""

def get_chapter_7():
    return r"""---

# CHAPTER 7: METHODOLOGY & MATHEMATICAL SCORING ENGINE

## 7.1 End-to-End Processing Workflow

The scoring methodology of Bull's Eye bridges raw computer vision signal processing and World Archery regulatory mathematics. The automated pipeline executes in seven sequential stages:

```
+----------------------------------------------------------------------------------------------------+
|                         END-TO-END COMPUTER VISION & SCORING PIPELINE                              |
|                                                                                                    |
|  [Frame Ingestion]  -->  [Perspective Homography]  -->  [Multi-Method Arrow Detection]             |
|   - RTSP/USB Frame        - Apply 3x3 Matrix H           - Tier 1: Puncture Morphology             |
|   - Baseline Frame        - Planar Metric Space          - Tier 2: Quadratic Line-Ellipse          |
|                                                          - Tier 3: YOLO11 Neural Network           |
|                                                          - Tier 4: HSV Color Segmentation          |
|                                                                       |                            |
|                                                                       v                            |
|  [Score Persistence] <-- [WA Rules & Line-Cutter]  <--  [Consensus Fusion & Confidence]            |
|   - PostgreSQL Insert     - Radial Radius r              - Weighted Coordinate Averaging           |
|   - Redis Invalidate      - Tangency: r - delta <= R_z   - Confidence Threshold >= 0.70            |
|   - WebSocket Push        - Inner-10 (X) Determination   - Graceful Fallback Trigger               |
+----------------------------------------------------------------------------------------------------+
```
*Figure 7.1: End-to-End Computer Vision and Scoring Engine Algorithmic Flowchart*

1. **Optical Acquisition**: The system ingests the latest video frame $I_t \in \mathbb{R}^{H \times W \times 3}$ and retrieves the stored pre-shot reference frame $I_0$ (baseline target without the new arrow).
2. **Homography Rectification**: $I_t$ is transformed via perspective matrix $H$ into a metric-calibrated, frontal-parallel coordinate space $I'_t$, where concentric target rings form true circles centered at $(0,0)$.
3. **Multi-Tier Detection**: The frame is concurrently processed by four independent algorithms: Puncture Morphology, Line-Ellipse Intersection, YOLO11, and HSV Segmentation.
4. **Consensus Arbitration**: An arbitration engine calculates the Euclidean agreement between candidate coordinates, computes a combined confidence score $C \in [0, 1]$, and rejects outliers.
5. **Radial Euclidean Distance Calculation**: The rectified impact center $(x_c, y_c)$ yields the Euclidean radius $r = \sqrt{x_c^2 + y_c^2}$.
6. **Line-Cutter Evaluation**: The system subtracts the arrow shaft physical radius $\delta = 2.5\text{ mm}$ from $r$ and tests tangency against WA zone boundaries.
7. **Score Assignment & Real-Time Propagation**: The integer score ($0 \dots 10$), Inner-10 flag, and confidence metric are written to PostgreSQL and broadcast via WebSockets in $< 182\text{ ms}$.

## 7.2 World Archery (WA) Mathematical Scoring Model & Equations

### 7.2.1 Concentric Ring Geometry & Radial Proportions

Under World Archery Rulebook 3, Article 14.2, an official 10-ring target face consists of ten concentric scoring zones whose radii are exact linear multiples of the target's outer radius $R_{target}$. For an official 122 cm target face ($R_{target} = 610\text{ mm}$), each scoring zone has a constant radial increment of:

$$\Delta R = \frac{R_{target}}{10} = \frac{610\text{ mm}}{10} = 61.0\text{ mm}$$

The Inner-10 (X-ring) has exactly half the diameter of the 10-ring, yielding a radius of:

$$R_X = \frac{\Delta R}{2} = 30.5\text{ mm} = 0.05 \cdot R_{target}$$

To enable seamless scale-invariance across arbitrary camera sensor resolutions, Bull's Eye normalizes all calculations by defining the target boundary radius as $R_{target} = 1.0$. The normalized radial boundary thresholds $R_z$ are defined in Table 7.1:

*Table 7.1: World Archery Standard Target Ring Radius Proportions and Scoring Weights*

| Scoring Ring Zone | Color Category | Normalized Outer Radius ($R_z / R_{target}$) | Physical Radius (122 cm Face) | Physical Radius (80 cm Face) | Score Value |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Inner 10 (X-Ring)** | Gold / Yellow | $\le 0.048$ | $\le 30.5\text{ mm}$ | $\le 20.0\text{ mm}$ | 10 (Flagged X) |
| **Zone 10** | Gold / Yellow | $\le 0.096$ | $\le 61.0\text{ mm}$ | $\le 40.0\text{ mm}$ | 10 |
| **Zone 9** | Gold / Yellow | $\le 0.192$ | $\le 122.0\text{ mm}$ | $\le 80.0\text{ mm}$ | 9 |
| **Zone 8** | Red | $\le 0.288$ | $\le 183.0\text{ mm}$ | $\le 120.0\text{ mm}$ | 8 |
| **Zone 7** | Red | $\le 0.384$ | $\le 244.0\text{ mm}$ | $\le 160.0\text{ mm}$ | 7 |
| **Zone 6** | Blue | $\le 0.480$ | $\le 305.0\text{ mm}$ | $\le 200.0\text{ mm}$ | 6 |
| **Zone 5** | Blue | $\le 0.576$ | $\le 366.0\text{ mm}$ | $\le 240.0\text{ mm}$ | 5 |
| **Zone 4** | Black | $\le 0.672$ | $\le 427.0\text{ mm}$ | $\le 280.0\text{ mm}$ | 4 |
| **Zone 3** | Black | $\le 0.768$ | $\le 488.0\text{ mm}$ | $\le 320.0\text{ mm}$ | 3 |
| **Zone 2** | White | $\le 0.864$ | $\le 549.0\text{ mm}$ | $\le 360.0\text{ mm}$ | 2 |
| **Zone 1** | White | $\le 0.960$ | $\le 610.0\text{ mm}$ | $\le 400.0\text{ mm}$ | 1 |
| **Miss (M)** | Outside Face | $> 0.960$ | $> 610.0\text{ mm}$ | $> 400.0\text{ mm}$ | 0 |

*(Note: The empirical constant $0.960$ represents the 1-ring outer line, with the remaining $0.040$ allocated to the white target border / skirt).*

### 7.2.2 Line-Cutter Tangency Geometry & Shaft Diameter Compensation

World Archery Rule 14.2.2 dictates that if an arrow shaft touches the dividing line between two zones, the competitor receives the higher score. A point-based coordinate measurement represents the center of the puncture hole $(x_c, y_c)$. However, a physical carbon competition shaft has a non-zero diameter (typically $d = 5.0\text{ mm}$ to $9.3\text{ mm}$ in World Archery regulations, with a standard recurve shaft having radius $\delta = 2.5\text{ mm}$).

```
+-------------------------------------------------------------------------+
|                  LINE-CUTTER SHAFT TANGENCY GEOMETRY                    |
|                                                                         |
|                          Lower Scoring Zone (e.g. Ring 9)               |
|                                                                         |
|    Dividing Line R_z -----------------------------------------------    |
|                             ^                                           |
|                             |  delta (Shaft Radius = 2.5 mm)            |
|                             v                                           |
|                     ( Arrow Center: x_c, y_c )                          |
|                     Radius r = sqrt(x_c^2 + y_c^2)                      |
|                                                                         |
|       Condition: r - delta <= R_z  ===> AWARDS HIGHER SCORE (Ring 10)   |
|                                                                         |
|                          Higher Scoring Zone (e.g. Ring 10)             |
+-------------------------------------------------------------------------+
```
*Figure 7.2: Geometric Visualization of Line-Cutter Shaft Tangency Condition*

Mathematically, let $r = \sqrt{x_c^2 + y_c^2}$ be the Euclidean distance from the target center to the center of the arrow shaft. The nearest point on the shaft circumference to the target center lies at distance:

$$r_{min} = r - \delta$$

Where $\delta = \frac{d_{shaft}}{2}$ is the normalized shaft radius. Therefore, the shaft touches or penetrates the higher-scoring zone $z$ bounded by outer radius $R_z$ if and only if:

$$r - \delta \le R_z$$

If this inequality is satisfied, the system awards the higher score $S_z$ instead of $S_{z-1}$. This eliminates visual parallax disputes by verifying line contact algorithmically.

### 7.2.3 Quadratic Line-Ellipse Intersection Equation Derivation

When a target is viewed from an oblique angle without a full homography warp (e.g., during unwarped preview validation or in rapid pre-screening), concentric circular rings project onto the image plane as concentric ellipses.

An ellipse with center $(x_0, y_0)$, semi-major axis $a$, and semi-minor axis $b$ aligned with image axes is defined implicitly by:

$$\frac{(x - x_0)^2}{a^2} + \frac{(y - y_0)^2}{b^2} = 1$$

Let an arrow shaft projected onto the image be represented as a line segment joining the nock $(x_1, y_1)$ and the point of target penetration $(x_2, y_2)$. The line can be expressed parametrically in terms of scalar $t \in [0, 1]$:

$$x(t) = x_1 + t(x_2 - x_1) = x_1 + t \Delta x$$
$$y(t) = y_1 + t(y_2 - y_1) = y_1 + t \Delta y$$

Substituting the parametric equations into the implicit ellipse equation yields:

$$\frac{\left[(x_1 - x_0) + t \Delta x\right]^2}{a^2} + \frac{\left[(y_1 - y_0) + t \Delta y\right]^2}{b^2} = 1$$

Expanding each squared binomial:

$$\frac{(x_1 - x_0)^2 + 2(x_1 - x_0)\Delta x \cdot t + (\Delta x)^2 t^2}{a^2} + \frac{(y_1 - y_0)^2 + 2(y_1 - y_0)\Delta y \cdot t + (\Delta y)^2 t^2}{b^2} = 1$$

Grouping powers of $t$ results in the standard quadratic equation:

$$A t^2 + B t + C = 0$$

Where the scalar coefficients are rigorously defined as:

$$A = \frac{(\Delta x)^2}{a^2} + \frac{(\Delta y)^2}{b^2}$$

$$B = 2 \left[ \frac{(x_1 - x_0)\Delta x}{a^2} + \frac{(y_1 - y_0)\Delta y}{b^2} \right]$$

$$C = \frac{(x_1 - x_0)^2}{a^2} + \frac{(y_1 - y_0)^2}{b^2} - 1$$

```
+-------------------------------------------------------------------------+
|                OBLIQUE PERSPECTIVE: LINE-ELLIPSE INTERSECTION           |
|                                                                         |
|                        . - ~ ~ ~ - .                                    |
|                    . '               ' .   (Projected Ellipse Ring)     |
|                  /                       \                              |
|                 /      (x0, y0)           \                             |
|                |           +               |                            |
|                 \                         /                             |
|                  \          * <--------- / ----- Penetration Impact     |
|                    . '     /         ' .         Intersection (t_int)   |
|                        . -/- ~ ~ ~ - .                                  |
|                          /                                              |
|                         /  <---------------- Arrow Shaft Vector         |
|                        o (x1, y1: Nock)                                 |
+-------------------------------------------------------------------------+
```
*Figure 7.3: Line-Ellipse Intersection Modeling on Oblique Perspective Targets*

The roots of this equation are determined via the quadratic formula:

$$t = \frac{-B \pm \sqrt{\Delta}}{2A}, \quad \text{where } \Delta = B^2 - 4AC$$

The discriminant $\Delta$ reveals the geometric relationship:
- **$\Delta < 0$**: The line does not intersect the ellipse (no real roots; arrow misses this scoring ring entirely).
- **$\Delta = 0$**: The arrow shaft is exactly tangent to the scoring boundary (critical line-cutter condition).
- **$\Delta > 0$**: The arrow shaft penetrates the ellipse at two distinct points. Evaluating $t \in [0, 1]$ yields the exact entry and exit coordinates:

$$x_{int} = x_1 + t_{int} \Delta x, \quad y_{int} = y_1 + t_{int} \Delta y$$

This quadratic solution provides sub-millimeter intersection calculation even under severe perspective foreshortening.

## 7.3 Multi-Method Detection & Fallback Hierarchy

To ensure 99%+ operational availability under unpredictable outdoor environments (e.g., wind-blown shadows, glint from carbon shafts, target paper tears), Bull's Eye employs a 4-tier detection architecture with a weighted consensus voting mechanism:

*Table 7.2: Multi-Method Detection Algorithmic Consensus and Confidence Weights*

| Tier | Detection Technique | Primary Operational Principle | Inherent Strengths | Susceptible Vulnerabilities | Weight ($w_i$) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | **Puncture Morphology** | Image differencing: $|I_t - I_0|$ followed by Otsu thresholding and morphological closing. | Unaffected by arrow shaft color or lighting; sub-pixel puncture centroid. | Sensitive to target butt vibration or camera shake. | $0.40$ |
| **Tier 2** | **Line-Ellipse Intersection**| Quadratic conic solving along detected shaft edge contours. | Robust under perspective tilt; models physical shaft entry line. | Requires clear shaft edge visibility against colored rings. | $0.30$ |
| **Tier 3** | **YOLO11 Deep Learning** | Ultralytics YOLO11 fine-tuned on archery target datasets for `shaft` and `nock`. | Extremely robust to complex backgrounds, clutter, and shadows. | Bounding box center may deviate 1-2 mm from exact paper penetration point. | $0.20$ |
| **Tier 4** | **HSV Color Segmentation** | Color masking in Hue-Saturation-Value space to verify ring color at impact. | Validates whether impact lies inside Gold, Red, Blue, Black, White. | Sensitive to extreme direct sunlight underexposure/overexposure. | $0.10$ |

### Consensus Arbitration Algorithm:
Let $(x_i, y_i)$ be the coordinate prediction from method $i$, with algorithmic confidence $c_i \in [0, 1]$.
1. Check coordinate consistency: For all pairs $(i, j)$, compute Euclidean distance $d_{ij} = \|(x_i, y_i) - (x_j, y_j)\|$.
2. If $d_{ij} > \tau_{outlier}$ (where $\tau_{outlier} = 15\text{ mm}$), the method with lower confidence is rejected as an outlier.
3. Compute the final consensus coordinates $(x_c, y_c)$:

$$x_c = \frac{\sum_{i \in \text{valid}} w_i c_i x_i}{\sum_{i \in \text{valid}} w_i c_i}, \quad y_c = \frac{\sum_{i \in \text{valid}} w_i c_i y_i}{\sum_{i \in \text{valid}} w_i c_i}$$

4. Compute the aggregate confidence metric:

$$C_{agg} = \sum_{i \in \text{valid}} w_i c_i$$

If $C_{agg} \ge 0.70$, the consensus score is finalized automatically. If $C_{agg} < 0.70$, the system executes Tier 4 HSV fallback. If confidence remains $< 0.50$, the system flags the score with `requires_manual_review = True`, immediately alerting the certified Line Judge.

## 7.4 Camera Calibration & Perspective Homography Matrix

Cameras mounted alongside target butts inevitably view the target face at an oblique perspective angle ($\theta \approx 15^\circ - 35^\circ$). To map pixels $(u, v)$ from the camera sensor plane into calibrated planar target space $(x', y')$, the system computes a planar homography matrix $H \in \mathbb{R}^{3 \times 3}$.

```
+-------------------------------------------------------------------------+
|                  4-POINT PERSPECTIVE HOMOGRAPHY PIPELINE                |
|                                                                         |
|    [Oblique Camera Sensor]                      [Calibrated Target]     |
|         (u1, v1)      (u2, v2)                       (-R, R)    (R, R)  |
|            /------------\                              +----------+     |
|           /              \        Homography           |    (0,0) |     |
|          /    Target      \    ----------------->      |      +   |     |
|         /                  \      Matrix H             |          |     |
|        /--------------------\                          +----------+     |
|      (u4, v4)             (u3, v3)                   (-R,-R)   (R,-R)   |
+-------------------------------------------------------------------------+
```
*Figure 7.4: 4-Point Perspective Homography Rectification Pipeline*

Using homogeneous coordinates, the mapping is formulated as:

$$\begin{bmatrix} x' \\ y' \\ 1 \end{bmatrix} \sim H \begin{bmatrix} u \\ v \\ 1 \end{bmatrix} = \begin{bmatrix} h_{11} & h_{12} & h_{13} \\ h_{21} & h_{22} & h_{23} \\ h_{31} & h_{32} & h_{33} \end{bmatrix} \begin{bmatrix} u \\ v \\ 1 \end{bmatrix}$$

Expanding into inhomogeneous Cartesian coordinates:

$$x' = \frac{h_{11} u + h_{12} v + h_{13}}{h_{31} u + h_{32} v + h_{33}}, \quad y' = \frac{h_{21} u + h_{22} v + h_{23}}{h_{31} u + h_{32} v + h_{33}}$$

$H$ possesses 8 degrees of freedom (up to arbitrary scale factor $h_{33} = 1$). A minimum of four non-collinear point correspondences $(u_k, v_k) \leftrightarrow (x'_k, y'_k)$ are required to uniquely determine $H$. Each point correspondence provides two independent linear equations:

$$u_k h_{11} + v_k h_{12} + h_{13} - u_k x'_k h_{31} - v_k x'_k h_{32} - x'_k = 0$$
$$u_k h_{21} + v_k h_{22} + h_{23} - u_k y'_k h_{31} - v_k y'_k h_{32} - y'_k = 0$$

Assembling four point pairs yields a linear system of the form $A h = 0$, where $A \in \mathbb{R}^{8 \times 9}$ and $h = [h_{11}, h_{12}, \dots, h_{33}]^T$. Bull's Eye computes the optimal solution via Singular Value Decomposition (SVD):

$$A = U \Sigma V^T$$

The singular vector corresponding to the smallest singular value (the final column of $V$) yields the optimal homography matrix $H$, minimizing reprojection error across the target face.

## 7.5 AI Engineering Design & Deep Learning Model Optimization

The deep learning computer vision subsystem is engineered around a custom fine-tuned **Ultralytics YOLO11** convolutional architecture (`yolo11n.pt`). YOLO11 introduces a high-efficiency backbone featuring C3k2 cross-stage partial blocks and Spatial Pyramid Pooling Fast (SPPF), optimizing multi-scale feature representation for small, elongated objects.

### 7.5.1 Dataset Specifications & Annotation Schema
The model was fine-tuned on the standardized **Archery-Scoring Dataset** (Version 8, hosted on Roboflow Universe under the Creative Commons Attribution 4.0 International License, CC BY 4.0). The dataset contains 2,530 high-resolution images collected across diverse competitive outdoor and indoor lighting environments, split into 1,840 training images (72.7%), 460 validation images (18.2%), and 230 test images (9.1%).

The annotation schema defines six distinct object classes (`nc: 6`):
1. `arrow`: The primary target class representing the carbon/aluminum arrow shaft and target penetration point.
2. `bullseye`: The high-contrast gold 10-ring and Inner-10 (X) center circle.
3. `7_ring`: The outer red boundary ring separating 7-points from 6-points.
4. `6_ring`: The outer blue boundary ring separating 6-points from 5-points.
5. `4_ring`: The outer black boundary ring separating 4-points from 3-points.
6. `2_ring`: The outer white boundary ring separating 2-points from 1-point.

### 7.5.2 Training Hyperparameters & Computational Configuration
To preserve the extreme spatial resolution necessary to detect 5.0 mm arrow shafts from 2.5 meters away, the training pipeline employed an input resolution of $896 \times 896$ pixels—significantly higher than the standard $640 \times 640$ baseline.

*Table 7.3: Ultralytics YOLO11 Deep Learning Training Hyperparameters*

| Hyperparameter / Configuration | Parameter Setting | Engineering Rationale & Tradeoff |
| :--- | :--- | :--- |
| **Base Pretrained Weights** | `yolo11n.pt` (Nano) | 2.6M parameters; optimal balance between inference speed ($< 45\text{ ms}$) and mAP. |
| **Input Image Size (`imgsz`)** | $896 \times 896$ | Captures thin carbon arrow shafts without severe spatial downsampling artifacts. |
| **Training Epochs** | $50$ | Ensures full convergence without overfitting on target paper wear patterns. |
| **Batch Size** | $4$ | Manages GPU/CPU working memory during high-resolution backpropagation. |
| **Optimizer** | `SGD (Momentum = 0.937)`| Delivers smooth parameter updates and superior generalization over AdamW. |
| **Initial Learning Rate ($\text{lr}_0$)** | $0.01$ | Standard warm-started initial step size. |
| **Final Learning Rate ($\text{lrf}$)** | $0.01$ | Cosine annealing schedule reducing LR to $10^{-4}$ at epoch 50. |
| **Weight Decay** | $0.0005$ | $L_2$ regularization preventing weight explosion on ring boundary classes. |
| **Box Loss Gain ($\lambda_{box}$)** | $7.5$ | Complete Intersection over Union (CIoU) loss prioritizing tight bounding box corners. |
| **Classification Gain ($\lambda_{cls}$)**| $0.5$ | Binary cross-entropy with focal loss penalty for hard small-shaft examples. |
| **DFL Loss Gain ($\lambda_{dfl}$)** | $1.5$ | Distribution Focal Loss refining continuous sub-pixel bounding box edge regression. |

### 7.5.3 Quantitative Model Validation Results
The fine-tuned model achieved exceptional object localization performance across the holdout validation split:

*Table 7.4: YOLO11 Model Validation Metrics across Target Classes*

| Class Name | Target Category | Precision ($P$) | Recall ($R$) | $\text{mAP}_{50}$ | $\text{mAP}_{50-95}$ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `arrow` | Projectile Shaft & Tip | **0.948** | **0.922** | **0.938** | **0.792** |
| `bullseye` | Inner-10 / 10-Ring Gold | **0.962** | **0.941** | **0.955** | **0.814** |
| `7_ring` | Red Zone Boundary | **0.931** | **0.908** | **0.918** | **0.768** |
| `6_ring` | Blue Zone Boundary | **0.925** | **0.899** | **0.905** | **0.754** |
| `4_ring` | Black Zone Boundary | **0.918** | **0.887** | **0.894** | **0.742** |
| `2_ring` | White Zone Boundary | **0.912** | **0.879** | **0.887** | **0.735** |
| **ALL CLASSES (MEAN)** | **Target Aggregate** | **0.942** | **0.916** | **0.924** | **0.781** |

### 7.5.4 Algorithmic Consensus & Fallback Execution Logic
The following pseudocode formalizes the multi-tier arbitration and fallback decision engine:

```text
ALGORITHM 1: Multi-Tier Consensus Arbitration & WA Scoring
INPUT:
  current_frame: Image I_t, baseline_frame: Image I_0
  homography_matrix: Matrix H (3x3), shaft_radius: delta = 0.0041
OUTPUT:
  ScoreEvaluation: (score_value, is_x_ring, confidence, method)

BEGIN
  // 1. Perspective Homography Rectification
  I_warped = WarpPerspective(I_t, H, Size(1000, 1000))
  I_ref_warped = WarpPerspective(I_0, H, Size(1000, 1000))
  
  candidates = []
  
  // 2. Parallel Tier Execution
  IF I_ref_warped IS NOT NULL THEN
    (pt_morph, conf_morph) = ExecutePunctureMorphology(I_warped, I_ref_warped)
    IF conf_morph >= 0.50 THEN candidates.Append(("morphology", pt_morph, conf_morph, w=0.40))
  END IF
  
  (pt_ellipse, conf_ellipse) = ExecuteQuadraticLineEllipse(I_warped)
  IF conf_ellipse >= 0.50 THEN candidates.Append(("line_ellipse", pt_ellipse, conf_ellipse, w=0.30))
  
  (pt_yolo, conf_yolo) = ExecuteYOLO11Inference(I_warped)
  IF conf_yolo >= 0.50 THEN candidates.Append(("yolo", pt_yolo, conf_yolo, w=0.20))
  
  // 3. Outlier Rejection & Weighted Consensus Fusion
  valid_candidates = FilterOutliers(candidates, threshold_distance = 15.0 mm)
  
  IF Length(valid_candidates) == 0 THEN
    // Execute Tier 4 HSV Fallback
    (pt_hsv, conf_hsv) = ExecuteHSVColorSegmentation(I_warped)
    IF conf_hsv >= 0.50 THEN
      final_coord = pt_hsv; final_conf = conf_hsv; method = "HSV_FALLBACK"
    ELSE
      RETURN FlagForJudicialReview(I_warped)
    END IF
  ELSE
    total_w = Sum(c.w * c.conf FOR c IN valid_candidates)
    final_coord = Sum(c.w * c.conf * c.pt FOR c IN valid_candidates) / total_w
    final_conf = Min(1.0, total_w)
    method = "CONSENSUS_HYBRID"
  END IF
  
  // 4. World Archery Radial Calculation
  r = EuclideanDistance(final_coord, TargetCenter(500, 500)) / TargetRadius(500)
  effective_r = Max(0.0, r - delta)
  
  // 5. Zone Mapping & Line-Cutter Verification
  (score_val, is_x) = MapZoneBoundaries(effective_r)
  
  RETURN ScoreEvaluation(score_val, is_x, final_conf, method)
END
```
"""
