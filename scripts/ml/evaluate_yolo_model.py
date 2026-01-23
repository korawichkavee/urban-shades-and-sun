#!/usr/bin/env python3
# ABOUTME: Evaluates YOLO model performance with confusion matrix for inshade/outshade classification
# ABOUTME: Loads trained model, runs inference on validation set, and generates confusion matrix visualization

from ultralytics import YOLO
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, classification_report
import seaborn as sns
from collections import defaultdict

# Configuration
SCRIPT_DIR = Path(__file__).parent
DATASET_DIR = SCRIPT_DIR / "city7sample/images_to_label/batch2/sunny_batch_from_json"
MODEL_PATH = SCRIPT_DIR / "runs/detect/sunny_batch_train/weights/best.pt"  # Adjust path as needed
IOU_THRESHOLD = 0.5  # IoU threshold for matching predictions to ground truth
CONF_THRESHOLD = 0.25  # Confidence threshold for predictions

# Class mapping
CLASS_NAMES = {
    0: 'person',
    1: 'inshade',
    2: 'outshade'
}

def parse_polygon_label(label_line):
    """Parse YOLO polygon format label.

    Args:
        label_line: String in format "class_id x1 y1 x2 y2 x3 y3 x4 y4"

    Returns:
        tuple: (class_id, polygon_coords) where polygon_coords is list of [x, y] points
    """
    parts = label_line.strip().split()
    class_id = int(parts[0])
    coords = [float(x) for x in parts[1:]]

    # Convert to list of [x, y] points
    polygon = [[coords[i], coords[i+1]] for i in range(0, len(coords), 2)]

    return class_id, polygon

def polygon_to_bbox(polygon):
    """Convert polygon to bounding box [x_min, y_min, x_max, y_max].

    Args:
        polygon: List of [x, y] points (normalized 0-1)

    Returns:
        list: [x_min, y_min, x_max, y_max] (normalized 0-1)
    """
    xs = [p[0] for p in polygon]
    ys = [p[1] for p in polygon]
    return [min(xs), min(ys), max(xs), max(ys)]

def calculate_iou(box1, box2):
    """Calculate IoU between two bounding boxes.

    Args:
        box1, box2: [x_min, y_min, x_max, y_max] in normalized coordinates

    Returns:
        float: IoU score
    """
    x1_min, y1_min, x1_max, y1_max = box1
    x2_min, y2_min, x2_max, y2_max = box2

    # Calculate intersection
    x_inter_min = max(x1_min, x2_min)
    y_inter_min = max(y1_min, y2_min)
    x_inter_max = min(x1_max, x2_max)
    y_inter_max = min(y1_max, y2_max)

    if x_inter_max < x_inter_min or y_inter_max < y_inter_min:
        return 0.0

    intersection = (x_inter_max - x_inter_min) * (y_inter_max - y_inter_min)

    # Calculate union
    area1 = (x1_max - x1_min) * (y1_max - y1_min)
    area2 = (x2_max - x2_min) * (y2_max - y2_min)
    union = area1 + area2 - intersection

    return intersection / union if union > 0 else 0.0

def load_ground_truth_labels(label_file):
    """Load ground truth labels from file.

    Args:
        label_file: Path to label txt file

    Returns:
        list: List of (class_id, bbox) tuples
    """
    labels = []
    if not label_file.exists():
        return labels

    with open(label_file, 'r') as f:
        for line in f:
            if line.strip():
                class_id, polygon = parse_polygon_label(line)
                bbox = polygon_to_bbox(polygon)
                labels.append((class_id, bbox))

    return labels

def match_predictions_to_ground_truth(pred_boxes, gt_boxes, iou_threshold=0.5):
    """Match predicted boxes to ground truth boxes using IoU.

    Args:
        pred_boxes: List of (class_id, bbox, confidence) tuples
        gt_boxes: List of (class_id, bbox) tuples
        iou_threshold: Minimum IoU for a match

    Returns:
        tuple: (matched_pairs, unmatched_preds, unmatched_gts)
            matched_pairs: List of (pred_class, gt_class) tuples
            unmatched_preds: List of pred_class values (false positives)
            unmatched_gts: List of gt_class values (false negatives)
    """
    matched_pairs = []
    matched_gt_indices = set()
    unmatched_preds = []

    # For each prediction, find best matching ground truth
    for pred_class, pred_bbox, pred_conf in pred_boxes:
        best_iou = 0
        best_gt_idx = -1

        for gt_idx, (gt_class, gt_bbox) in enumerate(gt_boxes):
            if gt_idx in matched_gt_indices:
                continue

            iou = calculate_iou(pred_bbox, gt_bbox)
            if iou > best_iou:
                best_iou = iou
                best_gt_idx = gt_idx

        if best_iou >= iou_threshold:
            gt_class, _ = gt_boxes[best_gt_idx]
            matched_pairs.append((pred_class, gt_class))
            matched_gt_indices.add(best_gt_idx)
        else:
            # False positive
            unmatched_preds.append(pred_class)

    # Find unmatched ground truths (false negatives)
    unmatched_gts = [gt_class for idx, (gt_class, _) in enumerate(gt_boxes)
                     if idx not in matched_gt_indices]

    return matched_pairs, unmatched_preds, unmatched_gts

def evaluate_model(model_path, dataset_dir, iou_threshold=0.5, conf_threshold=0.25):
    """Evaluate YOLO model on validation set.

    Args:
        model_path: Path to trained model weights
        dataset_dir: Path to dataset root directory
        iou_threshold: IoU threshold for matching
        conf_threshold: Confidence threshold for predictions

    Returns:
        tuple: (y_true, y_pred) lists of class labels
    """
    # Load model
    print(f"Loading model from: {model_path}")
    model = YOLO(str(model_path))

    # Get validation images
    val_images_dir = dataset_dir / "images/val"
    val_labels_dir = dataset_dir / "labels/val"

    if not val_images_dir.exists():
        raise ValueError(f"Validation images directory not found: {val_images_dir}")

    image_files = sorted(val_images_dir.glob("*.jpeg"))
    print(f"\nFound {len(image_files)} validation images")

    # Collect all predictions and ground truths
    y_true = []
    y_pred = []

    # Statistics
    total_gt = 0
    total_pred = 0
    total_matched = 0

    print("\nRunning inference on validation set...")
    for img_file in image_files:
        # Load ground truth
        label_file = val_labels_dir / f"{img_file.stem}.txt"
        gt_boxes = load_ground_truth_labels(label_file)
        total_gt += len(gt_boxes)

        # Run prediction
        results = model.predict(str(img_file), conf=conf_threshold, verbose=False)

        # Extract predictions
        pred_boxes = []
        if len(results) > 0 and results[0].boxes is not None:
            boxes = results[0].boxes
            for i in range(len(boxes)):
                class_id = int(boxes.cls[i].item())
                confidence = float(boxes.conf[i].item())

                # Get normalized bbox coordinates
                # boxes.xywhn gives [x_center, y_center, width, height] normalized
                xywhn = boxes.xywhn[i].cpu().numpy()
                x_center, y_center, width, height = xywhn

                # Convert to [x_min, y_min, x_max, y_max]
                x_min = x_center - width / 2
                y_min = y_center - height / 2
                x_max = x_center + width / 2
                y_max = y_center + height / 2

                pred_boxes.append((class_id, [x_min, y_min, x_max, y_max], confidence))

        total_pred += len(pred_boxes)

        # Match predictions to ground truth
        matched_pairs, unmatched_preds, unmatched_gts = match_predictions_to_ground_truth(
            pred_boxes, gt_boxes, iou_threshold
        )

        total_matched += len(matched_pairs)

        # Add matched pairs to confusion matrix data
        for pred_class, gt_class in matched_pairs:
            y_true.append(gt_class)
            y_pred.append(pred_class)

        # Add false negatives (missed detections)
        # For confusion matrix, we count these as predictions of class 0 (background/person)
        for gt_class in unmatched_gts:
            y_true.append(gt_class)
            y_pred.append(0)  # Missed detection

    print(f"\nEvaluation Statistics:")
    print(f"  Total ground truth boxes: {total_gt}")
    print(f"  Total predictions: {total_pred}")
    print(f"  Matched (IoU >= {iou_threshold}): {total_matched}")
    print(f"  Precision: {total_matched/total_pred*100:.2f}%" if total_pred > 0 else "  Precision: N/A")
    print(f"  Recall: {total_matched/total_gt*100:.2f}%" if total_gt > 0 else "  Recall: N/A")

    return y_true, y_pred

def plot_confusion_matrix(y_true, y_pred, class_names, save_path=None):
    """Plot confusion matrix with visualization.

    Args:
        y_true: List of true class labels
        y_pred: List of predicted class labels
        class_names: Dict mapping class IDs to names
        save_path: Optional path to save figure
    """
    # Get unique classes that appear in data
    unique_classes = sorted(set(y_true + y_pred))
    labels = [class_names.get(c, f'class_{c}') for c in unique_classes]

    # Compute confusion matrix
    cm = confusion_matrix(y_true, y_pred, labels=unique_classes)

    # Create figure
    fig, ax = plt.subplots(figsize=(10, 8))

    # Plot heatmap
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=labels, yticklabels=labels,
                ax=ax, cbar_kws={'label': 'Count'})

    ax.set_xlabel('Predicted Class', fontsize=12)
    ax.set_ylabel('True Class', fontsize=12)
    ax.set_title('Confusion Matrix - YOLO Shade Classification', fontsize=14, pad=20)

    # Add accuracy text
    accuracy = np.trace(cm) / np.sum(cm) * 100 if np.sum(cm) > 0 else 0
    plt.text(0.5, -0.15, f'Overall Accuracy: {accuracy:.2f}%',
             ha='center', va='center', transform=ax.transAxes, fontsize=12)

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"\nConfusion matrix saved to: {save_path}")

    plt.show()

    return cm

def print_classification_report(y_true, y_pred, class_names):
    """Print detailed classification report.

    Args:
        y_true: List of true class labels
        y_pred: List of predicted class labels
        class_names: Dict mapping class IDs to names
    """
    # Get unique classes
    unique_classes = sorted(set(y_true + y_pred))
    target_names = [class_names.get(c, f'class_{c}') for c in unique_classes]

    print("\n" + "="*60)
    print("Classification Report")
    print("="*60)
    print(classification_report(y_true, y_pred, labels=unique_classes,
                                target_names=target_names, digits=4))

def main():
    print("="*60)
    print("YOLO Model Evaluation - Confusion Matrix")
    print("="*60)

    # Check if model exists
    if not MODEL_PATH.exists():
        print(f"\nERROR: Model not found at {MODEL_PATH}")
        print("\nPlease update MODEL_PATH in the script to point to your trained model.")
        print("Common locations:")
        print("  - runs/detect/sunny_batch_train/weights/best.pt")
        print("  - runs/detect/sunny_batch_train2/weights/best.pt")
        return

    # Check if dataset exists
    if not DATASET_DIR.exists():
        print(f"\nERROR: Dataset not found at {DATASET_DIR}")
        print("\nPlease update DATASET_DIR in the script.")
        return

    # Evaluate model
    y_true, y_pred = evaluate_model(
        MODEL_PATH,
        DATASET_DIR,
        iou_threshold=IOU_THRESHOLD,
        conf_threshold=CONF_THRESHOLD
    )

    if len(y_true) == 0:
        print("\nWARNING: No predictions matched to ground truth.")
        print("This could mean:")
        print("  1. Model predictions are very poor (low IoU)")
        print("  2. Confidence threshold is too high")
        print("  3. No predictions were made")
        return

    # Print classification report
    print_classification_report(y_true, y_pred, CLASS_NAMES)

    # Plot confusion matrix
    save_path = SCRIPT_DIR / "confusion_matrix.png"
    cm = plot_confusion_matrix(y_true, y_pred, CLASS_NAMES, save_path)

    print("\n" + "="*60)
    print("Evaluation Complete!")
    print("="*60)

if __name__ == "__main__":
    main()
