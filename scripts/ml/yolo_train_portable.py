# ABOUTME: Portable YOLO training script for GPU machine with relative paths
# ABOUTME: Automatically detects dataset location relative to script directory

from ultralytics import YOLO
from pathlib import Path

# Get the directory where this script is located
script_dir = Path(__file__).parent

# Dataset is in the same directory as this script
data_yaml = script_dir / "sunny_batch" / "data.yaml"

if not data_yaml.exists():
    print(f"ERROR: data.yaml not found at {data_yaml}")
    print(f"Please ensure sunny_batch/ is in the same directory as this script")
    exit(1)

print(f"Using dataset: {data_yaml}")

# Load YOLO model
model = YOLO('yolo11s.pt')

# Train the model
# Adjust epochs, batch size, and other parameters as needed
results = model.train(
    data=str(data_yaml),
    epochs=100,  # Increased for GPU training
    batch=16,    # Adjust based on GPU memory
    imgsz=640,
    device=0,    # Use first GPU (change to 'cpu' if needed)
    save=True,
    project='runs/detect',
    name='sunny_batch_train'
)

print("\nTraining complete!")
print(f"Results saved to: {results.save_dir}")
