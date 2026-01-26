# ABOUTME: Alternative visualization methods for shade preference vs UTCI.
# ABOUTME: Uses logistic regression and LOESS on aggregated data instead of GAM.

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import statsmodels.api as sm
from statsmodels.nonparametric.smoothers_lowess import lowess
from pathlib import Path


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


def prepare_data(df):
    """Prepare data for modeling."""
    df['total_people'] = df['inshade_count'].fillna(0) + df['outshade_count'].fillna(0)

    mask = (df['is_sunny'] == True) & \
           (df['inshade_count'].notna()) & \
           (df['outshade_count'].notna()) & \
           (df['total_people'] > 0) & \
           (df['utci_C'].notna())

    filtered_df = df[mask].copy()
    filtered_df['shade_ratio'] = filtered_df['inshade_count'] / filtered_df['total_people']

    return filtered_df


def fit_logistic_quadratic(x, n_success, n_total):
    """Fit binomial logistic regression with quadratic term.

    The binomial family automatically weights by n_total (number of trials).
    Each observation contributes based on how many people were in that image.

    Returns fitted model.
    """
    # Create design matrix with intercept, linear, and quadratic terms
    X = np.column_stack([np.ones(len(x)), x, x**2])

    # Binomial response: [n_successes, n_failures]
    # GLM with binomial family automatically weights by total trials
    n_failures = n_total - n_success
    y = np.column_stack([n_success, n_failures])

    # Fit GLM with binomial family (inherently weighted by n_total)
    model = sm.GLM(y, X, family=sm.families.Binomial())
    results = model.fit()

    return results


def predict_with_ci(results, x_pred, alpha=0.05):
    """Get predictions and CIs from logistic model."""
    X_pred = np.column_stack([np.ones(len(x_pred)), x_pred, x_pred**2])

    predictions = results.get_prediction(X_pred)
    pred_summary = predictions.summary_frame(alpha=alpha)

    return pred_summary['mean'].values, pred_summary['mean_ci_lower'].values, pred_summary['mean_ci_upper'].values


def aggregate_by_temperature(x, n_success, n_total):
    """Aggregate observations by unique temperature values.

    Returns unique x values, aggregated ratios, and weights (total people).
    """
    unique_x = np.unique(x)
    agg_ratio = []
    agg_weights = []

    for ux in unique_x:
        mask = x == ux
        ratio = n_success[mask].sum() / n_total[mask].sum()
        weight = n_total[mask].sum()
        agg_ratio.append(ratio)
        agg_weights.append(weight)

    return unique_x, np.array(agg_ratio), np.array(agg_weights)


def create_plots_with_methods(df, output_dir):
    """Create plots using multiple methods."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    df_filtered = prepare_data(df)

    # Add season information
    df_filtered['month'] = pd.to_datetime(df_filtered['datetime_local'], format='ISO8601').dt.month
    df_filtered['season'] = df_filtered['month'].apply(get_season)

    print(f"Total observations: {len(df_filtered)}")
    print(f"Total people: {df_filtered['total_people'].sum():.0f}")
    print(f"Overall shade ratio: {df_filtered['inshade_count'].sum() / df_filtered['total_people'].sum():.3f}")

    # Season colors
    season_colors = {
        'Spring': '#2ecc71',
        'Summer': '#e74c3c',
        'Fall': '#e67e22',
        'Winter': '#3498db'
    }

    seasons = ['Spring', 'Summer', 'Fall', 'Winter']

    # Create seasonal plots
    for season in seasons:
        season_df = df_filtered[df_filtered['season'] == season]

        if len(season_df) < 20:
            print(f"\nSkipping {season} - insufficient data (n={len(season_df)})")
            continue

        print(f"\n{season}: {len(season_df)} observations")

        x = season_df['utci_C'].values
        n_success = season_df['inshade_count'].values
        n_total = season_df['total_people'].values
        y_ratio = season_df['shade_ratio'].values

        # Create single plot with binomial logistic regression
        fig, ax = plt.subplots(figsize=(12, 8))

        # Binomial Logistic Regression (weighted by number of people)
        try:
            logit_results = fit_logistic_quadratic(x, n_success, n_total)

            x_pred = np.linspace(x.min(), x.max(), 100)
            y_pred, ci_lower, ci_upper = predict_with_ci(logit_results, x_pred)

            # Scatter with point size proportional to number of people
            np.random.seed(42)
            y_jitter = y_ratio + np.random.normal(0, 0.01, size=len(y_ratio))
            y_jitter = np.clip(y_jitter, 0, 1)

            # Size points by number of people (with reasonable scaling)
            point_sizes = n_total * 10  # Scale factor for visibility
            ax.scatter(x, y_jitter, alpha=0.4, s=point_sizes, color=season_colors[season],
                      edgecolors='black', linewidth=0.5,
                      label=f'Observations (size ∝ people)')

            # CI and fit
            ax.fill_between(x_pred, ci_lower, ci_upper, alpha=0.2, color=season_colors[season],
                           label='95% CI')
            ax.plot(x_pred, y_pred, color=season_colors[season], linewidth=3,
                   label='Binomial Logistic (quadratic)')

            ax.set_xlabel('UTCI Temperature (°C)', fontsize=14)
            ax.set_ylabel('Shade Ratio', fontsize=14)
            ax.set_title(f'Shade-Seeking Behavior vs UTCI - {season} (Phoenix, AZ)\n' +
                        f'n={len(season_df)} observations, {n_total.sum():.0f} people total',
                        fontsize=16, fontweight='bold')
            ax.set_ylim(-0.05, 1.05)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=12, loc='best')

        except Exception as e:
            print(f"  Logistic regression failed: {e}")
            ax.text(0.5, 0.5, f'Failed: {str(e)}', ha='center', va='center', transform=ax.transAxes)

        plt.tight_layout()
        output_file = output_dir / f'phoenix_{season.lower()}_alternative_methods.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        print(f"  Saved: {output_file}")
        plt.close()

    # Create overall plot
    print(f"\nCreating overall plot...")
    create_overall_plot(df_filtered, season_colors, seasons, output_dir)


def create_overall_plot(df_filtered, season_colors, seasons, output_dir):
    """Create overall plot with all data."""
    fig, ax = plt.subplots(figsize=(14, 10))

    x_all = df_filtered['utci_C'].values
    n_success_all = df_filtered['inshade_count'].values
    n_total_all = df_filtered['total_people'].values
    y_ratio_all = df_filtered['shade_ratio'].values

    # Scatter by season with size proportional to number of people
    for season in seasons:
        season_df = df_filtered[df_filtered['season'] == season]
        if len(season_df) > 0:
            np.random.seed(42)
            y_jitter = season_df['shade_ratio'].values + np.random.normal(0, 0.01, size=len(season_df))
            y_jitter = np.clip(y_jitter, 0, 1)

            # Size by number of people
            point_sizes = season_df['total_people'].values * 5
            ax.scatter(season_df['utci_C'].values, y_jitter, alpha=0.3, s=point_sizes,
                      color=season_colors[season], edgecolors='black', linewidth=0.3,
                      label=f'{season} (n={len(season_df)})')

    # Binomial Logistic Regression (weighted by number of people)
    logit_results = fit_logistic_quadratic(x_all, n_success_all, n_total_all)
    x_pred = np.linspace(x_all.min(), x_all.max(), 200)
    y_pred, ci_lower, ci_upper = predict_with_ci(logit_results, x_pred)

    ax.fill_between(x_pred, ci_lower, ci_upper, alpha=0.2, color='black',
                   label='95% CI')
    ax.plot(x_pred, y_pred, color='black', linewidth=4,
           label='Binomial Logistic (quadratic)', linestyle='-', zorder=10)

    ax.set_xlabel('UTCI Temperature (°C)', fontsize=14)
    ax.set_ylabel('Shade Ratio', fontsize=14)
    ax.set_title('Shade-Seeking Behavior vs UTCI - All Seasons (Phoenix, AZ)\n' +
                f'n={len(df_filtered)} observations, {n_total_all.sum():.0f} people (point size ∝ people)',
                fontsize=16, fontweight='bold')
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=11, loc='best', ncol=2)

    plt.tight_layout()
    output_file = output_dir / 'phoenix_overall_alternative_methods.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"  Saved: {output_file}")
    plt.close()


def main():
    print("="*60)
    print("Phoenix UTCI Shade Analysis - Alternative Methods")
    print("="*60)

    input_file = Path("Phoenix_1840020568_with_utci.csv")
    if not input_file.exists():
        print(f"ERROR: {input_file} not found")
        return

    print(f"\nLoading {input_file}...")
    df = pd.read_csv(input_file)

    output_dir = Path("outputs/plots/phoenix_seasonal")
    create_plots_with_methods(df, output_dir)

    print("\n" + "="*60)
    print("Complete!")
    print("="*60)


if __name__ == "__main__":
    main()
