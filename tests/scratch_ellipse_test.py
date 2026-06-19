import os
import math
import cv2
import numpy as np

class TargetInfo:
    def __init__(self, center_x, center_y, a_outer, b_outer, angle, confidence):
        self.center_x = center_x
        self.center_y = center_y
        self.a_outer = a_outer
        self.b_outer = b_outer
        self.angle = angle
        self.confidence = confidence

class ArrowInfo:
    def __init__(self, tip_x, tip_y, confidence, method="unknown"):
        self.tip_x = tip_x
        self.tip_y = tip_y
        self.confidence = confidence
        self.method = method

def detect_target_ellipse(hsv, enhanced):
    h, w = hsv.shape[:2]
    yellow_mask = cv2.inRange(hsv, np.array([15, 80, 120]), np.array([40, 255, 255]))
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
    yellow_mask = cv2.morphologyEx(yellow_mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(yellow_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    best_info = None
    best_score = -1.0
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 1000 or area > (h * w * 0.25):
            continue
        hull = cv2.convexHull(cnt)
        if len(hull) < 5:
            continue
        hull_area = cv2.contourArea(hull)
        hull_perimeter = cv2.arcLength(hull, True)
        if hull_perimeter == 0:
            continue
        hull_circ = 4 * math.pi * hull_area / (hull_perimeter ** 2)

        x, y, bw, bh = cv2.boundingRect(cnt)
        aspect_ratio = float(bw) / bh if bh > 0 else 0

        if 0.5 <= aspect_ratio <= 2.0:
            # Fit ellipse to convex hull
            ellipse = cv2.fitEllipse(hull)
            (cx, cy), (axes_w, axes_h), angle = ellipse
            dist_to_center = math.hypot(cx - w/2, cy - h/2)
            score = (hull_circ + 0.1) * (1.0 - dist_to_center / max(w, h)) * math.log(area)
            if score > best_score:
                best_score = score
                best_info = (cx, cy, axes_w/2, axes_h/2, angle, hull_circ)

    if not best_info:
        return None

    cx, cy, a, b, angle, hull_circ = best_info
    
    # WA standard: yellow zone outer is 19.2% of target radius
    a_outer = a / 0.192
    b_outer = b / 0.192
    confidence = min(0.5 + hull_circ * 0.4, 0.95)

    return TargetInfo(float(cx), float(cy), float(a_outer), float(b_outer), float(angle), confidence)

def get_normalized_distance(x, y, target):
    # Translate to center
    dx = x - target.center_x
    dy = y - target.center_y
    
    # Rotate by -angle to align with ellipse axes
    rad = -math.radians(target.angle)
    rx = dx * math.cos(rad) - dy * math.sin(rad)
    ry = dx * math.sin(rad) + dy * math.cos(rad)
    
    # Normalized distance
    return math.hypot(rx / target.a_outer, ry / target.b_outer)

def test_ellipse_pipeline():
    test_folder = "/app/tests/TestImages"
    images = sorted([f for f in os.listdir(test_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    for img_name in images:
        img_path = os.path.join(test_folder, img_name)
        image = cv2.imread(img_path)
        h, w = image.shape[:2]
        
        # Preprocess
        scale = 1024 / max(h, w) if max(h, w) > 1024 else 1.0
        if scale < 1.0:
            image = cv2.resize(image, (int(w * scale), int(h * scale)))
            h, w = image.shape[:2]
            
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        target = detect_target_ellipse(hsv, enhanced)
        if not target:
            print(f"Image: {img_name} - NO TARGET FOUND")
            continue
            
        # 1. Hough lines
        edges = cv2.Canny(enhanced, 50, 150)
        
        # Mask out anything outside target face (norm_dist > 1.0)
        # We can construct an elliptical mask
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.ellipse(
            mask,
            (int(target.center_x), int(target.center_y)),
            (int(target.a_outer * 1.0), int(target.b_outer * 1.0)),
            target.angle,
            0, 360,
            255,
            -1
        )
        edges = cv2.bitwise_and(edges, mask)
        
        lines = cv2.HoughLinesP(edges, rho=1, theta=math.pi / 180, threshold=40, minLineLength=40, maxLineGap=10)
        
        arrows = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                length = math.hypot(x2 - x1, y2 - y1)
                
                # Check radial alignment using normalized coordinates
                # Midpoint
                x_mid, y_mid = (x1 + x2) / 2, (y1 + y2) / 2
                
                # Vector in normalized coordinate system
                # Point 1 normalized
                dx1, dy1 = x1 - target.center_x, y1 - target.center_y
                rad = -math.radians(target.angle)
                rx1 = dx1 * math.cos(rad) - dy1 * math.sin(rad)
                ry1 = dx1 * math.sin(rad) + dy1 * math.cos(rad)
                
                # Point 2 normalized
                dx2, dy2 = x2 - target.center_x, y2 - target.center_y
                rx2 = dx2 * math.cos(rad) - dy2 * math.sin(rad)
                ry2 = dx2 * math.sin(rad) + dy2 * math.cos(rad)
                
                # Normalized vector
                nvx, nvy = rx2 - rx1, ry2 - ry1
                nlen = math.hypot(nvx, nvy)
                
                # Midpoint normalized
                rx_mid, ry_mid = (rx1 + rx2) / 2, (ry1 + ry2) / 2
                ndist = math.hypot(rx_mid, ry_mid)
                
                if ndist > 0:
                    cos_theta = abs(nvx * rx_mid + nvy * ry_mid) / (nlen * ndist)
                else:
                    cos_theta = 1.0
                    
                if cos_theta < 0.95:
                    continue
                    
                # Endpoint closer to center
                dist1 = math.hypot(rx1 / target.a_outer, ry1 / target.b_outer)
                dist2 = math.hypot(rx2 / target.a_outer, ry2 / target.b_outer)
                tip_x, tip_y = (x1, y1) if dist1 < dist2 else (x2, y2)
                tip_ndist = min(dist1, dist2)
                
                # Ensure tip is inside the target rings
                if tip_ndist > 0.98:
                    continue
                    
                arrows.append(ArrowInfo(tip_x, tip_y, length / 250.0, "hough"))
                
        # NMS
        arrows.sort(key=lambda x: x.confidence, reverse=True)
        merged = []
        distance_threshold = 20.0
        for cand in arrows:
            is_dup = False
            for existing in merged:
                if math.hypot(cand.tip_x - existing.tip_x, cand.tip_y - existing.tip_y) < distance_threshold:
                    is_dup = True
                    break
            if not is_dup:
                merged.append(cand)
                
        print(f"Image: {img_name}")
        print(f"  Target: center=({target.center_x:.1f}, {target.center_y:.1f}), axes=({target.a_outer:.1f}, {target.b_outer:.1f}), angle={target.angle:.1f}")
        print(f"  Arrows count: {len(merged)}")
        for idx, arr in enumerate(merged):
            # Calculate zone
            ndist = get_normalized_distance(arr.tip_x, arr.tip_y, target)
            zone = 0
            for boundary, score in zip([0.048, 0.096, 0.192, 0.288, 0.384, 0.480, 0.576, 0.672, 0.768, 0.864, 0.960], [10, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]):
                if ndist <= boundary:
                    zone = score
                    break
            print(f"    {idx+1}: tip=({arr.tip_x:.1f}, {arr.tip_y:.1f}), zone={zone}, norm_dist={ndist:.3f}")
        print("-" * 50)

if __name__ == "__main__":
    test_ellipse_pipeline()
