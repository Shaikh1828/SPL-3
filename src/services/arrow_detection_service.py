"""
Advanced Arrow Detection Service — v2.

Multi-stage computer vision pipeline for archery scoring:

Stage 1 — Preprocessing
    - Resize, bilateral denoise, CLAHE contrast enhancement
    - LAB color space for superior color separation
    - Morphological gradient for edge sharpness

Stage 2 — Target Face Detection (WA Standard 10-ring)
    Method A: HoughCircles  → finds circular rings
    Method B: Color segmentation → finds yellow bullseye, red/blue rings
    Method C: Template contours → concentric ring fitting
    Method D: Multi-ring center fitting → centroid cluster from all color bands

Stage 3 — Arrow Tip Detection (v2 — geometrically correct)
    Method A: Color segmentation → elongated shaft → LINE-ELLIPSE INTERSECTION tip
    Method B: HoughLinesP → verified shaft → LINE-ELLIPSE INTERSECTION tip
    Method C: Canny contour → aspect ratio filter → LINE-ELLIPSE INTERSECTION tip
    Method D: Puncture hole detection → dark hole centroid (highest confidence)
    Refinement: Subpixel cornerSubPix + gradient profile scan

Stage 4 — Zone Calculation (World Archery Standard Proportions)
    - Normalized distance from target center → zone 0-10
    - Confidence = √(target_conf × arrow_conf)

Stage 5 — Confidence Scoring
    - Hierarchy: puncture_hole > line_intersection > color_segment
    - Penalize fallback methods

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

# Target-face zone colors in HSV (lower, upper, label)
TARGET_COLOR_BANDS: List[Tuple[List[int], List[int], str]] = [
    ([15, 80, 130], [40, 255, 255], "yellow"),
    ([0, 120, 100], [12, 255, 255], "red_low"),
    ([168, 120, 100], [180, 255, 255], "red_high"),
    ([95, 80, 80], [135, 255, 255], "blue"),
    ([0, 0, 0], [180, 255, 55], "black"),
]

# Common arrow shaft colors in HSV
ARROW_COLOR_RANGES: List[Tuple[List[int], List[int]]] = [
    ([0, 120, 100], [12, 255, 255]),     # Red
    ([168, 120, 100], [180, 255, 255]),  # Red (wrap)
    ([95, 80, 80], [135, 255, 255]),     # Blue
    ([0, 0, 0], [180, 255, 55]),         # Black
    ([15, 80, 130], [40, 255, 255]),     # Yellow/Gold
    ([0, 0, 190], [180, 40, 255]),       # White (high brightness, low sat)
    ([50, 80, 80], [85, 255, 255]),      # Green
    ([100, 50, 50], [140, 255, 200]),    # Dark blue/navy
    ([0, 0, 60], [180, 50, 180]),        # Gray/silver
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
    a_outer: float = 0.0
    b_outer: float = 0.0
    angle: float = 0.0

    def __post_init__(self) -> None:
        if self.a_outer == 0.0:
            self.a_outer = self.outer_radius
        if self.b_outer == 0.0:
            self.b_outer = self.outer_radius


@dataclass
class ArrowInfo:
    """Detected arrow tip position."""

    tip_x: float
    tip_y: float
    confidence: float
    method: str = "unknown"
    shaft_angle: Optional[float] = None
    zone: Optional[int] = None
    points: Optional[int] = None


@dataclass
class DetectionResult:
    """Complete detection and scoring result."""

    zone: Optional[int]
    points: Optional[int]
    confidence: float
    method: str
    target: Optional[TargetInfo] = None
    arrow: Optional[ArrowInfo] = None
    distance_ratio: Optional[float] = None
    arrows: List[ArrowInfo] = field(default_factory=list)

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
            # Ellipse axes for perspective-correct ring drawing in frontend/annotated image
            "a_outer": self.target.a_outer if self.target else None,
            "b_outer": self.target.b_outer if self.target else None,
            "angle": self.target.angle if self.target else 0.0,
            "arrow_tip": (
                (self.arrow.tip_x, self.arrow.tip_y) if self.arrow else None
            ),
            "arrows": [
                {
                    "tip_x": a.tip_x,
                    "tip_y": a.tip_y,
                    "confidence": round(a.confidence, 4),
                    "method": a.method,
                    "shaft_angle": a.shaft_angle,
                    "zone": a.zone,
                    "points": a.points,
                }
                for a in (self.arrows if self.arrows else ([self.arrow] if self.arrow else []))
            ],
        }


# ─── Main Service ─────────────────────────────────────────────────────────────


class ArrowDetectionService:
    """
    Advanced multi-method arrow detection pipeline (v2).

    Key improvements over v1:
      - Line-ellipse intersection for geometrically correct tip position
      - Puncture hole detection via morphological analysis
      - Subpixel tip refinement with cornerSubPix
      - Multi-ring target center fitting
      - LAB color space preprocessing
      - Shaft-overlap based NMS deduplication

    Usage:
        service = ArrowDetectionService()
        result = service.detect(image_data=raw_bytes)
        print(result.zone, result.confidence)
    """

    def detect(
        self,
        image_data: Optional[bytes] = None,
        image_path: Optional[str] = None,
        image_array: Optional[Any] = None,
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
            arrows = self._detect_arrows(image, preprocessed, target)

            if target and arrows and target.confidence > 0.25:
                for arr in arrows:
                    norm = self._get_normalized_distance(arr.tip_x, arr.tip_y, target)
                    arr_zone = 0
                    for boundary, score in zip(WA_ZONE_BOUNDARIES, WA_ZONE_SCORES):
                        if norm <= boundary:
                            arr_zone = score
                            break
                    arr.zone = arr_zone
                    arr.points = arr_zone

                primary_arrow = arrows[0]
                result = self._calculate_zone(target, primary_arrow)
                result.target = target
                result.arrow = primary_arrow
                result.arrows = arrows
                logger.info(
                    "detection_success_multi",
                    arrow_count=len(arrows),
                    primary_zone=result.zone,
                    confidence=result.confidence,
                    method=result.method,
                )
                return result

            if target and target.confidence > 0.25:
                result = self._fallback_zone_from_target(image, preprocessed, target)
                result.target = target
                if result.arrow:
                    result.arrow.zone = result.zone
                    result.arrow.points = result.points
                    result.arrows = [result.arrow]
                logger.info(
                    "detection_target_only_fallback",
                    zone=result.zone,
                    confidence=result.confidence,
                )
                return result

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

    # ─── Stage 1: Preprocessing ────────────────────────────────────────────

    def _preprocess(self, image: Any) -> Dict[str, Any]:
        """
        Resize, denoise (bilateral), enhance contrast (CLAHE).
        Returns dict of derived image views including LAB and morphological gradient.
        """
        h, w = image.shape[:2]
        scale = 1024 / max(h, w) if max(h, w) > 1024 else 1.0
        if scale < 1.0:
            image = cv2.resize(image, (int(w * scale), int(h * scale)),
                               interpolation=cv2.INTER_AREA)

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        sat = hsv[:, :, 1]

        # Lighting assessment
        mean_bright = float(np.mean(gray))
        if mean_bright < 80:
            lighting = "DARK"
            # Gamma correction for dark images
            gamma_table = np.array([((i/255.0)**0.5)*255 for i in range(256)]).astype(np.uint8)
            image = cv2.LUT(image, gamma_table)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            sat = hsv[:, :, 1]
        elif mean_bright > 200:
            lighting = "BRIGHT"
            gamma_table = np.array([((i/255.0)**1.4)*255 for i in range(256)]).astype(np.uint8)
            image = cv2.LUT(image, gamma_table)
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
            sat = hsv[:, :, 1]
        else:
            lighting = "NORMAL"


        # Bilateral filter — edge-preserving noise reduction (better than Gaussian for shafts)
        bilateral = cv2.bilateralFilter(gray, d=9, sigmaColor=75, sigmaSpace=75)

        # Standard Gaussian blur for HoughCircles
        blurred = cv2.GaussianBlur(gray, (9, 9), 2)

        # CLAHE — adaptive contrast for variable lighting
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        enhanced_bilateral = clahe.apply(bilateral)

        # Morphological gradient — highlights object boundaries (arrow shafts become bright lines)
        morph_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        morph_grad = cv2.morphologyEx(enhanced_bilateral, cv2.MORPH_GRADIENT, morph_kernel)

        # LAB 'a' channel separates red/green strongly (helps red arrow on red ring)
        lab_a = lab[:, :, 1]
        # LAB 'b' channel separates blue/yellow (helps yellow bullseye)
        lab_b = lab[:, :, 2]

        return {
            "image": image,
            "gray": gray,
            "blurred": blurred,
            "bilateral": bilateral,
            "hsv": hsv,
            "lab": lab,
            "lab_a": lab_a,
            "lab_b": lab_b,
            "enhanced": enhanced,
            "enhanced_bilateral": enhanced_bilateral,
            "morph_grad": morph_grad,
            "sat": sat,
            "scale": scale,
            "lighting": lighting,
        }

    # ─── Stage 2: Target Detection ─────────────────────────────────────────

    def _detect_target(self, image: Any, pp: Dict) -> Optional[TargetInfo]:
        """
        Try all target-detection methods, return highest-confidence result.

        Priority order:
          1. zone_ellipses (2+ bands) — multi-zone ellipse consensus, ratio-correct
             radius extrapolation. Most accurate: each color band's outer radius
             is divided by its own true WA ratio, so the inferred outer_radius is
             geometrically correct even when arrows fragment a ring.
          2. zone_ellipses (1 band) / color_bands — single-band ratio extrapolation,
             still ratio-correct but less cross-validated.
          3. dark_ring_boundary — outside-in saturation blob. NOTE: this measures
             the boundary of the colored+black region (~77% of the true outer
             radius, not 100%), and is prone to bleeding into the wooden stand
             below the target via morphological closing. It is only trustworthy
             as a *center* cross-check, never as the radius source, so it is
             demoted to a last-resort fallback.
          4. hough / concentric — geometric fallbacks when no color signal exists.
        """
        candidates: List[TargetInfo] = []

        # PRIMARY: Multi-zone ellipse consensus (inside-out, color-based, ratio-correct)
        t = self._target_by_zone_ellipses(image, pp)
        if t:
            candidates.append(t)

        # SECONDARY: Individual color band detection (yellow bullseye)
        t = self._target_by_color_bands(image, pp)
        if t:
            candidates.append(t)

        # FALLBACK: Dark ring boundary (radius unreliable — see docstring above)
        t = self._target_by_dark_ring_boundary(pp)
        if t:
            candidates.append(t)

        # FALLBACK: Hough circles
        t = self._target_by_hough(pp)
        if t:
            candidates.append(t)

        # FALLBACK: Concentric contours
        t = self._target_by_concentric_contours(pp)
        if t:
            candidates.append(t)

        if not candidates:
            return None

        zone_results = [c for c in candidates if "zone_ellipses" in c.method]
        dark_results = [c for c in candidates if "dark_ring" in c.method]
        color_results = [c for c in candidates if c.method == "color_yellow"]

        # Prefer multi-band zone_ellipses consensus (ratio-correct radius).
        ratio_correct = [c for c in (zone_results + color_results)]
        multi_band = [c for c in zone_results if c.detected_rings >= 2]

        if multi_band:
            primary = max(multi_band, key=lambda x: x.confidence)
        elif ratio_correct:
            primary = max(ratio_correct, key=lambda x: x.confidence)
        elif dark_results:
            # Last resort: dark_ring_boundary alone. Its radius measures the
            # colored+black region (~77% of true outer radius), so rescale.
            primary = max(dark_results, key=lambda x: x.confidence)
            correction = 1.0 / 0.77
            primary = TargetInfo(
                center_x=primary.center_x, center_y=primary.center_y,
                outer_radius=primary.outer_radius * correction,
                confidence=primary.confidence * 0.7,
                detected_rings=primary.detected_rings,
                method=primary.method + "+radius_corrected",
                a_outer=primary.a_outer * correction,
                b_outer=primary.b_outer * correction,
                angle=primary.angle,
            )
        else:
            return max(candidates, key=lambda x: x.confidence)

        # Cross-check: if dark_ring_boundary independently agrees with our
        # ratio-correct center, that's strong corroboration — boost confidence
        # slightly but NEVER adopt its radius.
        if dark_results:
            dr = max(dark_results, key=lambda x: x.confidence)
            dist = math.hypot(primary.center_x - dr.center_x, primary.center_y - dr.center_y)
            if dist < primary.outer_radius * 0.12:
                primary = TargetInfo(
                    center_x=primary.center_x, center_y=primary.center_y,
                    outer_radius=primary.outer_radius,
                    confidence=min(primary.confidence * 1.06, 0.97),
                    detected_rings=primary.detected_rings,
                    method=primary.method + "+dark_confirmed",
                    a_outer=primary.a_outer, b_outer=primary.b_outer,
                    angle=primary.angle,
                )

        return primary

    def _target_by_dark_ring_boundary(self, pp: Dict) -> Optional[TargetInfo]:
        """
        PRIMARY target detection: OUTSIDE-IN approach.

        The WA target face is a colorful disc surrounded by paper/background.
        The ENTIRE colored region (yellow+red+blue+black rings) can be detected
        by finding all HIGH-SATURATION pixels — regardless of which specific
        color they are.

        This gives us the OUTER BOUNDARY of the whole target face directly,
        without any extrapolation. Much more robust than inner-ring methods.

        Algorithm:
        1. Saturation mask: sat > 35 → all target-ring pixels lit up
        2. Morphological CLOSE → merge nearby colored pixels into one blob
        3. Find largest blob → this is the target face
        4. Fit ellipse to convex hull → gives center + full outer radius
        5. Validate: circularity, size, proximity to image center
        """
        try:
            sat = pp["sat"]
            hsv = pp["hsv"]
            h, w = sat.shape[:2]
            img_cx, img_cy = w / 2.0, h / 2.0

            # Combined saturation + value mask to find all colored ring pixels
            # sat > 35 catches yellow/red/blue/black rings even in dim light
            sat_mask = cv2.inRange(sat, np.array([35]), np.array([255]))

            # Also include dark (black) areas inside target using value channel
            val = hsv[:, :, 2]
            # Target black ring: medium-low value, any saturation
            # But NOT sky or background (which tend to be uniform)
            dark_mask = cv2.inRange(val, np.array([20]), np.array([120]))
            # Only include dark pixels that are near high-saturation pixels.
            # Kernel kept small (11px, not 25px) so this doesn't bridge across
            # the gap to the wooden stand mounted directly below the target.
            sat_dilated = cv2.dilate(
                sat_mask,
                cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
            )
            dark_near_sat = cv2.bitwise_and(dark_mask, sat_dilated)

            combined = cv2.bitwise_or(sat_mask, dark_near_sat)

            # Close gaps (arrows/holes punch through color) — small kernel to
            # avoid bridging into background (stand, shadows) below the target
            k_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13))
            k_open  = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
            closed = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, k_close)
            opened = cv2.morphologyEx(closed, cv2.MORPH_OPEN, k_open)

            # Flood fill from border to remove background blobs touching edges
            # Create 1-pixel border padded copy for floodfill
            padded = cv2.copyMakeBorder(opened, 1, 1, 1, 1, cv2.BORDER_CONSTANT, value=0)
            flood = padded.copy()
            cv2.floodFill(flood, None, (0, 0), 255)
            flood = flood[1:-1, 1:-1]
            # Invert: interior blobs = white
            foreground = cv2.bitwise_not(flood)
            # Combine with opened (retain internal colored areas)
            result_mask = cv2.bitwise_or(opened, foreground)

            # Find external contours
            cnts, _ = cv2.findContours(result_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if not cnts:
                return None

            # Filter: min area 5% of image, max area 95% (avoid full-frame blobs)
            min_area = w * h * 0.05
            max_area = w * h * 0.95
            valid = [c for c in cnts
                     if min_area < cv2.contourArea(c) < max_area]
            if not valid:
                return None

            # Score: large + circular + close to image center
            best_cnt = None; best_score = -1.0
            for cnt in valid:
                area = cv2.contourArea(cnt)
                hull = cv2.convexHull(cnt)
                hull_area = cv2.contourArea(hull)
                hull_perim = cv2.arcLength(hull, True)
                if hull_perim == 0 or hull_area == 0:
                    continue
                circ = 4.0 * math.pi * hull_area / (hull_perim ** 2)
                if circ < 0.35:
                    continue  # Too irregular — not a target face
                M = cv2.moments(cnt)
                if M["m00"] == 0:
                    continue
                mcx = M["m10"] / M["m00"]; mcy = M["m01"] / M["m00"]
                prox = 1.0 - math.hypot(mcx - img_cx, mcy - img_cy) / (max(w, h) * 0.6 + 1e-9)
                prox = max(0.0, prox)
                score = circ * 0.5 + prox * 0.3 + (area / (w * h)) * 0.2
                if score > best_score:
                    best_score = score; best_cnt = hull

            if best_cnt is None or len(best_cnt) < 5:
                return None

            # Fit ellipse to the convex hull
            try:
                ellipse = cv2.fitEllipse(best_cnt)
            except cv2.error:
                return None

            (ecx, ecy), (ew, eh), eang = ellipse
            # See _fit_and_validate in _target_by_zone_ellipses: picking a=max(ew,eh)
            # without rotating eang by 90 deg when eh > ew swaps which real-world
            # axis a/b describe, rotating the drawn ellipse 90 deg from the truth.
            if ew >= eh:
                a, b = ew / 2.0, eh / 2.0
            else:
                a, b = eh / 2.0, ew / 2.0
                eang += 90.0

            # Validate ellipse size
            if a < w * 0.08 or b < h * 0.08:
                return None  # Too small
            if a > max(w, h) * 0.95:
                return None  # Too large (frame-filling background)
            if a / (b + 1e-9) > 1.8:
                return None  # Too distorted — likely bled into stand/background

            # Reject if the fitted ellipse's bounding box touches the image
            # border: the wooden stand the target sits on almost always
            # touches the bottom edge of the frame, so a target ellipse that
            # reaches the border is a strong signal of background bleed-through.
            bx, by, bw_box, bh_box = cv2.boundingRect(best_cnt)
            margin = 2
            if (bx <= margin or by <= margin
                    or bx + bw_box >= w - margin or by + bh_box >= h - margin):
                return None

            # Confidence: circularity + proximity + coverage
            M = cv2.moments(best_cnt)
            area2 = cv2.contourArea(best_cnt)
            hull_p = cv2.arcLength(best_cnt, True)
            circ2 = 4.0 * math.pi * area2 / (hull_p ** 2 + 1e-9)
            prox2 = 1.0 - math.hypot(ecx - img_cx, ecy - img_cy) / (max(w, h) * 0.6 + 1e-9)
            prox2 = max(0.0, prox2)
            conf = min(circ2 * 0.5 + prox2 * 0.3 + 0.20, 0.92)

            logger.debug("dark_ring_boundary_found",
                         cx=round(ecx), cy=round(ecy),
                         a=round(a), b=round(b), conf=round(conf, 2))

            return TargetInfo(
                center_x=float(ecx), center_y=float(ecy),
                outer_radius=float((a + b) / 2.0),
                confidence=conf, detected_rings=1,
                method="dark_ring_boundary",
                a_outer=float(a), b_outer=float(b),
                angle=float(eang % 180),
            )
        except Exception as exc:
            logger.debug("dark_ring_boundary_error", error=str(exc))
        return None

    def _target_by_zone_ellipses(self, image: Any, pp: Dict) -> Optional[TargetInfo]:
        """
        PRIMARY target detection via multi-zone ellipse consensus.
        WA zone outer-boundary ratios: yellow=19.2%, red=38.4%, blue=57.6%.
        Fit weights: blue=2.5 (least amplification), red=1.5, yellow=0.8.
        Ellipse fit handles camera perspective (circular -> elliptical).
        Cross-validates zone centers within 15pct of outer radius.
        """
        try:
            hsv = pp["hsv"]; lab_a = pp["lab_a"]; lab_b = pp["lab_b"]
            h, w = hsv.shape[:2]
            k_cl = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
            k_op = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            k_d7 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            k_d5 = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))

            ym = cv2.bitwise_or(
                cv2.inRange(hsv, np.array([13, 70, 100]), np.array([45, 255, 255])),
                cv2.inRange(lab_b, np.array([143]), np.array([255]))
            )
            rm = cv2.bitwise_and(
                cv2.bitwise_or(cv2.bitwise_or(
                    cv2.inRange(hsv, np.array([0, 90, 70]), np.array([14, 255, 255])),
                    cv2.inRange(hsv, np.array([163, 90, 70]), np.array([180, 255, 255]))),
                    cv2.inRange(lab_a, np.array([140]), np.array([255]))
                ),
                cv2.bitwise_not(cv2.dilate(ym, k_d7))
            )
            # Higher saturation threshold (90) to exclude washed-out sky blue
            bm = cv2.bitwise_and(
                cv2.inRange(hsv, np.array([85, 90, 60]), np.array([140, 255, 255])),
                cv2.bitwise_not(cv2.dilate(cv2.bitwise_or(ym, rm), k_d5))
            )
            # Black ring: low value (dark), any saturation, excluding pixels
            # already claimed by the other bands. Low-saturation + low-value
            # also matches shadows/background, so this band gets an explicit
            # border-touch rejection below (the stand/shadow signature) rather
            # than relying on color alone.
            val = hsv[:, :, 2]
            blk_m = cv2.bitwise_and(
                cv2.inRange(val, np.array([15]), np.array([110])),
                cv2.bitwise_not(cv2.dilate(cv2.bitwise_or(ym, cv2.bitwise_or(rm, bm)), k_d5))
            )

            zone_defs = [
                ("yellow", 0.192, ym,    0.8),
                ("red",    0.384, rm,    1.5),
                ("blue",   0.576, bm,    2.5),
                ("black",  0.768, blk_m, 1.8),
            ]
            fitted = []

            for zname, ratio, raw_m, fw in zone_defs:
                m = cv2.morphologyEx(raw_m, cv2.MORPH_CLOSE, k_cl)
                m = cv2.morphologyEx(m, cv2.MORPH_OPEN, k_op)
                cnts, _ = cv2.findContours(m, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not cnts:
                    continue
                vcs = [c for c in cnts if cv2.contourArea(c) > w * h * 0.005]
                if not vcs:
                    continue
                # Score blobs: prefer circular + close to image center
                # Max area cap: a single WA zone ring cannot exceed 30% of image
                # This prevents sky/grass blobs from being picked as target
                img_cx, img_cy = w / 2.0, h / 2.0
                max_zone_area = w * h * 0.30
                best_blob = None; best_blob_score = -1.0
                blob_info = []  # (cand, ca, bcx, bcy, c_circ) for every contour passing filters
                for cand in vcs:
                    ca = cv2.contourArea(cand)
                    if ca > max_zone_area:
                        continue  # Too large — not a zone ring, likely sky/background
                    ch = cv2.convexHull(cand)
                    if len(ch) < 5:
                        continue
                    cha = cv2.contourArea(ch); chp = cv2.arcLength(ch, True)
                    if chp == 0 or cha == 0:
                        continue
                    c_circ = 4.0 * math.pi * cha / (chp ** 2)
                    if c_circ < 0.20:
                        continue
                    M = cv2.moments(cand)
                    if M["m00"] == 0:
                        continue
                    bcx = M["m10"] / M["m00"]; bcy = M["m01"] / M["m00"]
                    blob_info.append((cand, ca, bcx, bcy, c_circ))
                    # Proximity to image center (0=edge, 1=exact center)
                    prox = 1.0 - math.hypot(bcx - img_cx, bcy - img_cy) / (max(w, h) * 0.7 + 1e-9)
                    prox = max(0.0, prox)
                    # Score: circularity * proximity * log(area)
                    bscore = c_circ * (0.3 + prox * 0.7) * math.log(ca + 1)
                    if bscore > best_blob_score:
                        best_blob_score = bscore; best_blob = (cand, ca, bcx, bcy, c_circ)
                if best_blob is None:
                    continue
                lg, area, lg_cx, lg_cy, circ = best_blob

                # Reject if this blob's bounding box touches the image
                # border. Only applied to the value-based "black" band: the
                # colored bands (yellow/red/blue) legitimately reach the
                # image edge in tightly-cropped photos, but a dark blob
                # touching the border is the clearest signature of the
                # value-based mask bleeding into the stand/shadow below the
                # target rather than tracing a genuine ring.
                if zname == "black":
                    bx, by, bbw, bbh = cv2.boundingRect(lg)
                    bmargin = 2
                    if (bx <= bmargin or by <= bmargin
                            or bx + bbw >= w - bmargin or by + bbh >= h - bmargin):
                        continue

                # Solo fit on just the best fragment first — this is the safe
                # baseline we fall back to if merging makes things worse.
                solo_hull = cv2.convexHull(lg)
                if len(solo_hull) < 5:
                    continue
                try:
                    solo_el = cv2.fitEllipse(solo_hull)
                except cv2.error:
                    continue
                (solo_cx, solo_cy), (solo_aw, solo_ah), solo_eang = solo_el
                solo_az = max(solo_aw, solo_ah) / 2.0

                # Arrow clusters often cut a ring into several fragments. Gather
                # any OTHER fragment whose centroid sits within ~1.5 ring-radii
                # of the best fragment's centroid (same ring, just split by
                # shafts) and fit the ellipse to their COMBINED points — this
                # keeps the fit centered even when the ring is occluded.
                # Scale the search by the SOLO fragment's own semi-axis (a
                # genuine ring-size estimate), not by sqrt(area/pi), which
                # badly underestimates a thin arc fragment's true ring radius.
                cluster_pts = [lg.reshape(-1, 2)]
                merge_radius = max(solo_az * 1.5, 30.0)
                for cand, ca, bcx, bcy, c_circ in blob_info:
                    if cand is lg:
                        continue
                    if math.hypot(bcx - lg_cx, bcy - lg_cy) < merge_radius:
                        cluster_pts.append(cand.reshape(-1, 2))

                def _fit_and_validate(pts):
                    hull = cv2.convexHull(pts)
                    if len(hull) < 5:
                        return None
                    try:
                        el = cv2.fitEllipse(hull)
                    except cv2.error:
                        return None
                    (ecx, ecy), (aw, ah), eang = el
                    # cv2.fitEllipse pairs aw with the angle's own direction and ah
                    # with the perpendicular direction. Picking az=max(aw,ah) without
                    # rotating eang by 90 deg whenever ah > aw silently swaps which
                    # real-world axis az/bz describe — the ellipse ends up rotated
                    # 90 deg from the true ring (e.g. tall instead of wide).
                    if aw >= ah:
                        az, bz, fit_ang = aw / 2.0, ah / 2.0, eang
                    else:
                        az, bz, fit_ang = ah / 2.0, aw / 2.0, eang + 90.0
                    # Cross-validated multi-band consensus fits in this dataset
                    # cluster around a 1.2-1.4 axis ratio (genuine target/camera
                    # geometry); a lone band fit at 2x+ is a fragmented/occluded
                    # blob (e.g. a ring chopped up by a cluster of arrow holes),
                    # not a real perspective ellipse.
                    if az < 8 or bz < 8 or az / bz > 1.45:
                        return None
                    af = az / ratio; bf = bz / ratio
                    if af > max(w, h) * 0.9:
                        return None
                    return ecx, ecy, az, bz, af, bf, fit_ang

                result = None
                if len(cluster_pts) > 1:
                    combined_pts = np.vstack(cluster_pts)
                    result = _fit_and_validate(combined_pts)
                    # Reject merges that blow up the fitted size far beyond the
                    # solo fragment's own estimate — sign of an unrelated blob
                    # getting pulled in rather than a true ring fragment.
                    if result is not None and result[2] > solo_az * 1.8:
                        result = None
                if result is None:
                    result = _fit_and_validate(lg)
                if result is None:
                    continue
                ecx, ecy, az, bz, af, bf, eang = result

                conf = min(circ * 0.5 + (area / (w * h)) * 3.0 + 0.25, 0.90)
                fitted.append({"cx": float(ecx), "cy": float(ecy), "af": af, "bf": bf,
                                "ang": eang % 180, "conf": conf, "name": zname, "wt": fw * conf})

            if not fitted:
                return None

            if len(fitted) >= 2:
                ma = max(f["af"] for f in fitted); tol = ma * 0.15
                bg: List[Dict] = []
                for ref in fitted:
                    g = [f for f in fitted
                         if math.hypot(f["cx"] - ref["cx"], f["cy"] - ref["cy"]) < tol]
                    if len(g) > len(bg):
                        bg = g
                cons = bg if bg else fitted
            else:
                cons = fitted

            tw = sum(f["wt"] for f in cons)
            if tw == 0:
                return None
            avg_cx = sum(f["cx"] * f["wt"] for f in cons) / tw
            avg_cy = sum(f["cy"] * f["wt"] for f in cons) / tw
            avg_a  = sum(f["af"] * f["wt"] for f in cons) / tw
            avg_b  = sum(f["bf"] * f["wt"] for f in cons) / tw
            ss = sum(math.sin(2.0 * math.radians(f["ang"])) * f["wt"] for f in cons)
            cs_v = sum(math.cos(2.0 * math.radians(f["ang"])) * f["wt"] for f in cons)
            avg_ang = (math.degrees(math.atan2(ss, cs_v)) / 2.0) % 180.0

            n = len(cons)
            ac = sum(f["conf"] for f in cons) / n
            cb = 0.0
            if n >= 2:
                avs = [f["af"] for f in cons]
                rst = (max(avs) - min(avs)) / (sum(avs) / n + 1e-9)
                cb = max(0.0, 0.10 - rst * 0.20)
            fc = min(ac + n * 0.08 + cb, 0.96)

            return TargetInfo(
                center_x=float(avg_cx), center_y=float(avg_cy),
                outer_radius=float((avg_a + avg_b) / 2.0), confidence=fc,
                detected_rings=n,
                method="zone_ellipses_" + "+".join(f["name"] for f in cons),
                a_outer=float(avg_a), b_outer=float(avg_b), angle=float(avg_ang),
            )
        except Exception as exc:
            logger.debug("zone_ellipses_error", error=str(exc))
        return None

    def _target_by_color_bands(self, image: Any, pp: Dict) -> Optional[TargetInfo]:
        """
        Find yellow bullseye (zones 9-10) then back-calculate outer-ring radius.
        WA standard: yellow zone outer is 19.2% of total target radius.
        Uses LAB b-channel for superior yellow detection.
        """
        try:
            hsv = pp["hsv"]
            lab_b = pp["lab_b"]
            h, w = hsv.shape[:2]

            # Primary: HSV yellow mask
            yellow_mask_hsv = cv2.inRange(
                hsv, np.array([15, 80, 120]), np.array([40, 255, 255])
            )

            # Secondary: LAB b-channel yellow mask (b > 148 means yellow)
            yellow_mask_lab = cv2.inRange(lab_b, np.array([148]), np.array([255]))

            # Combine both masks
            yellow_mask = cv2.bitwise_or(yellow_mask_hsv, yellow_mask_lab)

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
            yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_CLOSE, kernel)
            yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_OPEN,
                                            cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)))

            contours, _ = cv2.findContours(
                yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
            if not contours:
                return None

            best_info = None
            best_score = -1.0
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 500 or area > (h * w * 0.30):
                    continue
                hull = cv2.convexHull(cnt)
                if len(hull) < 5:
                    continue
                hull_area = cv2.contourArea(hull)
                hull_perimeter = cv2.arcLength(hull, True)
                if hull_perimeter == 0 or hull_area == 0:
                    continue
                hull_circ = 4 * math.pi * hull_area / (hull_perimeter ** 2)

                x, y, bw, bh = cv2.boundingRect(cnt)
                aspect_ratio = float(bw) / bh if bh > 0 else 0

                if 0.4 <= aspect_ratio <= 2.5:
                    ellipse = cv2.fitEllipse(hull)
                    (cx, cy), (axes_w, axes_h), angle = ellipse
                    dist_to_center = math.hypot(cx - w / 2, cy - h / 2)
                    score = (hull_circ + 0.1) * (1.0 - dist_to_center / max(w, h)) * math.log(area + 1)
                    if score > best_score:
                        best_score = score
                        best_info = (cx, cy, axes_w / 2, axes_h / 2, angle, hull_circ)

            if not best_info:
                return None

            cx, cy, a, b, angle, hull_circ = best_info
            if a < 3 or b < 3:
                return None

            a_outer = a / 0.192
            b_outer = b / 0.192
            outer_radius = (a_outer + b_outer) / 2
            confidence = min(0.55 + hull_circ * 0.4, 0.95)
            # Yellow's 19.2% outer ratio means any mask over-segmentation gets
            # amplified ~5x when extrapolated to the full target. A predicted
            # radius bigger than the photo itself is only plausible for a
            # tightly-cropped/zoomed shot, so this can be a legitimate result —
            # discount confidence rather than reject outright, so a more
            # reliable multi-band estimate (if one exists) wins instead.
            if max(a_outer, b_outer) > max(w, h) * 0.9:
                confidence *= 0.55

            return TargetInfo(
                center_x=float(cx),
                center_y=float(cy),
                outer_radius=float(outer_radius),
                confidence=confidence,
                detected_rings=1,
                method="color_yellow",
                a_outer=float(a_outer),
                b_outer=float(b_outer),
                angle=float(angle),
            )
        except Exception as exc:
            logger.debug("color_target_error", error=str(exc))
        return None

    def _target_by_hough(self, pp: Dict) -> Optional[TargetInfo]:
        """Fallback: HoughCircles on blurred grayscale."""
        try:
            blurred = pp["blurred"]
            h, w = blurred.shape
            dim = min(h, w)
            circles = cv2.HoughCircles(
                blurred, cv2.HOUGH_GRADIENT, dp=1,
                minDist=dim // 4, param1=60, param2=30,
                minRadius=dim // 12, maxRadius=dim // 2,
            )
            if circles is None:
                return None
            circles = np.round(circles[0]).astype(int)
            cx, cy, r = max(circles, key=lambda c: c[2])
            nested = sum(
                1 for c in circles
                if c[2] < r * 0.95 and math.hypot(c[0] - cx, c[1] - cy) < r * 0.15
            )
            confidence = min(0.30 + nested * 0.10 + r / dim * 0.20, 0.65)
            return TargetInfo(
                center_x=float(cx), center_y=float(cy),
                outer_radius=float(r), confidence=confidence,
                detected_rings=nested + 1, method="hough",
            )
        except Exception as exc:
            logger.debug("hough_target_error", error=str(exc))
        return None

    def _target_by_concentric_contours(self, pp: Dict) -> Optional[TargetInfo]:
        """Fallback: Find concentric contours via Canny edge analysis."""
        try:
            edges = cv2.Canny(pp["enhanced"], 40, 120)
            contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
            if not contours:
                return None
            circles = []
            for cnt in contours:
                if len(cnt) < 5 or cv2.contourArea(cnt) < 50:
                    continue
                ellipse = cv2.fitEllipse(cnt)
                cx, cy = ellipse[0]
                r = (ellipse[1][0] + ellipse[1][1]) / 4
                if r > 10:
                    circles.append((cx, cy, r))
            if len(circles) < 2:
                return None
            best_center = None; best_count = 0; best_r = 0.0
            for cx1, cy1, _ in circles:
                cluster = [c for c in circles
                           if math.hypot(c[0] - cx1, c[1] - cy1) < max(c[2] for c in circles) * 0.1]
                if len(cluster) > best_count:
                    best_count = len(cluster)
                    best_center = (cx1, cy1)
                    best_r = max(c[2] for c in cluster)
            if best_center is None or best_count < 2:
                return None
            confidence = min(0.25 + best_count * 0.08, 0.65)
            return TargetInfo(
                center_x=float(best_center[0]), center_y=float(best_center[1]),
                outer_radius=float(best_r), confidence=confidence,
                detected_rings=best_count, method="concentric_contours",
            )
        except Exception as exc:
            logger.debug("concentric_contour_error", error=str(exc))
        return None

    def _target_by_ring_fitting(self, image: Any, pp: Dict) -> Optional[TargetInfo]:
        """
        NEW: Multi-ring center fitting.
        Extracts centroid of each color band (yellow, red, blue).
        Cluster of centroids → robust target center estimate.
        """
        try:
            hsv = pp["hsv"]
            lab_b = pp["lab_b"]
            h, w = hsv.shape[:2]

            ring_masks = {
                "yellow": cv2.bitwise_or(
                    cv2.inRange(hsv, np.array([15, 80, 120]), np.array([40, 255, 255])),
                    cv2.inRange(lab_b, np.array([148]), np.array([255]))
                ),
                "red": cv2.bitwise_or(
                    cv2.inRange(hsv, np.array([0, 120, 100]), np.array([12, 255, 255])),
                    cv2.inRange(hsv, np.array([168, 120, 100]), np.array([180, 255, 255]))
                ),
                "blue": cv2.inRange(hsv, np.array([95, 80, 80]), np.array([135, 255, 255])),
            }

            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
            centroids = []
            radii = []

            for ring_name, mask in ring_masks.items():
                mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
                mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN,
                                        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5)))

                cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if not cnts:
                    continue

                # Pick largest contour for each ring color
                largest = max(cnts, key=cv2.contourArea)
                area = cv2.contourArea(largest)
                if area < 800:
                    continue

                if len(largest) >= 5:
                    try:
                        ellipse = cv2.fitEllipse(cv2.convexHull(largest))
                        cx, cy = ellipse[0]
                        r = (ellipse[1][0] + ellipse[1][1]) / 4
                        circ_score = 4 * math.pi * area / (cv2.arcLength(largest, True) ** 2 + 1e-9)
                        if circ_score > 0.4 and r > 10:
                            centroids.append((cx, cy))
                            radii.append((ring_name, r))
                    except cv2.error:
                        pass

            if len(centroids) < 2:
                return None

            # Weighted average of centroids
            avg_cx = sum(c[0] for c in centroids) / len(centroids)
            avg_cy = sum(c[1] for c in centroids) / len(centroids)

            # Check centroid spread — if too scattered, not reliable
            spread = max(math.hypot(c[0] - avg_cx, c[1] - avg_cy) for c in centroids)

            # Estimate outer radius from the largest ring detected
            radius_vals = [r for _, r in radii]
            max_ring_r = max(radius_vals) if radius_vals else 0

            # WA proportions: blue outer ≈ 48% of target radius
            # red outer ≈ 38.4%, yellow outer ≈ 19.2%
            ring_scale = {"yellow": 1.0 / 0.192, "red": 1.0 / 0.384, "blue": 1.0 / 0.480}
            est_outer_radii = []
            for ring_name, r in radii:
                if ring_name in ring_scale:
                    est_outer_radii.append(r * ring_scale[ring_name])

            outer_radius = (
                sum(est_outer_radii) / len(est_outer_radii)
                if est_outer_radii
                else max_ring_r
            )

            if outer_radius < 20:
                return None

            # Confidence based on number of rings found + centroid consistency
            spread_ratio = spread / outer_radius if outer_radius > 0 else 1.0
            confidence = min(0.5 + len(centroids) * 0.12 - spread_ratio * 0.3, 0.92)

            return TargetInfo(
                center_x=float(avg_cx),
                center_y=float(avg_cy),
                outer_radius=float(outer_radius),
                confidence=confidence,
                detected_rings=len(centroids),
                method="ring_fitting",
            )
        except Exception as exc:
            logger.debug("ring_fitting_error", error=str(exc))
        return None

    # ─── Stage 3: Arrow Detection ───────────────────────────────────────────

    def _line_ellipse_intersection(
        self,
        lx1: float, ly1: float,
        lx2: float, ly2: float,
        cx: float, cy: float,
        a: float, b: float,
        angle_deg: float,
    ) -> Optional[Tuple[float, float]]:
        """
        Find the intersection of a line segment (lx1,ly1)-(lx2,ly2) with an ellipse
        centered at (cx, cy) with semi-axes a, b and rotation angle_deg.

        Returns the intersection point CLOSEST to (lx1, ly1) — i.e., the entry
        point of the shaft into the target. This is the geometrically correct tip.

        Returns None if no valid intersection exists inside the segment.
        """
        # Rotate line endpoints into ellipse coordinate frame (angle = 0)
        rad = -math.radians(angle_deg)
        cos_a, sin_a = math.cos(rad), math.sin(rad)

        def rotate(px, py):
            dx, dy = px - cx, py - cy
            return dx * cos_a - dy * sin_a, dx * sin_a + dy * cos_a

        rx1, ry1 = rotate(lx1, ly1)
        rx2, ry2 = rotate(lx2, ly2)

        # Parametric line: P(t) = (rx1 + t*(rx2-rx1), ry1 + t*(ry2-ry1))
        dvx, dvy = rx2 - rx1, ry2 - ry1

        # Substitute into ellipse equation: (x/a)^2 + (y/b)^2 = 1
        if a <= 0 or b <= 0:
            return None

        A_coeff = (dvx / a) ** 2 + (dvy / b) ** 2
        B_coeff = 2.0 * (rx1 * dvx / a**2 + ry1 * dvy / b**2)
        C_coeff = (rx1 / a) ** 2 + (ry1 / b) ** 2 - 1.0

        discriminant = B_coeff ** 2 - 4.0 * A_coeff * C_coeff
        if discriminant < 0 or A_coeff == 0:
            return None

        sqrt_disc = math.sqrt(discriminant)
        t1 = (-B_coeff - sqrt_disc) / (2.0 * A_coeff)
        t2 = (-B_coeff + sqrt_disc) / (2.0 * A_coeff)

        # We want intersections that are on the line segment (t in [−0.1, 1.1])
        valid_ts = [t for t in [t1, t2] if -0.1 <= t <= 1.1]
        if not valid_ts:
            return None

        # The entry point (closest to lx1, ly1) = smallest t
        t_entry = min(valid_ts)
        ix_rot = rx1 + t_entry * dvx
        iy_rot = ry1 + t_entry * dvy

        # Rotate back to image space
        cos_back, sin_back = math.cos(-rad), math.sin(-rad)
        ix = ix_rot * cos_back - iy_rot * sin_back + cx
        iy = ix_rot * sin_back + iy_rot * cos_back + cy

        return (ix, iy)

    def _shaft_line_to_tip(
        self,
        x1: float, y1: float,
        x2: float, y2: float,
        target: TargetInfo,
    ) -> Optional[Tuple[float, float]]:
        """
        Given a detected shaft line segment, find the tip = point where the
        shaft enters the target face (line-ellipse intersection).

        Falls back to closest endpoint to center if no intersection found.
        """
        a_outer = target.a_outer if target.a_outer > 0 else target.outer_radius
        b_outer = target.b_outer if target.b_outer > 0 else target.outer_radius

        # Determine which endpoint is closer to center (= inside or near target)
        d1 = self._get_normalized_distance(x1, y1, target)
        d2 = self._get_normalized_distance(x2, y2, target)
        inner_pt = (x1, y1) if d1 < d2 else (x2, y2)
        outer_pt = (x2, y2) if d1 < d2 else (x1, y1)

        # Try line-ellipse intersection along the shaft line
        intersection = self._line_ellipse_intersection(
            outer_pt[0], outer_pt[1],
            inner_pt[0], inner_pt[1],
            target.center_x, target.center_y,
            a_outer, b_outer,
            target.angle,
        )

        if intersection is not None:
            # Verify intersection is near the inner endpoint (not the other side)
            ix, iy = intersection
            dist_to_inner = math.hypot(ix - inner_pt[0], iy - inner_pt[1])
            shaft_len = math.hypot(x2 - x1, y2 - y1)
            if dist_to_inner <= shaft_len * 0.6:
                return intersection

        # Fallback: use the inner endpoint
        if min(d1, d2) <= 1.0:
            return inner_pt

        return None

    def _detect_puncture_holes(
        self, pp: Dict, target: TargetInfo
    ) -> List[ArrowInfo]:
        """
        Detect RECENT arrow puncture holes via morphological analysis.

        Key design decisions to avoid old-hole false positives:
        - Requires elongated holes (aspect ratio > 2.5) — fresh arrow holes are oblong
        - Requires shaft-alignment: hole must align radially toward target center
        - Minimum area threshold tuned to fresh holes (not tiny old pinholes)
        - Returns only top N candidates sorted by confidence
        """
        try:
            gray = pp["bilateral"]
            h, w = gray.shape[:2]

            cx = int(target.center_x)
            cy = int(target.center_y)
            a_outer = int(target.a_outer if target.a_outer > 0 else target.outer_radius)
            b_outer = int(target.b_outer if target.b_outer > 0 else target.outer_radius)

            # Ellipse mask
            roi_mask = np.zeros((h, w), dtype=np.uint8)
            cv2.ellipse(roi_mask, (cx, cy), (a_outer, b_outer),
                        target.angle, 0, 360, 255, -1)

            gray_roi = cv2.bitwise_and(gray, gray, mask=roi_mask)

            # Blackhat — highlights dark features smaller than kernel
            # Use moderate kernel: arrow shaft diameter ~8-20px
            hole_kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
            blackhat = cv2.morphologyEx(gray_roi, cv2.MORPH_BLACKHAT, hole_kernel)

            # High threshold — only very dark holes pass (fresh holes are darker than old)
            otsu_thresh, thresh = cv2.threshold(blackhat, 0, 255,
                                                 cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            # Raise threshold by 20% to reject faint old holes
            _, thresh = cv2.threshold(blackhat, max(otsu_thresh * 1.2, 10), 255,
                                       cv2.THRESH_BINARY)
            thresh = cv2.bitwise_and(thresh, roi_mask)

            # Morphological cleanup — close gaps in elongated holes
            close_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            open_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, open_k)
            thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, close_k)

            num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
                thresh, connectivity=8
            )

            candidates = []
            for label in range(1, num_labels):
                area = stats[label, cv2.CC_STAT_AREA]
                comp_w = stats[label, cv2.CC_STAT_WIDTH]
                comp_h = stats[label, cv2.CC_STAT_HEIGHT]
                cen_x, cen_y = centroids[label]

                # Fresh arrow holes: 50–3000 px² (larger min to reject tiny pinholes)
                if area < 50 or area > 3000:
                    continue

                # Must be inside target
                nd = self._get_normalized_distance(cen_x, cen_y, target)
                if nd > 0.96:
                    continue

                if comp_w == 0 or comp_h == 0:
                    continue

                # Elongation: a hole made by a shaft entering at a shallow
                # trajectory angle is oblong; one entering closer to
                # perpendicular is closer to round. 2.0 (was 2.5) recovers
                # genuine near-perpendicular hits without opening the door to
                # small round noise, since area/radial-alignment still gate it.
                aspect = max(comp_w, comp_h) / max(min(comp_w, comp_h), 1)
                if aspect < 2.0:
                    continue

                # Get hole orientation and verify radial alignment
                shaft_angle = None
                radial_cos = 0.0
                try:
                    component_mask = np.zeros((h, w), dtype=np.uint8)
                    component_mask[labels == label] = 255
                    cnts, _ = cv2.findContours(component_mask, cv2.RETR_EXTERNAL,
                                                cv2.CHAIN_APPROX_SIMPLE)
                    if cnts and len(cnts[0]) >= 5:
                        rect = cv2.minAreaRect(cnts[0])
                        # minAreaRect angle: long axis direction
                        raw_angle = rect[2]
                        hole_angle_rad = math.radians(raw_angle)
                        hx, hy = math.cos(hole_angle_rad), math.sin(hole_angle_rad)

                        # Direction from hole centroid toward target center
                        dx, dy = target.center_x - cen_x, target.center_y - cen_y
                        dist_c = math.hypot(dx, dy)
                        if dist_c > 0:
                            dx, dy = dx / dist_c, dy / dist_c
                            # Radial cos: hole must point toward center
                            radial_cos = abs(hx * dx + hy * dy)

                        shaft_angle = raw_angle % 180
                except Exception:
                    pass

                # Radial alignment: hole long axis should point toward center.
                # Lowered from 0.75 — at aspect closer to 2.0 the minAreaRect
                # angle estimate is noisier even for genuine holes, so an
                # over-strict cosine here was rejecting real near-round holes.
                if radial_cos < 0.65:
                    continue

                # Confidence: large + elongated + aligned = higher confidence
                conf = min(0.60 + math.log(area) / 25.0 + (aspect - 2.5) * 0.03
                           + radial_cos * 0.10, 0.85)

                candidates.append(ArrowInfo(
                    tip_x=float(cen_x),
                    tip_y=float(cen_y),
                    confidence=conf,
                    method="puncture_hole",
                    shaft_angle=shaft_angle,
                ))

            # Sort by confidence and return top 6 max (avoid returning all old holes)
            candidates.sort(key=lambda x: x.confidence, reverse=True)
            return candidates[:6]

        except Exception as exc:
            logger.debug("puncture_hole_error", error=str(exc))
        return []

    def _detect_arrow(
        self, image: Any, pp: Dict, target: Optional[TargetInfo]
    ) -> Optional[ArrowInfo]:
        """Run all arrow-detection methods, return highest-confidence tip."""
        arrows = self._detect_arrows(image, pp, target)
        return arrows[0] if arrows else None

    def _detect_arrows(
        self, image: Any, pp: Dict, target: Optional[TargetInfo]
    ) -> List[ArrowInfo]:
        """Run all arrow-detection methods, return all detected merged tips."""
        if target is None:
            h, w = pp["enhanced"].shape[:2]
            target = TargetInfo(
                center_x=w / 2,
                center_y=h / 2,
                outer_radius=min(h, w) / 2 * 0.85,
                confidence=0.15,
                method="assumed_center",
            )

        candidates: List[ArrowInfo] = []

        # Method D: Puncture holes (highest confidence when found)
        ph_arrows = self._detect_puncture_holes(pp, target)
        candidates.extend(ph_arrows)

        # Method E: SIFT keypoints (arrow holes as distinctive features)
        sift_arrows = self._arrows_by_sift(pp, target)
        candidates.extend(sift_arrows)

        # Method A: Color segment arrows
        c_arrows = self._arrows_by_color(image, pp, target)
        candidates.extend(c_arrows)

        # Method B: Hough lines arrows
        h_arrows = self._arrows_by_hough_lines(pp, target)
        candidates.extend(h_arrows)

        # Method C: Contour aspect ratio arrows
        cnt_arrows = self._arrows_by_contour(pp, target)
        candidates.extend(cnt_arrows)

        # Multi-method confidence boost: candidates detected by 2+ methods get boosted
        # Build proximity groups and boost confidence
        if candidates:
            for i, c in enumerate(candidates):
                support = sum(
                    1 for j, o in enumerate(candidates)
                    if i != j and math.hypot(c.tip_x - o.tip_x, c.tip_y - o.tip_y) < 20
                )
                if support >= 2:
                    c.confidence = min(c.confidence + 0.12, 0.97)  # 3+ methods agree
                elif support == 1:
                    c.confidence = min(c.confidence + 0.06, 0.90)  # 2 methods agree

        if not candidates:
            return []

        # Subpixel refinement on tip positions (for non-puncture methods)
        refined = []
        for cand in candidates:
            if cand.method != "puncture_hole" and cand.shaft_angle is not None:
                rx, ry = self._refine_tip_subpixel(
                    pp["enhanced_bilateral"], cand.tip_x, cand.tip_y, cand.shaft_angle, target
                )
                nd = self._get_normalized_distance(rx, ry, target)
                if nd <= 1.02:
                    cand.tip_x = rx
                    cand.tip_y = ry
            refined.append(cand)
        candidates = refined

        # NMS: shaft-overlap based deduplication
        candidates.sort(key=lambda x: x.confidence, reverse=True)
        merged: List[ArrowInfo] = []

        for cand in candidates:
            is_dup = False
            for existing in merged:
                dist_tips = math.hypot(cand.tip_x - existing.tip_x,
                                       cand.tip_y - existing.tip_y)

                # Compute shaft-based perpendicular distance
                if existing.shaft_angle is not None:
                    rad_a = math.radians(existing.shaft_angle)
                    perp = abs(
                        (cand.tip_x - existing.tip_x) * math.sin(rad_a)
                        - (cand.tip_y - existing.tip_y) * math.cos(rad_a)
                    )
                else:
                    perp = dist_tips

                # Angular similarity
                if cand.shaft_angle is not None and existing.shaft_angle is not None:
                    ang_diff = abs(cand.shaft_angle - existing.shaft_angle)
                    ang_diff = min(ang_diff, 180 - ang_diff)
                else:
                    ang_diff = 0.0

                # Adaptive merge threshold: scale with target size
                target_scale = target.outer_radius / 200.0
                tip_thresh = max(35.0, 45.0 * target_scale)
                perp_thresh = max(18.0, 25.0 * target_scale)

                is_same = (ang_diff < 15.0 and perp < perp_thresh) or dist_tips < tip_thresh

                if is_same:
                    is_dup = True
                    # Keep tip that is more precisely inside the target
                    cand_nd = self._get_normalized_distance(cand.tip_x, cand.tip_y, target)
                    exist_nd = self._get_normalized_distance(existing.tip_x, existing.tip_y, target)

                    # Prefer puncture_hole > hough_lines > color_segment > contour
                    method_priority = {
                        "puncture_hole": 5,
                        "sift": 4,
                        "hough_lines": 3,
                        "color_segment": 2,
                        "contour_aspect": 1,
                    }
                    cand_pri = method_priority.get(cand.method, 0)
                    exist_pri = method_priority.get(existing.method, 0)

                    if cand_pri > exist_pri or (cand_pri == exist_pri and cand_nd < exist_nd):
                        existing.tip_x = cand.tip_x
                        existing.tip_y = cand.tip_y
                        existing.confidence = max(existing.confidence, cand.confidence)
                        if cand.shaft_angle is not None:
                            existing.shaft_angle = cand.shaft_angle
                        existing.method = cand.method
                    break

            if not is_dup:
                merged.append(cand)

        return merged

    # ─── Arrow Detection Methods ────────────────────────────────────────────

    def _is_local_dark_spot(
        self, gray: Any, x: float, y: float, size: float, min_contrast: int = 12,
    ) -> bool:
        """
        True if (x, y) is notably darker than the ring of pixels around it —
        the signature of an actual puncture hole. Used to reject SIFT
        keypoints that fire on printed numerals/gridlines/old marks instead
        of fresh arrow holes (those have no consistent dark-center signature).
        """
        h, w = gray.shape[:2]
        r_in = max(2, int(size / 2))
        r_out = r_in + 6
        xi, yi = int(round(x)), int(round(y))
        x0, y0 = max(0, xi - r_out), max(0, yi - r_out)
        x1, y1 = min(w, xi + r_out + 1), min(h, yi + r_out + 1)
        if x1 <= x0 or y1 <= y0:
            return False

        patch = gray[y0:y1, x0:x1]
        py, px = np.mgrid[y0:y1, x0:x1]
        dist = np.hypot(px - xi, py - yi)

        inner = patch[dist <= r_in]
        outer = patch[(dist > r_in) & (dist <= r_out)]
        if inner.size == 0 or outer.size == 0:
            return False

        return float(np.mean(outer)) - float(np.mean(inner)) >= min_contrast

    def _arrows_by_sift(self, pp: Dict, target: Optional[TargetInfo]) -> List[ArrowInfo]:
        """
        SIFT keypoint detection for arrow holes (spec §5.3 Method 2).
        Arrow holes produce distinctive high-contrast, rotationally-invariant keypoints.
        Filter: small size (3-25px), inside target boundary.
        """
        try:
            gray = pp["enhanced"]
            h, w = gray.shape[:2]
            if target is None:
                return []

            # Create target mask to restrict search
            roi_mask = np.zeros((h, w), dtype=np.uint8)
            a_r = int((target.a_outer if target.a_outer > 0 else target.outer_radius) * 0.98)
            b_r = int((target.b_outer if target.b_outer > 0 else target.outer_radius) * 0.98)
            cv2.ellipse(roi_mask, (int(target.center_x), int(target.center_y)),
                        (max(1, a_r), max(1, b_r)), target.angle, 0, 360, 255, -1)

            sift = cv2.SIFT_create(nfeatures=200, contrastThreshold=0.03, edgeThreshold=15)
            kps = sift.detect(gray, mask=roi_mask)

            arrows = []
            for kp in kps:
                x, y = kp.pt
                size = kp.size
                # Arrow holes: small distinctive keypoints (3–25px diameter)
                if size < 3 or size > 25:
                    continue
                nd = self._get_normalized_distance(x, y, target)
                if nd > 0.97:
                    continue  # outside target

                # SIFT alone fires on printed zone numerals, grid lines, and
                # old leftover pinholes just as readily as on fresh arrow
                # holes. Require the keypoint to actually sit on a dark hole
                # (darker than its surrounding ring) to reject those false
                # positives — a real puncture is darker than the paper/ink
                # around it, printed text/gridlines are not reliably so.
                if not self._is_local_dark_spot(gray, x, y, size):
                    continue

                # Higher response = more distinctive = higher confidence
                conf = min(0.40 + kp.response * 0.01, 0.62)
                arrows.append(ArrowInfo(
                    tip_x=float(x), tip_y=float(y),
                    confidence=conf, method="sift",
                ))
            return arrows
        except Exception as exc:
            logger.debug("sift_arrow_error", error=str(exc))
        return []

    def _arrows_by_color(
        self, image: Any, pp: Dict, target: Optional[TargetInfo]
    ) -> List[ArrowInfo]:
        """
        Color-segment arrow shaft → elongated contours → LINE-ELLIPSE INTERSECTION tip.
        Uses both HSV and LAB channels for better arrow/background separation.
        """
        try:
            hsv = pp["hsv"]
            lab = pp["lab"]
            h, w = hsv.shape[:2]

            # Build combined mask for all arrow colors (HSV)
            combined = np.zeros((h, w), dtype=np.uint8)
            for lower, upper in ARROW_COLOR_RANGES:
                mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
                combined = cv2.bitwise_or(combined, mask)

            # Also add high-saturation mask (arrows tend to be saturated)
            sat_mask = cv2.inRange(pp["sat"], np.array([60]), np.array([255]))
            # Combine with LAB a-channel (red arrows on red target need this)
            # High a-channel (>140) = red/magenta; low a-channel (<110) = green
            lab_a_red = cv2.inRange(pp["lab_a"], np.array([148]), np.array([255]))
            combined = cv2.bitwise_or(combined, cv2.bitwise_and(sat_mask, lab_a_red))

            # Restrict search to target region
            if target:
                roi_mask = np.zeros((h, w), dtype=np.uint8)
                a_r = int((target.a_outer if target.a_outer > 0 else target.outer_radius) * 1.08)
                b_r = int((target.b_outer if target.b_outer > 0 else target.outer_radius) * 1.08)
                cv2.ellipse(roi_mask,
                            (int(target.center_x), int(target.center_y)),
                            (a_r, b_r), target.angle, 0, 360, 255, -1)
                combined = cv2.bitwise_and(combined, roi_mask)

            # Morphological cleanup
            k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
            combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, k)
            combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, k)

            contours, _ = cv2.findContours(
                combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            arrows = []
            for cnt in contours:
                area = cv2.contourArea(cnt)
                if area < 25:
                    continue
                rect = cv2.minAreaRect(cnt)
                bw, bh = rect[1]
                if min(bw, bh) == 0:
                    continue
                aspect = max(bw, bh) / min(bw, bh)
                if aspect < 3:
                    continue

                if len(cnt) < 5:
                    continue

                [vx, vy, x0, y0] = cv2.fitLine(cnt, cv2.DIST_L2, 0, 0.01, 0.01)
                vx, vy = float(vx[0]), float(vy[0])
                x0, y0 = float(x0[0]), float(y0[0])

                # Radial check — arrow must point toward target center
                if target:
                    ux, uy = x0 - target.center_x, y0 - target.center_y
                else:
                    ux, uy = x0 - w / 2, y0 - h / 2

                dist_to_center = math.hypot(ux, uy)
                if dist_to_center > 0:
                    cos_theta = abs(vx * ux + vy * uy) / dist_to_center
                else:
                    cos_theta = 1.0

                if cos_theta < 0.93:
                    continue

                angle_deg = math.degrees(math.atan2(vy, vx)) % 180

                # Find shaft endpoints from contour bounding
                points = cnt.reshape(-1, 2).astype(float)
                # Project points onto shaft direction to find extremes
                proj = points @ np.array([vx, vy])
                p_min_idx = int(np.argmin(proj))
                p_max_idx = int(np.argmax(proj))
                shaft_p1 = tuple(points[p_min_idx])
                shaft_p2 = tuple(points[p_max_idx])

                # Use line-ellipse intersection for accurate tip
                tip = self._shaft_line_to_tip(
                    shaft_p1[0], shaft_p1[1],
                    shaft_p2[0], shaft_p2[1],
                    target
                )

                if tip is None:
                    # Fallback: closest point to center
                    center = np.array([target.center_x, target.center_y])
                    dists = np.linalg.norm(points - center, axis=1)
                    tip_pt = points[int(np.argmin(dists))]
                    tip = (tip_pt[0], tip_pt[1])

                nd = self._get_normalized_distance(tip[0], tip[1], target)
                if nd > 0.98:
                    continue

                conf = min(0.35 + aspect / 15.0, 0.75)
                arrows.append(ArrowInfo(
                    tip_x=float(tip[0]),
                    tip_y=float(tip[1]),
                    confidence=conf,
                    method="color_segment",
                    shaft_angle=angle_deg,
                ))

            return arrows
        except Exception as exc:
            logger.debug("arrow_color_error", error=str(exc))
        return []

    def _arrows_by_hough_lines(
        self, pp: Dict, target: Optional[TargetInfo]
    ) -> List[ArrowInfo]:
        """
        HoughLinesP on combined CLAHE + bilateral + morph_grad Canny edges.
        Verifies shaft continuity. Uses LINE-ELLIPSE INTERSECTION for tip.
        """
        try:
            h, w = pp["enhanced"].shape[:2]
            if target is None:
                target = TargetInfo(
                    center_x=w / 2, center_y=h / 2,
                    outer_radius=min(h, w) / 2 * 0.85,
                    confidence=0.15, method="assumed_center",
                )

            # Multi-channel edge detection for robustness
            edges_enhanced = cv2.Canny(pp["enhanced_bilateral"], 50, 180)
            edges_sat = cv2.Canny(pp["sat"], 50, 180)
            edges_grad = cv2.Canny(pp["morph_grad"], 30, 120)
            edges = cv2.bitwise_or(edges_enhanced, cv2.bitwise_or(edges_sat, edges_grad))

            # Dilate slightly to connect nearby edge fragments
            dil_k = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            edges = cv2.dilate(edges, dil_k, iterations=1)

            # Elliptical target face mask
            mask = np.zeros((h, w), dtype=np.uint8)
            a_outer = target.a_outer if target.a_outer > 0 else target.outer_radius
            b_outer = target.b_outer if target.b_outer > 0 else target.outer_radius
            cv2.ellipse(mask,
                        (int(target.center_x), int(target.center_y)),
                        (int(a_outer * 1.00), int(b_outer * 1.00)),
                        target.angle, 0, 360, 255, -1)
            edges_masked = cv2.bitwise_and(edges, mask)

            lines = cv2.HoughLinesP(
                edges_masked, rho=1, theta=math.pi / 180,
                threshold=35, minLineLength=40, maxLineGap=25,
            )

            # Merge collinear line segments
            merged_lines = self._merge_lines(lines, dist_thresh=12.0, ang_thresh=7.0)

            arrows = []
            for (x1, y1, x2, y2) in merged_lines:
                length = math.hypot(x2 - x1, y2 - y1)
                if length < 35:
                    continue

                angle_deg = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180
                if angle_deg < 3 or angle_deg > 177 or (87 < angle_deg < 93):
                    continue

                # Radial angle check in ellipse-normalized coordinates
                vx, vy = x2 - x1, y2 - y1
                x_mid, y_mid = (x1 + x2) / 2, (y1 + y2) / 2
                dx, dy = x_mid - target.center_x, y_mid - target.center_y
                rad = -math.radians(target.angle)
                rx_mid = dx * math.cos(rad) - dy * math.sin(rad)
                ry_mid = dx * math.sin(rad) + dy * math.cos(rad)

                rx1 = (x1 - target.center_x) * math.cos(rad) - (y1 - target.center_y) * math.sin(rad)
                ry1 = (x1 - target.center_x) * math.sin(rad) + (y1 - target.center_y) * math.cos(rad)
                rx2 = (x2 - target.center_x) * math.cos(rad) - (y2 - target.center_y) * math.sin(rad)
                ry2 = (x2 - target.center_x) * math.sin(rad) + (y2 - target.center_y) * math.cos(rad)

                nvx, nvy = rx2 - rx1, ry2 - ry1
                nlen = math.hypot(nvx, nvy)
                ndist = math.hypot(rx_mid, ry_mid)

                if ndist > 0 and nlen > 0:
                    cos_theta = abs(nvx * rx_mid + nvy * ry_mid) / (nlen * ndist)
                else:
                    cos_theta = 1.0

                if cos_theta < 0.90:
                    continue

                # Shaft continuity check on bilateral-filtered image (cleaner profile)
                if not self._verify_arrow_shaft_continuity(pp["enhanced_bilateral"], x1, y1, x2, y2):
                    continue

                # LINE-ELLIPSE INTERSECTION for accurate tip
                tip = self._shaft_line_to_tip(float(x1), float(y1), float(x2), float(y2), target)

                if tip is None:
                    dist1 = math.hypot(rx1 / a_outer, ry1 / b_outer)
                    dist2 = math.hypot(rx2 / a_outer, ry2 / b_outer)
                    tip = (float(x1), float(y1)) if dist1 < dist2 else (float(x2), float(y2))

                tip_nd = self._get_normalized_distance(tip[0], tip[1], target)
                if tip_nd > 0.98:
                    continue

                # Confidence: longer shaft + more central tip = higher confidence
                conf = min(0.35 + length / 300.0 + (1.0 - tip_nd) * 0.15, 0.85)
                arrows.append(ArrowInfo(
                    tip_x=float(tip[0]),
                    tip_y=float(tip[1]),
                    confidence=conf,
                    method="hough_lines",
                    shaft_angle=angle_deg,
                ))

            return arrows
        except Exception as exc:
            logger.debug("arrow_lines_error", error=str(exc))
        return []

    def _arrows_by_contour(
        self, pp: Dict, target: Optional[TargetInfo]
    ) -> List[ArrowInfo]:
        """
        Canny + morph_grad edges → elongated contours → LINE-ELLIPSE INTERSECTION tip.
        """
        try:
            h, w = pp["enhanced"].shape[:2]
            if target is None:
                target = TargetInfo(
                    center_x=w / 2, center_y=h / 2,
                    outer_radius=min(h, w) / 2 * 0.85,
                    confidence=0.15, method="assumed_center",
                )

            edges_gray = cv2.Canny(pp["enhanced_bilateral"], 25, 90)
            edges_sat = cv2.Canny(pp["sat"], 25, 90)
            edges_grad = cv2.Canny(pp["morph_grad"], 20, 80)
            edges = cv2.bitwise_or(edges_gray, cv2.bitwise_or(edges_sat, edges_grad))

            k = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
            edges = cv2.dilate(edges, k, iterations=1)

            mask = np.zeros((h, w), dtype=np.uint8)
            a_outer = target.a_outer if target.a_outer > 0 else target.outer_radius
            b_outer = target.b_outer if target.b_outer > 0 else target.outer_radius
            cv2.ellipse(mask,
                        (int(target.center_x), int(target.center_y)),
                        (int(a_outer), int(b_outer)),
                        target.angle, 0, 360, 255, -1)
            edges = cv2.bitwise_and(edges, mask)

            contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            arrows = []
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
                if aspect < 4.0 or solidity < 0.30:
                    continue

                if len(cnt) < 5:
                    continue

                [vx, vy, x0, y0] = cv2.fitLine(cnt, cv2.DIST_L2, 0, 0.01, 0.01)
                vx, vy = float(vx[0]), float(vy[0])
                x0, y0 = float(x0[0]), float(y0[0])

                angle_deg = math.degrees(math.atan2(vy, vx)) % 180
                if angle_deg < 3 or angle_deg > 177 or (87 < angle_deg < 93):
                    continue

                dx, dy = x0 - target.center_x, y0 - target.center_y
                dist_to_center = math.hypot(dx, dy)
                if dist_to_center > 0:
                    cos_theta = abs(vx * dx + vy * dy) / dist_to_center
                else:
                    cos_theta = 1.0
                if cos_theta < 0.90:
                    continue

                # Find shaft endpoints via projection
                points = cnt.reshape(-1, 2).astype(float)
                proj = points @ np.array([vx, vy])
                shaft_p1 = tuple(points[int(np.argmin(proj))])
                shaft_p2 = tuple(points[int(np.argmax(proj))])

                # Verify shaft continuity
                if not self._verify_arrow_shaft_continuity(
                    pp["enhanced_bilateral"],
                    shaft_p1[0], shaft_p1[1],
                    shaft_p2[0], shaft_p2[1]
                ):
                    continue

                # LINE-ELLIPSE INTERSECTION tip
                tip = self._shaft_line_to_tip(
                    shaft_p1[0], shaft_p1[1],
                    shaft_p2[0], shaft_p2[1],
                    target
                )

                if tip is None:
                    center = np.array([target.center_x, target.center_y])
                    dists = np.linalg.norm(points - center, axis=1)
                    tip_pt = points[int(np.argmin(dists))]
                    tip = (tip_pt[0], tip_pt[1])

                tip_nd = self._get_normalized_distance(tip[0], tip[1], target)
                if tip_nd > 0.98:
                    continue

                conf = min(0.30 + aspect * solidity / 70.0, 0.72)
                arrows.append(ArrowInfo(
                    tip_x=float(tip[0]),
                    tip_y=float(tip[1]),
                    confidence=conf,
                    method="contour_aspect",
                    shaft_angle=angle_deg,
                ))

            return arrows
        except Exception as exc:
            logger.debug("arrow_contour_error", error=str(exc))
        return []

    # ─── Tip Refinement ────────────────────────────────────────────────────

    def _refine_tip_subpixel(
        self,
        gray: Any,
        tip_x: float,
        tip_y: float,
        shaft_angle: float,
        target: TargetInfo,
        search_range: int = 18,
    ) -> Tuple[float, float]:
        """
        Subpixel tip refinement using two-stage approach:
        1. cornerSubPix for gradient-based subpixel localization
        2. Profile scan along shaft direction to find exact termination point
        """
        h, w = gray.shape[:2]

        # Stage 1: cornerSubPix — finds the exact corner/edge at subpixel level
        try:
            tip_arr = np.array([[tip_x, tip_y]], dtype=np.float32)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.01)
            refined = cv2.cornerSubPix(
                gray, tip_arr,
                winSize=(search_range, search_range),
                zeroZone=(-1, -1),
                criteria=criteria,
            )
            rx, ry = float(refined[0][0]), float(refined[0][1])

            # Only accept if refinement didn't move too far (< 20px)
            if math.hypot(rx - tip_x, ry - tip_y) < 20:
                tip_x, tip_y = rx, ry
        except Exception:
            pass

        # Stage 2: gradient profile scan along shaft direction
        rad = math.radians(shaft_angle)
        ux, uy = math.cos(rad), math.sin(rad)

        # Point towards center
        cx_dir = tip_x - target.center_x
        cy_dir = tip_y - target.center_y
        if ux * cx_dir + uy * cy_dir > 0:
            ux, uy = -ux, -uy

        # Perpendicular
        px, py = -uy, ux
        shift = 4

        start_dist = 30.0
        x_start = tip_x - start_dist * ux
        y_start = tip_y - start_dist * uy
        t_vals = np.linspace(0, start_dist + 20.0, 51)

        valley_votes, ridge_votes, valid = 0, 0, 0
        for ts in np.linspace(5.0, 25.0, 12):
            lx, ly = x_start + ts * ux, y_start + ts * uy
            lxl, lyl = lx + shift * px, ly + shift * py
            lxr, lyr = lx - shift * px, ly - shift * py
            if 0 <= lx < w and 0 <= ly < h and 0 <= lxl < w and 0 <= lyl < h and 0 <= lxr < w and 0 <= lyr < h:
                val = int(gray[int(ly), int(lx)])
                vl = int(gray[int(lyl), int(lxl)])
                vr = int(gray[int(lyr), int(lxr)])
                valid += 1
                if val < vl - 2 and val < vr - 2:
                    valley_votes += 1
                elif val > vl + 2 and val > vr + 2:
                    ridge_votes += 1

        if valid < 4:
            return tip_x, tip_y

        is_valley = valley_votes >= ridge_votes
        contrasts = []
        for t in t_vals:
            lx, ly = x_start + t * ux, y_start + t * uy
            lxl, lyl = lx + shift * px, ly + shift * py
            lxr, lyr = lx - shift * px, ly - shift * py
            if 0 <= lx < w and 0 <= ly < h and 0 <= lxl < w and 0 <= lyl < h and 0 <= lxr < w and 0 <= lyr < h:
                val = int(gray[int(ly), int(lx)])
                vl = int(gray[int(lyl), int(lxl)])
                vr = int(gray[int(lyr), int(lxr)])
                c = min(vl - val, vr - val) if is_valley else min(val - vl, val - vr)
                contrasts.append((t, c))
            else:
                contrasts.append((t, -999))

        seen_high = False
        best_t = start_dist
        thresh = 5

        for idx, (t, c) in enumerate(contrasts):
            if c >= thresh:
                seen_high = True
            if seen_high and c < thresh:
                remaining_low = all(
                    contrasts[j][1] < thresh
                    for j in range(idx, min(idx + 5, len(contrasts)))
                )
                if remaining_low:
                    best_t = t
                    break

        return x_start + best_t * ux, y_start + best_t * uy

    def _verify_arrow_shaft_continuity(
        self, gray: Any, x1: float, y1: float, x2: float, y2: float,
        shift: int = 5, contrast_thresh: int = 7, continuity_ratio: float = 0.38,
    ) -> bool:
        """
        Verify if a segment is an arrow shaft using 1D valley/ridge profile checks.
        Uses bilateral-filtered image for cleaner profile.
        """
        h, w = gray.shape[:2]
        vx, vy = x2 - x1, y2 - y1
        length = math.hypot(vx, vy)
        if length == 0:
            return False

        px, py = -vy / length, vx / length
        num_samples = int(length / 2)
        if num_samples < 5:
            return False

        t_vals = np.linspace(0.1, 0.9, num_samples)
        valley_count, ridge_count, valid_samples = 0, 0, 0

        for t in t_vals:
            lx, ly = x1 + t * vx, y1 + t * vy
            lxl, lyl = lx + shift * px, ly + shift * py
            lxr, lyr = lx - shift * px, ly - shift * py

            if 0 <= lx < w and 0 <= ly < h and 0 <= lxl < w and 0 <= lyl < h and 0 <= lxr < w and 0 <= lyr < h:
                val = int(gray[int(ly), int(lx)])
                vl = int(gray[int(lyl), int(lxl)])
                vr = int(gray[int(lyr), int(lxr)])
                valid_samples += 1
                if val < vl - contrast_thresh and val < vr - contrast_thresh:
                    valley_count += 1
                elif val > vl + contrast_thresh and val > vr + contrast_thresh:
                    ridge_count += 1

        if valid_samples < 5:
            return False

        return (valley_count / valid_samples >= continuity_ratio or
                ridge_count / valid_samples >= continuity_ratio)

    def _get_normalized_distance(self, x: float, y: float, target: TargetInfo) -> float:
        dx = x - target.center_x
        dy = y - target.center_y
        rad = -math.radians(target.angle)
        rx = dx * math.cos(rad) - dy * math.sin(rad)
        ry = dx * math.sin(rad) + dy * math.cos(rad)
        a = target.a_outer if target.a_outer > 0 else target.outer_radius
        b = target.b_outer if target.b_outer > 0 else target.outer_radius
        if a > 0 and b > 0:
            return math.hypot(rx / a, ry / b)
        return 999.0

    def _merge_lines(
        self,
        lines: Optional[Any],
        dist_thresh: float = 12.0,
        ang_thresh: float = 7.0,
    ) -> List[Tuple[int, int, int, int]]:
        """Merge collinear HoughLinesP segments into longer representative lines."""
        if lines is None or len(lines) == 0:
            return []

        line_infos = []
        for line in lines:
            x1, y1, x2, y2 = line[0]
            angle = math.degrees(math.atan2(y2 - y1, x2 - x1)) % 180
            length = math.hypot(x2 - x1, y2 - y1)
            line_infos.append((x1, y1, x2, y2, angle, length))

        used = [False] * len(line_infos)
        merged = []

        for i in range(len(line_infos)):
            if used[i]:
                continue
            used[i] = True
            curr_x1, curr_y1, curr_x2, curr_y2, curr_ang, curr_len = line_infos[i]
            group = [i]

            while True:
                added = False
                for j in range(len(line_infos)):
                    if used[j]:
                        continue
                    ang_diff = abs(line_infos[j][4] - curr_ang)
                    ang_diff = min(ang_diff, 180 - ang_diff)
                    if ang_diff > ang_thresh:
                        continue

                    x3, y3, x4, y4, _, _ = line_infos[j]
                    mid_x, mid_y = (x3 + x4) / 2, (y3 + y4) / 2

                    A = curr_y2 - curr_y1
                    B = curr_x1 - curr_x2
                    C = curr_x2 * curr_y1 - curr_x1 * curr_y2
                    denom = math.hypot(A, B)
                    dist = abs(A * mid_x + B * mid_y + C) / denom if denom > 0 else 0.0

                    if dist > dist_thresh:
                        continue

                    min_ep = min(
                        math.hypot(curr_x1 - x3, curr_y1 - y3),
                        math.hypot(curr_x1 - x4, curr_y1 - y4),
                        math.hypot(curr_x2 - x3, curr_y2 - y3),
                        math.hypot(curr_x2 - x4, curr_y2 - y4),
                    )
                    if min_ep > 120:
                        continue

                    group.append(j)
                    used[j] = True
                    added = True

                    all_pts = []
                    for idx in group:
                        all_pts.append((line_infos[idx][0], line_infos[idx][1]))
                        all_pts.append((line_infos[idx][2], line_infos[idx][3]))

                    max_d = -1.0
                    best_pair = (curr_x1, curr_y1, curr_x2, curr_y2)
                    for p1i in range(len(all_pts)):
                        for p2i in range(p1i + 1, len(all_pts)):
                            d = math.hypot(all_pts[p1i][0] - all_pts[p2i][0],
                                           all_pts[p1i][1] - all_pts[p2i][1])
                            if d > max_d:
                                max_d = d
                                best_pair = (all_pts[p1i][0], all_pts[p1i][1],
                                             all_pts[p2i][0], all_pts[p2i][1])
                    curr_x1, curr_y1, curr_x2, curr_y2 = best_pair
                    curr_ang = math.degrees(math.atan2(curr_y2 - curr_y1, curr_x2 - curr_x1)) % 180

                if not added:
                    break

            merged.append((curr_x1, curr_y1, curr_x2, curr_y2))

        return merged

    # ─── Stage 4: Zone Calculation ─────────────────────────────────────────

    def _calculate_zone(self, target: TargetInfo, arrow: ArrowInfo) -> DetectionResult:
        """Map arrow-tip distance → WA zone (0-10). Confidence = √(t_conf × a_conf)."""
        norm = self._get_normalized_distance(arrow.tip_x, arrow.tip_y, target)

        zone = 0
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
        Target found but no shaft detected.
        Scan target ROI for dark puncture marks (arrow holes).
        """
        try:
            h, w = image.shape[:2]
            cx, cy = int(target.center_x), int(target.center_y)
            r = int(target.outer_radius)

            x1, y1 = max(0, cx - r), max(0, cy - r)
            x2, y2 = min(w, cx + r), min(h, cy + r)

            if x2 <= x1 or y2 <= y1:
                raise ValueError("Invalid ROI dimensions")

            roi_gray = pp["bilateral"][y1:y2, x1:x2]

            # Blackhat to find dark holes
            hole_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (21, 21))
            blackhat = cv2.morphologyEx(roi_gray, cv2.MORPH_BLACKHAT, hole_k)

            _, thresh = cv2.threshold(blackhat, 0, 255,
                                       cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            dark_contours, _ = cv2.findContours(
                thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            if dark_contours:
                largest = max(dark_contours, key=cv2.contourArea)
                M = cv2.moments(largest)
                if M["m00"] > 0:
                    tip_x = x1 + M["m10"] / M["m00"]
                    tip_y = y1 + M["m01"] / M["m00"]
                    arrow = ArrowInfo(
                        tip_x=tip_x, tip_y=tip_y,
                        confidence=0.40, method="dark_cluster",
                    )
                    result = self._calculate_zone(target, arrow)
                    result.confidence *= 0.65
                    result.method = f"fallback_dark_cluster+{target.method}"
                    return result

        except Exception as exc:
            logger.debug("fallback_target_error", error=str(exc))

        return DetectionResult(
            zone=None, points=None, confidence=0.1, method="fallback_no_arrow",
        )

    def _pure_geometric_fallback(self, image: Any, pp: Dict) -> DetectionResult:
        """No target detected. Assume centered target, run full arrow detection."""
        try:
            h, w = image.shape[:2]
            assumed_target = TargetInfo(
                center_x=w / 2, center_y=h / 2,
                outer_radius=min(h, w) / 2 * 0.85,
                confidence=0.15, method="assumed_center",
            )
            arrows = self._detect_arrows(image, pp, assumed_target)
            if arrows:
                for arr in arrows:
                    norm = self._get_normalized_distance(arr.tip_x, arr.tip_y, assumed_target)
                    arr_zone = 0
                    for boundary, score in zip(WA_ZONE_BOUNDARIES, WA_ZONE_SCORES):
                        if norm <= boundary:
                            arr_zone = score
                            break
                    arr.zone = arr_zone
                    arr.points = arr_zone

                primary = arrows[0]
                result = self._calculate_zone(assumed_target, primary)
                result.confidence *= 0.25
                result.method = f"pure_fallback_{result.method}"
                result.target = assumed_target
                result.arrow = primary
                result.arrows = arrows
                return result
        except Exception as exc:
            logger.debug("pure_fallback_error", error=str(exc))

        return DetectionResult(
            zone=None, points=None, confidence=0.0,
            method="detection_failed_no_target_no_arrow",
        )
