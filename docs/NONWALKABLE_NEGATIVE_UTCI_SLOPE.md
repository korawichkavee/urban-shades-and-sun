# Non-Walkable Streets: Negative UTCI–Shade Preference Slope

## 1. The Empirical Pattern

In the State College dataset, the binomial GLM fitted on non-walkable streets (primary
roads, cycleways, secondary roads) produces a **negative** association between UTCI
and shade preference: estimated shade-standing rates are *higher* in cold conditions
than in warm conditions.  This is the opposite of what is found on walkable streets,
and is counterintuitive from a shade-preference standpoint.

The underlying data are as follows (UTCI quartiles, non-walkable images only, n = 561):

| Quartile | UTCI (°C) | Shade pref | Shadow ratio | SR = 0 | Sun elevation |
|---|---|---|---|---|---|
| Q1 (coldest) | −5.0 | 52.2% | 0.207 | 38% | 23° |
| Q2 | +5.6 | 31.9% | 0.471 | 34% | — |
| Q3 | +13.8 | 24.2% | 0.340 | 37% | — |
| Q4 (warmest) | +25.6 | **5.6%** | **0.013** | **98%** | **66°** |

The pattern spans a 47 percentage-point range (5.6% to 52.2%), far larger than any
plausible behavioural effect.

---

## 2. Primary Mechanism: Shadow Supply Collapses in Warm Weather

The negative slope is **not a behavioural signal**.  It is almost entirely explained
by the geometry of shadows on primary roads across seasons.

### 2.1 Sun elevation drives shadow reach on wide carriageways

Primary roads in State College are wide, east–west aligned arterials.  The height of
adjacent buildings is modest relative to the carriageway width.  Shadow from a building
of height $h$ falls a horizontal distance $h / \tan(\theta)$ from the building face,
where $\theta$ is the solar elevation angle.

| Season | Solar elevation (non-walkable images) | Shadow reach |
|---|---|---|
| Winter / cold | ≈ 23° | $h / \tan(23°) \approx 2.4\,h$ — spans the carriageway |
| Summer / warm | ≈ 66° | $h / \tan(66°) \approx 0.45\,h$ — confined to the footpath |

In summer, building shadows never reach the centre of a primary road during the hours
captured in this dataset.  In winter, they drape across the full width.

### 2.2 Shadow ratio collapses to zero in the warmest quartile

In Q4 (UTCI ≈ 25.6°C, predominantly July images), **97.8% of non-walkable images have
`shadow_ratio = 0`** — no shadow falls on the road at all.  The 5.6% observed
"shade preference" in Q4 consists of the handful of people who happened to be near an
isolated shadow patch at a road edge; it does not represent active shade-seeking.

In Q1 (UTCI ≈ −5.0°C, predominantly February and October images), only 38% of images
have `shadow_ratio = 0`.  Long winter shadows are an ambient feature of the road
environment that pedestrians walk through regardless of preference.

### 2.3 Incidental shade-standing in cold weather inflates the cold-quartile estimate

The DCWP and IPW estimators assume that shade-standing is an **active choice** (A3 in
`docs/DCWP_METHOD.md`).  On primary roads with wide winter shadows, this assumption
fails: pedestrians are following a fixed route along the carriageway and happen to pass
through a shadow.  They have not deviated to seek shade; the shadow has deviated to
cover them.  The 52.2% "shade preference" in Q1 therefore overestimates true preference
for shade in cold conditions.

### 2.4 Summary of the mechanism

The GLM produces a negative UTCI slope because it is interpolating between two
confounded endpoints:

- **Cold**: shadow supply is high → many people incidentally in shadow → high apparent
  shade preference
- **Warm**: shadow supply is near-zero → almost nobody can be in shadow → near-zero
  apparent shade preference

The slope is a **shadow supply curve disguised as a preference curve**.

---

## 3. Secondary Factors

### 3.1 Non-representative seasonal sampling

The non-walkable image distribution is not evenly spread across months:

| Month | Images |
|---|---|
| October | 145 |
| July | 128 |
| February | 124 |
| November | 60 |
| April | 33 |
| Other | 71 |

The cold quartile is dominated by February and October images; the warm quartile is
almost entirely July.  The GLM is fitting on a bimodal seasonal distribution with very
few spring images, making the interpolated UTCI curve sensitive to these two seasonal
extremes rather than a continuous preference gradient.

### 3.2 IPW filter removes the summer observations entirely

The shadow ratio IPW filter (SR ≥ 0.05) removes 97.8% of Q4 (warm) images.  When
the IPW-adjusted estimate is computed for non-walkable streets at warm UTCI values,
it is extrapolating from the 2.2% of warm-season images that happen to have any shadow
coverage — an unrepresentative sample of an already small and unrepresentative group.
DCWP does not improve this because `dist_to_shade_m` is also large when SR = 0.

### 3.3 Small sample and dominant road type

Non-walkable streets are dominated by primary roads (n = 319) and cycleways (n = 170),
with only 41 secondary and 29 unknown.  The group is small (n = 561 vs 4,094 walkable)
and structured by two road types with completely different user populations.  Point
estimates in the warm quartile (n ≈ 136, but mostly SR = 0) are unreliable.

### 3.4 Time-of-day concentration

70% of non-walkable images were captured between 10am and 2pm.  Images at different
hours have different sun angles, which mechanically determines shadow coverage.  The
time-of-day distribution differs between cold and warm seasons (February images cluster
at 10–11am; July images at 13–14pm), contributing additional variation in SR that is
confounded with season and UTCI.

---

## 4. Corrections Missing from the Doubly-Adjusted Estimate

The IPW + DCWP combined estimator addresses two confounds: road-segment shade supply
(IPW) and point-level access cost to shade (DCWP).  Several important confounds remain
unaddressed.

### 4.1 Temperature activity selection (most important missing correction)

The metro SVI pipeline applies a **temperature IPW** derived from walk trip rates across
25 US travel surveys: it corrects for the fact that the composition of outdoor
pedestrians changes with temperature (more purposive cold-weather walkers; more
recreational warm-weather pedestrians).  This correction has **not** been applied to
the State College dataset.  Without it, the observed preference in cold weather reflects
the preferences of a self-selected cold-tolerant population, not the full population of
potential shade-seekers.

Applying the travel-survey temperature IPW to State College (using the same national
walk-trip-rate data already in use for the metro pipeline) is the most actionable
improvement to the current estimate.

### 4.2 Incidental shade-standing is not corrected

Both IPW and DCWP treat every shade-standing vote as evidence of active preference.
The DCWP method explicitly assumes (A3) that shade-standing is unconstrained: the
person chose to be in shade.  On primary roads in winter, this assumption fails —
pedestrians are in shadow because their route happens to pass through it, not because
they made a detour.  A correction for incidental shade-standing would require
distinguishing purposive from incidental presence, which is not possible from SVI alone.

The practical implication is that **shade preference estimates on non-walkable streets
in cold conditions are upward-biased** and should not be compared directly with
walkable street estimates.

### 4.3 Shadow supply collapse makes warm-season non-walkable estimates unreliable

When SR = 0 on nearly all images, both the IPW filter and the DCWP weight provide no
useful adjustment: there is nothing to reweight.  The warm-season non-walkable estimate
is effectively extrapolation.  No correction can recover preference signal that the
data do not contain.

A partial mitigation would be to use the DCWP-only estimate (no SR filter), which
retains all images with valid `dist_to_shade_m`.  On images with large
`dist_to_shade_m` and SR = 0, DCWP discounts sun-standing votes toward zero, which
shrinks the effective denominator and makes the aggregate preference undefined in the
limit.  This does not generate a preference estimate where none is possible, but it
does avoid the hard exclusion of the SR filter.

### 4.4 Time-of-day confounding

Sun angle at the time of image capture mechanically determines shadow coverage, and
the time-of-day distribution of images differs across road types and seasons.  The
current model includes UTCI (which incorporates radiation and temperature) but not
hour of day directly.  Adding an hour-of-day covariate or a solar elevation covariate
to the GLM would absorb residual variation in shadow supply that is not captured by
`shadow_ratio` (which is already the output of the shadow geometry model at that hour).

### 4.5 Pedestrian purpose and route-choice sorting

Pedestrians on primary roads have minimal route flexibility: they are crossing or
following the carriageway to a destination.  The assumption that observed sun/shade
standing reflects a preference comparison between sun and shade breaks down when the
pedestrian's lateral position is determined by the route, not by a comfort choice.
Cycleways are a related case: cyclists travel in designated lanes and have little
freedom to choose a shaded line.

Correcting for pedestrian purpose would require trip-type classification, which is not
available in SVI.  Stratifying estimates by road type — and treating non-walkable
streets as a separate, limited-inference population — is the defensible current approach.

### 4.6 Spatial clustering and image non-independence

Multiple SVI images from the same road segment, captured on the same day, have nearly
identical shadow conditions and similar pedestrian populations.  The binomial GLM with
`freq_weights` treats images as independent observations.  Within-segment correlation
inflates effective sample sizes and compresses standard errors.  A mixed model with a
random intercept per road segment or per capture day would be more appropriate,
particularly for the small non-walkable group.

### 4.7 Pedestrian detector reliability in shadow conditions

The YOLO pedestrian detector operates on raw imagery and has lower contrast sensitivity
in deep shadow under strong direct sun (high dynamic range scenes).  If the detector
preferentially misses shade-standing pedestrians in high-contrast summer images, shade
vote counts are systematically underestimated in exactly the conditions (warm, sunny)
where shade preference is most likely to be revealed.  Neither IPW nor DCWP corrects
for detector reliability; both treat the observed counts as ground truth.

### 4.8 Shade quality heterogeneity

`shadow_ratio` and `dist_to_shade_m` measure the *quantity* and *proximity* of shade
but not its *quality*.  A narrow shadow from a utility pole and deep canopy shade from
a mature oak both increment `inshade_count`.  Pedestrians may rationally avoid
low-quality shade even when it is nearby.  This bias is probably small relative to the
supply and access confounds, but it would push all four estimators (raw, IPW, DCWP,
combined) downward relative to true preference for comfortable shade.

---

## 5. Summary Table of Missing Corrections

| Correction | Mechanism | Likely magnitude | Addressable? |
|---|---|---|---|
| Temperature activity IPW | Self-selection into outdoor activity varies by temperature | Moderate (all streets); high for non-walkable cold | Yes — apply travel-survey IPW as in metro pipeline |
| Incidental shade-standing | Wide winter shadows place pedestrians in shade regardless of preference | High for primary roads in cold | Partially — road type stratification; note in caveats |
| SR = 0 filter → warm-season exclusion | IPW filter removes nearly all warm-season non-walkable images | High for non-walkable warm | Partially — DCWP-only analysis avoids hard filter |
| Time-of-day confounding | Sun angle at capture hour drives shadow coverage beyond what UTCI captures | Small–moderate | Yes — hour or solar elevation covariate |
| Pedestrian purpose / route flexibility | Primary road users cannot choose their lateral shade position | Structural; cannot be measured from SVI | Stratification by road type; caveat non-walkable inference |
| Spatial clustering | Within-segment images are correlated; standard errors underestimated | Small–moderate (variance) | Yes — GLMM or GEE with road-segment random effect |
| YOLO detection bias | Shadow/sun contrast degrades pedestrian detection in summer | Unknown; likely small | Requires detector calibration against ground truth |
| Shade quality heterogeneity | Not all shadow is equally comfortable or accessible | Small | Canopy/building shade classification from imagery |

---

## 6. Recommendation

The non-walkable UTCI curve is not a reliable estimate of behavioural shade preference
and should not be reported alongside the walkable curve as if it were.  The primary
drivers of the negative slope (shadow supply geometry and incidental cold-weather
shade-standing) are not addressable within the current estimation framework.

**Recommended approach:**

1. **Report walkable street estimates as the primary result.**  The walkable street
   population is behaviourally coherent (pedestrians have route flexibility), has
   adequate sample size (n = 4,094), and the IPW + DCWP estimators are well-grounded.

2. **Report non-walkable estimates with explicit caveats** about shadow supply collapse
   in warm weather, incidental shade-standing in cold weather, and the small sample.

3. **Apply the temperature activity IPW** (the most actionable missing correction) to
   both road type groups before the next round of analysis.

4. **Stratify** by specific road type within non-walkable (primary vs cycleway) rather
   than pooling — their user populations and shadow geometries differ substantially.

---

## Related Files

| File | Purpose |
|---|---|
| `docs/IPW_SHADOW_RATIO_METHOD.md` | Shadow ratio IPW, SR ≥ 0.05 filter |
| `docs/DCWP_METHOD.md` | DCWP formulation and τ |
| `docs/COMBINED_IPW_DCWP.md` | Combined IPW + DCWP and superadditivity |
| `docs/IPW_SHADE_PREFERENCE_METHOD.md` | Temperature activity IPW (metro pipeline) |
| `scripts/visualization/state_college/visualize_state_college_combined_ipw_dcwp.py` | Combined estimator plots |
| `data/state-college/state-college_svi_with_shadow.csv` | Input data |
