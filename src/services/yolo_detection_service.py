"""
YOLO11-based Arrow Detection Service with Hybrid ML/CV Pipeline.
"""

import os
import math
from typing import Any, Dict, List, Optional, Tuple
import structlog

logger = structlog.get_logger()

import cv2
import numpy as np

try:
    from ultralytics import YOLO
    OPENCV_AND_YOLO_AVAILABLE = True
except ImportError:
    logger.warning("ultralytics_not_available_yolo_detection_disabled")
    OPENCV_AND_YOLO_AVAILABLE = False
    YOLO = None

from src.config import settings
from src.services.arrow_detection_service import (
    TargetInfo,
    ArrowInfo,
    DetectionResult,
    ArrowDetectionService,
    WA_ZONE_BOUNDARIES,
    WA_ZONE_SCORES,
)

class YOLOArrowDetectionService:
    """
    Hybrid YOLO11 and Computer Vision arrow detection pipeline.
    
    1. Locates target and arrows using YOLO11.
    2. Performs local line/edge scanning within arrow bounding boxes to find precise subpixel tips.
    3. Integrates with existing CV fallback pipelines if YOLO is disabled or fails.
    """
    
    def __init__(self, model_path: Optional[str] = None):
        self.model_path = model_path or settings.yolo_model_path
        self.model = None
        self.model_loaded = False
        self.cv_fallback_service = ArrowDetectionService()
        
        if OPENCV_AND_YOLO_AVAILABLE:
            self._load_model()
            
    def _load_model(self):
        try:
            # Check if model weights exist
            abs_model_path = os.path.abspath(self.model_path)
            if not os.path.exists(abs_model_path):
                # Fallback to check runs directory
                alt_path = os.path.abspath(os.path.join(
                    os.path.dirname(__file__), "..", "..", "runs", "detect", "archery_yolo11", "weights", "best.pt"
                ))
                if os.path.exists(alt_path):
                    abs_model_path = alt_path
                else:
                    logger.warning("yolo_weights_not_found", path=self.model_path)
                    return
            
            logger.info("loading_yolo_model", path=abs_model_path)
            self.model = YOLO(abs_model_path)
            self.model_loaded = True
            logger.info("yolo_model_loaded_successfully")
        except Exception as exc:
            logger.exception("yolo_model_load_error", error=str(exc))
            
    def detect(
        self,
        image_data: Optional[bytes] = None,
        image_path: Optional[str] = None,
        image_array: Optional[Any] = None,
    ) -> DetectionResult:
        """
        Main entry point for hybrid YOLO11 detection.
        """
        if not OPENCV_AND_YOLO_AVAILABLE or not self.model_loaded:
            logger.info("yolo_service_not_ready_falling_back_to_cv")
            return self.cv_fallback_service.detect(image_data, image_path, image_array)
            
        # Load image
        image = self._load_image(image_data, image_path, image_array)
        if image is None:
            return DetectionResult(
                zone=None, points=None, confidence=0.0, method="image_load_failed"
            )
            
        try:
            # Run YOLO inference directly on image to preserve unscaled pixel coordinates
            results = self.model.predict(image, conf=0.25, verbose=False)
            result = results[0]
            
            # Parse detections (already in original image coordinates)
            boxes = result.boxes.xyxy.cpu().numpy()
            confs = result.boxes.conf.cpu().numpy()
            classes = result.boxes.cls.cpu().numpy()
            
            # Preprocess for CV fallback if needed
            pp = self.cv_fallback_service._preprocess(image)
            
            # Detect target geometry from rings
            target = self._detect_target_from_yolo(boxes, confs, classes, image.shape)
            
            # If no target found, fall back to legacy CV target detection
            if not target:
                logger.info("yolo_target_not_found_trying_cv_target")
                target = self.cv_fallback_service._detect_target(image, pp)
                
            if not target:
                # Absolute fallback if target center cannot be resolved
                logger.warning("all_target_detection_methods_failed")
                return self.cv_fallback_service._pure_geometric_fallback(image, pp)
                
            # Detect arrows
            arrows = self._detect_arrows_hybrid(boxes, confs, classes, image, pp, target)
            
            # If no arrows found, fall back to CV target-only fallbacks
            if not arrows:
                logger.info("yolo_arrows_not_found_trying_cv_arrow_fallbacks")
                arrows = self.cv_fallback_service._detect_arrows(image, pp, target)
                
            if target and arrows:
                # Update arrow zones and points based on calculated distances
                for arr in arrows:
                    norm = self.cv_fallback_service._get_normalized_distance(arr.tip_x, arr.tip_y, target)
                    arr_zone = 0
                    for boundary, score in zip(WA_ZONE_BOUNDARIES, WA_ZONE_SCORES):
                        if norm <= boundary:
                            arr_zone = score
                            break
                    arr.zone = arr_zone
                    arr.points = arr_zone
                    
                # Deduplicate arrows using NMS
                arrows = self._deduplicate_arrows(arrows, target)
                
                if arrows:
                    primary_arrow = arrows[0]
                    res = self.cv_fallback_service._calculate_zone(target, primary_arrow)
                    res.target = target
                    res.arrow = primary_arrow
                    res.arrows = arrows
                    res.method = f"yolo11+{res.method}"
                    return res
                    
            # Fallback if target exists but no arrows
            res = self.cv_fallback_service._fallback_zone_from_target(image, pp, target)
            res.target = target
            res.method = f"yolo11+{res.method}"
            if res.arrow:
                res.arrow.zone = res.zone
                res.arrow.points = res.points
                res.arrows = [res.arrow]
            return res
            
        except Exception as exc:
            logger.exception("yolo_detection_critical_error", error=str(exc))
            return self.cv_fallback_service.detect(image_data, image_path, image_array)
            
    def _load_image(self, image_data, image_path, image_array) -> Optional[Any]:
        return self.cv_fallback_service._load_image(image_data, image_path, image_array)

    def _detect_target_from_yolo(
        self, boxes: np.ndarray, confs: np.ndarray, classes: np.ndarray, img_shape: Tuple
    ) -> Optional[TargetInfo]:
        """
        Calculates target center and radius using YOLO ring detections.
        Maps classes dynamically by name.
        """
        h, w = img_shape[:2]
        
        # Ring proportions definitions (WA Standard boundaries)
        name_to_ratio = {
            "bullseye": 0.192,  # Gold yellow (10/9)
            "7_ring": 0.384,    # Red (8/7)
            "6_ring": 0.480,    # Blue (6)
            "4_ring": 0.672,    # Black (4)
            "2_ring": 0.864,    # White (2)
        }
        
        # Fallback numeric map if names not set in model
        fallback_ratios = {
            5: 0.192,
            3: 0.384,
            2: 0.480,
            1: 0.672,
            0: 0.864,
        }
        
        model_names = getattr(self.model, "names", {})
        
        centers = []
        outer_radii_estimates = []
        confidences = []
        detected_rings = 0
        bullseye_center = None
        
        for i in range(len(classes)):
            cls_id = int(classes[i])
            cls_name = str(model_names.get(cls_id, "")).lower()
            
            ratio = None
            for rname, rval in name_to_ratio.items():
                if rname in cls_name:
                    ratio = rval
                    break
                    
            if ratio is None and cls_id in fallback_ratios:
                ratio = fallback_ratios[cls_id]
                
            if ratio is None:
                continue
                
            detected_rings += 1
            bx = boxes[i]
            conf = confs[i]
            
            # Compute center of the detected bounding box
            cx = float((bx[0] + bx[2]) / 2.0)
            cy = float((bx[1] + bx[3]) / 2.0)
            
            if "bullseye" in cls_name or cls_id == 5:
                bullseye_center = (cx, cy)
                
            centers.append((cx, cy))
            confidences.append(float(conf))
            
            # Compute average radius of the bounding box
            bw = float(bx[2] - bx[0])
            bh = float(bx[3] - bx[1])
            box_r = (bw + bh) / 4.0
            
            # Extrapolate target outer radius: outer_radius = box_r / ratio
            est_outer_r = box_r / ratio
            outer_radii_estimates.append(est_outer_r)
            
        if not centers:
            return None
            
        # If bullseye center is detected, it is the true target center
        if bullseye_center:
            avg_cx, avg_cy = bullseye_center
        else:
            avg_cx = sum(c[0] for c in centers) / len(centers)
            avg_cy = sum(c[1] for c in centers) / len(centers)
        
        # Average of outer radius estimates
        avg_outer_r = sum(r for r in outer_radii_estimates) / len(outer_radii_estimates)
        avg_conf = sum(confidences) / len(confidences)
        
        # Find largest bounding box to estimate aspect ratio
        max_bw, max_bh = 0.0, 0.0
        max_area = 0.0
        for i in range(len(classes)):
            bx = boxes[i]
            area = float((bx[2] - bx[0]) * (bx[3] - bx[1]))
            if area > max_area:
                max_area = area
                max_bw = float(bx[2] - bx[0])
                max_bh = float(bx[3] - bx[1])
                
        ratio_ab = (max_bw / max_bh) if max_bh > 0 else 1.0
        ratio_ab = max(0.80, min(1.25, ratio_ab))  # Clamp to reasonable perspective
        
        a_outer = avg_outer_r * math.sqrt(ratio_ab)
        b_outer = avg_outer_r / math.sqrt(ratio_ab)
        angle = 0.0
                    
        return TargetInfo(
            center_x=float(avg_cx),
            center_y=float(avg_cy),
            outer_radius=float(avg_outer_r),
            confidence=float(avg_conf),
            detected_rings=detected_rings,
            method="yolo11_rings",
            a_outer=float(a_outer),
            b_outer=float(b_outer),
            angle=float(angle),
        )
        
    def _detect_arrows_hybrid(
        self,
        boxes: np.ndarray,
        confs: np.ndarray,
        classes: np.ndarray,
        image: np.ndarray,
        pp: Dict[str, Any],
        target: TargetInfo,
    ) -> List[ArrowInfo]:
        """
        Detects arrows using YOLO bounding boxes + Local CV line refinement.
        """
        arrows = []
        h, w = image.shape[:2]
        
        model_names = getattr(self.model, "names", {})
        arrow_classes = {
            k for k, v in model_names.items()
            if "arrow" in str(v).lower()
        }
        if not arrow_classes:
            arrow_classes = {4, 0}

        for i in range(len(classes)):
            cls_id = int(classes[i])
            if cls_id not in arrow_classes:
                continue
                
            bx = boxes[i]
            conf = confs[i]
            
            # Bounding box coordinates
            x1, y1, x2, y2 = int(bx[0]), int(bx[1]), int(bx[2]), int(bx[3])
            
            # Ensure coordinates are within image bounds
            x1 = max(0, min(x1, w - 1))
            y1 = max(0, min(y1, h - 1))
            x2 = max(0, min(x2, w - 1))
            y2 = max(0, min(y2, h - 1))
            
            if x2 <= x1 or y2 <= y1:
                continue
                
            # Local refinement inside arrow bounding box
            tip = self._refine_arrow_tip_locally(image, x1, y1, x2, y2, target)
            
            if tip:
                tx, ty, angle_deg = tip
                arrows.append(ArrowInfo(
                    tip_x=float(tx),
                    tip_y=float(ty),
                    confidence=float(conf),
                    method="yolo11_hybrid",
                    shaft_angle=angle_deg,
                ))
            else:
                # BBox fallback: choose the box endpoint closest to target center
                corners = [
                    (x1, y1), (x2, y1), (x1, y2), (x2, y2),
                    ((x1+x2)/2.0, y1), ((x1+x2)/2.0, y2),
                    (x1, (y1+y2)/2.0), (x2, (y1+y2)/2.0)
                ]
                dists = [math.hypot(c[0] - target.center_x, c[1] - target.center_y) for c in corners]
                best_idx = int(np.argmin(dists))
                tx, ty = corners[best_idx]
                
                # Approximate angle from center direction
                dx = tx - target.center_x
                dy = ty - target.center_y
                angle_deg = math.degrees(math.atan2(dy, dx)) % 180
                
                arrows.append(ArrowInfo(
                    tip_x=float(tx),
                    tip_y=float(ty),
                    confidence=float(conf * 0.85),
                    method="yolo11_bbox_fallback",
                    shaft_angle=angle_deg,
                ))
                
        return arrows

    def _shaft_line_to_tip(
        self, x1: float, y1: float, x2: float, y2: float, target: TargetInfo
    ) -> Tuple[float, float, float]:
        """
        Determines the arrow tip from a shaft line (x1, y1)-(x2, y2).
        The tip is the line endpoint closest to the target center.
        """
        d1 = math.hypot(x1 - target.center_x, y1 - target.center_y)
        d2 = math.hypot(x2 - target.center_x, y2 - target.center_y)
        
        if d1 <= d2:
            tip_x, tip_y = x1, y1
        else:
            tip_x, tip_y = x2, y2
            
        angle_deg = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180
        return tip_x, tip_y, angle_deg

    def _refine_arrow_tip_locally(
        self, image: np.ndarray, x1: int, y1: int, x2: int, y2: int, target: TargetInfo
    ) -> Optional[Tuple[float, float, float]]:
        """
        Runs local line detection (HoughLinesP) and contour aspect filters inside
        the crop defined by the YOLO arrow bounding box to find the exact tip.
        """
        crop = image[y1:y2, x1:x2]
        if crop.size == 0 or crop.shape[0] < 5 or crop.shape[1] < 5:
            return None
            
        crop_gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(crop_gray)
        edges = cv2.Canny(enhanced, 30, 110)
        
        # Detect lines inside the cropped arrow box
        lines = cv2.HoughLinesP(
            edges, rho=1, theta=math.pi / 180,
            threshold=15, minLineLength=15, maxLineGap=10
        )
        
        if lines is not None and len(lines) > 0:
            # Map lines back to absolute coordinates and pick the longest line
            abs_lines = []
            for line in lines:
                lx1, ly1, lx2, ly2 = line[0]
                abs_lines.append([[lx1 + x1, ly1 + y1, lx2 + x1, ly2 + y1]])
                
            merged_lines = self.cv_fallback_service._merge_lines(
                np.array(abs_lines), dist_thresh=8.0, ang_thresh=8.0
            )
            
            if merged_lines:
                longest_line = max(
                    merged_lines, 
                    key=lambda l: math.hypot(l[2] - l[0], l[3] - l[1])
                )
                lx1, ly1, lx2, ly2 = longest_line
                return self._shaft_line_to_tip(float(lx1), float(ly1), float(lx2), float(ly2), target)
                    
        # Contour-based fallback inside crop
        cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            large_cnts = [c for c in cnts if cv2.contourArea(c) > 15]
            if large_cnts:
                largest = max(large_cnts, key=cv2.contourArea)
                if len(largest) >= 5:
                    rect = cv2.minAreaRect(largest)
                    bw, bh = rect[1]
                    if min(bw, bh) > 0:
                        aspect = max(bw, bh) / min(bw, bh)
                        if aspect > 2.0:
                            pts = largest.reshape(-1, 2).astype(float)
                            pts[:, 0] += x1
                            pts[:, 1] += y1
                            
                            [vx, vy, x0, y0] = cv2.fitLine(pts, cv2.DIST_L2, 0, 0.01, 0.01)
                            vx, vy = float(vx[0]), float(vy[0])
                            
                            proj = pts @ np.array([vx, vy])
                            p1 = tuple(pts[int(np.argmin(proj))])
                            p2 = tuple(pts[int(np.argmax(proj))])
                            
                            return self._shaft_line_to_tip(p1[0], p1[1], p2[0], p2[1], target)
                                
        return None

    def _deduplicate_arrows(self, arrows: List[ArrowInfo], target: TargetInfo) -> List[ArrowInfo]:
        """
        Deduplicates arrows using tip distance constraints.
        """
        arrows.sort(key=lambda x: x.confidence, reverse=True)
        merged: List[ArrowInfo] = []
        
        for cand in arrows:
            is_dup = False
            for existing in merged:
                dist_tips = math.hypot(cand.tip_x - existing.tip_x, cand.tip_y - existing.tip_y)
                
                # Adaptive merge threshold based on target size
                target_scale = target.outer_radius / 200.0
                tip_thresh = max(15.0, 25.0 * target_scale)
                
                if dist_tips < tip_thresh:
                    is_dup = True
                    break
            if not is_dup:
                merged.append(cand)
                
        return merged
