"""
Script to train YOLO11 model on the archery dataset using CPU.
"""

import os
import sys
from ultralytics import YOLO

def main():
    # Dataset config path
    data_yaml = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "Data", "data.yaml"))
    
    if not os.path.exists(data_yaml):
        print(f"Error: Dataset configuration file not found at {data_yaml}")
        sys.exit(1)
        
    print(f"Using dataset configuration: {data_yaml}")
    
    # Get epochs from arguments if provided
    epochs = 50
    if len(sys.argv) > 1:
        try:
            epochs = int(sys.argv[1])
        except ValueError:
            print(f"Warning: Invalid epoch count provided. Using default of {epochs}.")
            
    print(f"Starting YOLO11 training for {epochs} epochs on CPU...")
    
    # Load pretrained YOLO11 Nano model
    model = YOLO("yolo11n.pt")
    
    # Train the model
    # Note: device='cpu' is explicitly specified since CUDA is not available.
    results = model.train(
        data=data_yaml,
        epochs=epochs,
        imgsz=896,
        batch=4,          # Keep batch size small for CPU to manage memory and compute
        device="cpu",
        workers=2,
        project="runs/detect",
        name="archery_yolo11",
        exist_ok=True,
    )
    
    print("\nTraining completed successfully!")
    print(f"Model saved to: {results.save_dir}")
    print(f"Best weights: {os.path.join(results.save_dir, 'weights', 'best.pt')}")

if __name__ == "__main__":
    main()
