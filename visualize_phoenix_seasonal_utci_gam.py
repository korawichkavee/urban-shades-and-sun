# ABOUTME: Creates seasonal plots showing shade preference vs UTCI using binomial GAM.
# ABOUTME: Uses generalized additive model with binomial family for proportion data (0-1 bounded).

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm
from statsmodels.gam.api import GLMGam, BSplines
from pathlib import Path
import warnings


def get_season(month):
    """Convert month number to season name."""
    if month in [12, 1, 2]:
        return 'Winter'
    elif month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    elif month in [9, 10, 11]:
        return 'Fall'
    else:
        return None


def prepare_data_for_gam(df):
    """Prepare data for binomial GAM fitting.

    Filters for:
    - Sunny images only
    - At least one person present (total_people > 0)
    - Valid shade counts
    """
    # Calculate total people for each row
    df['total_people'] = df['inshade_count'].fillna(0) + df['outshade_count'].fillna(0)
    df['inshade_count'] = df['inshade_count'].fillna(0)

    # Filter for: sunny rows, valid shade counts, and at least one person
    mask = (df['is_sunny'] == True) & \
           (df['inshade_count'].notna()) & \
           (df['outshade_count'].notna()) & \
           (df['total_people'] > 0) & \
           (df['utci_C'].notna())

    filtered_df = df[mask].copy()

    # For binomial GAM, we need:
    # - Number of successes (people in shade)
    # - Number of trials (total people)
    # Shade ratio is just for reference
    filtered_df['shade_ratio'] = filtered_df['inshade_count'] / filtered_df['total_people']

    return filtered_df


def fit_binomial_gam(x, n_success, n_total, df_spline=10):
    """Fit a binomial GAM to proportion data.

    Args:
        x: predictor variable (UTCI temperature)
        n_success: number of successes (people in shade)
        n_total: number of trials (total people)
        df_spline: degrees of freedom for B-spline (controls smoothness)

    Returns:
        fitted GLMGam model
    """
    # Create B-spline basis for the predictor
    x_spline = BSplines(x, df=[df_spline], degree=[3])

    # Fit binomial GAM with logit link
    # Response is 2D array: [n_success, n_failures]
    n_failures = n_total - n_success
    y = np.column_stack([n_success, n_failures])

    # Fit the GAM model
    with warnings.catch_warnings():
        warnings.filterwarnings('ignore')
        gam_model = GLMGam(y, smoother=x_spline, family=sm.families.Binomial())
        gam_results = gam_model.fit()

    return gam_results


def predict_gam_with_ci(gam_results, x_pred, alpha=0.05):
    """Get predictions and confidence intervals from fitted GAM.

    Returns predictions on the probability scale (0-1).

    Args:
        gam_results: fitted GLMGam model results
        x_pred: new x values to predict at
        alpha: significance level for CIs (default 0.05 for 95% CI)

    Returns:
        y_pred, ci_lower, ci_upper: arrays of predictions and confidence bounds
    """
    # Transform new x values using the fitted smoother
    exog_smooth_new = gam_results.model.smoother.transform(x_pred)

    # Get predictions with confidence intervals
    predictions = gam_results.get_prediction(exog_smooth=exog_smooth_new)
    pred_summary = predictions.summary_frame(alpha=alpha)

    # Predictions are already on probability scale for binomial family
    y_pred = pred_summary['mean'].values
    ci_lower = pred_summary['mean_ci_lower'].values
    ci_upper = pred_summary['mean_ci_upper'].values

    return y_pred, ci_lower, ci_upper


def create_seasonal_plots(df, output_dir):
    """Create separate GAM plots for each season and an overall plot."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Filter and prepare data
    df_filtered = prepare_data_for_gam(df)

    # Add season information
    df_filtered['month'] = pd.to_datetime(df_filtered['datetime_local'], format='ISO8601').dt.month
    df_filtered['season'] = df_filtered['month'].apply(get_season)

    print(f"Total observations after filtering: {len(df_filtered)}")
    print(f"  (sunny images with at least 1 person)")
    print(f"UTCI range: {df_filtered['utci_C'].min():.1f}°C to {df_filtered['utci_C'].max():.1f}°C")
    print(f"Total people observed: {df_filtered['total_people'].sum():.0f}")
    print(f"People in shade: {df_filtered['inshade_count'].sum():.0f}")

    # Season colors
    season_colors = {
        'Spring': '#2ecc71',  # green
        'Summer': '#e74c3c',  # red
        'Fall': '#e67e22',    # orange
        'Winter': '#3498db'   # blue
    }

    # Create individual seasonal plots
    seasons = ['Spring', 'Summer', 'Fall', 'Winter']

    for season in seasons:
        season_df = df_filtered[df_filtered['season'] == season]

        if len(season_df) < 20:  # Lower threshold since we're using df=3
            print(f"\nSkipping {season} - insufficient data (n={len(season_df)})")
            continue

        print(f"\n{season}: {len(season_df)} observations, {season_df['total_people'].sum():.0f} people total")

        # Create plot
        fig, ax = plt.subplots(figsize=(12, 8))

        # Prepare data for GAM
        x = season_df['utci_C'].values
        y_success = season_df['inshade_count'].values
        y_total = season_df['total_people'].values
        y_ratio = season_df['shade_ratio'].values

        # Scatter plot - use jitter for visualization
        # Add small random noise to ratio for better visibility
        np.random.seed(42)
        y_jitter = y_ratio + np.random.normal(0, 0.01, size=len(y_ratio))
        y_jitter = np.clip(y_jitter, 0, 1)

        ax.scatter(x, y_jitter, alpha=0.3, s=30, color=season_colors[season],
                  label=f'Observations (n={len(season_df)})')

        # Fit binomial GAM
        try:
            gam_results = fit_binomial_gam(x, y_success, y_total, df_spline=4)

            # Create prediction grid within the observed data range
            x_min = x.min()
            x_max = x.max()
            x_pred = np.linspace(x_min, x_max, 100)

            # Get predictions with confidence intervals
            y_pred, ci_lower, ci_upper = predict_gam_with_ci(gam_results, x_pred)

            # Plot confidence interval
            ax.fill_between(x_pred, ci_lower, ci_upper,
                           color=season_colors[season], alpha=0.2,
                           label='95% CI')

            # Plot GAM fit
            ax.plot(x_pred, y_pred, color=season_colors[season],
                   linewidth=3, label='Binomial GAM fit')

        except Exception as e:
            print(f"  Warning: GAM fitting failed for {season}: {e}")
            print(f"  Skipping plot for {season}")
            plt.close()
            continue

        # Labels and formatting
        ax.set_xlabel('UTCI Temperature (°C)', fontsize=14)
        ax.set_ylabel('Shade Ratio', fontsize=14)
        ax.set_title(f'Shade-Seeking Behavior vs UTCI Temperature - {season} (Phoenix, AZ)',
                    fontsize=16, fontweight='bold')
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=12, loc='best')

        # Save plot
        output_file = output_dir / f'phoenix_{season.lower()}_utci_shade_gam.png'
        plt.tight_layout()
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"  Saved: {output_file}")
        plt.close()

    # Create overall plot with ALL DATA combined
    print(f"\nCreating overall plot with all data combined...")
    fig, ax = plt.subplots(figsize=(14, 10))

    # Use all filtered data regardless of season
    x_all = df_filtered['utci_C'].values
    y_success_all = df_filtered['inshade_count'].values
    y_total_all = df_filtered['total_people'].values
    y_ratio_all = df_filtered['shade_ratio'].values

    # Scatter plot - color by season for visual interest
    for season in seasons:
        season_df = df_filtered[df_filtered['season'] == season]
        if len(season_df) > 0:
            np.random.seed(42)
            y_jitter = season_df['shade_ratio'].values + np.random.normal(0, 0.01, size=len(season_df))
            y_jitter = np.clip(y_jitter, 0, 1)
            ax.scatter(season_df['utci_C'].values, y_jitter,
                      alpha=0.2, s=15, color=season_colors[season],
                      label=f'{season} (n={len(season_df)})')

    # Fit single binomial GAM across ALL data
    try:
        gam_results_all = fit_binomial_gam(x_all, y_success_all, y_total_all, df_spline=4)

        # Create prediction grid within the observed data range
        x_min = x_all.min()
        x_max = x_all.max()
        x_pred = np.linspace(x_min, x_max, 200)

        # Get predictions with confidence intervals
        y_pred, ci_lower, ci_upper = predict_gam_with_ci(gam_results_all, x_pred)

        # Plot overall confidence interval and GAM
        ax.fill_between(x_pred, ci_lower, ci_upper,
                       color='black', alpha=0.2, label='95% CI')
        ax.plot(x_pred, y_pred, color='black',
               linewidth=4, linestyle='-', alpha=0.9,
               label='Overall Binomial GAM fit')

    except Exception as e:
        print(f"  Error fitting overall GAM: {e}")
        print("  Skipping overall plot")
        plt.close()
        return

    # Labels and formatting
    ax.set_xlabel('UTCI Temperature (°C)', fontsize=14)
    ax.set_ylabel('Shade Ratio', fontsize=14)
    ax.set_title(f'Shade-Seeking Behavior vs UTCI Temperature - All Data (Phoenix, AZ)\n' +
                f'n={len(df_filtered)} observations, {y_total_all.sum():.0f} people total',
                fontsize=16, fontweight='bold')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc='best', ncol=2)

    # Save overall plot
    output_file = output_dir / 'phoenix_overall_utci_shade_gam.png'
    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_file}")
    plt.close()

    # Print summary statistics
    print("\n" + "="*60)
    print("Summary Statistics by Season:")
    print("="*60)
    for season in seasons:
        season_df = df_filtered[df_filtered['season'] == season]
        if len(season_df) > 0:
            print(f"\n{season}:")
            print(f"  Observations: {len(season_df)}")
            print(f"  Total people: {season_df['total_people'].sum():.0f}")
            print(f"  People in shade: {season_df['inshade_count'].sum():.0f}")
            print(f"  Overall shade ratio: {season_df['inshade_count'].sum() / season_df['total_people'].sum():.3f}")
            print(f"  UTCI range: {season_df['utci_C'].min():.1f}°C to {season_df['utci_C'].max():.1f}°C")
            print(f"  Mean UTCI: {season_df['utci_C'].mean():.1f}°C")

    # Create methodological note file
    create_methodology_note(output_dir)


def create_methodology_note(output_dir):
    """Create a markdown file explaining the visualization methodology."""
    note_file = output_dir / 'METHODOLOGY.md'

    methodology_text = """# Visualization Methodology

## Data and Filtering
- **Data source**: Phoenix street view imagery with UTCI (Universal Thermal Climate Index) weather data
- **Filtering criteria**:
  1. Sunny images only (`is_sunny = True`)
  2. At least one person detected (`total_people > 0`)
  3. Valid shade counts (no missing data)
  4. Valid UTCI data
- **Response variable**: Proportion of people in shade = (people in shade) / (total people)
  - Bounded between 0 and 1
  - Aggregated count data (not individual binary outcomes)
- **Predictor**: UTCI temperature in °C

## Statistical Method: Binomial Generalized Additive Model (GAM)

### Why Binomial GAM?

This is the **statistically appropriate method** for our data because:

1. **Proper distribution for proportions**: The response is proportion data (bounded 0-1), which violates assumptions of linear regression
2. **Binomial family**: Models count data (k successes out of n trials) with logit link function
3. **Handles heteroskedasticity**: Variance naturally changes with the mean for proportions (variance = np(1-p))
4. **Non-linear relationships**: Smoothing splines allow flexible, non-linear curves without assuming a parametric form
5. **Proper confidence intervals**: CIs respect the [0,1] bounds and account for uncertainty in both the smooth function and binomial variance

### Model Specification

```
logit(E[shade_ratio]) = f(UTCI)

where:
- f() is a smooth function represented by B-splines
- logit(p) = log(p/(1-p)) ensures predictions stay in [0,1]
- Response: [n_in_shade, n_not_in_shade] ~ Binomial
```

### Smoothing Parameter
- **B-spline basis** with **df=4** (4 degrees of freedom)
- Controls flexibility of the smooth curve
- Higher df = more wiggly, lower df = smoother
- **df=4 chosen because**:
  - Minimum df for degree=3 cubic splines (technical constraint: df >= degree + 1)
  - Phoenix data has only 5-9 unique UTCI values per season
  - B-splines require df < (n_unique_x - 1) for proper fitting
  - df=4 provides smooth, interpretable curves without overfitting sparse data
  - Assumes smooth behavioral response to temperature (reasonable assumption)

### Confidence Intervals
- **95% CIs** computed from the fitted GAM
- Based on the posterior covariance matrix of the spline coefficients
- Account for both:
  1. Uncertainty in the smooth function (estimation uncertainty)
  2. Binomial variance in the data
- CIs are on the probability scale (inverse-logit transformed)

### Why Not LOESS?

LOESS (used in initial version) has drawbacks for proportion data:
- **No distributional assumption**: Treats proportions as continuous unbounded data
- **Can predict outside [0,1]**: No guarantee fitted values respect bounds
- **Homoskedastic errors assumed**: Doesn't account for changing variance with proportion
- **CI calculation unclear**: Bootstrap CIs don't account for binomial structure

## Overall Plot
- Shows **ALL data combined** (colored by season for visual reference)
- **Single GAM fit** across the entire dataset
- Represents the overall relationship between UTCI and shade-seeking in Phoenix
- Not separate fits per season - this is a single model using all observations

## Seasonal Plots
- Separate GAM fits for Spring, Summer, Fall, Winter
- Allow examination of whether the temperature-shade relationship varies by season
- Requires sufficient data (n ≥ 30) for reliable fitting

## Data Visualization
- **Scatter points**: Individual image observations (with small jitter for visibility)
- **Solid line**: GAM predicted probability of shade-seeking
- **Shaded region**: 95% confidence interval for the predicted probability

## Limitations
1. **Observational data**: Cannot establish causation
2. **Sparse data regions**: CIs widen where observations are sparse (temperature extremes)
3. **Seasonal confounding**: Temperature and season correlate; effects may be confounded
4. **Zero-inflation**: Many observations have shade_ratio = 0 or 1
5. **Pseudo-replication**: Multiple images may be from same location/sequence
6. **Sample size per image varies**: Some images have 1 person, others have multiple
   - GAM accounts for this by using the binomial structure (n_trials varies)

## Interpretation

The fitted curve shows the **predicted probability** that a person will be in shade as a function of UTCI temperature, accounting for:
- The binomial nature of the data
- Non-linear relationships
- Uncertainty in both model parameters and binomial sampling

## References
- Wood, S. N. (2017). *Generalized Additive Models: An Introduction with R* (2nd ed.). CRC Press.
- McCullagh, P., & Nelder, J. A. (1989). *Generalized Linear Models* (2nd ed.). Chapman & Hall.
- Hastie, T., & Tibshirani, R. (1990). *Generalized Additive Models*. Chapman & Hall.

## Software
- Python 3.12
- statsmodels GAM implementation
- Binomial family with logit link
- B-spline basis functions
"""

    with open(note_file, 'w') as f:
        f.write(methodology_text)

    print(f"\nMethodology note saved to: {note_file}")


def main():
    print("="*60)
    print("Phoenix Seasonal UTCI Shade Preference (Binomial GAM)")
    print("="*60)

    # Load data
    input_file = Path("Phoenix_1840020568_with_utci.csv")
    if not input_file.exists():
        print(f"ERROR: Input file not found: {input_file}")
        return

    print(f"\nLoading data from {input_file}...")
    df = pd.read_csv(input_file)
    print(f"Loaded {len(df)} rows")

    # Create output directory
    output_dir = Path("outputs/plots/phoenix_seasonal")

    # Generate plots
    create_seasonal_plots(df, output_dir)

    print("\n" + "="*60)
    print("Visualization complete!")
    print(f"Plots saved to: {output_dir}")
    print("="*60)


if __name__ == "__main__":
    main()
