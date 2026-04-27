#!/usr/bin/env python3
"""
Create presentation-ready plot of sample sizes per UTCI bin for Seattle and NYC.
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-whitegrid')
sns.set_palette("husl")

# Load binned data
seattle = pd.read_csv('outputs/analysis/seasonally_adjusted_plots/seattle_binned_data_with_temp.csv')
nyc = pd.read_csv('outputs/analysis/seasonally_adjusted_plots/new-york-city_binned_data_with_temp.csv')

# Create figure
fig, ax = plt.subplots(figsize=(12, 7))

# Plot sample sizes
ax.plot(seattle['bin_center'], seattle['n_raw'],
        marker='o', markersize=8, linewidth=2.5,
        color='#2E86AB', label='Seattle', alpha=0.9)

ax.plot(nyc['bin_center'], nyc['n_raw'],
        marker='s', markersize=8, linewidth=2.5,
        color='#A23B72', label='NYC', alpha=0.9)

# Add quality threshold lines
ax.axhline(y=1000, color='gray', linestyle='--', linewidth=1.5, alpha=0.5, zorder=1)
ax.axhline(y=5000, color='gray', linestyle='--', linewidth=1.5, alpha=0.5, zorder=1)

# Add threshold labels on right side
ax.text(35, 1000, 'N = 1,000', va='bottom', ha='left', fontsize=11, color='gray')
ax.text(35, 5000, 'N = 5,000', va='bottom', ha='left', fontsize=11, color='gray')

# Shade the reliable comparison region (-15 to 25°C)
ax.axvspan(-15, 25, alpha=0.1, color='green', zorder=0)
ax.text(5, 72000, 'Reliable comparison range',
        ha='center', fontsize=12, color='darkgreen',
        bbox=dict(boxstyle='round', facecolor='lightgreen', alpha=0.3))

# Labels and title
ax.set_xlabel('UTCI (°C)', fontsize=16, fontweight='bold')
ax.set_ylabel('Number of Observations per Bin', fontsize=16, fontweight='bold')
ax.set_title('Sample Size Coverage by Temperature Range',
             fontsize=18, fontweight='bold', pad=20)

# Format y-axis with comma separator
ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))

# Legend
ax.legend(fontsize=14, loc='upper left', framealpha=0.9)

# Grid
ax.grid(True, alpha=0.3, axis='y')

# Set limits
ax.set_xlim(-40, 40)
ax.set_ylim(0, 80000)

plt.tight_layout()

# Save
output_dir = 'outputs/analysis/seasonally_adjusted_plots'
plt.savefig(f'{output_dir}/sample_sizes_presentation.png', dpi=300, bbox_inches='tight')
plt.savefig(f'{output_dir}/sample_sizes_presentation.pdf', bbox_inches='tight')

print(f"✓ Saved sample size plots to {output_dir}/")
print(f"  - sample_sizes_presentation.png (300 dpi)")
print(f"  - sample_sizes_presentation.pdf")

# Print summary stats
print(f"\n=== Seattle Summary ===")
print(f"Total bins: {len(seattle)}")
print(f"UTCI range: {seattle['bin_center'].min():.0f}°C to {seattle['bin_center'].max():.0f}°C")
print(f"Median N: {seattle['n_raw'].median():.0f}")
print(f"Bins with N > 1,000: {(seattle['n_raw'] > 1000).sum()} ({100*(seattle['n_raw'] > 1000).sum()/len(seattle):.1f}%)")

print(f"\n=== NYC Summary ===")
print(f"Total bins: {len(nyc)}")
print(f"UTCI range: {nyc['bin_center'].min():.0f}°C to {nyc['bin_center'].max():.0f}°C")
print(f"Median N: {nyc['n_raw'].median():.0f}")
print(f"Bins with N > 1,000: {(nyc['n_raw'] > 1000).sum()} ({100*(nyc['n_raw'] > 1000).sum()/len(nyc):.1f}%)")

# Summary for overlap region
seattle_overlap = seattle[(seattle['bin_center'] >= -15) & (seattle['bin_center'] <= 25)]
nyc_overlap = nyc[(nyc['bin_center'] >= -15) & (nyc['bin_center'] <= 25)]

print(f"\n=== Overlap Region (-15°C to 25°C) ===")
print(f"Seattle bins: {len(seattle_overlap)}, median N = {seattle_overlap['n_raw'].median():.0f}")
print(f"NYC bins: {len(nyc_overlap)}, median N = {nyc_overlap['n_raw'].median():.0f}")
