# Seattle Walk Rate Data Issue & Temp-IPW Correction Problem

**Date:** 2026-03-23
**Issue:** Seattle Temp-IPW produces negative correction effect (-2.7 pp)
**Root Cause:** Survey data limitations create inverted walk rate pattern

---

## Problem Summary

When applying Temp-IPW to Seattle data without spatial/temporal standardization, the combined correction effect is **NEGATIVE** (-2.67 pp), meaning the IPW adjustment DECREASES shade preference estimates. This contradicts the theoretical expectation that correcting for temperature-based self-selection should increase shade preference.

---

## Root Cause Analysis

### Expected Pattern (Theoretical)
Temp-IPW assumes:
- **Cold temps (<20°C):** Walk rate ↓ → self-selected hardy walkers → **downweight**
- **Hot temps (>20°C):** Walk rate ↓ → self-selected heat-adapted → **upweight**
- Baseline at 20°C where walk rate is assumed to be near maximum

### Actual Pattern (Seattle 2023 Survey)

**Survey Coverage:** April-June 2023 ONLY (3 months, 56,704 trips)

| Month | Mean UTCI | Walk Rate | Sample Size |
|-------|-----------|-----------|-------------|
| April | 2.0°C | **25.4%** | 24,071 (42.5%) |
| May | 11.5°C | **19.3%** | 21,144 (37.3%) |
| June | 11.0°C | **21.1%** | 11,489 (20.3%) |

**Observed:** Walk rate is HIGHEST in April (coldest month), not at baseline 20°C.

**Result:**
- UTCI bins -20 to 0°C: walk rate 0.234-0.266 (from cold April days)
- UTCI bin at 20°C: walk rate 0.223 (baseline)
- **Ratio:** λ(-2°C) / λ(20°C) = 0.264 / 0.223 = **1.185 = UP-weight** ⚠️

This is the **OPPOSITE** of the intended downweight!

---

## Why Seattle Data Shows Inverted Pattern

### 1. **Temporal Confounding: Survey Limited to Spring**

The survey covers April-June only - NO winter (Dec-Feb) or summer (Jul-Aug) data.

**Implication:**
- "Cold temps" (-17°C to 0°C) = cold days in APRIL, not winter
- "Hot temps" (20-30°C) = warm days in MAY/JUNE, not summer
- Missing the true seasonal extremes

### 2. **April Effect: Springtime Walking Enthusiasm**

April has 25.4% walk rate vs May 19.3% despite being 10°C colder.

**Possible explanations:**
1. **Spring euphoria:** After winter, people excited to walk in April even when cold
2. **Selection bias:** April survey respondents may be more walk-oriented
3. **Response rate variation:** Different demographic response by month
4. **Daylight hours:** April has rapidly lengthening days → encourages walking
5. **COVID recovery (2023):** Post-pandemic behavior changes

### 3. **Temperature Range Compression**

Survey UTCI range: -17°C to +30°C (47°C span)
- Lacks extreme heat (>30°C)
- Lacks true winter cold with months of <0°C

True year-round Seattle:
- Winter mean: ~0-5°C for Dec-Feb
- Summer mean: ~20-25°C for Jul-Aug

**Implication:** The survey captures spring temperature variability, not annual temperature effects on walking.

---

## How This Breaks Temp-IPW

### Asymmetric Formula
```python
w_temp = np.where(
    utci < 20,
    λ(utci) / λ(20),      # Cold: downweight if λ(T) < λ(20)
    λ(20) / λ(utci)       # Hot: upweight if λ(T) < λ(20)
)
```

### What Actually Happens

**Cold temps (April cold days):**
- λ(-2°C) = 0.264 (April data)
- λ(20°C) = 0.223 (May/June data)
- Weight = 0.264 / 0.223 = **1.185** (UP-weight, not down!)

**Mild temps (May/June typical):**
- λ(12°C) = 0.191
- λ(20°C) = 0.223
- Weight = 0.191 / 0.223 = **0.857** (DOWN-weight)

### Shade Preference by UTCI Range

| UTCI Range | Mean UTCI | Temp-IPW | Shade Pref (DCWP) | People |
|------------|-----------|----------|-------------------|--------|
| -20 to 0°C | -3.8°C | **1.119** | **52.8%** | 11,514 |
| 0 to 10°C | 6.3°C | 0.977 | 44.9% | 21,987 |
| 10 to 20°C | 15.6°C | 0.951 | 43.0% | 48,247 |
| 20 to 30°C | 23.0°C | 0.944 | 44.5% | 17,701 |

**Problem:**
- High shade preference (52.8%) at cold temps gets **UP-weighted** (1.119)
- Mild shade preference (43-45%) at warm temps gets **DOWN-weighted** (<1.0)
- **Net effect:** Overall weighted average DECREASES

---

## Comparison: NYC Walk Rate

**NYC survey:** Likely has better temporal coverage (need to verify)

NYC Temp-IPW weights:
- Mean: 0.618 (downweights overall)
- Max: 1.067 (barely above 1.0)
- No extreme upweighting at cold temps

**Result:** NYC Temp-IPW contributes +0.1 pp (minimal but positive direction)

---

## Solutions & Recommendations

### Option 1: Exclude Temp-IPW for Seattle ⭐ RECOMMENDED
**Pros:**
- Avoids using corrupted correction
- Still have SR-IPW + DCWP corrections
- Transparent about data limitations

**Cons:**
- Lose one correction layer
- Asymmetric treatment of cities (NYC keeps it, Seattle doesn't)

**Justification:**
> "Seattle walk rate data covers only April-June 2023, insufficient for modeling annual temperature effects on outdoor activity. Temp-IPW correction excluded for Seattle."

### Option 2: Use Pooled Walk Rate Function
**Pros:**
- Pooled function (25 cities, 1988-2007) has full seasonal coverage
- More stable estimates
- Consistent across cities

**Cons:**
- Seattle-specific behavior lost
- Temporal mismatch (1988-2007 vs 2023)
- Still assumes pooled pattern applies to Seattle

**Implementation:**
- Use `data/transit_surveys/processed/p_walk_given_temp_final.csv` (pooled)
- From IPW_SHADE_PREFERENCE_METHOD.md line 210

### Option 3: Month-Conditional Baseline
**Pros:**
- Accounts for seasonal variation
- Uses available data

**Cons:**
- Complex to explain
- Still confounded by April effect
- Doesn't solve core problem (limited temporal range)

**Implementation:**
```python
# Use April baseline for April, May baseline for May, etc.
baseline_walk_rate = df.groupby('month')['walk_rate'].transform('mean')
```

### Option 4: Skip Temp-IPW Entirely for Both Cities
**Pros:**
- Simplest approach
- Avoids all temporal confounding
- SR-IPW + DCWP still provide substantive corrections

**Cons:**
- Loses temperature-based selection bias correction
- Doesn't use available walk rate data

---

## Recommended Action

**Use Option 1 for Seattle, keep Temp-IPW for NYC.**

**Justification:**
1. Seattle data is clearly insufficient (3-month survey, April bias)
2. NYC may have better coverage (verify first)
3. Document limitation transparently in paper
4. Report separate estimates:
   - Seattle: Raw, DCWP, SR-IPW (no Temp-IPW)
   - NYC: Raw, DCWP, SR-IPW, SR-IPW + Temp-IPW

**Paper text suggestion:**
> "Temperature-based activity selection bias (Temp-IPW) was not applied to Seattle estimates due to limited temporal coverage of the 2023 household travel survey (April-June only). The resulting walk rate function exhibits seasonal confounding inconsistent with year-round temperature response assumptions."

---

## Verification Needed

Before finalizing:

1. ✅ **Check Seattle survey documentation**
   - Confirmed: 2023 survey, April-June only
   - Single-year, spring-only coverage

2. ⏸️ **Check NYC survey temporal coverage**
   - If NYC also limited → skip Temp-IPW for both cities
   - If NYC has full year → can keep for NYC only

3. ⏸️ **Test pooled walk rate function**
   - Recompute with pooled function
   - Compare effect sizes
   - Check if pooled produces positive correction

4. ⏸️ **Sensitivity analysis**
   - Report estimates WITH and WITHOUT Temp-IPW
   - Show impact of inclusion/exclusion

---

## Files to Update

1. `scripts/processing/apply_triple_ipw_final_cities_revised.py`
   - Add `--skip-temp-ipw` flag
   - Default: exclude Temp-IPW for Seattle

2. `docs/IPW_RESULTS_INTERPRETATION.md`
   - Add section on walk rate limitations
   - Explain Seattle Temp-IPW exclusion

3. Paper methods section
   - Document survey coverage limitations
   - Justify differential treatment of cities

---

## Lessons Learned

1. **Always check temporal coverage of activity data** before computing temperature-based corrections
2. **Spring-only surveys are insufficient** for year-round temperature response modeling
3. **Month effects can dominate temperature effects** in limited-duration surveys
4. **Asymmetric corrections are sensitive to baseline choice** - requires full seasonal coverage
5. **City-specific walk rate functions may be worse than pooled** if data coverage is poor

---

**End of Document**
