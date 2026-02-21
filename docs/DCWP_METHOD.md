# Detour-Cost Weighted Preference (DCWP): Method and Interpretation

## 1. Background

Estimating behavioural preferences from passively observed data requires care when the
choice set is not identical across observations.  In this dataset, each street view image
records how many pedestrians are standing in sun versus shade at the moment of capture.
The raw proportion in shade is a natural estimate of shade preference, but it is
confounded by **access**: a person standing in the sun when shade is 2 metres away is
expressing something very different from a person standing in the sun when shade is
60 metres away.  The former has revealed a preference for sun; the latter may simply
not have made a detour.

This is an instance of the classical **revealed preference problem under constrained
choice** (Samuelson 1938): observed behaviour conflates preference and opportunity.
Two existing corrections address part of this confound.  The **shadow ratio IPW**
reweights images by the aggregate supply of shade on the nearest road segment
(`shadow_ratio = 1 / shadow_ratio`), standardising observations to a notional
"shadow-rich" baseline.  The **temperature IPW** corrects for self-selection into
outdoor activity at different temperatures.

DCWP addresses a third, complementary dimension: the **cost of reaching shade** from
the pedestrian's current position.  It does so by down-weighting the evidential value
of sun-standing as a function of how far away the nearest shade was at the time of
capture.

---

## 2. Conceptual Framework

### 2.1 Access cost and the choice to enter shade

The decision to stand in shade rather than sun can be modelled as a simple utility
comparison.  A pedestrian enters shade if:

$$U(\text{shade}) - U(\text{sun}) > C(d)$$

where $C(d)$ is the cost of travelling distance $d$ to reach shade.  If $C$ is
increasing in $d$ — as the literature on pedestrian route deviation consistently finds
— then the threshold at which shade is chosen rises with distance.  Equivalently, the
observed fraction in shade among pedestrians near shade is a better estimate of latent
shade preference than the same fraction among pedestrians far from shade.

The key terms to look up:
- **Revealed preference** (Samuelson 1938; Varian 2006) — inferring preferences from
  choices
- **Constrained revealed preference / limited consideration sets** — what observed
  choices imply when not all options are available
- **Pedestrian route deviation / detour tolerance** — empirical work measuring how far
  people deviate from direct routes for comfort amenities

### 2.2 Distance decay in spatial behaviour

A well-established regularity in spatial behaviour is that the probability of choosing a
destination or using an amenity declines with distance, and that this decline is well
described by a negative exponential function.  This originates in the gravity model
literature (Wilson 1967) and has been applied widely to pedestrian access to parks,
transit, retail, and environmental amenities.

The exponential form $a(d) = e^{-d/\tau}$ is appealing because:

1. It is normalised to $a(0) = 1$ (shade at zero distance carries full evidential
   weight)
2. It decays smoothly and is everywhere differentiable
3. It has a single interpretable parameter $\tau$ (the **characteristic decay distance**)
4. It arises naturally from models of random search and exponential travel time
   distributions

The parameter $\tau$ has a direct interpretation: at distance $d = \tau$, the weight
$a(\tau) = e^{-1} \approx 0.37$.  At $d = 2\tau$, $a(2\tau) \approx 0.14$.  At
$d = 3\tau$, $a(3\tau) \approx 0.05$ — effectively zero.  So $\tau$ is approximately
the distance at which shade access is considered "barely reachable" in terms of
informational content.

The key terms to look up:
- **Distance decay / gravity model** (Wilson 1967; Fotheringham & O'Kelly 1989)
- **Negative exponential access function** — used in transit, park, and pedestrian
  accessibility modelling
- **Hansen accessibility measure** — a related formulation using $e^{-\beta d}$ for
  urban land-use accessibility

---

## 3. The DCWP Estimator

### 3.1 Weighting scheme

For each street view image $i$, let:

- $k_i$ = number of people standing in shade (`inshade_count`)
- $s_i$ = number of people standing in sun (`outshade_count`)
- $d_i$ = distance from the SVI capture point to the nearest shadow boundary, in metres
  (`dist_to_shade_m`)
- $\tau$ = the decay constant (metres), a tuning parameter

The **accessibility weight** for image $i$ is:

$$a_i = e^{-d_i / \tau}$$

The **effective counts** are:

$$\tilde{k}_i = k_i \qquad \tilde{s}_i = s_i \cdot a_i \qquad \tilde{n}_i = \tilde{k}_i + \tilde{s}_i$$

The **DCWP score** for image $i$ is:

$$\widehat{p}_i^{\,\text{DCWP}} = \frac{\tilde{k}_i}{\tilde{n}_i} = \frac{k_i}{k_i + s_i \cdot a_i}$$

This is defined when $\tilde{n}_i > 0$ and is NaN otherwise (images where everyone is
in shade and $a_i = 0$ trivially; or images with $d_i = \text{NaN}$, i.e. captured when
the sun was below the horizon).

### 3.2 Interpretation of the weighting

Shade-standing votes ($k_i$) are unweighted.  Choosing to stand in shade is always
informative: it reveals shade preference regardless of how far away the shade is — the
pedestrian is demonstrably at the shade boundary or inside it.

Sun-standing votes ($s_i$) are discounted by $a_i \in (0, 1]$.  When shade is very
close ($d_i \to 0$, $a_i \to 1$), sun-standing is assigned full evidential weight as a
revealed preference for sun.  When shade is far away ($d_i \gg \tau$, $a_i \to 0$),
sun-standing contributes almost nothing: the person's choice is attributed to access
cost rather than preference.

This is structurally equivalent to **Approach A** in `docs/ADJUSTED_SHADE_PREFERENCE.md`
(the opportunity-weighted score), which discounts sun-standing by `shadow_ratio`.  DCWP
replaces the road-segment-level supply measure with a point-level access-cost function.

### 3.3 Aggregate and regression use

For **aggregate estimation**, the population-average DCWP shade preference is:

$$\hat{P}(\text{shade}) = \frac{\sum_i \tilde{k}_i}{\sum_i \tilde{n}_i}$$

For **regression** (e.g. shade preference vs UTCI), the effective counts are passed
directly as the binomial response in a GLM:

$$\text{logit}(p_i) = \beta_0 + \beta_1 \cdot \text{UTCI}_i + \beta_2 \cdot \text{UTCI}_i^2$$

with $y_i = [\tilde{k}_i,\; \tilde{s}_i]$ as the (successes, failures) pair.  No
additional observation weights are required — the down-weighting of uninformative
sun-standing is already encoded in $\tilde{s}_i$.

### 3.4 Contrast with shadow ratio IPW

| | Shadow ratio IPW | DCWP |
|---|---|---|
| **What is adjusted** | Road-segment shade supply | Point-level access cost |
| **Weight on sun votes** | $1 / \text{shadow\_ratio}$ (upweight) | $e^{-d/\tau}$ (downweight) |
| **Weight on shade votes** | 1 (unweighted) | 1 (unweighted) |
| **Filter required** | Yes (SR < 0.05 → undefined weight) | No (weight approaches 0 smoothly) |
| **Winsorisation required** | Yes (weights blow up near SR = 0) | No (weights bounded in [0, 1]) |
| **Tuning parameter** | Winsorise quantile (default p95) | $\tau$ (decay constant in metres) |
| **Estimand** | Preference under equal road supply | Preference discounted for access cost |

The two corrections are not redundant.  High shadow ratio does not imply the pedestrian
is near the shadow (they could be at the unshaded end of the segment).  Conversely,
low shadow ratio does not preclude being close to a shadow from an adjacent building.
Applying both simultaneously is the most complete adjustment for shade access.

---

## 4. The Decay Constant τ

### 4.1 What τ controls

$\tau$ is the single free parameter of the DCWP method.  It sets the spatial scale at
which access cost becomes material:

| τ (m) | $a(5\text{m})$ | $a(20\text{m})$ | $a(50\text{m})$ | Interpretation |
|---|---|---|---|---|
| 3 | 0.19 | 0.001 | ~0 | Only shade within 3 m matters |
| 5 | 0.37 | 0.018 | ~0 | Shade beyond ~15 m is ignored |
| 10 | 0.61 | 0.14 | 0.007 | Moderate decay; 20 m still informative |
| 20 | 0.78 | 0.37 | 0.082 | Comfortable detour range |
| 40 | 0.88 | 0.61 | 0.29 | Mild decay; 50 m still carries ~30% weight |
| 80 | 0.94 | 0.78 | 0.54 | Weak decay; most distances matter |
| 200 | 0.98 | 0.90 | 0.78 | Near-raw; minimal adjustment |

### 4.2 The ideal value of τ

The correct value of $\tau$ is the **characteristic distance pedestrians will walk to
access shade** — i.e., the median detour distance at which the cost of reaching shade
becomes prohibitive.

This is an empirical quantity that varies by population, climate, and context.  Some
reference points from related literature:

- Pedestrian route deviation studies typically find that walkers accept detours of
  roughly **10–30%** of total trip length for comfort or aesthetic amenities.  For a
  typical urban block of 80–120 m, this implies detour tolerance of roughly **8–35 m**.
- Studies of shade-seeking in hot climates (e.g. Phoenix, AZ; Mediterranean cities) find
  that pedestrians will cross the street or change route for shade, suggesting meaningful
  tolerance for detours of **20–50 m** in hot conditions.
- In mild conditions, detour tolerance for shade is lower; $\tau \approx 5$–10 m may be
  more appropriate.

The default of $\tau = 20$ m is a reasonable middle ground for a temperate climate
(State College, Pennsylvania), where shade is valued but not urgently sought at most
temperatures.  It implies that shade 20 m away is weighted at 37% of shade at the same
location, and shade 60 m away (three decay lengths) is effectively zero.

Key search terms for grounding τ empirically:
- **Pedestrian detour tolerance / acceptable detour distance**
- **Shade-seeking route deviation** in hot climates
- **Walking distance to urban amenities** (parks, transit stops) — gives an upper bound
  on what pedestrians consider accessible on foot

### 4.3 Sensitivity analysis

Because $\tau$ cannot be precisely identified from this data, a sensitivity analysis
across $\tau \in \{3, 5, 10, 20, 40, 80, 200\}$ m should accompany any reported result.
The key diagnostic is whether conclusions (e.g. the slope of shade preference vs UTCI;
the road-type ranking) are stable across the range.

In the State College data, the detour-tolerance curve is nearly flat: aggregate shade
preference at $d \leq 0$ m is only ~4 percentage points higher than at $d \leq \infty$.
This empirical flatness implies that DCWP results are **insensitive to τ**: all values
from 3 to 200 m produce broadly similar GLM curves, shifted only marginally above the
raw estimate.  This is itself an interpretable finding — the access cost to shade is not
a major driver of the observed sun/shade split in this population.

---

## 5. Identifiability and Assumptions

### 5.1 What the estimate recovers

The DCWP estimator does not recover the **structural preference** $U(\text{shade}) -
U(\text{sun})$ directly.  It recovers a **weighted summary** of observed behaviour in
which far-from-shade sun-standing is down-weighted.  Whether this constitutes an
unbiased estimate of latent preference depends on the correctness of the decay model
and the assumption that shade-standing is always freely chosen.

The critical assumptions are:

**A1 (Monotone access cost):** The cost of reaching shade is non-decreasing in
$d_i$.  This is almost certainly true.

**A2 (Exponential form):** The discount on sun-standing is well described by
$e^{-d/\tau}$.  This is a modelling choice; a linear decay or a step function at some
threshold would produce similar results in this dataset given the empirical flatness of
the detour-tolerance curve.

**A3 (Shade-standing is unconstrained):** A person standing in shade has demonstrated
they could access shade; their shade-standing is treated as a free choice.  This is
slightly optimistic — some shade-standing may reflect the person's prior route choice
rather than an active decision to seek shade.

**A4 (SVI point ≈ pedestrian location):** The distance $d_i$ is computed from the SVI
camera position (on or near the road centreline) to the nearest shadow polygon, not from
the individual pedestrian's position.  Spatial mismatch between the camera and the
pedestrian introduces noise that is largest at small $d_i$, where the distinction
between 1 m and 5 m matters most.

### 5.2 The NaN exclusion

Images with `dist_to_shade_m = NaN` are captured when the sun is below the horizon
($\text{elevation} \leq 1°$).  No shadows are modelled; the access cost concept is
undefined.  These observations are excluded from DCWP but not from the raw estimate.
The exclusion is exact (452 of 4,655 voted images), concentrated outside commute hours,
and should not introduce systematic preference bias.

### 5.3 Relationship to IPW

DCWP is not an inverse-probability-weighted estimator in the formal sense.  IPW
upweights observations from units with low probability of treatment (here: low
shadow_ratio) to recover a population-average treatment effect.  DCWP instead
**re-encodes the outcome** by scaling the sun-standing count, leaving the probability
model unchanged.

The two approaches are methodologically parallel but formally distinct.  DCWP does not
require a propensity score model, does not require a positivity assumption on shadow
availability, and does not produce unbounded weights.  Its weaker formal grounding is
balanced by greater numerical stability and more direct interpretability.

---

## 6. Key Search Terms for Literature

The following terms will locate the most relevant academic background:

| Concept | Key search terms |
|---|---|
| Revealed preference foundations | "revealed preference" Samuelson 1938; "weak axiom of revealed preference" WARP |
| Constrained choice sets | "limited consideration set" "choice under constraint" "constrained revealed preference" |
| Distance decay / gravity models | "distance decay function" "negative exponential decay" "gravity model" Wilson 1967 |
| Hansen accessibility | "Hansen accessibility measure" "potential accessibility" |
| Pedestrian detour behaviour | "pedestrian route deviation" "acceptable detour" "walking detour" "route choice pedestrian" |
| Shade-seeking detours | "shade seeking behavior" "thermal comfort walking" "pedestrian shade route" |
| Exponential discounting of spatial utility | "spatial discount factor" "distance decay park access" "pedestrian amenity distance" |
| IPW / causal inference comparison | "inverse probability weighting observational study" Rosenbaum Rubin 1983 |
| Thermal comfort outdoor pedestrian | "UTCI outdoor thermal comfort" "physiological equivalent temperature pedestrian" |

---

## 7. Summary

DCWP provides a correction for one source of revealed preference bias in SVI-based shade
preference estimation: the fact that sun-standing is less informative when shade requires
a meaningful detour.  It does so by multiplying sun-standing counts by a negative
exponential accessibility function $a(d) = e^{-d/\tau}$, where $d$ is the distance to
the nearest shadow and $\tau$ is a decay constant expressing the characteristic detour
distance a pedestrian will make for shade.

The method requires no additional data beyond `dist_to_shade_m` (already computed),
produces bounded weights with no instability, and has a single interpretable tuning
parameter.  In the State College dataset, the adjustment is modest (+1.9 percentage
points in aggregate shade preference), consistent with the nearly flat detour-tolerance
curve: access cost to shade is not the primary driver of the observed sun/shade
distribution at this location.

The appropriate value of $\tau$ should be grounded in empirical studies of pedestrian
detour tolerance in comparable climates.  Absent such data, a sensitivity analysis
across $\tau \in [5, 80]$ m should accompany any reported DCWP result.

---

## Related Files

| File | Purpose |
|---|---|
| `docs/DETOUR_CONDITIONED_SHADE_PREFERENCE.md` | Implementation notes and method overview |
| `docs/ADJUSTED_SHADE_PREFERENCE.md` | Approaches A–C using `shadow_ratio` |
| `docs/IPW_SHADOW_RATIO_METHOD.md` | Shadow ratio IPW details |
| `scripts/visualization/state_college/visualize_state_college_dtc.py` | All DCWP plots including tau sensitivity |
| `data/state-college/state-college_svi_with_shadow.csv` | Input data with `dist_to_shade_m` |
