# Shadow Ratio IPW: Filter and Winsorisation

## Overview

Inverse probability weighting (IPW) adjusts raw shade preference estimates to account
for shadow availability — the intuition being that a person standing in the sun when no
shade exists reveals nothing about their preference, while the same behaviour when shade
is plentiful is strong evidence of sun preference.  Two pre-processing steps are
required before any weighted analysis: a **shadow ratio filter** and **weight
winsorisation**.  Both have substantial effects on the dataset and on what the
resulting estimates actually mean.

---

## 1. The Shadow Ratio Filter (SR < 0.05)

### What it does

Images are excluded if the fraction of the nearest road segment in shadow at capture
time (`shadow_ratio`) falls below 0.05.  In the State College dataset this removes
**3,066 of 4,655 voted images — 65.9%**.

| Category | Count | Share of voted |
|---|---|---|
| `shadow_ratio == 0.00` (no shadow at all) | 2,986 | 64.1% |
| `shadow_ratio 0.00–0.05` (near-zero) | 80 | 1.7% |
| **Total filtered** | **3,066** | **65.9%** |
| Retained (SR ≥ 0.05) | 1,589 | 34.1% |

### Why the filter is necessary

The IPW weight formula is `w = 1 / shadow_ratio`.  At SR = 0 this is undefined;
at SR = 0.01 it is 100 — an absurdly large amplification.  The filter is therefore
not an arbitrary modelling choice but a logical requirement: images with no meaningful
shadow access cannot be reweighted to a "shadow-rich" baseline because they contain no
information about shadow-related choice.

A person standing in the sun when `shadow_ratio = 0` has not expressed a preference
for sun — they had no alternative.  Retaining such observations and assigning them
infinite or very large weight would amplify noise, not signal.

### The threshold is not very sensitive here

2,986 of the 3,066 filtered rows have SR = 0.00 exactly.  Only 80 fall in the
0.00–0.05 grey zone.  Moving the threshold to 0.03 or 0.08 would change the retained
sample by at most ~80 images in either direction — less than 2% of voted rows.  The
vast majority of filtering is driven by hard zeros, not a borderline judgement call
about the threshold value.

### The filter is not random — this matters

Streets with `shadow_ratio = 0` are systematically different from streets with
`shadow_ratio ≥ 0.05`.  They tend to be wider, more open roads with less building and
tree cover, and are more likely to be classified as primary or secondary (non-walkable)
highway types.

**The images that survive the filter skew towards denser, more sheltered urban fabric.**
The IPW estimate therefore answers a narrower question than the raw estimate:

> *Among images where meaningful shadow access existed (SR ≥ 0.05), and standardising
> for how much shadow was available, what is the underlying shade preference?*

This is a well-defined and useful quantity, but it is not the same as "the shade
preference of State College pedestrians overall."

### Recommended diagnostic before reporting IPW results

Compare the distribution of key covariates between filtered and retained images:

- UTCI (thermal stress at time of capture)
- Road type mix (highway classification)
- Time of day
- Spatial distribution

If these differ substantially, the IPW estimate is not representative of the full
population, and any comparison to raw estimates should account for the compositional
shift — not only the difference in weighting.

### The filtered images are not worthless

The 65.9% of images discarded for IPW purposes carry a different kind of signal.
Those images were captured at locations where shade was not a real option.  They
characterise the *gap* between people's actual thermal experience and their likely
preference.  The locations where `shadow_ratio = 0` are precisely the locations where
infrastructure interventions (tree planting, canopies, building overhangs) would have
the greatest potential impact.

The most complete analysis uses both estimates in tandem:

- **Raw estimate**: characterises the gap between actual experience and latent
  preference; highlights underserved locations
- **IPW estimate**: characterises latent preference conditional on access; controls for
  the confounding effect of shadow availability on observed behaviour

---

## 2. Weight Winsorisation

### What it does

After filtering, the raw weight for each image is `w = 1 / shadow_ratio`.  These
weights are capped (winsorised) at the 95th percentile of the weight distribution
before use.

In the State College dataset:

| Statistic | Value |
|---|---|
| Winsorise cap (p95) | 12.93 |
| Minimum weight | 1.00 (at SR = 1.0) |
| Median weight | 1.41 |
| Mean weight (post-winsorise) | 2.78 |
| Maximum weight (post-winsorise) | 12.93 |

### Why winsorisation is necessary

The weight function `1/SR` is convex and diverges sharply near zero.  At the filter
boundary of SR = 0.05, the raw weight is already 20.  A small cluster of images with
SR just above the threshold would each be assigned 15–20× the influence of an image at
SR = 1.0.  If those images happen to show unusually high or low shade preference by
chance, they will dominate the weighted estimator entirely.

IPW estimators are unbiased in expectation but can have very high variance when weights
are large.  Winsorisation trades a small amount of bias for a large reduction in
variance — the standard bias-variance trade-off in robust estimation.  With 1,589
retained observations and a convex weight function, unwinsorised weights would make
the estimator unstable.

### The threshold choice is arbitrary and should be tested

p95 is a widely used default but is not derived from the data-generating process.  The
recommended approach is a **sensitivity analysis**: re-run the key results (shade
preference vs UTCI slope; road-type ranking) at p90, p95, and p99 and check whether
conclusions change.

- **Stable across thresholds** → winsorisation is working cleanly; the choice of
  quantile is not material
- **Results change between thresholds** → high-weight images are carrying substantive
  signal; the estimator is unstable; either tighten the SR filter or report results
  under multiple winsorisation schemes

### A more interpretable alternative

Rather than winsorising on the statistical distribution of weights, the cap can be set
on `shadow_ratio` directly.  For example, excluding SR < 0.10 sets a hard cap of
`max(w) = 10` with a direct physical interpretation: "we only analyse images where at
least 10% of the nearest road segment is in shadow."  This is more transparent than a
quantile-based cap and easier to justify to a non-statistical audience, at the cost of
a further reduction in sample size.

---

## 3. Combined Implications

Together, the filter and winsorisation define the estimand precisely:

> **The IPW shade preference estimate answers:** among pedestrians captured in images
> where at least 5% of the nearest road was in shadow, what proportion would choose
> shade if shadow access were equalised across all locations?

This is narrower than the raw estimate (which includes all voted images regardless of
access) and broader than a naïve "shade-seeker fraction" (which ignores that some
sun-standing pedestrians had no choice).

The two estimates should be read as complementary, not competing:

| Estimate | Population | Question answered |
|---|---|---|
| Raw | All voted images | What behaviour do we observe? |
| IPW | Images with SR ≥ 0.05 | What would behaviour be if shadow access were equal? |
| Difference | — | How much is observed behaviour driven by access vs preference? |

A large divergence between raw and IPW estimates at a given location or road type
indicates that shadow availability — not preference — is the primary driver of observed
behaviour there.  That is precisely where shade infrastructure investment is most
likely to change pedestrian behaviour.

---

## 4. Parameter Reference

| Parameter | Value used | Notes |
|---|---|---|
| `SR_MIN` | 0.05 | Shadow ratio filter threshold |
| `IPW_WINSOR_QUANTILE` | 0.95 | Percentile at which raw weights are capped |
| Winsorise cap (data-driven) | 12.93 | Actual p95 of `1/shadow_ratio` in retained sample |
| `MIN_OBS` | 15 | Minimum group size for GLM fitting |

All parameters are defined as constants at the top of
`scripts/visualization/state_college/visualize_state_college_ipw.py` and can be
adjusted for sensitivity testing without modifying any logic.

---

## 5. Related Files

| File | Purpose |
|---|---|
| `scripts/visualization/state_college/visualize_state_college_ipw.py` | Produces all IPW comparison plots |
| `scripts/visualization/state_college/visualize_state_college_shadow_ratio.py` | Raw shadow ratio plots (unweighted) |
| `data/state-college/state-college_svi_with_shadow.csv` | Input data with `shadow_ratio` column |
| `outputs/plots/state_college/ipw/` | Output plots |
| `docs/ADJUSTED_SHADE_PREFERENCE.md` | Overview of all three adjustment approaches (A, B, C) |
