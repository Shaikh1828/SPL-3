"""
Script to evaluate the trained YOLO11 model on the test split.
"""

import os
import sys
from ultralytics import YOLO

def main():
    # Paths
    best_weights = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "runs", "detect", "archery_yolo11", "weights", "best.pt"
    ))
    data_yaml = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "Data", "data.yaml"
    ))
    
    if not os.path.exists(best_weights):
        print(f"Error: Trained weights not found at {best_weights}")
        print("Please run train_yolo.py first.")
        sys.exit(1)
        
    print(f"Loading trained model from: {best_weights}")
    model = YOLO(best_weights)
    
    print("Running evaluation on validation split...")
    metrics = model.val(data=data_yaml, split="val")
    
    print("\nEvaluation Metrics:")
    print(f"mAP50: {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")
    print(f"Precision: {metrics.box.mp:.4f}")
    print(f"Recall: {metrics.box.mr:.4f}")
    
    # Run a quick prediction on a test image as a sample
    test_dir = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "Data", "test", "images"
    ))
    
    if os.path.exists(test_dir):
        test_images = [os.path.join(test_dir, f) for f in os.listdir(test_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
        if test_images:
            sample_img = test_images[0]
            print(f"\nRunning sample prediction on: {sample_img}")
            results = model.predict(sample_img, save=True, project="runs/detect", name="evaluation_predictions")
            print(f"Sample prediction visualization saved.")

if __name__ == "__main__":
    main()
