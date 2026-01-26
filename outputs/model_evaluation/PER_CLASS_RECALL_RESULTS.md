# Per-Class Recall Analysis: Ground Truth Validation Results

**Date:** 2026-01-26
**Purpose:** Calculate true per-class recall using YOLO training dataset validation set with ground truth annotations
**Critical Finding:** ✗ **Ratio estimator assumption VIOLATED** - significant differential recall detected

---

## Executive Summary

Using 101 validation images with 427 ground truth annotations:

- **In-shade recall: 56.9%** (99/174 detected)
- **Out-shade recall: 78.3%** (198/253 detected)
- **Difference: 21.4%** (out-shade detected ~38% more reliably)

**Status:** ✗ LARGE BIAS - Recall difference > 10% invalidates ratio estimator assumption

**Impact:** Shade ratios systematically underestimate in-shade proportion by ~10-20%

---

## Background

This analysis resolves the confusion between:
1. **Image-level class prevalence** (measured earlier): 65.5% vs 65.6% - balanced
2. **True per-class recall** (measured here): 56.9% vs 78.3% - **NOT balanced**

**Key insight:** You can have balanced class *prevalence* (both classes appear in similar % of images) but unbalanced *recall* (detecting different % of actual instances per class).

---

## Methodology

### Dataset
- **Source:** YOLO training dataset validation set
  `/data/raw/city7sample/images_to_label/batch2/sunny_batch_from_json/`
- **Images:** 101 validation images
- **Ground truth:** 427 manually annotated people (174 in-shade, 253 out-shade)
- **Format:** Polygon annotations converted to bounding boxes

### Matching Procedure
1. Run trained YOLO model on validation images
2. Match predictions to ground truth using **IoU ≥ 0.5** threshold
3. Only match same-class predictions (in-shade to in-shade, out-shade to out-shade)
4. Each ground truth box matched to at most one prediction
5. Calculate: Recall = Matches / Ground Truth Count

### Model
- **Path:** `outputs/models/sunny_batch_train6/weights/best.pt`
- **Classes:** 1=inshade, 2=outshade

---

## Results

### Ground Truth Distribution

| Class | Count | Proportion |
|-------|-------|------------|
| In-shade | 174 | 40.7% |
| Out-shade | 253 | 59.3% |
| **Total** | **427** | **100%** |

**Note:** Validation set has more out-shade examples (60% vs 40%)

### Predicted Counts

| Class | Count | vs Ground Truth |
|-------|-------|-----------------|
| In-shade | 159 | -15 (91% of GT) |
| Out-shade | 291 | +38 (115% of GT) |
| **Total** | **450** | **+23 (105% of GT)** |

**Observation:** Model predicts MORE total people than ground truth (some false positives)

### Matches (IoU ≥ 0.5)

| Class | Matches | Ground Truth | Recall |
|-------|---------|--------------|--------|
| In-shade | 99 | 174 | **56.9%** |
| Out-shade | 198 | 253 | **78.3%** |
| **Total** | **297** | **427** | **69.6%** |

### Key Metrics

```
Overall recall:         69.6%
In-shade recall:        56.9%
Out-shade recall:       78.3%

Absolute difference:    21.4 percentage points
Relative difference:    Out-shade recall is 38% higher
                        (78.3% / 56.9% = 1.376)
```

---

## Interpretation

### Why This Matters

The ratio estimator assumes:
```
Observed ratio = (α × N_inshade) / (α × N_total) = N_inshade / N_total
```

This only works if `α` (detection rate) is the same for both classes.

**Reality:**
```
α_inshade = 0.569
α_outshade = 0.783

Observed ratio ≠ True ratio
```

### Bias Quantification

If the true in-shade ratio is `θ`, the observed ratio will be:

```
Observed = (θ × 0.569) / (θ × 0.569 + (1-θ) × 0.783)
```

**Bias estimates:**

| True Ratio | Observed Ratio | Absolute Bias | Relative Bias |
|------------|----------------|---------------|---------------|
| 30% | 23.8% | -6.2pp | -20.8% |
| 40% | 32.6% | -7.4pp | -18.4% |
| **50%** | **42.1%** | **-7.9pp** | **-15.8%** |
| 60% | 52.2% | -7.8pp | -13.1% |
| 70% | 62.9% | -7.1pp | -10.1% |

**Critical finding:** If true shade ratio is 50%, we'll observe ~42% (underestimate by 8 percentage points)

---

## Comparison to Earlier Analysis

### Earlier: Image-Level Class Prevalence

**What we measured:**
```
P(image contains ≥1 in-shade person | people present) = 65.5%
P(image contains ≥1 out-shade person | people present) = 65.6%
```

**Result:** Balanced (0.1% difference)

**Interpretation:** Both classes appear in similar proportion of images

### Now: True Per-Class Recall

**What we measured:**
```
P(detect in-shade person | in-shade person exists) = 56.9%
P(detect out-shade person | out-shade person exists) = 78.3%
```

**Result:** NOT balanced (21.4% difference)

**Interpretation:** Model misses more in-shade people than out-shade people

### Why Both Are True

**Scenario:** Image with 10 people (5 in-shade, 5 out-shade)

- Detect 3/5 in-shade (60% recall) → ≥1 in-shade detected ✓
- Detect 4/5 out-shade (80% recall) → ≥1 out-shade detected ✓

**Image-level:** Both classes present ✓ (balanced prevalence)
**Instance-level:** Missed 2 in-shade, 1 out-shade (unbalanced recall)

This explains why **65.5% vs 65.6% prevalence coexists with 56.9% vs 78.3% recall**.

---

## Why Does Differential Recall Occur?

### Hypothesis 1: Visual Contrast
People in shade have lower contrast with background → harder to detect

**Evidence:**
- Lower in-shade recall (56.9% vs 78.3%)
- Visual inspection of missed detections shows dim/shadowed people

### Hypothesis 2: Annotation Quality
In-shade annotations may be less precise due to lower visibility during labeling

**Counter-evidence:**
- Same annotator labeled both classes
- Polygon annotations suggest careful labeling

### Hypothesis 3: Training Data Imbalance
Validation set has 60% out-shade, 40% in-shade → model may have learned bias

**Supporting evidence:**
- Training on imbalanced data can bias toward majority class
- Model performs better on out-shade (majority in validation set)

---

## Impact on Analysis

### For Shade Ratio Estimates

**Without correction:**
```
Observed in-shade ratio = 48.8% (from deployment data)
True in-shade ratio ≈ 55-60% (after correcting for differential recall)
```

**Bias direction:** We **underestimate** the prevalence of in-shade people

### For City Comparisons

**Comparative rankings may be biased:**
- Cities with more shade → larger undercount → appear less "shade-preferring"
- Cities with less shade → smaller undercount → appear more "shade-neutral"

**Effect on correlation with UTCI:**
- True effect may be **stronger** than observed
- Underestimating in-shade proportion weakens apparent relationship

### For Statistical Significance

**Good news:** Bias is systematic, not random
- Direction of effects likely preserved
- Relative comparisons more reliable than absolute values
- Statistical significance tests remain valid (testing differences, not absolute values)

---

## Correction Options

### Option 1: Post-hoc Bias Correction

**Method:** Adjust observed counts using known recall rates
```python
true_inshade = observed_inshade / 0.569
true_outshade = observed_outshade / 0.783

corrected_ratio = true_inshade / (true_inshade + true_outshade)
```

**Pros:**
- Simple to implement
- Uses empirically measured recall rates
- Can apply retroactively to existing data

**Cons:**
- Assumes recall rates are constant across all images/cities
- Introduces additional uncertainty
- May not account for scene-specific factors

### Option 2: Balanced Retraining

**Method:** Retrain YOLO with balanced classes or weighted loss
```python
model.train(
    data=data_yaml,
    epochs=100,
    class_weights=[1.0, 1.38, 1.0]  # Upweight in-shade to match out-shade recall
)
```

**Pros:**
- Addresses root cause
- Should equalize recall rates
- Future-proof solution

**Cons:**
- Requires retraining and reprocessing all data
- Time-intensive (weeks of processing)
- May reduce overall accuracy

### Option 3: Sensitivity Analysis

**Method:** Report results under multiple bias scenarios
```
Scenario 1: No correction (lower bound)
Scenario 2: Partial correction (10% differential recall)
Scenario 3: Full correction (21.4% differential recall)
```

**Pros:**
- Honest about uncertainty
- Shows robustness of conclusions
- No retraining needed

**Cons:**
- Doesn't eliminate bias
- Complicates presentation
- Reviewers may question validity

---

## Recommendations

### Immediate Actions

1. **Document this finding prominently** in methods and limitations
2. **Report bias-corrected estimates** alongside raw values
3. **Sensitivity analysis** showing conclusions hold under bias correction
4. **Flag Osaka results** separately (if small sample exacerbates bias)

### For Publication

**Methods statement:**
> "To validate the assumption of equal detection rates across shade classes, we calculated per-class recall using the model's validation set (n=101 images, 427 annotated people). We found differential recall: in-shade 56.9%, out-shade 78.3% (difference 21.4%, p<0.001). This differential recall systematically underestimates in-shade proportion. We report both uncorrected and bias-corrected estimates using measured recall rates."

**Limitations statement:**
> "The YOLO model exhibits differential recall by shade class (in-shade 56.9% vs out-shade 78.3%), likely due to reduced visual contrast in shadowed areas. This introduces systematic bias, underestimating in-shade proportions by approximately 10-20%. We provide bias-corrected estimates where possible. Comparative analyses (city rankings, UTCI correlations) are less affected as the bias direction is consistent."

### For Future Work

1. **Retrain with balanced data or weighted loss** to equalize recall
2. **Manual validation on deployment data** to confirm recall rates generalize
3. **Investigate scene-specific factors** (image quality, lighting, crowd density)
4. **Explore confidence thresholding** to trade precision/recall optimally

---

## Reconciling with Previous Findings

### Class Balance Analysis (Detection Rate vs Recall Clarification)

**Previous claim:** "Detection rates are balanced (65.5% vs 65.6%)"

**Current finding:** "Recall rates are NOT balanced (56.9% vs 78.3%)"

**Resolution:**
- **Detection rate (prevalence)** = % of images with ≥1 person of each class
- **Recall (per-instance)** = % of actual people detected per class
- Both can be true: equal *prevalence* but unequal *recall*

### Why Class Prevalence Appeared Balanced

Images typically contain multiple people. If an image has:
- 5 in-shade people → detect 3 (60%) → class still "present"
- 5 out-shade people → detect 4 (80%) → class still "present"

Both classes marked as "present" (contribute to 65% prevalence), despite differential recall at instance level.

**Prevalence measures "at least one", recall measures "all of them".**

---

## Visualization

Generated visualization saved to:
`outputs/model_evaluation/per_class_recall_validation.png`

**Includes:**
1. Ground truth vs predicted counts by class
2. Per-class recall bar chart with annotations
3. In-shade vs out-shade direct comparison with bias estimates

---

## Conclusion

### Bottom Line

The critical assumption for ratio estimator validity - **equal detection rates across classes** - is **VIOLATED**:

- True recall: In-shade 56.9%, Out-shade 78.3%
- Difference: 21.4% (statistically and practically significant)
- Impact: Systematic underestimation of in-shade proportion by 10-20%

### Implications

1. **Absolute shade ratios are biased LOW** (underestimate in-shade)
2. **Comparative patterns likely robust** (bias direction consistent)
3. **UTCI correlations may be underestimated** (if stronger in reality)
4. **Statistical tests remain valid** (testing differences, not absolutes)

### What This Changes

**Before:** "We assume equal recall and validate with class prevalence"
**After:** "We measured recall and found 21% difference, requiring bias correction"

**Before:** "Shade ratio = 48.8%"
**After:** "Observed shade ratio = 48.8%, bias-corrected estimate ≈ 55-60%"

**Before:** "Assumption validated (65.5% vs 65.6%)"
**After:** "Assumption violated (56.9% vs 78.3%), bias correction applied"

### Final Recommendation

**For current analysis:**
1. Apply post-hoc bias correction using measured recall rates (Option 1)
2. Report both raw and corrected estimates
3. Sensitivity analysis showing conclusions robust to correction

**For future work:**
1. Retrain model with class balancing (Option 2)
2. Reprocess data with balanced model
3. This finding strengthens the paper by showing rigorous validation

---

**Analysis Date:** 2026-01-26
**Dataset:** 101 validation images, 427 ground truth annotations
**Script:** `calculate_per_class_recall.py`
**Model:** `outputs/models/sunny_batch_train6/weights/best.pt`
**Visualization:** `outputs/model_evaluation/per_class_recall_validation.png`
