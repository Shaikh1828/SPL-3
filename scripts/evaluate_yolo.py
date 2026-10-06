"""
Script to evaluate the trained YOLO11 model on the validation/test split.
"""

import os
import sys
import argparse
from ultralytics import YOLO

def parse_args():
    parser = argparse.ArgumentParser(description="Evaluate YOLO11 on Archery Dataset")
    
    default_weights = os.path.abspath(os.path.join(
        os.path.dirname(__file__), "..", "runs", "detect", "archery_yolo11", "weights", "best.pt"
    ))
    default_data = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Data2", "data.yaml"))
    if not os.path.exists(default_data):
        default_data = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Data", "data.yaml"))
        
    parser.add_argument("--weights", type=str, default=default_weights, help="Path to weights file")
    parser.add_argument("--data", type=str, default=default_data, help="Path to data.yaml")
    parser.add_argument("--split", type=str, default="val", help="Split to evaluate on ('val' or 'test')")
    parser.add_argument("--imgsz", type=int, default=896, help="Image size")
    
    return parser.parse_args()

def main():
    args = parse_args()
    
    best_weights = os.path.abspath(args.weights)
    data_yaml = os.path.abspath(args.data)
    
    if not os.path.exists(best_weights):
        print(f"Error: Trained weights not found at {best_weights}")
        print("Please train the model first.")
        sys.exit(1)
        
    if not os.path.exists(data_yaml):
        print(f"Error: Dataset yaml not found at {data_yaml}")
        sys.exit(1)
        
    print(f"Loading trained model from: {best_weights}")
    print(f"Dataset config: {data_yaml}")
    model = YOLO(best_weights)
    
    print(f"Running evaluation on {args.split} split...")
    metrics = model.val(data=data_yaml, split=args.split, imgsz=args.imgsz)
    
    print("\nEvaluation Metrics:")
    print(f"mAP50: {metrics.box.map50:.4f}")
    print(f"mAP50-95: {metrics.box.map:.4f}")
    print(f"Precision: {metrics.box.mp:.4f}")
    print(f"Recall: {metrics.box.mr:.4f}")
    
    # Run a sample prediction on a test image if available
    dataset_dir = os.path.dirname(data_yaml)
    test_dirs = [
        os.path.join(dataset_dir, "test", "images"),
        os.path.join(dataset_dir, "valid", "images")
    ]
    
    for t_dir in test_dirs:
        if os.path.exists(t_dir):
            test_images = [os.path.join(t_dir, f) for f in os.listdir(t_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]
            if test_images:
                sample_img = test_images[0]
                print(f"\nRunning sample prediction on: {sample_img}")
                project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "runs", "detect"))
                results = model.predict(sample_img, imgsz=args.imgsz, save=True, project=project_dir, name="evaluation_predictions", exist_ok=True)
                print(f"Sample prediction visualization saved.")
                break

if __name__ == "__main__":
    main()
