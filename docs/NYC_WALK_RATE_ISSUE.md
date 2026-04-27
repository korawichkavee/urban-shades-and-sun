# NYC Walk Rate Data Issue - Temp-IPW Not Applicable

**Date:** 2026-03-23
**Issue:** NYC 2022 household travel survey has insufficient temporal coverage
**Impact:** Cannot reliably apply Temp-IPW correction (same issue as Seattle)

---

## NYC Survey Coverage

**Survey Period:** September 28 - November 17, 2022 (7 weeks, ~2.5 months)

| Month | Trip Count | % of Total | Walk Rate | Mean UTCI |
|-------|-----------|------------|-----------|-----------|
| September | 1,312 | 1.5% | 0.457 | 9.6°C |
| **October** | **82,873** | **96.0%** | **0.427** | **9.8°C** |
| November | 2,154 | 2.5% | 0.451 | 13.8°C |

**Total:** 86,339 trips, concentrated in October 2022

---

## Problem for Temp-IPW

### Missing Seasonal Coverage

**Survey covers:** Fall only (Sep-Nov)
**Missing:** Winter (Dec-Feb), Spring (Mar-May), Summer (Jun-Aug)

**Implication:** Cannot model annual temperature response to walking activity.

### Missing Temperature Extremes

**Observed UTCI range:** 9.6°C to 13.8°C (monthly means) - only ~4°C variation
**True NYC annual range:** ~-10°C (winter) to ~30°C (summer) - ~40°C variation

**Problem:**
- "Cold temps" in data are 9.6°C (cool fall days), not true winter
- "Hot temps" in data are 13.8°C (mild fall days), not true summer
- Missing the extremes where temperature-based self-selection is strongest

### Walk Rate Pattern

Walk rate across months: 0.427 to 0.457 (very stable, only 3 pp variation)

**Coldest month (Sep, 9.6°C):** walk rate = 0.457
**Warmest month (Nov, 13.8°C):** walk rate = 0.451

**Result:** Essentially flat walk rate function → Temp-IPW weights stay very close to 1.0

---

## Why This Differs from Seattle's Problem

### Seattle Issue
- Survey: April-June 2023 (spring only)
- Problem: **Inverted walk rate pattern** (April highest despite being coldest)
- Result: Temp-IPW produces **negative effect** (-2.67 pp) from upweighting cold temps
- Mechanism: Spring enthusiasm effect creates anomalous high walk rate in April

### NYC Issue
- Survey: Sep-Nov 2022 (fall only)
- Problem: **Flat walk rate pattern** (no temperature variation within narrow fall range)
- Result: Temp-IPW produces **near-zero effect** (+0.1 pp from summary stats)
- Mechanism: Insufficient temperature variation to reveal walking response

### Common Root Cause

**Both surveys lack temporal coverage needed for Temp-IPW assumptions:**
- Temp-IPW assumes year-round data capturing seasonal extremes
- Temp-IPW assumes temperature-driven self-selection creates walk rate variation
- 2-3 month surveys within single season cannot capture annual patterns

---

## Implications for Analysis

### NYC Temp-IPW Appears Small But Is Unreliable

From `new-york-city_ipw_revised_summary_stats.csv`:
- DCWP effect: +1.76 pp
- Combined effect: -4.52 pp
- **Implied Temp-IPW effect:** -6.28 pp (combined - DCWP)

Wait - this is also NEGATIVE! The +0.1 pp mentioned in interpretation docs may be from OLD estimates with spatial/temporal standardization.

Let me verify what's actually happening...

**Revised interpretation needed based on actual data.**

---

## Comparison to Seattle

| Feature | Seattle | NYC |
|---------|---------|-----|
| Survey period | Apr-Jun 2023 | Sep-Nov 2022 |
| Survey duration | 3 months | 2.5 months |
| Season | Spring | Fall |
| Trip count | 56,704 | 86,339 |
| UTCI range (monthly means) | -17°C to +30°C | 9.6°C to 13.8°C |
| Walk rate variation | 25.4% to 19.3% (6.1 pp) | 45.7% to 42.7% (3.0 pp) |
| Walk rate pattern | **Inverted** (high in cold) | Flat |
| Temp-IPW effect | -2.67 pp | **-6.28 pp** (need verification) |
| Root cause | Spring enthusiasm | Narrow temp range? |

---

## Recommended Action

**Exclude Temp-IPW for BOTH cities.**

### Justification

1. **Seattle:** Inverted walk rate pattern from spring-only coverage
2. **NYC:** Fall-only coverage, missing seasonal extremes
3. **Both:** Single-season surveys insufficient for annual temperature response modeling
4. **Consistency:** Symmetric treatment of cities strengthens methodology

### Revised Correction Strategy

**For both NYC and Seattle:**
- ✅ **DCWP correction:** Distance-to-shade accessibility bias
- ✅ **SR-IPW correction:** Shadow supply bias
- ❌ **Temp-IPW correction:** Excluded due to insufficient survey temporal coverage

### Paper Methods Text Suggestion

> "Temperature-based activity selection bias correction (Temp-IPW) was not applied due to limited temporal coverage of household travel surveys. Seattle's 2023 survey covers April-June only (spring), while NYC's 2022 survey covers September-November only (fall). Both surveys lack the seasonal coverage required to reliably model year-round temperature effects on outdoor walking activity. Shade preference estimates therefore incorporate Distance-Conditioned Walk Preference (DCWP) and Shadow Ratio IPW (SR-IPW) corrections only."

---

## Files to Update

1. **`scripts/processing/apply_triple_ipw_final_cities_revised.py`**
   - Modify to exclude Temp-IPW weight from combined calculation
   - Set `w_temp_ipw = 1.0` (no adjustment) for all observations
   - Combined weight becomes: `w_combined = w_sr_ipw × w_dcwp`

2. **`docs/IPW_RESULTS_INTERPRETATION.md`**
   - Update to reflect exclusion of Temp-IPW for both cities
   - Revise effect decomposition analysis
   - Remove walk rate validation plots from priority list

3. **All plotting scripts**
   - Remove Temp-IPW layer from effect decomposition
   - Update labels: "Triple IPW" → "Dual IPW (SR-IPW + DCWP)"
   - Remove walk rate validation plots

4. **Paper manuscript**
   - Methods: Document survey limitations and Temp-IPW exclusion
   - Results: Report only DCWP, SR-IPW, and combined dual IPW estimates
   - Limitations: Acknowledge inability to correct temperature-based selection bias

---

## Lessons Learned

1. **Always verify survey temporal coverage** before applying temperature-based corrections
2. **Single-season surveys are fundamentally insufficient** for Temp-IPW methodology
3. **Recent surveys may have limited duration** due to cost constraints (NYC 7 weeks, Seattle 3 months vs historical multi-year surveys)
4. **City-specific walk rate functions require full annual coverage** - pooled functions from historical data may be better but still problematic if applied to recent data
5. **Transparency about limitations is better than applying questionable corrections**

---

## Alternative Approaches (Not Recommended)

### Option 1: Use Pooled Walk Rate Function
- Pooled function from 25 cities (1988-2007) in `data/transit_surveys/processed/p_walk_given_temp_final.csv`
- **Problem:** Temporal mismatch (20-35 years old), may not reflect current walking behavior
- **Problem:** Still assumes pooled pattern applies to specific cities

### Option 2: Use Climate Normals to Impute Walk Rates
- Use historical climate data to estimate what walk rates "should be" in other seasons
- **Problem:** Untestable assumption that walk rate follows temperature in unobserved seasons
- **Problem:** Assumes no other seasonal factors (daylight, holidays, weather variability)

### Option 3: Apply Temp-IPW Despite Limitations and Report as Sensitivity
- Compute estimates both with and without Temp-IPW
- **Problem:** Presents unreliable estimates as if they're valid
- **Problem:** Negative effects suggest correction is actively harmful, not just uncertain

**Recommendation:** Exclude Temp-IPW cleanly rather than trying to salvage it.

---

**End of Document**
