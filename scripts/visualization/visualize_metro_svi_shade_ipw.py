# ABOUTME: IPW-adjusted shade preference plot for metro commute SVI data.
# ABOUTME: Uses survey walk trip rates as IPW denominator to adjust for outdoor activity bias.

import argparse
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import statsmodels.api as sm
from scipy.interpolate import interp1d

warnings.filterwarnings('ignore')

WALK_RATE_CSV = 'data/transit_surveys/processed/p_walk_given_temp_final.csv'
BASELINE_TEMP = 20  # °C - reference temperature for IPW normalization


def load_walk_rate_func(walk_rate_csv):
    """
    Build an interpolation function for walk trips per person-day vs UTCI temperature.

    Uses the temp_bin midpoints and walk_trips_per_person_day column from the
    survey data. Returns a function: temp_C -> walk_rate.
    """
    df = pd.read_csv(walk_rate_csv)
    # Clip near-zero rates at the extremes to avoid infinite IPW weights.
    # Rates at 42.5°C+ drop sharply due to survey data sparsity, not real behavior.
    epsilon = 0.1
    df['walk_rate_safe'] = df['walk_trips_per_person_day'].clip(lower=epsilon)

    func = interp1d(
        df['temp_bin'].values,
        df['walk_rate_safe'].values,
        kind='linear',
        bounds_error=False,
        fill_value=(df['walk_rate_safe'].iloc[0], df['walk_rate_safe'].iloc[-1]),
    )
    return func


def compute_ipw_weights(utci_vals, walk_rate_func, baseline_temp=BASELINE_TEMP, cap_percentile=95):
    """
    Compute IPW weights from survey-derived outdoor probability.

    Weight = baseline_walk_rate / walk_rate(T)

    Observations at temperatures with low walk rates (extreme heat/cold) get
    upweighted to represent what shade choice would be if outdoor activity were
    uniform across temperatures.

    Weights are normalized to mean=1 and capped at cap_percentile to prevent
    extreme leverage.
    """
    baseline_rate = walk_rate_func(baseline_temp)
    walk_rates = walk_rate_func(utci_vals)

    weights = baseline_rate / walk_rates
    weights = weights / weights.mean()

    cap = np.percentile(weights, cap_percentile)
    weights = np.clip(weights, None, cap)

    return weights


def fit_logistic_quadratic(x, n_success, n_total, freq_weights=None):
    """Fit binomial GLM with quadratic UTCI term, optionally with frequency weights."""
    X = np.column_stack([np.ones(len(x)), x, x ** 2])
    n_failures = n_total - n_success
    y = np.column_stack([n_success, n_failures])

    kwargs = {}
    if freq_weights is not None:
        kwargs['freq_weights'] = freq_weights

    model = sm.GLM(y, X, family=sm.families.Binomial(), **kwargs)
    try:
        return model.fit()
    except Exception as e:
        print(f"    Warning: model fitting failed: {e}")
        return None


def predict_with_ci(results, x_pred, alpha=0.05):
    """Return predicted shade ratio and 95% CI over x_pred range."""
    X_pred = np.column_stack([np.ones(len(x_pred)), x_pred, x_pred ** 2])
    pred = results.get_prediction(X_pred)
    summary = pred.summary_frame(alpha=alpha)
    return (
        summary['mean'].values,
        summary['mean_ci_lower'].values,
        summary['mean_ci_upper'].values,
    )


def load_city_data(data_dir):
    """
    Load per-city *_svi_with_utci.csv files.

    Returns dict of city_name -> DataFrame filtered to sunny rows with people.
    """
    data_dir = Path(data_dir)
    city_data = {}

    csv_files = sorted(data_dir.glob('**/*_svi_with_utci.csv'))
    if not csv_files:
        print(f"No *_svi_with_utci.csv files found in {data_dir}")
        return city_data

    for csv_file in csv_files:
        city_name = csv_file.stem.replace('_svi_with_utci', '')
        df = pd.read_csv(csv_file, low_memory=False)

        if 'utci_C' not in df.columns:
            print(f"  Skipping {city_name}: no utci_C column")
            continue

        # Total people: person_count column may not exist in this pipeline output,
        # so build it from inshade + outshade (which are what the pipeline produces)
        df['total_people'] = df['inshade_count'].fillna(0) + df['outshade_count'].fillna(0)

        # Keep only sunny rows with at least one person
        is_sunny = df['is_sunny'].astype(str).str.lower() == 'true'
        df_sunny = df[is_sunny & (df['total_people'] > 0)].copy()

        if len(df_sunny) == 0:
            print(f"  Skipping {city_name}: no sunny rows with people")
            continue

        # UTCI validity filter
        df_sunny = df_sunny.dropna(subset=['utci_C'])
        df_sunny = df_sunny[(df_sunny['utci_C'] >= -50) & (df_sunny['utci_C'] <= 60)]

        df_sunny['n_success'] = df_sunny['inshade_count'].astype(int)
        df_sunny['n_total'] = df_sunny['total_people'].astype(int)
        df_sunny['shade_ratio'] = df_sunny['n_success'] / df_sunny['n_total']

        city_data[city_name] = df_sunny
        print(f"  {city_name}: {len(df_sunny):,} obs, {int(df_sunny['n_total'].sum()):,} people")

    return city_data


def plot_shade_ipw_per_city(city_data, walk_rate_func, output_dir, min_obs=50):
    """
    One plot per city: unweighted vs IPW-adjusted binomial logistic fit.

    X-axis is clipped to the city's p5–p95 UTCI range to focus on
    data-rich temperatures. Cities with fewer than min_obs observations
    are skipped.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for city_name, df in sorted(city_data.items()):
        if len(df) < min_obs:
            print(f"  Skipping {city_name}: only {len(df)} obs (< {min_obs})")
            continue

        x = df['utci_C'].values
        n_success = df['n_success'].values
        n_total = df['n_total'].values

        # Clip x-axis to data-rich range
        x_lo = np.percentile(x, 5)
        x_hi = np.percentile(x, 95)

        # Fit on full data, predict only within data-rich range
        ipw = compute_ipw_weights(x, walk_rate_func)

        print(f"  {city_name}: fitting models (n={len(df):,})...")
        results_uw = fit_logistic_quadratic(x, n_success, n_total)
        results_w = fit_logistic_quadratic(x, n_success, n_total,
                                           freq_weights=ipw * n_total)

        if results_uw is None or results_w is None:
            print(f"    Model fitting failed for {city_name}, skipping.")
            continue

        x_range = np.linspace(x_lo, x_hi, 300)
        y_uw, ci_lo_uw, ci_hi_uw = predict_with_ci(results_uw, x_range)
        y_w, ci_lo_w, ci_hi_w = predict_with_ci(results_w, x_range)

        fig, ax = plt.subplots(figsize=(10, 7))

        # Scatter (jitter y slightly for visibility)
        np.random.seed(42)
        y_jitter = df['shade_ratio'].values + np.random.normal(0, 0.01, len(df))
        y_jitter = np.clip(y_jitter, 0, 1)
        ax.scatter(x, y_jitter, alpha=0.2, s=12, color='gray', label='Observations')

        # Unweighted curve
        ax.fill_between(x_range, ci_lo_uw, ci_hi_uw, alpha=0.2, color='steelblue')
        ax.plot(x_range, y_uw, color='steelblue', linewidth=2.5,
                label='Unweighted', linestyle='--')

        # IPW-weighted curve
        ax.fill_between(x_range, ci_lo_w, ci_hi_w, alpha=0.2, color='firebrick')
        ax.plot(x_range, y_w, color='firebrick', linewidth=2.5,
                label='IPW-adjusted (survey walk rate)', linestyle='-')

        ax.set_xlabel('UTCI Temperature (°C)', fontsize=13)
        ax.set_ylabel('Shade Ratio (fraction of people in shade)', fontsize=13)
        ax.set_title(
            f'{city_name.replace("-", " ").title()} — Shade Preference vs UTCI\n'
            f'n={len(df):,} observations, {int(n_total.sum()):,} people  '
            f'(x-axis: p5–p95 = {x_lo:.0f}°C to {x_hi:.0f}°C)',
            fontsize=13, fontweight='bold',
        )
        ax.set_xlim(x_lo, x_hi)
        ax.set_ylim(-0.05, 1.05)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=11)

        plt.tight_layout()
        out = output_dir / f'{city_name}_shade_ipw.png'
        plt.savefig(out, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"    Saved: {out.name}")


def plot_shade_ipw(city_data, walk_rate_func, output_file):
    """
    Single-panel plot: unweighted vs IPW-adjusted binomial logistic fit.

    Combines all cities with equal city weighting (balanced sample), fits
    two GLM curves on the aggregated data, and overlays them.
    """
    # Aggregate across cities with equal city weighting:
    # sample the same number of observations from each city (min city size)
    min_size = min(len(df) for df in city_data.values())
    sample_size = min(min_size, 2000)  # cap per-city sample for speed

    np.random.seed(42)
    frames = []
    for city_name, df in city_data.items():
        sample = df.sample(n=sample_size, replace=(len(df) < sample_size))
        sample = sample.copy()
        sample['city'] = city_name
        frames.append(sample)

    combined = pd.concat(frames, ignore_index=True)

    x = combined['utci_C'].values
    n_success = combined['n_success'].values
    n_total = combined['n_total'].values

    # IPW weights from survey walk rates
    ipw = compute_ipw_weights(x, walk_rate_func)

    # Fit unweighted model
    print("  Fitting unweighted model...")
    results_unweighted = fit_logistic_quadratic(x, n_success, n_total)

    # Fit IPW-weighted model
    # Multiply freq_weights by n_total so the GLM sees effective person counts
    print("  Fitting IPW-weighted model...")
    results_weighted = fit_logistic_quadratic(x, n_success, n_total,
                                               freq_weights=ipw * n_total)

    if results_unweighted is None or results_weighted is None:
        print("  Model fitting failed, cannot produce plot.")
        return

    # Prediction range: p5–p95 of observed UTCI to focus on data-rich region
    x_range = np.linspace(np.percentile(x, 5), np.percentile(x, 95), 300)

    y_uw, ci_lo_uw, ci_hi_uw = predict_with_ci(results_unweighted, x_range)
    y_w, ci_lo_w, ci_hi_w = predict_with_ci(results_weighted, x_range)

    # --- Plot ---
    fig, ax = plt.subplots(figsize=(14, 9))

    # Scatter: one dot per observation, colored by city
    cities = sorted(combined['city'].unique())
    cmap = plt.cm.get_cmap('tab20', len(cities))
    for i, city in enumerate(cities):
        mask = combined['city'] == city
        ax.scatter(
            x[mask],
            combined['shade_ratio'].values[mask],
            alpha=0.15, s=10,
            color=cmap(i),
            label=city,
        )

    # Unweighted curve
    ax.fill_between(x_range, ci_lo_uw, ci_hi_uw, alpha=0.2, color='steelblue')
    ax.plot(x_range, y_uw, color='steelblue', linewidth=3,
            label='Unweighted fit', linestyle='--')

    # IPW-weighted curve
    ax.fill_between(x_range, ci_lo_w, ci_hi_w, alpha=0.2, color='firebrick')
    ax.plot(x_range, y_w, color='firebrick', linewidth=3,
            label='IPW-adjusted fit\n(survey walk rate)', linestyle='-')

    n_cities = len(city_data)
    n_obs = int(combined['n_total'].sum())

    ax.set_xlabel('UTCI Temperature (°C)', fontsize=14)
    ax.set_ylabel('Shade Ratio (fraction of people in shade)', fontsize=14)
    ax.set_title(
        f'Shade Preference vs UTCI Temperature — Metro Commute Cities\n'
        f'IPW adjustment uses survey-derived outdoor walk rate as P(outside | temp)\n'
        f'{n_cities} cities, {len(combined):,} observations, {n_obs:,} people total',
        fontsize=14, fontweight='bold',
    )
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)

    # Legend: curves first, then cities
    handles, labels = ax.get_legend_handles_labels()
    # Curves are last two added before city scatter — reorder so curves are first
    curve_handles = handles[-2:]
    curve_labels = labels[-2:]
    city_handles = handles[:-2]
    city_labels = labels[:-2]
    ax.legend(
        curve_handles + city_handles,
        curve_labels + city_labels,
        fontsize=9, loc='upper left', ncol=2,
    )

    plt.tight_layout()
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description='IPW-adjusted shade preference plots for metro commute SVI'
    )
    parser.add_argument('--data-dir', default='data/metro_commute_svi_with_utci',
                        help='Directory containing per-city *_svi_with_utci.csv files')
    parser.add_argument('--output-dir', default='outputs/plots/metro_commute_ipw',
                        help='Output directory for plots')
    parser.add_argument('--walk-rate-csv', default=WALK_RATE_CSV,
                        help='Path to p_walk_given_temp_final.csv')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print('=' * 60)
    print('METRO SVI SHADE PREFERENCE — IPW ADJUSTMENT')
    print('=' * 60)

    print('\nLoading walk rate function from survey data...')
    walk_rate_func = load_walk_rate_func(args.walk_rate_csv)
    baseline_rate = walk_rate_func(BASELINE_TEMP)
    print(f'  Baseline walk rate at {BASELINE_TEMP}°C: {baseline_rate:.3f} trips/person-day')

    print('\nLoading city SVI data...')
    city_data = load_city_data(args.data_dir)
    print(f'  Loaded {len(city_data)} cities')

    if not city_data:
        print('No city data found, exiting.')
        return

    print('\nFitting models and generating aggregate plot...')
    plot_shade_ipw(
        city_data,
        walk_rate_func,
        output_dir / 'metro_shade_ipw_vs_utci.png',
    )

    print('\nGenerating per-city plots...')
    plot_shade_ipw_per_city(
        city_data,
        walk_rate_func,
        output_dir / 'per_city',
    )

    print('\n' + '=' * 60)
    print('DONE')
    print(f'Output: {output_dir}')
    print('=' * 60)


if __name__ == '__main__':
    main()
