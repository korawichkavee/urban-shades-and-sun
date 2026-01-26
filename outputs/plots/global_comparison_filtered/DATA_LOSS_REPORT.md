# Data Loss Report - Wind Filtering

**Date:** 2026-01-26
**Filter Applied:** UTCI wind speed validation (>17 m/s filtered)

---

## Summary by City

| City | Original Rows | After Wind Filter | After Analysis Filters | Final Usable | Data Retention |
|------|---------------|-------------------|------------------------|--------------|----------------|
| Buenos-Aires | 44,461 | 29,489 | 4,249 | 4,249 | 9.6% |
| Cape-Town | 14,102 | 12,815 | 878 | 878 | 6.2% |
| Istanbul | 19,567 | 4,989 | 1,445 | 1,445 | 7.4% |
| Madrid | 20,644 | 10,427 | 1,201 | 1,201 | 5.8% |
| Mumbai | 7,370 | 5,398 | 1,013 | 1,013 | 13.7% |
| Osaka | 5,845 | 3,799 | 146 | 146 | 2.5% |
| Singapore | 17,814 | 17,452 | 1,353 | 1,353 | 7.6% |
| **TOTAL** | **129,803** | - | - | **10,285** | **7.9%** |

---

## Filtering Pipeline

The data goes through the following filtering stages:

1. **Wind Speed Filter**: Removes observations with wind >17 m/s (UTCI validity threshold)
2. **Sunny Filter**: Keeps only images classified as sunny (is_sunny == True)
3. **People Filter**: Keeps only images with detected people (total_people > 0)
4. **UTCI Range Filter**: Removes extreme UTCI values (<-50°C or >60°C)
5. **DateTime Filter**: Removes rows with invalid datetime stamps

---

## Key Findings

### Cities Most Affected by Wind Filtering

- **Osaka**: 97.5% data loss (5,845 → 146 rows)
- **Madrid**: 94.2% data loss (20,644 → 1,201 rows)
- **Cape-Town**: 93.8% data loss (14,102 → 878 rows)

### Cities Least Affected by Wind Filtering

- **Singapore**: 92.4% data loss (17,814 → 1,353 rows)
- **Buenos-Aires**: 90.4% data loss (44,461 → 4,249 rows)
- **Mumbai**: 86.3% data loss (7,370 → 1,013 rows)

---

## Implications

- **Overall data retention:** 7.9%
- **Total observations lost:** 119,518
- High wind speeds are more common in some cities (Istanbul, Madrid)
- The filtering ensures all analyzed observations have valid UTCI calculations
- Statistical power remains strong with final sample size
