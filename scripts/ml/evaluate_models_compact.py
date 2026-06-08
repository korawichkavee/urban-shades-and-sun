# ABOUTME: Compact model evaluation script for conference paper
# ABOUTME: Generates current performance metrics and publication-ready figures for YOLO and ViT models

import torch
import torch.nn as nn
from torchvision import models, transforms
from torch.utils.data import DataLoader, random_split
from torchvision.datasets import ImageFolder
from ultralytics import YOLO
from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (confusion_matrix, classification_report,
                              roc_curve, auc, precision_recall_fscore_support)
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# Set random seeds
np.random.seed(42)
torch.manual_seed(42)

# Configuration
VIT_MODEL_PATH = Path("outputs/models/vit_binary.pth")
YOLO_MODEL_PATH = Path("models/yolo_best.pt")
YOLO_VAL_DIR = Path("data/yolo_training_dataset")
VIT_DATA_DIR = Path("data/vit_training_dataset")
OUTPUT_DIR = Path("outputs/model_evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("=" * 80)
print("COMPACT MODEL EVALUATION - CURRENT PERFORMANCE")
print("=" * 80)
print()

# ============================================================================
# 1. EVALUATE VIT BINARY CLASSIFIER
# ============================================================================

print("1. EVALUATING ViT BINARY CLASSIFIER (sunny/not sunny)")
print("-" * 80)

# Load ViT model
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"Device: {device}")

vit_model = models.vit_b_16(pretrained=False)
vit_model.heads = nn.Sequential(
    nn.Linear(vit_model.heads.head.in_features, 1)
)
vit_model.load_state_dict(torch.load(VIT_MODEL_PATH, map_location=device))
vit_model.to(device)
vit_model.eval()
print("✓ ViT model loaded")

# Load ViT dataset and create test split
vit_transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=(0.5, 0.5, 0.5), std=(0.5, 0.5, 0.5))
])

dataset = ImageFolder(VIT_DATA_DIR, transform=vit_transform)
print(f"Total ViT dataset: {len(dataset)} images")
print(f"  Classes: {dataset.classes}")

# Create 80/20 train/test split
train_size = int(0.8 * len(dataset))
test_size = len(dataset) - train_size
_, test_dataset = random_split(dataset, [train_size, test_size],
                                generator=torch.Generator().manual_seed(42))

test_loader = DataLoader(test_dataset, batch_size=32, shuffle=False)
print(f"Test set: {len(test_dataset)} images")

# Evaluate ViT
print("\nEvaluating ViT on test set...")
vit_y_true = []
vit_y_pred = []
vit_y_probs = []

with torch.no_grad():
    for images, labels in tqdm(test_loader, desc="ViT inference"):
        images, labels = images.to(device), labels.to(device)
        outputs = vit_model(images).squeeze(1)
        probs = torch.sigmoid(outputs).cpu().numpy()
        preds = (probs > 0.5).astype(int)

        vit_y_true.extend(labels.cpu().numpy())
        vit_y_pred.extend(preds)
        vit_y_probs.extend(probs)

vit_y_true = np.array(vit_y_true)
vit_y_pred = np.array(vit_y_pred)
vit_y_probs = np.array(vit_y_probs)

# Calculate ViT metrics
vit_precision, vit_recall, vit_f1, _ = precision_recall_fscore_support(
    vit_y_true, vit_y_pred, average='binary', zero_division=0
)
vit_accuracy = (vit_y_true == vit_y_pred).mean()

# Calculate ROC curve
vit_fpr, vit_tpr, vit_thresholds = roc_curve(vit_y_true, vit_y_probs)
vit_auc = auc(vit_fpr, vit_tpr)

print(f"\n✓ ViT Performance:")
print(f"  Accuracy:  {vit_accuracy:.3f}")
print(f"  Precision: {vit_precision:.3f}")
print(f"  Recall:    {vit_recall:.3f}")
print(f"  F1 Score:  {vit_f1:.3f}")
print(f"  AUC:       {vit_auc:.3f}")

# ============================================================================
# 2. EVALUATE YOLO OBJECT DETECTOR
# ============================================================================

print("\n2. EVALUATING YOLO OBJECT DETECTOR (person/inshade/outshade)")
print("-" * 80)

# Load YOLO model
yolo_model = YOLO(str(YOLO_MODEL_PATH))
print("✓ YOLO model loaded")

# Run validation
print("\nRunning YOLO validation...")
val_results = yolo_model.val(data=str(YOLO_VAL_DIR / "data.yaml"),
                              split='val',
                              verbose=False)

# Extract metrics
yolo_map50 = val_results.box.map50  # mAP@0.5
yolo_map = val_results.box.map  # mAP@0.5:0.95
yolo_precision = val_results.box.mp  # mean precision
yolo_recall = val_results.box.mr  # mean recall

print(f"\n✓ YOLO Performance:")
print(f"  mAP@0.5:      {yolo_map50:.3f}")
print(f"  mAP@0.5:0.95: {yolo_map:.3f}")
print(f"  Precision:    {yolo_precision:.3f}")
print(f"  Recall:       {yolo_recall:.3f}")

# ============================================================================
# 3. CREATE COMPACT FIGURES
# ============================================================================

print("\n3. CREATING PUBLICATION-READY FIGURES")
print("-" * 80)

# Create a single compact figure with both model evaluations
fig = plt.figure(figsize=(12, 4.5))
gs = fig.add_gridspec(1, 3, hspace=0.3, wspace=0.4)

# Plot 1: ViT ROC Curve
ax1 = fig.add_subplot(gs[0, 0])
ax1.plot(vit_fpr, vit_tpr, linewidth=2, label=f'ViT (AUC = {vit_auc:.3f})', color='#3498db')
ax1.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.3)
ax1.set_xlabel('False Positive Rate', fontsize=10, fontweight='bold')
ax1.set_ylabel('True Positive Rate', fontsize=10, fontweight='bold')
ax1.set_title('ViT Binary Classifier\nROC Curve', fontsize=11, fontweight='bold')
ax1.legend(loc='lower right', fontsize=9)
ax1.grid(True, alpha=0.3)
ax1.set_xlim([0, 1])
ax1.set_ylim([0, 1])

# Plot 2: ViT Confusion Matrix
ax2 = fig.add_subplot(gs[0, 1])
vit_cm = confusion_matrix(vit_y_true, vit_y_pred)
sns.heatmap(vit_cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['Not Sunny', 'Sunny'],
            yticklabels=['Not Sunny', 'Sunny'],
            ax=ax2, cbar_kws={'label': 'Count'})
ax2.set_xlabel('Predicted', fontsize=10, fontweight='bold')
ax2.set_ylabel('True', fontsize=10, fontweight='bold')
ax2.set_title(f'ViT Confusion Matrix\nAccuracy: {vit_accuracy:.3f}',
              fontsize=11, fontweight='bold')

# Plot 3: YOLO Performance Bar Chart
ax3 = fig.add_subplot(gs[0, 2])
metrics = ['mAP@0.5', 'mAP@\n0.5:0.95', 'Precision', 'Recall']
values = [yolo_map50, yolo_map, yolo_precision, yolo_recall]
colors = ['#2ecc71', '#3498db', '#f39c12', '#e74c3c']

bars = ax3.bar(range(len(metrics)), values, color=colors, alpha=0.8, edgecolor='black')
ax3.set_xticks(range(len(metrics)))
ax3.set_xticklabels(metrics, fontsize=9)
ax3.set_ylabel('Score', fontsize=10, fontweight='bold')
ax3.set_title('YOLO Object Detector\nPerformance Metrics',
              fontsize=11, fontweight='bold')
ax3.set_ylim([0, 1])
ax3.grid(True, alpha=0.3, axis='y')

# Add value labels on bars
for bar, value in zip(bars, values):
    height = bar.get_height()
    ax3.text(bar.get_x() + bar.get_width()/2., height + 0.02,
             f'{value:.3f}', ha='center', va='bottom', fontsize=8, fontweight='bold')

plt.tight_layout()

# Save figure
output_path = OUTPUT_DIR / "model_performance_compact.png"
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"\n✓ Compact figure saved: {output_path}")

output_path_pdf = OUTPUT_DIR / "model_performance_compact.pdf"
plt.savefig(output_path_pdf, bbox_inches='tight')
print(f"✓ PDF saved: {output_path_pdf}")

plt.close()

# ============================================================================
# 4. SAVE METRICS TO CSV
# ============================================================================

# Create summary table
summary_data = {
    'Model': ['ViT Binary Classifier', 'YOLO Object Detector'],
    'Task': ['Sunny/Not Sunny Classification', 'Person/Shade Detection'],
    'Test Size': [len(test_dataset), 166],
    'Accuracy/mAP@0.5': [f'{vit_accuracy:.3f}', f'{yolo_map50:.3f}'],
    'Precision': [f'{vit_precision:.3f}', f'{yolo_precision:.3f}'],
    'Recall': [f'{vit_recall:.3f}', f'{yolo_recall:.3f}'],
    'F1/mAP@0.5:0.95': [f'{vit_f1:.3f}', f'{yolo_map:.3f}'],
    'AUC': [f'{vit_auc:.3f}', 'N/A']
}

summary_df = pd.DataFrame(summary_data)
summary_path = OUTPUT_DIR / "model_performance_summary.csv"
summary_df.to_csv(summary_path, index=False)
print(f"✓ Summary CSV saved: {summary_path}")

print("\n" + "=" * 80)
print("EVALUATION COMPLETE")
print("=" * 80)
print(f"\nOutputs:")
print(f"  - {output_path}")
print(f"  - {output_path_pdf}")
print(f"  - {summary_path}")
print()
