# ABOUTME: Creates figure showing pedestrian mode choice vs temperature from mobility survey data
# ABOUTME: Displays walking trip percentage by UTCI bins with 95% bootstrap confidence intervals

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

# Load Seattle mobility survey data
print("Loading Seattle mobility survey data...")
data_path = Path('/home/kieran/Documents/Python/sunny_day_SVI/data/mobility_surveys/seattle/seattle_trips_with_utci.csv')
df = pd.read_csv(data_path, low_memory=False)

print(f"Loaded {len(df):,} trips")
print(f"Walking trips: {df['is_walk'].sum():,} ({df['is_walk'].mean()*100:.1f}%)")

# Check for UTCI data
print(f"\nUTCI range: {df['utci'].min():.1f} to {df['utci'].max():.1f}°C")
print(f"Trips with UTCI data: {df['utci'].notna().sum():,}")

# Create UTCI bins (2°C intervals to match the other plot)
bin_width = 2
utci_min = np.floor(df['utci'].min() / bin_width) * bin_width
utci_max = np.ceil(df['utci'].max() / bin_width) * bin_width
bins = np.arange(utci_min, utci_max + bin_width, bin_width)
bin_centers = bins[:-1] + bin_width / 2

df['utci_bin'] = pd.cut(df['utci'], bins=bins, labels=bin_centers, include_lowest=True)
df['utci_bin'] = df['utci_bin'].astype(float)

print(f"Created {len(bin_centers)} bins from {utci_min:.1f} to {utci_max:.1f}°C")


def bootstrap_ci(data, n_bootstrap=1000, ci=95):
    """Calculate bootstrap confidence intervals for proportion"""
    if len(data) == 0:
        return np.nan, np.nan

    boot_props = []
    for _ in range(n_bootstrap):
        # Resample with replacement
        boot_sample = data.sample(n=len(data), replace=True)
        boot_prop = boot_sample.mean()
        boot_props.append(boot_prop)

    # Calculate percentile-based CI
    lower = (100 - ci) / 2
    upper = 100 - lower
    ci_lower, ci_upper = np.percentile(boot_props, [lower, upper])

    return ci_lower, ci_upper


def calculate_pedestrian_mode_share(df, min_trips=30):
    """Calculate pedestrian mode share by UTCI bin"""
    results = []

    for bin_center in bin_centers:
        bin_data = df[df['utci_bin'] == bin_center].copy()

        if len(bin_data) < min_trips:
            continue

        # Calculate proportion of walking trips
        walk_prop = bin_data['is_walk'].mean()

        # Bootstrap CI
        ci_lower, ci_upper = bootstrap_ci(bin_data['is_walk'], n_bootstrap=1000, ci=95)

        results.append({
            'utci': bin_center,
            'walk_pct': walk_prop * 100,
            'ci_lower': ci_lower * 100,
            'ci_upper': ci_upper * 100,
            'n_trips': len(bin_data),
            'n_walk': bin_data['is_walk'].sum()
        })

    return pd.DataFrame(results)


# Calculate pedestrian mode share
print("\nCalculating pedestrian mode share by temperature...")
mode_share = calculate_pedestrian_mode_share(df, min_trips=30)

print(f"UTCI bins with sufficient data: {len(mode_share)}")
print(f"\nMode share statistics:")
print(f"  Mean: {mode_share['walk_pct'].mean():.1f}%")
print(f"  Min: {mode_share['walk_pct'].min():.1f}% at {mode_share.loc[mode_share['walk_pct'].idxmin(), 'utci']:.1f}°C")
print(f"  Max: {mode_share['walk_pct'].max():.1f}% at {mode_share.loc[mode_share['walk_pct'].idxmax(), 'utci']:.1f}°C")

# Create figure
print("\nCreating figure...")
fig, ax = plt.subplots(figsize=(10, 6))

# Plot with error bars
ax.errorbar(
    mode_share['utci'],
    mode_share['walk_pct'],
    yerr=[
        mode_share['walk_pct'] - mode_share['ci_lower'],
        mode_share['ci_upper'] - mode_share['walk_pct']
    ],
    color='#3498db',
    marker='o',
    markersize=8,
    linewidth=2.5,
    capsize=4,
    capthick=2,
    alpha=0.8,
    linestyle='-',
    label='Walking mode share (95% CI)'
)

# Formatting
ax.set_xlabel('UTCI Temperature (°C)', fontsize=12, fontweight='bold')
ax.set_ylabel('Pedestrian Mode Share (%)', fontsize=12, fontweight='bold')
ax.set_title('Pedestrian Mode Choice vs Temperature\nSeattle Puget Sound Regional Council 2017 Mobility Survey',
             fontsize=13, fontweight='bold', pad=20)
ax.legend(loc='best', fontsize=10, framealpha=0.95)
ax.grid(True, alpha=0.3)

# Set reasonable y-axis limits
y_min = max(0, mode_share['ci_lower'].min() - 5)
y_max = min(100, mode_share['ci_upper'].max() + 5)
ax.set_ylim(y_min, y_max)

plt.tight_layout()

# Save figure
output_dir = Path('/home/kieran/Documents/Python/sunny_day_SVI/outputs/plots/mobility')
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / 'pedestrian_mode_choice_vs_temperature.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"\nFigure saved to: {output_path}")

# Also save as PDF
output_path_pdf = output_dir / 'pedestrian_mode_choice_vs_temperature.pdf'
plt.savefig(output_path_pdf, bbox_inches='tight')
print(f"PDF saved to: {output_path_pdf}")

# Save data table
output_csv = output_dir / 'pedestrian_mode_choice_vs_temperature_data.csv'
mode_share.to_csv(output_csv, index=False)
print(f"Data saved to: {output_csv}")

# Print detailed statistics by bin
print("\n" + "="*80)
print("DETAILED STATISTICS BY TEMPERATURE BIN")
print("="*80)
for _, row in mode_share.iterrows():
    print(f"\nUTCI {row['utci']:>5.1f}°C:")
    print(f"  Walking trips: {row['n_walk']:.0f} / {row['n_trips']:.0f} ({row['walk_pct']:.1f}%)")
    print(f"  95% CI: [{row['ci_lower']:.1f}%, {row['ci_upper']:.1f}%]")

plt.show()
