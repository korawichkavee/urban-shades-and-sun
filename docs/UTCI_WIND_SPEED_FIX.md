# UTCI Wind Speed Unit Bug — Discovery and Fix

**Date:** 2026-02-17
**File changed:** `scripts/utils/enhanced_utci.py`

---

## Summary

UTCI values computed from ERA5 data were severely underestimated (median ~−5 °C for State College, PA instead of the physically expected ~+9 °C) due to wind speed being passed in km/h where m/s was required.

---

## Root Cause

The Open-Meteo ERA5 API returns `wind_speed_10m` in **km/h** (confirmed via the `hourly_units` key in the API response).

The `thermofeel.calculate_utci()` function expects wind speed (`va`) in **m/s**.

The original code passed the raw API value directly, inflating wind speed by a factor of 3.6:

```python
# BEFORE (buggy) — Va is in km/h, but thermofeel expects m/s
Va = winds[idx]
utci_K, utci_C = _calculate_utci_from_met(Ta_C, Td_C, Va)
result['wind_speed_10m'] = Va
```

A median wind speed of ~12 km/h was being interpreted as ~12 m/s (≈ 43 km/h, Beaufort 6 — strong breeze), which produces unrealistically large wind chill and depresses UTCI values substantially.

---

## Fix

Divide by 3.6 before passing to `_calculate_utci_from_met` and before storing:

```python
# AFTER (fixed) — convert km/h → m/s
Va_ms = winds[idx] / 3.6
utci_K, utci_C = _calculate_utci_from_met(Ta_C, Td_C, Va_ms)
result['wind_speed_10m'] = Va_ms
```

---

## Impact on UTCI Values (State College, PA)

| Metric | Before fix | After fix |
|---|---|---|
| Median UTCI | −4.6 °C | +8.6 °C |
| Minimum UTCI | −56.6 °C | −44.3 °C |
| Median wind speed stored | ~12.3 m/s | ~3.4 m/s |

The remaining minimum of −44.3 °C corresponds to February 2015 data with air temperatures around −20 °C, which is physically plausible for central Pennsylvania in winter.

---

## Cache Handling

ERA5 data is cached to disk via `diskcache` in `cache/era5_cache/`. The cache stores the raw API hourly dictionaries (with wind speed still in km/h). No cache invalidation was needed: the unit conversion happens at read time in the code, so existing cached responses automatically produce correct UTCI values after the fix.

---

## Affected Outputs

All downstream UTCI-based outputs were regenerated after the fix:

- `data/state-college/state-college_svi_with_utci.csv` — deleted and recomputed
- `outputs/plots/state_college/shade_by_season/` — all seasonal GLM plots
- `outputs/plots/state_college/shade_by_year/` — all yearly GLM plots
- `outputs/plots/state_college/photo_counts/` — UTCI photo count histograms
- `outputs/plots/state_college/maps/` — all shade preference and UTCI maps

Any other cities processed using `enhanced_utci.py` will also benefit from the fix on their next rerun (their cached ERA5 data remains valid; only the conversion was wrong).
