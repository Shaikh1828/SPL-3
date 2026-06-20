"""
Diagnostic script: runs the CURRENT production ArrowDetectionService against
every image in tests/TestImages, prints target/arrow counts, and writes
annotated debug images to tests/TargetDebug/current_<name>.jpg so we can see
exactly what the production pipeline gets right/wrong today.

Not a pytest test — run directly: python tests/scratch_diagnose_current.py
"""
import os
import sys
import math

import importlib.util

import cv2
import numpy as np

_MODULE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "src", "services", "arrow_detection_service.py",
)
_spec = importlib.util.spec_from_file_location("arrow_detection_service", _MODULE_PATH)
_ads = importlib.util.module_from_spec(_spec)
sys.modules["arrow_detection_service"] = _ads
_spec.loader.exec_module(_ads)
ArrowDetectionService = _ads.ArrowDetectionService
WA_ZONE_BOUNDARIES = _ads.WA_ZONE_BOUNDARIES


def draw_debug(image, result):
    img = image.copy()
    t = result.target
    if t:
        a = int(t.a_outer if t.a_outer > 0 else t.outer_radius)
        b = int(t.b_outer if t.b_outer > 0 else t.outer_radius)
        cv2.ellipse(img, (int(t.center_x), int(t.center_y)), (a, b), t.angle, 0, 360, (0, 255, 0), 2)
        # draw all WA zone boundary ellipses
        for ratio in WA_ZONE_BOUNDARIES:
            cv2.ellipse(img, (int(t.center_x), int(t.center_y)),
                        (int(a * ratio), int(b * ratio)), t.angle, 0, 360, (0, 200, 255), 1)
        cv2.drawMarker(img, (int(t.center_x), int(t.center_y)), (0, 0, 255),
                        cv2.MARKER_CROSS, 12, 2)
        cv2.putText(img, f"target_conf={t.confidence:.2f} method={t.method}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

    for i, arr in enumerate(result.arrows or ([result.arrow] if result.arrow else [])):
        if arr is None:
            continue
        color = (0, 255, 0) if arr.confidence >= 0.7 else ((0, 255, 255) if arr.confidence >= 0.5 else (0, 0, 255))
        cv2.circle(img, (int(arr.tip_x), int(arr.tip_y)), 8, color, 2)
        cv2.putText(img, f"{arr.zone}/{arr.confidence:.2f}/{arr.method[:4]}",
                    (int(arr.tip_x) + 10, int(arr.tip_y)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

    cv2.putText(img, f"arrows={len(result.arrows)} method={result.method}",
                (10, 55), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
    return img


def main():
    test_folder = os.path.join(os.path.dirname(__file__), "TestImages")
    out_folder = os.path.join(os.path.dirname(__file__), "TargetDebug")
    os.makedirs(out_folder, exist_ok=True)

    images = sorted(f for f in os.listdir(test_folder) if f.lower().endswith((".jpg", ".jpeg", ".png")))
    svc = ArrowDetectionService()

    print(f"{'image':<55} {'tgt_conf':>8} {'tgt_method':<22} {'#arrows':>7} {'zones'}")
    for name in images:
        path = os.path.join(test_folder, name)
        image = cv2.imread(path)
        if image is None:
            print(f"{name}: FAILED TO LOAD")
            continue
        result = svc.detect(image_array=image)
        n_arrows = len(result.arrows)
        zones = [a.zone for a in result.arrows]
        tgt_conf = result.target.confidence if result.target else -1
        tgt_method = result.target.method if result.target else "NONE"
        print(f"{name:<55} {tgt_conf:>8.2f} {tgt_method:<22} {n_arrows:>7} {zones}")

        # Need to re-run preprocess scale to draw on the same (possibly resized) image
        h, w = image.shape[:2]
        scale = 1024 / max(h, w) if max(h, w) > 1024 else 1.0
        draw_img = image
        if scale < 1.0:
            draw_img = cv2.resize(image, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

        debug_img = draw_debug(draw_img, result)
        cv2.imwrite(os.path.join(out_folder, f"current_{name}"), debug_img)


if __name__ == "__main__":
    main()
