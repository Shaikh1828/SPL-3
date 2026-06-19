import os
import math
import cv2
import numpy as np

class TargetInfo:
    def __init__(self, center_x, center_y, outer_radius, confidence):
        self.center_x = center_x
        self.center_y = center_y
        self.outer_radius = outer_radius
        self.confidence = confidence

class ArrowInfo:
    def __init__(self, tip_x, tip_y, confidence, method="unknown", shaft_angle=None):
        self.tip_x = tip_x
        self.tip_y = tip_y
        self.confidence = confidence
        self.method = method
        self.shaft_angle = shaft_angle

def detect_target_area_based(hsv, enhanced):
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
        hull_area = cv2.contourArea(hull)
        hull_perimeter = cv2.arcLength(hull, True)
        if hull_perimeter == 0:
            continue
        hull_circ = 4 * math.pi * hull_area / (hull_perimeter ** 2)

        x, y, bw, bh = cv2.boundingRect(cnt)
        aspect_ratio = float(bw) / bh if bh > 0 else 0

        if 0.5 <= aspect_ratio <= 2.0:
            # Centroid
            M = cv2.moments(cnt)
            if M["m00"] > 0:
                cx = M["m10"] / M["m00"]
                cy = M["m01"] / M["m00"]
                dist_to_center = math.hypot(cx - w/2, cy - h/2)
                score = (hull_circ + 0.1) * (1.0 - dist_to_center / max(w, h)) * math.log(area)
                if score > best_score:
                    best_score = score
                    best_info = (cx, cy, area, hull_circ)

    if not best_info:
        return None

    cx, cy, area, hull_circ = best_info
    
    # Calculate radius from area: area = pi * r^2
    r_yellow = math.sqrt(area / math.pi)
    
    # WA standard: yellow zone outer is 19.2% of target radius
    outer_radius = r_yellow / 0.192
    confidence = min(0.5 + hull_circ * 0.4, 0.95)

    return TargetInfo(float(cx), float(cy), float(outer_radius), confidence)

def test_area_pipeline():
    test_folder = "/app/tests/TestImages"
    images = sorted([f for f in os.listdir(test_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    # Only test the first 3 images for debugging
    for img_name in images[:3]:
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
        
        target = detect_target_area_based(hsv, enhanced)
        if not target:
            print(f"Image: {img_name} - NO TARGET FOUND")
            continue
            
        # Hough lines on Canny edges inside target ROI mask
        edges = cv2.Canny(enhanced, 50, 150)
        mask = np.zeros((h, w), dtype=np.uint8)
        # Use 0.96 because outer_radius is the target radius (Zone 1 boundary is at 0.96)
        cv2.circle(mask, (int(target.center_x), int(target.center_y)), int(target.outer_radius * 0.96), 255, -1)
        edges = cv2.bitwise_and(edges, mask)
        
        # Stricter Hough lines parameters: min length 45 to ignore noise
        lines = cv2.HoughLinesP(edges, rho=1, theta=math.pi / 180, threshold=40, minLineLength=45, maxLineGap=10)
        
        arrows = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                length = math.hypot(x2 - x1, y2 - y1)
                
                # Check radial alignment
                vx, vy = x2 - x1, y2 - y1
                x_mid, y_mid = (x1 + x2) / 2, (y1 + y2) / 2
                ux, uy = x_mid - target.center_x, y_mid - target.center_y
                dist_to_center = math.hypot(ux, uy)
                
                if dist_to_center > 0:
                    cos_theta = abs(vx * ux + vy * uy) / (length * dist_to_center)
                else:
                    cos_theta = 1.0
                    
                # Use stricter cos_theta threshold: 0.96
                if cos_theta < 0.96:
                    continue
                    
                # Calculate angle in degrees [0, 180)
                angle_deg = math.degrees(math.atan2(vy, vx)) % 180
                # Filter out perfectly horizontal and vertical lines (printed axes/borders)
                if angle_deg < 6 or angle_deg > 174 or (84 < angle_deg < 96):
                    continue
                    
                d1 = math.hypot(x1 - target.center_x, y1 - target.center_y)
                d2 = math.hypot(x2 - target.center_x, y2 - target.center_y)
                tip_x, tip_y = (x1, y1) if d1 < d2 else (x2, y2)
                tip_dist = min(d1, d2)
                
                # Ensure tip is inside target rings
                if tip_dist > target.outer_radius * 0.96:
                    continue
                    
                arrows.append(ArrowInfo(tip_x, tip_y, length / 250.0, "hough", math.degrees(math.atan2(vy, vx))))
                
        # NMS with larger distance threshold (40 pixels) to merge duplicate lines of same arrow
        arrows.sort(key=lambda x: x.confidence, reverse=True)
        merged = []
        distance_threshold = 40.0
        for cand in arrows:
            is_dup = False
            for existing in merged:
                # Merge if tips are close
                if math.hypot(cand.tip_x - existing.tip_x, cand.tip_y - existing.tip_y) < distance_threshold:
                    is_dup = True
                    break
            if not is_dup:
                merged.append(cand)
                
        print(f"Image: {img_name}")
        print(f"  Target: center=({target.center_x:.1f}, {target.center_y:.1f}), r={target.outer_radius:.1f}")
        print(f"  Arrows count: {len(merged)}")
        for idx, arr in enumerate(merged):
            dist = math.hypot(arr.tip_x - target.center_x, arr.tip_y - target.center_y)
            norm = dist / target.outer_radius
            zone = 0
            for boundary, score in zip([0.048, 0.096, 0.192, 0.288, 0.384, 0.480, 0.576, 0.672, 0.768, 0.864, 0.960], [10, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]):
                if norm <= boundary:
                    zone = score
                    break
            print(f"    {idx+1}: tip=({arr.tip_x:.1f}, {arr.tip_y:.1f}), zone={zone}, norm_dist={norm:.3f}")
        print("-" * 50)

if __name__ == "__main__":
    test_area_pipeline()
