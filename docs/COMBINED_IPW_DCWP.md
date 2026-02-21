# Combining Shadow Ratio IPW and DCWP: Implications and Interpretation

## 1. The Two Corrections in Brief

The shadow ratio IPW and DCWP adjustments each address a distinct source of confounding
in the observed shade preference estimate.

**Shadow ratio IPW** corrects for *road-segment shade supply*.  Images from roads with
little shadow coverage are upweighted by $w_i = 1/\text{SR}_i$ to represent what
behaviour would look like if every road had equal (full) shadow availability.  The
estimand is: *shade preference standardised to a shadow-rich road baseline*.

**DCWP** corrects for *point-level access cost*.  Sun-standing votes are discounted by
$a_i = e^{-d_i/\tau}$, where $d_i$ is the distance from the SVI capture point to the
nearest shadow boundary.  Sun-standing when shade is nearby is treated as a stronger
revealed preference signal than sun-standing when shade was far away.  The estimand
is: *shade preference with access-cost-uninformative sun-standing down-weighted*.

Both corrections are motivated by the same intuition — that sun-standing should count
as evidence of sun preference only to the degree that shade was a realistic option — but
they operate on different dimensions of "shade access": aggregate supply on the road
versus marginal distance to the nearest shadow patch.

---

## 2. Are the Two Dimensions Independent?

Before deciding whether to combine the corrections, it is worth asking whether they
capture genuinely distinct variation or whether they are proxies for the same underlying
quantity.

In the State College data (SR ≥ 0.05, valid `dist_to_shade_m`, n = 1,589):

$$\text{Corr}(\text{shadow\_ratio},\ \text{dist\_to\_shade\_m}) = -0.499$$

The correlation is moderately negative: images with higher shadow ratio on the road tend
to have smaller distances to the nearest shadow.  This makes physical sense — when a
large fraction of the road is in shadow, the pedestrian is more likely to already be
at or inside the shadow.  Conversely, when shadow coverage is sparse, the nearest patch
may be some distance away.

However, the correlation is far from perfect ($r^2 \approx 0.25$).  The two variables
share only 25% of their variance.  The remaining 75% is genuinely distinct:

- A pedestrian at the unshadowed end of a road with SR = 0.8 can have `dist_to_shade_m`
  > 20 m, while the shadow ratio implies abundant coverage.
- A pedestrian 1 m from a shadow patch from a building off-road can have SR = 0.05
  (very little road in shadow) but `dist_to_shade_m` near zero.

The two corrections are therefore **neither redundant nor independent**.  Combining them
adds real information, but with the important consequence described in Section 4.

---

## 3. The Combined Estimator

### 3.1 Formulation

The combined estimator applies IPW weights to DCWP-adjusted effective counts:

$$\hat{P}(\text{shade})_{\text{combined}} =
  \frac{\displaystyle\sum_i w_i \cdot \tilde{k}_i}
       {\displaystyle\sum_i w_i \cdot \tilde{n}_i}$$

where:

$$w_i = \min\!\left(\frac{1}{\text{SR}_i},\ \text{cap}\right), \qquad
  \tilde{k}_i = k_i, \qquad
  \tilde{n}_i = k_i + s_i \cdot e^{-d_i/\tau}$$

IPW weights scale the *observation* (how much each image contributes to the aggregate);
DCWP weights scale the *outcome* within each image (how informative the sun-standing
is).  The two operations act on different parts of the estimator and are formally
compatible.

In a GLM context, this is implemented by passing $[\tilde{k}_i, \tilde{s}_i]$ as the
binomial response and $w_i$ as `freq_weights`.

### 3.2 The combined estimand

Each correction defines a counterfactual standardisation:

| Correction | Standardises to... |
|---|---|
| Raw | Observed roads and distances |
| IPW | Equal shadow supply on every road (SR = 1) |
| DCWP | Access cost discounted to zero at $\tau$ scale |
| **Combined** | **Equal supply on every road AND access cost removed** |

The combined estimand is: *among pedestrians on roads with full shadow coverage and
shade at arm's reach, what fraction would be in shade?*

This is the most aggressive standardisation — the closest the method gets to a "pure
preference" signal stripped of both supply and access confounds.  It is also the
narrowest and most hypothetical estimand: it extrapolates to a condition (full shadow
supply + zero access cost) that no observation actually satisfies.

---

## 4. The Superadditivity Problem

### 4.1 Empirical result

In the State College data, the corrections interact in a non-additive way:

| Estimator | Aggregate shade preference | Shift from raw |
|---|---|---|
| Raw (SR ≥ 0.05, valid dist) | 30.4% | — |
| IPW only | 31.5% | +1.2 pp |
| DCWP only (τ = 20 m) | 32.2% | +1.8 pp |
| **IPW + DCWP** | **36.1%** | **+5.7 pp** |

The combined shift (+5.7 pp) is nearly **twice** the sum of the individual shifts
(+1.2 + 1.8 = +3.0 pp).  The corrections are **superadditive**: applying both together
produces a larger adjustment than either correction alone would suggest.

### 4.2 Why this happens

The superadditivity arises from the interaction between which observations the two
corrections target.

IPW upweights low-SR images most aggressively ($w_i = 1/\text{SR}_i$, up to the cap).
The −0.499 correlation between SR and distance means that low-SR images also tend to
have *larger* `dist_to_shade_m` and therefore *smaller* accessibility weights $a_i$.
DCWP discounts sun-standing most aggressively in exactly the images that IPW amplifies
most.

The net effect: IPW takes the images where sun-standing is most discounted (far from
shade) and amplifies their contribution, while DCWP simultaneously shrinks the effective
denominator $\tilde{n}_i$ in those same images.  A smaller denominator in
high-IPW-weight images pushes the aggregate estimate up more than the sum of the two
individual corrections would imply.

Schematically, for a low-SR, large-distance image with 3 people in sun and 0 in shade:

|  | Sun votes | Denominator | Shade pref |
|---|---|---|---|
| Raw | 3.0 | 3.0 | 0% |
| IPW only (w = 5) | 3.0 × 5 = 15.0 | 15.0 | 0% |
| DCWP only (a = 0.5) | 1.5 | 1.5 | 0% |
| IPW + DCWP | 1.5 × 5 = 7.5 | 7.5 | 0% |

So far this image still contributes 0% shade — all three people are in sun, and no
adjustment changes that.  The superadditivity is not visible in the image-level
preference; it appears in the **aggregate**.

The mechanism is in the denominator at the aggregate level.  IPW increases the effective
weight of low-SR images.  DCWP shrinks the effective $\tilde{n}_i$ (because $a_i < 1$
compresses the sun-count toward zero).  When both are applied, the aggregate denominator
$\sum w_i \tilde{n}_i$ is smaller than either correction alone would produce, while the
numerator $\sum w_i k_i$ is unchanged by DCWP (shade votes are unweighted).  A smaller
denominator at constant numerator = higher estimate.

### 4.3 The interpretive tension

The superadditivity reveals a deeper tension between the two corrections' implied
counterfactuals.

IPW says: *these low-SR images should be upweighted, because they represent shade-scarce
conditions that are under-represented relative to a shadow-rich baseline; if shade were
available, people here would (at the observed rate) seek it.*

DCWP says: *the sun-standing in these images is largely uninformative, because shade was
far away; we cannot know what people would have done if shade were nearby.*

These are conflicting claims about the same observations.  IPW treats the sun-standing
in low-SR images as meaningful (upweighting it to correct for supply scarcity); DCWP
treats it as not meaningful (discounting it because access cost was high).  Applying
both simultaneously does not resolve the conflict — it amplifies it.  The result is a
combined estimator that simultaneously upweights and discounts the same sun-standing
counts, producing a large correction that may overstate how much behaviour would change
under a "shade-rich and shade-nearby" counterfactual.

---

## 5. When Combining Is and Is Not Worthwhile

### 5.1 When not to combine

Combining is least appropriate when:

1. **The corrections target the same observations.** If the correlation between SR and
   dist_to_shade_m is high (|r| > 0.6), the two corrections are largely capturing the
   same confound.  Adding DCWP on top of IPW will mostly amplify the IPW adjustment
   rather than providing independent information.

2. **DCWP is tau-insensitive and modest.** In State College, DCWP alone adds +1.8 pp
   and is stable across τ ∈ [3, 200] m.  This indicates access cost is not a major
   confound in the raw data.  Adding IPW on top does not cancel this — it amplifies it
   through the superadditivity mechanism.

3. **The superadditivity cannot be explained.** A +5.7 pp combined shift, when each
   correction alone produces +1.2 and +1.8 pp, should prompt scrutiny before reporting.
   The combined estimand is plausible, but the arithmetic of amplification may exceed
   the genuine information content of the data.

### 5.2 When combining adds value

Combining is more defensible when:

1. **SR and dist_to_shade are genuinely orthogonal** (|r| < 0.3).  This would occur in
   urban fabrics where narrow shadow patches cross wide roads: SR is low, but the
   pedestrian might be standing right at the shadow edge (small dist).  In this case
   the two corrections correct for independent variation, superadditivity is muted, and
   the combined estimate provides a genuine double adjustment.

2. **DCWP is not tau-insensitive.**  If the detour-tolerance curve shows a steep
   drop — shade preference at d = 5 m is substantially higher than at d = 50 m — then
   access cost is a real driver of behaviour.  IPW correcting for supply and DCWP
   correcting for access cost are then genuinely separating two material confounds.

3. **The estimand is the primary target.** If the research question specifically asks
   about shade preference under conditions of full shadow coverage AND zero access cost,
   the combined estimator directly targets that question, and the superadditivity is a
   feature rather than a problem.

### 5.3 Recommendation for State College

Given the flat detour-tolerance curve, the modest and tau-insensitive DCWP correction,
and the −0.499 SR–distance correlation, **the combined estimator is not recommended as
the primary reported estimate** for the State College dataset.

The superadditivity produces a +5.7 pp combined adjustment that is mechanically
plausible but difficult to interpret substantively: it is not clear that the true shade
preference under "full supply + zero access cost" conditions is 5.7 pp higher than the
observed rate, or whether this reflects the amplification artefact described in
Section 4.

The preferred approach is to report the corrections separately:

- **IPW estimate** as the primary causal-inference result (corrects for road-level
  supply, directly comparable to the shadow ratio IPW methodology)
- **DCWP estimate** as a sensitivity check on the access-cost assumption (shows the
  estimate is robust to down-weighting far-from-shade sun-standing)
- **Combined estimate** in a supplementary table, with explicit acknowledgement of the
  superadditivity and its cause

---

## 6. Practical Notes on Implementation

When applying both corrections:

1. **Apply the SR ≥ 0.05 filter first.**  This is required for IPW (to avoid undefined
   weights) and has no adverse effect on DCWP.  For DCWP-only analysis, the filter is
   not strictly required but is advisable for comparability.

2. **Compute DCWP effective counts, then apply IPW as `freq_weights`.**  In the GLM:

   ```python
   # DCWP effective counts
   a = np.exp(-df['dist_to_shade_m'] / tau)
   eff_shade = df['inshade_count']
   eff_sun   = df['outshade_count'] * a
   y = np.column_stack([eff_shade, eff_sun])

   # IPW weights (winsorised)
   w = (1.0 / df['shadow_ratio']).clip(upper=cap)

   model = sm.GLM(y, X, family=sm.families.Binomial(),
                  freq_weights=w).fit()
   ```

3. **Winsorise IPW weights on the original `shadow_ratio` distribution**, not on the
   DCWP-adjusted effective counts.  The cap should be set before DCWP so it reflects
   the supply-confound correction, not an interaction with access-cost discounting.

4. **Report τ alongside combined estimates.**  Since DCWP interacts with IPW through the
   superadditivity mechanism, the sensitivity of the combined estimate to τ is larger
   than DCWP alone.  A τ sensitivity analysis (τ ∈ [5, 80] m) should accompany any
   reported combined figure.

---

## 7. Summary

| Question | Correction |
|---|---|
| What is the shade preference standardised for road shadow supply? | IPW alone |
| What is the shade preference with uninformative sun-standing discounted? | DCWP alone |
| What is the shade preference under both corrections? | Combined — use with caution |
| How much of the combined shift is mechanical amplification vs genuine signal? | Diagnose via superadditivity ratio and τ sensitivity |

The two corrections address genuinely distinct (but correlated) dimensions of the same
underlying confound.  Combining them is formally coherent but produces superadditive
shifts driven by the negative correlation between shadow ratio and distance to shade.
In the State College data, this makes the combined estimate difficult to interpret
relative to the straightforward individual corrections.  The corrections are best
reported separately, with the combined estimate treated as an upper bound on the
access-confound adjustment rather than a primary result.

---

## Related Files

| File | Purpose |
|---|---|
| `docs/IPW_SHADOW_RATIO_METHOD.md` | Shadow ratio IPW filter and winsorisation |
| `docs/DCWP_METHOD.md` | DCWP formulation and τ interpretation |
| `docs/DETOUR_CONDITIONED_SHADE_PREFERENCE.md` | Implementation overview |
| `docs/ADJUSTED_SHADE_PREFERENCE.md` | Approaches A–C for comparison |
| `scripts/visualization/state_college/visualize_state_college_dtc.py` | DCWP and tau sensitivity plots |
