#!/usr/bin/env python3
# ABOUTME: Evaluate ViT and YOLO models, create sample visualizations from each city
# ABOUTME: Generates AUC/accuracy plots and annotated sample images with predictions

import torch
import torch.nn as nn
from torchvision import models, transforms
from ultralytics import YOLO
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import roc_curve, auc, confusion_matrix, classification_report
from tqdm import tqdm
import random
import warnings
warnings.filterwarnings('ignore')

# Set random seeds
random.seed(42)
np.random.seed(42)
torch.manual_seed(42)

# Configuration
VIT_MODEL_PATH = "outputs/models/vit_binary.pth"
YOLO_MODEL_PATH = "models/yolo_best.pt"
OUTPUT_DIR = Path("outputs/model_evaluation")
SAMPLES_DIR = OUTPUT_DIR / "sample_images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

SAMPLES_PER_CITY = 5  # Number of sample images per category per city

# Cities to sample from
CITIES = [
    "Buenos-Aires",
    "Cape-Town",
    "Istanbul",
    "Madrid",
    "Mumbai",
    "Osaka",
    "Singapore"
]

print("=" * 80)
print("MODEL EVALUATION AND VISUALIZATION")
print("=" * 80)
print()

# ============================================================================
# 1. LOAD MODELS
# ============================================================================

print("Loading models...")
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"  Device: {device}")

# Load ViT model
print("  Loading ViT binary classification model...")
vit_model = models.vit_b_16(pretrained=False)
vit_model.heads = nn.Sequential(
    nn.Linear(vit_model.heads.head.in_features, 1)
)
vit_model.load_state_dict(torch.load(VIT_MODEL_PATH, map_location=device))
vit_model.to(device)
vit_model.eval()
print("    ✓ ViT model loaded")

vit_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))
])

# Load YOLO model
print("  Loading YOLO shade detection model...")
yolo_model = YOLO(YOLO_MODEL_PATH)
yolo_class_names = {0: 'person', 1: 'inshade', 2: 'outshade'}
print("    ✓ YOLO model loaded")
print()

# ============================================================================
# 2. LOAD CITY DATA
# ============================================================================

print("Loading city data...")
city_data = {}
for city in CITIES:
    csv_path = Path(f"data/multi_city_results/{city}/{city}_analyzed_with_utci.csv")
    if csv_path.exists():
        df = pd.read_csv(csv_path, low_memory=False)
        city_data[city] = df
        print(f"  {city}: {len(df):,} observations")
    else:
        print(f"  {city}: CSV not found")

print(f"\n  Total cities loaded: {len(city_data)}")
print()

# ============================================================================
# 3. EXTRACT SAMPLE IMAGES FROM EACH CITY
# ============================================================================

print("Extracting and annotating sample images from each city...")
print()

def classify_sunny(image_path):
    """Classify image as sunny/not sunny with ViT."""
    try:
        img = Image.open(image_path).convert("RGB")
        x = vit_transform(img).unsqueeze(0).to(device)

        with torch.no_grad():
            output = vit_model(x).squeeze(1)
            prob = torch.sigmoid(output).item()
            is_sunny = prob > 0.5

        return is_sunny, prob
    except Exception as e:
        print(f"    Error classifying {image_path}: {e}")
        return None, None

def detect_shade(image_path):
    """Detect people and shade with YOLO."""
    counts = {'person': 0, 'inshade': 0, 'outshade': 0}
    boxes_data = []

    try:
        results = yolo_model(image_path, verbose=False)

        for result in results:
            if result.boxes is not None:
                for box in result.boxes:
                    class_id = int(box.cls.item())
                    class_name = yolo_class_names.get(class_id, 'unknown')
                    if class_name in counts:
                        counts[class_name] += 1

                        # Store box coordinates for visualization
                        xyxy = box.xyxy[0].cpu().numpy()
                        conf = box.conf.item()
                        boxes_data.append({
                            'class': class_name,
                            'bbox': xyxy,
                            'conf': conf
                        })
    except Exception as e:
        print(f"    Error detecting shade in {image_path}: {e}")

    return counts, boxes_data

def annotate_image(image_path, is_sunny, sunny_prob, shade_counts, boxes_data,
                    utci_c, datetime_local, city_name):
    """Create annotated version of image with predictions and metadata."""
    try:
        # Load image
        img = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(img)

        # Try to load a font
        try:
            title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 24)
            label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 16)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 14)
        except:
            title_font = ImageFont.load_default()
            label_font = ImageFont.load_default()
            small_font = ImageFont.load_default()

        # Draw bounding boxes for YOLO detections
        colors = {
            'person': (255, 255, 0),  # Yellow
            'inshade': (0, 255, 0),   # Green
            'outshade': (255, 0, 0)   # Red
        }

        for box_info in boxes_data:
            bbox = box_info['bbox']
            class_name = box_info['class']
            conf = box_info['conf']
            color = colors.get(class_name, (255, 255, 255))

            # Draw rectangle
            draw.rectangle(
                [(bbox[0], bbox[1]), (bbox[2], bbox[3])],
                outline=color,
                width=3
            )

            # Draw label
            label = f"{class_name} {conf:.2f}"
            draw.text((bbox[0], bbox[1] - 20), label, fill=color, font=small_font)

        # Calculate shade preference
        n_total = shade_counts['inshade'] + shade_counts['outshade']
        if n_total > 0:
            shade_pref = shade_counts['inshade'] / n_total
        else:
            shade_pref = 0

        # Add title bar with metadata
        width, height = img.size
        title_height = 120
        title_img = Image.new('RGB', (width, title_height), color=(0, 0, 0))
        title_draw = ImageDraw.Draw(title_img)

        # Parse datetime
        try:
            dt = pd.to_datetime(datetime_local)
            date_str = dt.strftime('%Y-%m-%d')
            time_str = dt.strftime('%H:%M')
        except:
            date_str = "N/A"
            time_str = "N/A"

        # Title text
        title_lines = [
            f"{city_name} | {date_str} {time_str}",
            f"Sunny: {'Yes' if is_sunny else 'No'} ({sunny_prob:.2f}) | UTCI: {utci_c:.1f}°C" if not pd.isna(utci_c) else f"Sunny: {'Yes' if is_sunny else 'No'} ({sunny_prob:.2f})",
            f"People: {shade_counts['person']} | In Shade: {shade_counts['inshade']} | Out Shade: {shade_counts['outshade']} | Shade Pref: {shade_pref:.2f}"
        ]

        y_offset = 10
        for line in title_lines:
            title_draw.text((10, y_offset), line, fill=(255, 255, 255), font=label_font)
            y_offset += 35

        # Combine title and image
        final_img = Image.new('RGB', (width, height + title_height))
        final_img.paste(title_img, (0, 0))
        final_img.paste(img, (0, title_height))

        return final_img

    except Exception as e:
        print(f"    Error annotating {image_path}: {e}")
        return None

# Process each city
for city_name in tqdm(CITIES, desc="Processing cities"):
    if city_name not in city_data:
        continue

    df_city = city_data[city_name]

    # Skip if no image directory
    img_dir = Path(f"data/multi_city_results/{city_name}/{city_name}img/walkable_images")
    if not img_dir.exists():
        print(f"  Skipping {city_name}: No image directory found")
        continue

    # Filter to only sunny images with people
    df_sunny = df_city[
        (df_city['is_sunny'] == True) &
        ((df_city['inshade_count'] > 0) | (df_city['outshade_count'] > 0))
    ].copy()

    df_not_sunny = df_city[df_city['is_sunny'] == False].copy()

    # Sample images
    categories = [
        ("sunny", df_sunny),
        ("not_sunny", df_not_sunny)
    ]

    for category_name, df_cat in categories:
        if len(df_cat) == 0:
            continue

        # Sample up to SAMPLES_PER_CITY
        n_samples = min(SAMPLES_PER_CITY, len(df_cat))
        sampled = df_cat.sample(n=n_samples, random_state=42)

        for idx, (_, row) in enumerate(sampled.iterrows(), 1):
            image_id = row['id']
            image_path = img_dir / f"{image_id}.jpeg"

            if not image_path.exists():
                image_path = img_dir / f"{image_id}.jpg"

            if not image_path.exists():
                continue

            # Get predictions
            is_sunny, sunny_prob = classify_sunny(image_path)
            if is_sunny is None:
                continue

            shade_counts, boxes_data = detect_shade(image_path)

            # Get metadata
            utci_c = row.get('utci_C', np.nan)
            datetime_local = row.get('datetime-local', 'N/A')

            # Create annotated image
            annotated = annotate_image(
                image_path, is_sunny, sunny_prob, shade_counts, boxes_data,
                utci_c, datetime_local, city_name
            )

            if annotated is not None:
                output_path = SAMPLES_DIR / f"{city_name}_{category_name}_{idx}.png"
                annotated.save(output_path)

print()
print(f"✓ Sample images saved to: {SAMPLES_DIR}")
print()

# ============================================================================
# 4. READ YOLO TRAINING RESULTS
# ============================================================================

print("Reading YOLO training results...")
yolo_results = pd.read_csv("outputs/models/sunny_batch_train6/results.csv")
print(f"  Loaded {len(yolo_results)} epochs")
print()

# ============================================================================
# 5. CREATE EVALUATION PLOTS
# ============================================================================

print("Creating evaluation plots...")

# Plot 1: YOLO Training Curves
fig, axes = plt.subplots(2, 2, figsize=(16, 12))

# mAP curves
ax = axes[0, 0]
ax.plot(yolo_results['epoch'], yolo_results['metrics/mAP50(B)'],
        label='mAP@0.5', linewidth=2, marker='o', markersize=3)
ax.plot(yolo_results['epoch'], yolo_results['metrics/mAP50-95(B)'],
        label='mAP@0.5:0.95', linewidth=2, marker='s', markersize=3)
ax.set_xlabel('Epoch', fontsize=12)
ax.set_ylabel('mAP', fontsize=12)
ax.set_title('YOLO Model - Mean Average Precision', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)

# Precision and Recall
ax = axes[0, 1]
ax.plot(yolo_results['epoch'], yolo_results['metrics/precision(B)'],
        label='Precision', linewidth=2, marker='o', markersize=3, color='green')
ax.plot(yolo_results['epoch'], yolo_results['metrics/recall(B)'],
        label='Recall', linewidth=2, marker='s', markersize=3, color='blue')
ax.set_xlabel('Epoch', fontsize=12)
ax.set_ylabel('Score', fontsize=12)
ax.set_title('YOLO Model - Precision and Recall', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)

# Loss curves
ax = axes[1, 0]
ax.plot(yolo_results['epoch'], yolo_results['train/box_loss'],
        label='Box Loss (train)', linewidth=2, alpha=0.7)
ax.plot(yolo_results['epoch'], yolo_results['train/cls_loss'],
        label='Class Loss (train)', linewidth=2, alpha=0.7)
ax.plot(yolo_results['epoch'], yolo_results['train/dfl_loss'],
        label='DFL Loss (train)', linewidth=2, alpha=0.7)
ax.set_xlabel('Epoch', fontsize=12)
ax.set_ylabel('Loss', fontsize=12)
ax.set_title('YOLO Model - Training Losses', fontsize=14, fontweight='bold')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3)

# Summary stats table
ax = axes[1, 1]
ax.axis('off')

# Get final metrics (last epoch with valid mAP)
valid_results = yolo_results.dropna(subset=['metrics/mAP50(B)'])
if len(valid_results) > 0:
    final = valid_results.iloc[-1]

    summary_text = f"""
YOLO Model - Final Performance
{'=' * 45}

Training completed: {len(yolo_results)} epochs

Final Metrics (Epoch {int(final['epoch'])}):
  mAP@0.5:          {final['metrics/mAP50(B)']:.3f}
  mAP@0.5:0.95:     {final['metrics/mAP50-95(B)']:.3f}
  Precision:        {final['metrics/precision(B)']:.3f}
  Recall:           {final['metrics/recall(B)']:.3f}

Training Losses (final):
  Box Loss:         {final['train/box_loss']:.4f}
  Class Loss:       {final['train/cls_loss']:.4f}
  DFL Loss:         {final['train/dfl_loss']:.4f}

Validation Losses (final):
  Box Loss:         {final.get('val/box_loss', 'N/A')}
  Class Loss:       {final.get('val/cls_loss', 'N/A')}
  DFL Loss:         {final.get('val/dfl_loss', 'N/A')}

Classes: person, inshade, outshade
    """
else:
    summary_text = "No valid YOLO metrics found"

ax.text(0.05, 0.95, summary_text, transform=ax.transAxes,
        fontsize=11, verticalalignment='top', family='monospace',
        bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "yolo_training_evaluation.png", dpi=300, bbox_inches='tight')
plt.close()
print("  ✓ YOLO evaluation plot saved")

# Plot 2: ViT Training Results (from log)
print("  Parsing ViT training log...")
vit_log_path = Path("logs/vit_training.log")

if vit_log_path.exists():
    with open(vit_log_path, 'r') as f:
        log_text = f.read()

    # Parse fold results
    import re
    fold_pattern = r'Fold (\d+), Epoch (\d+), Loss: ([\d.]+), Val Acc: ([\d.]+)'
    matches = re.findall(fold_pattern, log_text)

    if matches:
        vit_results = []
        for fold, epoch, loss, val_acc in matches:
            vit_results.append({
                'fold': int(fold),
                'epoch': int(epoch),
                'loss': float(loss),
                'val_acc': float(val_acc)
            })

        df_vit = pd.DataFrame(vit_results)

        # Create ViT evaluation plot
        fig, axes = plt.subplots(1, 2, figsize=(16, 6))

        # Training loss by fold
        ax = axes[0]
        for fold in sorted(df_vit['fold'].unique()):
            fold_data = df_vit[df_vit['fold'] == fold]
            ax.plot(fold_data['epoch'], fold_data['loss'],
                    label=f'Fold {fold}', linewidth=2, marker='o', markersize=4)

        ax.set_xlabel('Epoch', fontsize=12)
        ax.set_ylabel('Loss', fontsize=12)
        ax.set_title('ViT Binary Classifier - Training Loss', fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)

        # Validation accuracy by fold
        ax = axes[1]
        for fold in sorted(df_vit['fold'].unique()):
            fold_data = df_vit[df_vit['fold'] == fold]
            ax.plot(fold_data['epoch'], fold_data['val_acc'],
                    label=f'Fold {fold}', linewidth=2, marker='s', markersize=4)

        ax.set_xlabel('Epoch', fontsize=12)
        ax.set_ylabel('Validation Accuracy', fontsize=12)
        ax.set_title('ViT Binary Classifier - Validation Accuracy', fontsize=14, fontweight='bold')
        ax.legend(fontsize=11)
        ax.grid(True, alpha=0.3)
        ax.set_ylim([0.85, 1.0])

        plt.tight_layout()
        plt.savefig(OUTPUT_DIR / "vit_training_evaluation.png", dpi=300, bbox_inches='tight')
        plt.close()
        print("  ✓ ViT evaluation plot saved")

        # Print summary
        print()
        print("ViT Training Summary:")
        print(f"  Average final validation accuracy: {df_vit.groupby('fold')['val_acc'].last().mean():.3f}")
        print(f"  Best validation accuracy: {df_vit['val_acc'].max():.3f}")
    else:
        print("  Could not parse ViT training log")
else:
    print("  ViT training log not found")

print()
print("=" * 80)
print("✓ EVALUATION COMPLETE")
print("=" * 80)
print(f"\nOutputs saved to: {OUTPUT_DIR}")
print(f"  - yolo_training_evaluation.png")
print(f"  - vit_training_evaluation.png")
print(f"  - sample_images/ (annotated samples from each city)")
print()
