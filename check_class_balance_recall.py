#!/usr/bin/env python3
# ABOUTME: Check if YOLO recall is consistent across inshade/outshade classes
# ABOUTME: Critical assumption test for ratio estimator validity

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import warnings
warnings.filterwarnings('ignore')

print("="*80)
print("TESTING CLASS BALANCE ASSUMPTION")
print("="*80)
print()
print("Question: Does YOLO detect in-shade and out-of-shade people at similar rates?")
print("Critical for: Ratio estimator validity")
print()

# Load data from all cities
results_dir = Path("data/multi_city_results")
csv_files = list(results_dir.glob("*/*_analyzed_with_utci.csv"))

all_data = []
for csv_file in csv_files:
    city_name = csv_file.parent.name
    df = pd.read_csv(csv_file, low_memory=False)
    df['city'] = city_name
    all_data.append(df)

df_all = pd.concat(all_data, ignore_index=True)

print(f"Loaded {len(df_all):,} total images from {len(csv_files)} cities")
print()

# ============================================================================
# 1. DETECTION RATES BY CLASS
# ============================================================================

print("="*80)
print("1. DETECTION RATES: Images with at least one person detected")
print("="*80)
print()

# Images with any detection
has_person = df_all['person_count'] > 0
has_inshade = df_all['inshade_count'] > 0
has_outshade = df_all['outshade_count'] > 0
has_any = (df_all['person_count'] + df_all['inshade_count'] + df_all['outshade_count']) > 0

print(f"Images with person class detected: {has_person.sum():,} / {len(df_all):,} ({has_person.sum()/len(df_all)*100:.1f}%)")
print(f"Images with inshade detected: {has_inshade.sum():,} / {len(df_all):,} ({has_inshade.sum()/len(df_all)*100:.1f}%)")
print(f"Images with outshade detected: {has_outshade.sum():,} / {len(df_all):,} ({has_outshade.sum()/len(df_all)*100:.1f}%)")
print(f"Images with any people detected: {has_any.sum():,} / {len(df_all):,} ({has_any.sum()/len(df_all)*100:.1f}%)")
print()

# ============================================================================
# 2. CONDITIONAL DETECTION RATES
# ============================================================================

print("="*80)
print("2. CONDITIONAL DETECTION: Given people are present")
print("="*80)
print()

# Filter to images with people
df_with_people = df_all[has_any].copy()
print(f"Analyzing {len(df_with_people):,} images with detected people")
print()

# Calculate totals
total_inshade = df_with_people['inshade_count'].sum()
total_outshade = df_with_people['outshade_count'].sum()
total_people = total_inshade + total_outshade

print(f"Total in-shade people: {total_inshade:,.0f}")
print(f"Total out-of-shade people: {total_outshade:,.0f}")
print(f"Total people: {total_people:,.0f}")
print()

print(f"In-shade proportion: {total_inshade/total_people:.3f} ({total_inshade/total_people*100:.1f}%)")
print(f"Out-of-shade proportion: {total_outshade/total_people:.3f} ({total_outshade/total_people*100:.1f}%)")
print()

# ============================================================================
# 3. IMAGES WITH PEOPLE: Which class appears?
# ============================================================================

print("="*80)
print("3. WITHIN-IMAGE CLASS PATTERNS")
print("="*80)
print()

# Among images with people, how many have each class?
has_inshade_with_people = df_with_people['inshade_count'] > 0
has_outshade_with_people = df_with_people['outshade_count'] > 0
has_both = has_inshade_with_people & has_outshade_with_people
has_only_inshade = has_inshade_with_people & ~has_outshade_with_people
has_only_outshade = has_outshade_with_people & ~has_inshade_with_people

print(f"Images with only in-shade: {has_only_inshade.sum():,} ({has_only_inshade.sum()/len(df_with_people)*100:.1f}%)")
print(f"Images with only out-shade: {has_only_outshade.sum():,} ({has_only_outshade.sum()/len(df_with_people)*100:.1f}%)")
print(f"Images with both: {has_both.sum():,} ({has_both.sum()/len(df_with_people)*100:.1f}%)")
print()

# This is the key test!
inshade_detection_rate = has_inshade_with_people.sum() / len(df_with_people)
outshade_detection_rate = has_outshade_with_people.sum() / len(df_with_people)

print(f"In-shade detection rate (images with ≥1): {inshade_detection_rate:.3f} ({inshade_detection_rate*100:.1f}%)")
print(f"Out-shade detection rate (images with ≥1): {outshade_detection_rate:.3f} ({outshade_detection_rate*100:.1f}%)")
print(f"Difference: {abs(inshade_detection_rate - outshade_detection_rate):.3f} ({abs(inshade_detection_rate - outshade_detection_rate)*100:.1f}%)")
print()

if abs(inshade_detection_rate - outshade_detection_rate) < 0.05:
    print("✓ SIMILAR detection rates (< 5% difference) - ratio estimator assumption VALID")
elif abs(inshade_detection_rate - outshade_detection_rate) < 0.10:
    print("⚠ MODERATE difference (5-10%) - may introduce small bias")
else:
    print("✗ LARGE difference (> 10%) - ratio estimator assumption VIOLATED")
print()

# ============================================================================
# 4. AVERAGE COUNTS PER IMAGE
# ============================================================================

print("="*80)
print("4. AVERAGE COUNTS PER IMAGE (when detected)")
print("="*80)
print()

# Among images with that class, what's the average count?
df_has_inshade = df_with_people[has_inshade_with_people]
df_has_outshade = df_with_people[has_outshade_with_people]

avg_inshade_per_image = df_has_inshade['inshade_count'].mean()
avg_outshade_per_image = df_has_outshade['outshade_count'].mean()

print(f"Average in-shade count per image (with in-shade): {avg_inshade_per_image:.2f}")
print(f"Average out-shade count per image (with out-shade): {avg_outshade_per_image:.2f}")
print(f"Ratio: {avg_inshade_per_image / avg_outshade_per_image:.3f}")
print()

# ============================================================================
# 5. ANALYSIS BY CITY
# ============================================================================

print("="*80)
print("5. CLASS BALANCE BY CITY")
print("="*80)
print()

city_stats = []
for city in sorted(df_with_people['city'].unique()):
    df_city = df_with_people[df_with_people['city'] == city]

    city_inshade = df_city['inshade_count'].sum()
    city_outshade = df_city['outshade_count'].sum()
    city_total = city_inshade + city_outshade

    city_inshade_rate = (df_city['inshade_count'] > 0).sum() / len(df_city)
    city_outshade_rate = (df_city['outshade_count'] > 0).sum() / len(df_city)

    city_stats.append({
        'city': city,
        'n_images': len(df_city),
        'inshade_total': city_inshade,
        'outshade_total': city_outshade,
        'inshade_pct': city_inshade / city_total,
        'inshade_detection_rate': city_inshade_rate,
        'outshade_detection_rate': city_outshade_rate,
        'detection_diff': abs(city_inshade_rate - city_outshade_rate)
    })

city_df = pd.DataFrame(city_stats).sort_values('detection_diff')

print(f"{'City':<15} {'Images':>8} {'In%':>6} {'In-Rate':>8} {'Out-Rate':>8} {'Diff':>6}")
print("-" * 70)
for _, row in city_df.iterrows():
    print(f"{row['city']:<15} {row['n_images']:>8,} {row['inshade_pct']*100:>5.1f}% "
          f"{row['inshade_detection_rate']:>8.3f} {row['outshade_detection_rate']:>8.3f} "
          f"{row['detection_diff']:>6.3f}")

print()
print(f"Mean detection difference across cities: {city_df['detection_diff'].mean():.3f}")
print(f"Max detection difference across cities: {city_df['detection_diff'].max():.3f}")
print()

# ============================================================================
# 6. VISUAL CONTRAST HYPOTHESIS
# ============================================================================

print("="*80)
print("6. TESTING VISUAL CONTRAST HYPOTHESIS")
print("="*80)
print()
print("Hypothesis: People in sun have higher contrast → easier to detect")
print()

# Test: In sunny images, is out-shade detected more often?
df_sunny = df_all[df_all['is_sunny'] == True].copy()
df_sunny_people = df_sunny[(df_sunny['inshade_count'] + df_sunny['outshade_count']) > 0]

if len(df_sunny_people) > 0:
    sunny_inshade_rate = (df_sunny_people['inshade_count'] > 0).sum() / len(df_sunny_people)
    sunny_outshade_rate = (df_sunny_people['outshade_count'] > 0).sum() / len(df_sunny_people)

    print(f"Sunny images with people: {len(df_sunny_people):,}")
    print(f"In-shade detection rate: {sunny_inshade_rate:.3f} ({sunny_inshade_rate*100:.1f}%)")
    print(f"Out-shade detection rate: {sunny_outshade_rate:.3f} ({sunny_outshade_rate*100:.1f}%)")
    print(f"Difference: {abs(sunny_inshade_rate - sunny_outshade_rate):.3f}")
    print()

    if sunny_outshade_rate > sunny_inshade_rate + 0.05:
        print("⚠ WARNING: Out-shade detected MORE often in sunny images")
        print("   This could bias shade ratios DOWNWARD (underestimate shade-seeking)")
    elif sunny_inshade_rate > sunny_outshade_rate + 0.05:
        print("⚠ WARNING: In-shade detected MORE often in sunny images")
        print("   This could bias shade ratios UPWARD (overestimate shade-seeking)")
    else:
        print("✓ Similar detection rates - no strong visual contrast bias")

print()

# ============================================================================
# 7. POTENTIAL BIAS CALCULATION
# ============================================================================

print("="*80)
print("7. ESTIMATED BIAS FROM DIFFERENTIAL DETECTION")
print("="*80)
print()

# If detection rates differ, how much does this bias the ratio?
p_inshade = inshade_detection_rate
p_outshade = outshade_detection_rate

# True ratio (unknown, assume 0.50 for example)
true_ratio_assumed = 0.50

# Observed ratio if detection differs
observed_ratio = (true_ratio_assumed * p_inshade) / (true_ratio_assumed * p_inshade + (1 - true_ratio_assumed) * p_outshade)

bias = observed_ratio - true_ratio_assumed

print(f"Assuming true shade ratio = {true_ratio_assumed:.2f}")
print(f"In-shade detection probability = {p_inshade:.3f}")
print(f"Out-shade detection probability = {p_outshade:.3f}")
print()
print(f"Observed ratio (with differential detection) = {observed_ratio:.3f}")
print(f"Bias = {bias:.3f} ({bias/true_ratio_assumed*100:.1f}% relative bias)")
print()

if abs(bias) < 0.02:
    print("✓ Bias < 2% - NEGLIGIBLE for practical purposes")
elif abs(bias) < 0.05:
    print("⚠ Bias 2-5% - SMALL but worth noting")
else:
    print("✗ Bias > 5% - SIGNIFICANT bias that should be corrected")

print()

# ============================================================================
# 8. VISUALIZATION
# ============================================================================

print("="*80)
print("8. GENERATING VISUALIZATIONS")
print("="*80)
print()

fig, axes = plt.subplots(2, 2, figsize=(14, 12))

# Plot 1: Detection rates by city
ax = axes[0, 0]
x = np.arange(len(city_df))
width = 0.35
ax.bar(x - width/2, city_df['inshade_detection_rate'], width, label='In-shade', alpha=0.8, color='green')
ax.bar(x + width/2, city_df['outshade_detection_rate'], width, label='Out-shade', alpha=0.8, color='red')
ax.set_xticks(x)
ax.set_xticklabels(city_df['city'], rotation=45, ha='right')
ax.set_ylabel('Detection Rate (images with ≥1)', fontsize=11)
ax.set_title('Detection Rates by City', fontsize=12, fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3, axis='y')
ax.axhline(inshade_detection_rate, color='green', linestyle='--', alpha=0.5, label='Overall in-shade')
ax.axhline(outshade_detection_rate, color='red', linestyle='--', alpha=0.5, label='Overall out-shade')

# Plot 2: Class proportions by city
ax = axes[0, 1]
ax.barh(city_df['city'], city_df['inshade_pct']*100, color='green', alpha=0.7)
ax.set_xlabel('In-shade Proportion (%)', fontsize=11)
ax.set_title('In-shade Proportion by City', fontsize=12, fontweight='bold')
ax.axvline(50, color='black', linestyle='--', alpha=0.5, label='50%')
ax.grid(True, alpha=0.3, axis='x')
ax.legend()

# Plot 3: Detection difference by city
ax = axes[1, 0]
colors = ['green' if diff < 0.05 else 'orange' if diff < 0.10 else 'red' for diff in city_df['detection_diff']]
ax.bar(city_df['city'], city_df['detection_diff']*100, color=colors, alpha=0.7, edgecolor='black')
ax.set_xticklabels(city_df['city'], rotation=45, ha='right')
ax.set_ylabel('Absolute Detection Rate Difference (%)', fontsize=11)
ax.set_title('Detection Rate Difference (In-shade vs Out-shade)', fontsize=12, fontweight='bold')
ax.axhline(5, color='orange', linestyle='--', alpha=0.5, label='5% threshold')
ax.axhline(10, color='red', linestyle='--', alpha=0.5, label='10% threshold')
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

# Plot 4: Total counts
ax = axes[1, 1]
totals = pd.DataFrame({
    'In-shade': [total_inshade],
    'Out-shade': [total_outshade]
})
totals.T.plot(kind='bar', ax=ax, legend=False, color=['green', 'red'], alpha=0.7, edgecolor='black')
ax.set_xticklabels(['In-shade', 'Out-shade'], rotation=0)
ax.set_ylabel('Total People Detected', fontsize=11)
ax.set_title(f'Total People Detected\n(n={total_people:,.0f})', fontsize=12, fontweight='bold')
ax.grid(True, alpha=0.3, axis='y')

# Add text annotations
ax.text(0, total_inshade, f'{total_inshade:,.0f}\n({total_inshade/total_people*100:.1f}%)',
        ha='center', va='bottom', fontsize=10, fontweight='bold')
ax.text(1, total_outshade, f'{total_outshade:,.0f}\n({total_outshade/total_people*100:.1f}%)',
        ha='center', va='bottom', fontsize=10, fontweight='bold')

plt.tight_layout()
output_file = Path("outputs/model_evaluation/class_balance_analysis.png")
plt.savefig(output_file, dpi=300, bbox_inches='tight')
plt.close()

print(f"✓ Saved: {output_file}")
print()

# ============================================================================
# SUMMARY AND CONCLUSION
# ============================================================================

print("="*80)
print("CONCLUSION")
print("="*80)
print()

print(f"Key Findings:")
print(f"1. In-shade detection rate: {inshade_detection_rate*100:.1f}%")
print(f"2. Out-shade detection rate: {outshade_detection_rate*100:.1f}%")
print(f"3. Difference: {abs(inshade_detection_rate - outshade_detection_rate)*100:.1f}%")
print()

if abs(inshade_detection_rate - outshade_detection_rate) < 0.05:
    print("✓ CONCLUSION: Ratio estimator assumption IS VALID")
    print("  Detection rates are similar (< 5% difference)")
    print("  Estimated bias from differential detection: < 2%")
    print("  Safe to use ratio-based metrics")
elif abs(inshade_detection_rate - outshade_detection_rate) < 0.10:
    print("⚠ CONCLUSION: Ratio estimator assumption MOSTLY VALID")
    print("  Detection rates differ moderately (5-10%)")
    print("  Estimated bias from differential detection: 2-5%")
    print("  Ratio-based metrics still usable with caution")
else:
    print("✗ CONCLUSION: Ratio estimator assumption VIOLATED")
    print("  Detection rates differ substantially (> 10%)")
    print("  Estimated bias from differential detection: > 5%")
    print("  Should correct for differential detection or use alternative methods")

print()
print("="*80)
