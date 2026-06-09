# ABOUTME: Check for confounding between temperature and shadow availability
# ABOUTME: Analyzes correlation and creates diagnostic visualization

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Load data
df = pd.read_csv('data/final_datasets/seattle/seattle_final_analysis_with_seasonal_and_temp.csv', low_memory=False)
df = df[df['person_count'] > 0].copy()

print(f"Total images with people: {len(df):,}")
print()

# Overall correlation
corr = df[['utci_C', 'shadow_ratio']].corr().iloc[0, 1]
print(f"Correlation(UTCI, shadow_ratio): {corr:.4f}")
print()

# Temperature bins for analysis
df['temp_bin'] = pd.cut(df['utci_C'], bins=10)

# Shadow statistics by temperature
shadow_stats = df.groupby('temp_bin', observed=True).agg({
    'shadow_ratio': ['mean', 'median', 'std', 'count']
})

print("Shadow ratio by temperature bin:")
print("="*80)
for idx, row in shadow_stats.iterrows():
    print(f"{idx.mid:>6.1f}°C: mean={row[('shadow_ratio', 'mean')]:.3f}, "
          f"median={row[('shadow_ratio', 'median')]:.3f}, "
          f"std={row[('shadow_ratio', 'std')]:.3f}, "
          f"n={int(row[('shadow_ratio', 'count')]):>6,}")

# Create visualization
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Panel 1: Scatter plot with trend
ax = axes[0, 0]
sample = df.sample(min(10000, len(df)), random_state=42)
ax.scatter(sample['utci_C'], sample['shadow_ratio'], alpha=0.1, s=1)
z = np.polyfit(df['utci_C'], df['shadow_ratio'], 1)
p = np.poly1d(z)
x_line = np.linspace(df['utci_C'].min(), df['utci_C'].max(), 100)
ax.plot(x_line, p(x_line), "r-", linewidth=2,
        label=f'Linear fit (r={corr:.3f})')
ax.set_xlabel('UTCI Temperature (°C)', fontsize=11, fontweight='bold')
ax.set_ylabel('Shadow Ratio', fontsize=11, fontweight='bold')
ax.set_title('Shadow Availability vs Temperature\nScatter Plot',
             fontsize=12, fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3)

# Panel 2: Box plot by temperature deciles
ax = axes[0, 1]
temp_deciles = pd.qcut(df['utci_C'], q=10, duplicates='drop')
df_plot = df.copy()
df_plot['temp_decile'] = temp_deciles
box_data = [df_plot[df_plot['temp_decile'] == cat]['shadow_ratio'].values
            for cat in temp_deciles.cat.categories]
positions = range(len(box_data))
bp = ax.boxplot(box_data, positions=positions, widths=0.6)
decile_labels = [f"{cat.mid:.0f}" for cat in temp_deciles.cat.categories]
ax.set_xticks(positions)
ax.set_xticklabels(decile_labels, rotation=45)
ax.set_xlabel('UTCI Temperature (°C)', fontsize=11, fontweight='bold')
ax.set_ylabel('Shadow Ratio', fontsize=11, fontweight='bold')
ax.set_title('Shadow Ratio Distribution by Temperature\nBox Plot',
             fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')

# Panel 3: Mean shadow ratio by temperature bin
ax = axes[1, 0]
temp_bins = df.groupby('temp_bin', observed=True)['shadow_ratio'].agg(['mean', 'std', 'count'])
x = [interval.mid for interval in temp_bins.index]
y = temp_bins['mean']
yerr = temp_bins['std'] / np.sqrt(temp_bins['count'])  # Standard error
ax.errorbar(x, y, yerr=yerr, marker='o', markersize=8, linewidth=2,
            capsize=4, label='Mean ± SE')
ax.axhline(df['shadow_ratio'].mean(), color='red', linestyle='--',
           label=f'Overall mean: {df["shadow_ratio"].mean():.3f}')
ax.set_xlabel('UTCI Temperature (°C)', fontsize=11, fontweight='bold')
ax.set_ylabel('Mean Shadow Ratio', fontsize=11, fontweight='bold')
ax.set_title('Mean Shadow Availability by Temperature',
             fontsize=12, fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3)

# Panel 4: Sample size distribution
ax = axes[1, 1]
bins_mid = [interval.mid for interval in shadow_stats.index]
counts = shadow_stats[('shadow_ratio', 'count')].values
bars = ax.bar(bins_mid, counts, width=4, alpha=0.7, edgecolor='black')
ax.set_xlabel('UTCI Temperature (°C)', fontsize=11, fontweight='bold')
ax.set_ylabel('Number of Images', fontsize=11, fontweight='bold')
ax.set_title('Sample Size Distribution by Temperature',
             fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')

# Color bars by count
max_count = counts.max()
for bar, count in zip(bars, counts):
    normalized = count / max_count
    bar.set_facecolor(plt.cm.viridis(normalized))

plt.tight_layout()

# Save figure
output_dir = Path('outputs/analysis/figures')
output_dir.mkdir(parents=True, exist_ok=True)
output_path = output_dir / 'shadow_temperature_correlation.png'
plt.savefig(output_path, dpi=300, bbox_inches='tight')
print(f"\nFigure saved to: {output_path}")

output_path_pdf = output_dir / 'shadow_temperature_correlation.pdf'
plt.savefig(output_path_pdf, bbox_inches='tight')
print(f"PDF saved to: {output_path_pdf}")

# Summary statistics
print("\n" + "="*80)
print("SUMMARY: TEMPERATURE-SHADOW CONFOUNDING")
print("="*80)
print(f"\nCorrelation coefficient: {corr:.4f}")

if abs(corr) < 0.1:
    assessment = "NEGLIGIBLE - No meaningful confounding"
elif abs(corr) < 0.3:
    assessment = "WEAK - Minor confounding, likely already handled by SR-IPW"
elif abs(corr) < 0.5:
    assessment = "MODERATE - Consider additional stratification"
else:
    assessment = "STRONG - Additional correction recommended"

print(f"Assessment: {assessment}")

print(f"\nShadow ratio range by temperature:")
print(f"  Cold (-15°C):  {shadow_stats.iloc[0][('shadow_ratio', 'mean')]:.3f}")
print(f"  Warm (+30°C):  {shadow_stats.iloc[-1][('shadow_ratio', 'mean')]:.3f}")
print(f"  Difference:    {shadow_stats.iloc[0][('shadow_ratio', 'mean')] - shadow_stats.iloc[-1][('shadow_ratio', 'mean')]:.3f}")

print("\nConclusion:")
if corr < 0:
    print("  Warmer temps → LESS shadow (negative correlation)")
    print("  This is OPPOSITE of concern (cold → less sun)")
    print("  Current SR-IPW already handles this by upweighting low-shadow images")
else:
    print("  Warmer temps → MORE shadow (positive correlation)")
    print("  Shadow availability bias reinforces temperature effect")

plt.show()
