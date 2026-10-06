"""
Script to train YOLO11 model on the archery dataset using CPU.
Preserves the exact architecture, arguments, and structure of the original training pipeline.
"""

import os
import sys
import argparse
from ultralytics import YOLO

def parse_args():
    parser = argparse.ArgumentParser(description="Train YOLO11 on Archery Dataset")
    
    # Default to Data2/data.yaml if present, otherwise fallback to Data/data.yaml
    default_data = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Data2", "data.yaml"))
    if not os.path.exists(default_data):
        default_data = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Data", "data.yaml"))
        
    parser.add_argument(
        "--data",
        type=str,
        default=default_data,
        help="Path to dataset data.yaml file"
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=30,
        help="Number of training epochs (default: 30)"
    )
    parser.add_argument(
        "--batch",
        type=int,
        default=4,
        help="Batch size (default: 4 for CPU)"
    )
    parser.add_argument(
        "--imgsz",
        type=int,
        default=896,
        help="Input image resolution (default: 896)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cpu",
        help="Device to train on ('cpu' or '0')"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=2,
        help="Number of dataloader workers"
    )
    parser.add_argument(
        "--name",
        type=str,
        default="archery_yolo11",
        help="Run name under runs/detect/"
    )
    parser.add_argument(
        "--cache",
        action="store_true",
        default=True,
        help="Cache images in RAM for accelerated CPU training"
    )
    
    # Support positional argument for backward compatibility: python train_yolo.py [epochs]
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        args, unknown = parser.parse_known_args()
        args.epochs = int(sys.argv[1])
        return args
        
    return parser.parse_args()

def main():
    args = parse_args()
    
    data_yaml = os.path.abspath(args.data)
    if not os.path.exists(data_yaml):
        print(f"Error: Dataset configuration file not found at {data_yaml}")
        sys.exit(1)
        
    print(f"Using dataset configuration: {data_yaml}")
    print(f"Starting YOLO11 training for {args.epochs} epochs on {args.device}...")
    print(f"Hyperparameters: imgsz={args.imgsz}, batch={args.batch}, workers={args.workers}, cache={args.cache}")
    
    # Project directory: SPL-3/runs/detect
    project_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "runs", "detect"))
    os.makedirs(project_dir, exist_ok=True)
    
    # Load pretrained YOLO11 Nano model
    model_weight = "yolo11n.pt"
    if not os.path.exists(model_weight):
        model_weight = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "yolo11n.pt"))
    
    print(f"Loading base model: {model_weight}")
    model = YOLO(model_weight)
    
    # Train the model with exact hyperparameters and CPU compatibility
    results = model.train(
        data=data_yaml,
        epochs=args.epochs,
        imgsz=args.imgsz,
        batch=args.batch,
        device=args.device,
        workers=args.workers,
        project=project_dir,
        name=args.name,
        cache=args.cache,
        exist_ok=True,
    )
    
    print("\nTraining completed successfully!")
    print(f"Model saved to: {results.save_dir}")
    best_weights = os.path.join(results.save_dir, "weights", "best.pt")
    print(f"Best weights: {best_weights}")
    
    return results

if __name__ == "__main__":
    main()
