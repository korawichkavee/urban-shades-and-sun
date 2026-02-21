# Methodological Critique: Bias-Corrected Shade Preference Analysis

**Reviewer Perspective on Triple IPW + Spatial Post-Stratification + Temperature Range Standardization**

---

## Summary

The authors present a sophisticated bias correction methodology combining three inverse propensity weighting (IPW) schemes with spatial post-stratification and temperature range standardization. While the approach is methodologically innovative and addresses important confounders, several concerns warrant attention before publication.

---

## Major Concerns

### 1. **Stacked Corrections and Effective Sample Size Collapse**

**Issue:** The methodology applies five sequential corrections:
1. SR-IPW (shadow ratio inverse propensity weighting)
2. DCWP (detour-cost weighted preference)
3. Temp-IPW (temperature-activity weighting)
4. Spatial post-stratification weights
5. Temperature range standardization weights

Final weight: `w_final = w_sr × w_dcwp × w_temp × w_spatial × w_temp_range`

**Critique:**
- Summer season: n=180 → n_eff=20 (89% information loss)
- 2023 year: n=280 → n_eff=9 (97% information loss)
- Some strata become effectively un-analyzable

**Theoretical Concern:** Each correction targets a different bias source, but their **joint effect is multiplicative**. This can lead to:
- Extreme weight concentration on few observations
- High variance estimates despite bias reduction
- MSE (bias² + variance) may actually increase

**Recommendation:**
- Report weight diagnostics for all corrections separately
- Conduct **variance-bias tradeoff analysis**: Compare MSE of partially vs fully corrected estimates
- Consider **weight truncation** at 95th percentile for all correction stages (currently only done for SR-IPW and Temp-IPW)
- Provide **sensitivity analysis**: How do results change with different winsorization thresholds?

---

### 2. **Causal Estimand Ambiguity**

**Issue:** The analysis does not clearly specify what causal quantity is being estimated.

**Questions:**
- Is this the **Average Treatment Effect (ATE)** of UTCI on shade preference in the target population?
- What is the **target population**? People in State College? Metro areas? US pedestrians?
- Is this the **Population Average Treatment Effect (PATE)** or **Sample Average Treatment Effect (SATE)**?

**Critique:**
The spatial and temporal reweighting suggests the target is "typical pedestrian behavior across all locations and times," but:
- This population is **never explicitly defined**
- It's unclear if this population is **scientifically meaningful**
- Alternative: Target could be "preference during typical walking conditions" (weighted by walk frequency)

**Recommendation:**
- **Explicitly state the causal estimand** using potential outcomes notation
- Define the target population precisely
- Justify why this population is of scientific interest
- Consider whether **conditional** estimates (e.g., shade preference at a given location/time) are more interpretable than marginal estimates

---

### 3. **Positivity Violations and Extrapolation**

**Issue:** Temperature range standardization uses kernel density ratio weighting to match overall UTCI distribution.

**Critique:**
- **Summer** samples UTCI 9°C to 27°C but must extrapolate to -44°C to 27°C
- **Winter** samples -44°C to 2°C but must extrapolate to 27°C
- This violates the **positivity assumption**: P(Season=s | UTCI=u) > 0 for all s, u

**Evidence:**
```
Summer: UTCI range [9.3, 27.3]°C
Overall: UTCI range [-44.3, 27.3]°C
→ Summer has zero probability of observing UTCI < 9°C
```

**Consequences:**
- Density ratio weights become **extreme or undefined** in non-overlapping regions
- Results for Summer at cold temperatures are **pure extrapolation** without empirical support

**Recommendation:**
- **Restrict inference to common support**: Only report estimates within UTCI range observed for each stratum
- Add **overlap diagnostics**: Plot kernel densities for each season/year on same axes
- Consider **trimming** observations in tails with <1% density in any stratum
- Report **UTCI overlap percentage**: What % of overall UTCI range is represented in each stratum?

---

### 4. **Kernel Density Estimation Sensitivity**

**Issue:** Temperature standardization uses `gaussian_kde` with Scott's rule bandwidth.

**Critique:**
- **Bandwidth choice** (Scott's rule) is arbitrary and may not be optimal for this application
- **Gaussian kernel** assumes smooth, continuous UTCI distribution (may not hold)
- **No sensitivity analysis** to bandwidth or kernel choice
- Scott's rule can **over-smooth** with small samples (e.g., 2023 n=280)

**Evidence:**
```python
kde_season = gaussian_kde(season_df['utci_C'].values, bw_method='scott')
```

**Recommendation:**
- Test alternative bandwidths: Silverman's rule, cross-validation
- Compare **parametric alternatives**: Assume normal distribution, use empirical CDF ratio
- Provide **sensitivity analysis**: How do results change with ±20% bandwidth adjustment?
- For small samples (n<100), consider **bootstrap bandwidth selection**

---

### 5. **Spatial Grid Cell Specification**

**Issue:** Spatial post-stratification uses 500m × 500m grid cells.

**Critique:**
- **Grid size (500m) is arbitrary** - no justification provided
- Spatial correlation likely extends beyond 500m
- Too coarse: May not capture micro-scale spatial variation
- Too fine: Cells with few observations get extreme weights

**Evidence:**
- State College has 55 grid cells total
- Some years only sample 12-25 cells (out of 55)
- No analysis of spatial autocorrelation at different scales

**Recommendation:**
- **Justify grid size choice**:
  - Conduct spatial autocorrelation analysis at multiple scales (250m, 500m, 1000m)
  - Choose grid size that minimizes within-cell correlation
- **Sensitivity analysis**: Report results with 250m, 500m, 1000m grids
- Consider **adaptive grid size**: Finer grid in dense areas, coarser in sparse areas
- Alternative: Use **kernel-based spatial weighting** instead of discrete grid cells

---

### 6. **Unmodeled Confounders**

**Issue:** Several potential confounders are not addressed in the correction methodology.

**Uncontrolled Confounders:**

1. **Day of week / Weekend effects**
   - Weekday vs weekend pedestrians may differ systematically
   - Currently not reweighted

2. **Time of day**
   - Morning vs afternoon vs evening pedestrians
   - Only indirectly addressed through temperature correlation

3. **Weather conditions beyond UTCI**
   - Precipitation, cloud cover, wind
   - UTCI includes temperature, humidity, wind, radiation but data may have measurement error

4. **Land use / Activity type**
   - Commuters vs recreational walkers vs shoppers
   - Different tolerance for sun exposure

5. **Demographic composition**
   - Age, gender, cultural background may affect shade preference
   - Composition may vary by season/year

6. **Clothing / Behavioral adaptation**
   - People wear different clothing in different seasons
   - May tolerate sun differently with appropriate clothing

**Recommendation:**
- **Measure additional covariates** if data available:
  - Timestamp → day of week, hour of day
  - Land use type (residential, commercial, recreational)
- **Sensitivity analysis**:
  - Stratify by weekend vs weekday
  - Control for hour of day in propensity model
- **Acknowledge limitations**: Clearly state which confounders are not controlled
- **Bound unobserved confounding**: Use methods like E-value to assess robustness

---

### 7. **Model Dependence and Specification Uncertainty**

**Issue:** Results depend on several modeling choices that lack justification.

**Key Modeling Choices:**
1. Shadow ratio threshold (SR ≥ 0.10) - why 0.10 and not 0.05 or 0.15?
2. DCWP decay constant (τ = 20m) - based on what empirical evidence?
3. Baseline temperature (20°C) for asymmetric Temp-IPW - why 20°C?
4. GLM with quadratic UTCI term - why quadratic and not cubic, spline, or GAM?
5. Winsorization at 95th percentile - why 95% and not 90% or 99%?

**Critique:**
- These choices **substantially affect results** but are presented as if objective
- **No sensitivity analysis** to alternative specifications
- **No model selection procedure** (e.g., AIC, BIC, cross-validation)

**Recommendation:**
- **Pre-register modeling choices** or provide strong theoretical justification
- **Sensitivity analysis** for all key parameters:
  - SR threshold: 0.05, 0.10, 0.15
  - DCWP τ: 10m, 20m, 30m
  - Baseline temp: 15°C, 20°C, 25°C
  - Winsorization: 90%, 95%, 99%
- **Model selection**: Compare quadratic vs cubic vs spline GLM using cross-validation
- **Report range of estimates** across reasonable specifications

---

## Minor Concerns

### 8. **Seasonal Definition Arbitrary**

**Issue:** Seasons defined as:
- Winter: Dec-Jan-Feb
- Spring: Mar-Apr-May
- Summer: Jun-Jul-Aug
- Fall: Sep-Oct-Nov

**Critique:**
- These are **meteorological seasons**, not necessarily behavioral seasons
- Thermal comfort seasons may differ (e.g., "heating season" vs "cooling season")
- State College climate may not align with standard season boundaries

**Recommendation:**
- Justify seasonal boundaries or use **data-driven clustering** based on UTCI distribution
- Alternative: Use **monthly** or **continuous time** rather than discrete seasons

---

### 9. **GLM Convergence and Goodness of Fit**

**Issue:** Quadratic binomial GLM is fit to weighted data.

**Missing Diagnostics:**
- No reported goodness-of-fit tests (e.g., Hosmer-Lemeshow)
- No residual diagnostics
- No assessment of overdispersion
- Frequency weights used, which affect standard errors differently than sampling weights

**Recommendation:**
- Report **deviance residuals** and check for patterns
- Test for **overdispersion** (quasi-binomial if needed)
- Provide **pseudo-R²** or other fit metrics
- Consider **sandwich standard errors** robust to model misspecification

---

### 10. **Wilson Confidence Intervals May Be Too Narrow**

**Issue:** Wilson CIs are computed for binomial proportions in each UTCI bin.

**Critique:**
- Wilson CIs assume **independent observations**
- Even after DCWP correction, **residual spatial correlation** likely exists
- Weights introduce additional uncertainty not captured in standard CIs
- True uncertainty is likely **underestimated**

**Recommendation:**
- Use **cluster-robust standard errors** accounting for spatial correlation
- Consider **bootstrap confidence intervals** that properly propagate weighting uncertainty
- Report effective degrees of freedom adjustments

---

### 11. **No External Validation**

**Issue:** Results are not validated against independent data sources.

**Critique:**
- No comparison to **stated preference surveys** on shade preferences
- No comparison to **revealed preference** from other cities
- No **out-of-sample validation** (e.g., hold out one year)

**Recommendation:**
- Compare to **survey data** on thermal comfort and shade preferences (if available)
- Compare State College results to **similar cities** (same climate, size)
- Conduct **temporal cross-validation**: Fit on 2015-2017, validate on 2018
- Check if results are **qualitatively consistent** with theoretical expectations from thermal comfort literature

---

### 12. **Effective Sample Size Thresholds Not Justified**

**Issue:** Authors suggest thresholds:
- n_eff < 30: Unreliable
- 30-100: Marginal
- 100-300: Moderate
- ≥300: Reliable

**Critique:**
- These thresholds appear **ad hoc** without theoretical or simulation-based justification
- Appropriate threshold depends on **effect size**, **desired power**, **acceptable CI width**
- For binomial data with p≈0.3, n_eff=100 gives CI width ± 9 percentage points

**Recommendation:**
- **Justify thresholds** using power analysis or precision requirements
- Report **CI width** as function of n_eff to help readers interpret reliability
- Alternative: Use **precision-based criteria** (e.g., "CI width < 0.15" for reliable estimate)

---

## Strengths (To Acknowledge)

1. **Comprehensive bias correction**: Addresses multiple confounders simultaneously
2. **Transparent methodology**: Code and data appear well-documented
3. **Effective sample size reporting**: Commendable transparency about weight variability
4. **Person-weighting**: Appropriately weights by number of people in each image
5. **Multiple robustness checks**: Comparison of seasonal, propensity, and hierarchical methods
6. **Appropriate statistical methods**: GLM for binomial outcome, Wilson CIs

---

## Summary of Actionable Recommendations

### High Priority (Must Address)

1. **Define causal estimand explicitly** and justify target population
2. **Implement common support restriction**: Only report estimates within overlapping UTCI ranges
3. **Conduct sensitivity analyses** for:
   - Weight truncation thresholds
   - Grid cell size
   - Kernel bandwidth
   - SR threshold, DCWP τ, baseline temperature
4. **Add overlap diagnostics**: Plot density overlaps for all strata
5. **Report variance-bias tradeoff**: Is 5-way correction actually reducing MSE?

### Medium Priority (Should Address)

6. **Justify or test modeling choices**: SR threshold, DCWP decay, quadratic GLM
7. **Add residual diagnostics**: Goodness-of-fit tests, overdispersion checks
8. **Consider additional confounders**: Day of week, hour of day, land use
9. **Spatial correlation diagnostics**: Autocorrelation at multiple scales
10. **Bootstrap CIs**: Account for weighting uncertainty

### Low Priority (Nice to Have)

11. **External validation**: Compare to survey data or other cities
12. **Pre-registration**: Specify analyses before seeing results (for future work)
13. **Data-driven season definitions**: Use clustering instead of calendar months
14. **Model selection**: AIC/BIC comparison of alternative specifications

---

## Conclusion

The bias correction methodology is ambitious and addresses important confounding. However, the **multiplicative weight stacking** raises concerns about effective sample size collapse and variance inflation. The analysis would be strengthened by:

1. Clearer articulation of the **causal estimand**
2. Restriction to **common support** regions
3. Comprehensive **sensitivity analyses**
4. Acknowledgment of **remaining limitations**

With these revisions, the work would make a strong contribution to the literature on revealed preference for thermal comfort in urban environments.

---

**Recommendation: Major Revision**

The methodology is sound in principle but requires additional validation, sensitivity analyses, and clearer articulation of assumptions before publication. The authors should particularly address the effective sample size collapse in some strata and provide evidence that bias reduction outweighs variance inflation.
