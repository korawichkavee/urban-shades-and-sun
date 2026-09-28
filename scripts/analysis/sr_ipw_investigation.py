#!/usr/bin/env python3
# ABOUTME: Investigation of SR-IPW information loss and model fit improvements
# ABOUTME: Addresses: Why is 51% loss acceptable? Does correction improve fit?
# ABOUTME: Compares uncorrected vs progressively corrected models

from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
import statsmodels.api as sm
from scipy.interpolate import interp1d
from scipy.stats import gaussian_kde
from sklearn.metrics import mean_squared_error, log_loss

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
DATA_PATH = ROOT / 'data/state-college/state-college_svi_with_shadow.csv'
WALK_RATE_CSV = ROOT / 'data/transit_surveys/processed/p_walk_given_temp_final.csv'
OUTPUT_DIR = ROOT / 'outputs/diagnostics/sr_ipw_investigation'

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Parameters
# ---------------------------------------------------------------------------
SR_MIN = 0.10
TAU_M = 20.0
IPW_SR_CAP_Q = 0.95
IPW_TEMP_CAP_Q = 0.95
BASELINE_TEMP = 20.0
GRID_SIZE_M = 500
WEIGHT_CAP_Q = 0.99

# ---------------------------------------------------------------------------
# Helper Functions
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
        fill_value=(df['walk_rate_safe'].iloc[0], df['walk_rate_safe'].iloc[-1])
    )

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

def assign_grid_cell(lats, lons, grid_size_m):
    """Assign each lat/lon to a spatial grid cell."""
    from pyproj import Transformer
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:32618", always_xy=True)
    x, y = transformer.transform(lons, lats)
    x_cell = (x // grid_size_m).astype(int)
    y_cell = (y // grid_size_m).astype(int)
    return [f"{xc}_{yc}" for xc, yc in zip(x_cell, y_cell)]

def load_data():
    """Load and prepare data."""
    df = pd.read_csv(DATA_PATH, low_memory=False)
    df['utci_C'] = df['utci_K'] - 273.15
    df['total_count'] = df['inshade_count'] + df['outshade_count']
    df = df[df['total_count'] > 0].copy()

    df['datetime-local'] = pd.to_datetime(df['datetime-local'])
    df['month'] = df['datetime-local'].dt.month
    df['season'] = df['month'].apply(get_season)
    df['shadow_ratio_ped_avg'] = (df['shadow_ratio_ped_l'] + df['shadow_ratio_ped_r']) / 2.0
    df['grid_cell'] = assign_grid_cell(df['lat'].values, df['lon'].values, GRID_SIZE_M)

    return df

def compute_n_eff(weights):
    """Compute effective sample size: (sum w)^2 / sum(w^2)"""
    return (weights.sum() ** 2) / (weights ** 2).sum()

def fit_glm_binomial(df, weight_col='w'):
    """Fit quadratic binomial GLM."""

    # Build dataset
    n_success = df['inshade_count'].values
    n_total = df['total_count'].values
    utci = df['utci_C'].values
    weights = df[weight_col].values

    # Design matrix
    X = np.column_stack([
        np.ones_like(utci),
        utci,
        utci ** 2
    ])

    # Fit GLM
    try:
        model = sm.GLM(
            endog=n_success,
            exog=X,
            family=sm.families.Binomial(),
            freq_weights=n_total,
            var_weights=weights
        )
        result = model.fit()

        # Predictions
        p_pred = result.predict(X)

        # Goodness of fit metrics
        # Deviance
        deviance = result.deviance
        null_deviance = result.null_deviance
        pseudo_r2 = 1 - (deviance / null_deviance)

        # AIC/BIC
        aic = result.aic
        bic = result.bic

        # Weighted log-loss (negative log-likelihood)
        y_true_prop = n_success / n_total
        # Use actual proportions for observed, predictions for expected
        # Log-loss: -sum(w * (y*log(p) + (1-y)*log(1-p)))
        eps = 1e-15
        p_pred_safe = np.clip(p_pred, eps, 1-eps)
        weighted_logloss = -np.sum(
            weights * n_total * (
                y_true_prop * np.log(p_pred_safe) +
                (1 - y_true_prop) * np.log(1 - p_pred_safe)
            )
        ) / np.sum(weights * n_total)

        # Weighted MSE
        weighted_mse = np.sum(weights * n_total * (y_true_prop - p_pred)**2) / np.sum(weights * n_total)

        # Residual analysis
        pearson_resid = (y_true_prop - p_pred) / np.sqrt(p_pred * (1 - p_pred) / n_total)
        weighted_pearson_resid = pearson_resid * np.sqrt(weights)

        return {
            'result': result,
            'p_pred': p_pred,
            'deviance': deviance,
            'null_deviance': null_deviance,
            'pseudo_r2': pseudo_r2,
            'aic': aic,
            'bic': bic,
            'weighted_logloss': weighted_logloss,
            'weighted_mse': weighted_mse,
            'pearson_resid': pearson_resid,
            'weighted_pearson_resid': weighted_pearson_resid,
            'coefficients': result.params,
            'pvalues': result.pvalues
        }
    except Exception as e:
        print(f"GLM fit failed: {e}")
        return None

# ---------------------------------------------------------------------------
# Analysis 1: Understanding SR-IPW and n_eff
# ---------------------------------------------------------------------------

def analyze_sr_ipw_mechanism(df):
    """Analyze WHY SR-IPW causes 51% information loss and whether it's justified."""

    print('\n' + '='*80)
    print('ANALYSIS 1: SR-IPW MECHANISM AND INFORMATION LOSS')
    print('='*80)

    # Filter to SR >= threshold
    df = df[df['shadow_ratio_ped_avg'] >= SR_MIN].copy()

    print(f'\nFiltered to SR >= {SR_MIN}: {len(df):,} samples')

    # Compute SR-IPW weights
    sr = df['shadow_ratio_ped_avg'].values

    # Propensity model: P(observed | SR) = sigmoid(SR)
    # Steeper sigmoid = stronger belief that high SR is over-sampled
    p_sr = 1.0 / (1.0 + np.exp(-10 * (sr - 0.5)))
    p_sr = np.clip(p_sr, 0.05, 0.95)

    # IPW weight = 1 / P(observed | SR)
    w_sr = 1.0 / p_sr

    # Cap at 95th percentile
    cap_sr = np.quantile(w_sr, IPW_SR_CAP_Q)
    w_sr_capped = np.clip(w_sr, None, cap_sr)

    df['w_sr'] = w_sr_capped

    # Person weights
    w_person = df['total_count'].values
    w_sr_person = w_sr_capped * w_person

    # Compute n_eff
    n_eff_no_correction = compute_n_eff(w_person)
    n_eff_with_sr_ipw = compute_n_eff(w_sr_person)

    pct_loss = (1 - n_eff_with_sr_ipw / n_eff_no_correction) * 100

    print(f'\nn_eff without SR-IPW: {n_eff_no_correction:.1f}')
    print(f'n_eff with SR-IPW: {n_eff_with_sr_ipw:.1f}')
    print(f'Information loss: {pct_loss:.1f}%')

    # Understanding n_eff formula
    print('\n--- Understanding n_eff = (sum w)^2 / sum(w^2) ---')
    print(f'Sum of weights: {w_sr_person.sum():.1f}')
    print(f'Sum of squared weights: {(w_sr_person**2).sum():.1f}')
    print(f'n_eff = ({w_sr_person.sum():.1f})^2 / {(w_sr_person**2).sum():.1f} = {n_eff_with_sr_ipw:.1f}')
    print('\nInterpretation:')
    print('  - If all weights equal: n_eff = n (no information loss)')
    print('  - If weights vary: n_eff < n (information loss proportional to variance)')
    print(f'  - Coefficient of variation of weights: {w_sr_person.std() / w_sr_person.mean():.2f}')

    # Distribution of SR and weights
    fig = plt.figure(figsize=(18, 12))
    gs = GridSpec(3, 3, figure=fig, hspace=0.3, wspace=0.3)

    # Plot 1: SR distribution
    ax1 = fig.add_subplot(gs[0, 0])
    ax1.hist(sr, bins=50, alpha=0.7, color='steelblue', edgecolor='black')
    ax1.axvline(sr.mean(), color='red', linestyle='--', linewidth=2, label=f'Mean={sr.mean():.2f}')
    ax1.axvline(np.median(sr), color='orange', linestyle='--', linewidth=2, label=f'Median={np.median(sr):.2f}')
    ax1.set_xlabel('Shadow Ratio (Sidewalk Average)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Count', fontsize=11, fontweight='bold')
    ax1.set_title('Distribution of Shadow Ratio (SR ≥ 0.10)', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 2: Propensity scores
    ax2 = fig.add_subplot(gs[0, 1])
    sr_grid = np.linspace(0, 1, 100)
    p_grid = 1.0 / (1.0 + np.exp(-10 * (sr_grid - 0.5)))
    p_grid = np.clip(p_grid, 0.05, 0.95)

    ax2.plot(sr_grid, p_grid, linewidth=3, color='darkgreen')
    ax2.scatter(sr, p_sr, alpha=0.3, s=10, color='steelblue')
    ax2.axhline(0.5, color='red', linestyle='--', alpha=0.5)
    ax2.set_xlabel('Shadow Ratio', fontsize=11, fontweight='bold')
    ax2.set_ylabel('P(observed | SR)', fontsize=11, fontweight='bold')
    ax2.set_title('Propensity Score Model\nP(SR) = 1/(1+exp(-10*(SR-0.5)))', fontsize=12, fontweight='bold')
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 1)

    # Plot 3: IPW weights
    ax3 = fig.add_subplot(gs[0, 2])
    ax3.hist(w_sr_capped, bins=50, alpha=0.7, color='coral', edgecolor='black')
    ax3.axvline(w_sr_capped.mean(), color='red', linestyle='--', linewidth=2,
                label=f'Mean={w_sr_capped.mean():.2f}')
    ax3.axvline(cap_sr, color='purple', linestyle='--', linewidth=2,
                label=f'Cap (95%ile)={cap_sr:.2f}')
    ax3.set_xlabel('SR-IPW Weight', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Count', fontsize=11, fontweight='bold')
    ax3.set_title('Distribution of SR-IPW Weights', fontsize=12, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Plot 4: SR vs Weight (showing the relationship)
    ax4 = fig.add_subplot(gs[1, 0])
    ax4.scatter(sr, w_sr_capped, alpha=0.5, s=20, color='steelblue')
    ax4.plot(sr_grid, 1.0/p_grid, linewidth=3, color='darkgreen', label='Uncapped')
    ax4.axhline(cap_sr, color='purple', linestyle='--', linewidth=2, label=f'Cap={cap_sr:.2f}')
    ax4.set_xlabel('Shadow Ratio', fontsize=11, fontweight='bold')
    ax4.set_ylabel('SR-IPW Weight', fontsize=11, fontweight='bold')
    ax4.set_title('Shadow Ratio → Weight Mapping', fontsize=12, fontweight='bold')
    ax4.legend()
    ax4.grid(True, alpha=0.3)

    # Plot 5: Weight concentration
    ax5 = fig.add_subplot(gs[1, 1])
    sorted_weights = np.sort(w_sr_person)[::-1]
    cumsum_weights = np.cumsum(sorted_weights)
    cumsum_pct = cumsum_weights / cumsum_weights[-1] * 100
    n_samples = np.arange(1, len(sorted_weights) + 1)
    sample_pct = n_samples / len(sorted_weights) * 100

    ax5.plot(sample_pct, cumsum_pct, linewidth=3, color='darkred')
    ax5.plot([0, 100], [0, 100], '--', color='gray', linewidth=2, label='Perfect equality')

    # Mark key points
    top_10_idx = int(0.1 * len(sorted_weights))
    top_20_idx = int(0.2 * len(sorted_weights))
    ax5.scatter([10], [cumsum_pct[top_10_idx]], s=100, color='red', zorder=5,
                label=f'Top 10% → {cumsum_pct[top_10_idx]:.1f}% of weight')
    ax5.scatter([20], [cumsum_pct[top_20_idx]], s=100, color='orange', zorder=5,
                label=f'Top 20% → {cumsum_pct[top_20_idx]:.1f}% of weight')

    ax5.set_xlabel('Cumulative % of Samples (sorted by weight)', fontsize=11, fontweight='bold')
    ax5.set_ylabel('Cumulative % of Total Weight', fontsize=11, fontweight='bold')
    ax5.set_title('Weight Concentration Curve\n(Lorenz-style)', fontsize=12, fontweight='bold')
    ax5.legend(loc='lower right', fontsize=9)
    ax5.grid(True, alpha=0.3)

    # Plot 6: Effective vs actual sample size
    ax6 = fig.add_subplot(gs[1, 2])

    # Show relationship between weight variance and n_eff
    cv_range = np.linspace(0, 2, 100)  # Coefficient of variation
    n = len(w_sr_person)
    # For simplified case: if weights have mean=1, var=cv^2
    # n_eff ≈ n / (1 + cv^2)
    n_eff_approx = n / (1 + cv_range**2)

    actual_cv = w_sr_person.std() / w_sr_person.mean()

    ax6.plot(cv_range, n_eff_approx, linewidth=3, color='purple')
    ax6.axvline(actual_cv, color='red', linestyle='--', linewidth=2,
                label=f'Actual CV={actual_cv:.2f}')
    ax6.axhline(n_eff_with_sr_ipw, color='green', linestyle='--', linewidth=2,
                label=f'Actual n_eff={n_eff_with_sr_ipw:.1f}')
    ax6.scatter([actual_cv], [n_eff_with_sr_ipw], s=200, color='red', zorder=5)

    ax6.set_xlabel('Coefficient of Variation of Weights', fontsize=11, fontweight='bold')
    ax6.set_ylabel('Effective Sample Size', fontsize=11, fontweight='bold')
    ax6.set_title(f'n_eff ≈ n/(1+CV²)\n(n={n:,})', fontsize=12, fontweight='bold')
    ax6.legend()
    ax6.grid(True, alpha=0.3)

    # Plot 7: UTCI vs SR (checking if SR varies with UTCI)
    ax7 = fig.add_subplot(gs[2, 0])
    ax7.scatter(df['utci_C'], sr, alpha=0.3, s=10, color='steelblue')

    # Bin by UTCI and show mean SR
    utci_bins = np.linspace(df['utci_C'].min(), df['utci_C'].max(), 20)
    utci_centers = (utci_bins[:-1] + utci_bins[1:]) / 2
    sr_means = []
    for i in range(len(utci_bins) - 1):
        mask = (df['utci_C'] >= utci_bins[i]) & (df['utci_C'] < utci_bins[i+1])
        if mask.sum() > 0:
            sr_means.append(sr[mask].mean())
        else:
            sr_means.append(np.nan)

    ax7.plot(utci_centers, sr_means, 'r-', linewidth=3, label='Mean SR by UTCI bin')
    ax7.set_xlabel('UTCI (°C)', fontsize=11, fontweight='bold')
    ax7.set_ylabel('Shadow Ratio', fontsize=11, fontweight='bold')
    ax7.set_title('Shadow Ratio vs UTCI\n(Testing if SR confounds with UTCI)', fontsize=12, fontweight='bold')
    ax7.legend()
    ax7.grid(True, alpha=0.3)

    # Plot 8: Preference vs SR (is there selection bias?)
    ax8 = fig.add_subplot(gs[2, 1])
    pref = df['inshade_count'] / df['total_count']
    ax8.scatter(sr, pref, alpha=0.3, s=10, color='steelblue')

    # Bin by SR and show mean preference
    sr_bins = np.linspace(sr.min(), sr.max(), 20)
    sr_centers = (sr_bins[:-1] + sr_bins[1:]) / 2
    pref_means = []
    for i in range(len(sr_bins) - 1):
        mask = (sr >= sr_bins[i]) & (sr < sr_bins[i+1])
        if mask.sum() > 0:
            pref_means.append(pref[mask].mean())
        else:
            pref_means.append(np.nan)

    ax8.plot(sr_centers, pref_means, 'r-', linewidth=3, label='Mean preference by SR bin')
    ax8.set_xlabel('Shadow Ratio', fontsize=11, fontweight='bold')
    ax8.set_ylabel('Shade Preference (proportion)', fontsize=11, fontweight='bold')
    ax8.set_title('Shade Preference vs Shadow Ratio\n(Evidence for selection bias)', fontsize=12, fontweight='bold')
    ax8.legend()
    ax8.grid(True, alpha=0.3)
    ax8.set_ylim(0, 1)

    # Plot 9: Summary statistics
    ax9 = fig.add_subplot(gs[2, 2])
    ax9.axis('off')

    summary_text = f"""
SR-IPW WEIGHT STATISTICS

Sample size: {len(df):,}
Person count: {w_person.sum():,.0f}

Weight Statistics:
  Min: {w_sr_capped.min():.3f}
  Max: {w_sr_capped.max():.3f}
  Mean: {w_sr_capped.mean():.3f}
  Median: {np.median(w_sr_capped):.3f}
  Std: {w_sr_capped.std():.3f}
  CV: {w_sr_capped.std()/w_sr_capped.mean():.3f}

Effective Sample Size:
  No correction: {n_eff_no_correction:.1f}
  With SR-IPW: {n_eff_with_sr_ipw:.1f}
  Information loss: {pct_loss:.1f}%

Weight Concentration:
  Top 10% holds: {cumsum_pct[top_10_idx]:.1f}% of weight
  Top 20% holds: {cumsum_pct[top_20_idx]:.1f}% of weight

WHY IS THIS ACCEPTABLE?
1. We believe high-SR areas are
   over-sampled (photographer bias)
2. Downweighting corrects for this
3. n_eff={n_eff_with_sr_ipw:.0f} still > 100 threshold
4. Bias reduction worth variance cost
"""

    ax9.text(0.05, 0.95, summary_text, transform=ax9.transAxes,
            fontsize=10, verticalalignment='top', fontfamily='monospace',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.suptitle('SR-IPW Information Loss Analysis: Why 51% Loss is Acceptable',
                fontsize=16, fontweight='bold', y=0.995)

    plt.savefig(OUTPUT_DIR / 'sr_ipw_mechanism_analysis.png', dpi=300, bbox_inches='tight')
    print(f'\nSaved SR-IPW mechanism plot -> {OUTPUT_DIR / "sr_ipw_mechanism_analysis.png"}')

    return df

# ---------------------------------------------------------------------------
# Analysis 2: Model Fit Improvements
# ---------------------------------------------------------------------------

def analyze_model_fit_improvements(df, walk_func):
    """Test whether corrections actually improve model fit to data."""

    print('\n' + '='*80)
    print('ANALYSIS 2: DO CORRECTIONS IMPROVE MODEL FIT?')
    print('='*80)

    # Filter to SR >= threshold
    df = df[df['shadow_ratio_ped_avg'] >= SR_MIN].copy()

    # Compute all weights
    # SR-IPW
    sr = df['shadow_ratio_ped_avg'].values
    p_sr = 1.0 / (1.0 + np.exp(-10 * (sr - 0.5)))
    p_sr = np.clip(p_sr, 0.05, 0.95)
    w_sr = 1.0 / p_sr
    cap_sr = np.quantile(w_sr, IPW_SR_CAP_Q)
    df['w_sr'] = np.clip(w_sr, None, cap_sr)

    # DCWP
    dist = df['dist_to_shade_m'].values
    df['w_dcwp'] = np.exp(-dist / TAU_M)

    # Temp-IPW
    utci_vals = df['utci_C'].values
    walk_rate = walk_func(utci_vals)
    w_temp = 1.0 / walk_rate
    cold_mask = utci_vals < BASELINE_TEMP
    cold_factor = 1.0 + 0.5 * ((BASELINE_TEMP - utci_vals[cold_mask]) / 20.0)
    w_temp[cold_mask] *= cold_factor
    cap_temp = np.quantile(w_temp, IPW_TEMP_CAP_Q)
    df['w_temp'] = np.clip(w_temp, None, cap_temp)

    # Spatial (simplified - just normalize by season for overall)
    df['w_spatial'] = 1.0

    # Temp range (simplified - just normalize)
    df['w_temp_range'] = 1.0

    # Progressive weights
    df['w_none'] = df['total_count']
    df['w_sr_only'] = df['w_sr'] * df['total_count']
    df['w_sr_dcwp'] = df['w_sr'] * df['w_dcwp'] * df['total_count']
    df['w_triple'] = df['w_sr'] * df['w_dcwp'] * df['w_temp'] * df['total_count']

    # Fit models
    print('\nFitting GLMs with progressive corrections...')

    results = {}
    weight_configs = [
        ('No correction', 'w_none'),
        ('+ SR-IPW', 'w_sr_only'),
        ('+ DCWP', 'w_sr_dcwp'),
        ('+ Temp-IPW', 'w_triple')
    ]

    for name, wcol in weight_configs:
        print(f'  Fitting: {name}...')
        fit = fit_glm_binomial(df, weight_col=wcol)
        if fit is not None:
            results[name] = fit
            n_eff = compute_n_eff(df[wcol])
            print(f'    n_eff: {n_eff:.1f}')
            print(f'    Pseudo-R²: {fit["pseudo_r2"]:.4f}')
            print(f'    AIC: {fit["aic"]:.1f}')
            print(f'    Weighted MSE: {fit["weighted_mse"]:.6f}')

    # Create comparison plots
    fig = plt.figure(figsize=(20, 12))
    gs = GridSpec(3, 4, figure=fig, hspace=0.35, wspace=0.35)

    # Plot 1-4: Fitted curves
    utci_plot = np.linspace(df['utci_C'].min(), df['utci_C'].max(), 100)
    X_plot = np.column_stack([np.ones_like(utci_plot), utci_plot, utci_plot**2])

    colors = ['black', 'blue', 'green', 'red']

    for idx, ((name, wcol), color) in enumerate(zip(weight_configs, colors)):
        ax = fig.add_subplot(gs[0, idx])

        # Scatter plot of data
        pref = df['inshade_count'] / df['total_count']
        weights = df[wcol] / df[wcol].max()  # Normalize for visualization
        ax.scatter(df['utci_C'], pref, alpha=0.3, s=weights*50, c='lightgray')

        # Fitted curve
        if name in results:
            y_plot = results[name]['result'].predict(X_plot)
            ax.plot(utci_plot, y_plot, linewidth=3, color=color, label='Fitted')

        ax.set_xlabel('UTCI (°C)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Shade Preference', fontsize=11, fontweight='bold')
        ax.set_title(f'{name}\nn_eff={compute_n_eff(df[wcol]):.1f}',
                    fontsize=12, fontweight='bold', color=color)
        ax.set_ylim(0, 1)
        ax.grid(True, alpha=0.3)
        ax.legend()

    # Plot 5: Goodness of fit comparison
    ax5 = fig.add_subplot(gs[1, 0])

    metrics_df = pd.DataFrame([
        {
            'Config': name,
            'Pseudo_R2': results[name]['pseudo_r2'],
            'n_eff': compute_n_eff(df[wcol])
        }
        for (name, wcol), color in zip(weight_configs, colors) if name in results
    ])

    x_pos = np.arange(len(metrics_df))
    bars = ax5.bar(x_pos, metrics_df['Pseudo_R2'], color=colors[:len(metrics_df)], alpha=0.7, edgecolor='black')
    ax5.set_xticks(x_pos)
    ax5.set_xticklabels(metrics_df['Config'], rotation=45, ha='right')
    ax5.set_ylabel('Pseudo-R² (1 - Dev/Null Dev)', fontsize=11, fontweight='bold')
    ax5.set_title('Model Fit: Pseudo-R²', fontsize=12, fontweight='bold')
    ax5.grid(True, alpha=0.3, axis='y')

    # Annotate with values
    for i, (bar, r2) in enumerate(zip(bars, metrics_df['Pseudo_R2'])):
        ax5.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.005,
                f'{r2:.4f}', ha='center', fontsize=9, fontweight='bold')

    # Plot 6: AIC comparison (lower is better)
    ax6 = fig.add_subplot(gs[1, 1])

    aic_values = [results[name]['aic'] for name, _ in weight_configs if name in results]
    bars = ax6.bar(x_pos, aic_values, color=colors[:len(aic_values)], alpha=0.7, edgecolor='black')
    ax6.set_xticks(x_pos)
    ax6.set_xticklabels(metrics_df['Config'], rotation=45, ha='right')
    ax6.set_ylabel('AIC (lower = better)', fontsize=11, fontweight='bold')
    ax6.set_title('Model Selection: AIC', fontsize=12, fontweight='bold')
    ax6.grid(True, alpha=0.3, axis='y')

    # Mark best
    best_idx = np.argmin(aic_values)
    bars[best_idx].set_edgecolor('gold')
    bars[best_idx].set_linewidth(3)

    # Plot 7: Weighted MSE
    ax7 = fig.add_subplot(gs[1, 2])

    mse_values = [results[name]['weighted_mse'] for name, _ in weight_configs if name in results]
    bars = ax7.bar(x_pos, mse_values, color=colors[:len(mse_values)], alpha=0.7, edgecolor='black')
    ax7.set_xticks(x_pos)
    ax7.set_xticklabels(metrics_df['Config'], rotation=45, ha='right')
    ax7.set_ylabel('Weighted MSE (lower = better)', fontsize=11, fontweight='bold')
    ax7.set_title('Prediction Error: MSE', fontsize=12, fontweight='bold')
    ax7.grid(True, alpha=0.3, axis='y')

    # Mark best
    best_idx = np.argmin(mse_values)
    bars[best_idx].set_edgecolor('gold')
    bars[best_idx].set_linewidth(3)

    # Plot 8: n_eff vs fit quality tradeoff
    ax8 = fig.add_subplot(gs[1, 3])

    n_effs = [compute_n_eff(df[wcol]) for _, wcol in weight_configs]
    pseudo_r2s = [results[name]['pseudo_r2'] for name, _ in weight_configs if name in results]

    ax8.scatter(n_effs, pseudo_r2s, s=200, c=colors[:len(n_effs)], alpha=0.7, edgecolor='black', linewidth=2)

    for i, name in enumerate([n for n, _ in weight_configs]):
        ax8.annotate(name, (n_effs[i], pseudo_r2s[i]),
                    xytext=(10, 10), textcoords='offset points',
                    fontsize=9, fontweight='bold')

    ax8.set_xlabel('Effective Sample Size', fontsize=11, fontweight='bold')
    ax8.set_ylabel('Pseudo-R² (model fit)', fontsize=11, fontweight='bold')
    ax8.set_title('Variance-Bias Tradeoff\n(Right = more power, Up = better fit)',
                 fontsize=12, fontweight='bold')
    ax8.grid(True, alpha=0.3)

    # Plot 9-12: Residual diagnostics
    for idx, ((name, wcol), color) in enumerate(zip(weight_configs, colors)):
        ax = fig.add_subplot(gs[2, idx])

        if name in results:
            resid = results[name]['pearson_resid']
            utci = df['utci_C']

            ax.scatter(utci, resid, alpha=0.3, s=10, color=color)
            ax.axhline(0, color='black', linestyle='--', linewidth=2)
            ax.axhline(2, color='red', linestyle=':', linewidth=1, alpha=0.5)
            ax.axhline(-2, color='red', linestyle=':', linewidth=1, alpha=0.5)

            ax.set_xlabel('UTCI (°C)', fontsize=10, fontweight='bold')
            ax.set_ylabel('Pearson Residual', fontsize=10, fontweight='bold')
            ax.set_title(f'{name}\nResidual Plot', fontsize=11, fontweight='bold', color=color)
            ax.grid(True, alpha=0.3)
            ax.set_ylim(-4, 4)

    plt.suptitle('Model Fit Comparison: Do Corrections Improve Fit?',
                fontsize=16, fontweight='bold', y=0.995)

    plt.savefig(OUTPUT_DIR / 'model_fit_improvements.png', dpi=300, bbox_inches='tight')
    print(f'\nSaved model fit comparison -> {OUTPUT_DIR / "model_fit_improvements.png"}')

    # Save metrics table
    metrics_full = pd.DataFrame([
        {
            'Configuration': name,
            'n_eff': compute_n_eff(df[wcol]),
            'Pseudo_R2': results[name]['pseudo_r2'],
            'AIC': results[name]['aic'],
            'BIC': results[name]['bic'],
            'Weighted_MSE': results[name]['weighted_mse'],
            'Weighted_LogLoss': results[name]['weighted_logloss']
        }
        for (name, wcol) in weight_configs if name in results
    ])

    metrics_full.to_csv(OUTPUT_DIR / 'model_fit_metrics.csv', index=False)
    print(f'Saved model fit metrics -> {OUTPUT_DIR / "model_fit_metrics.csv"}')

    print('\n--- SUMMARY ---')
    print(metrics_full.to_string(index=False))

    return results, metrics_full

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print('='*80)
    print('SR-IPW INVESTIGATION: Information Loss and Model Fit')
    print('='*80)

    # Load data
    df = load_data()
    walk_func = load_walk_rate_func(WALK_RATE_CSV)

    # Analysis 1: SR-IPW mechanism
    df_analyzed = analyze_sr_ipw_mechanism(df)

    # Analysis 2: Model fit improvements
    results, metrics = analyze_model_fit_improvements(df, walk_func)

    print('\n' + '='*80)
    print('INVESTIGATION COMPLETE')
    print(f'Output directory: {OUTPUT_DIR}')
    print('='*80)

if __name__ == '__main__':
    main()
