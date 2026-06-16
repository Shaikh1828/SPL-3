"""
Advanced Arrow Detection Service.

Multi-stage computer vision pipeline for archery scoring:

Stage 1 — Preprocessing
    - Resize, denoise, CLAHE contrast enhancement

Stage 2 — Target Face Detection (WA Standard 10-ring)
    Method A: HoughCircles  → finds circular rings
    Method B: Color segmentation → finds yellow bullseye, red/blue rings
    Method C: Template contours → concentric ring fitting

Stage 3 — Arrow Tip Detection
    Method A: Color segmentation → elongated arrow shaft contour → tip
    Method B: HoughLinesP → longest line → tip closest to target center
    Method C: Canny contour aspect-ratio filter → tip localization

Stage 4 — Zone Calculation (World Archery Standard Proportions)
    - Normalized distance from target center → zone 0-10
    - Confidence = √(target_conf × arrow_conf)

Stage 5 — Confidence Scoring
    - Penalize when fallback methods are used
    - Return zone, points, method, confidence, distance_ratio

WA 10-ring target zones (normalized radial distance):
    Zone 10 inner (X): 0   – 4.8%
    Zone 10:           4.8 – 9.6%
    Zone  9:           9.6 – 19.2%
    Zone  8:          19.2 – 28.8%
    Zone  7:          28.8 – 38.4%
    Zone  6:          38.4 – 48.0%
    Zone  5:          48.0 – 57.6%
    Zone  4:          57.6 – 67.2%
    Zone  3:          67.2 – 76.8%
    Zone  2:          76.8 – 86.4%
    Zone  1:          86.4 – 96.0%
    Miss (0):          > 96.0%

Story coverage: US-3.2 (arrow detection), US-5.2 (image capture)
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import structlog

logger = structlog.get_logger()

try:
    import cv2
    import numpy as np

    OPENCV_AVAILABLE = True
except ImportError:
    logger.warning("opencv_not_available_arrow_detection_disabled")
    OPENCV_AVAILABLE = False
    cv2 = None  # type: ignore
    np = None  # type: ignore


# ─── World Archery Constants ──────────────────────────────────────────────────

# Cumulative zone boundary ratios (fraction of outer-ring radius)
# Index → upper boundary for that zone
WA_ZONE_BOUNDARIES: List[float] = [
    0.048,  # Zone 10 inner (X ring)
    0.096,  # Zone 10 outer
    0.192,  # Zone  9
    0.288,  # Zone  8
    0.384,  # Zone  7
    0.480,  # Zone  6
    0.576,  # Zone  5
    0.672,  # Zone  4
    0.768,  # Zone  3
    0.864,  # Zone  2
    0.960,  # Zone  1
]
WA_ZONE_SCORES: List[int] = [10, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]

# Target-face zone colors in HSV (for target detection)
# Each entry: (lower_hsv, upper_hsv, zone_label)
TARGET_COLOR_BANDS: List[Tuple[List[int], List[int], str]] = [
    ([15, 80, 130], [40, 255, 255], "yellow"),     # Zones 9-10 (gold)
    ([0, 120, 100], [12, 255, 255], "red_low"),    # Zones 7-8
    ([168, 120, 100], [180, 255, 255], "red_high"), # Zones 7-8 (wrap)
    ([95, 80, 80], [135, 255, 255], "blue"),       # Zones 5-6
    ([0, 0, 0], [180, 255, 55], "black"),           # Zones 3-4
]

# Common arrow shaft colors in HSV
ARROW_COLOR_RANGES: List[Tuple[List[int], List[int]]] = [
    ([0, 120, 100], [12, 255, 255]),    # Red
    ([168, 120, 100], [180, 255, 255]), # Red (wrap)
    ([95, 80, 80], [135, 255, 255]),    # Blue
    ([0, 0, 0], [180, 255, 55]),        # Black
    ([15, 80, 130], [40, 255, 255]),    # Yellow/Gold
    ([0, 0, 190], [180, 40, 255]),      # White (high brightness, low sat)
    ([50, 80, 80], [85, 255, 255]),     # Green
]


# ─── Data Classes ─────────────────────────────────────────────────────────────


@dataclass
class TargetInfo:
    """Detected archery target face."""

    center_x: float
    center_y: float
    outer_radius: float
    confidence: float
    detected_rings: int = 0
    method: str = "unknown"


@dataclass
class ArrowInfo:
    """Detected arrow tip position."""

    tip_x: float
    tip_y: float
    confidence: float
    method: str = "unknown"
    shaft_angle: Optional[float] = None


@dataclass
class DetectionResult:
    """Complete detection and scoring result."""

    zone: Optional[int]
    points: Optional[int]
    confidence: float
    method: str
    target: Optional[TargetInfo] = None
    arrow: Optional[ArrowInfo] = None
    distance_ratio: Optional[float] = None  # Normalized [0, 1+]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "zone": self.zone,
            "points": self.points,
            "confidence": round(self.confidence, 4),
            "method": self.method,
            "distance_ratio": (
                round(self.distance_ratio, 4) if self.distance_ratio is not None else None
            ),
            "target_center": (
                (self.target.center_x, self.target.center_y) if self.target else None
            ),
            "target_radius": self.target.outer_radius if self.target else None,
            "arrow_tip": (
                (self.arrow.tip_x, self.arrow.tip_y) if self.arrow else None
            ),
        }


# ─── Main Service ─────────────────────────────────────────────────────────────


class ArrowDetectionService:
    """
    Advanced multi-method arrow detection pipeline.

    Usage:
        service = ArrowDetectionService()
        result = service.detect(image_data=raw_bytes)
        print(result.zone, result.confidence)
    """

    def detect(
        self,
        image_data: Optional[bytes] = None,
        image_path: Optional[str] = None,
        image_array: Optional[Any] = None,  # np.ndarray when available
    ) -> DetectionResult:
        """
        Main entry point. Accepts raw bytes, file path, or ndarray.

        Returns DetectionResult with zone (0-10), points, confidence (0-1),
        detection method, and optional target/arrow metadata.
        """
        if not OPENCV_AVAILABLE:
            logger.warning("opencv_unavailable_returning_null_result")
            return DetectionResult(
                zone=None, points=None, confidence=0.0, method="opencv_unavailable"
            )

        image = self._load_image(image_data, image_path, image_array)
        if image is None:
            return DetectionResult(
                zone=None, points=None, confidence=0.0, method="image_load_failed"
            )

        try:
            preprocessed = self._preprocess(image)

            target = self._detect_target(image, preprocessed)
            arrow = self._detect_arrow(image, preprocessed, target)

            if target and arrow and target.confidence > 0.25:
                result = self._calculate_zone(target, arrow)
                result.target = target
                result.arrow = arrow
                logger.info(
                    "detection_success",
                    zone=result.zone,
                    confidence=result.confidence,
                    method=result.method,
                )
                return result

            if target and target.confidence > 0.25:
                result = self._fallback_zone_from_target(image, preprocessed, target)
                result.target = target
                logger.info(
                    "detection_target_only_fallback",
                    zone=result.zone,
                    confidence=result.confidence,
                )
                return result

            # No reliable target — pure geometric fallback
            return self._pure_geometric_fallback(image, preprocessed)

        except Exception as exc:
            logger.exception("arrow_detection_critical_error", error=str(exc))
            return DetectionResult(
                zone=None, points=None, confidence=0.0, method="internal_error"
            )

    # ─── Image Loading ─────────────────────────────────────────────────────

    def _load_image(self, image_data, image_path, image_array) -> Optional[Any]:
        try:
            if image_array is not None:
                return image_array
            if image_data:
                nparr = np.frombuffer(image_data, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    logger.warning("imdecode_returned_none")
                return img
            if image_path:
                img = cv2.imread(image_path)
                if img is None:
                    logger.warning("imread_returned_none", path=image_path)
                return img
        except Exception as exc:
            logger.warning("image_load_error", error=str(exc))
        return None

    # ─── Preprocessing ─────────────────────────────────────────────────────

    def _preprocess(self, image: Any) -> Dict[str, Any]:
        """Resize, denoise, enhance contrast — returns dict of derived views."""
        # Limit long edge to 1024 px for speed
        h, w = image.shape[:2]
        scale = 1024 / max(h, w) if max(h, w) > 1024 else 1.0
        if scale < 1.0:
            image = cv2.resize(image, (int(w * scale), int(h * scale)))

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # CLAHE — adaptive contrast for variable lighting
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        return {
            "image": image,
            "gray": gray,
            "blurred": blurred,
            "hsv": hsv,
            "enhanced": enhanced,
        }

    # ─── Stage 2: Target Detection ─────────────────────────────────────────

    def _detect_target(self, image: Any, pp: Dict) -> Optional[TargetInfo]:
        """Try all target-detection methods, return highest-confidence result."""
        candidates: List[TargetInfo] = []

        t = self._target_by_hough(pp)
        if t:
            candidates.append(t)

        t = self._target_by_color_bands(image, pp)
        if t:
            candidates.append(t)

        t = self._target_by_concentric_contours(pp)
        if t:
            candidates.append(t)

        if not candidates:
            return None
        return max(candidates, key=lambda x: x.confidence)

    def _target_by_hough(self, pp: Dict) -> Optional[TargetInfo]:
        """HoughCircles on blurred grayscale to find the outer ring."""
        try:
            blurred = pp["blurred"]
            h, w = blurred.shape
            dim = min(h, w)

            circles = cv2.HoughCircles(
                blurred,
                cv2.HOUGH_GRADIENT,
                dp=1,
                minDist=dim // 4,
                param1=60,
                param2=30,
                minRadius=dim // 12,
                maxRadius=dim // 2,
            )

            if circles is None:
                return None

            circles = np.round(circles[0]).astype(int)
            # Pick largest (most likely the target face)
            cx, cy, r = max(circles, key=lambda c: c[2])

            # Count how many circles nest inside (indicates genuine target)
            nested = sum(
                1
                for c in circles
                if c[2] < r * 0.95
                and math.hypot(c[0] - cx, c[1] - cy) < r * 0.15
            )
            confidence = min(0.4 + nested * 0.15 + r / dim * 0.3, 0.95)

            return TargetInfo(
                center_x=float(cx),
                center_y=float(cy),
                outer_radius=float(r),
                confidence=confidence,
                detected_rings=nested + 1,
                method="hough",
            )
        except Exception as exc:
            logger.debug("hough_target_error", error=str(exc))
        return None

    def _target_by_color_bands(self, image: Any, pp: Dict) -> Optional[TargetInfo]:
        """
        Find yellow bullseye (zones 9-10) then back-calculate outer-ring radius.
        WA standard: bullseye outer = 9.6% of total target radius.
        """
        try:
            hsv = pp["hsv"]
            h, w = hsv.shape[:2]

            yellow_mask = cv2.inRange(
                hsv, np.array([15, 80, 130]), np.array([40, 255, 255])
            )
            # Morphological cleanup
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_CLOSE, kernel)

            contours, _ = cv2.findContours(
                yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if not contours:
                return None

            largest = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest)
            if area < 50:
                return None

            (cx, cy), bullseye_r = cv2.minEnclosingCircle(largest)
            if bullseye_r < 3:
                return None

            # Zone 10 outer boundary = 9.6% of target radius
            outer_radius = bullseye_r / 0.096
            coverage = area / (h * w)
            confidence = min(0.5 + coverage * 200, 0.90)

            return TargetInfo(
                center_x=float(cx),
                center_y=float(cy),
                outer_radius=float(outer_radius),
                confidence=confidence,
                detected_rings=1,
                method="color_yellow",
            )
        except Exception as exc:
            logger.debug("color_target_error", error=str(exc))
        return None

    def _target_by_concentric_contours(self, pp: Dict) -> Optional[TargetInfo]:
        """
        Find concentric circular contours (Canny + hierarchy analysis).
        Multiple circles sharing a common center → target face.
        """
        try:
            edges = cv2.Canny(pp["enhanced"], 40, 120)
            contours, hierarchy = cv2.findContours(
                edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
            )
            if not contours or hierarchy is None:
                return None

            # Collect circles from ellipse-fit contours
            circles: List[Tuple[float, float, float]] = []  # (cx, cy, radius)
            for cnt in contours:
                if len(cnt) < 5 or cv2.contourArea(cnt) < 50:
                    continue
                ellipse = cv2.fitEllipse(cnt)
                cx, cy = ellipse[0]
                axes = ellipse[1]
                r = (axes[0] + axes[1]) / 4
                if r > 10:
                    circles.append((cx, cy, r))

            if len(circles) < 2:
                return None

            # Find the densest cluster by center proximity
            best_center = None
            best_count = 0
            best_max_r = 0.0

            for i, (cx1, cy1, _) in enumerate(circles):
                cluster = [
                    c
                    for c in circles
                    if math.hypot(c[0] - cx1, c[1] - cy1)
                    < max(c[2] for c in circles) * 0.1
                ]
                if len(cluster) > best_count:
                    best_count = len(cluster)
                    best_center = (cx1, cy1)
                    best_max_r = max(c[2] for c in cluster)

            if best_center is None or best_count < 2:
                return None

            confidence = min(0.35 + best_count * 0.12, 0.85)
            return TargetInfo(
                center_x=float(best_center[0]),
                center_y=float(best_center[1]),
                outer_radius=float(best_max_r),
                confidence=confidence,
                detected_rings=best_count,
                method="concentric_contours",
            )
        except Exception as exc:
            logger.debug("concentric_contour_error", error=str(exc))
        return None

    # ─── Stage 3: Arrow Detection ───────────────────────────────────────────

    def _detect_arrow(
        self, image: Any, pp: Dict, target: Optional[TargetInfo]
    ) -> Optional[ArrowInfo]:
        """Run all arrow-detection methods, return highest-confidence tip."""
        candidates: List[ArrowInfo] = []

        a = self._arrow_by_color(image, pp, target)
        if a:
            candidates.append(a)

        a = self._arrow_by_hough_lines(pp, target)
        if a:
            candidates.append(a)

        a = self._arrow_by_contour(pp, target)
        if a:
            candidates.append(a)

        if not candidates:
            return None
        return max(candidates, key=lambda x: x.confidence)

    def _arrow_by_color(
        self, image: Any, pp: Dict, target: Optional[TargetInfo]
    ) -> Optional[ArrowInfo]:
        """
        Color-segment arrow shaft → find elongated contour → locate tip.
        Tip = shaft endpoint closest to target center.
        """
        try:
            hsv = pp["hsv"]
            h, w = hsv.shape[:2]

            # Build combined mask for all arrow colors
            combined = np.zeros((h, w), dtype=np.uint8)
            for lower, upper in ARROW_COLOR_RANGES:
                mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
                combined = cv2.bitwise_or(combined, mask)

            # Restrict search to target region (±10%)
            if target:
                roi_mask = np.zeros((h, w), dtype=np.uint8)
                cv2.circle(
                    roi_mask,
                    (int(target.center_x), int(target.center_y)),
                    int(target.outer_radius * 1.1),
                    255,
                    -1,
                )
                combined = cv2.bitwise_and(combined, roi_mask)

            # Morphological cleanup
            k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, k)
            combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, k)

            contours, _ = cv2.findContours(
                combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            best: Optional[ArrowInfo] = None
            best_conf = 0.0

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 30:
                    continue
                rect = cv2.minAreaRect(cnt)
                bw, bh = rect[1]
                if min(bw, bh) == 0:
                    continue
                aspect = max(bw, bh) / min(bw, bh)
                if aspect < 3:
                    continue  # Not elongated enough for an arrow shaft

                points = cnt.reshape(-1, 2)
                if target:
                    center = np.array([target.center_x, target.center_y])
                    dists = np.linalg.norm(points.astype(float) - center, axis=1)
                    tip = points[int(np.argmin(dists))]
                else:
                    # Lowest point heuristic
                    tip = points[int(np.argmax(points[:, 1]))]

                conf = min(aspect / 12.0, 0.85)
                if conf > best_conf:
                    best_conf = conf
                    best = ArrowInfo(
                        tip_x=float(tip[0]),
                        tip_y=float(tip[1]),
                        confidence=conf,
                        method="color_segment",
                    )

            return best
        except Exception as exc:
            logger.debug("arrow_color_error", error=str(exc))
        return None

    def _arrow_by_hough_lines(
        self, pp: Dict, target: Optional[TargetInfo]
    ) -> Optional[ArrowInfo]:
        """
        HoughLinesP on Canny edges → longest line = arrow shaft.
        Tip = endpoint closer to target center.
        """
        try:
            edges = cv2.Canny(pp["enhanced"], 50, 150)
            lines = cv2.HoughLinesP(
                edges,
                rho=1,
                theta=math.pi / 180,
                threshold=40,
                minLineLength=25,
                maxLineGap=8,
            )
            if lines is None:
                return None

            best_line = max(
                lines,
                key=lambda l: math.hypot(l[0][2] - l[0][0], l[0][3] - l[0][1]),
            )
            x1, y1, x2, y2 = best_line[0]
            length = math.hypot(x2 - x1, y2 - y1)

            if target:
                d1 = math.hypot(x1 - target.center_x, y1 - target.center_y)
                d2 = math.hypot(x2 - target.center_x, y2 - target.center_y)
                tip = (x1, y1) if d1 < d2 else (x2, y2)
            else:
                tip = (int((x1 + x2) / 2), int((y1 + y2) / 2))

            angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
            conf = min(length / 250.0, 0.75)

            return ArrowInfo(
                tip_x=float(tip[0]),
                tip_y=float(tip[1]),
                confidence=conf,
                method="hough_lines",
                shaft_angle=angle,
            )
        except Exception as exc:
            logger.debug("arrow_lines_error", error=str(exc))
        return None

    def _arrow_by_contour(
        self, pp: Dict, target: Optional[TargetInfo]
    ) -> Optional[ArrowInfo]:
        """
        Canny + RETR_EXTERNAL → pick contour with max aspect × solidity.
        Tip = point on contour closest to target center.
        """
        try:
            edges = cv2.Canny(pp["enhanced"], 30, 100)
            k = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            edges = cv2.dilate(edges, k, iterations=1)

            contours, _ = cv2.findContours(
                edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if not contours:
                return None

            best_cnt = None
            best_score = 0.0

            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 25:
                    continue
                hull = cv2.convexHull(cnt)
                hull_area = cv2.contourArea(hull)
                if hull_area == 0:
                    continue
                solidity = area / hull_area
                rect = cv2.minAreaRect(cnt)
                bw, bh = rect[1]
                if min(bw, bh) == 0:
                    continue
                aspect = max(bw, bh) / min(bw, bh)
                score = aspect * solidity if aspect > 4 else 0
                if score > best_score:
                    best_score = score
                    best_cnt = cnt

            if best_cnt is None:
                return None

            points = best_cnt.reshape(-1, 2)
            if target:
                center = np.array([target.center_x, target.center_y])
                dists = np.linalg.norm(points.astype(float) - center, axis=1)
                tip = points[int(np.argmin(dists))]
            else:
                tip = points[int(np.argmax(points[:, 1]))]

            conf = min(best_score / 60.0, 0.70)
            return ArrowInfo(
                tip_x=float(tip[0]),
                tip_y=float(tip[1]),
                confidence=conf,
                method="contour_aspect",
            )
        except Exception as exc:
            logger.debug("arrow_contour_error", error=str(exc))
        return None

    # ─── Stage 4: Zone Calculation ─────────────────────────────────────────

    def _calculate_zone(
        self, target: TargetInfo, arrow: ArrowInfo
    ) -> DetectionResult:
        """
        Map arrow-tip distance from target center → WA zone (0-10).
        Combined confidence = √(target_conf × arrow_conf).
        """
        dist = math.hypot(
            arrow.tip_x - target.center_x, arrow.tip_y - target.center_y
        )
        norm = dist / target.outer_radius  # Normalized [0, 1+]

        zone = 0  # Default = miss
        for boundary, score in zip(WA_ZONE_BOUNDARIES, WA_ZONE_SCORES):
            if norm <= boundary:
                zone = score
                break

        conf = math.sqrt(target.confidence * arrow.confidence)
        method = f"geometric_{target.method}+{arrow.method}"

        return DetectionResult(
            zone=zone,
            points=zone,
            confidence=round(conf, 4),
            method=method,
            distance_ratio=round(norm, 4),
        )

    # ─── Fallback Methods ──────────────────────────────────────────────────

    def _fallback_zone_from_target(
        self, image: Any, pp: Dict, target: TargetInfo
    ) -> DetectionResult:
        """
        Target found but arrow tip not detected.
        Scan the target ROI for the darkest pixel cluster (arrow puncture).
        """
        try:
            h, w = image.shape[:2]
            cx = int(target.center_x)
            cy = int(target.center_y)
            r = int(target.outer_radius)

            x1, y1 = max(0, cx - r), max(0, cy - r)
            x2, y2 = min(w, cx + r), min(h, cy + r)

            if x2 <= x1 or y2 <= y1:
                raise ValueError("Invalid ROI dimensions")

            roi_gray = pp["gray"][y1:y2, x1:x2]

            # Bilateral filter to reduce noise while preserving edges
            roi_smooth = cv2.bilateralFilter(roi_gray, 9, 75, 75)

            # Find darkest point cluster (arrow creates dark mark)
            _, thresh = cv2.threshold(
                roi_smooth, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
            )
            dark_contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if dark_contours:
                # Largest dark cluster = most likely arrow puncture
                largest = max(dark_contours, key=cv2.contourArea)
                M = cv2.moments(largest)
                if M["m00"] > 0:
                    tip_x = x1 + M["m10"] / M["m00"]
                    tip_y = y1 + M["m01"] / M["m00"]
                    arrow = ArrowInfo(
                        tip_x=tip_x,
                        tip_y=tip_y,
                        confidence=0.35,
                        method="dark_cluster",
                    )
                    result = self._calculate_zone(target, arrow)
                    result.confidence *= 0.6  # Penalize fallback
                    result.method = f"fallback_dark_cluster+{target.method}"
                    return result

        except Exception as exc:
            logger.debug("fallback_target_error", error=str(exc))

        # Worst-case: unknown zone
        return DetectionResult(
            zone=None,
            points=None,
            confidence=0.1,
            method="fallback_no_arrow",
        )

    def _pure_geometric_fallback(self, image: Any, pp: Dict) -> DetectionResult:
        """
        No target detected.
        Assume target is centered; run full arrow detection on center-assumed target.
        """
        try:
            h, w = image.shape[:2]
            assumed_target = TargetInfo(
                center_x=w / 2,
                center_y=h / 2,
                outer_radius=min(h, w) / 2 * 0.85,
                confidence=0.15,
                method="assumed_center",
            )
            arrow = self._detect_arrow(image, pp, assumed_target)
            if arrow:
                result = self._calculate_zone(assumed_target, arrow)
                result.confidence *= 0.25  # Heavy penalty
                result.method = f"pure_fallback_{result.method}"
                return result
        except Exception as exc:
            logger.debug("pure_fallback_error", error=str(exc))

        return DetectionResult(
            zone=None,
            points=None,
            confidence=0.0,
            method="detection_failed_no_target_no_arrow",
        )
