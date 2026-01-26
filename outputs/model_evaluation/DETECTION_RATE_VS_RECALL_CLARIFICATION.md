# Detection Rate vs Recall: Important Distinction

**Date:** 2026-01-26
**Issue:** The class balance analysis measured "detection rate" not "recall"

---

## The Confusion

In `CLASS_BALANCE_ANALYSIS_RESULTS.md`, I used terms like:
- "In-shade detection rate: 65.5%"
- "Out-shade detection rate: 65.6%"

**This is MISLEADING terminology.** These are not detection rates in the technical sense.

---

## What We Actually Measured

### "Detection Rate" (Our Metric)
```
Detection Rate = (# images with ≥1 person of class X) / (# images with any people)
```

**For in-shade:**
```
65.5% = 13,048 images with ≥1 in-shade / 19,921 images with people
```

**This tells us:**
- In 65.5% of images with people, at least one in-shade person was detected
- **NOT** what fraction of actual in-shade people were detected

---

### Recall (The Correct Technical Term)
```
Recall = (# correctly detected instances) / (# actual instances)
```

**For in-shade recall to be 65.5% would mean:**
- Of all actual in-shade people in images, YOLO detected 65.5%
- Requires ground truth annotations to calculate

**We don't have ground truth**, so we cannot calculate true recall per class.

---

## What the Analysis Actually Shows

### What We Measured
**"Presence detection rate"** or **"image-level detection frequency"**

```
P(image contains ≥1 detected in-shade person | image has any people) = 65.5%
P(image contains ≥1 detected out-shade person | image has any people) = 65.6%
```

### What It Means

**Interpretation 1: Class Balance in Dataset**
- In-shade people appear in 65.5% of images with people
- Out-shade people appear in 65.6% of images with people
- Nearly equal prevalence in the dataset

**Interpretation 2: Conditional Independence Test**
- Given that people are present, the probability of detecting each class is similar
- Suggests no strong systematic bias toward detecting one class over another

**Interpretation 3: Not Direct Evidence of Equal Recall**
- Could have equal "presence detection" but different recall
- Example: Detect ≥1 in-shade in 65% of images, but only 40% of actual in-shade people
- And: Detect ≥1 out-shade in 65% of images, but only 60% of actual out-shade people

---

## Why This Still Supports Our Argument (Partially)

### What the 65.5% vs 65.6% Balance Tells Us

**Strong Evidence:**
1. **No systematic avoidance of either class**
   - If YOLO failed to detect in-shade people, that class would appear in far fewer images
   - Equal prevalence suggests both classes are detected "at least sometimes"

2. **Spatial distribution is balanced**
   - Images contain both classes with similar frequency
   - Suggests urban environments have mixed shade conditions
   - Real-world setting is conducive to detecting both classes

**Weak Evidence:**
1. **Does NOT directly prove equal recall**
   - Could detect 1 in-shade person in 65% of images (but miss 10 others)
   - Could detect 5 out-shade people in 65% of images (but miss 2 others)
   - Presence ≠ completeness

2. **Does NOT quantify undercounting bias**
   - Tells us classes appear equally often
   - Doesn't tell us if we're missing 40% or 60% within each class

---

## What We Can Actually Conclude

### From the Equal Presence Rates (65.5% vs 65.6%)

✅ **Valid Conclusions:**
1. Both classes are common in the dataset (appear in ~2/3 of images)
2. No systematic failure to detect either class entirely
3. YOLO's training included sufficient examples of both classes
4. Urban environments provide mixed shade conditions

❌ **Invalid Conclusions:**
1. ~~Recall is equal across classes~~ (not tested)
2. ~~Detection completeness is similar~~ (not tested)
3. ~~We detect 65% of in-shade people~~ (wrong interpretation)

### From the Total Count Balance (48.8% vs 51.2%)

**Total detected people:**
- In-shade: 34,534 (48.8%)
- Out-shade: 36,280 (51.2%)

✅ **Valid Conclusions:**
1. Overall class balance in detected people is good
2. No extreme class imbalance (not 90/10 or 20/80)
3. Dataset is suitable for training/analysis of both classes

⚠️ **Conditional Conclusion:**
If recall is similar for both classes, then true ratio ≈ 0.49
If recall differs, true ratio is unknown without ground truth

---

## The Missing Evidence: True Recall Per Class

### What We Need to Prove Equal Recall

**Requirement:** Ground truth annotations

**Method:**
1. Manually annotate 100-200 images
2. Count actual in-shade and out-shade people
3. Compare to YOLO predictions
4. Calculate:
   ```
   Recall_inshade = (Detected in-shade) / (True in-shade)
   Recall_outshade = (Detected out-shade) / (True out-shade)
   ```

**Then test:** Is Recall_inshade ≈ Recall_outshade?

**We have NOT done this**, so we cannot claim equal recall.

---

## Revised Argument for Ratio Estimator

### What We Can Actually Claim

**Weak Form (Current Evidence):**
> "Both classes appear in approximately 65% of images with people, suggesting no systematic detection failure for either class. While this does not directly prove equal recall, the balanced class prevalence (48.8% in-shade, 51.2% out-shade) provides circumstantial evidence that detection performance is similar across classes."

**Strong Form (Requires Validation):**
> "Manual validation of 100 images showed YOLO recall of 58% for in-shade and 57% for out-shade people (difference 1%, not significant). This confirms the assumption of equal detection rates across classes, validating the ratio estimator approach."

**We currently have the weak form, not the strong form.**

---

## Impact on Our Analysis

### Is the Ratio Estimator Still Valid?

**Yes, but with caveats:**

1. **Best Case:** Recall is truly equal
   - Ratio estimator is unbiased (modulo O(1/n) bias)
   - Our conclusions are fully valid

2. **Moderate Case:** Recall differs by 10-20%
   - Ratio estimator has small bias (~5-10%)
   - Aggregate patterns still valid
   - City comparisons slightly biased

3. **Worst Case:** Recall differs by 50%+
   - Ratio estimator heavily biased
   - Conclusions may be invalid
   - Need correction or alternative approach

**Evidence suggests we're in Best or Moderate case:**
- Equal class prevalence in images (65.5% vs 65.6%)
- Balanced total counts (48.8% vs 51.2%)
- No obvious mechanism for large recall difference
- Visual contrast hypothesis tested negative

---

## Corrected Technical Language

### What We Measured

**Correct Terms:**
- "Image-level class prevalence"
- "Presence detection rate"
- "Conditional class frequency"

**Incorrect Terms:**
- ~~"Detection rate"~~ (ambiguous)
- ~~"Recall"~~ (requires ground truth)
- ~~"Class accuracy"~~ (different metric)

### What We Should Say

**In Papers/Reports:**

❌ **Don't Say:**
> "YOLO detects in-shade and out-shade people at equal rates (65.5% vs 65.6%)"

✅ **Do Say:**
> "Both in-shade and out-shade people appear in approximately 65% of images with detected people (65.5% vs 65.6%), with overall class balance of 48.8% in-shade and 51.2% out-shade among 70,814 detected people. This balanced class distribution suggests no systematic bias toward detecting one class over another, though we cannot directly measure recall without ground truth annotations."

---

## Recommended Actions

### Option 1: Keep Current Approach (Conservative)

**Statement:**
> "While we lack ground truth data to calculate class-specific recall, the balanced class distribution (48.8% in-shade, 51.2% out-shade) and equal class prevalence across images (65.5% vs 65.6%) suggest that detection performance is similar for both classes. This supports the use of ratio-based metrics, though we acknowledge potential for small biases if recall differs substantially between classes."

**Pros:**
- Honest about limitations
- Cites available evidence
- Acknowledges uncertainty

**Cons:**
- Weaker claim than "validated equal recall"
- Reviewers may question validity

---

### Option 2: Manual Validation (Gold Standard)

**Process:**
1. Randomly sample 100-200 images with people
2. Manually annotate all people and their shade status
3. Compare to YOLO predictions
4. Calculate recall per class
5. Report difference

**Effort:** 3-6 hours of manual annotation

**Payoff:**
- Direct evidence of recall equality (or difference)
- Addresses reviewer concerns definitively
- Strengthens methodological rigor

**Recommendation:** Worth doing if submitting to high-tier journal

---

### Option 3: Sensitivity Analysis (Statistical)

**Process:**
1. Assume recall differs by X% (where X = 0, 5, 10, 15, 20)
2. Recalculate shade ratios under each scenario
3. Show that conclusions hold even with 10-15% recall difference
4. Report as robustness check

**Example:**
```
Scenario 1: Equal recall → Shade ratio = 0.488
Scenario 2: In-shade recall 10% lower → Shade ratio = 0.452
Scenario 3: In-shade recall 20% lower → Shade ratio = 0.418

UTCI effect still positive and significant in all scenarios
City rankings largely unchanged
Conclusions robust to recall differences up to 15%
```

**This approach acknowledges uncertainty but shows it doesn't affect main results.**

---

## Conclusion

### What We Actually Showed

✅ **Validated:**
- Equal class prevalence in images (65.5% vs 65.6%)
- Balanced class distribution overall (48.8% vs 51.2%)
- No systematic failure to detect either class

❌ **Not Validated:**
- Equal recall per class (requires ground truth)
- Unbiased ratio estimator (depends on equal recall)
- Exact shade ratios (may have small bias)

### Bottom Line

**The evidence SUGGESTS equal recall, but doesn't PROVE it.**

For publication, we should:
1. Use correct terminology (class prevalence, not detection rate)
2. Acknowledge this limitation
3. Either: manually validate (Option 2) or perform sensitivity analysis (Option 3)
4. Report results with appropriate caveats

**The analysis is still valuable and results are likely robust, but we need to be more precise in our claims.**

---

**Thank you for catching this imprecision!** This is exactly the kind of careful thinking needed for rigorous scientific work.

**Date:** 2026-01-26
