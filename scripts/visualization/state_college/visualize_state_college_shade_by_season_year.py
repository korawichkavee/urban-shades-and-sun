# ABOUTME: Plots UTCI vs shade ratio for State College, PA by season and by year.
# ABOUTME: Uses binomial GLM with quadratic UTCI term; generates individual and combined plots.

from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import statsmodels.api as sm


INPUT_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_utci.csv'
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / 'outputs' / 'plots' / 'state_college'

SEASON_COLORS = {
    'Winter': '#3498db',
    'Spring': '#2ecc71',
    'Summer': '#e74c3c',
    'Fall':   '#f39c12',
}

SEASON_ORDER = ['Spring', 'Summer', 'Fall', 'Winter']

YEAR_PALETTE = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
    '#9467bd', '#8c564b', '#e377c2', '#7f7f7f',
]

MIN_OBS = 20


def get_season(month):
    """Map month number to season name (northern hemisphere)."""
    if month in [12, 1, 2]:
        return 'Winter'
    elif month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    elif month in [9, 10, 11]:
        return 'Fall'
    return None


def filter_for_shade(df):
    """Keep sunny rows with at least one person and valid UTCI."""
    df = df.copy()
    df['total_people'] = df['inshade_count'].fillna(0) + df['outshade_count'].fillna(0)
    mask = (
        (df['is_sunny'].astype(str).str.lower() == 'true') &
        df['inshade_count'].notna() &
        df['outshade_count'].notna() &
        (df['total_people'] > 0) &
        df['utci_C'].notna() &
        (df['utci_C'] >= -50) &
        (df['utci_C'] <= 60)
    )
    filtered = df[mask].copy()
    filtered['n_success'] = filtered['inshade_count'].astype(int)
    filtered['n_total'] = filtered['total_people'].astype(int)
    filtered['shade_ratio'] = filtered['n_success'] / filtered['n_total']
    return filtered


def fit_glm(x, n_success, n_total):
    """Fit binomial GLM with quadratic UTCI term.

    Returns fitted Results object, or None if fitting fails.
    """
    X = np.column_stack([np.ones(len(x)), x, x ** 2])
    n_failures = n_total - n_success
    y = np.column_stack([n_success, n_failures])
    try:
        return sm.GLM(y, X, family=sm.families.Binomial()).fit()
    except Exception as e:
        print(f'    Warning: GLM failed: {e}')
        return None


def predict_with_ci(results, x_pred, alpha=0.05):
    """Return predicted shade ratio and 95% CI over x_pred."""
    X_pred = np.column_stack([np.ones(len(x_pred)), x_pred, x_pred ** 2])
    pred = results.get_prediction(X_pred)
    s = pred.summary_frame(alpha=alpha)
    return s['mean'].values, s['mean_ci_lower'].values, s['mean_ci_upper'].values


def _apply_common_style(ax):
    ax.set_xlabel('UTCI Temperature (°C)', fontsize=14)
    ax.set_ylabel('Shade Ratio (fraction in shade)', fontsize=14)
    ax.set_ylim(-0.05, 1.05)
    ax.grid(True, alpha=0.3)


def _plot_glm_on_ax(ax, x, n_success, n_total, shade_ratio, color, label):
    """Scatter + GLM fit + 95% CI on a given axes. Returns True if fit succeeded."""
    np.random.seed(42)
    y_jitter = shade_ratio + np.random.normal(0, 0.01, len(shade_ratio))
    y_jitter = np.clip(y_jitter, 0, 1)
    ax.scatter(x, y_jitter, alpha=0.25, s=15, color=color)

    results = fit_glm(x, n_success, n_total)
    if results is None:
        return False

    x_lo, x_hi = np.percentile(x, 5), np.percentile(x, 95)
    x_range = np.linspace(x_lo, x_hi, 300)
    y_pred, ci_lo, ci_hi = predict_with_ci(results, x_range)

    ax.fill_between(x_range, ci_lo, ci_hi, color=color, alpha=0.2)
    ax.plot(x_range, y_pred, color=color, linewidth=3, label=label)
    return True


# ── Seasonal plots ─────────────────────────────────────────────────────────────

def plot_seasons_individual(df, out_dir):
    """One plot per season."""
    out_dir.mkdir(parents=True, exist_ok=True)
    for season in SEASON_ORDER:
        sdf = df[df['season'] == season]
        if len(sdf) < MIN_OBS:
            print(f'  Skipping {season} — insufficient data (n={len(sdf)})')
            continue

        fig, ax = plt.subplots(figsize=(12, 8))
        color = SEASON_COLORS[season]
        x = sdf['utci_C'].values

        ok = _plot_glm_on_ax(ax, x, sdf['n_success'].values, sdf['n_total'].values,
                              sdf['shade_ratio'].values, color,
                              f'GLM fit (95% CI)  n={len(sdf)}')

        _apply_common_style(ax)
        ax.set_title(
            f'Shade-Seeking Behavior vs UTCI — {season}\nState College, PA  (n={len(sdf)})',
            fontsize=16, fontweight='bold',
        )
        if ok:
            ax.legend(fontsize=12)
        plt.tight_layout()
        path = out_dir / f'state_college_{season.lower()}_utci_shade.png'
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f'  Saved: {path}')


def plot_seasons_combined(df, out_dir):
    """All seasons on one plot plus overall GLM fit."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(14, 10))

    for season in SEASON_ORDER:
        sdf = df[df['season'] == season]
        if len(sdf) < MIN_OBS:
            continue
        color = SEASON_COLORS[season]
        _plot_glm_on_ax(ax, sdf['utci_C'].values, sdf['n_success'].values,
                         sdf['n_total'].values, sdf['shade_ratio'].values,
                         color, f'{season} (n={len(sdf)})')

    # Overall GLM in black
    x_all = df['utci_C'].values
    results_all = fit_glm(x_all, df['n_success'].values, df['n_total'].values)
    if results_all is not None:
        x_lo, x_hi = np.percentile(x_all, 5), np.percentile(x_all, 95)
        x_range = np.linspace(x_lo, x_hi, 300)
        y_pred, ci_lo, ci_hi = predict_with_ci(results_all, x_range)
        ax.fill_between(x_range, ci_lo, ci_hi, color='black', alpha=0.15)
        ax.plot(x_range, y_pred, color='black', linewidth=4, linestyle='--',
                alpha=0.8, label=f'Overall (n={len(df)})')

    _apply_common_style(ax)
    ax.set_title(
        f'Shade-Seeking Behavior vs UTCI — All Seasons\nState College, PA  (n={len(df)})',
        fontsize=16, fontweight='bold',
    )
    ax.legend(fontsize=11, ncol=2)
    plt.tight_layout()
    path = out_dir / 'state_college_all_seasons_utci_shade.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path}')


# ── Yearly plots ───────────────────────────────────────────────────────────────

def plot_years_individual(df, out_dir):
    """One plot per year."""
    out_dir.mkdir(parents=True, exist_ok=True)
    years = sorted(df['year'].unique())
    for i, year in enumerate(years):
        ydf = df[df['year'] == year]
        if len(ydf) < MIN_OBS:
            print(f'  Skipping {year} — insufficient data (n={len(ydf)})')
            continue

        color = YEAR_PALETTE[i % len(YEAR_PALETTE)]
        fig, ax = plt.subplots(figsize=(12, 8))

        ok = _plot_glm_on_ax(ax, ydf['utci_C'].values, ydf['n_success'].values,
                              ydf['n_total'].values, ydf['shade_ratio'].values,
                              color, f'GLM fit (95% CI)  n={len(ydf)}')

        _apply_common_style(ax)
        ax.set_title(
            f'Shade-Seeking Behavior vs UTCI — {year}\nState College, PA  (n={len(ydf)})',
            fontsize=16, fontweight='bold',
        )
        if ok:
            ax.legend(fontsize=12)
        plt.tight_layout()
        path = out_dir / f'state_college_{year}_utci_shade.png'
        plt.savefig(path, dpi=300, bbox_inches='tight')
        plt.close()
        print(f'  Saved: {path}')


def plot_years_combined(df, out_dir):
    """All years on one plot plus overall GLM fit."""
    out_dir.mkdir(parents=True, exist_ok=True)
    years = sorted(df['year'].unique())

    fig, ax = plt.subplots(figsize=(14, 10))

    for i, year in enumerate(years):
        ydf = df[df['year'] == year]
        if len(ydf) < MIN_OBS:
            continue
        color = YEAR_PALETTE[i % len(YEAR_PALETTE)]
        _plot_glm_on_ax(ax, ydf['utci_C'].values, ydf['n_success'].values,
                         ydf['n_total'].values, ydf['shade_ratio'].values,
                         color, f'{year} (n={len(ydf)})')

    # Overall GLM in black
    x_all = df['utci_C'].values
    results_all = fit_glm(x_all, df['n_success'].values, df['n_total'].values)
    if results_all is not None:
        x_lo, x_hi = np.percentile(x_all, 5), np.percentile(x_all, 95)
        x_range = np.linspace(x_lo, x_hi, 300)
        y_pred, ci_lo, ci_hi = predict_with_ci(results_all, x_range)
        ax.fill_between(x_range, ci_lo, ci_hi, color='black', alpha=0.15)
        ax.plot(x_range, y_pred, color='black', linewidth=4, linestyle='--',
                alpha=0.8, label=f'Overall (n={len(df)})')

    _apply_common_style(ax)
    ax.set_title(
        f'Shade-Seeking Behavior vs UTCI — By Year\nState College, PA  (n={len(df)})',
        fontsize=16, fontweight='bold',
    )
    ax.legend(fontsize=11, ncol=2)
    plt.tight_layout()
    path = out_dir / 'state_college_all_years_utci_shade.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path}')


def main():
    print('=' * 60)
    print('State College — UTCI vs Shade Ratio (Season & Year)')
    print('=' * 60)

    if not INPUT_PATH.exists():
        print(f'ERROR: Input file not found: {INPUT_PATH}')
        print('Run scripts/processing/add_utci_to_state_college.py first.')
        return

    df = pd.read_csv(INPUT_PATH, low_memory=False)
    print(f'Loaded {len(df):,} rows')

    df = filter_for_shade(df)
    print(f'After filtering (sunny, with people, valid UTCI): {len(df):,} rows')

    if len(df) == 0:
        print('ERROR: No usable rows after filtering.')
        return

    df['captured_at'] = pd.to_datetime(df['captured_at'], format='mixed')
    df['month'] = df['captured_at'].dt.month
    df['year'] = df['captured_at'].dt.year
    df['season'] = df['month'].apply(get_season)

    print(f'UTCI range: {df["utci_C"].min():.1f}°C to {df["utci_C"].max():.1f}°C')
    print(f'Years: {sorted(df["year"].unique())}')
    print(f'Season counts:\n{df["season"].value_counts()}')

    season_dir = OUTPUT_DIR / 'shade_by_season'
    year_dir = OUTPUT_DIR / 'shade_by_year'

    print('\n-- Seasonal plots --')
    plot_seasons_individual(df, season_dir)
    plot_seasons_combined(df, season_dir)

    print('\n-- Yearly plots --')
    plot_years_individual(df, year_dir)
    plot_years_combined(df, year_dir)

    print('\nDone.')


if __name__ == '__main__':
    main()
