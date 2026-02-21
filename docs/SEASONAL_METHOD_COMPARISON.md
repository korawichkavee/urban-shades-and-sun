# Seasonal Bias Correction Methods: Comparison and Assessment

## Summary of Methods Implemented

We implemented four approaches to correct seasonal sampling bias in State College SVI shade preference estimates:

1. **Uncorrected** (baseline): Triple IPW only (SR-IPW + DCWP + Temp-IPW)
2. **Spatial Post-Stratification + Temperature Range Standardization**: Reweighting to match overall spatial and UTCI distributions
3. **Inverse Propensity Score Weighting**: Multinomial logit model for season assignment probability
4. **Hierarchical Spatial Model**: Bayesian GLM with spatial random effects and season interactions

---

## Method-by-Method Assessment

### Method 1: Uncorrected (Triple IPW Only)

**Effective Sample Sizes:**
- Overall: 1,668
- Fall: 869 (52.1%)
- Spring: 386 (23.1%)
- Winter: 233 (14.0%)
- Summer: 180 (10.8%)

**Strengths:**
- Simplest approach
- No additional modeling assumptions
- Fast computation
- Corrects within-season biases (shadow supply, shade access, activity)

**Weaknesses:**
- Does NOT address spatial imbalance (Fall samples different streets than Summer)
- Does NOT address temperature truncation (Winter only observes cold temps)
- Seasonal estimates confound true preferences with sampling artifacts
- No mechanism to distinguish signal from noise

**Credibility: ★★☆☆☆ (Low)**
- Suitable for **overall pooled estimate only**
- Seasonal comparisons are **biased by spatial/temporal sampling**

---

### Method 2: Spatial Post-Stratification + Temperature Standardization

**Effective Sample Sizes:**
- Overall: 590.1 (35.4% of raw)
- Fall: 426.7 (72.3% of corrected sample)
- Spring: 153.6 (26.0%)
- Winter: 56.8 (9.6%)
- Summer: 19.6 (3.3%) ⚠️

**Spatial Balance:**
- 55 grid cells total (500m resolution)
- Winter: 26 cells (47% of total)
- Spring: 24 cells (44%)
- Summer: 47 cells (85%) - most spatially diverse
- Fall: 37 cells (67%)

**Temperature Reweighting:**
- Winter: Upweighted at mild temps (mean w = 0.47, range 0.14-11.15)
- Summer: Downweighted heavily (mean w = 0.54, range 0.13-1.92)
- Combined with spatial weights → Summer collapsed to n_eff = 19.6

**Strengths:**
- **Principled survey methodology** (post-stratification is standard practice)
- **Non-parametric** (no model misspecification risk)
- **Directly addresses two main biases**: spatial and temperature range
- **Interpretable**: "reweights to match overall spatial/thermal footprint"

**Weaknesses:**
- **Summer severely downweighted** (n_eff = 19.6, only 3% of effective sample)
- Requires **sufficient spatial overlap** across seasons (achieved here)
- **Extrapolation still required** for temperature ranges not observed
- Can produce **extreme weights** if seasons poorly overlap (mitigated by winsorization)

**Credibility: ★★★★☆ (Good)**
- Overall estimate is **robust** (n_eff = 590)
- Fall and Spring estimates are **credible** (sufficient effective sample)
- **Winter is marginal** (n_eff = 57, wide CIs expected)
- **Summer is unreliable** (n_eff = 20, essentially lost)

**Recommendation:**
- Use for **Overall, Fall, Spring**
- Report **Winter with wide CIs and caveats**
- **Do not report Summer** (insufficient effective data)

---

### Method 3: Inverse Propensity Score Weighting

**Effective Sample Sizes:**
- Overall: 420.9 (25.2% of raw)
- Fall: 351.4 (83.5% of corrected sample)
- Spring: 128.6 (30.6%)
- Winter: 43.1 (10.2%)
- Summer: 39.8 (9.5%)

**Propensity Model Performance:**
- Features: lat, lon, hour, day_of_week, is_weekend, highway type (17 categories)
- Training accuracy: **67.7%** (multinomial logistic regression)
- Mean propensities: Spring (0.61), Fall (0.59), Winter (0.39), Summer (0.32)

**Covariate Balance (Standardized Mean Differences):**
| Season | Before | After | Assessment |
|--------|--------|-------|------------|
| Summer | 0.381 | 0.102 | ✓ **Good balance achieved** |
| Fall | 0.157 | 0.129 | ✓ Slight improvement |
| Winter | 0.371 | 0.214 | ○ Moderate improvement |
| Spring | 0.243 | 0.374 | ✗ **Balance worsened** |

**Strengths:**
- **Principled causal inference framework** (Rosenbaum & Rubin 1983)
- **Summer improved dramatically** vs spatial method (n_eff 40 vs 20)
- **Balances all covariates simultaneously** (not just spatial location)
- Can assess balance diagnostics post-hoc

**Weaknesses:**
- **Spring balance worsened** (SMD 0.24 → 0.37) - propensity model misfits Spring
- **Strong unconfoundedness assumption**: no unmeasured confounders (likely violated)
- **Model-dependent**: Misspecified propensity model propagates bias
- More **conservative weighting** (lower overall n_eff than spatial method)

**Credibility: ★★★☆☆ (Moderate)**
- Overall estimate is **trustworthy** (n_eff = 421)
- **Fall is reliable** (n_eff = 351, good balance)
- **Summer improved** over spatial method but still marginal (n_eff = 40)
- **Winter and Spring questionable** (poor balance, low n_eff)

**Recommendation:**
- Use for **Overall and Fall**
- **Caveat for Summer**: Improved but still low power
- **Do not trust Spring** (balance worsened, suggests model misfit)
- Winter remains marginal

---

### Method 4: Hierarchical Spatial Model

**Model Specification:**
```
logit(p) = β₀ + β₁·UTCI + β₂·UTCI²           [Global]
         + γ_s + δ_s·(β₁·UTCI + β₂·UTCI²)    [Season-specific]
         + α_j                                [Spatial random effects]
```

**MCMC Diagnostics:**
| Parameter | Mean | SD | ESS_bulk | ESS_tail | R-hat | Status |
|-----------|------|-----|----------|----------|-------|--------|
| β₀ | -0.61 | 0.36 | 40 | 244 | 1.07 | ⚠️ Low ESS |
| β₁ | -0.15 | 0.83 | **5** | 28 | **2.11** | ❌ Not converged |
| β₂ | 0.16 | 0.39 | **5** | 30 | **2.10** | ❌ Not converged |
| σ_season_intercept | 0.57 | 0.20 | 107 | 4268 | 1.03 | ✓ Converged |
| σ_season_slope | 0.95 | 0.26 | 27 | 175 | 1.10 | ○ Marginal |
| σ_spatial | 1.12 | 0.16 | 17 | 46 | 1.15 | ⚠️ Low ESS |

**Convergence Issues:**
- **R-hat > 1.1 for critical parameters** (β₁, β₂, σ_spatial) indicates poor mixing
- **Extremely low ESS** for global UTCI effects (5 samples!) → unreliable
- **1 divergence** (minor, 0.01% of samples)
- Likely cause: **Strong correlation** between global β and season-specific δ (identifiability problem)

**Strengths:**
- **Principled Bayesian uncertainty quantification** (credible intervals, not just CIs)
- **Explicitly models spatial correlation** (random effects by grid cell)
- **Partial pooling** stabilizes small-sample seasons (borrows strength)
- **Variance estimates reveal heterogeneity**: Large σ_spatial (1.12) and σ_season_slope (0.95)
- No extreme weights (random effects absorb heterogeneity)

**Weaknesses:**
- **Did not converge** for key parameters (β₁, β₂)
- **Overparameterized** for this dataset (global + season-specific UTCI effects redundant)
- **Computationally expensive** (59 seconds for this small dataset, would be hours for metro-scale)
- Requires **MCMC expertise** to diagnose and fix convergence issues
- **Model misspecification** if spatial correlation structure wrong

**Credibility: ★★☆☆☆ (Low, as implemented)**
- Variance components (σ) are interesting and converged
- But **predictions are unreliable** due to β₁, β₂ non-convergence
- Would need **reparameterization** and much longer chains for production use

**Recommendations for Fixing:**
1. **Non-centered parameterization** for hierarchical effects
2. **Remove redundancy**: Either global β OR season-specific δ, not both
3. **Stronger priors** on β₁, β₂ (e.g., Normal(0, 0.5) instead of Normal(0, 1))
4. **Longer chains**: 4000 tune, 8000 samples
5. Or **abandon hierarchical model** in favor of simpler methods given convergence difficulties

---

## Overall Ranking: Which Method is Most Trustworthy?

### For **Overall (Pooled) Estimate**:

**Winner: Spatial Post-Stratification + Temperature Standardization (Method 2)**

**Ranking:**
1. ★★★★★ **Spatial + Temp** (n_eff = 590): Most robust, principled, sufficient power
2. ★★★★☆ **Propensity Score** (n_eff = 421): More conservative, good balance overall
3. ★★★☆☆ **Uncorrected** (n = 1668): Largest sample but biased
4. ★☆☆☆☆ **Hierarchical** (as implemented): Convergence failures

**Why Spatial + Temp wins:**
- Directly addresses known confounders (space + temperature)
- Non-parametric (minimal assumptions)
- Sufficient effective sample size
- Standard survey methodology with decades of validation

---

### For **Seasonal Estimates**:

**No single winner - depends on season:**

#### Fall (6,296 people, 53.7% right-facing cameras):
- ✓ **Spatial + Temp**: n_eff = 427 (best)
- ✓ **Propensity**: n_eff = 351 (good balance)
- ✓ **Uncorrected**: n = 869 (largest raw)
- **Recommendation**: **Report all three**, they should agree. Fall is most reliable season.

#### Spring (3,331 people, 27% of total):
- ✓ **Spatial + Temp**: n_eff = 154 (moderate power)
- ✗ **Propensity**: Balance worsened (SMD 0.37), questionable
- ○ **Uncorrected**: n = 386 (biased but large)
- **Recommendation**: **Use Spatial + Temp**, caveat moderate precision.

#### Winter (1,670 people, 13% of total):
- ○ **Spatial + Temp**: n_eff = 57 (marginal)
- ○ **Propensity**: n_eff = 43 (marginal)
- **Recommendation**: **Report with wide CIs**, emphasize low power.

#### Summer (1,233 people, 10% of total):
- ✗ **Spatial + Temp**: n_eff = 20 (**too low**)
- ○ **Propensity**: n_eff = 40 (marginal improvement)
- **Recommendation**: **Do not report** or report as "insufficient data" with extreme caution.

---

## Are Seasonal Predictions Credible?

### Assessment: **Partially Credible**

**Credible Seasons:**
- ✓ **Fall**: Yes, all methods converge, large effective samples
- ○ **Spring**: Moderately credible with Spatial + Temp method

**Not Credible:**
- ✗ **Winter**: Low power (n_eff < 60), wide CIs, substantial extrapolation
- ✗ **Summer**: Critically low power (n_eff 20-40), results dominated by noise

### Key Issues Limiting Credibility:

1. **Spatial Confounding Remains**: Even after correction, seasons sample different street types
   - Winter: Major arterials (easier to photograph in snow)
   - Summer: Residential streets (more photography activity)
   - Correction assumes observables capture all spatial heterogeneity (unlikely)

2. **Temperature Extrapolation**:
   - Winter predictions at 20°C extrapolate 18°C beyond observed max (1.7°C)
   - Summer predictions at 0°C extrapolate 8.7°C beyond observed min
   - Quadratic GLM may not capture true functional form at extremes

3. **Population Composition**:
   - Different seasons may photograph different populations (students in Fall, tourists in Summer)
   - Under interchangeability assumption, this shouldn't matter - but it might
   - No observable to correct for "who is walking"

4. **Small Sample Sizes**:
   - Winter: 233 obs, Summer: 180 obs (before any filtering)
   - After SR ≥ 0.10 filter + corrections → critically small effective samples
   - Statistical power insufficient for reliable seasonal comparisons

---

## Assessment Metrics for Seasonal Credibility

### 1. Effective Sample Size (Primary Metric)

**Rule of Thumb:**
- **n_eff < 30**: Unreliable, do not report
- **30 ≤ n_eff < 100**: Marginal, report with extreme caution and wide CIs
- **100 ≤ n_eff < 300**: Moderate, acceptable for exploratory analysis
- **n_eff ≥ 300**: Reliable for inference

**Applied to State College:**
- Fall: 351-427 ✓ Reliable
- Spring: 129-154 ○ Moderate
- Winter: 43-57 ⚠️ Marginal
- Summer: 20-40 ❌ Unreliable

---

### 2. Covariate Balance (For Propensity Methods)

**Standardized Mean Difference (SMD):**
- |SMD| < 0.10: Good balance
- 0.10 ≤ |SMD| < 0.25: Acceptable balance
- |SMD| ≥ 0.25: Poor balance

**Love Plot:** Visualize SMD before/after for all covariates

**Applied to State College Propensity Method:**
- Summer: |SMD| = 0.10 ✓ Good
- Fall: |SMD| = 0.13 ✓ Acceptable
- Winter: |SMD| = 0.21 ○ Acceptable
- Spring: |SMD| = 0.37 ✗ Poor (propensity method fails for Spring)

---

### 3. Overlap in Covariate Distributions

**Visual Inspection:**
- Plot UTCI distributions by season
- Plot spatial distributions (lat/lon) by season
- Identify regions of **common support** (where all seasons have data)

**Quantitative:**
- Proportion of season observations in common support: Should be > 80%
- Maximum weight ratio: Should be < 10:1

**Applied to State College:**
```
UTCI Overlap:
  Winter: [-44.3, 1.7]°C
  Spring: [-22.4, 23.5]°C
  Summer: [8.7, 27.3]°C
  Fall: [-7.5, 18.9]°C
  Common support: ~[0, 10]°C (only 10°C range!)
```
- **Poor UTCI overlap** → heavy extrapolation required
- This alone suggests seasonal comparisons are questionable

---

### 4. Sensitivity Analysis

**Approach 1: Compare Methods**
- If Spatial + Temp, Propensity, and Hierarchical produce **similar estimates** → credible
- If they **diverge substantially** → one or more methods failing, results questionable

**Approach 2: E-value for Unmeasured Confounding**
- For observed seasonal difference Δ, compute minimum strength of unmeasured confounder needed to explain it away
- E-value > 2 suggests robust to modest unmeasured confounding
- E-value < 1.5 suggests fragile estimate

**Approach 3: Exclude-One-Season Jackknife**
- Refit overall model excluding each season
- If overall estimate changes substantially → that season is influential outlier

---

### 5. Posterior Predictive Checks (For Bayesian Methods)

**Generate samples from posterior predictive distribution:**
```python
y_rep ~ Binomial(n, p_posterior)
```

**Check:**
- Do replicated datasets look like observed data?
- Are observed data within 95% posterior predictive interval?
- Plot observed vs predicted by season

**Applied to Hierarchical Model:**
- Not performed due to convergence issues
- Should compute if model re-fit successfully

---

### 6. Cross-Validation Metrics

**Leave-One-Season-Out (LOSO):**
1. Fit model on 3 seasons, predict held-out season
2. Repeat for each season
3. Compute log-likelihood or calibration error

**Metric:**
- If held-out season is well-predicted → model captures seasonal pattern
- If poorly predicted → overfitting or poor generalization

**Applied to State College:**
- Not implemented (would require refitting models 4 times)
- Recommend for production analysis

---

### 7. Width of Confidence/Credible Intervals

**Rule of Thumb:**
- CI width < 0.10 (±5 percentage points): Precise
- 0.10 ≤ CI width < 0.20: Moderate precision
- CI width ≥ 0.20 (±10 pp): Imprecise, low power

**Applied to State College (from Spatial + Temp method):**
- Fall: Likely narrow CIs (n_eff = 427)
- Spring: Moderate CIs (n_eff = 154)
- Winter: Wide CIs (n_eff = 57)
- Summer: Extremely wide CIs (n_eff = 20)

**Action:** Compute and report actual CI widths in plots

---

### 8. Consistency with External Data

**Gold Standard:** Independent validation dataset
- Conduct in-person survey in State College across seasons
- Compare observed shade-seeking rates to SVI estimates

**Weak Validation:** Plausibility checks
- Do warmer seasons show higher shade preference? (Expected: Yes)
- Are effect sizes realistic? (0-50% preference range is plausible)
- Do trends align with prior literature?

**Applied to State College:**
- No external validation data available
- Plausibility: Results should show monotonic increase in preference with temperature

---

## Recommended Assessment Protocol

For any stratified analysis (seasonal, spatial bins, demographic subgroups):

### Step 1: Compute Effective Sample Sizes
```python
w = weights
n_eff = (w.sum() ** 2) / (w ** 2).sum()
```
- **Threshold:** Require n_eff ≥ 100 for reporting

### Step 2: Assess Covariate Balance (if using propensity/weighting)
```python
smd = (mean_stratum - mean_overall) / std_overall
```
- **Threshold:** Require |SMD| < 0.25 for all key covariates

### Step 3: Check Overlap
- Visualize covariate distributions by stratum
- Compute proportion in common support
- **Threshold:** Require ≥ 70% overlap

### Step 4: Compare Multiple Methods
- Fit ≥ 2 correction methods (e.g., Spatial + Propensity)
- Estimates should agree within 1 SE
- If divergence > 2 SE, investigate

### Step 5: Sensitivity Analysis
- Vary key assumptions (e.g., SR threshold, grid size)
- Compute E-values for observed differences
- Results should be qualitatively robust

### Step 6: Report Diagnostics
- **Always report:** n_eff, CI width, sample size
- **For weighting:** weight ranges, covariate balance
- **For Bayesian:** R-hat, ESS, posterior predictive checks
- **Transparency:** Show results with and without correction

---

## Final Recommendations for State College Analysis

### What to Report:

1. **Overall Pooled Estimate (Primary Result):**
   - Use **Spatial Post-Stratification + Temperature Standardization**
   - n_eff = 590, robust and reliable
   - Compare to uncorrected (n = 1668) as sensitivity check

2. **Fall Estimate (Credible Seasonal Comparison):**
   - Report Spatial + Temp (n_eff = 427)
   - Compare to Propensity (n_eff = 351) as robustness check
   - Sufficient power for reliable inference

3. **Spring Estimate (Moderate Confidence):**
   - Report Spatial + Temp (n_eff = 154) with caveats
   - Wide CIs, exploratory only
   - Do NOT report Propensity (poor balance)

4. **Winter and Summer (Insufficient Data):**
   - Report as "Insufficient data for reliable seasonal estimates"
   - Can show curves with very wide CIs labeled "Exploratory/Underpowered"
   - Emphasize extrapolation concerns

### Key Takeaway:

**Seasonal estimates are credible for Fall only.** For a credible seasonal analysis, you would need:
- 3-5x more images per season (especially Winter/Summer)
- Better temporal coverage (reduce extrapolation)
- Validation data (in-person observations)

The **overall pooled estimate is highly credible** and should be the primary scientific claim. Seasonal patterns are **suggestive but not definitive** given current data limitations.

---

## References for Assessment Metrics

1. **Effective Sample Size**: Kish, L. (1965). *Survey Sampling*. Wiley.
2. **Standardized Mean Difference**: Austin, P. C. (2011). An introduction to propensity score methods for reducing the effects of confounding. *Multivariate Behavioral Research*, 46(3), 399-424.
3. **E-values**: VanderWeele, T. J., & Ding, P. (2017). Sensitivity analysis in observational research. *Annals of Internal Medicine*, 167(4), 268-274.
4. **Cross-Validation**: Vehtari, A., Gelman, A., & Gabry, J. (2017). Practical Bayesian model evaluation using leave-one-out cross-validation and WAIC. *Statistics and Computing*, 27(5), 1413-1432.
5. **Survey Post-Stratification**: Gelman, A., & Little, T. C. (1997). Poststratification into many categories using hierarchical logistic regression. *Survey Methodology*, 23(2), 127-135.
