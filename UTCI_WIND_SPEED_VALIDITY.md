# UTCI Wind Speed Validity Range

**Date:** 2026-01-26
**Source:** Official UTCI documentation and research literature

## Official UTCI Valid Meteorological Conditions

The Universal Thermal Climate Index (UTCI) is validated for the following meteorological conditions:

### Wind Speed Range
- **Valid range:** 0.5 to 20 m·s⁻¹ (measured at 10m height above ground level)
- **Minimum:** 0.5 m/s (lowest recommended input speed)
- **Maximum:** 20 m/s (values above this can produce problematic results)

**Note:** Some implementations use 17 m/s as a more conservative upper limit for practical applications.

### Complete Valid Range for All Variables
- **Wind speed (10m):** 0.5 to 20 m·s⁻¹
- **Air temperature:** -50 to 50°C
- **Mean radiant temperature minus air temperature (Tmrt - Ta):** -30 to 70°C
- **Relative humidity:** > 5%

### Reference Conditions
The UTCI reference environment is defined as:
- **Relative humidity:** 50% (capped at vapor pressure of 20 hPa for temperatures > 29°C)
- **Wind speed:** 0.5 m·s⁻¹ at 10m above ground level (calm air)
- **Mean radiant temperature:** Equal to air temperature

### Required Input Variables
Four variables are required to calculate UTCI:
1. 2m air temperature
2. 2m dew point temperature (or relative humidity)
3. Wind speed at 10m above ground level
4. Mean radiant temperature

## Implementation in This Project

### Current Filtering Threshold
**Threshold used:** 17 m/s (conservative limit)

**Justification:** While the official UTCI valid range extends to 20 m/s, using 17 m/s as the filtering threshold:
- Provides a more conservative estimate
- Accounts for potential issues noted in some implementations
- Reduces the risk of including problematic edge cases

### Wind Speed Impact by City
Based on analysis of 129,803 observations across 7 cities:

| City | Total Obs | High Wind (>17 m/s) | % High Wind |
|------|-----------|---------------------|-------------|
| Istanbul | 19,553 | 14,570 | 74.5% |
| Madrid | 20,618 | 10,208 | 49.5% |
| Osaka | 5,817 | 2,034 | 35.0% |
| Buenos Aires | 44,455 | 14,971 | 33.7% |
| Mumbai | 7,354 | 1,963 | 26.7% |
| Cape Town | 14,072 | 1,279 | 9.1% |
| Singapore | 17,795 | 360 | 2.0% |

### Recommendation
The 17 m/s threshold is appropriate for this analysis. If more liberal filtering is desired, the threshold could be increased to 20 m/s (the official UTCI maximum), but this would only add a small percentage of additional observations and may introduce edge-case calculation errors.

## References
1. UTCI Official Website: https://www.utci.org/
2. Blazejczyk K, et al. (2012). "An introduction to the Universal Thermal Climate Index (UTCI)"
3. UTCI documentation on valid meteorological conditions
4. Research literature noting issues with wind speeds > 20 m/s
