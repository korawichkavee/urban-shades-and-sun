from ultralytics import YOLO

# Train YOLO model on new training_labels.json dataset
model = YOLO('yolo11s.pt')
results = model.train(
    data='/home/kieran/Documents/Python/sunny_day_SVI/data/yolo_training_dataset/data.yaml',
    epochs=100,
    batch=16,
    imgsz=640,
    device='cpu',  # No GPU available
    save=True,
    project='outputs/models',
    name='yolo_training_labels'
)

print("\nTraining complete!")
print(f"Results saved to: {results.save_dir}")
print(f"Best weights: {results.save_dir}/weights/best.pt")
