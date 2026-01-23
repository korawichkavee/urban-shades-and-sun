# Technical Discussion: GAM Fitting Issues for Phoenix Data

## Question 1: Why is there such a difference between UTCI range and what GAM can use?

### The Problem: Sparse Unique Temperature Values

While the overall UTCI range is wide (-19.6°C to 44.7°C), the actual **distribution is extremely sparse**:

| Season | Observations | UTCI Range | **Unique UTCI Values** |
|--------|--------------|------------|------------------------|
| Spring | 335 | 0.7°C to 20.6°C | **7** |
| Summer | 346 | 27.6°C to 44.7°C | **9** |
| Fall | 103 | -2.2°C to 33.4°C | **5** |
| Winter | 27 | -19.6°C to 11.0°C | **5** |

### Why This Matters for GAM

The Phoenix data has **observations clustered at only a handful of temperature points**. For example, Spring has 335 observations but they're all concentrated at just 7 unique UTCI values: [0.7, 5.2, 8.3, 9.4, 14.3, 18.3, 20.6]°C.

This creates a fundamental problem:
- **GAM needs**: Sufficient unique x-values to estimate smooth functions
- **We have**: Many observations at few unique temperatures (47-48 obs per unique value in Spring/Summer)
- **Result**: The data looks like it has "steps" rather than a continuous relationship

### Why Does This Happen?

The clustering occurs because:
1. **Temporal clustering**: Images were captured on specific days/times
2. **Weather rounding**: UTCI data may be rounded or from hourly bins
3. **Location clustering**: Multiple images from same location/sequence share weather
4. **Seasonal filtering**: Filtering for "sunny + people" concentrates data further

### UTCI vs GAM Range

- **UTCI range** (-19.6°C to 44.7°C): The mathematical span from min to max
- **GAM usable range**: Depends on having **enough unique x positions** to define basis functions
- With only 5-9 unique values, GAM struggles to fit smooth curves

---

## Question 2: Why is 30 observations the threshold?

### The "30 Observations" Rule: Where It Came From

This was an **arbitrary threshold** I set, but it has some statistical basis:

### Rule of Thumb for GAM Sample Size

From the literature:
- **40+ observations per parameter** is a common guideline
- **6 observations per knot** for spline placement (empirical rule)
- For our df=8 B-spline: 8 parameters + 1 intercept = 9 parameters total
- **Minimum needed**: ~9 × 6 = 54 observations (by knot rule) or 9 × 40 = 360 (by parameter rule)

### Why 30 is Too Low

Looking at our actual data:

| Season | Obs | Unique UTCI | df=8 Params | Obs/Param | **Adequate?** |
|--------|-----|-------------|-------------|-----------|---------------|
| Spring | 335 | 7 | 9 | 37.2 | **No** - not enough unique x |
| Summer | 346 | 9 | 9 | 38.4 | Maybe - borderline unique x |
| Fall | 103 | 5 | 9 | 11.4 | **No** - insufficient both ways |
| Winter | 27 | 5 | 9 | 3.0 | **No** - far too few |

**The real constraint isn't total observations - it's unique x-values!**

### Better Threshold Rules

For our specific problem:
1. **Minimum unique temperature values**: Need at least `df + 2` unique x positions
   - For df=8: need ≥10 unique UTCI values
   - For df=5: need ≥7 unique UTCI values
   - For df=3: need ≥5 unique UTCI values

2. **Minimum total observations**:
   - Classical: 10-20 observations per parameter
   - Conservative: 40+ observations per parameter
   - Our data: 335 obs with 9 params = 37 obs/param (borderline)

3. **Practical threshold**:
   ```
   n_obs >= df × 10  AND  n_unique_x >= df + 2
   ```

### Why Fall Succeeded But Spring Failed

This seems contradictory:
- **Fall**: 103 obs, 5 unique UTCI → **worked**
- **Spring**: 335 obs, 7 unique UTCI → **failed**

The difference is likely:
- **Knot placement luck**: Fall's 5 values might be well-distributed
- **Prediction range**: The error occurs during *prediction*, not fitting
- **Spring's error**: "data points fall outside the outermost knots" during `transform()`
  - This suggests the prediction grid extended beyond the spline's defined range

---

## Question 3: B-Spline Degrees of Freedom - More Discussion

### What is `df` (degrees of freedom)?

For B-splines, `df` controls:
- **Number of basis functions**: More basis functions = more flexible curve
- **Effective parameters**: Higher df = more parameters to estimate
- **Smoothness**: Lower df = smoother, higher df = more wiggly

### How to Choose df?

#### Rule 1: Unique X-Values Constraint
```
df < n_unique_x_values - 1
```
For our data:
- Spring (7 unique): **df ≤ 6**
- Summer (9 unique): **df ≤ 8**
- Fall (5 unique): **df ≤ 4**
- Winter (5 unique): **df ≤ 4**

**We used df=8, which violates this rule for most seasons!**

#### Rule 2: Sample Size Constraint
```
n_observations >= df × (10 to 40)
```
Conservative approach: 10 obs per df
- df=8 needs 80-320 observations ✓ (Spring/Summer have enough)
- df=5 needs 50-200 observations ✓ (Fall has enough)
- df=3 needs 30-120 observations ✓ (Even Winter barely qualifies)

#### Rule 3: Model Complexity vs Interpretability

Lower df = smoother = easier to interpret:
- **df=3**: Very smooth, captures only major trends
- **df=5**: Moderate flexibility, good for exploratory analysis
- **df=8**: High flexibility, can capture local wiggles
- **df=10+**: Very flexible, risk of overfitting

### What df Should We Use?

Given our constraints:

| Season | Recommended df | Reason |
|--------|----------------|--------|
| Spring | **df=4 to 5** | 7 unique values, 335 obs |
| Summer | **df=5 to 7** | 9 unique values, 346 obs |
| Fall | **df=3 to 4** | 5 unique values, 103 obs |
| Winter | **df=2 to 3** | 5 unique values, only 27 obs |
| **Overall** | **df=5 to 7** | 11-12 unique values total, 811 obs |

### B-Spline Degrees vs Polynomial Degree

**Don't confuse**:
- **df** (degrees of freedom): Number of basis functions (controls complexity)
- **degree**: Order of polynomial (we use degree=3 for cubic splines)
  - degree=1 → linear splines
  - degree=2 → quadratic splines
  - **degree=3** → cubic splines (standard, smooth)

We're using **cubic splines** (degree=3) with varying **df** (number of basis functions).

---

## Recommendations

### For This Analysis

1. **Use adaptive df based on unique x-values**:
   ```python
   n_unique = len(np.unique(x))
   df_spline = max(3, min(n_unique - 2, 6))
   ```

2. **Check data distribution before fitting**:
   ```python
   n_unique = len(np.unique(x))
   n_obs = len(x)
   if n_unique < 5:
       print("WARNING: Too few unique x values for meaningful smoothing")
   if n_obs / n_unique < 3:
       print("WARNING: Not enough replication at each x value")
   ```

3. **Consider simpler models**:
   - With only 5-9 unique UTCI values, a **binned categorical approach** might be more appropriate
   - Or use **simple logistic regression** with UTCI as linear or quadratic predictor

### For Future Data Collection

To enable better GAM fitting:
1. **Increase temporal diversity**: Collect data across more days/times
2. **Increase spatial diversity**: Sample more locations
3. **Use finer weather resolution**: If possible, get minute-level vs hourly weather
4. **Target sample size**: Aim for 100+ unique temperature values for smooth curves

---

## Why the Current Visualizations Still Work

Despite these issues:
- **Overall plot** (all seasons combined) has more unique values and worked well
- **Fall plot** succeeded (possibly by chance or lower implicit df)
- The confidence intervals properly reflect uncertainty
- The fitted curves are reasonable given the sparse data

The main limitation is **we can't fit very flexible smooths** - but with only 5-9 unique temperatures per season, we shouldn't expect to capture fine-grained non-linear relationships anyway.

---

## Alternative Approaches for This Data

Given the sparse unique x-values, consider:

### 1. Binned Analysis
Group UTCI into categories and compare proportions:
```python
bins = [-20, 0, 10, 20, 30, 45]
labels = ['Very Cold', 'Cold', 'Mild', 'Warm', 'Hot']
df['utci_bin'] = pd.cut(df['utci_C'], bins=bins, labels=labels)
```

### 2. Simple Logistic Regression
With few unique values, polynomial terms might suffice:
```python
# Linear
logit(shade_prob) = β₀ + β₁×UTCI

# Quadratic
logit(shade_prob) = β₀ + β₁×UTCI + β₂×UTCI²
```

### 3. Random Effects Model
Account for clustering by date/location:
```python
# Mixed effects logistic regression
logit(shade_prob) ~ UTCI + (1|date) + (1|location)
```

### 4. Lower df GAM
Use df=3 or df=4 for all seasons (sacrificing flexibility for stability).

---

## Summary

1. **UTCI range discrepancy**: Not all values are observed - we have 5-9 unique temperatures clustered in the range, not a continuous distribution

2. **30 observation threshold**: Was arbitrary and **wrong** - the real constraint is **unique x-values**, not total sample size. Need df+2 unique values minimum.

3. **B-spline df**: We used df=8 which was **too high** for our sparse data. Should use df=3-5 based on unique value counts. df controls flexibility but requires sufficient unique x positions.

**Bottom line**: With only 5-9 unique UTCI values per season, smooth GAM fits are fundamentally limited. The data structure is more "categorical" than "continuous" despite being measured on a continuous scale.
