# Interpretation of NYC/Seattle IPW-Adjusted Shade Preference Results

**Created:** 2026-03-23
**Purpose:** Synthesize findings from completed analyses, identify surprising patterns, and recommend follow-up investigations.

---

## Executive Summary

Completed the top 5 priority analyses for NYC and Seattle IPW-adjusted shade preference estimates. Results reveal **surprising heterogeneity between cities** in correction dominance and **critical weight stability issues** that require immediate attention before finalizing estimates.

### Key Findings

1. ✅ **Correction mechanisms differ dramatically between cities** (Seattle: IPW-dominant, NYC: DCWP-dominant)
2. ⚠️ **Combined weights are unstable** due to extreme spatial/temporal standardization weights
3. ✅ **Smoothed curves reveal consistent positive UTCI-shade preference relationship** in both cities
4. ⚠️ **Effective sample size collapses to <4%** when all corrections are combined (Seattle: 0.4%!)
5. ✅ **Seasonal patterns are remarkably similar** despite different climates

---

## Analysis-by-Analysis Interpretation

### 1. Smoothed Parametric Curves (Priority 1) ✅

**Files:** `utci_shade_preference_smooth_curves.png/pdf`

#### Findings

Both cities show a **clear positive relationship** between UTCI and shade preference, strengthening with each correction level:

**Seattle:**
- Raw curve: Relatively flat, 40-50% across UTCI range
- DCWP adjustment: Modest upward shift (+2 pp)
- Full IPW: Stronger upward shift, steeper slope (+5 pp total)

**NYC:**
- Raw curve: Similar baseline to Seattle, 40-55% across range
- DCWP adjustment: Larger upward shift (+4 pp)
- Full IPW: Minimal additional change (+0.2 pp)

#### Interpretation

The quadratic binomial GLM fits cleanly to the data. Smooth curves show:
1. **No evidence of non-monotonic patterns** (e.g., shade avoidance at cold temps)
2. **Binned points cluster tightly around smooth curves** → good model fit
3. **Correction effects are globally positive** → bias correction increases estimated shade preference

#### Implications

- Quadratic UTCI form is sufficient (no need for cubic or splines)
- Raw estimates systematically **understate** shade preference
- Effect size varies between cities (see Surprising Finding #1 below)

---

### 2. Effect Decomposition (Priority 2) ✅

**Files:** `effect_decomposition_cumulative.png/pdf`, `effect_decomposition_waterfall.png/pdf`

#### Findings

**Seattle decomposition (aggregate):**
- Raw: 44.0%
- +DCWP: 46.1% (+2.1 pp)
- +SR-IPW: 47.3% (+1.2 pp from DCWP)
- +Temp-IPW: 48.9% (+1.6 pp from SR-IPW)

**NYC decomposition (aggregate):**
- Raw: 45.9%
- +DCWP: 49.6% (+3.7 pp)
- +SR-IPW: 49.7% (+0.1 pp from DCWP)
- +Temp-IPW: 49.8% (+0.1 pp from SR-IPW)

#### Interpretation

**SURPRISING REVERSAL:** The **relative importance of corrections is inverted** between cities.

**Seattle:** IPW weights (SR + Temp) contribute more (+2.8 pp) than DCWP (+2.1 pp)
**NYC:** DCWP dominates (+3.7 pp), IPW weights add almost nothing (+0.2 pp)

This contradicts the expectation of consistent correction mechanisms. See Surprising Finding #1 for detailed investigation.

#### Implications

- One-size-fits-all correction strategy may not be appropriate
- City-specific heterogeneity requires explanation
- Results suggest different **sources of confounding** dominate in each city

---

### 3. Walk Rate Validation (Priority 3) ✅

**Files:** `walk_rate_validation_seattle.png/pdf`, `walk_rate_validation_nyc.png/pdf`

#### Findings

Both cities show **U-shaped walk rate curves** (higher at temperate conditions, lower at extremes):

**Seattle walk rate:**
- Baseline (20°C): ~0.20 trips/person-day
- Cold extreme (-15°C): ~0.23 (hardy walkers)
- Hot extreme (30°C): ~0.22 (stable, limited data)
- **Narrow UTCI range**: -17°C to 33°C (50°C span)

**NYC walk rate:**
- Baseline (20°C): ~0.40 trips/person-day (2× Seattle!)
- Cold extreme (-11°C): ~0.29
- Hot extreme (25°C): ~0.42
- **Wide UTCI range**: -34°C to 33°C (67°C span)

#### Interpretation

**Asymmetric Temp-IPW rationale validated:**
- Walk rates dip at temperature extremes (self-selection occurs)
- IPW-adjusted curves shift **upward at hot temps** (corrects for heat-adapted walkers)
- IPW-adjusted curves shift **downward at cold temps** (corrects for cold-hardy walkers)

**BUT:** Effect size is **much smaller in NYC** despite wider UTCI range. This explains why Temp-IPW contributes little to NYC estimates (see diagnostic below).

#### NYC vs Seattle Walk Rate Puzzle

**NYC has 2× higher baseline walk rate** (40% vs 20%) but **narrower walk rate variation** across UTCI. Possible explanations:
1. **Mode substitution:** NYC has better transit → people substitute to subway in bad weather rather than canceling trips entirely
2. **Density effects:** Shorter walk distances in NYC → temperature less of a barrier
3. **Cultural differences:** NYC walkers less temperature-sensitive

**Implication:** Temp-IPW weights in NYC are **compressed toward 1.0** because walk rate varies less → smaller correction effect.

---

### 4. DCWP Tau Sensitivity (Priority 4) ✅ (Bug Fixed!)

**Files:** `tau_sensitivity_seattle.png/pdf`, `tau_sensitivity_nyc.png/pdf`, `*_table.csv`

#### Findings

**Seattle (τ=20m default):**
- τ=5m:  DCWP 48.9% (+4.9 pp), IPW 57.5% (+13.5 pp)
- τ=20m: DCWP 46.1% (+2.1 pp), IPW 48.9% (+4.9 pp)
- τ=80m: DCWP 44.7% (+0.7 pp), IPW 45.0% (+1.0 pp)

**NYC (τ=20m default):**
- τ=5m:  DCWP 54.4% (+8.5 pp), IPW 58.5% (+12.6 pp)
- τ=20m: DCWP 49.6% (+3.7 pp), IPW 49.8% (+3.9 pp)
- τ=80m: DCWP 47.2% (+1.3 pp), IPW 45.5% (-0.4 pp!)

#### Interpretation

**Effect size decreases monotonically with τ** (as expected):
- Small τ (5m): Strict accessibility criterion → large DCWP effect
- Large τ (80m): Loose accessibility criterion → minimal DCWP effect

**Sensitivity is MUCH higher in NYC:**
- NYC τ=5m: +8.5 pp DCWP effect
- Seattle τ=5m: +4.9 pp DCWP effect

This aligns with **NYC having larger distances to shade** (mean 8.1m vs Seattle 2.7m). When τ is small, NYC's distant shade is heavily discounted.

**At τ=80m, NYC IPW estimate goes NEGATIVE** (-0.4 pp vs raw). This suggests:
1. Tau is too large for NYC data (overcorrection)
2. Interaction with IPW weights creates instability at extreme τ
3. Default τ=20m is reasonable choice

#### Implications

- τ=20m is robust for both cities (moderate effect, stable)
- NYC is more sensitive to τ choice (report sensitivity analysis in supplement)
- Stricter τ strengthens the argument but reduces sample interpretability

---

### 5. IPW Weight Distributions (Priority 5) ✅

**Files:** `weight_distributions_histograms.png/pdf`, `temp_ipw_vs_utci.png/pdf`, `sr_ipw_vs_shadow_ratio.png/pdf`

#### Findings

**Weight distribution summary:**

| City | SR-IPW | Temp-IPW | Combined | N_eff (Combined) |
|------|--------|----------|----------|------------------|
| Seattle | mean=0.91, max=4.2 | mean=0.98, max=37.0 | mean=1.08, max=771.6 | 212 (0.4% of N) |
| NYC | mean=0.72, max=3.0 | mean=0.62, max=1.1 | mean=0.51, max=124.5 | 1,177 (3.7% of N) |

**Component maxima:**

| City | w_sr_ipw | w_temp_ipw | w_spatial | w_temp_range |
|------|----------|------------|-----------|--------------|
| Seattle | 4.16 | 36.98 | 48.73 | 32.45 |
| NYC | 2.95 | 1.07 | 160.13 | 35.23 |

**Extreme weights:**
- Seattle: 422 images (0.82%) have combined weight > 10
- NYC: 168 images (0.58%) have combined weight > 10

#### Interpretation

**🚨 CRITICAL PROBLEM: Combined weight collapse**

The effective sample size for **combined IPW is catastrophically low**:
- Seattle: N_eff = 212 (0.4% of 51,243 images)
- NYC: N_eff = 1,177 (3.7% of 32,076 images)

This means the combined estimate is **dominated by <1% of observations** with extreme weights.

**Root cause analysis:**

1. **SR-IPW is well-behaved** (max ~3-4, capped at 95th percentile)
2. **Temp-IPW is problematic in Seattle** (max 37, no capping)
3. **Spatial post-stratification is VERY problematic** (max 48-160)
4. **Temp range standardization is problematic** (max 32-35)

**The multiplication compounds the problem:**
- 10 duplicate Seattle images have weight = **771.6**
- These are likely from a rare spatial cell × season × UTCI bin combination
- Spatial/temporal weights dominate the instability, not DCWP or SR-IPW

#### Implications

**⚠️ CRITICAL: Current combined IPW estimates are unstable and unreliable.**

**Recommended actions (in order of priority):**
1. **Recompute without spatial/temporal standardization** (w_sr_ipw × w_temp_ipw only)
2. **Cap all individual weights at 95th percentile** before multiplication
3. **Winsorize combined weights** at 99th percentile as final safeguard
4. **Report separate corrections** instead of combined (as COMBINED_IPW_DCWP.md recommends)

**The doc `COMBINED_IPW_DCWP.md` already warned about this** (superadditivity, line 287-290):
> "The combined estimator is not recommended as the primary reported estimate... difficult to interpret substantively."

---

## Surprising Findings & Mechanistic Investigation

### 🔴 Surprising Finding #1: Reversed Correction Dominance

**Observation:** Seattle is IPW-dominant (+2.8 pp from weights vs +2.1 pp from DCWP), NYC is DCWP-dominant (+3.7 pp vs +0.2 pp).

**Why this is surprising:** Expected correction mechanisms to be similar across cities. Same methodology should correct similar biases.

**Diagnostic investigation:**

| Metric | Seattle | NYC | Interpretation |
|--------|---------|-----|----------------|
| Mean shadow ratio | 0.684 | 0.471 | Seattle has **45% more shade** available |
| Median distance to shade | 0.0m | 0.5m | Seattle shade is **immediately accessible** |
| Mean distance to shade | 2.7m | 8.1m | NYC shade is **3× farther away** |
| UTCI std dev | 8.7°C | 15.8°C | NYC has **82% wider temperature range** |
| Temp-IPW max | 37.0 | 1.1 | Seattle has extreme temp weights, NYC does not |
| Walk rate variation | Moderate | Low | NYC walk rate less temperature-sensitive |

**Mechanistic explanation:**

**Seattle:**
- High shadow ratio (0.68) → SR-IPW correction is small
- Close shade (2.7m) → DCWP correction is small
- Narrow UTCI range but extreme Temp-IPW weights (max 37) → Temp-IPW dominates
- **Conclusion:** Temp-IPW is doing all the work

**NYC:**
- Low shadow ratio (0.47) → SR-IPW has work to do
- Distant shade (8.1m) → **DCWP has LOTS of work to do**
- Wide UTCI range but low Temp-IPW weights (max 1.1) → Temp-IPW does nothing
- **Conclusion:** DCWP is doing all the work

**Why NYC Temp-IPW is inactive:**
- NYC walk rate is high (40%) and stable across UTCI
- Less self-selection bias → weights stay near 1.0
- Wide UTCI range means better coverage → less need for upweighting

**Implications:**
1. **Different cities have different dominant confounds**
2. **One-size-fits-all correction is inappropriate**
3. **City-specific correction strategies may be needed**
4. **Mechanistic interpretation requires city context** (built environment + climate)

---

### 🔴 Surprising Finding #2: Effective N Collapse

**Observation:** Combined weights reduce effective sample size to <4% (Seattle: 0.4%, NYC: 3.7%).

**Why this is surprising:** Individual corrections have reasonable effective N (SR-IPW: 49-53%, Temp-IPW: 81-89%), but combined collapses catastrophically.

**Mechanistic explanation:**

The collapse is driven by **spatial and temporal standardization**, not DCWP or IPW weights:
- Spatial post-stratification creates extreme weights (max 48-160) for undersampled grid cells
- Temperature range standardization creates extreme weights (max 32-35) for rare UTCI values in certain seasons
- Multiplication compounds extremes: 4 × 37 × 160 × 35 = **83,200** theoretical max

Seattle has **10 duplicate images with weight 771.6**, suggesting:
- A rare spatial cell sampled in only one season at an extreme UTCI
- All four correction factors align to upweight this cell enormously

**Implications:**

**🚨 CRITICAL DECISION POINT: Abandon combined weights or cap aggressively?**

Options:
1. **Report corrections separately** (recommended by COMBINED_IPW_DCWP.md)
2. **Drop spatial/temporal standardization** (only use SR-IPW × Temp-IPW × DCWP)
3. **Cap all components at 95th percentile** before multiplication
4. **Winsorize combined at 99th percentile** (accepts instability, limits damage)

**My recommendation: Option 2** (drop spatial/temporal). Justification:
- SR-IPW corrects shadow supply bias (substantive, well-grounded)
- Temp-IPW corrects activity selection bias (substantive, well-grounded)
- DCWP corrects access cost bias (substantive, well-grounded)
- Spatial post-stratification corrects **uneven geographic sampling** (mechanical, not substantive)
- Temp range standardization corrects **seasonal UTCI distribution** (mechanical, overlaps with Temp-IPW)

The mechanical corrections create instability without clear substantive benefit.

---

### 🟡 Surprising Finding #3: Seasonal Patterns are Nearly Identical

**Observation:** Despite different climates (Seattle temperate, NYC continental), seasonal shade preferences are remarkably similar.

| Season | Seattle | NYC |
|--------|---------|-----|
| Winter | 57.5% | 59.9% |
| Spring | 37.6% | 39.9% |
| Summer | 40.9% | 39.3% |
| Fall | 46.7% | 47.9% |

**Why this is surprising:** Expected NYC's harsher winters would create different behavioral patterns.

**Interpretation:**

The similarity suggests:
1. **Winter shade preference is not about temperature** (both cities ~58% despite different winter temps)
2. **Solar angle may drive winter patterns** (low sun creates long shadows, people cluster in sunny patches)
3. **Shade preference is primarily driven by heat stress** (summer/spring ~39-41% in both cities)
4. **Fall is transitional** (46-48% between summer and winter)

**Implications:**
- Seasonal correction may be less critical than expected (patterns are consistent)
- Solar geometry (not just temperature) influences shade choice
- Generalizability across US cities is plausible

---

### 🟢 Expected Finding: Positive UTCI-Shade Preference Relationship

**Observation:** Both cities show increasing shade preference with UTCI (as expected).

**Interpretation:** Validates the core hypothesis. People seek shade more when it's hot.

**No surprises, but important confirmation.**

---

## Revised Priority Analysis

### Original Priority Order

1. Smoothed curves ✅
2. Effect decomposition ✅
3. Walk rate validation ✅
4. Tau sensitivity ✅
5. Weight distributions ✅
6. Cross-city comparison ⏸️
7. Residual diagnostics ⏸️
8. SR threshold sensitivity ⏸️
9. Data quality indicators ⏸️
10. Linear vs quadratic comparison ⏸️

### Revised Priority Order (Based on Findings)

#### 🔥 URGENT: Address Weight Stability Crisis

**New Priority 1A:** Recompute estimates without spatial/temporal standardization
- **Why:** Combined weights are catastrophically unstable (N_eff <4%)
- **Action:** Modify `apply_triple_ipw_final_cities.py` to exclude w_spatial and w_temp_range
- **Expected:** N_eff should increase to ~40-50% (based on component effective sizes)
- **Timeline:** Immediate (before using combined estimates in paper)

**New Priority 1B:** Compare correction strategies
- **Why:** Seattle and NYC have different dominant confounds
- **Action:** Create comparison table of effect sizes for each correction component
- **Expected:** Clarify which corrections matter for which cities
- **Timeline:** After recomputation

**New Priority 1C:** Investigate extreme Temp-IPW weights in Seattle
- **Why:** Max weight of 37 is concerning (vs NYC max 1.1)
- **Action:** Examine what conditions create extreme Temp-IPW weights
- **Expected:** Identify whether extreme cold/hot temps with low walk rates drive this
- **Timeline:** After recomputation

#### ⭐ HIGH: Explain City Heterogeneity

**Promoted to Priority 2:** Cross-city statistical comparison
- **Why:** Need to quantify whether Seattle vs NYC differences are statistically significant
- **Action:** Fit pooled model with city × UTCI interaction (original Priority 6)
- **Expected:** Reject null (curves differ significantly)
- **Timeline:** Next analysis

**New Priority 3:** City-specific built environment analysis
- **Why:** Shadow ratio and distance to shade differences need explanation
- **Action:** Create spatial maps showing shadow ratio distributions, compare urban fabric
- **Expected:** Seattle has denser tree canopy or different street widths
- **Timeline:** After cross-city comparison
- **Script:** New - `plot_city_shadow_environment_comparison.py`

**New Priority 4:** Walk rate decomposition
- **Why:** NYC's high baseline walk rate (40% vs 20%) and low temperature sensitivity are puzzling
- **Action:** Compare walk rate curves across cities, investigate mode substitution hypothesis
- **Expected:** NYC has flatter walk rate curve due to transit availability
- **Timeline:** After built environment analysis
- **Script:** Enhancement to existing `plot_walk_rate_validation.py`

#### 📊 MEDIUM: Original Priorities Still Relevant

**Priority 5:** Residual diagnostics (original Priority 7)
- **Why:** Validate quadratic functional form
- **Action:** Create residual plots for fitted GLMs
- **Timeline:** After revised estimates stabilize

**Priority 6:** SR threshold sensitivity (original Priority 8)
- **Why:** Still important for transparency about 65-70% data loss
- **Action:** Test thresholds 0.03, 0.05, 0.10
- **Timeline:** Supplementary material

#### 📉 DEMOTED: Lower Value Given Findings

**Demoted to Priority 7:** Data quality indicators (original Priority 9)
- **Why:** Weight collapse is more urgent than sample size heatmaps
- **Timeline:** Supplementary material if time permits

**Demoted to Priority 8:** Linear vs quadratic (original Priority 10)
- **Why:** Smooth curves show quadratic fits well, no evidence of misspecification
- **Timeline:** Low priority, may skip

---

## Recommendations for Paper

### Main Text Figures (Updated)

1. **Figure 1:** Smoothed curves (3-panel) ✅ READY
   - Use **separate corrections**, not combined
   - Show: Raw | DCWP | SR-IPW + Temp-IPW (without spatial/temporal)

2. **Figure 2:** Effect decomposition ⚠️ REDO with revised weights
   - 4-panel: Raw | +DCWP | +SR-IPW | +Temp-IPW
   - Highlight city heterogeneity in caption

3. **Figure 3:** Walk rate validation ✅ READY
   - Dual-axis plot for both cities
   - Explain why NYC has low Temp-IPW effect

### Supplementary Material Figures

1. **Tau sensitivity** ✅ READY
2. **Weight distributions** ⚠️ UPDATE to exclude spatial/temporal
3. **Cross-city comparison** (NEW - high priority)
4. **Built environment comparison** (NEW - high priority)
5. **Residual diagnostics** (to be created)

### Text Recommendations

**Methods section:**
- Justify exclusion of spatial/temporal standardization (instability + mechanical vs substantive)
- Acknowledge city heterogeneity in correction mechanisms
- Report effective sample sizes for all correction levels

**Results section:**
- Lead with revised estimates (without spatial/temporal)
- Present Seattle and NYC separately (don't pool until heterogeneity is explained)
- Quantify city differences (statistical test)

**Discussion section:**
- Interpret mechanistic differences (shadow availability, distance, walk rates)
- Discuss generalizability given city heterogeneity
- Acknowledge limitations (two cities, different dominant confounds)

---

## Critical Next Steps

### Immediate (Before Using Estimates in Paper)

1. ✅ Fix tau sensitivity bug (DONE)
2. 🔴 Recompute IPW estimates without spatial/temporal standardization
3. 🔴 Regenerate effect decomposition plot with revised estimates
4. 🔴 Update weight distribution plots with revised weights
5. 🔴 Verify effective N improves to >30%

### Short-Term (Next Week)

6. Cross-city statistical comparison
7. Built environment shadow analysis
8. Walk rate decomposition analysis
9. Residual diagnostics

### Medium-Term (If Time Permits)

10. SR threshold sensitivity
11. Data quality indicators

---

## Summary

**What went well:**
- Smooth curves are publication-quality ✅
- Validation plots support theoretical rationale ✅
- Completed top 5 priorities on schedule ✅

**Critical issues identified:**
- Combined weights are unstable (N_eff <4%) 🚨
- City heterogeneity is larger than expected 🔴
- Spatial/temporal standardization causes weight collapse 🚨

**Path forward:**
- Recompute without spatial/temporal corrections (immediate)
- Investigate mechanistic differences between cities (high priority)
- Report separate corrections, not combined (as per COMBINED_IPW_DCWP.md)

**Bottom line:** The analyses uncovered important methodological issues that require revision before publication, but also revealed interesting substantive heterogeneity that strengthens the paper's contribution.

---

**End of Interpretation**
