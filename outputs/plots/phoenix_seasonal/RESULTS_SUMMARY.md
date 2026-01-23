# Phoenix UTCI Shade-Seeking Analysis Results

## Successfully Generated Plots (df=4)

### ✅ Overall Plot (All Data Combined)
- **File**: `phoenix_overall_utci_shade_gam.png`
- **Data**: 811 observations, 1,125 people total across all seasons
- **UTCI range**: -19.6°C to 44.7°C
- **Method**: Binomial GAM with df=4, cubic B-splines
- **Shows**: Single smooth curve across entire temperature range with 95% CI

### ✅ Fall Seasonal Plot
- **File**: `phoenix_fall_utci_shade_gam.png`
- **Data**: 103 observations, 143 people
- **UTCI range**: -2.2°C to 33.4°C
- **Overall shade ratio**: 16.1%
- **Unique UTCI values**: 5
- **Method**: Binomial GAM with df=4

### ✅ Winter Seasonal Plot
- **File**: `phoenix_winter_utci_shade_gam.png`
- **Data**: 27 observations, 43 people
- **UTCI range**: -19.6°C to 11.0°C
- **Overall shade ratio**: 0% (no shade-seeking observed)
- **Unique UTCI values**: 5
- **Note**: Very limited data, wide confidence intervals expected

## Failed to Generate (Technical Issues)

### ❌ Spring Seasonal Plot
- **Data**: 335 observations, 490 people
- **UTCI range**: 0.7°C to 20.6°C
- **Unique UTCI values**: 7
- **Error**: "data points fall outside the outermost knots"
- **Cause**: BSplines transform issue with prediction grid
- **Overall shade ratio**: 22.9% (highest among seasons)

### ❌ Summer Seasonal Plot
- **Data**: 346 observations, 449 people
- **UTCI range**: 27.6°C to 44.7°C
- **Unique UTCI values**: 9
- **Error**: "data points fall outside the outermost knots"
- **Cause**: BSplines transform issue with prediction grid
- **Overall shade ratio**: 13.8% (lowest among seasons)

---

## Key Findings

### Seasonal Shade-Seeking Patterns

| Season | Observations | People | Shade Ratio | Mean UTCI | Unique Temps |
|--------|--------------|--------|-------------|-----------|--------------|
| **Spring** | 335 | 490 | **22.9%** | 11.2°C | 7 |
| Summer | 346 | 449 | 13.8% | 35.3°C | 9 |
| Fall | 103 | 143 | 16.1% | 20.5°C | 5 |
| Winter | 27 | 43 | 0.0% | -17.5°C | 5 |

### Surprising Result: Spring > Summer Shade-Seeking

The **highest shade ratio occurs in Spring (22.9%)**, not Summer (13.8%). Possible explanations:

1. **Selection bias**: Different types of people/activities in different seasons
2. **Shade availability**: More shade structures available in spring locations
3. **Adaptation**: Phoenix residents may be more adapted to summer heat
4. **Sample timing**: Spring images may be from hotter parts of the day
5. **Small sample effects**: Only 5-9 unique temperature points per season

### Data Limitations

1. **Sparse unique temperatures**: Only 5-9 unique UTCI values per season
   - Limits ability to fit smooth curves
   - Essentially "categorical" data despite continuous measurement

2. **Clustered observations**:
   - Multiple images share same weather (same day/time)
   - Spring: 47.9 obs per unique UTCI value
   - Summer: 38.4 obs per unique UTCI value

3. **Small sample sizes for some seasons**:
   - Winter: Only 27 observations
   - Fall: Only 103 observations

4. **Technical constraints**:
   - Spring and Summer failed due to BSplines knot placement issues
   - df=4 is minimum for cubic splines (technical requirement)
   - df=4 vs 5-9 unique values = marginal for smooth fitting

---

## Statistical Approach

### Method: Binomial GAM

**Model specification**:
```
logit(P(shade)) = f(UTCI)

where f() is a smooth function using cubic B-splines with df=4
```

**Why this method?**
- Response is proportion data (bounded 0-1)
- Binomial family with logit link respects bounds
- Smooth splines capture non-linear relationships
- Proper confidence intervals accounting for binomial variance

### Degrees of Freedom Choice

**Used df=4 because**:
1. Minimum for cubic splines (df >= degree + 1 = 3 + 1 = 4)
2. Balances smoothness with sparse unique x-values
3. Assumes smooth behavioral response (reasonable for temperature)

**Constraints from data**:
- Need df < (n_unique_x - 1)
- Spring (7 unique): df ≤ 6 ✓
- Summer (9 unique): df ≤ 8 ✓
- Fall (5 unique): df ≤ 4 ✓ (exactly at limit)
- Winter (5 unique): df ≤ 4 ✓ (exactly at limit)

---

## Interpretation of Results

### Overall Plot (Most Reliable)

The overall plot combining all seasons provides:
- Largest sample size (811 observations)
- Widest temperature range (-19.6°C to 44.7°C)
- Most reliable curve estimates
- Shows general trend across full thermal comfort spectrum

**Visual inspection shows** (check the actual plot):
- Shade-seeking behavior vs UTCI relationship
- Confidence intervals (wider at temperature extremes)
- Seasonal clustering visible in scatter points

### Confidence Intervals

**Wide CIs indicate**:
- Statistical uncertainty due to sparse data
- Areas with fewer observations
- Binomial variance (changes with proportion)

**Narrow CIs indicate**:
- More observations at that temperature
- More certain about the relationship
- Note: Even with many observations at one UTCI value, CIs can be wide if proportion is near 0.5

---

## Recommendations

### For Interpreting These Results

1. **Focus on overall plot** - most stable estimates
2. **Don't over-interpret wiggles** - only 5-9 unique temperatures per season
3. **Note the surprising Spring result** - warrants further investigation
4. **Consider confidence intervals** - uncertainty is substantial

### For Future Analysis

1. **Collect more diverse temporal data**:
   - More days across each season
   - Different times of day
   - Result: More unique UTCI values for smoother curves

2. **Consider simpler models**:
   - Binned categorical analysis (hot/mild/cold)
   - Linear or quadratic logistic regression
   - Mixed effects models (account for date/location clustering)

3. **Alternative visualizations**:
   - Box plots by temperature bins
   - Bar charts by season
   - Time series showing temporal patterns

4. **Investigate Spring paradox**:
   - Check time-of-day distribution
   - Examine shade structure availability
   - Consider sample selection effects

---

## Files Generated

1. **phoenix_overall_utci_shade_gam.png** - All data combined
2. **phoenix_fall_utci_shade_gam.png** - Fall season only
3. **phoenix_winter_utci_shade_gam.png** - Winter season only
4. **Phoenix_1840020568_with_utci.csv** - Data with UTCI added
5. **METHODOLOGY.md** - Statistical methods explanation
6. **TECHNICAL_DISCUSSION.md** - Deep dive on GAM issues
7. **RESULTS_SUMMARY.md** - This file

---

## Code and Reproducibility

**Script**: `visualize_phoenix_seasonal_utci_gam.py`

**Key parameters**:
- df=4 (degrees of freedom for B-splines)
- degree=3 (cubic splines)
- Binomial family with logit link
- 95% confidence intervals

**Data filtering**:
- Sunny images only (`is_sunny = True`)
- At least 1 person detected (`total_people > 0`)
- Valid shade counts (no missing data)
- Valid UTCI data

**To reproduce**:
```bash
source .venv/bin/activate
python visualize_phoenix_seasonal_utci_gam.py
```
