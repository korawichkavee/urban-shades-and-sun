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
PERSON_DAY_CSV = 'data/transit_surveys/processed/person_day_trip_rates.csv'
SURVEY_LOCATIONS_CSV = 'data/transit_surveys/processed/survey_locations.csv'
BASELINE_TEMP = 20  # °C - reference temperature for IPW normalization

# Maps SVI city names to survey metro_area values in survey_locations.csv.
# Cities not listed here have no matching survey and fall back to the pooled function.
CITY_TO_SURVEY_METRO = {
    'atlanta':        'atlanta',
    'cleveland':      'cleveland',
    'columbia':       'columbia-sc',
    'evansville':     'evansville',
    'minneapolis':    'minneapolis-st-paul',
    'st.-louis':      'saint-louis',
    'tucson':         'tucson',
    'honolulu':       'oahu',
    'denver':         'colorado-north-front-range',
}


def _build_walk_rate_func(df_person_days):
    """
    Build an interpolation function for walk trips per person-day vs UTCI temperature.

    Bins person-day rows into 5°C UTCI intervals, computes walk trips per person-day
    per bin, and returns a linear interpolation function: temp_C -> walk_rate.
    Only bins with >= 100 person-days are used; others are dropped before interpolation.
    """
    epsilon = 0.1

    df = df_person_days.copy()
    df = df.dropna(subset=['utci_C'])
    df = df[(df['utci_C'] >= -15) & (df['utci_C'] <= 40)]

    df['temp_bin'] = (np.floor(df['utci_C'] / 5) * 5 + 2.5).round(1)
    grouped = df.groupby('temp_bin').agg(
        walk_trips=('walk_only', 'sum'),
        n_person_days=('person_id', 'count'),
    ).reset_index()

    grouped = grouped[grouped['n_person_days'] >= 25].copy()
    if len(grouped) == 0:
        raise ValueError('no temperature bins with >= 25 person-days; survey too sparse')

    grouped['walk_trips_per_person_day'] = grouped['walk_trips'] / grouped['n_person_days']
    grouped['walk_rate_safe'] = grouped['walk_trips_per_person_day'].clip(lower=epsilon)

    func = interp1d(
        grouped['temp_bin'].values,
        grouped['walk_rate_safe'].values,
        kind='linear',
        bounds_error=False,
        fill_value=(grouped['walk_rate_safe'].iloc[0], grouped['walk_rate_safe'].iloc[-1]),
    )
    return func


def load_walk_rate_func(walk_rate_csv):
    """
    Build the pooled interpolation function for walk trips per person-day vs UTCI.

    Uses the pre-aggregated temp_bin summary CSV (all surveys combined).
    Returns a function: temp_C -> walk_rate.
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


def load_per_city_walk_rate_funcs(person_day_csv, survey_locations_csv):
    """
    Build per-metro-area walk rate interpolation functions from person-day trip data.

    Joins person_day_trip_rates.csv with survey_locations.csv on 'survey' to get
    metro_area, then aggregates and builds one interp function per metro_area.
    Returns a dict: metro_area -> (func, n_person_days).
    """
    df = pd.read_csv(person_day_csv)
    locs = pd.read_csv(survey_locations_csv)[['survey', 'metro_area']]
    df = df.merge(locs, on='survey', how='left')

    result = {}
    for metro_area, group in df.groupby('metro_area'):
        n = len(group)
        try:
            func = _build_walk_rate_func(group)
            result[metro_area] = (func, n)
        except Exception as e:
            print(f'  Warning: could not build walk rate func for {metro_area}: {e}')

    return result


def get_walk_rate_func(city_name, per_city_funcs, pooled_func):
    """
    Return the walk rate function for a city, falling back to pooled if unavailable.

    Uses CITY_TO_SURVEY_METRO to map SVI city names to survey metro areas.
    Returns (func, label) where label describes the source for plot annotation.
    """
    metro = CITY_TO_SURVEY_METRO.get(city_name)
    if metro and metro in per_city_funcs:
        func, n = per_city_funcs[metro]
        return func, f'IPW-adjusted ({metro} survey, n={n:,})'
    else:
        if metro:
            print(f'  Note: {city_name} maps to survey metro "{metro}" but no data found; using pooled')
        else:
            print(f'  Note: {city_name} has no matching survey; using pooled walk rate')
        return pooled_func, 'IPW-adjusted (pooled survey)'


def compute_ipw_weights(utci_vals, walk_rate_func, baseline_temp=BASELINE_TEMP, cap_percentile=95):
    """
    Compute asymmetric directional IPW weights from survey-derived outdoor probability.

    The thesis: people avoid going outside for different reasons at different temps.
    - Below baseline: people stay inside because it's cold. Those who do walk are
      less heat-sensitive, so observed shade preference overstates the population's
      preference. Weight < 1 (downweight shade ratio).
    - Above baseline: people stay inside because it's hot. Those who brave the heat
      may under-represent shade-seeking in the general population.
      Weight > 1 (upweight shade ratio).

    Asymmetric formulation (both branches equal 1.0 at baseline_temp):
      T < baseline:  weight = walk_rate(T) / baseline_rate   (< 1)
      T >= baseline: weight = baseline_rate / walk_rate(T)   (>= 1)

    Weights are normalized to mean=1 and capped at cap_percentile.
    """
    baseline_rate = float(walk_rate_func(baseline_temp))
    walk_rates = walk_rate_func(utci_vals)

    weights = np.where(
        utci_vals < baseline_temp,
        walk_rates / baseline_rate,
        baseline_rate / walk_rates,
    )

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

        # Assign time-of-day block from local hour
        df_sunny['_dt_local'] = pd.to_datetime(df_sunny['datetime-local'], errors='coerce')
        df_sunny['_hour_local'] = df_sunny['_dt_local'].dt.hour
        df_sunny['time_block'] = df_sunny['_hour_local'].apply(
            lambda h: 'Morning' if h in (8, 9) else ('Evening' if h in (16, 17) else 'Other')
        )

        city_data[city_name] = df_sunny
        n_morn = (df_sunny['time_block'] == 'Morning').sum()
        n_even = (df_sunny['time_block'] == 'Evening').sum()
        print(f"  {city_name}: {len(df_sunny):,} obs, {int(df_sunny['n_total'].sum()):,} people "
              f"(morning={n_morn:,}, evening={n_even:,})")

    return city_data


TOD_BLOCKS = ['Morning', 'Evening']
TOD_COLORS = {
    'Morning': '#e67e22',  # orange
    'Evening': '#8e44ad',  # purple
}
TOD_LABELS = {
    'Morning': 'Morning (8–10 am)',
    'Evening': 'Evening (4–6 pm)',
}

SEASON_MONTHS = {
    'Winter': [12, 1, 2],
    'Spring': [3, 4, 5],
    'Summer': [6, 7, 8],
    'Fall':   [9, 10, 11],
}

SEASON_COLORS = {
    'Winter': '#3498db',
    'Spring': '#2ecc71',
    'Summer': '#e74c3c',
    'Fall':   '#f39c12',
}


def assign_season(month):
    """Map month number to season name (northern hemisphere)."""
    for season, months in SEASON_MONTHS.items():
        if month in months:
            return season
    return 'Unknown'


def _plot_tod_panel(ax, df_block, walk_rate_func, tod, color, title_suffix='', ipw_label='IPW-adjusted'):
    """
    Fit and draw unweighted + IPW curves for a single time-of-day block onto ax.
    Returns False if fitting failed, True otherwise.
    """
    x = df_block['utci_C'].values
    n_success = df_block['n_success'].values
    n_total = df_block['n_total'].values

    x_lo = np.percentile(x, 5)
    x_hi = np.percentile(x, 95)

    ipw = compute_ipw_weights(x, walk_rate_func)

    results_uw = fit_logistic_quadratic(x, n_success, n_total)
    results_w = fit_logistic_quadratic(x, n_success, n_total,
                                       freq_weights=ipw * n_total)

    if results_uw is None or results_w is None:
        ax.set_title(f'{TOD_LABELS[tod]}{title_suffix}\n(model failed)', fontsize=11)
        return False

    x_range = np.linspace(x_lo, x_hi, 300)
    y_uw, ci_lo_uw, ci_hi_uw = predict_with_ci(results_uw, x_range)
    y_w, ci_lo_w, ci_hi_w = predict_with_ci(results_w, x_range)

    # Scatter
    np.random.seed(42)
    y_jitter = df_block['shade_ratio'].values + np.random.normal(0, 0.01, len(df_block))
    y_jitter = np.clip(y_jitter, 0, 1)
    ax.scatter(x, y_jitter, alpha=0.2, s=10, color='gray')

    # Unweighted
    ax.fill_between(x_range, ci_lo_uw, ci_hi_uw, alpha=0.15, color='steelblue')
    ax.plot(x_range, y_uw, color='steelblue', linewidth=2,
            linestyle='--', label='Unweighted')

    # IPW-weighted
    ax.fill_between(x_range, ci_lo_w, ci_hi_w, alpha=0.2, color=color)
    ax.plot(x_range, y_w, color=color, linewidth=2.5,
            linestyle='-', label=ipw_label)

    ax.set_title(
        f'{TOD_LABELS[tod]}{title_suffix}\nn={len(df_block):,}, {x_lo:.0f}–{x_hi:.0f}°C',
        fontsize=11, fontweight='bold', color=color,
    )
    ax.set_xlabel('UTCI Temperature (°C)', fontsize=11)
    ax.set_xlim(x_lo, x_hi)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9)
    return True


def plot_shade_ipw_per_city_tod(city_data, per_city_funcs, pooled_func, output_dir, min_obs=50):
    """
    One plot per city: Morning vs Evening columns, unweighted + IPW curves each.

    X-axis is clipped to each block's p5–p95. Blocks with fewer than min_obs
    observations are skipped.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for city_name, df in sorted(city_data.items()):
        blocks_present = [
            b for b in TOD_BLOCKS
            if (df['time_block'] == b).sum() >= min_obs
        ]

        if not blocks_present:
            print(f"  {city_name}: no time block with >= {min_obs} obs, skipping")
            continue

        walk_rate_func, ipw_label = get_walk_rate_func(city_name, per_city_funcs, pooled_func)

        n_blocks = len(blocks_present)
        fig, axes = plt.subplots(1, n_blocks, figsize=(8 * n_blocks, 7), sharey=True)
        if n_blocks == 1:
            axes = [axes]

        for ax, tod in zip(axes, blocks_present):
            df_block = df[df['time_block'] == tod]
            _plot_tod_panel(ax, df_block, walk_rate_func, tod, TOD_COLORS[tod],
                            ipw_label=ipw_label)

        axes[0].set_ylabel('Shade Ratio (fraction of people in shade)', fontsize=12)
        fig.suptitle(
            f'{city_name.replace("-", " ").title()} — Shade Preference by Time of Day',
            fontsize=14, fontweight='bold', y=1.02,
        )
        plt.tight_layout()
        out = output_dir / f'{city_name}_shade_ipw_tod.png'
        plt.savefig(out, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  {city_name}: saved {out.name} ({n_blocks} blocks)")


def plot_shade_ipw_per_city_season_tod(city_data, per_city_funcs, pooled_func, output_dir, min_obs=50):
    """
    One plot per city: rows = Morning / Evening, columns = seasons.

    Each cell shows unweighted + IPW curves. Cells with fewer than min_obs
    observations are skipped. Only seasons that have at least one qualifying
    time block are included.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for city_name, df in sorted(city_data.items()):
        df = df.copy()
        df['_dt'] = pd.to_datetime(df['datetime-local'], errors='coerce')
        df = df.dropna(subset=['_dt'])
        df['_month'] = df['_dt'].dt.month
        df['_season'] = df['_month'].apply(assign_season)

        # Determine which seasons have at least one qualifying time block
        seasons_present = []
        for season in SEASON_MONTHS:
            df_s = df[df['_season'] == season]
            for tod in TOD_BLOCKS:
                if (df_s['time_block'] == tod).sum() >= min_obs:
                    if season not in seasons_present:
                        seasons_present.append(season)
                    break

        if not seasons_present:
            print(f"  {city_name}: no (season × tod) cell with >= {min_obs} obs, skipping")
            continue

        walk_rate_func, ipw_label = get_walk_rate_func(city_name, per_city_funcs, pooled_func)

        # rows = time-of-day blocks, columns = seasons
        n_rows = len(TOD_BLOCKS)
        n_cols = len(seasons_present)
        fig, axes = plt.subplots(
            n_rows, n_cols,
            figsize=(7 * n_cols, 7 * n_rows),
            sharey=True,
            squeeze=False,
        )

        for row_idx, tod in enumerate(TOD_BLOCKS):
            for col_idx, season in enumerate(seasons_present):
                ax = axes[row_idx][col_idx]
                df_s = df[df['_season'] == season]
                df_cell = df_s[df_s['time_block'] == tod]
                season_color = SEASON_COLORS[season]

                if len(df_cell) < min_obs:
                    ax.text(0.5, 0.5, f'< {min_obs} obs', ha='center', va='center',
                            transform=ax.transAxes, fontsize=12, color='gray')
                    ax.set_title(f'{TOD_LABELS[tod]} · {season}', fontsize=11, color='gray')
                    ax.set_visible(True)
                    continue

                _plot_tod_panel(
                    ax, df_cell, walk_rate_func, tod, TOD_COLORS[tod],
                    ipw_label=ipw_label,
                )
                ax.set_title(
                    f'{TOD_LABELS[tod]} · {season}\nn={len(df_cell):,}',
                    fontsize=11, fontweight='bold',
                    color=season_color,
                )

            # Y-axis label on leftmost column of each row
            axes[row_idx][0].set_ylabel(
                'Shade Ratio (fraction in shade)', fontsize=11
            )

        # Indicate IPW source in subtitle so pooled vs per-city is visible on the plot
        ipw_source = ipw_label.split('(', 1)[1].rstrip(')') if '(' in ipw_label else ipw_label
        fig.suptitle(
            f'{city_name.replace("-", " ").title()} — Shade Preference by Season × Time of Day\n'
            f'IPW: {ipw_source}',
            fontsize=14, fontweight='bold',
        )
        plt.tight_layout()
        out = output_dir / f'{city_name}_shade_ipw_season_tod.png'
        plt.savefig(out, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  {city_name}: saved {out.name} ({n_rows} TOD × {n_cols} seasons)")


def plot_shade_ipw_per_city_season(city_data, per_city_funcs, pooled_func, output_dir, min_obs=50):
    """
    For each city, produce one plot per season with unweighted and IPW-adjusted curves.

    Each subplot shows shade ratio vs UTCI for that city-season combination.
    X-axis is clipped to the season's p5–p95 UTCI range. Seasons with fewer
    than min_obs observations are skipped.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    for city_name, df in sorted(city_data.items()):
        # Parse local datetime to get month/season
        df = df.copy()
        df['_dt'] = pd.to_datetime(df['datetime-local'], errors='coerce')
        df = df.dropna(subset=['_dt'])
        df['_month'] = df['_dt'].dt.month
        df['_season'] = df['_month'].apply(assign_season)

        seasons_present = [s for s in SEASON_MONTHS if (df['_season'] == s).sum() >= min_obs]

        if not seasons_present:
            print(f"  {city_name}: no season with >= {min_obs} obs, skipping seasonal plots")
            continue

        walk_rate_func, ipw_label = get_walk_rate_func(city_name, per_city_funcs, pooled_func)

        n_seasons = len(seasons_present)
        fig, axes = plt.subplots(1, n_seasons, figsize=(7 * n_seasons, 7), sharey=True)
        if n_seasons == 1:
            axes = [axes]

        for ax, season in zip(axes, seasons_present):
            df_s = df[df['_season'] == season]
            x = df_s['utci_C'].values
            n_success = df_s['n_success'].values
            n_total = df_s['n_total'].values
            color = SEASON_COLORS[season]

            x_lo = np.percentile(x, 5)
            x_hi = np.percentile(x, 95)

            ipw = compute_ipw_weights(x, walk_rate_func)

            results_uw = fit_logistic_quadratic(x, n_success, n_total)
            results_w = fit_logistic_quadratic(x, n_success, n_total,
                                               freq_weights=ipw * n_total)

            if results_uw is None or results_w is None:
                ax.set_title(f'{season}\n(model failed)', fontsize=12)
                continue

            x_range = np.linspace(x_lo, x_hi, 300)
            y_uw, ci_lo_uw, ci_hi_uw = predict_with_ci(results_uw, x_range)
            y_w, ci_lo_w, ci_hi_w = predict_with_ci(results_w, x_range)

            # Scatter
            np.random.seed(42)
            y_jitter = df_s['shade_ratio'].values + np.random.normal(0, 0.01, len(df_s))
            y_jitter = np.clip(y_jitter, 0, 1)
            ax.scatter(x, y_jitter, alpha=0.2, s=10, color='gray')

            # Unweighted
            ax.fill_between(x_range, ci_lo_uw, ci_hi_uw, alpha=0.15, color='steelblue')
            ax.plot(x_range, y_uw, color='steelblue', linewidth=2,
                    linestyle='--', label='Unweighted')

            # IPW-weighted
            ax.fill_between(x_range, ci_lo_w, ci_hi_w, alpha=0.2, color=color)
            ax.plot(x_range, y_w, color=color, linewidth=2.5,
                    linestyle='-', label=ipw_label)

            ax.set_title(f'{season}\nn={len(df_s):,}, {x_lo:.0f}–{x_hi:.0f}°C',
                         fontsize=12, fontweight='bold', color=color)
            ax.set_xlabel('UTCI Temperature (°C)', fontsize=11)
            ax.set_xlim(x_lo, x_hi)
            ax.set_ylim(-0.05, 1.05)
            ax.grid(True, alpha=0.3)
            ax.legend(fontsize=9)

        axes[0].set_ylabel('Shade Ratio (fraction of people in shade)', fontsize=12)
        fig.suptitle(
            f'{city_name.replace("-", " ").title()} — Shade Preference by Season',
            fontsize=14, fontweight='bold', y=1.02,
        )
        plt.tight_layout()
        out = output_dir / f'{city_name}_shade_ipw_seasonal.png'
        plt.savefig(out, dpi=300, bbox_inches='tight')
        plt.close()
        print(f"  {city_name}: saved {out.name} ({n_seasons} seasons)")


def plot_shade_ipw_per_city(city_data, per_city_funcs, pooled_func, output_dir, min_obs=50):
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

        walk_rate_func, ipw_label = get_walk_rate_func(city_name, per_city_funcs, pooled_func)
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
                label=ipw_label, linestyle='-')

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


def plot_ipw_weights(per_city_funcs, pooled_func, city_data, output_file):
    """
    Plot IPW weight vs UTCI for the pooled function and each matched city.

    Shows how much each city's adjustment differs from pooled and from 1.0
    (no adjustment). Cities that fall back to pooled are omitted — they would
    just duplicate the black pooled line. The observed UTCI range for each
    matched SVI city is marked with a shaded band so the reader can see
    where the weights are actually applied.
    """
    t = np.linspace(-15, 40, 400)

    fig, ax = plt.subplots(figsize=(13, 7))

    # Pooled line first (black dashed)
    w_pooled = compute_ipw_weights(t, pooled_func)
    ax.plot(t, w_pooled, color='black', linewidth=2.5, linestyle='--',
            label='Pooled (all surveys)', zorder=5)

    # Per-city lines, colored by city
    matched_cities = sorted(
        city for city in CITY_TO_SURVEY_METRO
        if CITY_TO_SURVEY_METRO[city] in per_city_funcs
    )
    cmap = plt.cm.get_cmap('tab10', len(matched_cities))

    for i, city_name in enumerate(matched_cities):
        metro = CITY_TO_SURVEY_METRO[city_name]
        func, n_person_days = per_city_funcs[metro]
        w = compute_ipw_weights(t, func)
        color = cmap(i)

        ax.plot(t, w, color=color, linewidth=2,
                label=f'{city_name} ({metro}, n={n_person_days:,})')

        # Shade the observed UTCI range for this city if SVI data is available
        if city_name in city_data:
            city_utci = city_data[city_name]['utci_C'].values
            x_lo = np.percentile(city_utci, 5)
            x_hi = np.percentile(city_utci, 95)
            ax.axvspan(x_lo, x_hi, alpha=0.06, color=color)

    ax.axhline(1.0, color='gray', linewidth=1, linestyle=':', zorder=1,
               label='Weight = 1 (no adjustment)')
    ax.axvline(BASELINE_TEMP, color='gray', linewidth=1, linestyle='--', zorder=1,
               label=f'Baseline temp ({BASELINE_TEMP}°C)')

    ax.set_xlabel('UTCI Temperature (°C)', fontsize=13)
    ax.set_ylabel('IPW Weight', fontsize=13)
    ax.set_title(
        'IPW Weights by Temperature — Per-City vs Pooled Survey\n'
        'Weight < 1: downweight (cold-temp selection bias correction); '
        'Weight > 1: upweight (hot-temp)\n'
        'Shaded bands show p5–p95 UTCI range of each city\'s SVI observations',
        fontsize=12, fontweight='bold',
    )
    ax.set_xlim(-15, 40)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9, loc='upper left')

    plt.tight_layout()
    Path(output_file).parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"  Saved: {output_file}")


def plot_shade_ipw(city_data, per_city_funcs, pooled_func, output_file):
    """
    Single-panel plot: unweighted vs IPW-adjusted binomial logistic fit.

    Combines all cities with equal city weighting (balanced sample), fits
    two GLM curves on the aggregated data, and overlays them. Each city's
    observations are weighted using that city's survey-derived walk rate
    function (falling back to the pooled function for unmatched cities).
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

    # Compute per-observation IPW weights using each city's own walk rate function
    ipw = np.empty(len(combined))
    for city_name, group_idx in combined.groupby('city').groups.items():
        walk_rate_func, _ = get_walk_rate_func(city_name, per_city_funcs, pooled_func)
        city_x = combined.loc[group_idx, 'utci_C'].values
        ipw[group_idx] = compute_ipw_weights(city_x, walk_rate_func)

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
            label='IPW-adjusted fit\n(per-city survey walk rate)', linestyle='-')

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
    parser.add_argument('--person-day-csv', default=PERSON_DAY_CSV,
                        help='Path to person_day_trip_rates.csv')
    parser.add_argument('--survey-locations-csv', default=SURVEY_LOCATIONS_CSV,
                        help='Path to survey_locations.csv')
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print('=' * 60)
    print('METRO SVI SHADE PREFERENCE — IPW ADJUSTMENT')
    print('=' * 60)

    print('\nLoading pooled walk rate function from survey data...')
    pooled_func = load_walk_rate_func(args.walk_rate_csv)
    baseline_rate = pooled_func(BASELINE_TEMP)
    print(f'  Baseline walk rate at {BASELINE_TEMP}°C: {baseline_rate:.3f} trips/person-day')

    print('\nBuilding per-city walk rate functions...')
    per_city_funcs = load_per_city_walk_rate_funcs(args.person_day_csv, args.survey_locations_csv)
    print(f'  Built functions for {len(per_city_funcs)} metro areas: {sorted(per_city_funcs)}')

    print('\nLoading city SVI data...')
    city_data = load_city_data(args.data_dir)
    print(f'  Loaded {len(city_data)} cities')

    if not city_data:
        print('No city data found, exiting.')
        return

    print('\nGenerating IPW weight diagnostic plot...')
    plot_ipw_weights(
        per_city_funcs,
        pooled_func,
        city_data,
        output_dir / 'ipw_weights_by_temp.png',
    )

    print('\nFitting models and generating aggregate plot...')
    plot_shade_ipw(
        city_data,
        per_city_funcs,
        pooled_func,
        output_dir / 'metro_shade_ipw_vs_utci.png',
    )

    print('\nGenerating per-city plots...')
    plot_shade_ipw_per_city(
        city_data,
        per_city_funcs,
        pooled_func,
        output_dir / 'per_city',
    )

    print('\nGenerating per-city time-of-day plots...')
    plot_shade_ipw_per_city_tod(
        city_data,
        per_city_funcs,
        pooled_func,
        output_dir / 'per_city_tod',
    )

    print('\nGenerating per-city seasonal plots...')
    plot_shade_ipw_per_city_season(
        city_data,
        per_city_funcs,
        pooled_func,
        output_dir / 'per_city_season',
    )

    print('\nGenerating per-city season × time-of-day plots...')
    plot_shade_ipw_per_city_season_tod(
        city_data,
        per_city_funcs,
        pooled_func,
        output_dir / 'per_city_season_tod',
    )

    print('\n' + '=' * 60)
    print('DONE')
    print(f'Output: {output_dir}')
    print('=' * 60)


if __name__ == '__main__':
    main()
