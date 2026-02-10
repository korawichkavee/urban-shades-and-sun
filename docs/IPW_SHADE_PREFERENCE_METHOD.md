# IPW Adjustment for Shade Preference Estimation

## What We're Estimating

The raw shade ratio from street view imagery measures:

> **p(in shade | person visible, sunny image, temperature T)**

This is conditioned on a person being outside and visible. But the probability of being outside is itself a function of temperature — people walk less in extreme heat or cold. This creates **selection bias**: at extreme temperatures, the pedestrians we observe are not a representative sample of the general population.

The IPW adjustment estimates what the shade ratio *would be* if the same population were equally likely to be outside at all temperatures — isolating shade-seeking as a behavioral preference independent of how much people go outside.

---

## The Adjustment

### Walk Trip Rate as Outdoor Probability

We use walk trips per person-day as a proxy for P(outside | temperature T):

```
λ(T) = walk trips per person-day at temperature T
```

From the travel survey data (described below), this function varies with temperature:

| UTCI range | Walk trips/person-day |
|---|---|
| Cold (< 0°C) | ~1.4 – 2.0 |
| Mild (15–25°C) | ~1.97 – 2.17 |
| Warm (25–40°C) | ~2.15 – 2.19 |
| Extreme heat (> 40°C) | drops sharply (survey sparsity) |

The overall mean across the dataset is **2.00 walk trips per person-day**.

### IPW Weight Calculation

For each street view image observation at temperature T:

```
ipw(T) = λ(baseline) / λ(T)
```

where `baseline = 20°C` (a mild, representative temperature). This:
- **Upweights** observations at temperatures where fewer people go outside (cold winters, extreme heat)
- **Downweights** observations at mild temperatures where pedestrian activity is highest

Weights are normalized to mean = 1 and capped at the 95th percentile to prevent extreme leverage from the temperature tails where survey data is sparse.

### Applying Weights to the GLM

We fit a **binomial logistic regression** with a quadratic UTCI term to model shade choice:

```
inshade_count ~ Binomial(n_total, p_shade(UTCI))
logit(p_shade) = β₀ + β₁·UTCI + β₂·UTCI²
```

For the IPW-adjusted model, each observation's effective count is scaled by its weight:

```
effective_weight = ipw(T) × n_total
```

This is passed as `freq_weights` to the binomial GLM. The fitted curve then represents shade preference as if outdoor activity were uniform across temperatures.

---

## Travel Survey Data

### Sources

Walk trip rates were derived from **25 US metropolitan travel surveys** spanning 1988–2007, processed via the flexible survey pipeline. The surveys included:

| Survey | Year |
|---|---|
| phoenix | 1988 |
| saint-louis | 1990 |
| seattle | 1989, 1990, 1992, 1994, 1996, 1997, 1999, 2000, 2002 |
| atlanta | 1991, 2001 |
| california (multi-city) | 1991 |
| los-angeles | 1991 |
| tucson | 1993, 2000 |
| cleveland | 1994 |
| oahu | 1995 |
| seattle | multiple years (see above) |
| colorado-north-front-range | 1998 |
| evansville | 2000 |
| minneapolis-st-paul | 2000 |
| saint-louis | 2002 |
| greater-triangle-nc | 2006 |
| columbia-sc | 2007 |

The dataset spans **19 years** (1988–2007) and covers a broad range of US climates.

### Scale

After filtering to temperature bins with ≥ 100 person-days and UTCI between −15°C and 40°C:

- **174,027** person-days
- **767,483** total trips
- **347,865** walk trips
- **2.00** walk trips per person-day overall

Walk rates were binned by UTCI in 5°C intervals, then linearly interpolated to produce a smooth function λ(T). Rates at extreme temperatures (> 40°C UTCI) drop sharply due to data sparsity and are clipped to a minimum of 0.1 to avoid infinite weights.

### UTCI Annotation

Survey trips do not have precise daily dates in all cases — NHTS data provides month-only resolution, and some metro surveys use approximate date fields. Trip coordinates are at zip code or county centroid resolution rather than exact trip endpoints. UTCI values were fetched from the **ERA5 reanalysis** via the Open-Meteo historical weather API.

---

## Street View Imagery Data

The IPW-adjusted shade preference plot draws on commute-hour Mapillary imagery from **13 US metro cities**:

| City | Sunny obs with people | Total people |
|---|---|---|
| anchorage | 858 | 1,067 |
| atlanta | 95 | 138 |
| boise | 3,665 | 5,368 |
| cleveland | 1,903 | 3,082 |
| columbia | 3,295 | 3,750 |
| denver | 9,277 | 13,026 |
| evansville | 1,403 | 1,804 |
| honolulu | 1,272 | 2,475 |
| louisville | 6,703 | 9,912 |
| minneapolis | 8,281 | 16,077 |
| salt-lake-city | 14,028 | 20,749 |
| st.-louis | 6,426 | 8,603 |
| tucson | 1,655 | 2,395 |

Images were filtered to commute hours (8–10 am and 4–6 pm local time) and classified as sunny by a ViT model. Shade counts were produced by a YOLO object detector. UTCI was fetched from ERA5 for each image's lat/lon and capture timestamp, deduplicated by date × hour × 0.01° grid cell.

---

## Limitations and Assumptions

### Temporal mismatch
Travel surveys are from **1988–2007**; street view images are from **2014–2023**. Walking behavior and infrastructure have changed in that period. We assume the *relative* effect of temperature on outdoor activity (the shape of λ(T)) is stable over time, even if absolute rates differ.

### Geographic mismatch
The surveys cover US metro areas. The SVI cities overlap partially (atlanta, cleveland, columbia, evansville, minneapolis, st.-louis, tucson) but not fully (anchorage, boise, denver, honolulu, louisville, salt-lake-city have no matching survey). We assume the temperature-walk rate relationship generalizes across US cities.

### Coordinate resolution
Survey trip coordinates are at zip or county centroid level. UTCI values therefore represent area-level conditions rather than exact trip locations. For the purpose of computing walk rates by temperature bin, this is a minor source of noise.

### Walk trips ≈ outdoor probability
We treat walk trips per person-day as a proxy for the probability of being outdoors. This conflates multiple mechanisms: trip suppression (people make fewer trips), mode substitution (people drive instead of walk), and activity avoidance (people skip outings entirely). All three reduce the chance of a pedestrian being visible in street view, so the proxy is directionally correct.

### Independence assumption
We assume temperature's effect on being outside is independent of its effect on shade-seeking behavior. This may not hold — e.g. at very high temperatures, the people who *do* go outside may be systematically more heat-adapted and less likely to seek shade, which would cause the IPW-adjusted curve to understate shade preference at extreme heat.

### No interaction with time of day
The current implementation applies temperature-only IPW weights. The imagery is pre-filtered to commute hours (8–10 am, 4–6 pm), so time-of-day variation in outdoor activity is partially controlled by design. A more complete model would interact temperature and time of day.

---

## Interpretation

The two fitted curves in the output plot answer different questions:

| Curve | Question answered |
|---|---|
| **Unweighted** | Among pedestrians visible in sunny commute-hour images, what fraction chose shade at temperature T? |
| **IPW-adjusted** | What fraction *would* choose shade at temperature T if the same population were equally likely to be outside at all temperatures? |

If the IPW curve lies **above** the unweighted curve at extreme temperatures, it means people who brave extreme conditions are less likely to seek shade than the general population would be — i.e. the observed shade ratio understates the behavioral preference for shade at those temperatures.

---

## Related Files

| File | Purpose |
|---|---|
| `data/transit_surveys/processed/p_walk_given_temp_final.csv` | Walk trip rates by UTCI bin |
| `scripts/travel_surveys/plot_p_walk_given_temp.py` | Walk rate visualization |
| `scripts/processing/add_utci_to_metro_svi.py` | Adds UTCI to analyzed SVI CSVs |
| `scripts/visualization/visualize_metro_svi_shade_ipw.py` | Produces IPW shade preference plot |
| `data/metro_commute_svi_with_utci/` | Per-city SVI data with UTCI |
| `outputs/plots/metro_commute_ipw/metro_shade_ipw_vs_utci.png` | Output plot |
