from __future__ import annotations

"""
Image processing service for arrow detection and storage management.

Implements:
- NFR Pattern #4: Image Fallback Chain (color → edge → ML voting)
- NFR Pattern #12: Image Compression (JPEG quality 70)
- NFR Pattern #9: Storage Management (90-day rotation, quota)
- Arrow detection pipeline

Story coverage: US-3.2 (arrow detection), US-5.2 (image capture and storage)
"""

import os
import uuid
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor
import structlog

logger = structlog.get_logger()

try:
    import cv2
    import numpy as np
except ImportError:
    logger.warning("opencv_not_available")
    cv2 = None
    np = None

from src.config import settings
from src.events import publish_event, EventType


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
        self, image_data: bytes, image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Detect arrow in image using fallback chain.

        Implements NFR Pattern #4: Image Fallback Chain
        - Method 1: Color-based detection (HSV range)
        - Method 2: Edge-based detection (Canny + contours)
        - Method 3: ML-based detection (placeholder)

        Args:
            image_data: Raw image bytes or
            image_path: Path to image file

        Returns:
            Dictionary with zone, confidence, method used
        """
        if not cv2:
            logger.warning("opencv_not_available_using_fallback")
            return {"zone": None, "confidence": 0.0, "method": "unavailable"}

        try:
            # Load image
            if image_data:
                nparr = np.frombuffer(image_data, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            elif image_path:
                image = cv2.imread(image_path)
            else:
                return {"zone": None, "confidence": 0.0, "method": "no_input"}

            if image is None:
                logger.warning("image_decode_failed")
                return {"zone": None, "confidence": 0.0, "method": "decode_failed"}

            # Method 1: Color-based detection (Pattern #4 Step 1)
            result = self._detect_arrow_color(image)
            if result["confidence"] > 0.7:
                logger.info("arrow_detected_by_color", zone=result["zone"], confidence=result["confidence"])
                return result

            # Method 2: Edge-based detection (Pattern #4 Step 2)
            result = self._detect_arrow_edge(image)
            if result["confidence"] > 0.7:
                logger.info("arrow_detected_by_edge", zone=result["zone"], confidence=result["confidence"])
                return result

            # Method 3: ML-based detection (Pattern #4 Step 3 - placeholder)
            result = self._detect_arrow_ml(image)
            if result["confidence"] > 0.5:
                logger.info("arrow_detected_by_ml", zone=result["zone"], confidence=result["confidence"])
                return result

            # All methods failed
            logger.warning("arrow_detection_failed")
            return {"zone": None, "confidence": 0.0, "method": "failed"}

        except Exception as e:
            logger.exception("arrow_detection_error", error=str(e))
            return {"zone": None, "confidence": 0.0, "method": "error"}

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

    def _detect_arrow_ml(self, image: np.ndarray) -> Dict[str, Any]:
        """ML-based arrow detection (placeholder - would use trained model)."""
        # Placeholder for ML detection
        # In production, would use a pre-trained YOLO or custom CNN model
        logger.debug("ml_detection_placeholder")
        return {"zone": None, "confidence": 0.0, "method": "ml"}

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
