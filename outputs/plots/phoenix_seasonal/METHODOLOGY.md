# Visualization Methodology

## Data and Filtering
- **Data source**: Phoenix street view imagery with UTCI (Universal Thermal Climate Index) weather data
- **Filtering criteria**:
  1. Sunny images only (`is_sunny = True`)
  2. At least one person detected (`total_people > 0`)
  3. Valid shade counts (no missing data)
  4. Valid UTCI data
- **Response variable**: Proportion of people in shade = (people in shade) / (total people)
  - Bounded between 0 and 1
  - Aggregated count data (not individual binary outcomes)
- **Predictor**: UTCI temperature in °C

## Statistical Method: Binomial Generalized Additive Model (GAM)

### Why Binomial GAM?

This is the **statistically appropriate method** for our data because:

1. **Proper distribution for proportions**: The response is proportion data (bounded 0-1), which violates assumptions of linear regression
2. **Binomial family**: Models count data (k successes out of n trials) with logit link function
3. **Handles heteroskedasticity**: Variance naturally changes with the mean for proportions (variance = np(1-p))
4. **Non-linear relationships**: Smoothing splines allow flexible, non-linear curves without assuming a parametric form
5. **Proper confidence intervals**: CIs respect the [0,1] bounds and account for uncertainty in both the smooth function and binomial variance

### Model Specification

```
logit(E[shade_ratio]) = f(UTCI)

where:
- f() is a smooth function represented by B-splines
- logit(p) = log(p/(1-p)) ensures predictions stay in [0,1]
- Response: [n_in_shade, n_not_in_shade] ~ Binomial
```

### Smoothing Parameter
- **B-spline basis** with **df=4** (4 degrees of freedom)
- Controls flexibility of the smooth curve
- Higher df = more wiggly, lower df = smoother
- **df=4 chosen because**:
  - Minimum df for degree=3 cubic splines (technical constraint: df >= degree + 1)
  - Phoenix data has only 5-9 unique UTCI values per season
  - B-splines require df < (n_unique_x - 1) for proper fitting
  - df=4 provides smooth, interpretable curves without overfitting sparse data
  - Assumes smooth behavioral response to temperature (reasonable assumption)

### Confidence Intervals
- **95% CIs** computed from the fitted GAM
- Based on the posterior covariance matrix of the spline coefficients
- Account for both:
  1. Uncertainty in the smooth function (estimation uncertainty)
  2. Binomial variance in the data
- CIs are on the probability scale (inverse-logit transformed)

### Why Not LOESS?

LOESS (used in initial version) has drawbacks for proportion data:
- **No distributional assumption**: Treats proportions as continuous unbounded data
- **Can predict outside [0,1]**: No guarantee fitted values respect bounds
- **Homoskedastic errors assumed**: Doesn't account for changing variance with proportion
- **CI calculation unclear**: Bootstrap CIs don't account for binomial structure

## Overall Plot
- Shows **ALL data combined** (colored by season for visual reference)
- **Single GAM fit** across the entire dataset
- Represents the overall relationship between UTCI and shade-seeking in Phoenix
- Not separate fits per season - this is a single model using all observations

## Seasonal Plots
- Separate GAM fits for Spring, Summer, Fall, Winter
- Allow examination of whether the temperature-shade relationship varies by season
- Requires sufficient data (n ≥ 30) for reliable fitting

## Data Visualization
- **Scatter points**: Individual image observations (with small jitter for visibility)
- **Solid line**: GAM predicted probability of shade-seeking
- **Shaded region**: 95% confidence interval for the predicted probability

## Limitations
1. **Observational data**: Cannot establish causation
2. **Sparse data regions**: CIs widen where observations are sparse (temperature extremes)
3. **Seasonal confounding**: Temperature and season correlate; effects may be confounded
4. **Zero-inflation**: Many observations have shade_ratio = 0 or 1
5. **Pseudo-replication**: Multiple images may be from same location/sequence
6. **Sample size per image varies**: Some images have 1 person, others have multiple
   - GAM accounts for this by using the binomial structure (n_trials varies)

## Interpretation

The fitted curve shows the **predicted probability** that a person will be in shade as a function of UTCI temperature, accounting for:
- The binomial nature of the data
- Non-linear relationships
- Uncertainty in both model parameters and binomial sampling

## References
- Wood, S. N. (2017). *Generalized Additive Models: An Introduction with R* (2nd ed.). CRC Press.
- McCullagh, P., & Nelder, J. A. (1989). *Generalized Linear Models* (2nd ed.). Chapman & Hall.
- Hastie, T., & Tibshirani, R. (1990). *Generalized Additive Models*. Chapman & Hall.

## Software
- Python 3.12
- statsmodels GAM implementation
- Binomial family with logit link
- B-spline basis functions
