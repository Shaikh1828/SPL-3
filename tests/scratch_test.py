import sys
import os

# Add workspace src to path
sys.path.insert(0, os.path.abspath(os.path.dirname(os.path.dirname(__file__))))

from src.services.arrow_detection_service import ArrowDetectionService

def run_tests():
    test_folder = "/app/tests/TestImages"
    images = sorted([f for f in os.listdir(test_folder) if f.lower().endswith(('.png', '.jpg', '.jpeg'))])
    
    print(f"Found {len(images)} images in {test_folder}\n")
    
    service = ArrowDetectionService()
    
    for img_name in images:
        img_path = os.path.join(test_folder, img_name)
        result = service.detect(image_path=img_path)
        
        print(f"Image: {img_name}")
        print(f"  Target: {result.target.method if result.target else 'None'} (Conf: {result.target.confidence:.2%} if result.target else 0%)")
        if result.target:
            print(f"    Center: ({result.target.center_x:.1f}, {result.target.center_y:.1f}), Radius: {result.target.outer_radius:.1f}")
        print(f"  Detected Score: {result.points} pts, Conf: {result.confidence:.2%}")
        print(f"  Arrow Count: {len(result.arrows)}")
        for idx, arr in enumerate(result.arrows):
            print(f"    {idx+1}: Tip=({arr.tip_x:.1f}, {arr.tip_y:.1f}), Conf={arr.confidence:.2%}, Zone={arr.zone}, Method={arr.method}")
        print("-" * 50)

if __name__ == "__main__":
    run_tests()
