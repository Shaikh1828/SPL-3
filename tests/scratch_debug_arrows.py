import os
import math
import cv2
import numpy as np

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
    r_yellow = math.sqrt(area / math.pi)
    outer_radius = r_yellow / 0.192
    confidence = min(0.5 + hull_circ * 0.4, 0.95)
    return cx, cy, outer_radius, confidence

def debug_image_2():
    test_folder = "/app/tests/TestImages"
    images = sorted([f for f in os.listdir(test_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    if len(images) < 2:
        print("Not enough images")
        return
        
    img_name = images[1] # Image 2
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
    
    res = detect_target_area_based(hsv, enhanced)
    if not res:
        print("No target found")
        return
        
    cx, cy, r_outer, confidence = res
    print(f"Target: center=({cx:.1f}, {cy:.1f}), r={r_outer:.1f}")
    
    # Canny & Mask
    edges = cv2.Canny(enhanced, 50, 150)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, (int(cx), int(cy)), int(r_outer * 0.96), 255, -1)
    edges = cv2.bitwise_and(edges, mask)
    
    # HoughLinesP
    lines = cv2.HoughLinesP(edges, rho=1, theta=math.pi / 180, threshold=40, minLineLength=45, maxLineGap=10)
    
    arrows = []
    if lines is not None:
        for line in lines:
            x1, y1, x2, y2 = line[0]
            length = math.hypot(x2 - x1, y2 - y1)
            
            vx, vy = x2 - x1, y2 - y1
            x_mid, y_mid = (x1 + x2) / 2, (y1 + y2) / 2
            ux, uy = x_mid - cx, y_mid - cy
            dist_to_center = math.hypot(ux, uy)
            
            if dist_to_center > 0:
                cos_theta = abs(vx * ux + vy * uy) / (length * dist_to_center)
            else:
                cos_theta = 1.0
                
            if cos_theta < 0.96:
                continue
                
            # Filter perfectly horizontal and vertical lines (printed axes/borders)
            angle_deg = math.degrees(math.atan2(vy, vx)) % 180
            if angle_deg < 6 or angle_deg > 174 or (84 < angle_deg < 96):
                continue
                
            d1 = math.hypot(x1 - cx, y1 - cy)
            d2 = math.hypot(x2 - cx, y2 - cy)
            tip_x, tip_y = (x1, y1) if d1 < d2 else (x2, y2)
            tip_dist = min(d1, d2)
            
            if tip_dist > r_outer * 0.96:
                continue
                
            arrows.append((tip_x, tip_y, x1, y1, x2, y2, length))
            
    # NMS
    arrows.sort(key=lambda x: x[6], reverse=True)
    merged = []
    distance_threshold = 40.0
    for cand in arrows:
        is_dup = False
        for existing in merged:
            if math.hypot(cand[0] - existing[0], cand[1] - existing[1]) < distance_threshold:
                is_dup = True
                break
        if not is_dup:
            merged.append(cand)
            
    print(f"Detected {len(merged)} arrows in Image 2:")
    
    # Draw on image
    debug_img = image.copy()
    cv2.circle(debug_img, (int(cx), int(cy)), int(r_outer * 0.96), (0, 255, 0), 2)
    cv2.circle(debug_img, (int(cx), int(cy)), 5, (0, 0, 255), -1)
    
    for idx, (tx, ty, x1, y1, x2, y2, length) in enumerate(merged):
        cv2.line(debug_img, (x1, y1), (x2, y2), (255, 0, 0), 2)
        cv2.circle(debug_img, (int(tx), int(ty)), 6, (0, 255, 255), -1)
        cv2.putText(debug_img, str(idx+1), (int(tx) + 10, int(ty) - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        print(f"  {idx+1}: Tip=({tx:.1f}, {ty:.1f}), length={length:.1f}")
        
    os.makedirs("/app/tests/TargetDebug", exist_ok=True)
    cv2.imwrite("/app/tests/TargetDebug/debug_arrows_2.jpg", debug_img)
    print("Saved debug image to /app/tests/TargetDebug/debug_arrows_2.jpg")

if __name__ == "__main__":
    debug_image_2()
