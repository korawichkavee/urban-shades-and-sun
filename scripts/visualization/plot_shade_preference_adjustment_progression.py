# ABOUTME: Creates figure showing shade preference vs UTCI with progressive IPW adjustments
# ABOUTME: Displays raw, seasonal-adjusted, seasonal+temp-adjusted, and fully-adjusted estimates with 95% CIs

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

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


def calculate_shade_preference(df, weight_col=None, min_images=10):
    """Calculate shade preference by UTCI bin with optional weighting"""
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

        # Bootstrap CI
        ci_lower, ci_upper = bootstrap_ci(bin_data['in_shade'], weights, n_bootstrap=1000, ci=95)

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

# 1. Raw (no weights)
print("  - Raw (no adjustments)")
raw_results = calculate_shade_preference(df, weight_col=None)

# 2. Seasonal adjustment only
print("  - Seasonal adjustment")
seasonal_results = calculate_shade_preference(df, weight_col='w_season')

# 3. Seasonal + temperature adjustment
print("  - Seasonal + temperature adjustment")
df['seasonal_temp_weight'] = df['w_season'] * df['w_temp_ipw']
seasonal_temp_results = calculate_shade_preference(df, weight_col='seasonal_temp_weight')

# 4. Full combined adjustment
print("  - Full combined adjustment")
combined_results = calculate_shade_preference(df, weight_col='w_final')

# Create figure
print("\nCreating figure...")
fig, ax = plt.subplots(figsize=(12, 7))

# Define colors and styles for each adjustment level
adjustments = [
    (raw_results, 'Raw (unadjusted)', '#e74c3c', 'o'),
    (seasonal_results, 'Seasonal adjustment', '#f39c12', 's'),
    (seasonal_temp_results, 'Seasonal + temperature', '#3498db', '^'),
    (combined_results, 'Full IPW (seasonal + temp + shadow ratio)', '#2ecc71', 'D')
]

# Plot each adjustment level
for results_df, label, color, marker in adjustments:
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
ax.set_ylabel('Shade Preference (proportion in shade)', fontsize=12, fontweight='bold')
ax.set_title('Shade Response Parameter Estimate',
             fontsize=14, fontweight='bold', pad=20)
ax.legend(loc='lower center', bbox_to_anchor=(0.5, -0.15), fontsize=10, framealpha=0.95, ncol=2)
ax.grid(True, alpha=0.3)
ax.set_ylim(-0.05, 1.05)

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
    print(f"  Mean shade preference: {results_df['shade_pref'].mean():.3f}")
    print(f"  Min shade preference: {results_df['shade_pref'].min():.3f} at {results_df.loc[results_df['shade_pref'].idxmin(), 'utci']:.1f}°C")
    print(f"  Max shade preference: {results_df['shade_pref'].max():.3f} at {results_df.loc[results_df['shade_pref'].idxmax(), 'utci']:.1f}°C")

plt.show()
