# Adjusting Shade Ratio Analysis for Walking Sensitivity to Temperature

## The Problem

Current shade ratio analysis (in `scripts/visualization/visualize_shade_ratios.py`) shows:

**p(in shade | person visible, sunny, temp)** = inshade_count / (inshade_count + outshade_count)

This is conditional on:
1. A person being outside and visible in a street view image
2. It being a sunny day

However, this doesn't account for **selection bias**: people are less likely to be outside at extreme temperatures. The metro survey analysis shows walking trip rates vary significantly with temperature:
- Cold (<0°C): 1.87 walk trips/person-day
- Mild (15-25°C): 2.08 walk trips/person-day
- Warm (>25°C): 2.16 walk trips/person-day

## What We Want to Estimate

**p(person outside in shade | temp)** = probability a randomly selected person is outside AND in shade at temperature T

This decomposes as:
- p(outside in shade | temp) = p(outside | temp) × p(shade | outside, temp)

Where:
- **p(outside | temp)** comes from metro survey walking trip rates
- **p(shade | outside, temp)** comes from current shade ratio analysis

## What's Needed

### 1. Walking Trip Rate Function

From `data/transit_surveys/processed/p_walk_given_temp_final.csv`, we have:

```python
def get_walk_trip_rate(temp_C):
    """
    Get expected walk trips per person-day at temperature.

    Returns: λ(walk | temp) - expected number of walk trips per person per day
    """
    # Load from p_walk_given_temp_final.csv
    # Interpolate or use nearest temperature bin
    pass
```

This gives us a relative measure of p(outside | temp).

### 2. Normalize to Baseline

Since we want relative probabilities, normalize by a baseline temperature:

```python
baseline_temp = 20  # Reference temperature (comfortable)
baseline_rate = get_walk_trip_rate(baseline_temp)

def get_outside_probability_ratio(temp_C, baseline_temp=20):
    """
    Get p(outside | temp) / p(outside | baseline_temp).

    This gives relative likelihood of being outside at temp vs baseline.
    """
    return get_walk_trip_rate(temp_C) / get_walk_trip_rate(baseline_temp)
```

### 3. Adjust Shade Observations

For each street view image observation:

**Current**: Count people, calculate shade_percent = inshade / (inshade + outshade)

**Adjusted**: Weight each observation by walking sensitivity

```python
def calculate_adjusted_shade_percentage(df, temp_column='utci_C', baseline_temp=20):
    """
    Calculate shade percentage adjusted for temperature-dependent walking rates.
    """
    # Calculate current shade percentage (as before)
    df = calculate_shade_percentage(df, temp_column)

    # Get walking probability ratio for each row
    df['walk_rate'] = df[temp_column].apply(get_walk_trip_rate)
    baseline_rate = get_walk_trip_rate(baseline_temp)
    df['outside_prob_ratio'] = df['walk_rate'] / baseline_rate

    # Weight people counts by outside probability
    # Interpretation: "How many people WOULD be here if everyone was equally
    # likely to be outside as at baseline temperature?"
    df['adjusted_inshade'] = df['inshade_count'] / df['outside_prob_ratio']
    df['adjusted_outshade'] = df['outshade_count'] / df['outside_prob_ratio']
    df['adjusted_total'] = df['adjusted_inshade'] + df['adjusted_outshade']

    # Recalculate shade percentage with adjusted counts
    df['adjusted_shade_percent'] = (df['adjusted_inshade'] / df['adjusted_total']) * 100

    return df
```

### 4. Alternative: Exposure-Weighted Analysis

Instead of adjusting individual observations, weight temperature bins by expected exposure:

```python
def create_exposure_weighted_shade_plot(city_data, temp_column, temp_label, output_file):
    """
    Create shade vs temp plot weighted by pedestrian exposure.
    """
    # For each temperature bin:
    #   - Calculate mean shade_percent (current approach)
    #   - Weight by walk_trip_rate (pedestrian exposure at that temp)

    for city_name, df in city_data.items():
        filtered_df = calculate_shade_percentage(df, temp_column)

        # Bin by temperature
        temp_bins = np.arange(-10, 50, 5)  # 5°C bins
        for i in range(len(temp_bins) - 1):
            mask = (filtered_df[temp_column] >= temp_bins[i]) & \
                   (filtered_df[temp_column] < temp_bins[i+1])

            if mask.sum() > 0:
                subset = filtered_df[mask]
                mean_temp = subset[temp_column].mean()
                mean_shade = subset['shade_percent'].mean()

                # Weight by walking exposure
                walk_rate = get_walk_trip_rate(mean_temp)

                # Plot with size/weight proportional to walk_rate
                plt.scatter(mean_temp, mean_shade, s=walk_rate*100, alpha=0.6)
```

## Key Decision: Which Adjustment?

Two approaches, each answering a different question:

### Approach 1: Adjust Observations (Inverse Probability Weighting)

**Question**: "What would the shade ratio be if people were equally likely to be outside at all temperatures?"

**Method**: Upweight observations at extreme temps where people avoid being outside

**Use case**: Estimating shade-seeking behavior independent of trip suppression

**Interpretation**: Pure behavioral preference for shade, controlling for temperature-dependent outdoor activity

### Approach 2: Weight by Exposure

**Question**: "What is the expected pedestrian exposure to shade vs sun, accounting for how much people are actually outside?"

**Method**: Weight each temperature's shade ratio by walking trip rate

**Use case**: Estimating actual population sun/shade exposure for health outcomes

**Interpretation**: Real-world exposure accounting for both trip suppression and shade-seeking

## Recommendation

**Use Approach 2 (Exposure Weighting)** if the goal is understanding actual pedestrian sun exposure for:
- Heat vulnerability analysis
- UV exposure estimation
- Infrastructure planning (where to add shade)

**Use Approach 1 (IPW Adjustment)** if the goal is understanding behavioral preference:
- Do people seek shade MORE at higher temps? (behavioral elasticity)
- How does shade availability affect mode choice?
- Isolating shade-seeking behavior from trip suppression

## Implementation Steps

1. Load walking trip rate data: `data/transit_surveys/processed/p_walk_given_temp_final.csv`

2. Create interpolation function for walk_trip_rate(temp)

3. Add to `visualize_shade_ratios.py`:
   - `get_walk_trip_rate(temp_C)` helper function
   - `calculate_adjusted_shade_percentage()` for Approach 1
   - `create_exposure_weighted_shade_plot()` for Approach 2

4. Generate both sets of plots for comparison:
   - Original (conditional on being outside)
   - IPW-adjusted (controlling for trip suppression)
   - Exposure-weighted (accounting for trip suppression)

5. Document which question each plot answers

## Assumptions

1. **Metro survey trip rates are representative**: Walking trip rates from metro surveys (1988-2007, US cities) apply to street view imagery cities (global, 2014-2023)

2. **Trip rate ≈ outdoor probability**: Walk trips per person-day is proportional to probability of being outdoors at that temperature

3. **Linear relationship**: The relationship between trip rate and outdoor visibility is approximately linear (doubling trip rate = doubling visible people)

4. **No interaction effects**: Temperature's effect on being outside is independent of its effect on shade-seeking behavior

5. **Steady-state**: Street view images capture typical pedestrian behavior at each temperature, not short-term responses to temperature changes

## Limitations

- Metro surveys are cross-sectional, not longitudinal (comparing different people at different temps, not same people)
- Geographic mismatch: US metro areas vs global street view cities
- Temporal mismatch: 1988-2007 surveys vs 2014-2023 imagery
- Weather confounding: Temperature correlates with other weather (precipitation, wind) that also affect outdoor activity
- Activity type: Metro surveys include ALL walk trips (errands, recreation, commute); street view might over-represent certain activities

## Related Files

- Walking trip rate data: `data/transit_surveys/processed/p_walk_given_temp_final.csv`
- Walking analysis: `scripts/travel_surveys/plot_p_walk_given_temp.py`
- Shade ratio analysis: `scripts/visualization/visualize_shade_ratios.py`
- IPW version (if exists): `scripts/visualization/visualize_shade_ratios_ipw.py`
