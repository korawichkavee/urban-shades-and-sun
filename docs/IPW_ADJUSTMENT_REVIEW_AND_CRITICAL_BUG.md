# IPW Adjustment Review and Critical Bug Discovery

## Executive Summary

After reviewing the IPW documentation and implementation, I've discovered a **critical data integrity bug** that explains why the UTCI vs shade preference curves show unexpected patterns and why the IPW adjustments appear ineffective.

**The Bug**: The `person_count` column is **zero for all images**, despite having 99,463 total people in Seattle and 117,412 in NYC recorded in `inshade_count` + `outshade_count`.

**Impact**: The IPW summary statistics calculation filters to `person_count > 0`, which excludes ALL data, resulting in NaN values for all shade preference estimates.

---

## How Shade Availability IS Controlled For

You correctly stated: "Availability is controlled for via the IPW adjustment". Here's how:

### The Triple IPW System

The method applies **three distinct corrections** for different sources of bias:

#### 1. Shadow Ratio IPW (Shade AVAILABILITY)
- **What it adjusts**: Road-segment level shade SUPPLY
- **How**: Upweights images where `shadow_ratio` (fraction of road in shadow) is low
- **Weight formula**: `w_sr_ipw = 1 / shadow_ratio` (capped at p95)
- **Estimand**: "What would shade preference be if every road had equal (full) shadow availability?"
- **Filter required**: `shadow_ratio >= 0.05` (otherwise weights blow up)

**This IS the availability adjustment you mentioned.**

#### 2. Temperature IPW (Selection BIAS)
- **What it adjusts**: Who chooses to be outside at different temperatures
- **How**: Uses walk trip rates from travel surveys as proxy for P(outside | temperature)
- **Asymmetric adjustment**:
  - **Cold temps**: Downweight (people outside in cold are hardy → overstate general population's shade pref)
  - **Hot temps**: Upweight (people outside in heat are heat-tolerant → understate general population's shade pref)
- **Weight formula**:
  ```
  T < 20°C:   w_temp = λ(T) / λ(20°C)      (downweight)
  T ≥ 20°C:   w_temp = λ(20°C) / λ(T)      (upweight)
  ```
- **Estimand**: "What would shade preference be if people were equally likely to be outside at all temperatures?"

**This addresses the mobility/activity selection bias.**

#### 3. DCWP (Detour-Cost Weighted Preference)
- **What it adjusts**: Point-level ACCESS COST to shade (NOT availability!)
- **How**: Discounts sun-standing votes by `a = exp(-d/τ)` where `d` = distance to nearest shadow
- **Key insight**:
  - Shade-standing votes: always weight = 1.0 (fully informative)
  - Sun-standing votes: discounted based on how far away shade was
  - Sun-standing 60m from shade ≠ sun-standing 2m from shade
- **Estimand**: "What is shade preference when uninformative sun-standing (far from shade) is down-weighted?"

**This is NOT an availability adjustment - it's an access cost adjustment.**

### Combined Estimand

The full "w_combined" weight multiplies all corrections:

```python
w_combined = w_sr_ipw × w_temp_ipw × w_spatial × w_temp_range
```

And applies it to DCWP-adjusted outcomes:

```
shade_pref_ipw = Σ(shade_pref_dcwp × w_combined × people) / Σ(w_combined × people)
```

**Final estimand**: "Among pedestrians on roads with full shadow coverage, equally likely to be outside at all temps, with far-from-shade sun-standing discounted for access cost, what fraction would choose shade?"

---

## The Critical Bug

### What Should Happen

In the IPW script (`apply_triple_ipw_final_cities.py:321-351`):

```python
# Shade preference estimates (only on images with people)
df_with_people = df_filtered[df_filtered['person_count'] > 0].copy()

if len(df_with_people) > 0:
    # Compute shade preferences...
else:
    logger.warning("No images with people detected")
    stats['shade_pref_raw'] = np.nan
    # etc.
```

### What Actually Happens

**Seattle:**
- `person_count` column: all zeros (780,451 images)
- `inshade_count` sum: 43,782
- `outshade_count` sum: 55,681
- **Total people (computed)**: 99,463
- **Images with `person_count > 0`**: **ZERO**

**NYC:**
- `person_count` column: all zeros (254,507 images)
- `inshade_count` sum: 52,983
- `outshade_count` sum: 64,429
- **Total people (computed)**: 117,412
- **Images with `person_count > 0`**: **ZERO**

### Why The Plots Still Worked

The plotting scripts correctly computed:

```python
df['total_people'] = df['inshade_count'] + df['outshade_count']
df = df[df['total_people'] > 0].copy()
```

This bypasses the bug by recomputing person counts from the shade counts.

### Why The Summary Stats Are NaN

The IPW summary file (`new-york-city_ipw_summary_stats.csv`) shows:

```
shade_pref_raw,shade_pref_dcwp,shade_pref_ipw,dcwp_effect_pp,combined_effect_pp
,,,,,
```

All blank (NaN) because the script found "No images with people detected".

---

## Why The Backwards Curve Pattern Exists

Now we can diagnose the unexpected pattern (shade preference DECREASING with temperature):

### What We Know:
1. **Walking rates are stable** across temperatures (20-25% Seattle, 36-45% NYC)
   - Selection bias should be minimal
   - Temperature IPW should have modest effect

2. **IPW weights ARE being computed** (columns exist in output)
   - But summary stats use the buggy person_count filter
   - The weights may still be wrong if applied to filtered data

3. **DCWP operates on outcomes** before IPW weighting
   - Down-weights sun-standing based on distance to shade
   - Should reduce backwards bias if it's driven by access costs

4. **The plots show minimal change** between raw, DCWP, and DCWP+IPW
   - This suggests either:
     - (a) The adjustments are correctly showing that access/availability aren't major confounds
     - (b) The adjustments are being applied incorrectly due to filtering issues

### Possible Explanations for Backwards Curve:

1. **Data filtering artifact**:
   - The `shadow_ratio >= 0.05` filter removes 65-93% of data (typical for State College)
   - If sunny, high-UTCI images disproportionately have low shadow_ratio, they get excluded
   - The remaining sample is biased toward shaded areas at high temps

2. **Temporal confounding**:
   - High-UTCI images might be from different times of day
   - Morning/evening commute patterns differ from midday

3. **Actual behavioral pattern**:
   - People in hot conditions might prioritize other factors (direct routes, speed)
   - Or activity types differ (delivery workers vs leisure walkers)

4. **IPW not actually being applied**:
   - Due to person_count bug, the weights might not be properly applied in weighted aggregation

---

## Next Steps To Fix

### 1. Fix the person_count Bug

The `person_count` column needs to be populated. This should happen in either:
- The shadow annotation script
- The UTCI annotation script
- The IPW script itself (add: `df['person_count'] = df['inshade_count'] + df['outshade_count']`)

### 2. Re-run IPW With Fixed Data

After fixing person_count, re-run:
```bash
python scripts/processing/apply_triple_ipw_final_cities.py --city seattle
python scripts/processing/apply_triple_ipw_final_cities.py --city new-york-city
```

### 3. Check Summary Statistics

The summary stats should show:
- Non-NaN shade preference values
- Clear effects from each adjustment level
- Effective sample sizes that match expectations

### 4. Re-plot With Verified Data

After confirming summary stats are correct, regenerate plots to see if:
- The backwards curve persists (real effect)
- The curve flips to expected pattern (was a bug)
- The adjustments have larger/smaller effects than currently shown

---

## Documentation Review Summary

### What DCWP Does (NOT Availability)
From `docs/DCWP_METHOD.md`:

> "DCWP addresses a third, complementary dimension: the **cost of reaching shade** from the pedestrian's current position. It does so by down-weighting the evidential value of sun-standing as a function of how far away the nearest shade was at the time of capture."

**Key insight**: Distance to shade ≠ shadow ratio. You can be:
- On a road with high shadow_ratio (lots of shade) but still far from it
- On a road with low shadow_ratio but standing right at a shadow edge

DCWP adjusts for the SECOND dimension (point-level access), not the FIRST (road-level availability).

### What Shadow Ratio IPW Does (IS Availability)
From `docs/IPW_SHADOW_RATIO_METHOD.md`:

> "Images are excluded if the fraction of the nearest road segment in shadow at capture time (`shadow_ratio`) falls below 0.05... The IPW weight formula is `w = 1 / shadow_ratio`."

**This IS the availability adjustment.** It standardizes to a "shadow-rich baseline" by upweighting images from roads with little shadow coverage.

### Superadditivity Warning
From `docs/COMBINED_IPW_DCWP.md`:

> "The combined shift (+5.7 pp) is nearly **twice** the sum of the individual shifts (+1.2 + 1.8 = +3.0 pp). The corrections are **superadditive**."

This happens because shadow_ratio and dist_to_shade are correlated (r = -0.499):
- Low shadow_ratio → IPW upweights
- Low shadow_ratio → larger distances → DCWP discounts more
- Combined effect amplifies beyond additive sum

**Recommendation from docs**: Report corrections separately, treat combined as sensitivity check, not primary estimate.

---

## Conclusion

**Your statement was correct**: "Availability is controlled for via the IPW adjustment"

**But specifically**: It's controlled for by the **Shadow Ratio IPW**, not by DCWP. DCWP controls for access cost (distance), which is related but distinct.

**The critical issue**: The `person_count` column bug prevents proper calculation of weighted shade preferences, making it impossible to assess whether the adjustments are working correctly or why the backwards curve exists.

**Priority**: Fix person_count, re-run IPW, verify summary stats, then re-analyze the curve pattern.
