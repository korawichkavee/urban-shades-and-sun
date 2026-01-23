# Machine Learning Guide

## Overview

Scripts for computer vision tasks including people detection, sunny/shade classification, and YOLO model training.

Located in: `scripts/ml/`

## Computer Vision Tasks

### 1. Binary Classification (Sunny vs Shade)

#### `binary_image_classification.py`
Trains a Vision Transformer (ViT) to classify images as sunny or shaded.

**Purpose**: Determine if an image shows sunny or cloudy/shaded conditions.

**Usage**:
```bash
python scripts/ml/binary_image_classification.py \
  --train_dir data/train/ \
  --val_dir data/val/ \
  --epochs 20 \
  --batch_size 32
```

**Model Architecture**:
- Vision Transformer (ViT-B/16)
- Transfer learning from ImageNet
- Fine-tuned for sunny/shade binary classification

**Output**:
- Trained model: `outputs/models/vit_binary.pth`
- Training logs
- Validation accuracy metrics

---

#### `binary_image_inference.py`
Applies trained binary classifier to new images.

**Purpose**: Classify a batch of images as sunny or shaded.

**Usage**:
```bash
python scripts/ml/binary_image_inference.py \
  --model outputs/models/vit_binary.pth \
  --input_dir images/ \
  --output results.csv
```

**Output CSV Columns**:
- `image_id` - Image identifier
- `prediction` - Binary: sunny (1) or shade (0)
- `confidence` - Model confidence (0-1)

---

### 2. YOLO Object Detection

YOLO models detect people and shadows in street view images.

#### `prepare_yolo_dataset.py`
Prepares YOLO-format dataset from annotations.

**Purpose**: Convert annotations to YOLO training format.

**Usage**:
```bash
python scripts/ml/prepare_yolo_dataset.py \
  --input annotations/ \
  --output yolo_dataset/ \
  --classes person shadow
```

**Output Structure**:
```
yolo_dataset/
├── images/
│   ├── train/
│   └── val/
├── labels/
│   ├── train/
│   └── val/
└── data.yaml
```

**YOLO Label Format**: `class x_center y_center width height` (normalized 0-1)

---

#### `convert_json_to_yolo.py`
Converts JSON annotations to YOLO format.

**Purpose**: Handle various annotation formats (COCO, Labelbox, etc.)

**Usage**:
```bash
python scripts/ml/convert_json_to_yolo.py \
  --json annotations.json \
  --output_dir yolo_labels/ \
  --format coco
```

**Supported Formats**:
- COCO JSON
- Labelbox JSON
- Custom annotation formats

---

#### `package_yolo_dataset.py`
Packages YOLO dataset for deployment or sharing.

**Purpose**: Create distributable YOLO dataset archives.

**Usage**:
```bash
python scripts/ml/package_yolo_dataset.py \
  --dataset_dir yolo_dataset/ \
  --output package.zip
```

---

#### `yolo_train_portable.py`
Trains YOLO model on custom dataset.

**Purpose**: Train or fine-tune YOLO for people/shadow detection.

**Usage**:
```bash
python scripts/ml/yolo_train_portable.py \
  --data yolo_dataset/data.yaml \
  --epochs 100 \
  --batch 16 \
  --img 640
```

**Configuration**:
- Base model: YOLOv11 (or v8)
- Image size: 640x640
- Classes: person, shadow
- Augmentation: enabled by default

**Output**:
- `outputs/models/YOLO/best.pt` - Best model weights
- `outputs/models/YOLO/last.pt` - Final epoch weights
- Training curves and metrics

---

#### `evaluate_yolo_model.py`
Evaluates trained YOLO model performance.

**Purpose**: Generate metrics and visualizations for model assessment.

**Usage**:
```bash
python scripts/ml/evaluate_yolo_model.py \
  --model outputs/models/YOLO/best.pt \
  --data yolo_dataset/data.yaml \
  --save_plots
```

**Metrics Generated**:
- mAP@0.5 (mean Average Precision)
- mAP@0.5:0.95
- Precision/Recall curves
- Confusion matrix
- Per-class AP

**Visualizations**:
- Precision-Recall curves
- F1-Score curves
- Confusion matrix heatmap
- Sample predictions

---

#### `yolo_finetune_test.py`
Quick test script for YOLO fine-tuning.

**Purpose**: Validate YOLO training setup before full run.

**Usage**:
```bash
python scripts/ml/yolo_finetune_test.py
```

---

### 3. Utility Scripts

#### `fix_label_names.py`
Fixes inconsistent label names in YOLO annotations.

**Purpose**: Normalize class names across annotation files.

**Usage**:
```bash
python scripts/ml/fix_label_names.py \
  --labels_dir yolo_dataset/labels/ \
  --mapping '{"ppl": "person", "prsn": "person"}'
```

---

## Model Inference Pipeline

### Integration with Full Pipeline

The full pipeline (`scripts/pipelines/hot_cities_full_pipeline.py`) integrates:

1. **Binary Classification**: Determine sunny vs cloudy
2. **YOLO Detection**: Count people and shadows
3. **Geometric Analysis**: Calculate shade ratios

**Usage**:
```bash
python scripts/pipelines/hot_cities_full_pipeline.py \
  --city Bangkok \
  --input data/processed/Bangkok_walkable.csv \
  --binary_model outputs/models/vit_binary.pth \
  --yolo_model outputs/models/YOLO/best.pt
```

**Output Columns Added**:
- `is_sunny` - Binary classification result
- `sunny_confidence` - Classifier confidence
- `num_people` - Count of detected people
- `num_shadows` - Count of detected shadows
- `people_in_shade` - Geometric calculation
- `shade_ratio` - people_in_shade / num_people

---

## Model Files

### Pretrained Models

Located in: `outputs/models/`

#### Binary Classifier
- **File**: `vit_binary.pth`
- **Architecture**: Vision Transformer (ViT-B/16)
- **Classes**: [sunny, shade]
- **Input size**: 224x224

#### YOLO Models
- **Best weights**: `YOLO/best.pt`
- **Classes**: [person, shadow]
- **Input size**: 640x640
- **Framework**: Ultralytics YOLOv11

#### Segment Anything Model (SAM2)
- **Directory**: `SAM2/`
- **Purpose**: Advanced segmentation (experimental)
- **Status**: Not actively used in main pipeline

---

## Training Workflows

### Training Binary Classifier

```bash
# 1. Organize images into sunny/shade folders
mkdir -p data/binary_train/{sunny,shade}
# ... move images ...

# 2. Train model
python scripts/ml/binary_image_classification.py \
  --train_dir data/binary_train/ \
  --epochs 30

# 3. Test on sample images
python scripts/ml/binary_image_inference.py \
  --model outputs/models/vit_binary.pth \
  --input_dir test_images/
```

### Training YOLO Detector

```bash
# 1. Prepare dataset
python scripts/ml/prepare_yolo_dataset.py \
  --input raw_annotations/ \
  --output yolo_dataset/

# 2. Train model
python scripts/ml/yolo_train_portable.py \
  --data yolo_dataset/data.yaml \
  --epochs 100

# 3. Evaluate
python scripts/ml/evaluate_yolo_model.py \
  --model outputs/models/YOLO/best.pt \
  --data yolo_dataset/data.yaml

# 4. Run inference
python -c "
from ultralytics import YOLO
model = YOLO('outputs/models/YOLO/best.pt')
results = model('test_image.jpg')
print(results[0].boxes)
"
```

### Fine-tuning on New Data

```bash
# Start from existing weights
python scripts/ml/yolo_train_portable.py \
  --data new_dataset/data.yaml \
  --weights outputs/models/YOLO/best.pt \
  --epochs 50
```

---

## Data Annotation

### Recommended Tools

- **Labelbox**: Web-based, team collaboration
- **Roboflow**: Quick YOLO format export
- **CVAT**: Open-source, powerful
- **Label Studio**: Versatile, supports multiple formats

### Annotation Guidelines

**People Detection**:
- Bounding box around full person (head to feet)
- Include partially visible people
- Minimum visibility: 30% of body

**Shadow Detection**:
- Bounding box around person's shadow
- Must be associated with detected person
- Clear shadow boundary required

---

## Model Performance

### Binary Classifier (Sunny/Shade)
- Training accuracy: ~95%
- Validation accuracy: ~92%
- Inference speed: ~50 images/sec (GPU)

### YOLO Detector (People + Shadows)
- mAP@0.5: ~0.85
- Person detection: Precision ~0.90, Recall ~0.88
- Shadow detection: Precision ~0.75, Recall ~0.70
- Inference speed: ~30 FPS (GPU)

---

## Hardware Requirements

### Training
- **GPU**: NVIDIA GPU with 8GB+ VRAM (RTX 3070 or better)
- **RAM**: 16GB+ recommended
- **Storage**: 50GB+ for datasets and models

### Inference
- **GPU**: Optional, but 10x faster than CPU
- **CPU inference**: Possible but slow (~2 images/sec)

---

## Troubleshooting

### CUDA Out of Memory
- Reduce batch size
- Use smaller image size
- Enable gradient accumulation

### Low mAP Scores
- Check annotation quality
- Increase dataset size
- Adjust augmentation parameters
- Train for more epochs

### Slow Training
- Use GPU instead of CPU
- Increase batch size (if memory allows)
- Reduce image resolution
- Use mixed precision training

### Poor Generalization
- Add more diverse training data
- Increase augmentation
- Use regularization (dropout, weight decay)
- Collect data from multiple cities/conditions

---

## Advanced Topics

### Custom YOLO Architectures

Modify `yolo_train_portable.py` to use different YOLO versions:

```python
from ultralytics import YOLO

# YOLOv8
model = YOLO('yolov8n.pt')

# YOLOv11 (current)
model = YOLO('yolo11n.pt')

# Custom architecture
model = YOLO('custom_config.yaml')
```

### Ensemble Models

Combine multiple models for better accuracy:
- Multiple YOLO models (different architectures)
- Binary classifier + YOLO confidence thresholds
- Temporal consistency (video sequences)

### Active Learning

Iteratively improve models:
1. Run inference on new data
2. Identify low-confidence predictions
3. Manually annotate uncertain cases
4. Retrain with expanded dataset
