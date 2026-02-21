# Adjusted Shade Preference: Accounting for Shadow Availability

## The Problem

Raw shade preference derived from SVI votes (fraction of people standing in shade vs. sun) is **biased by shadow availability**. A location with no shadows offers no real choice: a person standing in the sun there may well prefer shade but simply has no access to it. Treating that observation the same as a person standing in sun when shade is readily available overstates sun preference — or understates shade preference — at low-shadow locations.

This is a classic **revealed preference under constrained choice** problem. The observed behaviour conflates:
1. Actual preference (sun vs. shade)
2. Availability of the preferred option

### What observed behaviour actually implies

| Observed | `shadow_ratio` | Implication |
|---|---|---|
| Person in **sun** | 0.00 | **Uninformative** — no shadow available |
| Person in **sun** | 1.00 | **Strong sun preference** — shade was easily accessible |
| Person in **sun** | 0.50 | **Weak/moderate sun preference** — some shade accessible |
| Person in **shade** | any > 0 | **Shade preference** — chose available shade |

`shadow_ratio` here is the fraction of the nearest road segment that lies inside the shadow footprint at the time of image capture (0 = fully sun-exposed, 1 = fully shadowed).

---

## Approach A: Opportunity-Weighted Preference Score (Recommended)

### Intuition

Discount "sun votes" by the fraction of shadow available. A person standing in the sun when `shadow_ratio = 0.5` contributes only half as much evidence of sun preference as one standing in sun when `shadow_ratio = 1.0`. Shade votes are left unweighted (choosing shade is informative regardless of how much shadow is available).

### Formula

For each SVI location $i$ with votes $k_i$ (in shade) and $n_i - k_i$ (in sun):

$$\text{effective\_sun}_i = (n_i - k_i) \times \text{shadow\_ratio}_i$$

$$\text{effective\_total}_i = k_i + \text{effective\_sun}_i$$

$$\hat{p}_i = \frac{k_i}{\text{effective\_total}_i}$$

Where `shadow_ratio` = 0, sun votes are zeroed out — the image contributes no information (set to NaN and excluded from downstream analysis).

### Implementation

```python
df['effective_sun']   = df['outshade_count'] * df['shadow_ratio']
df['effective_shade'] = df['inshade_count']
df['effective_total'] = df['effective_shade'] + df['effective_sun']

df['adjusted_shade_pref'] = np.where(
    df['effective_total'] > 0,
    df['effective_shade'] / df['effective_total'],
    np.nan
)
```

### Filter recommendation

Exclude images where `shadow_ratio < 0.05` (near-zero availability makes the adjustment numerically unstable and the image is almost uninformative):

```python
df_valid = df[df['shadow_ratio'] >= 0.05].copy()
```

### Pros and Cons

| Pros | Cons |
|---|---|
| Intuitive, directly interpretable as a probability | Shade votes are not adjusted for availability (shade-full vs. shade-scarce) |
| Preserves absolute scale (still a 0–1 preference) | Collapses to NaN when `shadow_ratio = 0` |
| Simple to implement | Assumes linear relationship between availability and informational content |
| Consistent with standard revealed-preference corrections | |

---

## Approach B: Inverse Probability Weighting (IPW)

### Intuition

Reweight each image so that it represents what the distribution of behaviour would look like if every location had equal (full) shadow availability. Each image is upweighted by `1 / shadow_ratio`, standardising observations to a common "shadow-rich" baseline.

### Formula

For a binary outcome $Y_i$ (1 = in shade, 0 = in sun), the IPW estimator of the population-average shade preference is:

$$\hat{P}(\text{shade}) = \frac{\sum_i w_i \cdot Y_i}{\sum_i w_i}, \quad w_i = \frac{1}{\text{shadow\_ratio}_i}$$

For a regression context, include $w_i$ as observation weights in a GLM:

$$\text{logit}(p_i) = \alpha + \beta X_i, \quad \text{weighted by } w_i$$

### Implementation

```python
# Trim extreme weights (shadow_ratio near 0 → huge weights)
SR_MIN = 0.05
df_ipw = df[df['shadow_ratio'] >= SR_MIN].copy()
df_ipw['ipw'] = 1.0 / df_ipw['shadow_ratio']

# Winsorise at 95th percentile to reduce variance
cap = df_ipw['ipw'].quantile(0.95)
df_ipw['ipw_trimmed'] = df_ipw['ipw'].clip(upper=cap)

# Weighted GLM example
import statsmodels.api as sm
y = df_ipw[['inshade_count', 'outshade_count']].values
X = sm.add_constant(df_ipw['utci_C'])
model = sm.GLM(y, X, family=sm.families.Binomial(),
               freq_weights=df_ipw['ipw_trimmed']).fit()
```

### Pros and Cons

| Pros | Cons |
|---|---|
| Principled causal-inference framework | Sensitive to near-zero `shadow_ratio` (weights blow up) |
| Works naturally with regression models | Requires trimming/winsorising, adding a tuning decision |
| Well-established in epidemiology and economics | Does not produce an interpretable per-image adjusted score |
| Can control for multiple confounders simultaneously | Higher variance than Approach A |

---

## Approach C: Regression Residual

### Intuition

Fit a model predicting raw shade preference from shadow availability. The residual captures the component of shade preference that is **not explained by shadow availability** — i.e., genuine preference independent of access.

### Formula

$$\text{logit}(\hat{p}_i) = \alpha + \beta \cdot \text{shadow\_ratio}_i$$

$$\text{residual\_shade\_pref}_i = \text{logit}(p_i) - \text{logit}(\hat{p}_i)$$

Positive residual → more shade-seeking than the availability would predict.
Negative residual → more sun-seeking than availability would predict.

### Implementation

```python
import statsmodels.api as sm

df_r = df[df['total_votes'] > 0].copy()

# Binomial GLM: shade preference ~ shadow_ratio
y = df_r[['inshade_count', 'outshade_count']].values
X = sm.add_constant(df_r['shadow_ratio'])
model = sm.GLM(y, X, family=sm.families.Binomial()).fit()

df_r['pred_shade_pref'] = model.predict(X)
df_r['residual_shade_pref'] = (
    df_r['shade_pref'] - df_r['pred_shade_pref']
)
```

### Pros and Cons

| Pros | Cons |
|---|---|
| Simple to implement | Residual loses absolute level — cannot say "X% prefer shade" |
| Removes linear availability effect cleanly | Assumes linear (on logit scale) availability–preference relationship |
| Allows including other covariates in the same model | Residual interpretation requires care (relative, not absolute) |
| | Does not handle zero-shadow images as elegantly as Approach A |

---

## Comparison Summary

| | Approach A | Approach B | Approach C |
|---|---|---|---|
| **Output** | Adjusted probability (0–1) | Weighted aggregate or regression | Residual (centred at 0) |
| **Per-image score** | Yes | No (aggregate only) | Yes |
| **Handles shadow_ratio = 0** | NaN (excluded) | Excluded via filter | Poorly (need filter) |
| **Implementation complexity** | Low | Medium | Low–Medium |
| **Statistical robustness** | Medium | High | Medium |
| **Interpretability** | High | Medium | Low |
| **Recommended for** | Mapping, EDA, per-location scores | Causal inference, regression | Exploratory, covariate adjustment |

---

## Recommendation

**Use Approach A** for producing adjusted per-location shade preference scores for mapping and exploratory analysis. Its output is directly interpretable (probability of shade preference, corrected for availability), easy to communicate, and simple to implement.

**Use Approach B** (IPW) when the goal is causal inference — e.g., estimating the effect of UTCI or street type on shade preference while controlling for shadow availability. Combine with a `shadow_ratio >= 0.05` filter and weight winsorisation.

**Use Approach C** only if you want to include shadow availability as one covariate among several in a single regression model, and are comfortable with residual-based interpretation.

---

## Variable Reference

| Variable | Description |
|---|---|
| `inshade_count` | Number of people standing in shade in the SVI image |
| `outshade_count` | Number of people standing in sun in the SVI image |
| `total_votes` | `inshade_count + outshade_count` |
| `shade_pref` | `inshade_count / total_votes` (raw, uncorrected) |
| `shadow_ratio` | Fraction of nearest road segment in shadow at image capture time (0–1) |
| `in_shade_shadow` | Boolean: does the SVI capture point fall inside a shadow polygon |
| `adjusted_shade_pref` | Approach A corrected score (NaN where `effective_total = 0`) |
