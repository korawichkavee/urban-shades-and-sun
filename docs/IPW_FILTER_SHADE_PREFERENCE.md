# Shade Preference in Filtered vs Retained Images

## Summary

The IPW shadow ratio filter (SR < 0.05) removes 65.9% of voted images.  A natural
concern is that this discards images that carry genuine shade preference signal —
i.e. that the filtered images look systematically different from the retained ones and
their exclusion biases the analysis.

The data show this concern is **partially justified but misframes the problem**.
The filtered images *do* contain shade preference signal — 38.7% of SR=0 images
have at least one person in shade, and the mean shade preference in the filtered group
(27.5%) is only ~7 percentage points below the retained group (34.5%).  The filter
is not removing "all-sun, no-preference" images; it is removing images where the
*interpretation* of sun-standing is ambiguous.  That ambiguity — not the absence of
preference — is the justification for exclusion.

---

## Data

Voted sunny images from State College SVI with at least 1 person observed
(`inshade_count + outshade_count ≥ 1`).  Total: 4,655 images.

---

## Results by Shadow Ratio Band

| Band | Status | n | Mean shade pref | Any in shade | All in shade | None in shade |
|---|---|---|---|---|---|---|
| SR = 0 (no shadow) | Filtered | 2,986 | 27.5% | 38.7% | 18.7% | 61.3% |
| 0 < SR < 0.05 | Filtered | 80 | 25.1% | 37.5% | 18.8% | 62.5% |
| 0.05–0.10 | Kept | 110 | 35.3% | 46.4% | 26.4% | 53.6% |
| 0.10–0.25 | Kept | 182 | 30.3% | 37.9% | 24.2% | 62.1% |
| 0.25–0.50 | Kept | 263 | 34.1% | 43.7% | 26.6% | 56.3% |
| 0.50–0.75 | Kept | 299 | 39.6% | 52.2% | 30.4% | 47.8% |
| 0.75–1.0 | Kept | 735 | 33.6% | 48.7% | 23.0% | 51.3% |

"Any in shade" = at least one person in shade (shade_pref > 0).
"All in shade" = everyone in shade (shade_pref = 1).
"None in shade" = everyone in sun (shade_pref = 0).

---

## Key Observations

### 1. The filtered images contain non-trivial shade preference

The SR=0 group has a mean shade preference of 27.5% and 38.7% of images have at
least one person in shade.  18.7% have *everyone* in shade.  These are not
zero-preference observations.

This is the most counterintuitive result: if `shadow_ratio = 0` means the nearest
road segment is fully sun-exposed, how can people be standing in shade in 38.7% of
those images?  The most likely explanation is that the `shadow_ratio` metric — the
fraction of the nearest OSM road segment in shadow at capture time — is an imperfect
proxy for actual shade access.  People can access shade from:

- Building setbacks and recessed doorways not captured by the road segment geometry
- Trees or canopies not mapped in OSM
- Neighbouring streets or footpaths just outside the shadow footprint
- The image capture point being slightly offset from the pedestrian's actual location

In other words, the road segment shadow metric underestimates local shade access,
particularly in dense urban fabric.  Some SR=0 images are genuinely shade-free; others
are at locations where shade exists but is not captured by the metric.

### 2. The relationship between shadow ratio and shade preference is weak and non-monotone

The band means range from 25.1% (0 < SR < 0.05) to 39.6% (SR = 0.50–0.75), but
the pattern is not monotone: the SR = 0.75–1.0 band drops back to 33.6%, below the
SR = 0.05–0.10 band (35.3%).  A rolling mean over the full continuous range is nearly
flat.  This flatness is the key visual result from panel D: shadow availability as
measured by `shadow_ratio` does not strongly predict observed shade preference in the
raw data.

There are two plausible interpretations:

- **Measurement noise dominates**: `shadow_ratio` is computed at the nearest road
  segment centroid, not at the pedestrian's precise location, and is rounded to the
  nearest hour.  Substantial spatial and temporal mismatch introduces noise that
  attenuates the signal.
- **Preference is largely constant across locations**: people's underlying shade
  preference may not vary much with SR — what varies is their *ability* to act on it.
  The IPW correction is then recovering a preference signal that is suppressed at
  low-SR locations, not one that is absent.

### 3. The distribution is heavily zero-inflated at all SR levels

The median shade preference is 0.0 in every band.  Most images have everyone in sun.
The shade preference "signal" sits entirely in the upper tail — images where at least
one person is in shade.  This structure means means are poor summaries; the more
informative quantities are the "any shade" and "all shade" proportions, which do show
a clearer gradient across bands (38.7% → 52.2% as SR increases from 0 to 0.50–0.75).

### 4. The filter is justified on logical grounds, not behavioural separation

Because the filtered and retained images look broadly similar in terms of shade
preference, one might argue the filter is unnecessary.  The counterargument is
methodological, not empirical: the IPW weight `1/SR` is defined as a correction for
the *probability* that shade is accessible.  At SR=0, that probability is (by
definition of the metric) zero.  Assigning weight `1/0 = ∞` is undefined.  At SR=0.02
the weight is 50 — amplifying each observation 50-fold.  The filter is required
because the weighting framework breaks down, not because the filtered images have zero
preference.

Put differently: a person standing in sun at SR=0 may well prefer shade, but their
observed behaviour (sun-standing) cannot be corrected to a "shadow-rich" counterfactual
because we have no information about what they would have done if shade were available.
Their preference is real but unidentifiable from this data source.

---

## Implication for Interpretation

The fact that filtered images contain preference signal has two consequences:

**1. The IPW estimate is conservative.**  By excluding all SR<0.05 images, we
discard some genuine shade-preference signal (the ~38.7% who were in shade despite
SR=0).  The IPW estimate of shade preference under full shadow access is therefore
likely an underestimate of the true population preference.  The retained sample skews
towards people in locations with some shadow access; the most shadow-deprived locations
are excluded entirely.

**2. The filtered images characterise unmet demand.**  The 61.3% of SR=0 images
where everyone is in sun, at locations with no shadow access, is the most direct
empirical signal of unmet shade demand in the dataset.  These are people who cannot
seek shade even if they want to.  The 18.7% where everyone is in shade at SR=0
locations illustrates that shadow_ratio underestimates real access, but the 61.3%
majority is the policy-relevant group.

The most complete analysis treats the two groups as answering different questions:

| Group | Question |
|---|---|
| SR < 0.05 (filtered) | Where is shade infrastructure missing, and what is the scale of constrained exposure? |
| SR ≥ 0.05 (retained) | What is the latent shade preference of people who have meaningful shade access? |

---

## Caveats on shadow_ratio as a Metric

The finding that 38.7% of SR=0 images contain shade-seekers suggests the metric has
meaningful measurement error.  Specific sources:

- **Temporal mismatch**: shadow_ratio is computed at the nearest UTC hour; image
  capture may be up to 30 minutes off, shifting shadow footprints substantially
- **Spatial mismatch**: the SVI point is snapped to the nearest OSM road segment
  centroid; the actual pedestrian may be on a side path or set back from the road
- **OSM incompleteness**: trees and small canopy structures are under-mapped in OSM,
  especially in residential areas, causing the shadow model to undercount shade
- **3D microenvironment**: building facades, awnings, and parked vehicles cast shadow
  not captured by the 2D footprint model

These sources of noise attenuate the `shadow_ratio → shade_preference` relationship
and reduce the statistical power of the IPW correction.  They also imply that a
higher SR filter threshold (e.g. SR ≥ 0.10) might better isolate "genuinely
accessible" shadow from measurement noise, at the cost of further reducing sample size.

---

## Related Files

| File | Purpose |
|---|---|
| `scripts/visualization/state_college/visualize_state_college_ipw_filter_check.py` | Produces the four-panel comparison plot |
| `outputs/plots/state_college/ipw/ipw_filter_shade_preference.png` | Output figure |
| `docs/IPW_SHADOW_RATIO_METHOD.md` | Filter and winsorisation methodology |
| `docs/ADJUSTED_SHADE_PREFERENCE.md` | Overview of all adjustment approaches |
