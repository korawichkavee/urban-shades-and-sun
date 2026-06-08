# ABOUTME: Creates figure showing shade preference vs UTCI with progressive IPW adjustments
# ABOUTME: Displays raw, temp-adjusted, shade ratio, and DCWP-adjusted estimates with 95% CIs

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
from scipy.interpolate import interp1d

# Set up plotting style
sns.set_style("whitegrid")
plt.rcParams['figure.dpi'] = 300
plt.rcParams['savefig.dpi'] = 300
plt.rcParams['font.size'] = 10

# Load Seattle data
print("Loading Seattle data...")
data_path = Path('/home/kieran/Documents/Python/sunny_day_SVI/data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv')
df = pd.read_csv(data_path, low_memory=False)

# Filter to images with people
df = df[df['person_count'] > 0].copy()
print(f"Loaded {len(df):,} images with people")

# Check available weight columns
print("\nAvailable columns:")
weight_cols = [col for col in df.columns if 'weight' in col.lower()]
print(f"Weight columns: {weight_cols}")

# Create UTCI bins (2°C intervals)
bin_width = 2
utci_min = np.floor(df['utci_C'].min() / bin_width) * bin_width
utci_max = np.ceil(df['utci_C'].max() / bin_width) * bin_width
bins = np.arange(utci_min, utci_max + bin_width, bin_width)
bin_centers = bins[:-1] + bin_width / 2

df['utci_bin'] = pd.cut(df['utci_C'], bins=bins, labels=bin_centers, include_lowest=True)
df['utci_bin'] = df['utci_bin'].astype(float)

print(f"\nUTCI range: {df['utci_C'].min():.1f} to {df['utci_C'].max():.1f}°C")
print(f"Created {len(bin_centers)} bins from {utci_min:.1f} to {utci_max:.1f}°C")

# Load mobility walk rate data for temperature adjustment
print("\nLoading mobility walk rate data...")
walk_rate_path = Path('/home/kieran/Documents/Python/sunny_day_SVI/outputs/analysis/seattle_walking_by_utci.csv')
walk_rate_df = pd.read_csv(walk_rate_path)
print(f"Loaded walk rates for {len(walk_rate_df)} temperature bins")

# Create interpolation function for walk rates
walk_rate_interp = interp1d(
    walk_rate_df['utci_bin_center'],
    walk_rate_df['walk_rate'],
    kind='linear',
    bounds_error=False,
    fill_value=(walk_rate_df['walk_rate'].iloc[0], walk_rate_df['walk_rate'].iloc[-1])
)

# Set baseline walk rate at 20°C
baseline_utci = 20.0
baseline_walk_rate = walk_rate_interp(baseline_utci)
print(f"Baseline walk rate at {baseline_utci}°C: {baseline_walk_rate:.3f}")


def bootstrap_ci(data, weights, n_bootstrap=1000, ci=95):
    """Calculate bootstrap confidence intervals for weighted mean"""
    if len(data) == 0:
        return np.nan, np.nan

    boot_means = []
    for _ in range(n_bootstrap):
        # Resample indices with replacement
        indices = np.random.choice(len(data), size=len(data), replace=True)
        boot_data = data.iloc[indices]
        boot_weights = weights.iloc[indices]

        # Calculate weighted mean
        weighted_mean = (boot_data * boot_weights).sum() / boot_weights.sum()
        boot_means.append(weighted_mean)

    # Calculate percentile-based CI
    lower = (100 - ci) / 2
    upper = 100 - lower
    ci_lower, ci_upper = np.percentile(boot_means, [lower, upper])

    return ci_lower, ci_upper


def calculate_shade_preference(df, weight_col=None, min_images=10, temp_adjustment=False):
    """Calculate shade preference by UTCI bin with optional weighting and temperature adjustment"""
    results = []

    for bin_center in bin_centers:
        bin_data = df[df['utci_bin'] == bin_center].copy()

        if len(bin_data) < min_images:
            continue

        # Set weights
        if weight_col is None:
            weights = pd.Series(np.ones(len(bin_data)), index=bin_data.index)
        else:
            weights = bin_data[weight_col]

        # Calculate weighted mean shade preference
        shade_pref = (bin_data['in_shade'] * weights).sum() / weights.sum()

        # Apply temperature adjustment if requested
        if temp_adjustment:
            walk_rate_T = walk_rate_interp(bin_center)
            adjustment = (walk_rate_T - baseline_walk_rate) * 1.0  # sensitivity = 1.0
            shade_pref = shade_pref + adjustment

        # Bootstrap CI
        ci_lower, ci_upper = bootstrap_ci(bin_data['in_shade'], weights, n_bootstrap=1000, ci=95)

        # Apply same adjustment to CI bounds if using temp adjustment
        if temp_adjustment:
            walk_rate_T = walk_rate_interp(bin_center)
            adjustment = (walk_rate_T - baseline_walk_rate) * 1.0
            ci_lower = ci_lower + adjustment
            ci_upper = ci_upper + adjustment

        results.append({
            'utci': bin_center,
            'shade_pref': shade_pref,
            'ci_lower': ci_lower,
            'ci_upper': ci_upper,
            'n_images': len(bin_data)
        })

    return pd.DataFrame(results)


# Calculate shade preference for each adjustment level
print("\nCalculating shade preference with different adjustments...")

# 1. Raw (no weights, no adjustments)
print("  - Raw (no adjustments)")
raw_results = calculate_shade_preference(df, weight_col=None, temp_adjustment=False)

# 2. Temperature adjustment (linear, sensitivity=1.0)
print("  - Temperature adjustment (linear)")
temp_adjusted_results = calculate_shade_preference(df, weight_col=None, temp_adjustment=True)

# 3. Temp adjustment + shade ratio
print("  - Temp adjustment + shade ratio correction")
temp_sr_results = calculate_shade_preference(df, weight_col='w_sr_ipw', temp_adjustment=True)

# 4. Full: Temp adjustment + shade ratio + DCWP
print("  - Full: Temp adjustment + shade ratio + DCWP")
df['sr_dcwp_weight'] = df['w_sr_ipw'] * df['w_dcwp']
full_results = calculate_shade_preference(df, weight_col='sr_dcwp_weight', temp_adjustment=True)

# Create figure
print("\nCreating figure...")
fig, ax = plt.subplots(figsize=(12, 7))

# Define colors and styles for each adjustment level
adjustments = [
    (raw_results, 'Raw (unadjusted)', '#e74c3c', 'o'),
    (temp_adjusted_results, 'Temperature adjustment (linear)', '#f39c12', 's'),
    (temp_sr_results, 'Temp adjustment + shade ratio', '#3498db', '^'),
    (full_results, 'Temp adjustment + shade ratio + DCWP', '#2ecc71', 'D')
]

# Plot each adjustment level
for results_df, label, color, marker in adjustments:
    # Convert to percentage
    results_df = results_df.copy()
    results_df['shade_pref'] = results_df['shade_pref'] * 100
    results_df['ci_lower'] = results_df['ci_lower'] * 100
    results_df['ci_upper'] = results_df['ci_upper'] * 100

    # Plot mean with error bars
    ax.errorbar(
        results_df['utci'],
        results_df['shade_pref'],
        yerr=[
            results_df['shade_pref'] - results_df['ci_lower'],
            results_df['ci_upper'] - results_df['shade_pref']
        ],
        label=label,
        color=color,
        marker=marker,
        markersize=6,
        linewidth=2,
        capsize=3,
        capthick=1.5,
        alpha=0.8,
        linestyle='-'
    )

# Formatting
ax.set_xlabel('UTCI Temperature (°C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Shade Preference (%)', fontsize=12, fontweight='bold')
ax.set_title('Shade Response Parameter Estimate\nProgressive Adjustments for Selection Bias',
             fontsize=14, fontweight='bold', pad=20)
ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.25), fontsize=9, framealpha=0.95, ncol=2)
ax.grid(True, alpha=0.3)
ax.set_ylim(-5, 105)

plt.tight_layout()

# Save figure
output_dir = Path('/home/kieran/Documents/Python/sunny_day_SVI/outputs/plots/shade_behavior')
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / 'shade_preference_adjustment_progression.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"\nFigure saved to: {output_path}")

# Also save as PDF for publications
output_path_pdf = output_dir / 'shade_preference_adjustment_progression.pdf'
plt.savefig(output_path_pdf, bbox_inches='tight')
print(f"PDF saved to: {output_path_pdf}")

# Print summary statistics
print("\n" + "="*80)
print("SUMMARY STATISTICS")
print("="*80)
for results_df, label, _, _ in adjustments:
    print(f"\n{label}:")
    print(f"  UTCI bins with data: {len(results_df)}")
    print(f"  Mean shade preference: {results_df['shade_pref'].mean()*100:.1f}%")
    print(f"  Min shade preference: {results_df['shade_pref'].min()*100:.1f}% at {results_df.loc[results_df['shade_pref'].idxmin(), 'utci']:.1f}°C")
    print(f"  Max shade preference: {results_df['shade_pref'].max()*100:.1f}% at {results_df.loc[results_df['shade_pref'].idxmax(), 'utci']:.1f}°C")

plt.show()
