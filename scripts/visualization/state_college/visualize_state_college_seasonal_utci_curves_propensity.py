# ABOUTME: Seasonal shade preference vs UTCI curves - PROPENSITY SCORE WEIGHTED.
# ABOUTME: Triple IPW + inverse propensity score weighting for season assignment. Overall + per-season plots.
# ABOUTME: All estimates weighted by number of people in each image.
# ABOUTME: Uses average of left+right sidewalk shadow ratios and SR >= 0.10 threshold.

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import statsmodels.api as sm
from scipy.interpolate import interp1d
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[3]
DATA_PATH = ROOT / 'data/state-college/state-college_svi_with_shadow.csv'
WALK_RATE_CSV = ROOT / 'data/transit_surveys/processed/p_walk_given_temp_final.csv'
OUTPUT_DIR = ROOT / 'outputs/plots/state_college/seasonal_utci_curves_propensity'

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
SR_MIN = 0.10          # shadow-ratio filter threshold (sidewalk average)
TAU_M = 20.0           # DCWP decay constant (metres)
IPW_SR_CAP_Q = 0.95    # winsorise SR-IPW weights at this quantile
IPW_TEMP_CAP_Q = 0.95  # winsorise temp-IPW weights at this quantile
BASELINE_TEMP = 20.0   # °C reference for asymmetric temp-IPW

# Propensity score
WEIGHT_CAP_Q = 0.99    # Winsorize extreme weights at this quantile
MIN_PROPENSITY = 0.01  # Minimum propensity to avoid extreme weights

# Colour scheme for seasons
SEASON_COLORS = {
    'Overall': '#000000',
    'Winter': '#2E86AB',    # Blue
    'Spring': '#229954',    # Green
    'Summer': '#E05A2B',    # Orange-red
    'Fall': '#A23B72'       # Purple
}

# Season order
SEASONS = ['Winter', 'Spring', 'Summer', 'Fall']

# ---------------------------------------------------------------------------
# Walk-rate IPW helpers
# ---------------------------------------------------------------------------

def load_walk_rate_func(csv_path):
    """Linear interpolation of pooled walk trips per person-day vs UTCI (°C)."""
    df = pd.read_csv(csv_path)
    df['walk_rate_safe'] = df['walk_trips_per_person_day'].clip(lower=0.1)
    return interp1d(
        df['temp_bin'].values,
        df['walk_rate_safe'].values,
        kind='linear',
        bounds_error=False,
        fill_value=(df['walk_rate_safe'].iloc[0], df['walk_rate_safe'].iloc[-1]),
    )


def compute_temp_ipw(utci_c, walk_func, baseline=BASELINE_TEMP, cap_q=IPW_TEMP_CAP_Q):
    """Asymmetric temperature activity IPW."""
    baseline_rate = float(walk_func(baseline))
    rates = walk_func(utci_c)
    w = np.where(utci_c < baseline, rates / baseline_rate, baseline_rate / rates)
    w = w / w.mean()
    cap = np.percentile(w, cap_q * 100)
    return np.clip(w, None, cap)


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def get_season(month):
    """Map month to season."""
    if month in [12, 1, 2]:
        return 'Winter'
    elif month in [3, 4, 5]:
        return 'Spring'
    elif month in [6, 7, 8]:
        return 'Summer'
    else:
        return 'Fall'


def load_data():
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df['utci_C'] = df['utci_K'] - 273.15
    df['total_count'] = df['inshade_count'] + df['outshade_count']
    df = df[df['total_count'] > 0].copy()

    # Add datetime features
    df['datetime-local'] = pd.to_datetime(df['datetime-local'])
    df['month'] = df['datetime-local'].dt.month
    df['season'] = df['month'].apply(get_season)
    df['hour'] = df['datetime-local'].dt.hour
    df['day_of_week'] = df['datetime-local'].dt.dayofweek
    df['is_weekend'] = (df['day_of_week'] >= 5).astype(int)

    # Compute average pedestrian shadow ratio (left + right sidewalks)
    df['shadow_ratio_ped_avg'] = (df['shadow_ratio_ped_l'] + df['shadow_ratio_ped_r']) / 2.0

    return df


# ---------------------------------------------------------------------------
# Propensity score estimation
# ---------------------------------------------------------------------------

def compute_propensity_weights(df):
    """
    Estimate propensity score for season assignment using multinomial logistic regression.
    Returns inverse propensity weights: w = 1 / P(season = s | X)
    """
    print('\n--- Propensity Score Estimation ---')

    # Features that predict season assignment
    # (location, time of day, day of week, road type)
    feature_cols = ['lat', 'lon', 'hour', 'day_of_week', 'is_weekend']

    # One-hot encode highway type
    highway_dummies = pd.get_dummies(df['highway'], prefix='highway', drop_first=True)

    # Combine features
    X = pd.concat([df[feature_cols], highway_dummies], axis=1)

    # Handle missing values
    X = X.fillna(X.mean())

    # Standardize features for better numerical stability
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X)

    # Target: season (convert to numeric codes)
    season_mapping = {s: i for i, s in enumerate(SEASONS)}
    y = df['season'].map(season_mapping).values

    print(f'  Features: {list(X.columns)}')
    print(f'  Training multinomial logistic regression...')

    # Fit multinomial logistic regression
    model = LogisticRegression(
        multi_class='multinomial',
        solver='lbfgs',
        max_iter=1000,
        random_state=42
    )
    model.fit(X_scaled, y)

    # Predict propensity scores
    propensities = model.predict_proba(X_scaled)  # Shape: (n_samples, 4 seasons)

    # Extract propensity for observed season
    df['propensity_score'] = propensities[np.arange(len(df)), y]

    # Clip very low propensities to avoid extreme weights
    df['propensity_score'] = df['propensity_score'].clip(lower=MIN_PROPENSITY)

    # Inverse propensity weight
    df['w_propensity'] = 1.0 / df['propensity_score']

    # Report statistics by season
    print(f'\n  Propensity Score Statistics:')
    for season in SEASONS:
        season_mask = df['season'] == season
        ps = df.loc[season_mask, 'propensity_score']
        w = df.loc[season_mask, 'w_propensity']
        print(f'    {season}:')
        print(f'      Propensity: mean={ps.mean():.3f}, min={ps.min():.3f}, max={ps.max():.3f}')
        print(f'      IPW weight: mean={w.mean():.2f}, min={w.min():.2f}, max={w.max():.2f}')

    # Normalize weights within season (mean=1)
    for season in SEASONS:
        season_mask = df['season'] == season
        if season_mask.sum() > 0:
            mean_w = df.loc[season_mask, 'w_propensity'].mean()
            df.loc[season_mask, 'w_propensity'] /= mean_w

    # Assess covariate balance
    print(f'\n  Model Performance:')
    print(f'    Training accuracy: {model.score(X_scaled, y):.3f}')

    return df, model


def assess_covariate_balance(df, feature_cols=['lat', 'lon', 'hour']):
    """
    Assess covariate balance before and after propensity weighting.
    Compute standardized mean differences (SMD) across seasons.
    """
    print('\n--- Covariate Balance Assessment ---')

    results = []

    for feature in feature_cols:
        if feature not in df.columns:
            continue

        # Overall mean and std (target)
        overall_mean = df[feature].mean()
        overall_std = df[feature].std()

        # For each season, compute SMD before and after weighting
        for season in SEASONS:
            season_mask = df['season'] == season
            season_df = df[season_mask]

            if len(season_df) == 0:
                continue

            # Before weighting
            smd_before = (season_df[feature].mean() - overall_mean) / overall_std

            # After weighting
            w = season_df['w_propensity']
            weighted_mean = (season_df[feature] * w).sum() / w.sum()
            smd_after = (weighted_mean - overall_mean) / overall_std

            results.append({
                'Season': season,
                'Feature': feature,
                'SMD_before': smd_before,
                'SMD_after': smd_after,
                'Improvement': abs(smd_before) - abs(smd_after)
            })

    balance_df = pd.DataFrame(results)

    # Print summary
    print('\n  Standardized Mean Differences (|SMD| < 0.1 indicates good balance):')
    for season in SEASONS:
        season_balance = balance_df[balance_df['Season'] == season]
        if len(season_balance) == 0:
            continue
        avg_smd_before = season_balance['SMD_before'].abs().mean()
        avg_smd_after = season_balance['SMD_after'].abs().mean()
        print(f'    {season}: Avg |SMD| before={avg_smd_before:.3f}, after={avg_smd_after:.3f}')

    return balance_df


# ---------------------------------------------------------------------------
# Triple IPW dataset builder with propensity weighting
# ---------------------------------------------------------------------------

def make_triple_ipw_propensity(df, walk_func):
    """Build propensity-weighted triple IPW dataset."""
    # Filter to valid data
    d = df.dropna(subset=['utci_C', 'dist_to_shade_m', 'shadow_ratio_ped_avg']).copy()
    d = d[d['shadow_ratio_ped_avg'] >= SR_MIN].copy()

    if len(d) == 0:
        return d

    # SR-IPW weights
    sr_ipw = (1.0 / d['shadow_ratio_ped_avg'])
    cap = sr_ipw.quantile(IPW_SR_CAP_Q)
    d['sr_ipw'] = sr_ipw.clip(upper=cap)

    # DCWP effective counts
    a = np.exp(-d['dist_to_shade_m'] / TAU_M)
    d['eff_shade'] = d['inshade_count']
    d['eff_sun'] = d['outshade_count'] * a

    # Temperature IPW
    d['temp_ipw'] = compute_temp_ipw(d['utci_C'].values, walk_func)

    # Combined IPW (SR + DCWP + Temp)
    d['combined_ipw'] = d['sr_ipw'] * d['temp_ipw']

    # Add propensity weight
    d['w_final'] = d['combined_ipw'] * d['w_propensity']

    # Winsorize extreme weights
    cap_final = d['w_final'].quantile(WEIGHT_CAP_Q)
    d['w_final'] = d['w_final'].clip(upper=cap_final)

    # Normalize to mean=1 (for interpretability)
    d['w_final'] = d['w_final'] / d['w_final'].mean()

    return d


# ---------------------------------------------------------------------------
# GLM fitting
# ---------------------------------------------------------------------------

def fit_glm(x, y_success, y_fail, freq_weights=None, n_pred=300):
    """Fit quadratic binomial GLM; return (x_pred, y_pred, ci_lo, ci_hi)."""
    if len(x) < 20:
        return None

    X = np.column_stack([np.ones(len(x)), x, x ** 2])
    y = np.column_stack([y_success, y_fail])
    kw = {} if freq_weights is None else {'freq_weights': freq_weights}

    try:
        res = sm.GLM(y, X, family=sm.families.Binomial(), **kw).fit(disp=False)
    except Exception as e:
        print(f'    GLM failed: {e}')
        return None

    x_lo, x_hi = np.percentile(x, 5), np.percentile(x, 95)
    xp = np.linspace(x_lo, x_hi, n_pred)
    Xp = np.column_stack([np.ones(n_pred), xp, xp ** 2])
    sf = res.get_prediction(Xp).summary_frame(alpha=0.05)

    return xp, sf['mean'].values, sf['mean_ci_lower'].values, sf['mean_ci_upper'].values


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

def analyze_season(df, walk_func, season_name):
    """Analyze single season and return GLM fit."""
    print(f'\n{season_name}:')

    # Build propensity-weighted triple IPW dataset
    d = make_triple_ipw_propensity(df, walk_func)

    if len(d) == 0:
        print(f'  No valid data for {season_name}')
        return None

    n_svi = len(df[df['total_count'] > 0])
    n_people = df['total_count'].sum()

    # Effective sample size
    w = d['w_final'].values
    n_eff = (w.sum() ** 2) / (w ** 2).sum()

    print(f'  SVI images: {n_svi:,}')
    print(f'  Total people: {n_people:,.0f}')
    print(f'  Propensity-weighted sample: {len(d):,}')
    print(f'  Effective sample size: {n_eff:.1f}')
    if len(d) > 0:
        print(f'  UTCI range: {d["utci_C"].min():.1f}°C to {d["utci_C"].max():.1f}°C')
        print(f'  Weight range: [{d["w_final"].min():.2f}, {d["w_final"].max():.2f}]')

    # Fit GLM with propensity-weighted person-weighted estimates
    w_glm = d['w_final'].values * d['total_count'].values
    result = fit_glm(
        d['utci_C'].values,
        d['eff_shade'].values,
        d['eff_sun'].values,
        freq_weights=w_glm
    )

    if result is None:
        print(f'  GLM fit failed for {season_name}')
        return None

    return {
        'season': season_name,
        'n_svi': n_svi,
        'n_people': int(n_people),
        'n_sample': len(d),
        'n_eff': n_eff,
        'utci_min': d['utci_C'].min(),
        'utci_max': d['utci_C'].max(),
        'weight_min': d['w_final'].min(),
        'weight_max': d['w_final'].max(),
        'glm_result': result
    }


# ---------------------------------------------------------------------------
# Plotting
# ---------------------------------------------------------------------------

def plot_seasonal_curves(all_results, out_dir):
    """Create preference vs UTCI curves for all seasons."""
    out_dir.mkdir(parents=True, exist_ok=True)

    valid_results = [r for r in all_results if r is not None and r['glm_result'] is not None]

    if len(valid_results) == 0:
        print('No valid results to plot')
        return

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 7))

    # --- LEFT: All seasons together ---
    for result in valid_results:
        season = result['season']
        xp, yp, ci_lo, ci_hi = result['glm_result']

        color = SEASON_COLORS.get(season, '#000000')
        label = f'{season} (n_eff={result["n_eff"]:.0f})'

        ax1.plot(xp, yp, color=color, linewidth=2.5, label=label, alpha=0.9)
        ax1.fill_between(xp, ci_lo, ci_hi, color=color, alpha=0.15)

    ax1.set_xlabel('UTCI (°C)', fontsize=13, fontweight='bold')
    ax1.set_ylabel('Shade Preference', fontsize=13, fontweight='bold')
    ax1.set_title('Seasonal Shade Preference vs UTCI (Propensity Weighted)\n(Person-Weighted Triple IPW + Inverse Propensity Score)',
                  fontsize=14, fontweight='bold', pad=15)
    ax1.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='best', fontsize=11, framealpha=0.95)
    ax1.set_ylim(0, 1)
    ax1.axhline(0.5, color='gray', linestyle='--', linewidth=1, alpha=0.5, zorder=0)
    ax1.axvline(20, color='gray', linestyle='--', linewidth=1, alpha=0.5, zorder=0)

    # --- RIGHT: Individual season panels ---
    ax2.axis('off')
    season_results = [r for r in valid_results if r['season'] != 'Overall']
    n_seasons = len(season_results)

    if n_seasons > 0:
        from matplotlib.gridspec import GridSpec
        gs = GridSpec(2, 2, left=0.52, right=0.98, top=0.92, bottom=0.08,
                     hspace=0.35, wspace=0.3)

        for idx, result in enumerate(season_results):
            row = idx // 2
            col = idx % 2
            ax_sub = fig.add_subplot(gs[row, col])

            season = result['season']
            xp, yp, ci_lo, ci_hi = result['glm_result']
            color = SEASON_COLORS.get(season, '#000000')

            ax_sub.plot(xp, yp, color=color, linewidth=2.5, alpha=0.9)
            ax_sub.fill_between(xp, ci_lo, ci_hi, color=color, alpha=0.2)

            ax_sub.set_xlabel('UTCI (°C)', fontsize=10, fontweight='bold')
            ax_sub.set_ylabel('Shade Pref.', fontsize=10, fontweight='bold')
            ax_sub.set_title(f'{season}\n(n_eff={result["n_eff"]:.0f} | People={result["n_people"]:,})',
                           fontsize=11, fontweight='bold', color=color)
            ax_sub.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
            ax_sub.grid(True, alpha=0.3)
            ax_sub.set_ylim(0, 1)
            ax_sub.axhline(0.5, color='gray', linestyle='--', linewidth=0.8, alpha=0.4, zorder=0)
            ax_sub.axvline(20, color='gray', linestyle='--', linewidth=0.8, alpha=0.4, zorder=0)

    plt.suptitle('State College Seasonal Shade Preference (Propensity Score Weighted)\nInverse Propensity Score for Season Assignment | Sidewalk SR ≥ 0.10',
                 fontsize=16, fontweight='bold', y=0.98)

    output_path = out_dir / 'seasonal_utci_curves_propensity.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f'\nSaved propensity-weighted seasonal curves -> {output_path}')


def plot_overall_only(overall_result, out_dir):
    """Create standalone plot for overall preference curve."""
    if overall_result is None or overall_result['glm_result'] is None:
        print('No valid overall result to plot')
        return

    out_dir.mkdir(parents=True, exist_ok=True)

    fig, ax = plt.subplots(1, 1, figsize=(10, 7))

    xp, yp, ci_lo, ci_hi = overall_result['glm_result']

    ax.plot(xp, yp, color=SEASON_COLORS['Overall'], linewidth=3, label='Overall (Propensity Weighted)', alpha=0.9)
    ax.fill_between(xp, ci_lo, ci_hi, color=SEASON_COLORS['Overall'], alpha=0.2)

    ax.set_xlabel('UTCI (°C)', fontsize=14, fontweight='bold')
    ax.set_ylabel('Shade Preference', fontsize=14, fontweight='bold')
    ax.set_title(f'Overall Shade Preference vs UTCI (State College - Propensity Weighted)\n'
                f'Inverse Propensity Score for Season Assignment\n'
                f'(n_eff={overall_result["n_eff"]:.0f}, {overall_result["n_people"]:,} people)',
                fontsize=15, fontweight='bold', pad=20)
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
    ax.grid(True, alpha=0.3)
    ax.set_ylim(0, 1)

    ax.axhline(0.5, color='gray', linestyle='--', linewidth=1.5, alpha=0.5, zorder=0, label='50% preference')
    ax.axvline(20, color='red', linestyle='--', linewidth=1.5, alpha=0.5, zorder=0, label='20°C baseline')

    ax.legend(loc='best', fontsize=12, framealpha=0.95)

    output_path = out_dir / 'overall_utci_curve_propensity.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f'Saved propensity-weighted overall curve -> {output_path}')


def create_summary_table(all_results, out_dir):
    """Create summary table of results."""
    valid_results = [r for r in all_results if r is not None]

    if len(valid_results) == 0:
        print('No valid results for summary table')
        return

    rows = []
    for r in valid_results:
        rows.append({
            'Season': r['season'],
            'SVI Images': r['n_svi'],
            'Total People': r['n_people'],
            'Sample Size': r['n_sample'],
            'Eff. Sample Size': f'{r["n_eff"]:.1f}',
            'UTCI Min (°C)': f'{r["utci_min"]:.1f}',
            'UTCI Max (°C)': f'{r["utci_max"]:.1f}',
            'Weight Min': f'{r["weight_min"]:.2f}',
            'Weight Max': f'{r["weight_max"]:.2f}',
        })

    summary_df = pd.DataFrame(rows)
    summary_path = out_dir / 'seasonal_summary_propensity.csv'
    summary_df.to_csv(summary_path, index=False)
    print(f'\nSaved summary table -> {summary_path}')
    print('\n' + summary_df.to_string(index=False))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print('=' * 70)
    print('PROPENSITY SCORE WEIGHTED SEASONAL UTCI CURVES - STATE COLLEGE')
    print('Inverse Propensity Score for Season Assignment')
    print('=' * 70)

    # Load data
    print('\nLoading data...')
    df = load_data()
    walk_func = load_walk_rate_func(WALK_RATE_CSV)
    print(f'  Total images with people: {len(df):,}')
    print(f'  Total people: {df["total_count"].sum():,.0f}')

    # Compute propensity scores
    df, propensity_model = compute_propensity_weights(df)

    # Assess covariate balance
    balance_df = assess_covariate_balance(df)

    # Overall analysis
    print('\n' + '=' * 70)
    print('OVERALL (ALL SEASONS, PROPENSITY WEIGHTED)')
    print('=' * 70)
    overall_result = analyze_season(df, walk_func, 'Overall')

    # Seasonal analysis
    print('\n' + '=' * 70)
    print('BY SEASON (PROPENSITY WEIGHTED)')
    print('=' * 70)
    seasonal_results = []
    for season in SEASONS:
        season_df = df[df['season'] == season].copy()
        if len(season_df) > 0:
            result = analyze_season(season_df, walk_func, season)
            if result is not None:
                seasonal_results.append(result)

    # Create plots
    print('\n' + '=' * 70)
    print('CREATING PLOTS')
    print('=' * 70)

    all_results = [overall_result] + seasonal_results
    plot_seasonal_curves(all_results, OUTPUT_DIR)
    plot_overall_only(overall_result, OUTPUT_DIR)
    create_summary_table(all_results, OUTPUT_DIR)

    # Save covariate balance
    balance_path = OUTPUT_DIR / 'covariate_balance_propensity.csv'
    balance_df.to_csv(balance_path, index=False)
    print(f'\nSaved covariate balance table -> {balance_path}')

    print('\n' + '=' * 70)
    print('Done.')
    print('=' * 70)


if __name__ == '__main__':
    main()
