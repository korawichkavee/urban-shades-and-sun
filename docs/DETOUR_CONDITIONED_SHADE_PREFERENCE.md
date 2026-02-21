# Detour-Conditioned Shade Preference

## Motivation

The `shadow_ratio` IPW method adjusts for **shade supply at the road segment level**: it
reweights images by how much of the nearest road segment was in shadow at capture time,
standardising to a "shadow-rich" baseline.  This is a sound correction for the aggregate
supply of shade, but it does not capture whether any particular pedestrian was *close* to
the shadow.

Two pedestrians can be on the same road segment with the same `shadow_ratio = 0.5`, yet
one may be standing 2 m from a shadow patch while the other is 45 m away.  The
behavioural interpretation of their sun-standing is completely different: the first is
expressing a strong preference for sun; the second may simply not have bothered with a
45 m detour.  `shadow_ratio` is identical in both cases.

`dist_to_shade_m` — the distance from the SVI capture point to the nearest shadow
boundary — is a **point-level access cost**.  This document describes a method that uses
it to condition shade preference estimates on the cost of reaching shade, rather than on
the supply of shade on the road.

---

## The Key Variable: `dist_to_shade_m`

`dist_to_shade_m` is computed by `add_shadow_to_state_college.py` as the Euclidean
distance from the SVI point (projected to local UTM) to the nearest edge of any shadow
polygon, at the capture time rounded to the nearest UTC hour.

Its semantics differ depending on whether the SVI point is inside a shadow:

| `in_shade_shadow` | `dist_to_shade_m` | Meaning |
|---|---|---|
| `True`  | 0.0 | Point is inside a shadow polygon (shade access at zero additional detour) |
| `False` | > 0 | Point is outside shadow; value is metres to nearest shadow edge |
| Either  | NaN | Sun below horizon at capture time — no shadow modelled |

When `dist_to_shade_m = 0`, shade is present at the SVI location itself.  When it is,
say, 12 m, the pedestrian would need to walk roughly 12 m off their current path to
reach any shade.

---

## The Estimand

> Among pedestrians observed at locations where the nearest shade was within *D* metres,
> what fraction chose to be in shade?

For a given detour threshold *D*, this is estimated straightforwardly:

```
p̂(shade | dist ≤ D) = Σ inshade_count  /  Σ total_count
                        over all images with dist_to_shade_m ≤ D
```

Because `dist_to_shade_m = 0` for all in-shadow SVI points, the filter
`dist_to_shade_m ≤ D` automatically includes every in-shadow point for any D ≥ 0, and
adds progressively more out-of-shadow points as D grows.

---

## The Detour-Tolerance Curve

The core analytical product is a curve of p̂(shade | dist ≤ D) plotted against D,
evaluated at a grid of thresholds (e.g. 0, 5, 10, 20, 30, 50, 75, 100 m).

### Expected shape

- **D = 0**: Only in-shadow SVI points.  The people visible here are mostly already in
  shade by default; the estimate reflects a mixture of active choice and accidental
  presence.  This is the highest expected shade preference, but the weakest revealed
  preference signal (we cannot tell who chose to enter the shadow).

- **Small D (5–20 m)**: Adds people at locations just outside the shadow boundary.
  Sun-standing here is a clear active choice — shade was a few metres away.  These are
  the observations with the strongest revealed sun preference signal.  If the preference
  estimate drops quickly between D = 0 and D = 20, that means many people who had shade
  very close by chose sun anyway.

- **Large D (50–100 m)**: Adds people who would need a substantial detour to reach
  shade.  Sun-standing at these distances is ambiguous (it may reflect logistical
  indifference rather than sun preference).  The estimate converges toward the raw
  unweighted estimate as D → ∞ (all images included regardless of access).

The **rate of decline** in p̂ as D increases quantifies **detour tolerance**: if
preference drops sharply between D = 5 and D = 20, people abandon shade quickly once it
requires more than a short step; if the curve is flat, people actively seek shade even
across substantial detours.

---

## Continuous-Weight Version (DCWP)

Instead of a hard threshold, a smooth **Detour-Cost Weighted Preference (DCWP)** score
can be computed per observation:

For each SVI image *i*:

```
effective_sun_i   = outshade_count_i × a(dist_to_shade_m_i)
effective_shade_i = inshade_count_i  × 1.0
effective_total_i = effective_shade_i + effective_sun_i

DCWP_i = effective_shade_i / effective_total_i   (NaN if effective_total = 0)
```

where `a(d)` is an **accessibility function** that discounts the information content of
sun-standing by how far shade was away:

| Function | Formula | Properties |
|---|---|---|
| Exponential decay | `exp(−d / τ)` | Smooth, single parameter τ (e.g. 20 m) |
| Linear decay | `max(0, 1 − d/D)` | Zero at distance D; computationally transparent |
| Step | `1 if d ≤ D else 0` | Equivalent to the threshold approach above |

The exponential decay is recommended: it approaches 1.0 when shade is very close
(sun-standing is maximally informative) and approaches 0.0 when shade is far away
(sun-standing is uninformative).  At d = τ, `a(d) = 1/e ≈ 0.37`.

Shade-standing votes are always weighted 1.0: a person who chose shade has revealed
shade preference regardless of how far shade was from the SVI capture point.

### Relationship to Approach A (ADJUSTED_SHADE_PREFERENCE.md)

Approach A uses `shadow_ratio` as the discount factor for sun votes:

```
effective_sun = outshade_count × shadow_ratio
```

DCWP replaces that discount with an access-cost function of `dist_to_shade_m`:

```
effective_sun = outshade_count × a(dist_to_shade_m)
```

This is the same structural idea applied to a different measure of shade availability —
road-segment supply vs. point-level access cost.

---

## Sample Size by Detour Threshold

The table below should be computed from the State College data before committing to any
particular threshold:

| D (m) | Expected n (images) | Notes |
|---|---|---|
| 0 (in shadow only) | subset of images where `in_shade_shadow = True` | Baseline |
| 5 | + images with shade within 5 m | Small step to any nearby shadow |
| 10 | … | Comfortable single step |
| 20 | … | Short diversion |
| 50 | … | Longer but still plausible detour |
| 100 | … | Substantial detour; sun-preference signal weak |
| ∞ | All images with shade modelled | Equivalent to unweighted raw estimate |

Because 65.9% of voted images have `shadow_ratio = 0` (no shadow on the road), many of
those may still have `dist_to_shade_m` less than 50 m — a shadow from a building on an
adjacent parcel can be nearby without covering the road.  The proximity filter may
therefore retain substantially more images than the `shadow_ratio ≥ 0.05` filter, at the
cost of including images where the pedestrian's shade access required crossing a road or
entering private space.

---

## Properties

### Advantages over shadow_ratio IPW

| Property | shadow_ratio IPW | Detour-conditioned |
|---|---|---|
| Unit of analysis | Road segment (aggregate) | SVI point (individual) |
| What is conditioned on | Shade supply on road | Access cost to nearest shade |
| Filter threshold interpretation | Statistical (SR ≥ 0.05 prevents 1/0) | Physical (detour in metres) |
| Weight instability | Present; requires winsorisation | Absent; no 1/x weighting |
| Sample retained | 34.1% of voted images | Depends on D; likely broader |
| Estimand | Preference under equal road supply | Preference given accessible shade |

### Complementarity with shadow_ratio

The two variables capture different dimensions of shade availability:

- `shadow_ratio` = how much of the road is in shadow (supply)
- `dist_to_shade_m` = how far the nearest shadow is from the pedestrian (access)

A location can have high shadow_ratio but the pedestrian be far from the shadow (they're
at the un-shadowed end of the segment).  Conversely, a low shadow_ratio location might
have the pedestrian standing just at the edge of a building shadow.  A joint filter
(SR ≥ threshold AND dist ≤ D) provides the most stringent conditioning but at further
cost to sample size.

### Limitations

**Detour distance is from the SVI point, not the pedestrian.**  The SVI image capture
location is on or near the road centreline; actual pedestrians may be on footpaths,
setbacks, or on the opposite side of the road.  The distance is therefore an
approximation of the pedestrian's access cost, not a precise measurement.

**In-shadow SVI points are ambiguous.**  When `in_shade_shadow = True`, the SVI point
is inside a shadow polygon, so `dist_to_shade_m = 0`.  People visible at such a point
include both active shade-seekers and people who happened to be there.  This makes the
D = 0 estimate a poor baseline for pure preference; the most informative part of the
analysis is the slope of the detour-tolerance curve, not its level.

**Sun-standing at small D captures sun preference most cleanly.**  People who are in sun
with shade 3 m away are the clearest revealed-preference observations in the dataset.
This is the primary behavioural signal the method is designed to surface.

**`dist_to_shade_m = NaN` when sun is below horizon.**  Images captured when
`sun_elevation ≤ 1°` have no modelled shadow and should be excluded (as they are
currently excluded from the shadow_ratio analysis).

**Temporal and spatial mismatch still apply.**  The same limitations that affect
`shadow_ratio` (shadow computed at nearest UTC hour; SVI point snapped to road) also
affect `dist_to_shade_m`.  A 30-minute timing offset can shift a shadow polygon by
several metres, which matters more at small D thresholds than at large ones.

**Detour feasibility varies by infrastructure.**  A 10 m detour to shade across the road
is a very different decision from a 10 m detour along the footpath.  The metric does not
distinguish.

---

## Interpretation

### What it answers

| Analysis | Question answered |
|---|---|
| p̂(shade &#124; dist ≤ 5 m) | Among pedestrians with shade within arm's reach, what fraction entered it? |
| p̂(shade &#124; dist ≤ 20 m) | Among pedestrians for whom shade required a short diversion, what fraction made it? |
| Slope of curve D = 5 → 50 | How quickly does shade-seeking drop off as detour distance grows? |
| DCWP score per image | Per-location preference score downweighted for shade being far away |

### Relationship to raw and IPW estimates

| Estimate | Population | Access assumption |
|---|---|---|
| Raw | All voted images | No conditioning on access |
| shadow_ratio IPW | SR ≥ 0.05 images | Road-level supply ≥ 5% |
| Detour-conditioned (D) | dist_to_shade_m ≤ D | Shade within D metres of SVI point |

The raw estimate is always the upper-bound sample.  The shadow_ratio IPW and
detour-conditioned estimates target overlapping but distinct subpopulations.  A large
gap between detour-conditioned preference at D = 5 m and D = 50 m is direct evidence
that detour cost is suppressing revealed shade preference in the data.

---

## Implementation Notes

```python
import numpy as np

# Hard-threshold version
def detour_conditioned_preference(df, D):
    """
    Shade preference among images where shade was within D metres.
    df must have: dist_to_shade_m, inshade_count, outshade_count
    """
    df_sub = df[df['dist_to_shade_m'] <= D].copy()
    total  = df_sub['inshade_count'].sum() + df_sub['outshade_count'].sum()
    if total == 0:
        return np.nan, 0
    pref = df_sub['inshade_count'].sum() / total
    return float(pref), len(df_sub)

# Continuous DCWP score per image (exponential decay)
def dcwp_score(df, tau_m=20.0):
    """
    Per-image detour-cost weighted preference score.
    tau_m: decay constant in metres (shade at tau_m has a(d) = 1/e ~ 0.37).
    """
    d = df['dist_to_shade_m'].fillna(np.inf)
    a = np.exp(-d / tau_m)
    effective_sun   = df['outshade_count'] * a
    effective_shade = df['inshade_count']
    effective_total = effective_shade + effective_sun
    return np.where(effective_total > 0,
                    effective_shade / effective_total,
                    np.nan)
```

### Parameter choices

| Parameter | Suggested value | Rationale |
|---|---|---|
| Threshold grid for detour-tolerance curve | 0, 5, 10, 20, 30, 50, 75, 100 m | Spans comfortable step to substantial detour |
| τ for exponential DCWP | 20 m | At 20 m `a(d) = 0.37`; at 50 m `a(d) = 0.08` — effectively zero |
| NaN handling | Exclude `dist_to_shade_m = NaN` | Sun-below-horizon images; no shadow modelled |
| Joint filter option | `dist_to_shade_m ≤ D AND shadow_ratio ≥ 0.05` | Combines point-level and road-level conditioning |

---

## Related Files

| File | Purpose |
|---|---|
| `data/state-college/state-college_svi_with_shadow.csv` | Input data with `dist_to_shade_m` and `in_shade_shadow` columns |
| `scripts/processing/add_shadow_to_state_college.py` | Computes `dist_to_shade_m` (Shapely `.distance()` to shadow union) |
| `docs/ADJUSTED_SHADE_PREFERENCE.md` | Approaches A–C using `shadow_ratio` for comparison |
| `docs/IPW_SHADOW_RATIO_METHOD.md` | shadow_ratio IPW filter and winsorisation details |
| `docs/IPW_FILTER_SHADE_PREFERENCE.md` | Properties of filtered vs retained images under shadow_ratio filter |
