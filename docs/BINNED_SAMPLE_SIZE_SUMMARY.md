# Binned Sample Size Summary - Seattle vs NYC

**Date:** 2026-03-25
**Analysis:** Seasonally-adjusted shade preference estimates with 2°C UTCI bins

---

## Overview

Both cities have excellent sample sizes in their core UTCI ranges but show sparse coverage at temperature extremes, reflecting their different climate profiles.

---

## Seattle Sample Sizes

**Total observations:** 780,000+ pedestrians

**UTCI Range:** -27°C to +34°C (28 bins with data)

**Sample size by range:**

| UTCI Range | Bins | Raw N per bin | Effective N per bin | Data Quality |
|------------|------|---------------|---------------------|--------------|
| **< -15°C** | 3 bins | 10-1,046 | 6-532 | **Poor** (sparse) |
| **-15°C to +15°C** | 16 bins | 6,553-75,379 | 3,020-30,508 | **Excellent** |
| **+15°C to +25°C** | 6 bins | 7,335-63,613 | 4,184-27,803 | **Excellent** |
| **> +25°C** | 3 bins | 6-3,174 | 5-1,876 | **Poor** (sparse) |

**Peak coverage:** -1°C to +1°C bin (N=75,379 raw, N_eff=30,508)

**Key limitations:**
- Only 10 observations at -27°C (unreliable)
- Only 6 observations at +31°C (unreliable)
- Negligible data above 25°C (not a hot climate)

---

## NYC Sample Sizes

**Total observations:** 254,000+ pedestrians

**UTCI Range:** -35°C to +34°C (35 bins with data)

**Sample size by range:**

| UTCI Range | Bins | Raw N per bin | Effective N per bin | Data Quality |
|------------|------|---------------|---------------------|--------------|
| **< -15°C** | 11 bins | 81-2,526 | 46-1,199 | **Moderate** |
| **-15°C to +15°C** | 17 bins | 2,253-15,058 | 1,163-6,406 | **Excellent** |
| **+15°C to +25°C** | 5 bins | 8,208-23,303 | 3,973-9,154 | **Excellent** |
| **> +25°C** | 2 bins | 3,774-8,016 | 2,536-2,847 | **Good** |

**Peak coverage:** +19°C to +21°C bin (N=26,554 raw, N_eff=11,734)

**Key limitations:**
- Very sparse below -30°C (N=81-160)
- Moderate sample sizes in -30°C to -15°C range (N=317-1,643)
- Better hot weather coverage than Seattle but still limited above 30°C

---

## Cross-City Comparison Coverage

**Overlapping UTCI range for reliable comparison:** **-15°C to +25°C**

### Why this range?

1. **Both cities have N > 1,000 per bin** in this range (adequate precision)
2. **Seattle limitation:** Virtually no data above 25°C (only 3,180 observations total)
3. **NYC limitation:** Sparse data below -15°C (mostly <1,000 per bin)

### Sample size comparison in overlap region:

| UTCI Range | Seattle N (avg) | NYC N (avg) | Ratio (S:NYC) |
|------------|-----------------|-------------|---------------|
| -15°C to 0°C | 20,000-75,000 | 2,200-11,100 | **3-7x more** |
| 0°C to +15°C | 40,000-64,000 | 3,900-15,000 | **4-6x more** |
| +15°C to +25°C | 7,300-63,600 | 8,200-23,300 | **comparable** |

**Seattle has substantially more data** in cold/moderate conditions due to:
- Larger total sample size (780k vs 254k)
- Climate profile centered on mild, cool conditions

**NYC has better hot weather coverage** (more uniform across warm temps).

---

## Effective Sample Size Impact

**Weighting reduces effective sample size:**

- **Seattle:** N_eff ≈ 40-50% of N_raw (moderate loss)
- **NYC:** N_eff ≈ 40-67% of N_raw (variable, larger loss at extremes)

**Smallest effective sample sizes:**

**Seattle:**
- -27°C: N_eff = 6 ❌ (unreliable)
- +31°C: N_eff = 5 ❌ (unreliable)

**NYC:**
- -33°C: N_eff = 46 ⚠️ (marginal)
- -35°C: N_eff = 108 ⚠️ (marginal)

**Threshold for reliability:**
- **N_eff > 500:** Adequate precision (SE < 0.02)
- **N_eff > 1,000:** Good precision (SE < 0.015)
- **N_eff < 500:** Poor precision (wide confidence intervals)

---

## Implications for Analysis

### 1. **Restrict cross-city comparison to -15°C to +25°C**

This range has:
- Both cities well-represented (N > 1,000 per bin)
- Narrow confidence intervals (SE < 0.01 in most bins)
- Minimal extrapolation risk

### 2. **Flag sparse bins in visualizations**

Bins with N_raw < 500 should be:
- Shown with different marker style (hollow circles)
- Noted in figure captions
- Excluded from quantitative comparisons

### 3. **Climate-specific coverage reflects real-world use**

**Seattle:**
- Excellent coverage where Seattle residents actually experience outdoor conditions (-5°C to +20°C)
- Sparse hot weather data is not a major limitation (rarely occurs)

**NYC:**
- Better coverage of hot extremes (summer heat is common)
- Cold extremes still under-sampled but adequate for analysis

### 4. **Seasonal adjustment preserved sample sizes**

- Seasonal reweighting did not dramatically reduce effective N
- Loss primarily due to SR-IPW and DCWP corrections (not seasonal)
- All bins with N_raw > 1,000 still have N_eff > 500

---

## Recommendations

### For Manuscript

**Main text:**
> "Both cities show excellent coverage in the -15°C to +25°C UTCI range (Seattle: 6,500-75,000 observations per 2°C bin; NYC: 2,200-26,500 observations per bin). Outside this range, sample sizes become sparse (N < 1,000), particularly for Seattle above 25°C and NYC below -15°C, reflecting each city's climate profile."

**Methods:**
> "We restrict formal cross-city comparisons to the -15°C to +25°C UTCI range where both cities have adequate sample sizes (N_eff > 500 per bin after weighting). Bins with fewer than 500 raw observations are shown but flagged as low-precision estimates."

**Supplementary table:**
Include full bin-by-bin sample sizes (N_raw, N_eff) for transparency.

### For Figures

- Mark bins with N_raw < 500 with hollow circles
- Include sample size overlay (secondary y-axis or inset)
- Shade the -15°C to +25°C comparison region for clarity

---

## Conclusion

**Seattle and NYC have complementary coverage:**
- Seattle: Deep coverage of cool/moderate conditions (climate-typical)
- NYC: Better representation of hot weather (summer heat common)
- Overlap region (-15°C to +25°C): Both cities well-powered for comparison

**The binned estimates are reliable within each city's climate-relevant range**, and cross-city comparisons are well-powered in the shared UTCI range where both populations have substantial exposure.

---

**End of Document**
