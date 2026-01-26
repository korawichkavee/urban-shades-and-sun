# Model Evaluation Summary

**Date:** 2026-01-26
**Models Evaluated:** ViT Binary Classifier (Sunny/Not Sunny) + YOLO Shade Detection

---

## Overview

This document summarizes the performance of the two ML models used in the Sunny Day SVI analysis pipeline:
1. **ViT Binary Classifier** - Determines if street view images are sunny or not sunny
2. **YOLO Object Detector** - Detects people and classifies them as in-shade or out-of-shade

---

## 1. ViT Binary Classifier (Sunny/Not Sunny)

### Model Architecture
- **Base Model:** Vision Transformer (ViT-B/16) pretrained on ImageNet
- **Task:** Binary classification (sunny vs not sunny)
- **Training:** 5-fold cross-validation, 5 epochs per fold
- **Input:** 224x224 RGB images
- **Output:** Binary prediction + probability

### Performance Metrics

**Cross-Validation Results:**
- **Average Final Validation Accuracy:** 92.3%
- **Best Validation Accuracy:** 95.4% (Fold 2, Epoch 4)
- **Training Loss Convergence:** Rapid convergence from ~0.35 → 0.03-0.04 by epoch 5

**Per-Fold Performance (Final Epoch):**
- Fold 1: 92.6% accuracy
- Fold 2: 90.1% accuracy
- Fold 3: 93.3% accuracy
- Fold 4: 94.4% accuracy
- Fold 5: 92.0% accuracy

### Key Observations

✅ **Strengths:**
- Very rapid convergence (most learning happens in first 2 epochs)
- Consistent performance across folds (90-95% accuracy)
- Low variance between folds suggests good generalization
- Training loss decreases smoothly without signs of overfitting

⚠️ **Considerations:**
- Some folds show slight overfitting in later epochs (accuracy plateaus or decreases)
- Fold 2 shows early overfitting (95.4% at epoch 4 → 90.1% at epoch 5)
- Could benefit from early stopping or regularization

### Training Characteristics
- **Convergence Speed:** Fast (2-3 epochs to reach plateau)
- **Stability:** Stable across folds
- **Overfitting Risk:** Moderate (some folds peak before final epoch)

---

## 2. YOLO Shade Detection Model

### Model Architecture
- **Base Model:** YOLOv8 (ultralytics)
- **Task:** Multi-class object detection
- **Classes:** 3 classes (person, inshade, outshade)
- **Training:** 259 epochs
- **Input:** Variable size images (auto-resized by YOLO)
- **Output:** Bounding boxes + class predictions + confidence scores

### Performance Metrics (Final Epoch 259)

**Detection Performance:**
- **mAP@0.5:** 63.0% (mean Average Precision at IoU=0.5)
- **mAP@0.5:0.95:** 40.4% (mean Average Precision at IoU=0.5-0.95)
- **Precision:** 78.7%
- **Recall:** 57.9%

**Loss Values (Final):**
- **Box Loss (train):** 0.734
- **Class Loss (train):** 0.472
- **DFL Loss (train):** 0.867
- **Box Loss (val):** 1.263
- **Class Loss (val):** 1.010
- **DFL Loss (val):** 1.187

### Training Dynamics

**Learning Progression:**
- **Epochs 1-50:** Rapid initial learning
  - mAP@0.5 increases from ~8% → 60%
  - Large loss reductions across all metrics
  - High volatility in early training

- **Epochs 50-150:** Gradual refinement
  - mAP@0.5 stabilizes around 60-66%
  - Precision improves from 50% → 75%
  - Recall plateaus around 55-60%

- **Epochs 150-259:** Plateau/slight improvements
  - mAP@0.5 stable at 60-65%
  - Minor fluctuations but no major gains
  - Training essentially converged

### Key Observations

✅ **Strengths:**
- High precision (78.7%) - low false positive rate
- Smooth convergence without major instabilities
- Good box localization (mAP@0.5 = 63%)
- Training losses continue decreasing throughout

⚠️ **Weaknesses:**
- Moderate recall (57.9%) - misses ~42% of objects
- Gap between train and validation losses suggests some overfitting
- mAP@0.5:0.95 (40.4%) indicates localization could be tighter
- Performance plateau after epoch ~150 (may be overtrained)

⚠️ **Class Balance Considerations:**
- Three-class problem: person, inshade, outshade
- Likely class imbalance (more outshade than inshade in sunny images)
- No per-class metrics available in current training logs

### Precision vs Recall Trade-off
- **High Precision (78.7%):** When model says "person in shade", it's usually correct
- **Moderate Recall (57.9%):** Model misses many true instances
- **Implication:** Conservative predictions - prefers to miss detections rather than make false positives
- **For Analysis:** May underestimate shade-seeking behavior (people in shade not detected)

---

## 3. Model Performance in Context

### ViT Binary Classifier Context
**Task Difficulty:** Medium
- Sunny vs not sunny is relatively clear-cut
- Strong visual cues (shadows, lighting, sky)
- 92.3% accuracy is good for this task

**Expected Real-World Performance:**
- Given 7 cities × 129,803 total images analyzed
- Expected ~10,000 misclassifications (8% error rate)
- Errors likely on edge cases: overcast, dusk/dawn, partial clouds

**Impact on Analysis:**
- Misclassifications reduce sample size for sunny images
- False positives (cloudy classified as sunny) dilute shade-seeking signal
- False negatives (sunny classified as cloudy) waste potential data

### YOLO Detector Context
**Task Difficulty:** High
- Small objects in street view images
- Occlusion, distance, varying poses
- Fine distinction between "in shade" vs "out of shade"

**Expected Real-World Performance:**
- 78.7% precision means ~21% false positives (people incorrectly classified)
- 57.9% recall means ~42% of actual people missed
- mAP@0.5 of 63% is respectable for this difficult task

**Impact on Analysis:**
- Missed detections (42% recall) reduce statistical power
- Systematic bias if model preferentially misses one class
- Precision-recall trade-off favors false negatives over false positives

### Comparison to State-of-the-Art

**ViT Binary Classifier:**
- 92.3% accuracy is strong for binary classification
- Comparable to typical transfer learning results
- Could potentially reach 95%+ with more training data or fine-tuning

**YOLO Detector:**
- mAP@0.5 of 63% is moderate
- COCO dataset state-of-the-art: ~55% mAP@0.5:0.95
- Our task is more specialized (shade vs sun), making comparison difficult
- Recall of 58% suggests room for improvement

---

## 4. Recommendations

### ViT Binary Classifier Improvements

1. **Early Stopping**
   - Implement early stopping based on validation accuracy
   - Stop at epoch 3-4 instead of 5 to prevent overfitting
   - Expected gain: +1-2% accuracy

2. **Data Augmentation**
   - Add color jitter, brightness adjustments
   - Rotate/flip images
   - Expected gain: +1-2% accuracy, better generalization

3. **Ensemble**
   - Combine predictions from all 5 folds
   - Majority voting or probability averaging
   - Expected gain: +2-3% accuracy

### YOLO Detector Improvements

1. **Address Recall Issue**
   - Lower confidence threshold (currently detecting conservatively)
   - Use techniques like multi-scale training
   - Add more training data for underrepresented classes
   - Expected gain: +10-15% recall (at cost of some precision)

2. **Class Balance**
   - Analyze per-class performance
   - Oversample minority class (likely "inshade")
   - Use weighted loss function
   - Expected gain: More balanced predictions

3. **Early Stopping**
   - Training plateaued around epoch 150
   - Could have stopped 100 epochs earlier
   - Save computation time with no performance loss

4. **Architecture Changes**
   - Try larger YOLO variant (YOLOv8-large vs medium)
   - Experiment with input resolution
   - Expected gain: +5-10% mAP

### Analysis Pipeline Considerations

1. **Quantify Uncertainty**
   - Report confidence intervals accounting for model errors
   - Sensitivity analysis: how do results change with ±5% accuracy?
   - Bootstrap resampling to estimate variance

2. **Validation on Held-Out Cities**
   - Test models on cities not in training set
   - Assess geographic generalization
   - Current: All 7 cities likely in training data

3. **Error Analysis**
   - Manually inspect false positives and false negatives
   - Identify systematic failure modes
   - Targeted data collection for problem cases

---

## 5. Data Statistics

**Cities Analyzed:** 7
- Buenos Aires: 44,461 observations
- Cape Town: 14,102 observations
- Istanbul: 19,567 observations
- Madrid: 20,644 observations
- Mumbai: 7,370 observations
- Osaka: 5,845 observations
- Singapore: 17,814 observations

**Total Observations:** 129,803

**Model Performance Impact:**
- ViT classifier (92.3% accuracy): ~10,384 potential misclassifications
- YOLO detector (57.9% recall): ~42% of people not detected
- Combined effect: Reduces effective sample size significantly

---

## 6. Conclusions

### ViT Binary Classifier
✅ **Strong performance** (92.3% avg accuracy)
✅ **Consistent across folds** (90-95%)
✅ **Fast convergence** (3 epochs sufficient)
⚠️ Minor overfitting in some folds
📊 **Recommendation:** Production-ready with minor improvements

### YOLO Shade Detector
✅ **Good precision** (78.7%)
✅ **Smooth training** (259 epochs)
✅ **Stable convergence**
⚠️ **Moderate recall** (57.9% - misses 42% of people)
⚠️ **Class imbalance likely**
📊 **Recommendation:** Usable but could benefit from improvements

### Overall Assessment
Both models are **production-ready** for research purposes with known limitations:
- ViT classifier is **strong** and reliable
- YOLO detector is **moderate** with room for improvement
- Results should include **confidence intervals** accounting for model uncertainty
- Consider **ensemble methods** and **error analysis** for publication-quality results

---

## Appendix: Visualizations

The following plots are available in `outputs/model_evaluation/`:

1. **yolo_training_evaluation.png**
   - mAP curves over 259 epochs
   - Precision and recall curves
   - Training loss progression
   - Final performance summary

2. **vit_training_evaluation.png**
   - Training loss by fold (5 folds × 5 epochs)
   - Validation accuracy by fold
   - Cross-fold performance comparison

3. **sample_images/** (directory)
   - Annotated sample images from each city
   - Shows predictions with bounding boxes
   - Includes metadata (UTCI, datetime, shade preference)
   - Note: Could not generate samples (images not stored locally)

---

**Document Generated:** 2026-01-26
**Script:** `evaluate_models_and_visualize.py`
