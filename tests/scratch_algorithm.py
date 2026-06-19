import sys
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

def detect_target_by_color_bands(hsv, enhanced):
    h, w = hsv.shape[:2]
    # Standard yellow range
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
            (cx, cy), r = cv2.minEnclosingCircle(cnt)
            dist_to_center = math.hypot(cx - w/2, cy - h/2)
            score = (hull_circ + 0.1) * (1.0 - dist_to_center / max(w, h)) * math.log(area)
            if score > best_score:
                best_score = score
                best_info = (cx, cy, r, hull_circ, area)

    if not best_info:
        return None

    cx, cy, r, hull_circ, area = best_info
    if r < 3:
        return None

    # WA standard: yellow zone outer is 19.2% of target radius
    outer_radius = r / 0.192
    confidence = min(0.5 + hull_circ * 0.4, 0.95)

    return TargetInfo(float(cx), float(cy), float(outer_radius), confidence)

def test_combination(min_len, cos_thresh):
    test_folder = "tests/TestImages"
    images = sorted([f for f in os.listdir(test_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    total_arrows = 0
    results = []
    
    for img_name in images:
        img_path = os.path.join(test_folder, img_name)
        image = cv2.imread(img_path)
        h, w = image.shape[:2]
        
        # Preprocess
        scale = 1024 / max(h, w) if max(h, w) > 1024 else 1.0
        if scale < 1.0:
            image = cv2.resize(image, (int(w * scale), int(h * scale)))
            
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        target = detect_target_by_color_bands(hsv, enhanced)
        if not target:
            results.append((img_name, 0))
            continue
            
        # 1. Hough lines
        edges = cv2.Canny(enhanced, 50, 150)
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(mask, (int(target.center_x), int(target.center_y)), int(target.outer_radius * 1.0), 255, -1)
        edges = cv2.bitwise_and(edges, mask)
        
        lines = cv2.HoughLinesP(edges, rho=1, theta=math.pi / 180, threshold=40, minLineLength=min_len, maxLineGap=10)
        
        arrows = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                length = math.hypot(x2 - x1, y2 - y1)
                
                # Vector
                vx, vy = x2 - x1, y2 - y1
                # Midpoint
                x_mid, y_mid = (x1 + x2) / 2, (y1 + y2) / 2
                # Vector from target center to midpoint
                ux, uy = x_mid - target.center_x, y_mid - target.center_y
                dist_to_center = math.hypot(ux, uy)
                
                if dist_to_center > 0:
                    cos_theta = abs(vx * ux + vy * uy) / (length * dist_to_center)
                else:
                    cos_theta = 1.0
                    
                if cos_theta < cos_thresh:
                    continue
                    
                d1 = math.hypot(x1 - target.center_x, y1 - target.center_y)
                d2 = math.hypot(x2 - target.center_x, y2 - target.center_y)
                tip_x, tip_y = (x1, y1) if d1 < d2 else (x2, y2)
                tip_dist = min(d1, d2)
                
                if tip_dist > target.outer_radius * 0.98:
                    continue
                    
                arrows.append(ArrowInfo(tip_x, tip_y, length / 250.0, "hough"))
                
        # 2. Color Segment
        combined = np.zeros((h, w), dtype=np.uint8)
        for lower, upper in [
            ([0, 120, 100], [12, 255, 255]),
            ([168, 120, 100], [180, 255, 255]),
            ([95, 80, 80], [135, 255, 255]),
            ([0, 0, 0], [180, 255, 55]),
            ([15, 80, 130], [40, 255, 255]),
            ([0, 0, 190], [180, 40, 255]),
            ([50, 80, 80], [85, 255, 255]),
        ]:
            m = cv2.inRange(hsv, np.array(lower), np.array(upper))
            combined = cv2.bitwise_or(combined, m)
            
        roi_mask = np.zeros((h, w), dtype=np.uint8)
        cv2.circle(roi_mask, (int(target.center_x), int(target.center_y)), int(target.outer_radius * 1.0), 255, -1)
        combined = cv2.bitwise_and(combined, roi_mask)
        
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        combined = cv2.morphologyEx(combined, cv2.MORPH_CLOSE, k)
        combined = cv2.morphologyEx(combined, cv2.MORPH_OPEN, k)
        
        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
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
                continue
                
            [vx, vy, x0, y0] = cv2.fitLine(cnt, cv2.DIST_L2, 0, 0.01, 0.01)
            vx, vy = float(vx), float(vy)
            x0, y0 = float(x0), float(y0)
            ux, uy = x0 - target.center_x, y0 - target.center_y
            dist_to_center = math.hypot(ux, uy)
            
            if dist_to_center > 0:
                cos_theta = abs(vx * ux + vy * uy) / dist_to_center
            else:
                cos_theta = 1.0
                
            if cos_theta < cos_thresh:
                continue
                
            points = cnt.reshape(-1, 2)
            dists = np.linalg.norm(points.astype(float) - np.array([target.center_x, target.center_y]), axis=1)
            min_idx = int(np.argmin(dists))
            tip_dist = dists[min_idx]
            if tip_dist > target.outer_radius * 0.98:
                continue
            tip = points[min_idx]
            arrows.append(ArrowInfo(tip[0], tip[1], aspect / 12.0, "color"))
            
        # 3. Contour Aspect
        edges_c = cv2.Canny(enhanced, 30, 100)
        edges_c = cv2.dilate(edges_c, cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2)), iterations=1)
        edges_c = cv2.bitwise_and(edges_c, roi_mask)
        contours, _ = cv2.findContours(edges_c, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if contours:
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
                if score > 0:
                    [vx, vy, x0, y0] = cv2.fitLine(cnt, cv2.DIST_L2, 0, 0.01, 0.01)
                    vx, vy = float(vx), float(vy)
                    x0, y0 = float(x0), float(y0)
                    ux, uy = x0 - target.center_x, y0 - target.center_y
                    dist_to_center = math.hypot(ux, uy)
                    if dist_to_center > 0:
                        cos_theta = abs(vx * ux + vy * uy) / dist_to_center
                    else:
                        cos_theta = 1.0
                        
                    if cos_theta < cos_thresh:
                        continue
                        
                    points = cnt.reshape(-1, 2)
                    dists = np.linalg.norm(points.astype(float) - np.array([target.center_x, target.center_y]), axis=1)
                    min_idx = int(np.argmin(dists))
                    tip_dist = dists[min_idx]
                    if tip_dist > target.outer_radius * 0.98:
                        continue
                    tip = points[min_idx]
                    arrows.append(ArrowInfo(tip[0], tip[1], score / 60.0, "contour"))
                    
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
                
        results.append((img_name, len(merged)))
        total_arrows += len(merged)
        
    return total_arrows, results

if __name__ == "__main__":
    for min_len in [35, 45, 55]:
        for cos_thresh in [0.90, 0.94, 0.96, 0.98]:
            total, results = test_combination(min_len, cos_thresh)
            print(f"min_len={min_len}, cos_thresh={cos_thresh} -> Total Arrows={total}, Avg={total/20:.1f}")
            # print first 3 image arrow counts
            print("  First 3:", results[:3])
