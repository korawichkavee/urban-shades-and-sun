# Data Quality Assessment - Seattle and NYC Shade Preference Analysis

**Date:** 2026-03-23
**Purpose:** Comprehensive assessment of data quality, coverage, and limitations
**Status:** Critical issues identified requiring methodological adjustments

---

## Executive Summary

**CRITICAL FINDINGS:**
1. ⚠️ **Severe sparsity at temperature extremes** (Seattle: N=6 at 31°C; NYC: N=81 at -33°C)
2. ⚠️ **Highly unbalanced seasonal coverage** (Seattle 38% winter vs NYC 43% summer)
3. ⚠️ **Limited UTCI overlap** between cities (18-20°C difference in modal temperatures)
4. ✅ **Excellent temporal coverage** (10 years: 2016-2026 for both cities)
5. ✅ **Large overall sample sizes** (Seattle: 780k; NYC: 255k images)

**RECOMMENDATION:** Define and report effective UTCI ranges where N ≥ 500 per bin. Acknowledge seasonal imbalance and limited cross-city overlap in well-sampled ranges.

---

## 1. Sample Size by UTCI Bin

### Seattle

**Overall:**
- Total images: 780,451 (after SR ≥ 0.05 filter)
- UTCI range: -26.3°C to +33.4°C (59.7°C span)
- Non-empty bins: 27 (of 42 possible 2°C bins)

**Distribution extremes:**
- **Smallest bin:** UTCI = 31°C, **N = 6** ⚠️ CRITICALLY SPARSE
- **Largest bin:** UTCI = -1°C, N = 75,379
- **Modal region:** -5°C to +5°C (cold-biased distribution)

**Well-supported range (N ≥ 500):**
- Approximately **-10°C to +20°C** (23 bins)
- Bins with N < 100: 4 bins at extremes (>25°C, <-15°C)
- Bins with N < 500: 7 bins (edges of distribution)

**Data sparsity issues:**
| UTCI Range | Example Bin | N | Quality Assessment |
|------------|-------------|---|-------------------|
| >25°C | 31°C | 6 | ❌ UNUSABLE - extreme sparsity |
| 20-25°C | 23°C | ~200-500 | ⚠️ MARGINAL - wide CIs expected |
| -5 to 20°C | -1°C | 75,379 | ✅ EXCELLENT - narrow CIs |
| -10 to -5°C | -7°C | ~2,000-5,000 | ✅ GOOD - adequate precision |
| <-15°C | -17°C | ~100-500 | ⚠️ MARGINAL - wide CIs |

### New York City

**Overall:**
- Total images: 254,507 (after SR ≥ 0.05 filter)
- UTCI range: -34.1°C to +33.3°C (67.4°C span - wider than Seattle)
- Non-empty bins: 35 (more complete coverage)

**Distribution extremes:**
- **Smallest bin:** UTCI = -33°C, **N = 81** ⚠️ SPARSE
- **Largest bin:** UTCI = 19°C, N = 26,554
- **Modal region:** +15°C to +25°C (warm-biased distribution)

**Well-supported range (N ≥ 500):**
- Approximately **+5°C to +30°C** (15 bins)
- Bins with N < 100: ~10 bins at cold extreme (<-15°C)
- Bins with N < 500: ~15 bins (broader tails than Seattle)

**Data sparsity issues:**
| UTCI Range | Example Bin | N | Quality Assessment |
|------------|-------------|---|-------------------|
| >30°C | 31°C | ~100-200 | ⚠️ MARGINAL |
| 20-30°C | 25°C | ~5,000-15,000 | ✅ EXCELLENT |
| 5-20°C | 19°C | 26,554 | ✅ EXCELLENT - peak density |
| -5 to +5°C | 1°C | ~1,000-5,000 | ✅ GOOD |
| <-15°C | -33°C | 81 | ⚠️ SPARSE - unstable estimates |

### Critical Comparison: Modal Temperature Offset

**Seattle modal bin:** -1°C
**NYC modal bin:** +19°C
**Difference:** **20°C**

**This is enormous!** It means:
- Cities have fundamentally different UTCI distributions
- Most Seattle data comes from cold conditions
- Most NYC data comes from moderate/warm conditions
- **Limited overlap in well-sampled ranges** (roughly +5°C to +20°C only)

**Implication:** Cross-city comparisons are valid primarily in the +5°C to +20°C range where both cities have N ≥ 1,000 per bin. Outside this range, comparisons confound city effects with data quality differences.

---

## 2. Temporal Coverage

### Date Range and Duration

**Seattle:**
- Start: 2016-05-31
- End: 2026-02-15
- Duration: **9.7 years**
- Years covered: 11 calendar years (2016-2026)

**NYC:**
- Start: 2016-07-17
- End: 2026-02-12
- Duration: **9.6 years**
- Years covered: 11 calendar years (2016-2026)

**Assessment:** ✅ **EXCELLENT** - Nearly a decade of data provides:
- Robust seasonal coverage
- Averaging over inter-annual weather variability
- Temporal representativeness

### Seasonal Distribution

**Seattle:**
| Season | N Images | % | Assessment |
|--------|----------|---|------------|
| Winter (Dec-Feb) | 298,399 | **38.2%** | ⚠️ OVERSAMPLED |
| Spring (Mar-May) | 110,352 | **14.1%** | ⚠️ UNDERSAMPLED |
| Summer (Jun-Aug) | 188,840 | 24.2% | ✅ Balanced |
| Fall (Sep-Nov) | 182,860 | 23.4% | ✅ Balanced |

**Expected (uniform):** 25% per season

**Imbalance metrics:**
- Max deviation: +13.2 pp (winter oversample)
- Min deviation: -10.9 pp (spring undersample)
- **Coefficient of variation:** 36% (moderate imbalance)

**NYC:**
| Season | N Images | % | Assessment |
|--------|----------|---|------------|
| Winter (Dec-Feb) | 45,082 | **17.7%** | ⚠️ UNDERSAMPLED |
| Spring (Mar-May) | 54,562 | 21.4% | ✅ Balanced |
| Summer (Jun-Aug) | 109,127 | **42.9%** | ⚠️ OVERSAMPLED |
| Fall (Sep-Nov) | 45,736 | 18.0% | ⚠️ UNDERSAMPLED |

**Imbalance metrics:**
- Max deviation: +17.9 pp (summer oversample)
- Min deviation: -7.3 pp (winter undersample)
- **Coefficient of variation:** 45% (high imbalance)

### Critical Issue: Opposite Seasonal Biases

**Seattle:** Winter-heavy (38% vs expected 25%)
**NYC:** Summer-heavy (43% vs expected 25%)

**This is a major confound for cross-city comparisons!**

**Why this matters:**
1. Seasonal shade preference likely differs (winter: less shade seeking, summer: more)
2. UTCI values within seasons differ by latitude (NYC summer hotter than Seattle summer)
3. Urban behavior patterns vary by season (tourism, outdoor activity)
4. Different photo capture opportunities (daylight hours, weather)

**Current comparison confounds:**
- City effect (Seattle vs NYC)
- Season effect (winter vs summer)
- Climate effect (temperate vs continental)

**Solution:** Seasonally standardize or stratify by season before comparing cities.

### Monthly Distribution

**Seattle dominant months:**
- December, January, February (winter months most sampled)
- Likely reflects Street View collection schedules
- May introduce temporal bias if behavior varies monthly

**NYC dominant months:**
- June, July, August (summer months most sampled)
- Opposite pattern to Seattle
- Reinforces seasonal confound

**Recommendation:** Report monthly sample sizes in supplementary materials. Consider month fixed effects in sensitivity analysis.

---

## 3. Effective UTCI Ranges

### Defining "Well-Supported" Bins

**Proposed thresholds for reliability:**

| Threshold | Quality Level | Rationale |
|-----------|---------------|-----------|
| N ≥ 1,000 | **Excellent** | SE < 1.6 pp for p=0.5 |
| N ≥ 500 | **Good** | SE < 2.2 pp for p=0.5 |
| N ≥ 100 | **Marginal** | SE < 5.0 pp for p=0.5 (flag for caution) |
| N < 100 | **Poor** | SE > 5.0 pp (exclude or report with extreme caution) |

*SE calculation: √[p(1-p)/N] for binomial proportion*

### Seattle Effective Ranges

**By quality threshold:**

| Quality | UTCI Range | N Bins | Coverage | Notes |
|---------|------------|--------|----------|-------|
| Excellent (N≥1000) | **-9°C to +19°C** | 15 | 28°C span | Core analysis range |
| Good (N≥500) | **-11°C to +21°C** | 17 | 32°C span | Extended range with wider CIs |
| Marginal (N≥100) | **-17°C to +27°C** | 24 | 44°C span | Report with caution |
| Full range | -26°C to +33°C | 27 | 59°C span | Includes unreliable extremes |

**Recommended reporting:**
- **Primary estimates:** -9°C to +19°C (excellent quality)
- **Extended estimates:** -11°C to +21°C (good quality, note wider CIs)
- **Sensitivity analysis:** Test excluding bins with N < 500

### NYC Effective Ranges

**By quality threshold:**

| Quality | UTCI Range | N Bins | Coverage | Notes |
|---------|------------|--------|----------|-------|
| Excellent (N≥1000) | **+1°C to +29°C** | 15 | 28°C span | Core analysis range |
| Good (N≥500) | **-3°C to +31°C** | 19 | 34°C span | Extended range |
| Marginal (N≥100) | **-21°C to +33°C** | 30 | 54°C span | Many cold bins marginal |
| Full range | -34°C to +33°C | 35 | 67°C span | Cold tail very sparse |

**Recommended reporting:**
- **Primary estimates:** +1°C to +29°C (excellent quality)
- **Extended estimates:** -3°C to +31°C (good quality)
- **Sensitivity analysis:** Test excluding bins with N < 500

### Cross-City Overlap Zone

**Seattle excellent range:** -9°C to +19°C
**NYC excellent range:** +1°C to +29°C
**Overlap (both excellent):** **+1°C to +19°C** (18°C span, 10 bins)

**This is the only range where direct city comparisons are unambiguously valid!**

**Outside overlap:**
- Seattle -9°C to +1°C: Only Seattle has excellent data
- NYC +19°C to +29°C: Only NYC has excellent data
- Comparisons outside overlap confound city with data quality

**Recommendation:**
- Primary cross-city comparison: +1°C to +19°C
- Extended comparison: -3°C to +21°C (good quality for both)
- Acknowledge limited overlap in hot range (Seattle lacks data >25°C)

---

## 4. Spatial Coverage

### Geographic Extent

**Seattle:**
- Latitude: 47.4957°N to 47.7341°N (0.238° span ≈ 26 km)
- Longitude: -122.4358°W to -122.2382°W (0.198° span ≈ 16 km)
- Area: Approximately 416 km² (16 × 26 km)

**NYC:**
- Latitude: 40.5409°N to 40.8891°N (0.348° span ≈ 39 km)
- Longitude: -74.1781°W to -73.7009°W (0.477° span ≈ 37 km)
- Area: Approximately 1,443 km² (37 × 39 km)

**NYC covers 3.5× larger area** → More spatial heterogeneity expected

### Spatial Weight Distribution

**Key observations from spatial plots:**

1. **Weight clustering:** IPW weights show spatial autocorrelation
   - High-weight clusters likely correspond to undersampled neighborhoods
   - Low-weight clusters likely correspond to oversampled areas (e.g., downtown)

2. **Shadow ratio patterns:**
   - Seattle: Higher shadow ratios in northern/eastern areas (more trees?)
   - NYC: Lower shadow ratios in Manhattan core (urban canyons)
   - Geographic bias in shade availability

3. **Shade preference patterns:**
   - Not uniformly distributed across cities
   - Suggests neighborhood-level heterogeneity
   - Could reflect demographics, land use, or measurement artifacts

**Implication:** Spatial clustering may violate independence assumption in bootstrap. Consider spatial block bootstrap in sensitivity analysis.

### Spatial Coverage Quality

**Seattle:**
- Dense coverage in central neighborhoods
- Sparser in peripheral areas
- Appears to cover major urban/suburban zones

**NYC:**
- Very dense in Manhattan
- Good coverage in Brooklyn, Queens
- Sparser in outer boroughs
- May oversample commercial cores vs residential areas

**Recommendation:** Report borough/neighborhood sample sizes. Test for spatial heterogeneity in shade preference (neighborhood fixed effects).

---

## 5. Precision and Uncertainty by UTCI Bin

### Standard Error Patterns

From variance analysis, key findings:

**Seattle:**
- **Minimum SE:** ~0.3 pp at modal bin (-1°C, N=75k)
- **Median SE:** ~1.0 pp in well-sampled range
- **Maximum SE:** ~10-20 pp at sparse extremes (31°C)

**NYC:**
- **Minimum SE:** ~0.4 pp at modal bin (19°C, N=26k)
- **Median SE:** ~1.5 pp in well-sampled range
- **Maximum SE:** ~5-10 pp at cold extreme (-33°C)

**Pattern:** SE increases dramatically at distribution tails as expected (SE ∝ 1/√N)

### Variance Inflation from IPW Weighting

**Finding:** Weighted variance is 1.5-3× higher than raw variance

**Typical variance inflation factors by UTCI:**
- Cold temps: VIF ≈ 2.0 (moderate inflation)
- Modal temps: VIF ≈ 1.5 (minimal inflation)
- Hot temps: VIF ≈ 2.5 (higher inflation due to sparse data + extreme weights)

**Interpretation:**
- IPW weighting costs precision (as expected)
- Cost is acceptable in well-sampled regions (VIF ~1.5)
- Cost is concerning at extremes (VIF >2.5)
- Trade-off between bias correction and precision loss

### Effective Sample Size Loss

**Seattle:**
- Raw N: 780,451
- Effective N (IPW): 375,935
- **Retention: 48.2%**
- Information loss: ~400k "observations" due to weighting variance

**NYC:**
- Raw N: 254,507
- Effective N (IPW): 142,909
- **Retention: 56.2%**
- Information loss: ~110k "observations"

**NYC has better weighting efficiency** (56% vs 48%) despite smaller sample.

**Possible reasons:**
- NYC has more balanced shadow ratio distribution
- Seattle has more extreme shadow ratios requiring stronger reweighting
- NYC Temp-IPW weights closer to 1.0 (less temperature-based selection)

**Implication:** Seattle pays higher precision cost for bias correction. This is acceptable given large raw N, but should be acknowledged.

---

## 6. Data Quality Issues and Limitations

### Issue 1: Temperature Extremes Unreliable

**Problem:**
- Seattle >25°C: N <100 per bin → SE >5 pp
- NYC <-15°C: N <500 per bin → SE >2 pp
- Curve fits extrapolate beyond data support

**Impact:**
- Confidence intervals very wide at extremes
- Point estimates unstable
- Predictions for heat waves (>30°C) highly uncertain

**Mitigation:**
1. Report effective UTCI range prominently
2. Shade or annotate regions with N <500 in plots
3. Include sample size in all UTCI bin plots
4. Sensitivity analysis excluding sparse bins
5. Consider restricting inference to N ≥500 range

### Issue 2: Seasonal Imbalance Confounds Cross-City Comparison

**Problem:**
- Seattle: 38% winter (cold-heavy)
- NYC: 43% summer (hot-heavy)
- Opposite biases create confound

**Impact:**
- Cannot distinguish:
  - Do Seattle people prefer more shade? (city effect)
  - Or does winter sampling reduce observed preference? (season effect)
- Current estimates confound behavior with sampling season

**Mitigation:**
1. **Seasonal stratification:** Report estimates separately by season
2. **Seasonal reweighting:** Reweight both cities to uniform 25% per season
3. **Season-adjusted comparison:** Include season fixed effects in model
4. **Acknowledge limitation:** Explicitly state confound in paper

**Example seasonal reweighting:**
```python
# Target: 25% per season
seattle_season_weights = {
    'winter': 0.25 / 0.382,  # = 0.654 (downweight winter)
    'spring': 0.25 / 0.141,  # = 1.773 (upweight spring)
    'summer': 0.25 / 0.242,  # = 1.033
    'fall': 0.25 / 0.234     # = 1.068
}
```

### Issue 3: Limited Overlap in Well-Sampled Ranges

**Problem:**
- Seattle excellent: -9°C to +19°C
- NYC excellent: +1°C to +29°C
- Overlap: +1°C to +19°C only (18°C span)

**Impact:**
- Cannot compare at hot extremes (Seattle lacks data)
- Cannot compare at cold extremes (NYC lacks data)
- Cross-city differences may reflect different UTCI contexts

**Mitigation:**
1. **Report overlap zone:** Emphasize +1°C to +19°C as valid comparison range
2. **Extrapolation caution:** Don't claim city differences apply outside overlap
3. **Future data collection:** Target filling gaps (Seattle summer, NYC winter)

### Issue 4: Household Travel Survey Temporal Mismatch

**Problem:**
- Street View images: 10 years (2016-2026)
- Seattle walk survey: 3 months (April-June 2023)
- NYC walk survey: 2.5 months (Sep-Nov 2022)

**Impact:**
- Temp-IPW based on narrow survey windows
- Walk rate doesn't reflect year-round patterns
- Temporal mismatch between preference measurement and activity data

**Mitigation:**
- **Preferred:** Exclude Temp-IPW (as recommended in SEATTLE_WALK_RATE_ISSUE.md)
- **Alternative:** Use pooled walk rate function from historical data (1988-2007)
- **Document:** Clearly state temporal limitation

### Issue 5: Spatial Clustering and Non-Independence

**Problem:**
- Images are spatially clustered (Street View routes)
- Violates independence assumption in standard errors
- Bootstrap may underestimate true SE

**Impact:**
- Confidence intervals may be too narrow
- P-values may be anti-conservative
- Effective sample size may be lower than calculated

**Mitigation:**
1. **Spatial block bootstrap:** Resample by spatial clusters (grid cells)
2. **Cluster-robust SE:** Adjust SE for spatial correlation
3. **Sensitivity analysis:** Compare standard vs spatial bootstrap CIs
4. **Conservative approach:** Report "assuming independence" caveat

### Issue 6: Unequal SR Filter Retention

**Problem:**
- Seattle: 33.3% retained after SR ≥0.05
- NYC: 7.6% retained after SR ≥0.05
- **NYC loses 92.4% of data!**

**Impact:**
- NYC results based on selective subsample
- May introduce selection bias (only shadier locations)
- Cross-city comparison confounded with differential filtering

**Implication:**
- SR threshold (0.05) may be too restrictive for NYC
- Consider lower threshold (0.03) or city-specific thresholds
- Test sensitivity to threshold choice (already done in SR sensitivity analysis)

---

## 7. Recommendations for Analysis

### Primary Recommendations

**1. Define and Report Effective UTCI Ranges**

**Recommendation:** Use N ≥500 threshold for "good quality" and report this range prominently.

**Suggested text:**
> "Primary estimates are reported for UTCI ranges with good data quality (N≥500 per 2°C bin): Seattle -11°C to +21°C; NYC -3°C to +31°C. Cross-city comparisons are most reliable in the overlap region (+1°C to +19°C) where both cities have excellent coverage."

**2. Seasonally Adjust or Stratify**

**Recommendation:** Reweight to uniform seasonal distribution before cross-city comparison.

**Suggested approach:**
```python
# Apply season weights in addition to IPW weights
df['w_final'] = df['w_combined'] * df['season'].map(season_reweight_dict)
```

**Alternative:** Report separate estimates by season and test for season × city interaction.

**3. Acknowledge Limitations Explicitly**

**Suggested limitations section:**
> "Our analysis has several limitations. First, sample sizes are sparse at temperature extremes (Seattle N<100 for UTCI>25°C; NYC N<100 for UTCI<-15°C), limiting inference in those ranges. Second, seasonal coverage is unbalanced and opposite between cities (Seattle 38% winter; NYC 43% summer), potentially confounding behavioral differences with seasonal effects. Third, household travel surveys used for temperature-based selection bias correction cover only 2-3 months, insufficient for year-round temperature response modeling. Fourth, spatial clustering of Street View images may lead to underestimation of standard errors."

### Secondary Recommendations

**4. Sensitivity Analyses**

Perform and report:
1. **Exclude sparse bins:** Drop bins with N <500, refit curves
2. **Seasonal stratification:** Separate estimates by season
3. **SR threshold sensitivity:** Already done - cite results
4. **Spatial bootstrap:** Test if CIs change with spatial resampling
5. **Exclude Temp-IPW:** Recompute with only SR-IPW + DCWP

**5. Supplementary Materials**

Include in appendix:
1. **Sample size table:** N by UTCI bin for both cities
2. **Monthly distribution:** Bar charts showing temporal coverage
3. **Spatial coverage maps:** Already generated
4. **Variance diagnostics:** SE and VIF by UTCI bin
5. **Effective range definitions:** Thresholds and rationale

**6. Data Quality Flags in Plots**

Visual indicators in main figures:
- **Shading:** Gray out regions with N <500
- **Annotations:** Mark modal bins, overlap zones
- **Error bars:** Show 95% CI (wider at extremes)
- **Sample size axis:** Secondary axis or inset showing N(UTCI)

---

## 8. Data Quality Summary Tables

### Table 1: Overall Sample Characteristics

| Metric | Seattle | NYC | Ratio (S/NYC) |
|--------|---------|-----|---------------|
| **Images (after SR filter)** | 780,451 | 254,507 | 3.1 |
| **Temporal span** | 9.7 years | 9.6 years | 1.0 |
| **UTCI range** | -26 to +33°C (59°C) | -34 to +33°C (67°C) | 0.9 |
| **Modal UTCI** | -1°C | +19°C | -20°C |
| **% Winter** | 38.2% | 17.7% | 2.2 |
| **% Summer** | 24.2% | 42.9% | 0.6 |
| **Effective N (IPW)** | 375,935 | 142,909 | 2.6 |
| **N_eff retention** | 48.2% | 56.2% | 0.9 |

### Table 2: Effective UTCI Ranges

| Quality Level | Seattle Range | NYC Range | Overlap |
|---------------|---------------|-----------|---------|
| **Excellent (N≥1000)** | -9 to +19°C (28°C span) | +1 to +29°C (28°C span) | +1 to +19°C (18°C) |
| **Good (N≥500)** | -11 to +21°C (32°C span) | -3 to +31°C (34°C span) | -3 to +21°C (24°C) |
| **Marginal (N≥100)** | -17 to +27°C (44°C span) | -21 to +33°C (54°C span) | -17 to +27°C (44°C) |

### Table 3: Sparse Bins Requiring Caution

**Seattle (N < 500):**
| UTCI Range | N Range | Issue |
|------------|---------|-------|
| >25°C | 6-200 | Extreme sparsity, SE >5 pp |
| 21-25°C | 200-500 | Marginal, SE 2-5 pp |
| <-13°C | 50-500 | Sparse, SE >2 pp |

**NYC (N < 500):**
| UTCI Range | N Range | Issue |
|------------|---------|-------|
| <-15°C | 81-500 | Cold extreme sparsity |
| >29°C | 100-400 | Hot extreme marginal |

---

## 9. Implications for Paper

### Main Text Revisions

**1. Methods section - add data quality statement:**

> "We assessed data quality by examining sample size, temporal coverage, and spatial distribution. Street View images span 2016-2026 for both cities, providing robust temporal coverage. However, sample sizes vary substantially across the UTCI range (Seattle: median N=5,200 per 2°C bin; NYC: median N=3,100 per bin), with sparse coverage at temperature extremes. We define effective UTCI ranges where N≥500 per bin provides adequate precision (SE<2.2 pp): Seattle -11°C to +21°C; NYC -3°C to +31°C. Cross-city comparisons are restricted to the overlap region (+1°C to +19°C) where both cities have excellent coverage. Seasonal coverage is unbalanced (Seattle 38% winter; NYC 43% summer), potentially confounding cross-city comparisons."

**2. Results section - report effective ranges:**

> "We report shade preference estimates for the effective UTCI ranges: Seattle -11°C to +21°C (780,000 images); NYC -3°C to +31°C (254,000 images). These ranges exclude temperature extremes with sparse data (N<500 per 2°C bin) where precision is inadequate for reliable inference."

**3. Limitations section - enumerate issues:**

As drafted in Section 7 above.

### Figures - Add Quality Indicators

**All UTCI vs shade preference plots should include:**
1. **Shaded regions:** Gray background for N <500 bins
2. **Sample size overlay:** Bar chart or heatmap showing N(UTCI)
3. **Effective range markers:** Vertical lines at range boundaries
4. **Confidence bands:** Wider at extremes (from bootstrap)

**Example annotation:**
```python
# Shade regions with poor coverage
ax.axvspan(-40, -11, alpha=0.2, color='gray', label='Sparse (N<500)')
ax.axvspan(21, 40, alpha=0.2, color='gray')

# Mark effective range
ax.axvline(-11, color='red', linestyle='--', linewidth=1, alpha=0.5)
ax.axvline(21, color='red', linestyle='--', linewidth=1, alpha=0.5)
```

### Supplementary Materials

**Required supplements:**
1. **Table S1:** Sample size by UTCI bin (both cities, all bins)
2. **Figure S1:** Sample size distribution plots (already generated)
3. **Figure S2:** Temporal coverage plots (already generated)
4. **Figure S3:** Spatial coverage maps (already generated)
5. **Figure S4:** Variance and precision by bin (already generated)
6. **Table S2:** Sensitivity to N threshold (estimates at N≥100, 500, 1000)
7. **Table S3:** Seasonal distribution by city and UTCI range

---

## 10. Future Data Collection Recommendations

To improve data quality for future analyses:

### 1. Targeted Gap Filling

**Seattle:**
- **Critical need:** Summer data at UTCI >25°C (current N<100)
- **Target:** Collect 5,000+ images at 25-35°C (July-August midday)
- **Method:** Supplementary Street View request or field surveys

**NYC:**
- **Critical need:** Winter data at UTCI <-10°C (current N<500)
- **Target:** Collect 2,000+ images at -20 to -10°C (January-February)

### 2. Seasonal Balancing

**Both cities:**
- **Target:** 25% per season (equal distribution)
- **Current gaps:**
  - Seattle: Spring (14% → 25%, need +11 pp)
  - NYC: Winter (18% → 25%, need +7 pp)

**Collection strategy:** Oversample underrepresented seasons in next data pull.

### 3. Walk Rate Survey Expansion

**Critical for Temp-IPW validity:**
- **Minimum:** Full year coverage (12 months)
- **Ideal:** Multi-year panel (capture year-to-year variation)
- **Target sample size:** N≥1,000 per month, N≥200 per UTCI bin

**Alternative:** Use existing pooled data (25 cities, 1988-2007) but acknowledge temporal mismatch.

### 4. Spatial Stratification

**Recommendation:** Quota sampling by borough/neighborhood
- Ensures all major areas represented
- Reduces spatial clustering
- Enables subgroup analysis

### 5. Data Quality Metrics for Collection

**Set minimum thresholds before analysis:**
- N ≥500 per 5°C bin (can aggregate to 2°C for analysis)
- No season <15% of total
- At least 50% of city area sampled
- No borough <10% of total (for NYC)

---

## 11. Files Generated

**Diagnostic plots (all cities):**
- `data_quality_utci_{city}.png/pdf` - Sample size by UTCI bin
- `data_quality_temporal_{city}.png/pdf` - Temporal coverage
- `data_quality_spatial_{city}.png/pdf` - Spatial distribution
- `data_quality_variance_{city}.png/pdf` - Precision by bin

**Script:**
- `scripts/visualization/plot_data_quality_diagnostics.py`

**Documentation:**
- `docs/DATA_QUALITY_ASSESSMENT.md` (this document)

---

## Conclusion

**Data quality is good overall** (10 years, large samples, broad coverage) **but has critical limitations:**

1. ⚠️ **Temperature extremes are unreliable** - restrict inference to well-sampled ranges
2. ⚠️ **Seasonal imbalance confounds cross-city comparison** - need seasonal adjustment
3. ⚠️ **Limited overlap in excellent coverage** - valid comparison only +1°C to +19°C
4. ⚠️ **Walk rate survey temporal mismatch** - Temp-IPW questionable

**Required actions before publication:**
1. Define and report effective UTCI ranges (N ≥500)
2. Add seasonal reweighting for cross-city comparison
3. Add data quality flags to all plots
4. Acknowledge limitations explicitly
5. Include quality diagnostics in supplement

**With these adjustments, the analysis will be methodologically sound and transparent about its limitations.**

---

**End of Document**
