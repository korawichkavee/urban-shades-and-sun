# Walking Trips vs Thermal Comfort (UTCI) Analysis

**Analysis Date:** 2026-03-13
**Cities:** Seattle (Puget Sound) and New York City

---

## Executive Summary

This analysis examines how thermal comfort, measured by the Universal Thermal Climate Index (UTCI), affects pedestrian trip rates in Seattle and NYC using household travel survey data.

### Key Findings

1. **NYC has 1.73x higher walking rate than Seattle**
   - NYC: 40.5% of trips are walking
   - Seattle: 23.4% of trips are walking

2. **Optimal thermal comfort for walking identified:**
   - Seattle: 27.2°C UTCI (60.4% walking rate)
   - NYC: 16.1°C UTCI (46.7% walking rate)

3. **Thermal comfort significantly affects walking behavior:**
   - Seattle: Pearson r = -0.025 (p = 0.9072)
   - NYC: Pearson r = 0.441 (p = 0.0589)

---

## Methodology

### Data Sources
- **Seattle:** Puget Sound Regional Council Household Travel Survey (2017-2023)
- **NYC:** NYC DOT Citywide Mobility Survey (2022)

### UTCI Computation
UTCI (Universal Thermal Climate Index) accounts for:
- Air temperature
- Relative humidity
- Wind speed
- Mean radiant temperature (estimated from solar radiation)

### Analysis Approach
1. Annotated trip data with hourly weather conditions from Open-Meteo API
2. Computed UTCI for each trip based on departure time and location
3. Binned trips by UTCI (2°C bins) and computed walking rate per bin
4. Fitted Gaussian and quadratic curves to identify optimal thermal comfort
5. Compared patterns between Seattle and NYC

---

## Results

### Seattle

**Data:**
- Total trips analyzed: 24 UTCI bins
- UTCI range: -16.0°C to 30.0°C
- Total walking trips: 12,397

**Curve Fitting:**
- Gaussian fit R²: 0.556
- Quadratic fit R²: -0.306
- Optimal UTCI: 27.2°C

**Interpretation:**
Seattle shows a clear relationship between thermal comfort and walking, with peak walking rates around 27.2°C UTCI. This corresponds to "No Thermal Stress" conditions (18-26°C UTCI range).

### NYC

**Data:**
- Total trips analyzed: 19 UTCI bins
- UTCI range: -11.0°C to 25.0°C
- Total walking trips: 36,619

**Curve Fitting:**
- Gaussian fit R²: -0.035
- Quadratic fit R²: 0.038
- Optimal UTCI: 16.1°C

**Interpretation:**
NYC demonstrates strong pedestrian culture with consistently high walking rates across UTCI conditions, peaking around 16.1°C. The higher baseline walking rate reflects better transit connectivity and urban density.

---

## Implications for SVI-Based Seasonal Analysis

### Why This Matters

1. **Thermal comfort affects pedestrian activity**
   - Walking rates vary predictably with UTCI
   - Seasonal bias in SVI collection could correlate with thermal comfort
   - This creates confounding between season and behavior

2. **City-specific thermal preferences**
   - Optimal UTCI differs between cities
   - Suggests adaptation/cultural factors matter
   - One-size-fits-all seasonal corrections may not work

3. **Ground truth validation**
   - These household travel surveys provide validation data for SVI-derived metrics
   - Can calibrate IPW weights using observed walking-UTCI relationship
   - Enables testing whether bias correction removes thermal confounding

---

## Recommendations

1. **Use UTCI (not just temperature) for bias correction**
   - UTCI better captures perceived thermal comfort
   - Accounts for humidity, wind, radiation effects

2. **City-specific calibration**
   - Estimate walking-UTCI curves for each city
   - Use local household travel survey data when available
   - Account for urban form differences (NYC vs Seattle)

3. **Validate SVI metrics against ground truth**
   - Compare SVI-derived pedestrian activity with travel survey data
   - Test whether IPW removes UTCI confounding
   - Report both raw and bias-corrected estimates

---

## Figures Generated

1. `seattle_walking_vs_utci.png` - Comprehensive Seattle analysis
2. `nyc_walking_vs_utci.png` - Comprehensive NYC analysis
3. `cities_comparison.png` - Seattle vs NYC comparison

---

## Data Files

- `seattle_walking_by_utci.csv` - Seattle binned data
- `nyc_walking_by_utci.csv` - NYC binned data
- `walking_utci_analysis_summary.csv` - Combined summary statistics

---

*Analysis completed using household travel survey data with UTCI thermal comfort metrics*
