#!/usr/bin/env python3
"""
Investigate differences between cities with U-shaped vs flat/decreasing shade preference curves.
"""

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Paths
ROOT = Path(__file__).resolve().parents[2]
METRO_DATA_DIR = ROOT / 'data/metro_commute_svi_with_shadow'
STATE_COLLEGE_FILE = ROOT / 'data/state-college/state-college_svi_with_shadow.csv'
OUTPUT_DIR = ROOT / 'outputs/analysis'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Cities to analyze
CITIES_WITH_U_SHAPE = ['denver']  # Will add state_college
CITIES_WITH_FLAT_DECREASING = ['st.-louis', 'salt-lake-city', 'minneapolis', 'louisville', 'columbia', 'boise']

SR_MIN = 0.10

def load_and_filter_city(city_name, is_state_college=False):
    """Load and filter city data."""
    if is_state_college:
        df = pd.read_csv(STATE_COLLEGE_FILE, low_memory=False)
        df['city'] = 'state_college'
    else:
        city_file = METRO_DATA_DIR / city_name / f'{city_name}_svi_with_shadow.csv'
        df = pd.read_csv(city_file, low_memory=False)
        df['city'] = city_name

    # Filter
    df['datetime-local'] = pd.to_datetime(df['datetime-local'])
    df['total_people'] = df['inshade_count'] + df['outshade_count']

    mask = (
        (df['total_people'] > 0) &
        df['utci_C'].notna() &
        df['shadow_ratio'].notna() &
        df['dist_to_shade_m'].notna() &
        (df['shadow_ratio'] >= SR_MIN)
    )
    df = df[mask].copy()

    # Add season
    df['season'] = pd.cut(
        df['datetime-local'].dt.month,
        bins=[0, 3, 6, 9, 12],
        labels=['Winter', 'Spring', 'Summer', 'Fall']
    )
    df['year'] = df['datetime-local'].dt.year

    return df

def analyze_city(df, city_name):
    """Compute summary statistics for a city."""
    stats = {
        'city': city_name,
        'n_total': len(df),
        'n_people_total': df['total_people'].sum(),
        'utci_min': df['utci_C'].min(),
        'utci_max': df['utci_C'].max(),
        'utci_mean': df['utci_C'].mean(),
        'utci_std': df['utci_C'].std(),
        'utci_range': df['utci_C'].max() - df['utci_C'].min(),
    }

    # Seasonal distribution
    season_counts = df.groupby('season').size()
    for season in ['Winter', 'Spring', 'Summer', 'Fall']:
        stats[f'n_{season.lower()}'] = season_counts.get(season, 0)
        stats[f'pct_{season.lower()}'] = (season_counts.get(season, 0) / len(df)) * 100

    # UTCI range by season
    for season in ['Winter', 'Spring', 'Summer', 'Fall']:
        season_df = df[df['season'] == season]
        if len(season_df) > 0:
            stats[f'utci_min_{season.lower()}'] = season_df['utci_C'].min()
            stats[f'utci_max_{season.lower()}'] = season_df['utci_C'].max()
            stats[f'utci_mean_{season.lower()}'] = season_df['utci_C'].mean()
        else:
            stats[f'utci_min_{season.lower()}'] = np.nan
            stats[f'utci_max_{season.lower()}'] = np.nan
            stats[f'utci_mean_{season.lower()}'] = np.nan

    # Temperature extremes
    stats['has_cold_temps'] = (df['utci_C'].min() < -20)
    stats['has_hot_temps'] = (df['utci_C'].max() > 35)
    stats['temp_balanced'] = stats['has_cold_temps'] and stats['has_hot_temps']

    # Seasonal balance
    season_pcts = [stats[f'pct_{s.lower()}'] for s in ['Winter', 'Spring', 'Summer', 'Fall']]
    stats['season_balance_std'] = np.std([p for p in season_pcts if p > 0])
    stats['dominant_season'] = df.groupby('season').size().idxmax()
    stats['dominant_season_pct'] = df.groupby('season').size().max() / len(df) * 100

    return stats

# Load all cities
print("Loading data...")
all_cities = []

# State College (U-shaped)
print("  Loading State College...")
df_sc = load_and_filter_city('state_college', is_state_college=True)
stats_sc = analyze_city(df_sc, 'state_college')
stats_sc['curve_type'] = 'U-shaped'
all_cities.append(stats_sc)

# Denver (U-shaped)
print("  Loading Denver...")
df_denver = load_and_filter_city('denver')
stats_denver = analyze_city(df_denver, 'denver')
stats_denver['curve_type'] = 'U-shaped'
all_cities.append(stats_denver)

# Flat/decreasing cities
for city in CITIES_WITH_FLAT_DECREASING:
    print(f"  Loading {city}...")
    df_city = load_and_filter_city(city)
    if len(df_city) >= 100:  # Only analyze if sufficient data
        stats_city = analyze_city(df_city, city)
        stats_city['curve_type'] = 'Flat/Decreasing'
        all_cities.append(stats_city)

# Create DataFrame
df_summary = pd.DataFrame(all_cities)

# Save summary
print("\nSaving summary statistics...")
df_summary.to_csv(OUTPUT_DIR / 'curve_pattern_analysis.csv', index=False)

# Print comparison
print("\n" + "="*80)
print("COMPARISON: U-SHAPED vs FLAT/DECREASING CURVES")
print("="*80)

u_shaped = df_summary[df_summary['curve_type'] == 'U-shaped']
flat = df_summary[df_summary['curve_type'] == 'Flat/Decreasing']

print("\n--- TEMPERATURE CHARACTERISTICS ---")
print(f"\nU-shaped cities (n={len(u_shaped)}):")
print(f"  UTCI range: {u_shaped['utci_range'].mean():.1f}°C (± {u_shaped['utci_range'].std():.1f})")
print(f"  UTCI min: {u_shaped['utci_min'].mean():.1f}°C")
print(f"  UTCI max: {u_shaped['utci_max'].mean():.1f}°C")
print(f"  Has cold temps (<-20°C): {u_shaped['has_cold_temps'].sum()}/{len(u_shaped)}")
print(f"  Has hot temps (>35°C): {u_shaped['has_hot_temps'].sum()}/{len(u_shaped)}")
print(f"  Temperature balanced: {u_shaped['temp_balanced'].sum()}/{len(u_shaped)}")

print(f"\nFlat/decreasing cities (n={len(flat)}):")
print(f"  UTCI range: {flat['utci_range'].mean():.1f}°C (± {flat['utci_range'].std():.1f})")
print(f"  UTCI min: {flat['utci_min'].mean():.1f}°C")
print(f"  UTCI max: {flat['utci_max'].mean():.1f}°C")
print(f"  Has cold temps (<-20°C): {flat['has_cold_temps'].sum()}/{len(flat)}")
print(f"  Has hot temps (>35°C): {flat['has_hot_temps'].sum()}/{len(flat)}")
print(f"  Temperature balanced: {flat['temp_balanced'].sum()}/{len(flat)}")

print("\n--- SEASONAL DISTRIBUTION ---")
print(f"\nU-shaped cities:")
for season in ['Winter', 'Spring', 'Summer', 'Fall']:
    print(f"  {season}: {u_shaped[f'pct_{season.lower()}'].mean():.1f}% (± {u_shaped[f'pct_{season.lower()}'].std():.1f})")
print(f"  Dominant season %: {u_shaped['dominant_season_pct'].mean():.1f}%")
print(f"  Season balance (std): {u_shaped['season_balance_std'].mean():.1f}")

print(f"\nFlat/decreasing cities:")
for season in ['Winter', 'Spring', 'Summer', 'Fall']:
    mean_pct = flat[f'pct_{season.lower()}'].mean()
    std_pct = flat[f'pct_{season.lower()}'].std()
    print(f"  {season}: {mean_pct:.1f}% (± {std_pct:.1f})")
print(f"  Dominant season %: {flat['dominant_season_pct'].mean():.1f}%")
print(f"  Season balance (std): {flat['season_balance_std'].mean():.1f}")

print("\n--- INDIVIDUAL CITY DETAILS ---")
for _, row in df_summary.iterrows():
    print(f"\n{row['city'].upper()} ({row['curve_type']}):")
    print(f"  n={row['n_total']:,}, UTCI: {row['utci_min']:.1f} to {row['utci_max']:.1f}°C")
    print(f"  Seasons: W={row['pct_winter']:.1f}%, Sp={row['pct_spring']:.1f}%, Su={row['pct_summer']:.1f}%, F={row['pct_fall']:.1f}%")
    print(f"  Dominant: {row['dominant_season']} ({row['dominant_season_pct']:.1f}%)")

# Create visualization
print("\nCreating visualizations...")

fig, axes = plt.subplots(2, 3, figsize=(18, 10))

# 1. UTCI range comparison
ax = axes[0, 0]
cities_u = u_shaped['city'].tolist()
cities_f = flat['city'].tolist()
ranges_u = u_shaped['utci_range'].tolist()
ranges_f = flat['utci_range'].tolist()

positions_u = np.arange(len(cities_u))
positions_f = np.arange(len(cities_f)) + len(cities_u) + 0.5

ax.bar(positions_u, ranges_u, color='#E74C3C', alpha=0.7, label='U-shaped')
ax.bar(positions_f, ranges_f, color='#3498DB', alpha=0.7, label='Flat/Decreasing')
ax.set_xticks(list(positions_u) + list(positions_f))
ax.set_xticklabels(cities_u + cities_f, rotation=45, ha='right')
ax.set_ylabel('UTCI Range (°C)', fontweight='bold')
ax.set_title('Temperature Range by City', fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

# 2. Min/Max temperature scatter
ax = axes[0, 1]
ax.scatter(u_shaped['utci_min'], u_shaped['utci_max'], s=200, c='#E74C3C', alpha=0.7,
           label='U-shaped', edgecolors='black', linewidths=2)
ax.scatter(flat['utci_min'], flat['utci_max'], s=200, c='#3498DB', alpha=0.7,
           label='Flat/Decreasing', edgecolors='black', linewidths=2)

for _, row in df_summary.iterrows():
    ax.annotate(row['city'], (row['utci_min'], row['utci_max']),
                fontsize=8, ha='center', va='bottom')

ax.axhline(-20, color='blue', linestyle='--', alpha=0.5, label='Cold threshold')
ax.axvline(35, color='red', linestyle='--', alpha=0.5, label='Hot threshold')
ax.set_xlabel('Min UTCI (°C)', fontweight='bold')
ax.set_ylabel('Max UTCI (°C)', fontweight='bold')
ax.set_title('Temperature Extremes', fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3)

# 3. Seasonal distribution - U-shaped cities
ax = axes[0, 2]
seasons = ['Winter', 'Spring', 'Summer', 'Fall']
x = np.arange(len(seasons))
width = 0.35

for i, city in enumerate(cities_u):
    city_data = u_shaped[u_shaped['city'] == city].iloc[0]
    pcts = [city_data[f'pct_{s.lower()}'] for s in seasons]
    ax.bar(x + i*width, pcts, width, label=city, alpha=0.8)

ax.set_xlabel('Season', fontweight='bold')
ax.set_ylabel('Percentage of Data (%)', fontweight='bold')
ax.set_title('Seasonal Distribution - U-shaped Cities', fontweight='bold')
ax.set_xticks(x + width/2)
ax.set_xticklabels(seasons)
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

# 4. Seasonal distribution - Flat/decreasing cities
ax = axes[1, 0]
width = 0.15
for i, city in enumerate(cities_f):
    city_data = flat[flat['city'] == city].iloc[0]
    pcts = [city_data[f'pct_{s.lower()}'] for s in seasons]
    ax.bar(x + i*width, pcts, width, label=city, alpha=0.8)

ax.set_xlabel('Season', fontweight='bold')
ax.set_ylabel('Percentage of Data (%)', fontweight='bold')
ax.set_title('Seasonal Distribution - Flat/Decreasing Cities', fontweight='bold')
ax.set_xticks(x + width*2.5)
ax.set_xticklabels(seasons)
ax.legend(fontsize=8)
ax.grid(True, alpha=0.3, axis='y')

# 5. Dominant season percentage
ax = axes[1, 1]
ax.bar(positions_u, u_shaped['dominant_season_pct'], color='#E74C3C', alpha=0.7, label='U-shaped')
ax.bar(positions_f, flat['dominant_season_pct'], color='#3498DB', alpha=0.7, label='Flat/Decreasing')
ax.axhline(25, color='black', linestyle='--', alpha=0.5, label='Perfect balance (25%)')
ax.set_xticks(list(positions_u) + list(positions_f))
ax.set_xticklabels(cities_u + cities_f, rotation=45, ha='right')
ax.set_ylabel('Dominant Season (%)', fontweight='bold')
ax.set_title('Seasonal Imbalance\n(% of data from dominant season)', fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

# 6. Season balance std
ax = axes[1, 2]
ax.bar(positions_u, u_shaped['season_balance_std'], color='#E74C3C', alpha=0.7, label='U-shaped')
ax.bar(positions_f, flat['season_balance_std'], color='#3498DB', alpha=0.7, label='Flat/Decreasing')
ax.set_xticks(list(positions_u) + list(positions_f))
ax.set_xticklabels(cities_u + cities_f, rotation=45, ha='right')
ax.set_ylabel('Std Dev of Season %', fontweight='bold')
ax.set_title('Seasonal Variability\n(lower = more balanced)', fontweight='bold')
ax.legend()
ax.grid(True, alpha=0.3, axis='y')

plt.tight_layout()
plt.savefig(OUTPUT_DIR / 'curve_pattern_comparison.png', dpi=300, bbox_inches='tight')
print(f"  Saved: {OUTPUT_DIR / 'curve_pattern_comparison.png'}")

print("\n" + "="*80)
print("Analysis complete!")
print("="*80)
