#!/usr/bin/env python3
# ABOUTME: Calculate per-class recall using YOLO validation dataset with ground truth
# ABOUTME: Answers: Does YOLO detect in-shade and out-shade people at equal rates?

from ultralytics import YOLO
from pathlib import Path
import numpy as np
from collections import defaultdict
import matplotlib.pyplot as plt

print("="*80)
print("PER-CLASS RECALL ANALYSIS USING TRAINING DATASET")
print("="*80)
print()

# Paths
DATASET_ROOT = Path("/home/kieran/Documents/Python/sunny_day_SVI/data/raw/city7sample/images_to_label/batch2/sunny_batch_from_json")
VAL_IMAGES = DATASET_ROOT / "images" / "val"
VAL_LABELS = DATASET_ROOT / "labels" / "val"
MODEL_PATH = Path("outputs/models/sunny_batch_train6/weights/best.pt")

# Class names
CLASS_NAMES = {0: 'person', 1: 'inshade', 2: 'outshade'}

print(f"Dataset root: {DATASET_ROOT}")
print(f"Validation images: {VAL_IMAGES}")
print(f"Validation labels: {VAL_LABELS}")
print(f"Model: {MODEL_PATH}")
print()

# Check paths exist
if not VAL_IMAGES.exists():
    print(f"ERROR: Validation images not found at {VAL_IMAGES}")
    exit(1)

if not VAL_LABELS.exists():
    print(f"ERROR: Validation labels not found at {VAL_LABELS}")
    exit(1)

if not MODEL_PATH.exists():
    print(f"ERROR: Model not found at {MODEL_PATH}")
    exit(1)

# Load model
print("Loading YOLO model...")
model = YOLO(str(MODEL_PATH))
print("✓ Model loaded")
print()

# Get all validation images
val_image_files = sorted(VAL_IMAGES.glob("*.jpg")) + sorted(VAL_IMAGES.glob("*.jpeg")) + sorted(VAL_IMAGES.glob("*.png"))
print(f"Found {len(val_image_files)} validation images")
print()

# ============================================================================
# 1. PARSE GROUND TRUTH LABELS
# ============================================================================

print("="*80)
print("1. PARSING GROUND TRUTH LABELS")
print("="*80)
print()

ground_truth = defaultdict(list)  # image_name -> list of (class_id, bbox)

for image_file in val_image_files:
    label_file = VAL_LABELS / (image_file.stem + ".txt")

    if label_file.exists():
        with open(label_file, 'r') as f:
            for line in f:
                parts = line.strip().split()
                if len(parts) == 9:  # Polygon format: class x1 y1 x2 y2 x3 y3 x4 y4
                    class_id = int(parts[0])
                    # Convert polygon to bounding box (xywh)
                    polygon_x = [float(parts[i]) for i in [1, 3, 5, 7]]
                    polygon_y = [float(parts[i]) for i in [2, 4, 6, 8]]
                    x_min, x_max = min(polygon_x), max(polygon_x)
                    y_min, y_max = min(polygon_y), max(polygon_y)
                    x_center = (x_min + x_max) / 2
                    y_center = (y_min + y_max) / 2
                    width = x_max - x_min
                    height = y_max - y_min
                    bbox = [x_center, y_center, width, height]
                    ground_truth[image_file.name].append((class_id, bbox))
                elif len(parts) >= 5:  # Standard bbox format: class x y w h
                    class_id = int(parts[0])
                    bbox = [float(x) for x in parts[1:5]]
                    ground_truth[image_file.name].append((class_id, bbox))

# Count ground truth instances per class
gt_counts = defaultdict(int)
for image_name, annotations in ground_truth.items():
    for class_id, bbox in annotations:
        gt_counts[class_id] += 1

print("Ground Truth Counts:")
for class_id in sorted(gt_counts.keys()):
    print(f"  {CLASS_NAMES[class_id]}: {gt_counts[class_id]}")
print(f"  Total: {sum(gt_counts.values())}")
print()

# ============================================================================
# 2. RUN YOLO PREDICTIONS
# ============================================================================

print("="*80)
print("2. RUNNING YOLO PREDICTIONS")
print("="*80)
print()

predictions = {}  # image_name -> list of (class_id, bbox, conf)

print(f"Processing {len(val_image_files)} images...")
for i, image_file in enumerate(val_image_files):
    if (i + 1) % 20 == 0:
        print(f"  Processed {i+1}/{len(val_image_files)}...")

    results = model(str(image_file), verbose=False)

    pred_list = []
    for result in results:
        if result.boxes is not None:
            for box in result.boxes:
                class_id = int(box.cls.item())
                bbox_xyxy = box.xyxy[0].cpu().numpy()
                conf = box.conf.item()

                # Convert xyxy to xywh (normalized)
                img_h, img_w = result.orig_shape
                x1, y1, x2, y2 = bbox_xyxy
                x_center = ((x1 + x2) / 2) / img_w
                y_center = ((y1 + y2) / 2) / img_h
                width = (x2 - x1) / img_w
                height = (y2 - y1) / img_h

                pred_list.append((class_id, [x_center, y_center, width, height], conf))

    predictions[image_file.name] = pred_list

print(f"✓ Completed predictions")
print()

# Count predicted instances per class
pred_counts = defaultdict(int)
for image_name, preds in predictions.items():
    for class_id, bbox, conf in preds:
        pred_counts[class_id] += 1

print("Predicted Counts:")
for class_id in sorted(pred_counts.keys()):
    print(f"  {CLASS_NAMES[class_id]}: {pred_counts[class_id]}")
print(f"  Total: {sum(pred_counts.values())}")
print()

# ============================================================================
# 3. CALCULATE MATCHES (IoU >= 0.5)
# ============================================================================

print("="*80)
print("3. MATCHING PREDICTIONS TO GROUND TRUTH")
print("="*80)
print()

def calculate_iou(box1, box2):
    """Calculate IoU between two boxes in xywh format."""
    # Convert xywh to xyxy
    def xywh_to_xyxy(box):
        x, y, w, h = box
        return [x - w/2, y - h/2, x + w/2, y + h/2]

    box1_xyxy = xywh_to_xyxy(box1)
    box2_xyxy = xywh_to_xyxy(box2)

    # Calculate intersection
    x1 = max(box1_xyxy[0], box2_xyxy[0])
    y1 = max(box1_xyxy[1], box2_xyxy[1])
    x2 = min(box1_xyxy[2], box2_xyxy[2])
    y2 = min(box1_xyxy[3], box2_xyxy[3])

    intersection = max(0, x2 - x1) * max(0, y2 - y1)

    # Calculate union
    box1_area = (box1_xyxy[2] - box1_xyxy[0]) * (box1_xyxy[3] - box1_xyxy[1])
    box2_area = (box2_xyxy[2] - box2_xyxy[0]) * (box2_xyxy[3] - box2_xyxy[1])
    union = box1_area + box2_area - intersection

    return intersection / union if union > 0 else 0

# Match predictions to ground truth
matches_per_class = defaultdict(int)  # class_id -> number of matches
IoU_THRESHOLD = 0.5

for image_name in ground_truth.keys():
    gt_boxes = ground_truth[image_name]
    pred_boxes = predictions.get(image_name, [])

    # Track which GT boxes have been matched
    matched_gt = set()

    # For each prediction, find best matching GT box
    for pred_class, pred_bbox, pred_conf in pred_boxes:
        best_iou = 0
        best_gt_idx = -1
        best_gt_class = None

        for gt_idx, (gt_class, gt_bbox) in enumerate(gt_boxes):
            if gt_idx in matched_gt:
                continue

            # Only match same class
            if gt_class == pred_class:
                iou = calculate_iou(pred_bbox, gt_bbox)
                if iou > best_iou:
                    best_iou = iou
                    best_gt_idx = gt_idx
                    best_gt_class = gt_class

        # If IoU >= 0.5, count as a match
        if best_iou >= IoU_THRESHOLD and best_gt_idx >= 0:
            matches_per_class[pred_class] += 1
            matched_gt.add(best_gt_idx)

print(f"Matches (IoU >= {IoU_THRESHOLD}):")
for class_id in sorted(matches_per_class.keys()):
    print(f"  {CLASS_NAMES[class_id]}: {matches_per_class[class_id]}")
print()

# ============================================================================
# 4. CALCULATE RECALL PER CLASS
# ============================================================================

print("="*80)
print("4. PER-CLASS RECALL")
print("="*80)
print()

recall_per_class = {}
for class_id in gt_counts.keys():
    recall = matches_per_class[class_id] / gt_counts[class_id] if gt_counts[class_id] > 0 else 0
    recall_per_class[class_id] = recall

print("Recall by Class:")
print("-" * 60)
for class_id in sorted(recall_per_class.keys()):
    recall = recall_per_class[class_id]
    print(f"{CLASS_NAMES[class_id]:12s}: {matches_per_class[class_id]:4d} / {gt_counts[class_id]:4d} = {recall:.3f} ({recall*100:.1f}%)")

print()

# Overall recall
total_matches = sum(matches_per_class.values())
total_gt = sum(gt_counts.values())
overall_recall = total_matches / total_gt if total_gt > 0 else 0
print(f"Overall Recall: {total_matches:4d} / {total_gt:4d} = {overall_recall:.3f} ({overall_recall*100:.1f}%)")
print()

# ============================================================================
# 5. COMPARE IN-SHADE VS OUT-SHADE RECALL
# ============================================================================

print("="*80)
print("5. KEY COMPARISON: IN-SHADE VS OUT-SHADE")
print("="*80)
print()

if 1 in recall_per_class and 2 in recall_per_class:
    inshade_recall = recall_per_class[1]
    outshade_recall = recall_per_class[2]
    difference = abs(inshade_recall - outshade_recall)

    print(f"In-shade recall:   {inshade_recall:.3f} ({inshade_recall*100:.1f}%)")
    print(f"Out-shade recall:  {outshade_recall:.3f} ({outshade_recall*100:.1f}%)")
    print(f"Absolute difference: {difference:.3f} ({difference*100:.1f}%)")
    print()

    if difference < 0.05:
        status = "✓ VALID"
        interpretation = "Recall difference < 5% - assumption VALIDATED"
    elif difference < 0.10:
        status = "⚠ MODERATE"
        interpretation = "Recall difference 5-10% - small bias expected"
    else:
        status = "✗ LARGE"
        interpretation = "Recall difference > 10% - significant bias possible"

    print(f"Status: {status}")
    print(f"Interpretation: {interpretation}")
    print()

    # Estimate bias in shade ratio
    print("Estimated Bias in Shade Ratio:")
    print("-" * 60)

    # Assume true ratio = 0.50 for example
    for true_ratio in [0.30, 0.40, 0.50, 0.60, 0.70]:
        observed_ratio = (true_ratio * inshade_recall) / (true_ratio * inshade_recall + (1 - true_ratio) * outshade_recall)
        bias = observed_ratio - true_ratio
        print(f"  True ratio {true_ratio:.2f} → Observed {observed_ratio:.3f} (bias: {bias:+.3f}, {bias/true_ratio*100:+.1f}%)")

    print()

# ============================================================================
# 6. VISUALIZATION
# ============================================================================

print("="*80)
print("6. GENERATING VISUALIZATION")
print("="*80)
print()

fig, axes = plt.subplots(1, 3, figsize=(16, 5))

# Plot 1: Counts comparison
ax = axes[0]
x = np.arange(len(CLASS_NAMES))
width = 0.35

gt_vals = [gt_counts[i] for i in sorted(CLASS_NAMES.keys())]
pred_vals = [pred_counts[i] for i in sorted(CLASS_NAMES.keys())]

ax.bar(x - width/2, gt_vals, width, label='Ground Truth', alpha=0.8, color='steelblue')
ax.bar(x + width/2, pred_vals, width, label='Predicted', alpha=0.8, color='orange')

ax.set_xlabel('Class', fontsize=12)
ax.set_ylabel('Count', fontsize=12)
ax.set_title('Ground Truth vs Predicted Counts', fontsize=13, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels([CLASS_NAMES[i] for i in sorted(CLASS_NAMES.keys())])
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

# Plot 2: Recall by class
ax = axes[1]
recall_vals = [recall_per_class.get(i, 0) for i in sorted(CLASS_NAMES.keys())]
colors = ['gray' if i == 0 else 'green' if i == 1 else 'red' for i in sorted(CLASS_NAMES.keys())]

bars = ax.bar(CLASS_NAMES.values(), recall_vals, alpha=0.7, color=colors, edgecolor='black')

# Add value labels on bars
for bar, val in zip(bars, recall_vals):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height,
            f'{val:.3f}\n({val*100:.1f}%)',
            ha='center', va='bottom', fontsize=10, fontweight='bold')

ax.set_ylabel('Recall', fontsize=12)
ax.set_title(f'Per-Class Recall (IoU ≥ {IoU_THRESHOLD})', fontsize=13, fontweight='bold')
ax.set_ylim(0, 1.0)
ax.grid(True, alpha=0.3, axis='y')
ax.axhline(overall_recall, color='black', linestyle='--', linewidth=1, alpha=0.5, label=f'Overall: {overall_recall:.3f}')
ax.legend()

# Plot 3: In-shade vs Out-shade comparison
ax = axes[2]
if 1 in recall_per_class and 2 in recall_per_class:
    comparison_data = [
        ('In-shade', inshade_recall, 'green'),
        ('Out-shade', outshade_recall, 'red')
    ]

    labels = [d[0] for d in comparison_data]
    values = [d[1] for d in comparison_data]
    colors_comp = [d[2] for d in comparison_data]

    bars = ax.bar(labels, values, alpha=0.7, color=colors_comp, edgecolor='black', linewidth=2)

    # Add value labels
    for bar, val in zip(bars, values):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height,
                f'{val:.3f}\n({val*100:.1f}%)',
                ha='center', va='bottom', fontsize=12, fontweight='bold')

    # Add difference annotation
    ax.plot([0, 1], [inshade_recall, outshade_recall], 'k--', alpha=0.3, linewidth=2)
    mid_y = (inshade_recall + outshade_recall) / 2
    ax.text(0.5, mid_y, f'Δ = {difference:.3f}\n({difference*100:.1f}%)',
            ha='center', va='center', fontsize=11, fontweight='bold',
            bbox=dict(boxstyle='round', facecolor='yellow', alpha=0.7))

    ax.set_ylabel('Recall', fontsize=12)
    ax.set_title('Critical Comparison: In-Shade vs Out-Shade Recall', fontsize=13, fontweight='bold')
    ax.set_ylim(0, 1.0)
    ax.grid(True, alpha=0.3, axis='y')

    # Add status text
    status_text = f"Status: {status}\n{interpretation}"
    ax.text(0.5, 0.05, status_text, ha='center', va='bottom', transform=ax.transAxes,
            fontsize=10, bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8))

plt.tight_layout()
output_file = Path("outputs/model_evaluation/per_class_recall_validation.png")
plt.savefig(output_file, dpi=300, bbox_inches='tight')
plt.close()

print(f"✓ Saved: {output_file}")
print()

# ============================================================================
# SUMMARY AND CONCLUSION
# ============================================================================

print("="*80)
print("CONCLUSION")
print("="*80)
print()

if 1 in recall_per_class and 2 in recall_per_class:
    print(f"In-shade recall:   {inshade_recall*100:.1f}%")
    print(f"Out-shade recall:  {outshade_recall*100:.1f}%")
    print(f"Difference:        {difference*100:.1f}%")
    print()

    if difference < 0.05:
        print("✓ CONCLUSION: Ratio estimator assumption IS VALIDATED")
        print("  Recall rates are very similar (< 5% difference)")
        print("  Systematic bias from differential detection is negligible")
        print("  Safe to use ratio-based metrics throughout analysis")
    elif difference < 0.10:
        print("⚠ CONCLUSION: Ratio estimator assumption MOSTLY VALID")
        print("  Recall rates differ moderately (5-10%)")
        print("  Small bias expected in shade ratio estimates (~2-5%)")
        print("  Aggregate patterns still reliable, but acknowledge limitation")
    else:
        print("✗ CONCLUSION: Ratio estimator assumption VIOLATED")
        print("  Recall rates differ substantially (> 10%)")
        print("  Significant bias in shade ratio estimates")
        print("  Should correct for differential recall or use alternative methods")

print()
print("="*80)
