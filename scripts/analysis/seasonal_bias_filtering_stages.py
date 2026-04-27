#!/usr/bin/env python3
"""
Analyze seasonal bias at each stage of data filtering.
Shows how seasonal distribution changes from raw data to final filtered data.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Paths
ROOT = Path(__file__).resolve().parents[2]
METRO_DATA_DIR = ROOT / 'data/metro_commute_svi_with_shadow'
STATE_COLLEGE_FILE = ROOT / 'data/state-college/state-college_svi_with_shadow.csv'
OUTPUT_DIR = ROOT / 'outputs/analysis'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Filtering criteria
SR_MIN = 0.10

# Cities to analyze
ALL_CITIES = ['state-college', 'denver', 'st.-louis', 'salt-lake-city', 'minneapolis',
              'louisville', 'columbia', 'boise']

def load_city_data(city_name):
    """Load city data (all stages)."""
    if city_name == 'state-college':
        df = pd.read_csv(STATE_COLLEGE_FILE, low_memory=False)
    else:
        city_file = METRO_DATA_DIR / city_name / f'{city_name}_svi_with_shadow.csv'
        df = pd.read_csv(city_file, low_memory=False)

    df['city'] = city_name
    df['datetime-local'] = pd.to_datetime(df['datetime-local'])

    # Add season
    df['season'] = pd.cut(
        df['datetime-local'].dt.month,
        bins=[0, 3, 6, 9, 12],
        labels=['Winter', 'Spring', 'Summer', 'Fall']
    )

    # Calculate total people
    df['total_people'] = df['inshade_count'] + df['outshade_count']

    return df

def analyze_filtering_stages(df, city_name):
    """Analyze seasonal distribution at each filtering stage."""
    results = []

    # Stage 0: Raw data (all images)
    stage_0 = df.copy()
    results.append({
        'city': city_name,
        'stage': '0_raw',
        'stage_name': 'Raw Data',
        'n_total': len(stage_0),
        **get_seasonal_stats(stage_0)
    })

    # Stage 1: Has UTCI data
    stage_1 = df[df['utci_C'].notna()].copy()
    results.append({
        'city': city_name,
        'stage': '1_utci',
        'stage_name': 'Has UTCI',
        'n_total': len(stage_1),
        **get_seasonal_stats(stage_1)
    })

    # Stage 2: Has people (> 0)
    stage_2 = df[(df['total_people'] > 0) & df['utci_C'].notna()].copy()
    results.append({
        'city': city_name,
        'stage': '2_people',
        'stage_name': 'Has People',
        'n_total': len(stage_2),
        **get_seasonal_stats(stage_2)
    })

    # Stage 3: Has shadow data (sun above horizon)
    stage_3 = df[
        (df['total_people'] > 0) &
        df['utci_C'].notna() &
        df['shadow_ratio'].notna() &
        df['dist_to_shade_m'].notna()
    ].copy()
    results.append({
        'city': city_name,
        'stage': '3_shadow',
        'stage_name': 'Has Shadow Data',
        'n_total': len(stage_3),
        **get_seasonal_stats(stage_3)
    })

    # Stage 4: Shadow ratio filter (SR >= 0.10)
    stage_4 = df[
        (df['total_people'] > 0) &
        df['utci_C'].notna() &
        df['shadow_ratio'].notna() &
        df['dist_to_shade_m'].notna() &
        (df['shadow_ratio'] >= SR_MIN)
    ].copy()
    results.append({
        'city': city_name,
        'stage': '4_sr_filter',
        'stage_name': 'SR ≥ 0.10 (Final)',
        'n_total': len(stage_4),
        **get_seasonal_stats(stage_4)
    })

    return results

def get_seasonal_stats(df):
    """Get seasonal distribution statistics."""
    if len(df) == 0:
        return {
            'n_winter': 0, 'n_spring': 0, 'n_summer': 0, 'n_fall': 0,
            'pct_winter': 0, 'pct_spring': 0, 'pct_summer': 0, 'pct_fall': 0,
            'dominant_season': None,
            'dominant_pct': 0,
            'season_balance_std': 0
        }

    season_counts = df.groupby('season', observed=True).size()

    stats = {}
    for season in ['Winter', 'Spring', 'Summer', 'Fall']:
        n = season_counts.get(season, 0)
        pct = (n / len(df)) * 100
        stats[f'n_{season.lower()}'] = n
        stats[f'pct_{season.lower()}'] = pct

    # Dominant season
    if len(season_counts) > 0:
        stats['dominant_season'] = season_counts.idxmax()
        stats['dominant_pct'] = (season_counts.max() / len(df)) * 100
    else:
        stats['dominant_season'] = None
        stats['dominant_pct'] = 0

    # Season balance (std of percentages)
    pcts = [stats[f'pct_{s.lower()}'] for s in ['Winter', 'Spring', 'Summer', 'Fall']]
    stats['season_balance_std'] = np.std([p for p in pcts if p > 0])

    return stats

# Main analysis
print("Analyzing seasonal bias across filtering stages...\n")

all_results = []
for city in ALL_CITIES:
    print(f"Processing {city}...")
    df = load_city_data(city)
    city_results = analyze_filtering_stages(df, city)
    all_results.extend(city_results)

# Create DataFrame
df_results = pd.DataFrame(all_results)

# Save results
df_results.to_csv(OUTPUT_DIR / 'seasonal_bias_filtering_stages.csv', index=False)
print(f"\nSaved: {OUTPUT_DIR / 'seasonal_bias_filtering_stages.csv'}")

# Print summary for each city
print("\n" + "="*100)
print("SEASONAL BIAS ACROSS FILTERING STAGES")
print("="*100)

for city in ALL_CITIES:
    city_data = df_results[df_results['city'] == city]

    print(f"\n{city.upper()}:")
    print("-" * 100)
    print(f"{'Stage':<25} {'N':<10} {'Winter':>8} {'Spring':>8} {'Summer':>8} {'Fall':>8} {'Dominant':>12} {'Balance':>8}")
    print("-" * 100)

    for _, row in city_data.iterrows():
        print(f"{row['stage_name']:<25} {row['n_total']:<10,} "
              f"{row['pct_winter']:>7.1f}% {row['pct_spring']:>7.1f}% "
              f"{row['pct_summer']:>7.1f}% {row['pct_fall']:>7.1f}% "
              f"{row['dominant_pct']:>11.1f}% {row['season_balance_std']:>8.1f}")

# Visualization
print("\nCreating visualizations...")

# Select key cities for detailed visualization
key_cities = ['state-college', 'denver', 'st.-louis', 'columbia']

fig, axes = plt.subplots(len(key_cities), 1, figsize=(14, 4*len(key_cities)))
if len(key_cities) == 1:
    axes = [axes]

for idx, city in enumerate(key_cities):
    ax = axes[idx]
    city_data = df_results[df_results['city'] == city]

    stages = city_data['stage_name'].values
    winter = city_data['pct_winter'].values
    spring = city_data['pct_spring'].values
    summer = city_data['pct_summer'].values
    fall = city_data['pct_fall'].values

    x = np.arange(len(stages))
    width = 0.2

    ax.bar(x - 1.5*width, winter, width, label='Winter', color='#3498DB', alpha=0.8)
    ax.bar(x - 0.5*width, spring, width, label='Spring', color='#2ECC71', alpha=0.8)
    ax.bar(x + 0.5*width, summer, width, label='Summer', color='#E74C3C', alpha=0.8)
    ax.bar(x + 1.5*width, fall, width, label='Fall', color='#F39C12', alpha=0.8)

    ax.axhline(25, color='black', linestyle='--', alpha=0.5, linewidth=1)

    ax.set_xlabel('Filtering Stage', fontweight='bold', fontsize=11)
    ax.set_ylabel('Percentage of Data (%)', fontweight='bold', fontsize=11)
    ax.set_title(f'{city.title().replace("-", " ")} - Seasonal Distribution Across Filtering Stages',
                 fontweight='bold', fontsize=13)
    ax.set_xticks(x)
    ax.set_xticklabels(stages, rotation=20, ha='right')
    ax.legend(loc='upper right')
    ax.grid(True, alpha=0.3, axis='y')
    ax.set_ylim(0, 105)

    # Add sample sizes
    for i, (stage, n) in enumerate(zip(stages, city_data['n_total'].values)):
        ax.text(i, 102, f'n={n:,}', ha='center', va='bottom', fontsize=8, rotation=0)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'seasonal_bias_by_stage_detailed.png', dpi=300, bbox_inches='tight')
print(f"Saved: {OUTPUT_DIR / 'seasonal_bias_by_stage_detailed.png'}")

# Summary visualization: Dominant season % across stages
fig, ax = plt.subplots(figsize=(14, 8))

for city in ALL_CITIES:
    city_data = df_results[df_results['city'] == city].sort_values('stage')
    stages = city_data['stage_name'].values
    dominant_pcts = city_data['dominant_pct'].values

    # Different styles for U-shaped vs flat cities
    if city in ['state-college', 'denver']:
        linestyle = '-'
        linewidth = 2.5
        marker = 'o'
        markersize = 8
        alpha = 1.0
        label = f'{city} (U-shaped)'
    else:
        linestyle = '--'
        linewidth = 1.5
        marker = 's'
        markersize = 6
        alpha = 0.7
        label = f'{city} (Flat)'

    ax.plot(stages, dominant_pcts, marker=marker, linestyle=linestyle,
            linewidth=linewidth, markersize=markersize, alpha=alpha, label=label)

ax.axhline(70, color='red', linestyle='--', alpha=0.5, linewidth=2, label='70% threshold (severe imbalance)')
ax.axhline(60, color='orange', linestyle='--', alpha=0.5, linewidth=2, label='60% threshold (moderate)')
ax.axhline(25, color='green', linestyle='--', alpha=0.5, linewidth=1, label='25% (perfect balance)')

ax.set_xlabel('Filtering Stage', fontweight='bold', fontsize=12)
ax.set_ylabel('Dominant Season Percentage (%)', fontweight='bold', fontsize=12)
ax.set_title('Evolution of Seasonal Imbalance Through Filtering Stages',
             fontweight='bold', fontsize=14)
ax.set_xticklabels(stages, rotation=20, ha='right')
ax.legend(loc='upper left', fontsize=9, ncol=2)
ax.grid(True, alpha=0.3)
ax.set_ylim(20, 105)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'seasonal_imbalance_evolution.png', dpi=300, bbox_inches='tight')
print(f"Saved: {OUTPUT_DIR / 'seasonal_imbalance_evolution.png'}")

# Calculate change in imbalance from raw to final
print("\n" + "="*100)
print("CHANGE IN SEASONAL IMBALANCE (Raw Data → Final Filtered)")
print("="*100)
print(f"{'City':<20} {'Raw Dom %':>12} {'Final Dom %':>12} {'Change':>12} {'Interpretation':<40}")
print("-" * 100)

for city in ALL_CITIES:
    city_data = df_results[df_results['city'] == city]
    raw_dom = city_data[city_data['stage'] == '0_raw']['dominant_pct'].values[0]
    final_dom = city_data[city_data['stage'] == '4_sr_filter']['dominant_pct'].values[0]
    change = final_dom - raw_dom

    if abs(change) < 5:
        interpretation = "Minimal change - bias inherent in raw data"
    elif change > 15:
        interpretation = "Large increase - filtering amplifies bias"
    elif change > 5:
        interpretation = "Moderate increase - filtering contributes"
    elif change < -5:
        interpretation = "Filtering reduces imbalance (unusual)"
    else:
        interpretation = "Slight change"

    print(f"{city:<20} {raw_dom:>11.1f}% {final_dom:>11.1f}% {change:>+11.1f}% {interpretation:<40}")

print("\n" + "="*100)
print("Analysis complete!")
print("="*100)
