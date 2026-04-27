# Cross-City Statistical Comparison - Bootstrap Analysis

**Date:** 2026-03-23
**Analysis:** Bootstrap resampling with 1000 iterations
**Random seed:** 42 (reproducible)
**Purpose:** Rigorous statistical comparison of shade preference between Seattle and New York City

---

## Executive Summary

**FINDING:** Seattle and New York City show **highly statistically significant differences** in shade preference (p < 0.001) across **all temperature ranges**. The differences persist after IPW corrections, indicating genuine cross-city heterogeneity in shade preference behavior.

**Key Results:**
- Raw preference: Seattle 28 pp higher than NYC [95% CI: 27.8, 28.2]
- IPW preference: Seattle 19.7 pp higher than NYC [95% CI: 19.5, 19.9]
- Curves differ significantly at 100% of UTCI points tested (-30°C to +35°C)

**Implication:** Cities cannot be pooled. Report separate estimates for each city.

---

## Methodology

### Bootstrap Procedure

**Aggregate metrics:**
1. For each city, resample with replacement (n = sample size)
2. Compute shade preference for Raw and IPW-weighted estimates
3. Repeat 1000 times
4. Compute 95% CI from percentiles (2.5th, 97.5th)

**Curve comparison:**
1. For each city, resample with replacement
2. Fit quadratic binomial GLM (logistic regression)
3. Predict shade preference on UTCI grid [-30, 35]°C (200 points)
4. Repeat 1000 times
5. Compute mean prediction and 95% CI at each UTCI point
6. Test difference: significant if 95% CI excludes zero

### Sample Sizes

| City | Total Images | After SR Filter | Bootstrap Samples |
|------|--------------|-----------------|-------------------|
| Seattle | 2,347,104 | 780,451 (33.3%) | 1000 |
| New York City | 3,363,343 | 254,507 (7.6%) | 1000 |

---

## Results: Aggregate Metrics

### Point Estimates with Bootstrap Confidence Intervals

| City | Estimate | Shade Pref (%) | 95% CI | SE (pp) |
|------|----------|----------------|---------|---------|
| **Seattle** | Raw | 64.2% | [64.1, 64.3] | 0.05 |
| | DCWP | 46.1% | - | - |
| | IPW | 37.4% | [37.2, 37.5] | 0.07 |
| **New York City** | Raw | 36.1% | [36.0, 36.3] | 0.09 |
| | DCWP | 49.6% | - | - |
| | IPW | 17.7% | [17.5, 17.8] | 0.08 |

**Notes:**
- DCWP uses aggregate formula (no bootstrap needed - deterministic transformation)
- Confidence intervals are very narrow due to large sample sizes
- Standard errors are sub-percentage point (high precision)

### Hypothesis Tests: Seattle vs NYC

#### Test 1: Raw Shade Preference Difference

**H₀:** Seattle and NYC have equal raw shade preference
**Hₐ:** Seattle and NYC differ in raw shade preference

**Results:**
- Point estimate difference: **+28.0 pp** (Seattle higher)
- Bootstrap mean difference: **+28.0 pp**
- Bootstrap 95% CI: **[27.8, 28.2]**
- P(Seattle > NYC): **1.000** (all 1000 bootstrap iterations)

**Conclusion:** **REJECT H₀** at p < 0.001. Seattle has significantly higher raw shade preference than NYC.

#### Test 2: IPW-Adjusted Shade Preference Difference

**H₀:** Seattle and NYC have equal IPW-adjusted shade preference
**Hₐ:** Seattle and NYC differ in IPW-adjusted shade preference

**Results:**
- Point estimate difference: **+19.7 pp** (Seattle higher)
- Bootstrap mean difference: **+19.7 pp**
- Bootstrap 95% CI: **[19.5, 19.9]**
- P(Seattle > NYC): **1.000** (all 1000 bootstrap iterations)

**Conclusion:** **REJECT H₀** at p < 0.001. Seattle has significantly higher IPW-adjusted shade preference than NYC.

**Key Finding:** IPW corrections reduce the gap (28 pp → 19.7 pp) but **do not eliminate it**. The difference is robust.

---

## Results: Curve Comparison

### Statistical Test at Each UTCI Point

For each of 200 UTCI values from -30°C to +35°C:
- Computed difference in predicted shade preference (Seattle - NYC)
- Tested if 95% CI of difference excludes zero

**Raw Curves:**
- Significant difference at: **200 / 200 UTCI points (100.0%)**
- Cities differ across entire temperature range

**IPW Curves:**
- Significant difference at: **200 / 200 UTCI points (100.0%)**
- Cities differ across entire temperature range even after corrections

**Interpretation:**
- Not just a level shift - the SHAPE and magnitude differ everywhere
- No temperature range where cities behave similarly
- Corrections don't make cities comparable

### Pattern of Differences

**Raw curves (Seattle - NYC):**
- Difference ranges from ~+20 pp (cold temps) to ~+35 pp (hot temps)
- Gap is LARGER at hot temperatures (diverging effect)
- Seattle shows steeper increase with UTCI

**IPW curves (Seattle - NYC):**
- Difference ranges from ~+5 pp (cold temps) to ~+30 pp (hot temps)
- Still diverging but less extreme
- IPW corrections reduce gap more at cold temps than hot temps

**Implication:** Cities have different temperature-shade preference relationships, not just different baseline preferences.

---

## Precision and Uncertainty

### Standard Errors (from Bootstrap)

| City | Estimate | SE (pp) | Relative SE |
|------|----------|---------|-------------|
| Seattle | Raw | 0.05 | 0.08% |
| Seattle | IPW | 0.07 | 0.19% |
| NYC | Raw | 0.09 | 0.25% |
| NYC | IPW | 0.08 | 0.45% |

**Key observations:**
1. **Very high precision:** Standard errors <0.1 pp for all estimates
2. **Relative SE increases for IPW:** Weighting adds variability (as expected)
3. **NYC slightly less precise:** Smaller sample after SR filter (254k vs 780k)
4. **IPW SE similar across cities:** ~0.07-0.08 pp despite sample size differences

### Effective Sample Size Impact

| City | N (after SR) | N_eff (IPW) | N_eff % | Bootstrap SE |
|------|--------------|-------------|---------|--------------|
| Seattle | 780,451 | 375,935 | 48.2% | 0.07 pp |
| NYC | 254,507 | 142,909 | 56.2% | 0.08 pp |

**Finding:** Despite NYC having better weighting efficiency (56% vs 48%), Seattle has lower SE due to larger absolute sample size.

**Calculation check:**
- Seattle: SE ≈ √(0.37 × 0.63 / 375,935) ≈ 0.08 pp ✓
- NYC: SE ≈ √(0.18 × 0.82 / 142,909) ≈ 0.10 pp ✓ (close to observed 0.08)

---

## Robustness Checks

### Sensitivity to Bootstrap Parameters

**Random seed:** Results are deterministic with seed=42

**Number of iterations:** 1000 iterations provides:
- SE of estimated percentiles ≈ 0.7% of CI width
- For 95% CI, margin of error ≈ ±0.02 pp
- Adequate precision for our purposes

**Resampling unit:** Bootstrap resamples entire images (with their weights), not individual people
- Appropriate for clustered data (multiple people per image)
- Conservative approach (may slightly overestimate SE)

### Comparison to Analytical SE

Analytical SE (assuming simple random sample):
- Seattle Raw: √(0.642 × 0.358 / 780,451) = 0.05 pp
- Bootstrap SE: 0.05 pp

**Match:** Bootstrap and analytical SE agree, validating bootstrap procedure.

---

## Interpretation and Discussion

### Why Do Cities Differ?

**Potential explanations for Seattle > NYC by 20-28 pp:**

#### 1. Urban Form and Shadow Supply
**Seattle:**
- More tree-lined residential streets
- Lower building density
- Abundant vegetation-based shade

**NYC:**
- Urban canyon effect
- Buildings create shade but also trap heat
- Less vegetation, more hardscape

**Effect:** Seattle images may show MORE people in shade simply because MORE shade is available and accessible, even if intrinsic preference is similar.

**Counter-argument:** SR-IPW should correct for this, but maybe it doesn't fully capture accessibility differences.

#### 2. Climate and Adaptation
**Seattle:**
- Temperate maritime climate (cool, overcast)
- Residents less heat-adapted
- Higher discomfort at given UTCI

**NYC:**
- Hot humid summers (continental climate)
- Residents more heat-adapted
- Higher heat tolerance

**Effect:** At same UTCI, Seattle residents may seek shade more because they're less adapted to heat.

**Supporting evidence:** Gap is LARGER at hot temps (35 pp vs 20 pp at cold), consistent with adaptation hypothesis.

#### 3. Measurement and Sampling Artifacts

**Street View sampling:**
- Seattle: More residential, tree-lined streets sampled
- NYC: More commercial corridors, wide avenues
- Different typical street widths and orientations

**Survey timing:**
- Seattle: April-June 2023 (spring)
- NYC: Sep-Nov 2022 (fall)
- Different seasonal behavioral patterns

**Image quality:**
- Different camera generations, image processing
- Different pedestrian detection accuracy
- Different typical distances to people

**Effect:** Could introduce systematic bias making cities incomparable.

#### 4. Population Characteristics

**Demographics:**
- Age distributions
- Cultural backgrounds
- Tourist vs resident ratios

**Activity patterns:**
- Commuting vs leisure
- Rush hour vs midday
- Weekday vs weekend

**Effect:** Different populations have different shade preferences.

**Data needed:** Demographic information from images (difficult) or area-level census data.

### Implications for IPW Corrections

**Key finding:** IPW corrections reduce gap (28 pp → 19.7 pp) but don't eliminate it.

**What this means:**
1. **IPW is working:** Corrects within-city biases effectively
2. **IPW can't fix between-city differences:** Fundamental heterogeneity remains
3. **City-specific estimates are essential:** Can't pool data

**What IPW DOES correct:**
- Seattle SR-IPW: Corrects for tree-lined street oversampling
- Seattle Temp-IPW: Corrects for... (negative effect, problematic)
- DCWP: Corrects for distance-to-shade access costs

**What IPW DOESN'T correct:**
- Different urban forms between cities
- Different climate adaptation levels
- Different typical street geometries
- Different image sampling strategies

---

## Implications for Research Paper

### Main Text Recommendations

#### 1. Present City-Specific Estimates

**DO NOT:**
- Pool cities into single aggregate estimate
- Present city averages without acknowledging heterogeneity
- Claim estimates generalize to "US cities"

**DO:**
- Report Seattle and NYC estimates separately
- Highlight that cities differ significantly
- Discuss potential reasons for differences

**Example text:**
> "Shade preference varies substantially between cities. After IPW corrections, Seattle exhibits 37% shade preference compared to NYC's 18% (difference: 19.7 pp, 95% CI: [19.5, 19.9], p < 0.001). This difference persists across the full UTCI range and may reflect differences in urban form, climate adaptation, or measurement contexts."

#### 2. Report Statistical Tests

Include bootstrap confidence intervals and hypothesis tests:
- Table showing point estimates with 95% CIs
- Explicit p-values for city differences
- Statement about significance at all UTCI points

#### 3. Interpret Differences Cautiously

**Avoid causal claims:**
- ❌ "Seattle residents prefer shade more than NYC residents"
- ✓ "Shade preference is higher in Seattle than NYC, potentially due to urban form, climate, or measurement differences"

**Emphasize uncertainty about mechanisms:**
> "The observed difference could reflect genuine behavioral heterogeneity, different urban environments, or measurement artifacts. Future work with controlled experimental designs is needed to isolate causal factors."

#### 4. Discuss Generalizability

**Be humble about external validity:**
> "These results characterize shade preference in two US cities (Seattle and NYC) during specific seasons (2022-2023). Generalization to other cities, seasons, or time periods requires caution. The substantial cross-city heterogeneity suggests local factors (urban form, climate, culture) strongly influence shade preference."

### Supplementary Materials

Include in appendix:
1. **Bootstrap procedure details** (methodology)
2. **Full statistical test results** (all p-values)
3. **Diagnostic plots** showing bootstrap distributions
4. **Sensitivity analyses** (different bootstrap iterations)
5. **Comparison to pooled estimates** (showing what's lost by pooling)

---

## Technical Details

### Bootstrap Algorithm

```python
def bootstrap_aggregate_metrics(df, weight_col=None, n_bootstrap=1000):
    estimates = []
    for i in range(n_bootstrap):
        # Resample with replacement
        df_boot = df.sample(n=len(df), replace=True, random_state=i)

        # Compute metric
        if weight_col:
            weights = df_boot[weight_col].values
            est = (df_boot['in_shade'] * weights).sum() / weights.sum()
        else:
            est = df_boot['in_shade'].mean()

        estimates.append(est)

    # Compute CI
    ci_lower = np.percentile(estimates, 2.5)
    ci_upper = np.percentile(estimates, 97.5)

    return {
        'mean': np.mean(estimates),
        'ci_lower': ci_lower,
        'ci_upper': ci_upper
    }
```

### Curve Bootstrap Algorithm

```python
def bootstrap_curves(df, weight_col=None, n_bootstrap=1000, utci_grid=None):
    predictions = np.zeros((n_bootstrap, len(utci_grid)))

    for i in range(n_bootstrap):
        # Resample
        df_boot = df.sample(n=len(df), replace=True, random_state=i)

        # Fit quadratic binomial GLM
        y = df_boot['in_shade'].values
        X = pd.DataFrame({
            'const': 1,
            'utci': df_boot['utci_C'].values,
            'utci_sq': df_boot['utci_C'].values ** 2
        })

        if weight_col:
            weights = df_boot[weight_col].values
        else:
            weights = None

        model = sm.GLM(y, X, family=sm.families.Binomial(),
                      freq_weights=weights).fit()

        # Predict on grid
        X_grid = pd.DataFrame({
            'const': 1,
            'utci': utci_grid,
            'utci_sq': utci_grid ** 2
        })
        predictions[i, :] = model.predict(X_grid)

    # Compute percentiles
    ci_lower = np.percentile(predictions, 2.5, axis=0)
    ci_upper = np.percentile(predictions, 97.5, axis=0)

    return {
        'mean': np.mean(predictions, axis=0),
        'ci_lower': ci_lower,
        'ci_upper': ci_upper
    }
```

### Hypothesis Test for Curve Differences

```python
def test_curve_difference(city1_preds, city2_preds):
    # city1_preds, city2_preds: arrays of shape (n_bootstrap, n_utci_points)

    # Compute difference for each bootstrap iteration
    differences = city1_preds - city2_preds

    # Test if difference CI excludes zero
    ci_lower = np.percentile(differences, 2.5, axis=0)
    ci_upper = np.percentile(differences, 97.5, axis=0)

    # Significant if CI doesn't include 0
    significant = (ci_lower > 0) | (ci_upper < 0)

    return {
        'difference_mean': np.mean(differences, axis=0),
        'difference_ci_lower': ci_lower,
        'difference_ci_upper': ci_upper,
        'significant': significant
    }
```

---

## Computational Performance

**Total runtime:** ~21 minutes (1260 seconds)

**Breakdown:**
- Seattle aggregate bootstrap: ~3.5 min (1000 × 780k resamples)
- NYC aggregate bootstrap: ~1.2 min (1000 × 254k resamples)
- Seattle curve bootstrap: ~8 min (1000 GLM fits on 780k obs)
- NYC curve bootstrap: ~2.5 min (1000 GLM fits on 254k obs)
- Plotting and analysis: ~5.5 min

**Bottleneck:** GLM fitting for large datasets (Seattle 780k observations)

**Optimization potential:**
- Subsample for bootstrap (e.g., 10k per iteration) - trades accuracy for speed
- Parallel processing (joblib) - 8× speedup on 8 cores
- Use lightweight GLM solver - marginal gains

**Memory usage:** Peak ~2 GB (storing prediction matrices)

---

## Files Generated

### Plots
- `outputs/analysis/ipw_plots/cross_city_aggregate_comparison.png/pdf`
  - Bar charts with error bars
  - Bootstrap distribution of differences

- `outputs/analysis/ipw_plots/cross_city_curve_comparison.png/pdf`
  - 4-panel plot: Raw curves, IPW curves, Raw difference, IPW difference
  - Confidence bands around all curves
  - Red dots mark significant UTCI points

### Tables
- `outputs/analysis/ipw_plots/cross_city_summary_table.csv`
  - Publication-ready table with point estimates, CIs, and SEs
  - Ready for LaTeX/Word import

### Script
- `scripts/visualization/plot_cross_city_statistical_comparison.py`
  - Fully documented, reproducible analysis
  - Seed = 42 for exact replication

---

## Future Work

### Recommended Additional Analyses

1. **Subgroup comparisons:**
   - Test if differences vary by UTCI bin (already done at point level)
   - Test if differences vary by season
   - Test if differences vary by time of day

2. **Pooled vs separate models:**
   - Fit interaction model: `shade ~ utci + utci² + city + city×utci`
   - Test if city interaction is significant (Wald test)
   - Compare AIC/BIC for pooled vs separate models

3. **Spatial heterogeneity within cities:**
   - Test if differences exist within Seattle neighborhoods
   - Test if differences exist within NYC boroughs
   - Bootstrap by spatial cluster instead of overall

4. **Temporal stability:**
   - If multi-year data available, test consistency over time
   - Test if differences are stable across survey years

5. **Bayesian hierarchical model:**
   - City as random effect
   - Shrinkage estimation for city-specific slopes
   - Quantify between-city vs within-city variation

### Data Collection Recommendations

To better understand cross-city differences:

1. **Expand to more cities:**
   - Sample 10-20 US cities with varying climates
   - Standardize image collection protocol
   - Ensure seasonal coverage for all cities

2. **Controlled experiments:**
   - Same-season data collection across cities
   - Same street types (residential vs commercial)
   - Same time-of-day sampling

3. **Auxiliary data:**
   - Link to census demographics
   - Link to urban form metrics (tree canopy, building density)
   - Link to climate normals

4. **Survey validation:**
   - Stated preference surveys in both cities
   - Ask "would you seek shade at 25°C?"
   - Compare revealed vs stated preferences

---

## Conclusion

**Seattle and NYC exhibit statistically significant, large-magnitude differences in shade preference that persist after IPW corrections.** The cities differ at all temperature points from -30°C to +35°C. This finding has important implications:

1. **Methodological:** City-specific estimates are essential. Cannot pool.
2. **Substantive:** Shade preference heterogeneity suggests local factors (urban form, climate, culture) matter.
3. **Policy:** Heat mitigation strategies may need city-specific calibration.

**The bootstrap analysis provides high confidence in these conclusions,** with very narrow confidence intervals (0.05-0.09 pp) and unanimous bootstrap agreement (p = 1.000).

**Future research should:**
- Expand to more cities to map heterogeneity
- Investigate mechanisms (urban form vs climate vs culture)
- Develop theory explaining cross-city variation

---

**End of Document**
