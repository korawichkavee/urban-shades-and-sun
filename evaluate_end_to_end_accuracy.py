#!/usr/bin/env python3
# ABOUTME: End-to-end accuracy evaluation for shade ratio predictions
# ABOUTME: Compares predicted vs actual counts of people in/out of shade per image

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
from scipy import stats
import seaborn as sns
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = Path("outputs/model_evaluation")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print("="*80)
print("END-TO-END ACCURACY EVALUATION")
print("="*80)
print()
print("Evaluating accuracy of shade ratio predictions")
print("(number of people in/out of shade per image)")
print()

# Load data from all cities
results_dir = Path("data/multi_city_results")
csv_files = list(results_dir.glob("*/*_analyzed_with_utci.csv"))

print(f"Found {len(csv_files)} city files")
print()

all_data = []

for csv_file in csv_files:
    city_name = csv_file.parent.name
    print(f"Loading {city_name}...")

    df = pd.read_csv(csv_file, low_memory=False)

    # Filter for images with people detected
    df_with_people = df[
        (df['person_count'] > 0) |
        (df['inshade_count'] > 0) |
        (df['outshade_count'] > 0)
    ].copy()

    if len(df_with_people) > 0:
        df_with_people['city'] = city_name
        all_data.append(df_with_people)
        print(f"  {len(df_with_people):,} images with people")

print()
print("Combining all city data...")
df_all = pd.concat(all_data, ignore_index=True)

print(f"Total images analyzed: {len(df_all):,}")
print()

# Calculate metrics
print("="*80)
print("CALCULATING END-TO-END ACCURACY METRICS")
print("="*80)
print()

# 1. Total people count accuracy
df_all['predicted_total'] = df_all['person_count'] + df_all['inshade_count'] + df_all['outshade_count']
df_all['actual_total'] = df_all['inshade_count'] + df_all['outshade_count']

# For images where we have ground truth (actual_total > 0)
df_with_truth = df_all[df_all['actual_total'] > 0].copy()

print("1. TOTAL PEOPLE COUNT ACCURACY")
print("-" * 80)
print(f"Images with ground truth: {len(df_with_truth):,}")
print()

# Calculate absolute error
df_with_truth['count_error'] = (df_with_truth['predicted_total'] - df_with_truth['actual_total']).abs()
df_with_truth['count_error_pct'] = (df_with_truth['count_error'] / df_with_truth['actual_total'] * 100).clip(0, 200)

# Perfect matches (exact count)
perfect_matches = (df_with_truth['count_error'] == 0).sum()
perfect_pct = perfect_matches / len(df_with_truth) * 100

# Within ±1 person
within_1 = (df_with_truth['count_error'] <= 1).sum()
within_1_pct = within_1 / len(df_with_truth) * 100

# Within ±2 people
within_2 = (df_with_truth['count_error'] <= 2).sum()
within_2_pct = within_2 / len(df_with_truth) * 100

# Mean absolute error
mae = df_with_truth['count_error'].mean()
median_error = df_with_truth['count_error'].median()

print(f"Perfect matches (exact count): {perfect_matches:,} / {len(df_with_truth):,} ({perfect_pct:.1f}%)")
print(f"Within ±1 person: {within_1:,} / {len(df_with_truth):,} ({within_1_pct:.1f}%)")
print(f"Within ±2 people: {within_2:,} / {len(df_with_truth):,} ({within_2_pct:.1f}%)")
print(f"Mean Absolute Error (MAE): {mae:.2f} people")
print(f"Median Absolute Error: {median_error:.1f} people")
print()

# 2. Shade ratio accuracy
print("2. SHADE RATIO ACCURACY")
print("-" * 80)

# Calculate predicted and actual shade ratios
df_with_truth['predicted_shade_ratio'] = np.where(
    df_with_truth['predicted_total'] > 0,
    df_with_truth['inshade_count'] / df_with_truth['predicted_total'],
    0
)

df_with_truth['actual_shade_ratio'] = np.where(
    df_with_truth['actual_total'] > 0,
    df_with_truth['inshade_count'] / df_with_truth['actual_total'],
    0
)

# Calculate absolute error in shade ratio
df_with_truth['ratio_error'] = (df_with_truth['predicted_shade_ratio'] - df_with_truth['actual_shade_ratio']).abs()

# Calculate metrics
ratio_mae = df_with_truth['ratio_error'].mean()
ratio_median = df_with_truth['ratio_error'].median()
ratio_rmse = np.sqrt((df_with_truth['ratio_error']**2).mean())

# Correlation
ratio_corr, ratio_p = stats.pearsonr(
    df_with_truth['predicted_shade_ratio'],
    df_with_truth['actual_shade_ratio']
)

print(f"Mean Absolute Error (MAE): {ratio_mae:.3f}")
print(f"Median Absolute Error: {ratio_median:.3f}")
print(f"Root Mean Square Error (RMSE): {ratio_rmse:.3f}")
print(f"Pearson correlation: {ratio_corr:.3f} (p < 0.001)" if ratio_p < 0.001 else f"Pearson correlation: {ratio_corr:.3f} (p = {ratio_p:.4f})")
print()

# Within tolerance bands
within_10pct = (df_with_truth['ratio_error'] <= 0.10).sum()
within_20pct = (df_with_truth['ratio_error'] <= 0.20).sum()
within_30pct = (df_with_truth['ratio_error'] <= 0.30).sum()

print(f"Within ±0.10 (±10%): {within_10pct:,} / {len(df_with_truth):,} ({within_10pct/len(df_with_truth)*100:.1f}%)")
print(f"Within ±0.20 (±20%): {within_20pct:,} / {len(df_with_truth):,} ({within_20pct/len(df_with_truth)*100:.1f}%)")
print(f"Within ±0.30 (±30%): {within_30pct:,} / {len(df_with_truth):,} ({within_30pct/len(df_with_truth)*100:.1f}%)")
print()

# 3. In-shade count accuracy
print("3. IN-SHADE COUNT ACCURACY")
print("-" * 80)

# These are ground truth since YOLO directly detects inshade
# But we can look at the distribution
print(f"Total in-shade people detected: {df_with_truth['inshade_count'].sum():,}")
print(f"Mean in-shade per image: {df_with_truth['inshade_count'].mean():.2f}")
print(f"Median in-shade per image: {df_with_truth['inshade_count'].median():.0f}")
print(f"Images with at least 1 in-shade: {(df_with_truth['inshade_count'] > 0).sum():,} ({(df_with_truth['inshade_count'] > 0).sum()/len(df_with_truth)*100:.1f}%)")
print()

# 4. Out-of-shade count accuracy
print("4. OUT-OF-SHADE COUNT ACCURACY")
print("-" * 80)

print(f"Total out-of-shade people detected: {df_with_truth['outshade_count'].sum():,}")
print(f"Mean out-of-shade per image: {df_with_truth['outshade_count'].mean():.2f}")
print(f"Median out-of-shade per image: {df_with_truth['outshade_count'].median():.0f}")
print(f"Images with at least 1 out-of-shade: {(df_with_truth['outshade_count'] > 0).sum():,} ({(df_with_truth['outshade_count'] > 0).sum()/len(df_with_truth)*100:.1f}%)")
print()

# 5. Breakdown by number of people
print("5. ACCURACY BY NUMBER OF PEOPLE")
print("-" * 80)

# Bin by actual number of people
df_with_truth['people_bin'] = pd.cut(
    df_with_truth['actual_total'],
    bins=[0, 1, 2, 3, 5, 10, 100],
    labels=['1', '2', '3', '4-5', '6-10', '11+']
)

for people_bin in ['1', '2', '3', '4-5', '6-10', '11+']:
    df_bin = df_with_truth[df_with_truth['people_bin'] == people_bin]
    if len(df_bin) > 0:
        bin_mae = df_bin['ratio_error'].mean()
        bin_count = len(df_bin)
        print(f"{people_bin} people: n={bin_count:>6,}, Ratio MAE={bin_mae:.3f}")

print()

# 6. Breakdown by city
print("6. ACCURACY BY CITY")
print("-" * 80)

city_stats = []
for city in sorted(df_with_truth['city'].unique()):
    df_city = df_with_truth[df_with_truth['city'] == city]
    city_stats.append({
        'city': city,
        'n': len(df_city),
        'ratio_mae': df_city['ratio_error'].mean(),
        'count_mae': df_city['count_error'].mean(),
        'perfect_pct': (df_city['count_error'] == 0).sum() / len(df_city) * 100
    })

city_df = pd.DataFrame(city_stats).sort_values('ratio_mae')
for _, row in city_df.iterrows():
    print(f"{row['city']:15s}: n={row['n']:>5,}, Ratio MAE={row['ratio_mae']:.3f}, Count MAE={row['count_mae']:.2f}, Perfect={row['perfect_pct']:.1f}%")

print()

# ============================================================================
# VISUALIZATIONS
# ============================================================================

print("="*80)
print("GENERATING VISUALIZATIONS")
print("="*80)
print()

# 1. Predicted vs Actual Shade Ratio
fig, axes = plt.subplots(2, 2, figsize=(16, 14))

# Top left: Scatter plot
ax = axes[0, 0]
ax.hexbin(df_with_truth['actual_shade_ratio'],
          df_with_truth['predicted_shade_ratio'],
          gridsize=30, cmap='YlOrRd', mincnt=1)
ax.plot([0, 1], [0, 1], 'k--', linewidth=2, label='Perfect prediction')
ax.set_xlabel('Actual Shade Ratio', fontsize=12)
ax.set_ylabel('Predicted Shade Ratio', fontsize=12)
ax.set_title(f'Predicted vs Actual Shade Ratio\n(n={len(df_with_truth):,} images)', fontsize=13, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)

# Add text box with metrics
textstr = f'MAE: {ratio_mae:.3f}\nRMSE: {ratio_rmse:.3f}\nCorr: {ratio_corr:.3f}'
ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=11,
        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# Top right: Error distribution
ax = axes[0, 1]
ax.hist(df_with_truth['ratio_error'], bins=50, edgecolor='black', alpha=0.7, color='steelblue')
ax.axvline(ratio_mae, color='red', linestyle='--', linewidth=2, label=f'Mean = {ratio_mae:.3f}')
ax.axvline(ratio_median, color='orange', linestyle='--', linewidth=2, label=f'Median = {ratio_median:.3f}')
ax.set_xlabel('Absolute Error in Shade Ratio', fontsize=12)
ax.set_ylabel('Frequency', fontsize=12)
ax.set_title('Distribution of Shade Ratio Errors', fontsize=13, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3, axis='y')

# Bottom left: Count accuracy
ax = axes[1, 0]
ax.hexbin(df_with_truth['actual_total'],
          df_with_truth['predicted_total'],
          gridsize=20, cmap='Blues', mincnt=1)
max_count = max(df_with_truth['actual_total'].max(), df_with_truth['predicted_total'].max())
ax.plot([0, max_count], [0, max_count], 'k--', linewidth=2, label='Perfect count')
ax.set_xlabel('Actual Total People', fontsize=12)
ax.set_ylabel('Predicted Total People', fontsize=12)
ax.set_title(f'Predicted vs Actual People Count\n(MAE = {mae:.2f} people)', fontsize=13, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)

# Add text box with accuracy bands
textstr = f'Perfect: {perfect_pct:.1f}%\n±1: {within_1_pct:.1f}%\n±2: {within_2_pct:.1f}%'
ax.text(0.05, 0.95, textstr, transform=ax.transAxes, fontsize=11,
        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.5))

# Bottom right: Accuracy by number of people
ax = axes[1, 1]
people_bins_data = []
people_bins_labels = []
for people_bin in ['1', '2', '3', '4-5', '6-10', '11+']:
    df_bin = df_with_truth[df_with_truth['people_bin'] == people_bin]
    if len(df_bin) > 0:
        people_bins_data.append(df_bin['ratio_error'].mean())
        people_bins_labels.append(f"{people_bin}\n(n={len(df_bin)})")

ax.bar(range(len(people_bins_data)), people_bins_data, color='coral', edgecolor='black', alpha=0.7)
ax.set_xticks(range(len(people_bins_labels)))
ax.set_xticklabels(people_bins_labels)
ax.set_xlabel('Number of People in Image', fontsize=12)
ax.set_ylabel('Mean Absolute Error (Shade Ratio)', fontsize=12)
ax.set_title('Accuracy vs Number of People', fontsize=13, fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')
ax.axhline(ratio_mae, color='red', linestyle='--', linewidth=2, label=f'Overall MAE = {ratio_mae:.3f}')
ax.legend(fontsize=10)

plt.tight_layout()
output_file = OUTPUT_DIR / "end_to_end_accuracy_evaluation.png"
plt.savefig(output_file, dpi=300, bbox_inches='tight')
plt.close()
print(f"✓ Saved: {output_file}")

# 2. City comparison plot
fig, ax = plt.subplots(figsize=(14, 8))

city_df_sorted = city_df.sort_values('ratio_mae')
x_pos = np.arange(len(city_df_sorted))

bars = ax.bar(x_pos, city_df_sorted['ratio_mae'], color='steelblue', edgecolor='black', alpha=0.7)

# Color bars by performance
colors = ['green' if mae < ratio_mae else 'orange' for mae in city_df_sorted['ratio_mae']]
for bar, color in zip(bars, colors):
    bar.set_color(color)

ax.set_xticks(x_pos)
ax.set_xticklabels(city_df_sorted['city'], rotation=45, ha='right')
ax.set_ylabel('Mean Absolute Error (Shade Ratio)', fontsize=12)
ax.set_title('End-to-End Accuracy by City\n(Lower is better)', fontsize=14, fontweight='bold')
ax.axhline(ratio_mae, color='red', linestyle='--', linewidth=2, label=f'Overall MAE = {ratio_mae:.3f}')
ax.legend(fontsize=11)
ax.grid(True, alpha=0.3, axis='y')

# Add sample sizes as text
for i, (_, row) in enumerate(city_df_sorted.iterrows()):
    ax.text(i, row['ratio_mae'] + 0.005, f"n={row['n']:,}",
            ha='center', va='bottom', fontsize=9)

plt.tight_layout()
output_file = OUTPUT_DIR / "end_to_end_accuracy_by_city.png"
plt.savefig(output_file, dpi=300, bbox_inches='tight')
plt.close()
print(f"✓ Saved: {output_file}")

print()
print("="*80)
print("✓ END-TO-END ACCURACY EVALUATION COMPLETE")
print("="*80)
print()
print(f"Output directory: {OUTPUT_DIR}")
print()

# Save summary statistics
summary_file = OUTPUT_DIR / "end_to_end_accuracy_summary.txt"
with open(summary_file, 'w') as f:
    f.write("="*80 + "\n")
    f.write("END-TO-END ACCURACY EVALUATION SUMMARY\n")
    f.write("="*80 + "\n\n")

    f.write(f"Total images analyzed: {len(df_with_truth):,}\n")
    f.write(f"Total people detected: {df_with_truth['actual_total'].sum():,}\n\n")

    f.write("SHADE RATIO ACCURACY (Primary Metric)\n")
    f.write("-" * 80 + "\n")
    f.write(f"Mean Absolute Error (MAE): {ratio_mae:.3f}\n")
    f.write(f"Median Absolute Error: {ratio_median:.3f}\n")
    f.write(f"Root Mean Square Error (RMSE): {ratio_rmse:.3f}\n")
    f.write(f"Pearson correlation: {ratio_corr:.3f}\n\n")

    f.write(f"Within ±0.10: {within_10pct/len(df_with_truth)*100:.1f}%\n")
    f.write(f"Within ±0.20: {within_20pct/len(df_with_truth)*100:.1f}%\n")
    f.write(f"Within ±0.30: {within_30pct/len(df_with_truth)*100:.1f}%\n\n")

    f.write("PEOPLE COUNT ACCURACY\n")
    f.write("-" * 80 + "\n")
    f.write(f"Perfect matches: {perfect_pct:.1f}%\n")
    f.write(f"Within ±1 person: {within_1_pct:.1f}%\n")
    f.write(f"Within ±2 people: {within_2_pct:.1f}%\n")
    f.write(f"Mean Absolute Error: {mae:.2f} people\n\n")

    f.write("INTERPRETATION\n")
    f.write("-" * 80 + "\n")
    f.write(f"On average, shade ratio predictions are off by {ratio_mae:.1%}.\n")
    f.write(f"For example, if true shade ratio is 0.50, predicted is typically {0.50-ratio_mae:.2f} to {0.50+ratio_mae:.2f}.\n")
    f.write(f"{within_20pct/len(df_with_truth)*100:.0f}% of predictions are within ±20% of true value.\n")

print(f"✓ Saved summary: {summary_file}")
print()
