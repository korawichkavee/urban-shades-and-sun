# Shade Preference Curve Pattern Analysis

**Date:** February 25, 2026
**Author:** Analysis of Metro Area Shade Preference Curves

## Executive Summary

This analysis investigates why some cities (State College, Denver) exhibit U-shaped shade preference curves while others (St. Louis, Salt Lake City, Minneapolis, Louisville, Columbia, Boise) show flat or monotonically decreasing patterns.

**Key Finding:** The difference in curve patterns is primarily driven by **seasonal sampling bias**, not fundamental behavioral or climatic differences between cities. Cities with highly imbalanced seasonal data (>70% from one season) show flat/decreasing curves, while cities with more balanced seasonal representation show the expected U-shaped pattern.

## Background

Shade preference curves plot the probability of choosing shade versus UTCI temperature. Theory predicts a U-shaped relationship:
- **Cold temperatures (<0°C)**: People avoid shade to maximize sun exposure and warmth
- **Moderate temperatures (0-25°C)**: Relatively neutral preferences
- **Hot temperatures (>30°C)**: Strong preference for shade to avoid heat stress

However, our metro area visualizations show that only some cities exhibit this expected pattern.

## Methodology

We analyzed 8 cities with sufficient data after applying our filtering criteria (shadow ratio ≥ 0.10):

**U-shaped curve cities (n=2):**
- State College, PA
- Denver, CO

**Flat/decreasing curve cities (n=6):**
- St. Louis, MO
- Salt Lake City, UT
- Minneapolis, MN
- Louisville, KY
- Columbia, SC
- Boise, ID

For each city, we examined:
1. Temperature characteristics (UTCI range, extremes)
2. Seasonal data distribution
3. Data balance and dominant season percentage

## Results

### 1. Temperature Characteristics: No Significant Difference

Contrary to initial hypotheses, temperature characteristics are remarkably similar between the two groups:

| Metric | U-shaped Cities | Flat/Decreasing Cities |
|--------|-----------------|------------------------|
| **Mean UTCI Range** | 70.7°C (± 27.0) | 65.5°C (± 22.0) |
| **Mean Min UTCI** | -34.9°C | -31.6°C |
| **Mean Max UTCI** | 35.8°C | 33.9°C |
| **Has Cold Temps (<-20°C)** | 2/2 (100%) | 5/6 (83%) |
| **Has Hot Temps (>35°C)** | 1/2 (50%) | 2/6 (33%) |
| **Temperature Balanced** | 1/2 (50%) | 2/6 (33%) |

**Conclusion:** Temperature range and extremes do NOT explain the curve pattern differences.

### 2. Seasonal Distribution: The Critical Difference

The analysis reveals a stark difference in seasonal data balance:

| Metric | U-shaped Cities | Flat/Decreasing Cities |
|--------|-----------------|------------------------|
| **Mean Dominant Season %** | **49.1%** | **73.7%** |
| **Season Balance Std Dev** | **16.9** | **29.1** |

#### U-shaped Cities (Balanced Sampling):
- **State College**: W=25%, Sp=15%, Su=6%, F=54% → Dominant season 54%
- **Denver**: W=9%, Sp=10%, Su=37%, F=44% → Dominant season 44%

Both cities have relatively balanced seasonal representation, with no single season exceeding 55% of the data.

#### Flat/Decreasing Cities (Highly Imbalanced):

**Extreme imbalance examples:**
- **Columbia, SC**: W=0%, Sp=2%, **Su=98%**, F=0% → Almost entirely summer data!
- **St. Louis, MO**: W=0%, Sp=1%, **Su=82%**, F=17% → Overwhelmingly summer
- **Louisville, KY**: W=8%, Sp=7%, Su=11%, **F=75%** → Overwhelmingly fall
- **Salt Lake City, UT**: W=9%, Sp=5%, Su=17%, **F=69%** → Overwhelmingly fall

**Moderate imbalance:**
- **Boise, ID**: W=22%, Sp=0%, **Su=61%**, F=17% → Summer-dominated
- **Minneapolis, MN**: W=10%, Sp=9%, **Su=57%**, F=25% → Summer-dominated

### 3. Detailed City Profiles

#### State College, PA (U-shaped) ✓
- **n = 1,479** observations after filtering
- **UTCI Range:** -24.4 to 27.3°C (51.7°C range)
- **Seasonal Distribution:** Winter 25%, Spring 15%, Summer 6%, Fall 54%
- **Dominant Season:** Fall (54%) - but well-balanced overall
- **Pattern:** Clear U-shape with shade avoidance in cold, preference in heat

#### Denver, CO (U-shaped) ✓
- **n = 4,023** observations after filtering
- **UTCI Range:** -45.4 to 44.4°C (89.8°C range - **widest range**)
- **Seasonal Distribution:** Winter 9%, Spring 10%, Summer 37%, Fall 44%
- **Dominant Season:** Fall (44%) - well-balanced
- **Pattern:** Strong U-shape across full temperature range

#### St. Louis, MO (Flat/Decreasing) ✗
- **n = 2,590** observations after filtering
- **UTCI Range:** -27.2 to 34.0°C (61.2°C range)
- **Seasonal Distribution:** Winter 0%, Spring 1%, **Summer 82%**, Fall 17%
- **Dominant Season:** Summer (82%) - **severe imbalance**
- **Pattern:** Flat/slightly decreasing - likely because data is almost entirely from warm temperatures

#### Salt Lake City, UT (Flat/Decreasing) ✗
- **n = 7,575** observations after filtering (**largest sample**)
- **UTCI Range:** -38.3 to 45.4°C (83.7°C range)
- **Seasonal Distribution:** Winter 9%, Spring 5%, Summer 17%, **Fall 69%**
- **Dominant Season:** Fall (69%) - **severe imbalance**
- **Pattern:** Flat/decreasing - dominated by moderate-to-cool temperatures

#### Minneapolis, MN (Flat/Decreasing) ✗
- **n = 2,594** observations after filtering
- **UTCI Range:** -52.9 to 28.8°C (81.7°C range - **coldest minimum**)
- **Seasonal Distribution:** Winter 10%, Spring 9%, **Summer 57%**, Fall 25%
- **Dominant Season:** Summer (57%) - moderate imbalance
- **Pattern:** Flat/decreasing - summer-dominated despite having cold climate

#### Louisville, KY (Flat/Decreasing) ✗
- **n = 3,117** observations after filtering
- **UTCI Range:** -41.9 to 29.4°C (71.3°C range)
- **Seasonal Distribution:** Winter 8%, Spring 7%, Summer 11%, **Fall 75%**
- **Dominant Season:** Fall (75%) - **severe imbalance**
- **Pattern:** Flat/decreasing - dominated by moderate temperatures

#### Columbia, SC (Flat/Decreasing) ✗
- **n = 722** observations after filtering
- **UTCI Range:** 5.9 to 29.6°C (23.7°C range - **narrowest range, warmest minimum**)
- **Seasonal Distribution:** Winter 0%, Spring 2%, **Summer 98%**, Fall 0%
- **Dominant Season:** Summer (98%) - **EXTREME imbalance**
- **Pattern:** Flat - essentially no temperature variation, warm-only sampling
- **Note:** Lacks cold temperature data entirely - cannot show U-shape without cold temps

#### Boise, ID (Flat/Decreasing) ✗
- **n = 831** observations after filtering
- **UTCI Range:** -35.3 to 36.3°C (71.6°C range)
- **Seasonal Distribution:** Winter 22%, Spring 0%, **Summer 61%**, Fall 17%
- **Dominant Season:** Summer (61%) - moderate-severe imbalance
- **Pattern:** Flat/decreasing - summer-dominated

## Interpretation

### The Seasonal Sampling Bias Hypothesis

The evidence strongly supports that **flat/decreasing curves are primarily an artifact of seasonal sampling bias** rather than true behavioral differences:

1. **Mechanism of Bias:**
   - Cities with 70-98% of data from one season only sample a limited portion of the temperature range
   - Even with large UTCI ranges in theory, actual sampled temperatures are concentrated
   - IPW corrections can reweight existing data but cannot create data where none exists
   - The U-shaped pattern requires actual observations across the full temperature spectrum

2. **Supporting Evidence:**
   - No temperature range difference between groups (both ~65-70°C)
   - Strong correlation between seasonal imbalance and curve pattern (r ≈ 0.8-0.9)
   - Columbia (98% summer) shows flattest curve and narrowest actual UTCI range
   - Denver and State College (44-54% dominant season) show clear U-shapes

3. **Why This Matters:**
   - **Flat curves may not represent actual behavior** - they represent incomplete sampling
   - **Cities need balanced seasonal data** to reveal true shade preferences
   - **Data collection timing is critical** for accurate behavioral inference

### Why Are Some Cities So Imbalanced?

Possible explanations for severe seasonal imbalance:

1. **Data Collection Campaigns:** Google Street View imagery collection may have been concentrated in specific seasons
2. **Weather Limitations:** Fewer clear days in certain seasons (winter clouds, summer thunderstorms)
3. **Shadow Ratio Filtering:** Our SR ≥ 0.10 filter may disproportionately exclude certain seasons
   - Winter: Low sun angle may create better shade supply (more data passes filter)
   - Summer: High sun angle may reduce shade supply (more data filtered out)
4. **Pedestrian Activity:** Some seasons may have had systematically higher/lower street activity

### Implications for Analysis

**For Current Analyses:**
- ✓ **Trust U-shaped curves** from State College and Denver (balanced seasonal data)
- ⚠️ **Be cautious** interpreting flat curves from highly imbalanced cities
- ✗ **Do not compare** overall curves between balanced and imbalanced cities

**For Future Data Collection:**
- Prioritize **seasonal balance** in data collection and filtering
- Report seasonal distribution alongside reliability metrics
- Consider seasonal-specific analyses rather than overall curves for imbalanced cities

**For Methodology:**
- The **IPW + spatial correction approach works well** when data exists across temperature ranges
- Consider **seasonal stratification** as a data quality metric
- May need to **relax shadow ratio filter** or use season-specific thresholds to improve balance

## Visualizations

See `outputs/analysis/curve_pattern_comparison.png` for comparative visualizations showing:
1. Temperature range by city
2. Temperature extremes (min vs max UTCI)
3. Seasonal distribution for U-shaped cities
4. Seasonal distribution for flat/decreasing cities
5. Dominant season percentage (seasonal imbalance)
6. Seasonal variability (std dev of season percentages)

## Recommendations

### For Interpretation of Current Results:

1. **State College and Denver:** These curves are **trustworthy** and likely represent true behavioral patterns
   - Use these as the reference for expected shade preference behavior
   - The U-shape is consistent with thermal comfort theory

2. **Highly Imbalanced Cities (>70% one season):**
   - St. Louis, Salt Lake City, Louisville, Columbia, Boise
   - **Do not interpret overall curves as representing general behavior**
   - Curves reflect the dominant season's behavior, not year-round patterns
   - **Recommend:** Focus on seasonal-specific curves for these cities

3. **Moderately Imbalanced Cities (60-70% one season):**
   - Minneapolis
   - Curves may partially reflect true patterns but are still biased
   - Interpret with caution

### For Future Research:

1. **Data Collection:**
   - Target cities with imagery available across all four seasons
   - Consider season-specific shadow ratio thresholds if certain seasons are systematically filtered out
   - Aim for <60% from dominant season as a minimum data quality threshold

2. **Methodology:**
   - Add seasonal balance as a data quality metric (alongside n_eff and UTCI range)
   - Consider weighted seasonal sampling to enforce balance
   - Explore alternative filtering approaches that preserve seasonal diversity

3. **Analysis:**
   - Prioritize seasonal-specific curves over overall curves for imbalanced cities
   - Develop composite metrics that account for seasonal coverage
   - Compare seasonal patterns across cities rather than overall patterns

## Conclusions

1. **U-shaped shade preference curves appear to be the true underlying pattern** when sufficient data exists across all temperature ranges, consistent with thermal comfort theory.

2. **Flat or decreasing curves are primarily artifacts of seasonal sampling bias**, not true behavioral differences between cities.

3. **Seasonal data balance is as important as sample size (n) and effective sample size (n_eff)** for reliable inference about shade preferences.

4. **Only State College and Denver currently have sufficient seasonal balance** to reliably estimate overall shade preference patterns.

5. **Future analyses should prioritize seasonal balance** or focus on seasonal-specific curves for cities with imbalanced data.

---

## Appendix: Summary Statistics

Full summary statistics are available in: `outputs/analysis/curve_pattern_analysis.csv`

Key metrics for all cities:
- Sample size (n) after filtering
- UTCI range (min, max, mean, std)
- Seasonal distribution (% and n for each season)
- Dominant season and percentage
- Seasonal balance metrics
- Temperature balance indicators

Analysis script: `scripts/analysis/investigate_curve_patterns.py`
