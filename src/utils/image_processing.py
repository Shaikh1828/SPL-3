"""
Image processing utilities for arrow detection and enhancement.

Pattern #4: Image Fallback Chain
Pattern #12: Image Compression
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict
from PIL import Image
import io
import structlog

logger = structlog.get_logger()

# Arrow detection color ranges (HSV)
RED_LOWER_1 = np.array([0, 50, 50])
RED_UPPER_1 = np.array([10, 255, 255])
RED_LOWER_2 = np.array([170, 50, 50])
RED_UPPER_2 = np.array([180, 255, 255])


def preprocess_image(image_bytes: bytes, max_width: int = 1024, max_height: int = 1024) -> Tuple[bool, bytes, str]:
    """
    Preprocess image: resize and compress.

    Pattern #12: Image Compression

    Args:
        image_bytes: Raw image data
        max_width: Maximum width for resize
        max_height: Maximum height for resize

    Returns:
        (success, compressed_bytes, error_msg) tuple
    """
    try:
        # Decode image
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            return False, b"", "Failed to decode image"

        # Resize
        height, width = image.shape[:2]
        if width > max_width or height > max_height:
            scale = min(max_width / width, max_height / height)
            new_width = int(width * scale)
            new_height = int(height * scale)
            image = cv2.resize(image, (new_width, new_height))

        # Compress to JPEG (quality 70 for ~20-30% latency reduction)
        success, encoded = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 70])

        if not success:
            return False, b"", "Failed to encode image"

        compressed_bytes = encoded.tobytes()
        logger.debug("image_preprocessed", original_size=len(image_bytes), compressed_size=len(compressed_bytes))

        return True, compressed_bytes, ""

    except Exception as e:
        logger.exception("preprocess_image_error", error=str(e))
        return False, b"", str(e)


def detect_arrow_color(image_bytes: bytes) -> Tuple[bool, Optional[Dict]]:
    """
    Detect arrow using color range (HSV).

    Method 1 of fallback chain (Pattern #4).

    Args:
        image_bytes: Image data

    Returns:
        (success, detection_dict) tuple with keys: zone, confidence, method
    """
    try:
        # Decode image
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            return False, None

        # Convert BGR to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)

        # Create mask for red color (two ranges for hue wrap-around)
        mask1 = cv2.inRange(hsv, RED_LOWER_1, RED_UPPER_1)
        mask2 = cv2.inRange(hsv, RED_LOWER_2, RED_UPPER_2)
        mask = cv2.bitwise_or(mask1, mask2)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return False, None

        # Get largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        total_pixels = image.shape[0] * image.shape[1]
        confidence = min(area / (total_pixels * 0.1), 1.0)  # Normalize confidence

        # Estimate zone from bounding box
        x, y, w, h = cv2.boundingRect(largest_contour)
        zone = _estimate_zone_from_coordinates(x, y, image.shape)

        logger.debug("arrow_detected_color", zone=zone, confidence=confidence)

        return True, {
            "zone": zone,
            "confidence": confidence,
            "method": "color_detection",
        }

    except Exception as e:
        logger.exception("color_detection_error", error=str(e))
        return False, None


def detect_arrow_edge(image_bytes: bytes) -> Tuple[bool, Optional[Dict]]:
    """
    Detect arrow using edge detection (Canny + contours).

    Method 2 of fallback chain (Pattern #4).

    Args:
        image_bytes: Image data

    Returns:
        (success, detection_dict) tuple with keys: zone, confidence, method
    """
    try:
        # Decode image
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            return False, None

        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Apply Canny edge detection
        edges = cv2.Canny(gray, 100, 200)

        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return False, None

        # Get largest contour
        largest_contour = max(contours, key=cv2.contourArea)
        area = cv2.contourArea(largest_contour)
        total_pixels = image.shape[0] * image.shape[1]
        confidence = min(area / (total_pixels * 0.05), 1.0)

        # Estimate zone
        x, y, w, h = cv2.boundingRect(largest_contour)
        zone = _estimate_zone_from_coordinates(x, y, image.shape)

        logger.debug("arrow_detected_edge", zone=zone, confidence=confidence)

        return True, {
            "zone": zone,
            "confidence": confidence,
            "method": "edge_detection",
        }

    except Exception as e:
        logger.exception("edge_detection_error", error=str(e))
        return False, None


def detect_arrow_ml(image_bytes: bytes) -> Tuple[bool, Optional[Dict]]:
    """
    Detect arrow using ML model (placeholder).

    Method 3 of fallback chain (Pattern #4).

    Args:
        image_bytes: Image data

    Returns:
        (success, detection_dict) tuple with keys: zone, confidence, method
    """
    # Placeholder for ML-based detection
    # In production, would load trained model and run inference
    logger.info("ml_detection_placeholder")
    return False, None


def detect_arrow(image_bytes: bytes) -> Tuple[bool, Optional[Dict], str]:
    """
    Detect arrow in image using fallback chain.

    Pattern #4: Image Fallback Chain
    Tries: Color → Edge → ML

    Args:
        image_bytes: Image data

    Returns:
        (success, detection_dict, error_msg) tuple
    """
    try:
        # Method 1: Color-based detection
        success, detection = detect_arrow_color(image_bytes)
        if success and detection and detection.get("confidence", 0) > 0.7:
            logger.debug("arrow_detected_primary_method", method="color")
            return True, detection, ""

        # Method 2: Edge-based detection
        success, detection = detect_arrow_edge(image_bytes)
        if success and detection:
            logger.debug("arrow_detected_fallback_method", method="edge")
            return True, detection, ""

        # Method 3: ML-based detection
        success, detection = detect_arrow_ml(image_bytes)
        if success and detection:
            logger.debug("arrow_detected_tertiary_method", method="ml")
            return True, detection, ""

        # All methods failed
        logger.warning("arrow_detection_failed_all_methods")
        return False, None, "No arrow detected in image"

    except Exception as e:
        logger.exception("arrow_detection_error", error=str(e))
        return False, None, str(e)


def _estimate_zone_from_coordinates(x: int, y: int, image_shape: Tuple) -> int:
    """
    Estimate target zone from arrow position.

    Maps pixel distance from center to zone (0-10).

    Args:
        x: Pixel x coordinate
        y: Pixel y coordinate
        image_shape: (height, width, channels)

    Returns:
        Zone (0-10)
    """
    height, width = image_shape[:2]
    center_x, center_y = width / 2, height / 2

    # Calculate distance from center
    distance = np.sqrt((x - center_x) ** 2 + (y - center_y) ** 2)
    max_distance = np.sqrt(center_x ** 2 + center_y ** 2)

    # Map distance to zone (0-10)
    # 0 = center, 10 = edge
    zone = int((distance / max_distance) * 10)
    zone = max(0, min(10, zone))

    return zone


def enhance_image_for_display(image_bytes: bytes) -> Tuple[bool, bytes, str]:
    """
    Enhance image for display (increase contrast, brightness).

    Args:
        image_bytes: Image data

    Returns:
        (success, enhanced_bytes, error_msg) tuple
    """
    try:
        # Decode image
        image_array = np.frombuffer(image_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

        if image is None:
            return False, b"", "Failed to decode image"

        # Convert to LAB
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a, b = cv2.split(lab)

        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        l_channel = clahe.apply(l_channel)

        # Merge back
        enhanced_lab = cv2.merge([l_channel, a, b])
        enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)

        # Encode
        success, encoded = cv2.imencode(".jpg", enhanced, [cv2.IMWRITE_JPEG_QUALITY, 85])

        if not success:
            return False, b"", "Failed to encode image"

        return True, encoded.tobytes(), ""

    except Exception as e:
        logger.exception("enhance_image_error", error=str(e))
        return False, b"", str(e)
