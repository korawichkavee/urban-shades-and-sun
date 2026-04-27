# Additional Analyses for NYC/Seattle IPW-Adjusted Shade Preference

**Created:** 2026-03-23
**Last Updated:** 2026-03-23
**Purpose:** Proposed additional plots and analyses to strengthen the research paper argument that triple IPW corrections reveal true shade preference vs UTCI relationship.

---

## Status Update (2026-03-23)

### ✅ Completed Analyses (Top 5 Priorities)

**Phase 1 & 2 (5/10 analyses complete):**
1. ✅ Smoothed parametric curves with binned overlays
2. ✅ Effect decomposition (cumulative + waterfall)
3. ✅ Walk rate validation
4. ✅ DCWP tau sensitivity (bug fixed!)
5. ✅ IPW weight distributions

**All outputs:** `outputs/analysis/figures/` (PNG 300 DPI + PDF)

**Scripts:** `scripts/visualization/plot_*.py`

### 🐛 Bug Fixed: Tau Sensitivity Table

**Issue:** Negative percentage point effects (e.g., -51 pp) caused by using per-image `shade_pref_raw` instead of aggregate.

**Fix:** Compute aggregate raw shade preference before calculating effect sizes:
```python
raw_shade_pref = (city_data['inshade_count'].sum() /
                 (city_data['inshade_count'].sum() + city_data['outshade_count'].sum()))
```

**Corrected Results:**
- Seattle: Raw 44.0% → DCWP 46.1% (+2.1 pp) → Full IPW 48.9% (+4.9 pp)
- NYC: Raw 45.9% → DCWP 49.6% (+3.7 pp) → Full IPW 49.8% (+3.9 pp)

### 📋 Remaining Analyses (5/10)
- Cross-city statistical comparison
- Residual diagnostics
- SR threshold sensitivity
- Data quality indicators
- Linear vs quadratic model comparison

---

## Current State

The existing plot (`outputs/analysis/utci_shade_preference_curves.pdf`) shows:
- **Format:** 3-panel comparison (Raw / DCWP / DCWP+IPW)
- **Visualization:** Binned line segments (15 UTCI bins, ≥5 images/bin)
- **Cities:** Seattle (green) and NYC (blue)

**Strengths:**
- Non-parametric (no functional form assumptions)
- Shows data sparsity transparently (gaps = no data)
- Clear visual of adjustment effects

**Weaknesses:**
- Visually noisy, especially in temperature extremes
- Discontinuous jumps between bins
- Overlapping confidence bands make city comparison difficult
- Hard to extract quantitative effect sizes
- No validation that corrections are working as intended

---

## Proposed Additional Analyses

### 1. Smoothed Parametric Curves with Binned Overlays ✅ COMPLETED

**Script:** `scripts/visualization/plot_ipw_smooth_curves.py`
**Output:** `outputs/analysis/figures/utci_shade_preference_smooth_curves.png/pdf`

#### Description
Replace connected binned line segments with:
1. **Binned estimates as scatter points with error bars** (shows observed data)
2. **Smooth quadratic logistic curve overlay** (shows best-fit function)

Fit binomial GLM for each city × adjustment level:
```
logit(p_shade) = β₀ + β₁·UTCI + β₂·UTCI²
```

For IPW-adjusted: pass `w_combined` as `freq_weights` to GLM.

#### Implementation
```python
import statsmodels.api as sm
import numpy as np

# Build design matrix
X = sm.add_constant(pd.DataFrame({
    'utci': df['utci_C'],
    'utci_sq': df['utci_C']**2
}))

# Response: [shade_count, sun_count]
y = np.column_stack([df['inshade_count'], df['outshade_count']])

# Fit weighted binomial GLM
model = sm.GLM(y, X,
               family=sm.families.Binomial(),
               freq_weights=df['w_combined']).fit()

# Predict smooth curve over fine grid
utci_grid = np.linspace(-30, 30, 200)
X_pred = sm.add_constant(pd.DataFrame({
    'utci': utci_grid,
    'utci_sq': utci_grid**2
}))
p_shade_smooth = model.predict(X_pred)
```

#### Why This Is Useful
- **Clarity:** Smooth curves show overall trend; points show raw evidence
- **Statistical rigor:** GLM provides standard errors, confidence intervals, AIC/BIC for model selection
- **Interpretability:** Can report effect sizes like "10°C increase in UTCI → X pp increase in shade preference"
- **Publication quality:** Professional appearance for journal submission

#### Output
- Update existing 3-panel plot: bins as points, smooth curves as lines
- Alternative: Side-by-side 6-panel (3 bins, 3 smooth)

#### Priority
**🔥 HIGHEST (Rank 1)** - This is the most important improvement for the paper figure.

---

### 2. Effect Decomposition Plot ✅ COMPLETED

**Script:** `scripts/visualization/plot_effect_decomposition.py`
**Output:**
- `outputs/analysis/figures/effect_decomposition_cumulative.png/pdf`
- `outputs/analysis/figures/effect_decomposition_waterfall.png/pdf`

#### Description
Show how each correction layer contributes to the final estimate.

Create 4-panel cumulative plot:
1. **Raw (baseline)**
2. **Raw + DCWP** (shows DCWP marginal effect)
3. **Raw + DCWP + SR-IPW** (shows SR-IPW marginal effect)
4. **Raw + DCWP + SR-IPW + Temp-IPW** (shows Temp-IPW marginal effect)

Each panel shows Seattle and NYC curves.

Alternative: **Waterfall plot at fixed UTCI values**
```
At UTCI = 25°C, Seattle:
Raw:          0.42 ───────────────────────────┐
+ DCWP:       +0.03 ────┐                     │ = 0.45
+ SR-IPW:     +0.05 ──────┐                   │ = 0.50
+ Temp-IPW:   +0.08 ────────────┐             │ = 0.58
```

Show waterfalls for 4 temperatures: 0°C, 10°C, 20°C, 30°C.

#### Why This Is Useful
- **Transparency:** Shows exactly what each correction does
- **Mechanistic validation:** DCWP docs predict superadditivity (SR-IPW × DCWP interaction) - this plot shows whether it occurs
- **Argumentation:** Strengthens claim that corrections are independent and additive (or explains non-additivity)
- **Diagnosis:** If one correction dominates, may indicate others are unnecessary

#### Output
- 4-panel cumulative effect plot (smooth curves recommended)
- OR waterfall bar chart at 4 UTCI values × 2 cities

#### Priority
**🔥 HIGHEST (Rank 2)** - Critical for demonstrating correction mechanisms work as documented.

---

### 3. Mechanistic Validation: Walk Rate vs Shade Preference ✅ COMPLETED

**Script:** `scripts/visualization/plot_walk_rate_validation.py`
**Output:**
- `outputs/analysis/figures/walk_rate_validation_seattle.png/pdf`
- `outputs/analysis/figures/walk_rate_validation_nyc.png/pdf`

#### Description
Overlay walk rate λ(T) from mobility surveys with shade preference p(T) from SVI.

**Plot structure:**
- X-axis: UTCI (°C)
- Left Y-axis: Walk rate (trips/person-day)
- Right Y-axis: Shade preference (fraction in shade)
- Curves:
  - Walk rate from `{city}_walking_by_utci.csv` (solid line)
  - Raw shade preference (dashed line)
  - IPW-adjusted shade preference (solid line)

#### Why This Is Useful
- **Validates Temp-IPW rationale:** Asymmetric weighting assumes:
  - Cold temps: Walk rate ↓ → self-selected hardy walkers → shade pref overstated → downweight
  - Hot temps: Walk rate ↓ → self-selected heat-adapted walkers → shade pref understated → upweight
- **Empirical test:** If rationale is correct, IPW-adjusted curve should be:
  - Lower than raw at cold temps (correction pulls down)
  - Higher than raw at hot temps (correction pulls up)
- **Grounding:** Shows data basis for Temp-IPW, not just theoretical argument

#### Output
- 2 plots (Seattle, NYC), each with dual Y-axis showing walk rate + shade preference

#### Priority
**⭐ HIGH (Rank 3)** - Important for validating the theoretical motivation in the methods section.

---

### 4. Sensitivity Analysis: DCWP τ Parameter ✅ COMPLETED

**Script:** `scripts/visualization/plot_tau_sensitivity.py`
**Output:**
- `outputs/analysis/figures/tau_sensitivity_seattle.png/pdf`
- `outputs/analysis/figures/tau_sensitivity_nyc.png/pdf`
- `outputs/analysis/figures/tau_sensitivity_seattle_table.csv`
- `outputs/analysis/figures/tau_sensitivity_nyc_table.csv`

**Corrected Results (after bug fix):**

Seattle:
- Raw: 44.0% | DCWP (τ=20m): 46.1% (+2.1 pp) | Full IPW: 48.9% (+4.9 pp)

NYC:
- Raw: 45.9% | DCWP (τ=20m): 49.6% (+3.7 pp) | Full IPW: 49.8% (+3.9 pp)

**Key finding:** Effect size decreases as τ increases (stricter distance requirement = larger DCWP effect).

#### Description
Test sensitivity of DCWP-adjusted estimates to decay constant τ.

Current default: τ = 20m (from `apply_triple_ipw_final_cities.py` line 438).

**Analysis:**
- Compute DCWP adjustment for τ ∈ [5, 10, 20, 40, 80] meters
- Plot 5 curves (one per τ) on same panel
- Do this for both cities

**Interpretation of τ:**
- τ = 5m: Shade must be very close to be considered "accessible"
- τ = 20m: Moderate detour tolerance (default)
- τ = 80m: Pedestrians willing to walk far for shade

At distance d:
- τ=5m:  weight at d=20m → 0.02 (heavily discounted)
- τ=20m: weight at d=20m → 0.37 (moderately discounted)
- τ=80m: weight at d=20m → 0.78 (lightly discounted)

#### Why This Is Useful
- **Robustness check:** If curves are similar across τ, estimate is robust
- **Modeling choice transparency:** Shows DCWP effect is not an artifact of arbitrary τ choice
- **Substantive interpretation:** If τ matters, can discuss what it means (e.g., "shade seeking is only relevant within 10-20m")
- **Addresses superadditivity:** DCWP docs warn that SR-IPW + DCWP interaction amplifies at specific τ values - this tests it

#### Output
- 2 panels (Seattle, NYC)
- 5 curves per panel (τ = 5, 10, 20, 40, 80)
- Annotate default τ=20m curve

#### Priority
**⭐ HIGH (Rank 4)** - Important for showing results aren't driven by arbitrary parameter choice.

---

### 5. IPW Weight Distributions ✅ COMPLETED

**Script:** `scripts/visualization/plot_weight_distributions.py`
**Output:**
- `outputs/analysis/figures/weight_distributions_histograms.png/pdf`
- `outputs/analysis/figures/temp_ipw_vs_utci.png/pdf`
- `outputs/analysis/figures/sr_ipw_vs_shadow_ratio.png/pdf`

#### Description
Visualize the weight distributions to show where corrections are concentrated.

**Three plots:**

**Plot A: Histograms of weight distributions**
- 3 subplots: `w_sr_ipw`, `w_temp_ipw`, `w_combined`
- Show kernel density overlay
- Annotate with mean, median, effective N

**Plot B: Temp-IPW weight vs UTCI**
- Scatter plot or binned means
- X-axis: UTCI
- Y-axis: `w_temp_ipw`
- Show baseline at w=1.0 (UTCI=20°C)
- Expected shape: U-curve (low at extremes per asymmetric formula)

**Plot C: SR-IPW vs Shadow Ratio**
- Scatter plot (sample if >100k points)
- X-axis: `shadow_ratio`
- Y-axis: `w_sr_ipw`
- Show hyperbolic relationship (w = 1/SR, capped at 95th percentile)

#### Why This Is Useful
- **Diagnostic:** Shows where weights are doing the most work
- **Effective N:** If weights are mostly ~1.0, correction is minor; if highly variable, correction is substantial
- **Validates implementation:** Temp-IPW should equal 1.0 at 20°C baseline (sanity check)
- **Identifies outliers:** Extreme weights may indicate data quality issues

#### Output
- 3-panel figure (Histograms / Temp vs UTCI / SR-IPW vs SR)
- Summary table with effective N values

#### Priority
**⭐ MEDIUM (Rank 5)** - Useful for methods validation, less critical for main argument.

---

### 6. Cross-City Statistical Comparison ⏸️ NOT STARTED

**Script:** `scripts/visualization/plot_cross_city_comparison.py` (to be created)
**Output:** TBD

#### Description
Fit pooled binomial GLM with city × UTCI interaction to test whether curves differ statistically.

**Model:**
```
logit(p_shade) = β₀ + β₁·utci + β₂·utci² + β₃·city_nyc +
                 β₄·(city_nyc × utci) + β₅·(city_nyc × utci²)
```

**Hypothesis test:** H₀: β₄ = β₅ = 0 (curves identical across cities)

**Report:**
- Wald test p-value for interaction
- City-specific parameter estimates
- AIC/BIC for pooled vs separate models

**Interpretation:**
- p > 0.05: "NYC and Seattle show statistically indistinguishable shade preference curves"
- p < 0.05: "NYC shows significantly different UTCI response (steeper/flatter) than Seattle"

#### Why This Is Useful
- **Generalizability:** If curves are similar, strengthens claim that findings generalize beyond specific cities
- **Heterogeneity:** If different, provides interesting substantive result (why do cities differ?)
- **Sample pooling:** Justifies pooling cities for increased statistical power (if H₀ not rejected)
- **Publication rigor:** Statistical test is expected in peer review

#### Output
- Model comparison table (pooled vs separate)
- Statistical test results (p-value, confidence intervals)
- Optional: Predicted curves with interaction terms visualized

#### Priority
**⭐ MEDIUM (Rank 6)** - Important for discussion section, not essential for main figure.

---

### 7. Residual Diagnostics ⏸️ NOT STARTED

**Script:** `scripts/visualization/plot_residual_diagnostics.py` (to be created)
**Output:** TBD

#### Description
After fitting quadratic logistic GLM, plot residuals to validate functional form.

**Residuals:**
```
r_i = (observed_bin_mean_i - predicted_smooth_i) / SE_i
```

**Plot:**
- X-axis: UTCI
- Y-axis: Standardized residuals
- Points: One per UTCI bin
- Expected: Random scatter around zero
- Problematic: Systematic patterns (U-shape, trend)

**Augment with:**
- Q-Q plot (test normality of residuals)
- Scale-location plot (test homoscedasticity)

#### Why This Is Useful
- **Model validation:** Confirms quadratic form is appropriate
- **Identifies misspecification:** If residuals show pattern, may need:
  - Higher-order polynomial (cubic UTCI)
  - Spline/GAM
  - Interaction terms
- **Reviewer defense:** Pre-empts "why not use flexible GAM?" question

#### Output
- 4-panel diagnostic plot (Residuals vs UTCI / Q-Q / Scale-Location / Residuals vs Fitted)
- Do for each city × adjustment level (12 plots total) or just final IPW-adjusted (2 plots)

#### Priority
**⭐ MEDIUM (Rank 7)** - Important for methods rigor, but supplementary material quality.

---

### 8. Shadow Ratio Threshold Sensitivity ⏸️ NOT STARTED

**Script:** `scripts/visualization/plot_sr_threshold_sensitivity.py` (to be created)
**Output:** TBD

#### Description
Test sensitivity of estimates to SR ≥ 0.05 filter threshold.

**Analysis:**
- Compute estimates for SR thresholds: 0.03, 0.05, 0.10
- For each threshold, report:
  - Sample retention rate
  - Effective N after IPW
  - Shade preference estimates (raw, DCWP, IPW)
  - Shade preference vs UTCI curve

**Expected:**
- Lower threshold (0.03) → more data retained, but noisier weights
- Higher threshold (0.10) → less data, but cleaner weights

#### Why This Is Useful
- **Transparency:** SR filter discards ~65-70% of data - readers will question this
- **Robustness:** If estimates stable across thresholds, filtering is not cherry-picking
- **Justification:** If 0.05 is optimal (balance retention vs weight stability), explain why

#### Output
- Sample retention table (threshold × retention % × effective N)
- 3 curves overlaid (SR≥0.03, 0.05, 0.10) for final IPW-adjusted estimates

#### Priority
**📊 LOW (Rank 8)** - Good for supplementary material, not essential for main text.

---

### 9. Data Quality Indicators ⏸️ NOT STARTED

**Script:** `scripts/visualization/plot_data_quality.py` (to be created)
**Output:** TBD

#### Description
Visualize sample sizes and spatial coverage to show data limitations transparently.

**Plot A: Sample Size Heatmap**
- Rows: UTCI bins (-30°C to +30°C, 5°C width)
- Columns: Adjustment levels (Raw / DCWP / DCWP+IPW)
- Cell color: log₁₀(effective N)
- Annotation: Show "no data" for empty bins

**Plot B: Spatial Coverage Map**
- Map of NYC/Seattle with points colored by season
- Shows whether seasonal imbalance is also spatial (e.g., summer images concentrated downtown)

**Plot C: Temporal Coverage**
- Histogram of image counts by month
- Check for seasonal balance (should be ~8% per month if uniform)

#### Why This Is Useful
- **Transparency:** Shows where data is strong/weak
- **Trust:** Acknowledging limitations builds credibility
- **Interpretation:** If UTCI extremes have low N, caveat extrapolation

#### Output
- 3-panel figure (Heatmap / Spatial Map / Temporal Histogram)

#### Priority
**📊 LOW (Rank 9)** - Useful for appendix, not main results.

---

### 10. Linear vs Quadratic Model Comparison ⏸️ NOT STARTED

**Script:** `scripts/visualization/plot_model_comparison.py` (to be created)
**Output:** TBD

#### Description
Fit both linear and quadratic UTCI models, compare fit statistics.

**Models:**
- M1 (linear): `logit(p_shade) = β₀ + β₁·UTCI`
- M2 (quadratic): `logit(p_shade) = β₀ + β₁·UTCI + β₂·UTCI²`

**Compare:**
- AIC, BIC (lower is better)
- Likelihood ratio test (H₀: β₂ = 0)
- Visual comparison of fitted curves

#### Why This Is Useful
- **Parsimony:** If linear is sufficient, use simpler model
- **Justification:** If quadratic improves fit, justify complexity
- **Reviewer question:** "Why quadratic?" can be answered with formal test

#### Output
- Model comparison table
- Overlaid curves (linear vs quadratic) on data

#### Priority
**📊 LOW (Rank 10)** - Nice to have, but quadratic is already standard in your docs.

---

## Priority Ranking Summary

### Tier 1: Essential for Main Paper Figure 🔥 ✅ COMPLETED
1. ✅ **Smoothed Parametric Curves with Binned Overlays** - Replaces current plot with publication-quality version
2. ✅ **Effect Decomposition Plot** - Shows correction mechanisms work as intended

### Tier 2: Important for Methods Validation ⭐
3. ✅ **Mechanistic Validation: Walk Rate vs Shade Preference** - Validates Temp-IPW rationale
4. ✅ **Sensitivity Analysis: DCWP τ Parameter** - Shows robustness to modeling choices (bug fixed)
5. ✅ **IPW Weight Distributions** - Diagnostics for weight performance
6. ⏸️ **Cross-City Statistical Comparison** - Quantifies generalizability
7. ⏸️ **Residual Diagnostics** - Validates functional form assumption

### Tier 3: Supplementary Material Quality 📊
8. ⏸️ **Shadow Ratio Threshold Sensitivity** - Addresses SR filter concerns
9. ⏸️ **Data Quality Indicators** - Transparency about sample limitations
10. ⏸️ **Linear vs Quadratic Model Comparison** - Formal model selection

---

## Recommended Implementation Order

### Phase 1: Main Paper Figures ✅ COMPLETED
1. ✅ Smoothed curves + binned overlay (Rank 1) - `plot_ipw_smooth_curves.py`
2. ✅ Effect decomposition plot (Rank 2) - `plot_effect_decomposition.py`
3. ✅ Walk rate validation plot (Rank 3) - `plot_walk_rate_validation.py`

**Deliverable:** ✅ 3 high-quality figures for main text

### Phase 2: Methods Validation (PARTIALLY COMPLETE)
4. ✅ DCWP τ sensitivity (Rank 4) - `plot_tau_sensitivity.py` (bug fixed!)
5. ✅ IPW weight distributions (Rank 5) - `plot_weight_distributions.py`
6. ⏸️ Residual diagnostics (Rank 7) - NOT STARTED

**Deliverable:** Methods supplement with diagnostics (4/6 complete)

### Phase 3: Robustness Checks ⏸️ NOT STARTED
7. ⏸️ Cross-city statistical test (Rank 6)
8. ⏸️ SR threshold sensitivity (Rank 8)
9. ⏸️ Data quality indicators (Rank 9)
10. ⏸️ Linear vs quadratic comparison (Rank 10)

**Deliverable:** Complete supplementary materials (0/4 complete)

---

## Technical Notes

### Key Functions Needed

**From existing codebase:**
- `compute_sr_ipw()` - Already in `apply_triple_ipw_final_cities.py:32`
- `compute_temp_ipw()` - Already in `apply_triple_ipw_final_cities.py:62`
- `compute_dcwp_adjustment()` - Already in `apply_triple_ipw_final_cities.py:108`
- `effective_sample_size()` - Already in `apply_triple_ipw_final_cities.py:279`

**New functions to write:**
- `fit_binomial_glm()` - Quadratic logistic regression
- `plot_smooth_with_bins()` - Scatter + smooth curve overlay
- `plot_effect_decomposition()` - Waterfall or cumulative panels
- `plot_walk_rate_validation()` - Dual Y-axis overlay
- `sensitivity_tau()` - Loop over τ values
- `plot_weight_distributions()` - Histograms + scatter

### Data Requirements

**Inputs:**
- `final_run_outputs/{city}/{city}_final_analysis_with_ipw.csv` (output of `apply_triple_ipw_final_cities.py`)
- `outputs/analysis/{city}_walking_by_utci.csv` (walk rate functions)

**Columns needed:**
- `utci_C`, `inshade_count`, `outshade_count`, `person_count`
- `shadow_ratio`, `dist_to_shade_m`
- `w_sr_ipw`, `w_temp_ipw`, `w_combined`
- `shade_pref_raw`, `shade_pref_dcwp`

### Plotting Style

**Match existing style from current plot:**
- Seattle: Green (#2ca02c)
- NYC: Blue (#1f77b4)
- Font: Sans-serif, readable at journal column width
- Confidence bands: Shaded region (alpha=0.2)
- Grid: Light gray, subtle

---

## Questions for Discussion

1. **Model complexity:** Should we test cubic UTCI or stick with quadratic?
2. **City pooling:** If cross-city test shows no difference, present pooled curve?
3. **Seasonal plots:** Current plot pools seasons - should we show seasonal-specific curves too?
4. **Baseline choice:** Temp-IPW uses 20°C baseline - sensitivity to 15°C or 25°C?
5. **Bootstrap CI:** Compute confidence intervals via bootstrap, or use GLM standard errors?

---

**End of Proposal**
