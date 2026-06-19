import os
import math
import cv2
import numpy as np

# Use the yellow target detection from before
def detect_target(hsv, enhanced):
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
            (cx, cy), r = cv2.minEnclosingCircle(cnt)
            dist_to_center = math.hypot(cx - w/2, cy - h/2)
            score = (hull_circ + 0.1) * (1.0 - dist_to_center / max(w, h)) * math.log(area)
            if score > best_score:
                best_score = score
                best_info = (cx, cy, r, hull_circ, area)

    if not best_info:
        return None

    cx, cy, r, hull_circ, area = best_info
    outer_radius = r / 0.192
    return cx, cy, outer_radius

def debug_one_image():
    test_folder = "/app/tests/TestImages"
    images = sorted([f for f in os.listdir(test_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    if not images:
        print("No images found")
        return
        
    img_name = images[0]
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
    
    target = detect_target(hsv, enhanced)
    if not target:
        print("No target found")
        return
        
    cx, cy, r_outer = target
    print(f"Target center: ({cx:.1f}, {cy:.1f}), radius: {r_outer:.1f}")
    
    # Canny & Mask
    edges = cv2.Canny(enhanced, 50, 150)
    mask = np.zeros((h, w), dtype=np.uint8)
    cv2.circle(mask, (int(cx), int(cy)), int(r_outer * 1.0), 255, -1)
    edges = cv2.bitwise_and(edges, mask)
    
    # Run HoughLinesP
    lines = cv2.HoughLinesP(edges, rho=1, theta=math.pi / 180, threshold=40, minLineLength=40, maxLineGap=10)
    
    # Draw debug image
    debug_img = image.copy()
    cv2.circle(debug_img, (int(cx), int(cy)), int(r_outer), (0, 255, 0), 2)
    cv2.circle(debug_img, (int(cx), int(cy)), 5, (0, 0, 255), -1)
    
    passed_lines = []
    if lines is not None:
        for idx, line in enumerate(lines):
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
                
            # Let's print info for a few lines
            if idx < 10:
                print(f"Line {idx}: ({x1},{y1})->({x2},{y2}), len={length:.1f}, dist={dist_to_center:.1f}, cos={cos_theta:.3f}")
                
            if cos_theta >= 0.98:
                # Ensure tip is inside target region
                d1 = math.hypot(x1 - cx, y1 - cy)
                d2 = math.hypot(x2 - cx, y2 - cy)
                tip_dist = min(d1, d2)
                if tip_dist <= r_outer * 0.98:
                    passed_lines.append(line[0])
                    cv2.line(debug_img, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    print(f"Passed Line: ({x1},{y1})->({x2},{y2}), len={length:.1f}, dist={dist_to_center:.1f}, cos={cos_theta:.4f}")
                    
    print(f"Total lines returned by Hough: {len(lines) if lines is not None else 0}")
    print(f"Total lines passed cos_theta >= 0.98: {len(passed_lines)}")
    
    # Save debug image
    os.makedirs("/app/tests/TargetDebug", exist_ok=True)
    cv2.imwrite("/app/tests/TargetDebug/debug_lines.jpg", debug_img)
    print("Debug image saved at /app/tests/TargetDebug/debug_lines.jpg")

if __name__ == "__main__":
    debug_one_image()
