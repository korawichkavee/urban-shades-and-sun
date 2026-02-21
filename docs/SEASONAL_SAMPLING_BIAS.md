# Seasonal Sampling Bias in Street View Imagery Analysis

## Problem Statement

Seasonal-level UTCI vs shade preference curves remain biased even after triple inverse probability weighting (SR-IPW + DCWP + Temp-IPW). The bias arises from **non-random seasonal variation in spatial and temporal sampling** of street view imagery (SVI). While triple IPW successfully corrects for within-season biases (shadow supply, shade access cost, and activity levels), it does not address the fundamental issue that different seasons sample different spatial and thermal environments.

### Key Assumption
Individuals pictured in SVI are **interchangeable at the city level**: any person in any image is equally representative of the city's behavioral preferences. Under this assumption, differences in seasonal estimates should reflect true seasonal variation in preferences, not artifacts of which streets were photographed when.

---

## Sources of Seasonal Sampling Bias

### 1. Spatial Coverage Heterogeneity Across Seasons

Street view collection is opportunistic and incomplete. In State College:

- **Fall**: 1,787 images (38.4%) with widest spatial coverage
- **Spring**: 1,426 images (30.6%)
- **Winter**: 770 images (16.5%) - limited coverage, likely arterials only
- **Summer**: 672 images (14.4%) - most spatially restricted

**Consequence**: If winter images oversample busy streets near campus while summer images oversample residential neighborhoods, estimated preferences conflate *spatial heterogeneity* with *seasonal variation*.

**Example**: Suppose students (high shade preference) concentrate near campus, while families (lower preference) concentrate in suburbs. If winter = campus streets and summer = suburban streets, winter will appear to have higher shade preference even if true seasonal preferences are identical.

### 2. Temperature Range Truncation by Season

Each season observes a restricted UTCI range:

- **Winter**: -44.3°C to 1.7°C (cold only)
- **Summer**: 8.7°C to 27.3°C (warm only)
- **Spring/Fall**: Overlapping intermediate ranges

**Consequence**: Seasonal curves extrapolate beyond observed data. The winter curve at 20°C is pure extrapolation from cold-weather observations. If the true preference function is non-monotonic or has seasonal shifts, polynomial GLMs fitted to truncated ranges will produce misleading seasonal comparisons.

### 3. Temporal Confounding with Activity Patterns

Collection times vary by season:

- **Commute-time analysis** shows Fall dominates (55% of commute-time people)
- Different seasons may sample different times of day due to photographer behavior

**Consequence**: Even with Temp-IPW, if seasons systematically differ in *who is outside* (students vs workers vs tourists), estimated preferences reflect population composition, not seasonal preference shifts.

### 4. Photographer Selection Bias

Mapillary contributors may preferentially photograph:
- Pleasant weather conditions (mild temps, sunny days)
- Accessible streets (plowed in winter, not flooded in spring)
- Interesting locations (downtown in summer, campus in fall)

**Consequence**: Selection into the dataset is non-random with respect to both season and unobserved preference heterogeneity.

---

## Why Triple IPW Is Insufficient

Triple IPW corrects for:

1. **SR-IPW**: Shadow supply bias (reweights images to simulate balanced shadow availability)
2. **DCWP**: Shade access cost (downweights sun-standing pedestrians near shade)
3. **Temp-IPW**: Activity level variation (reweights to simulate constant walking activity)

**What it does NOT correct**:
- **Spatial imbalance**: Different streets sampled across seasons
- **Temperature truncation**: Extrapolation beyond observed ranges
- **Population composition**: Different people types photographed in different seasons

Triple IPW assumes the **treatment** (shadow ratio, distance to shade, temperature) is randomly assigned conditional on observables. But **season** itself acts as an unmeasured confounder that determines which streets, times, and populations enter the sample.

---

## Proposed Correction Methods

### Method 1: Spatial Post-Stratification (Recommended)

**Motivation**: Survey methodology literature on raking and post-stratification (Gelman & Hill 2006; Mercer et al. 2018).

**Approach**:
1. Define spatial strata (e.g., grid cells, street segments, or neighborhoods)
2. Compute overall spatial sampling distribution across all seasons
3. Within each season, reweight observations so spatial distribution matches overall
4. Apply quadruple weighting: `w_final = w_triple_ipw × w_spatial_poststrat`

**Implementation**:
```python
# Compute overall spatial distribution
df['grid_cell'] = assign_grid_cell(df['lat'], df['lon'], cell_size=500m)
overall_spatial_dist = df.groupby('grid_cell').size() / len(df)

# For each season
for season in seasons:
    season_df = df[df['season'] == season]
    season_spatial_dist = season_df.groupby('grid_cell').size() / len(season_df)

    # Post-stratification weight
    df.loc[df['season'] == season, 'w_spatial'] = (
        overall_spatial_dist[df['grid_cell']] /
        season_spatial_dist[df['grid_cell']]
    )

    # Final weight
    df.loc[df['season'] == season, 'w_final'] = (
        df['w_triple_ipw'] * df['w_spatial']
    )
```

**Strengths**:
- Standard approach in survey sampling
- Directly addresses spatial imbalance
- Interpretable: "reweights season to match overall spatial footprint"

**Limitations**:
- Requires sufficient spatial overlap across seasons
- Can produce extreme weights if some cells only appear in one season
- Does not address temperature truncation

---

### Method 2: Propensity Score Weighting for Season Assignment

**Motivation**: Causal inference literature on observational studies (Rosenbaum & Rubin 1983; Imbens & Rubin 2015).

**Approach**:
1. Model probability of being sampled in season $s$ given observables:
   $$P(\text{season} = s \mid \text{location}, \text{time}, \text{weather})$$
2. Weight observations by inverse propensity: `w_season = 1 / P(season = s | X)`
3. Combine with triple IPW: `w_final = w_triple_ipw × w_season`

**Implementation**:
```python
from sklearn.linear_model import LogisticRegression

# Features predicting season assignment
X = df[['lat', 'lon', 'hour', 'day_of_week', 'is_weekend',
        'highway_type', 'distance_to_downtown']]

# Multinomial logit for season
model = LogisticRegression(multi_class='multinomial')
model.fit(X, df['season'])
propensity = model.predict_proba(X)  # P(season | X)

# Inverse propensity weight
df['w_propensity'] = 1.0 / propensity[np.arange(len(df)),
                                       df['season'].cat.codes]
df['w_final'] = df['w_triple_ipw'] * df['w_propensity']
```

**Strengths**:
- Principled causal inference framework
- Balances all observables simultaneously
- Can assess covariate balance after weighting

**Limitations**:
- Assumes no unmeasured confounders (strong assumption)
- Propensity model misspecification propagates to estimates
- Extreme weights if seasons have little overlap in covariate distributions

---

### Method 3: Hierarchical Spatial Model with Season Interactions

**Motivation**: Multilevel modeling for spatial data (Gelman & Hill 2006; Diggle & Ribeiro 2007).

**Approach**:
1. Specify hierarchical GLM with spatial random effects:
   $$
   \begin{align}
   \text{inshade}_i &\sim \text{Binomial}(n_i, p_i) \\
   \text{logit}(p_i) &= \beta_0 + \beta_1 \text{UTCI}_i + \beta_2 \text{UTCI}_i^2 \\
   &\quad + \gamma_s + \gamma_s \times (\beta_1 \text{UTCI}_i + \beta_2 \text{UTCI}_i^2) \\
   &\quad + \alpha_{j[i]} \\
   \alpha_j &\sim \text{Normal}(0, \sigma^2_{\text{spatial}})
   \end{align}
   $$
   where $\gamma_s$ are season-specific intercepts and slopes, $\alpha_j$ are spatial random effects (e.g., street segment or grid cell).

2. Estimate via MCMC (Stan, PyMC) or penalized likelihood (lme4, statsmodels)

3. Marginal season effects integrate over spatial distribution:
   $$\text{E}[p \mid \text{UTCI}, \text{season}] = \text{E}_{\alpha}[p \mid \text{UTCI}, \text{season}, \alpha]$$

**Implementation**:
```python
import pymc as pm

with pm.Model() as model:
    # Spatial random effects
    sigma_spatial = pm.HalfNormal('sigma_spatial', sigma=1)
    alpha = pm.Normal('alpha', mu=0, sigma=sigma_spatial,
                     shape=n_spatial_units)

    # Season-specific coefficients
    beta_season = pm.Normal('beta_season', mu=0, sigma=1, shape=4)
    beta_utci_season = pm.Normal('beta_utci_season', mu=0, sigma=1, shape=4)

    # Linear predictor
    eta = (beta_season[season_idx] +
           beta_utci_season[season_idx] * utci +
           alpha[spatial_idx])

    # Likelihood
    p = pm.invlogit(eta)
    y = pm.Binomial('y', n=n_total, p=p, observed=n_shade,
                   shape=len(df))
```

**Strengths**:
- Explicitly models spatial dependence
- Separates within-location from between-location variation
- Provides uncertainty quantification via posterior

**Limitations**:
- Computationally intensive (MCMC required for inference)
- Requires careful prior specification
- Assumes spatial units are observed in multiple seasons (may not hold)

---

### Method 4: Temperature Range Standardization via Kernel Reweighting

**Motivation**: Matching and weighting in observational studies (Hainmueller 2012; Kallus 2020).

**Approach**:
1. Define target temperature distribution (e.g., pooled across all seasons)
2. For each season, reweight observations to match target via kernel balancing:
   $$w_i \propto \frac{f_{\text{target}}(\text{UTCI}_i)}{f_{\text{season}}(\text{UTCI}_i)}$$
3. Combine with triple IPW

**Implementation**:
```python
from scipy.stats import gaussian_kde

# Target distribution (all seasons pooled)
kde_target = gaussian_kde(df['utci_C'])

# Season-specific reweighting
for season in seasons:
    season_df = df[df['season'] == season]
    kde_season = gaussian_kde(season_df['utci_C'])

    # Density ratio weight
    w_temp = kde_target(season_df['utci_C']) / kde_season(season_df['utci_C'])
    df.loc[df['season'] == season, 'w_temp_range'] = w_temp

# Normalize and combine
df['w_temp_range'] /= df.groupby('season')['w_temp_range'].transform('mean')
df['w_final'] = df['w_triple_ipw'] * df['w_temp_range']
```

**Strengths**:
- Directly addresses temperature truncation
- Non-parametric (no functional form assumptions)

**Limitations**:
- Extrapolation still required outside observed ranges
- Can produce extreme weights at range boundaries
- Doesn't address spatial imbalance

---

### Method 5: Instrument-Free Panel Data Approach (Acknowledge Limitations)

**Motivation**: Panel econometrics for observational data (Angrist & Pischke 2009).

**Approach**:
Accept that clean seasonal comparisons are **not identified** from this data. Instead:

1. Report **pooled** (all-season) estimate as primary result
2. Report seasonal estimates as **descriptive** with explicit caveats
3. Bound true seasonal effects via sensitivity analysis:
   - Best case: Assume no spatial confounding → seasonal curves as reported
   - Worst case: Assume seasonal differences entirely due to spatial sampling → no seasonal variation in preferences
   - Realistic: Partial sensitivity (e.g., E-value for unmeasured confounding)

**Documentation**:
```markdown
## Seasonal Estimates: Interpretive Cautions

Seasonal UTCI curves should be interpreted as **season-conditional descriptives**,
not causal seasonal effects. Differences may reflect:
1. True seasonal preference variation
2. Spatial sampling differences (Fall = downtown, Summer = residential)
3. Temperature range extrapolation artifacts
4. Population composition shifts (students in Fall, tourists in Summer)

**Recommendation**: Use pooled estimate for inference. Seasonal curves provide
qualitative patterns but are not directly comparable without additional assumptions.
```

**Strengths**:
- Honest about limitations
- Avoids overconfident claims
- Focuses attention on better-identified pooled estimate

**Limitations**:
- Does not provide seasonal comparisons (which user wants)
- May be unsatisfying if seasonal variation is of substantive interest

---

## Recommended Approach

**Primary**: **Method 1 (Spatial Post-Stratification)** + **Method 4 (Temperature Range Standardization)**

**Rationale**:
1. Spatial post-stratification directly addresses the most severe bias (different streets photographed)
2. Temperature range standardization ensures seasonal comparisons at matched UTCI values
3. Both methods are non-parametric and well-established in survey/causal literature
4. Combined, they address both spatial and thermal sampling imbalances
5. Computational feasibility (no MCMC required)

**Implementation**:
```python
# Step 1: Spatial post-stratification
df['grid_cell'] = assign_spatial_strata(df)
overall_spatial = df.groupby('grid_cell').size() / len(df)

for season in ['Winter', 'Spring', 'Summer', 'Fall']:
    season_mask = df['season'] == season
    season_spatial = df[season_mask].groupby('grid_cell').size() / season_mask.sum()
    df.loc[season_mask, 'w_spatial'] = (
        overall_spatial.loc[df.loc[season_mask, 'grid_cell']].values /
        season_spatial.loc[df.loc[season_mask, 'grid_cell']].values
    )

# Step 2: Temperature range standardization
kde_target = gaussian_kde(df['utci_C'])
for season in ['Winter', 'Spring', 'Summer', 'Fall']:
    season_mask = df['season'] == season
    kde_season = gaussian_kde(df.loc[season_mask, 'utci_C'])
    w_temp = kde_target(df.loc[season_mask, 'utci_C']) / \
             kde_season(df.loc[season_mask, 'utci_C'])
    df.loc[season_mask, 'w_temp_range'] = w_temp / w_temp.mean()

# Step 3: Combine with triple IPW
df['w_final'] = df['w_triple_ipw'] * df['w_spatial'] * df['w_temp_range']

# Step 4: Truncate extreme weights (winsorize at 99th percentile)
df['w_final'] = df['w_final'].clip(upper=df['w_final'].quantile(0.99))

# Step 5: Normalize within season
df['w_final'] = df.groupby('season')['w_final'].transform(
    lambda x: x / x.mean()
)
```

**Sensitivity Check**:
- Compare seasonal estimates with and without adjustment
- Report effective sample sizes after weighting: `n_eff = (Σw)² / Σw²`
- Assess covariate balance: Do seasons have similar spatial/UTCI distributions after weighting?

---

## Alternative: Restrict to Spatially Balanced Subset

If weighting produces extreme weights or insufficient overlap, consider:

**Subset Analysis**:
1. Identify spatial units (street segments, grid cells) observed in **all four seasons**
2. Restrict analysis to this balanced subset
3. Estimate seasonal curves on matched spatial footprint

**Trade-off**:
- **Pro**: Eliminates spatial confounding by design (no weighting needed)
- **Con**: Drastically reduces sample size (may lose statistical power)
- **Con**: Subset may not be representative of city (e.g., only major arterials photographed year-round)

**When to use**: If post-stratification weights exceed 10:1 ratio, indicating severe imbalance.

---

## Conclusion

Seasonal UTCI vs preference curves from opportunistic SVI are biased by non-random spatial and temporal sampling. While triple IPW corrects important within-season confounders, it cannot address between-season sampling differences.

**Recommended solution**: Combine spatial post-stratification with temperature range standardization to reweight seasonal samples toward a common spatial and thermal distribution. This approach:
- Leverages established survey methodology (post-stratification)
- Directly targets the two main confounders (space and temperature range)
- Remains computationally tractable
- Produces interpretable adjusted weights

**Honest reporting**: Even with adjustment, seasonal estimates should be presented with appropriate uncertainty and caveats about unmeasured confounding. The pooled (all-season) estimate remains the most credible parameter for population-level shade preferences.

---

## References

- Angrist, J. D., & Pischke, J. S. (2009). *Mostly Harmless Econometrics*. Princeton University Press.
- Diggle, P. J., & Ribeiro, P. J. (2007). *Model-Based Geostatistics*. Springer.
- Gelman, A., & Hill, J. (2006). *Data Analysis Using Regression and Multilevel/Hierarchical Models*. Cambridge University Press.
- Hainmueller, J. (2012). Entropy balancing for causal effects. *Political Analysis*, 20(1), 25-46.
- Imbens, G. W., & Rubin, D. B. (2015). *Causal Inference for Statistics, Social, and Biomedical Sciences*. Cambridge University Press.
- Kallus, N. (2020). Generalized optimal matching methods for causal inference. *Journal of Machine Learning Research*, 21(62), 1-54.
- Mercer, A. W., Kreuter, F., Keeter, S., & Stuart, E. A. (2018). Theory and practice in nonprobability surveys. *Public Opinion Quarterly*, 81(S1), 250-271.
- Rosenbaum, P. R., & Rubin, D. B. (1983). The central role of the propensity score in observational studies for causal effects. *Biometrika*, 70(1), 41-55.
