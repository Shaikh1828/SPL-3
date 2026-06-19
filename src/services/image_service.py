from __future__ import annotations

"""
Image processing service for arrow detection and storage management.

Implements:
- NFR Pattern #4: Image Fallback Chain — delegates to ArrowDetectionService
  (HoughCircles target + color/line/contour arrow → WA zone calculation)
- NFR Pattern #12: Image Compression (JPEG quality 70)
- NFR Pattern #9: Storage Management (90-day rotation, quota)

Story coverage: US-3.2 (arrow detection), US-5.2 (image capture and storage)
"""

import os
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import structlog

logger = structlog.get_logger()

try:
    import cv2
    import numpy as np
except ImportError:
    logger.warning("opencv_not_available")
    cv2 = None  # type: ignore
    np = None   # type: ignore

from src.config import settings
from src.events import publish_event, EventType
from src.services.arrow_detection_service import ArrowDetectionService

# Singleton detection service (stateless, reuse across calls)
_arrow_detector = ArrowDetectionService()


class ImageService:
    """Image processing and storage management service."""

    def __init__(self, thread_pool: Optional[ThreadPoolExecutor] = None):
        """
        Initialize image service.

        Args:
            thread_pool: Optional ThreadPoolExecutor for parallel processing
        """
        self.thread_pool = thread_pool
        self.storage_path = settings.storage_path
        self.jpeg_quality = settings.image_jpeg_quality
        self.image_width = settings.image_resize_width
        self.image_height = settings.image_resize_height

    def detect_arrow_in_image(
        self, image_data: bytes = None, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect arrow in image using the ArrowDetectionService pipeline.

        Implements NFR Pattern #4: Image Fallback Chain
          Primary  → HoughCircles target + multi-method arrow tip detection
          Fallback → dark-cluster scan (target found, arrow tip not found)
          Last     → assumed-center geometric fallback

        Args:
            image_data: Raw image bytes
            image_path: Path to image file (used when image_data is None)

        Returns:
            dict with keys: zone (int|None), confidence (float), method (str),
                            points (int|None), distance_ratio (float|None)
        """
        try:
            result = _arrow_detector.detect(
                image_data=image_data,
                image_path=image_path,
            )
            output = result.to_dict()
            logger.info(
                "arrow_detection_complete",
                zone=output["zone"],
                confidence=output["confidence"],
                method=output["method"],
            )
            return output
        except Exception as exc:
            logger.exception("arrow_detection_error", error=str(exc))
            return {"zone": None, "points": None, "confidence": 0.0, "method": "error"}

    def _detect_arrow_color(self, image: np.ndarray) -> Dict[str, Any]:
        """Color-based arrow detection (HSV range)."""
        try:
            # Convert BGR to HSV
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

            # Red arrow color range (HSV)
            lower_red1 = np.array([0, 100, 100])
            upper_red1 = np.array([10, 255, 255])
            lower_red2 = np.array([170, 100, 100])
            upper_red2 = np.array([180, 255, 255])

            # Create mask
            mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
            mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
            mask = cv2.bitwise_or(mask1, mask2)

            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            if len(contours) > 0:
                # Find largest contour
                largest = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest)

                # Estimate zone (simplified: map image region to zone)
                zone = self._estimate_zone_from_coordinates(x, y, image.shape)
                confidence = min(cv2.contourArea(largest) / (image.shape[0] * image.shape[1]), 1.0)

                return {"zone": zone, "confidence": confidence, "method": "color"}

            return {"zone": None, "confidence": 0.0, "method": "color"}

        except Exception as e:
            logger.warning("color_detection_error", error=str(e))
            return {"zone": None, "confidence": 0.0, "method": "color_error"}

    def _detect_arrow_edge(self, image: np.ndarray) -> Dict[str, Any]:
        """Edge-based arrow detection (Canny + contours)."""
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Canny edge detection
            edges = cv2.Canny(gray, 100, 200)

            # Find contours
            contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

            if len(contours) > 0:
                # Find largest contour
                largest = max(contours, key=cv2.contourArea)
                x, y, w, h = cv2.boundingRect(largest)

                # Estimate zone
                zone = self._estimate_zone_from_coordinates(x, y, image.shape)
                confidence = min(cv2.contourArea(largest) / (image.shape[0] * image.shape[1]), 1.0)

                return {"zone": zone, "confidence": confidence, "method": "edge"}

            return {"zone": None, "confidence": 0.0, "method": "edge"}

        except Exception as e:
            logger.warning("edge_detection_error", error=str(e))
            return {"zone": None, "confidence": 0.0, "method": "edge_error"}

    # NOTE: _detect_arrow_color, _detect_arrow_edge, and _detect_arrow_ml
    # are superseded by ArrowDetectionService (arrow_detection_service.py).
    # All detection logic is now consolidated there with:
    #   - HoughCircles target detection
    #   - Color segmentation arrow detection
    #   - HoughLinesP shaft detection
    #   - Contour aspect-ratio arrow detection
    #   - WA standard zone calculation
    # These legacy methods are kept below for backward compatibility only.

    def _estimate_zone_from_coordinates(
        self, x: int, y: int, image_shape: Tuple[int, int]
    ) -> int:
        """Estimate archery zone from image coordinates."""
        height, width = image_shape[:2]
        center_x = width / 2
        center_y = height / 2

        # Calculate distance from center
        dx = abs(x - center_x)
        dy = abs(y - center_y)
        distance = (dx ** 2 + dy ** 2) ** 0.5

        # Map distance to zone (simplified)
        max_distance = ((width / 2) ** 2 + (height / 2) ** 2) ** 0.5
        normalized_distance = distance / max_distance

        if normalized_distance < 0.1:
            zone = 10  # Bullseye
        elif normalized_distance < 0.25:
            zone = 8
        elif normalized_distance < 0.4:
            zone = 6
        elif normalized_distance < 0.6:
            zone = 4
        elif normalized_distance < 0.8:
            zone = 2
        else:
            zone = 0  # Miss

        return zone

    def preprocess_image(self, image_data: bytes) -> Optional[bytes]:
        """
        Preprocess and compress image for storage.

        Implements NFR Pattern #12: Image Compression (JPEG quality 70)

        Args:
            image_data: Raw image bytes

        Returns:
            Compressed image bytes
        """
        if not cv2:
            return image_data

        try:
            # Decode image
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

            if image is None:
                return image_data

            # Resize to standard dimensions
            resized = cv2.resize(image, (self.image_width, self.image_height))

            # Compress to JPEG
            _, compressed = cv2.imencode(
                ".jpg",
                resized,
                [cv2.IMWRITE_JPEG_QUALITY, self.jpeg_quality],
            )

            return compressed.tobytes()

        except Exception as e:
            logger.warning("image_preprocessing_error", error=str(e))
            return image_data

    def save_image(
        self, image_data: bytes, session_id: int, round: int, arrow_num: int
    ) -> str:
        """
        Save image to storage with quota enforcement.

        Implements NFR Pattern #9: Storage Management

        Args:
            image_data: Image bytes
            session_id: Session ID
            round: Round number
            arrow_num: Arrow number

        Returns:
            Image ID (UUID)

        Raises:
            OSError: If storage quota exceeded
        """
        # Preprocess and compress
        processed_data = self.preprocess_image(image_data)

        # Generate image ID
        image_id = str(uuid.uuid4())

        # Determine save path
        raw_dir = os.path.join(self.storage_path, "raw", str(session_id))
        os.makedirs(raw_dir, exist_ok=True)

        image_path = os.path.join(raw_dir, f"{image_id}.jpg")

        # Check storage quota before saving
        used_gb = self._get_storage_usage_gb()
        if used_gb + (len(processed_data) / 1024 / 1024 / 1024) > settings.storage_quota_gb:
            logger.error("storage_quota_exceeded", used_gb=used_gb, quota_gb=settings.storage_quota_gb)
            raise OSError("Storage quota exceeded")

        # Save image
        with open(image_path, "wb") as f:
            f.write(processed_data)

        logger.info(
            "image_saved",
            image_id=image_id,
            session_id=session_id,
            size_kb=len(processed_data) / 1024,
        )

        return image_id

    def _get_storage_usage_gb(self) -> float:
        """Calculate total storage usage in GB."""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(self.storage_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return total_size / 1024 / 1024 / 1024

    def archive_old_images(self, days: int = 90) -> int:
        """
        Archive images older than specified days.

        Implements NFR Pattern #9: Storage Management (90-day rotation)

        Args:
            days: Age threshold in days

        Returns:
            Number of images archived
        """
        import tarfile
        import shutil

        cutoff_date = datetime.utcnow() - timedelta(days=days)
        archived_count = 0

        raw_dir = os.path.join(self.storage_path, "raw")
        archives_dir = os.path.join(self.storage_path, "archives")
        os.makedirs(archives_dir, exist_ok=True)

        if not os.path.exists(raw_dir):
            return 0

        for session_dir in os.listdir(raw_dir):
            session_path = os.path.join(raw_dir, session_dir)
            if not os.path.isdir(session_path):
                continue

            # Check if session directory is old enough
            mtime = os.path.getmtime(session_path)
            mod_time = datetime.utcfromtimestamp(mtime)

            if mod_time < cutoff_date:
                # Archive to tar.gz
                archive_path = os.path.join(archives_dir, f"session_{session_dir}_{datetime.utcnow().isoformat()}.tar.gz")

                try:
                    with tarfile.open(archive_path, "w:gz") as tar:
                        tar.add(session_path, arcname=session_dir)

                    # Remove original
                    shutil.rmtree(session_path)
                    archived_count += 1

                    logger.info("session_archived", session_dir=session_dir, archive_path=archive_path)

                except Exception as e:
                    logger.warning("archival_error", session_dir=session_dir, error=str(e))

        # Emit archival event
        if archived_count > 0:
            publish_event(
                EventType.STORAGE_ARCHIVED,
                {"archived_count": archived_count, "cutoff_days": days},
            )

        return archived_count

    def generate_annotated_image(
        self, image_data: bytes, detection: Dict[str, Any]
    ) -> Optional[bytes]:
        """
        Draw target rings (ellipse-aware), arrow tips, and metadata onto the image.
        Uses a_outer/b_outer/angle from detection for accurate perspective-correct rings.
        Rings drawn in proper WA color (gold/red/blue/black/white).
        Arrow markers color-coded by confidence (green>=0.85, yellow>=0.60, red<0.60).
        """
        if not cv2 or not np:
            return None
        try:
            import math as _math
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                return None

            target_center = detection.get("target_center")
            target_radius  = detection.get("target_radius")
            zone           = detection.get("zone")
            confidence     = detection.get("confidence", 0.0)
            method         = detection.get("method", "unknown")
            # Ellipse axes from backend (fallback to circular if missing)
            a_outer = detection.get("a_outer") or target_radius
            b_outer = detection.get("b_outer") or target_radius
            angle   = detection.get("angle") or 0.0

            h, w = image.shape[:2]
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = max(0.45, min(w, h) / 1100.0)
            text_thick  = max(1, int(font_scale * 2))

            # ── Draw concentric elliptical rings ─────────────────────────────
            if target_center and target_radius and a_outer and b_outer:
                cx = int(target_center[0])
                cy = int(target_center[1])
                # WA boundary ratios, BGR color, label
                # Colors: Gold=(0,215,255), Red=(0,0,200), Blue=(200,100,0)
                #         Black=(50,50,50), White=(220,220,220)
                ring_specs = [
                    (0.048, (0, 215, 255), "X"),
                    (0.096, (0, 215, 255), "10"),
                    (0.192, (0, 215, 255), "9"),
                    (0.288, (30,  30, 220), "8"),
                    (0.384, (30,  30, 220), "7"),
                    (0.480, (200, 100, 10), "6"),
                    (0.576, (200, 100, 10), "5"),
                    (0.672, (55,  55,  55), "4"),
                    (0.768, (55,  55,  55), "3"),
                    (0.864, (210, 210, 210), "2"),
                    (0.960, (210, 210, 210), "1"),
                ]
                thick = max(1, int(min(a_outer, b_outer) * 0.005))
                for ratio, color, lbl in ring_specs:
                    ra = int(a_outer * ratio)
                    rb = int(b_outer * ratio)
                    if ra > 1 and rb > 1:
                        cv2.ellipse(
                            image, (cx, cy), (ra, rb),
                            angle, 0, 360, color, thick
                        )
                        # Zone label at right edge of each ellipse
                        lx = int(cx + ra * _math.cos(_math.radians(angle)) + 4)
                        ly = int(cy - rb * _math.sin(_math.radians(angle)))
                        cv2.putText(image, lbl, (lx, ly), font,
                                    font_scale * 0.55, color, 1)
                # Center dot (green)
                cv2.circle(image, (cx, cy), max(3, int(min(a_outer, b_outer) * 0.012)),
                           (0, 220, 0), -1)

            # ── Draw arrow tips ───────────────────────────────────────────────
            arrows = detection.get("arrows", [])
            if not arrows and detection.get("arrow_tip"):
                arrows = [{
                    "tip_x": detection["arrow_tip"][0],
                    "tip_y": detection["arrow_tip"][1],
                    "confidence": confidence,
                    "method": method,
                    "zone": zone,
                    "points": zone,
                }]

            for idx, arr in enumerate(arrows):
                tx, ty = int(arr["tip_x"]), int(arr["tip_y"])
                conf = arr.get("confidence", 0.0)
                arr_zone = arr.get("zone") or arr.get("points")

                # Color code by confidence
                if conf >= 0.85:
                    color = (0, 230, 0)    # Green
                elif conf >= 0.60:
                    color = (0, 215, 255)  # Yellow
                else:
                    color = (0, 0, 255)    # Red

                # Crosshair
                rad = max(5, int(w * 0.009))
                ll  = max(10, int(w * 0.017))
                cv2.circle(image, (tx, ty), rad, color, 2)
                cv2.line(image, (tx - ll, ty), (tx + ll, ty), color, 2)
                cv2.line(image, (tx, ty - ll), (tx, ty + ll), color, 2)

                # Arrow label: number + zone score
                label = f"{idx + 1}"
                if arr_zone is not None:
                    label += f"({arr_zone})"
                cv2.putText(image, label, (tx + 8, ty - 8),
                            font, font_scale * 0.72, color, text_thick)

                # Line from center to tip
                if target_center:
                    cv2.line(image,
                             (int(target_center[0]), int(target_center[1])),
                             (tx, ty), (0, 165, 255), 1)

            # ── Warning banner (low confidence) ──────────────────────────────
            low_conf_arrows = [a for a in arrows if a.get("confidence", 1.0) < 0.60]
            if low_conf_arrows or confidence < 0.60:
                banner_h = max(28, int(h * 0.04))
                cv2.rectangle(image, (0, h - banner_h), (w, h), (0, 100, 220), -1)
                cv2.putText(image, "\u26a0 Review Recommended",
                            (10, h - banner_h + max(20, banner_h - 6)),
                            font, font_scale * 0.85, (255, 255, 255), text_thick)

            # ── Score / method overlay ────────────────────────────────────────
            total_pts  = sum(a.get("points", 0) or 0 for a in arrows) if arrows else (zone or 0)
            avg_conf   = (sum(a.get("confidence", 0.0) for a in arrows) / len(arrows)) if arrows else confidence
            label_txt  = f"Total: {total_pts} pts ({len(arrows)} arrows)"
            conf_txt   = f"Avg Conf: {int(avg_conf * 100)}% ({method})"

            rect_w = max(300, int(len(conf_txt) * font_scale * 14))
            rect_h = int(85 * font_scale)
            cv2.rectangle(image, (8, 8), (8 + rect_w, 8 + rect_h), (0, 0, 0), -1)
            cv2.putText(image, label_txt,
                        (16, int(8 + 38 * font_scale)),
                        font, font_scale, (255, 255, 255), text_thick)
            cv2.putText(image, conf_txt,
                        (16, int(8 + 70 * font_scale)),
                        font, font_scale * 0.80, (180, 180, 180), max(1, text_thick - 1))

            _, compressed = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 80])
            return compressed.tobytes()
        except Exception as e:
            logger.warning("failed_to_generate_annotated_image", error=str(e))
            return None

    def save_annotated_image(
        self, image_data: bytes, session_id: int, image_id: str, detection: Dict[str, Any]
    ) -> bool:
        """
        Generate and save the annotated image.
        """
        annotated_bytes = self.generate_annotated_image(image_data, detection)
        if not annotated_bytes:
            return False
            
        annotated_dir = os.path.join(self.storage_path, "annotated", str(session_id))
        os.makedirs(annotated_dir, exist_ok=True)
        image_path = os.path.join(annotated_dir, f"{image_id}.jpg")
        
        try:
            with open(image_path, "wb") as f:
                f.write(annotated_bytes)
            logger.info("annotated_image_saved", image_id=image_id, session_id=session_id)
            return True
        except Exception as e:
            logger.error("failed_to_save_annotated_image", error=str(e))
            return False

