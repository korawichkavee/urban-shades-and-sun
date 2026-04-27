#!/usr/bin/env python3
"""
Data Quality Diagnostic Plots

Creates diagnostic plots to assess data quality and coverage:
1. Sample size by UTCI bin
2. Temporal coverage (months, seasons)
3. Spatial coverage (geographic distribution of weights)
4. Variance estimates by bin

Priority 9 from ADDITIONAL_IPW_ANALYSES_PROPOSAL.md
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Paths
DATA_DIR = Path("final_run_outputs")
OUTPUT_DIR = Path("outputs/analysis/ipw_plots")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Plotting settings
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.size'] = 10
plt.rcParams['figure.dpi'] = 150


def plot_sample_size_by_utci(city):
    """Plot sample size distribution across UTCI bins."""

    print(f"\n{'='*70}")
    print(f"{city.upper()} - SAMPLE SIZE BY UTCI")
    print('='*70)

    df = pd.read_csv(DATA_DIR / city / f"{city}_final_analysis_with_ipw_revised.csv")
    df = df[df['shadow_ratio'] >= 0.05].copy()

    # Create UTCI bins
    bins = np.arange(-40, 45, 2)
    df['utci_bin'] = pd.cut(df['utci_C'], bins=bins)

    # Aggregate by bin
    bin_stats = df.groupby('utci_bin', observed=False).agg({
        'in_shade': ['count', 'mean', 'std'],
        'w_combined': ['sum', 'mean']
    }).reset_index()

    bin_stats.columns = ['utci_bin', 'n_images', 'shade_pref_mean', 'shade_pref_std',
                          'effective_n', 'mean_weight']

    # Get bin centers
    bin_stats['utci_center'] = bin_stats['utci_bin'].apply(lambda x: x.mid if pd.notna(x) else np.nan)

    # Remove empty bins
    bin_stats = bin_stats[bin_stats['n_images'] > 0].copy()

    # Compute SE
    bin_stats['shade_pref_se'] = bin_stats['shade_pref_std'] / np.sqrt(bin_stats['n_images'])

    print(f"\nTotal images: {len(df):,}")
    print(f"UTCI range: {df['utci_C'].min():.1f}°C to {df['utci_C'].max():.1f}°C")
    print(f"Non-empty bins: {len(bin_stats)}")
    print(f"\nBin with smallest sample:")
    min_bin = bin_stats.nsmallest(1, 'n_images').iloc[0]
    print(f"  UTCI: {min_bin['utci_center']:.1f}°C, N={min_bin['n_images']:.0f}")
    print(f"\nBin with largest sample:")
    max_bin = bin_stats.nlargest(1, 'n_images').iloc[0]
    print(f"  UTCI: {max_bin['utci_center']:.1f}°C, N={max_bin['n_images']:.0f}")

    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'{city.replace("-", " ").title()} - Data Quality by UTCI Bin',
                 fontsize=14, fontweight='bold')

    # Plot 1: Sample size
    ax = axes[0, 0]
    ax.bar(bin_stats['utci_center'], bin_stats['n_images'], width=1.8,
           color='steelblue', alpha=0.7, edgecolor='black')
    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Number of Images')
    ax.set_title('Sample Size by UTCI Bin')
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(1000, color='red', linestyle='--', linewidth=1, alpha=0.5, label='n=1000')
    ax.legend()

    # Plot 2: Effective N (weighted)
    ax = axes[0, 1]
    ax.bar(bin_stats['utci_center'], bin_stats['effective_n'], width=1.8,
           color='orange', alpha=0.7, edgecolor='black')
    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Effective N (weighted)')
    ax.set_title('Effective Sample Size (IPW)')
    ax.grid(True, alpha=0.3, axis='y')

    # Plot 3: Standard error
    ax = axes[1, 0]
    ax.bar(bin_stats['utci_center'], bin_stats['shade_pref_se']*100, width=1.8,
           color='green', alpha=0.7, edgecolor='black')
    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Standard Error (pp)')
    ax.set_title('Precision by UTCI Bin')
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(1.0, color='red', linestyle='--', linewidth=1, alpha=0.5, label='SE=1 pp')
    ax.axhline(2.0, color='orange', linestyle='--', linewidth=1, alpha=0.5, label='SE=2 pp')
    ax.legend()

    # Plot 4: Coverage ratio (effective N / raw N)
    ax = axes[1, 1]
    coverage_ratio = bin_stats['effective_n'] / bin_stats['n_images'] * 100
    ax.bar(bin_stats['utci_center'], coverage_ratio, width=1.8,
           color='purple', alpha=0.7, edgecolor='black')
    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Effective N / Raw N (%)')
    ax.set_title('Data Retention After Weighting')
    ax.grid(True, alpha=0.3, axis='y')
    ax.axhline(50, color='red', linestyle='--', linewidth=1, alpha=0.5, label='50%')
    ax.legend()

    plt.tight_layout()

    # Save
    for ext in ['png', 'pdf']:
        outfile = OUTPUT_DIR / f"data_quality_utci_{city}.{ext}"
        plt.savefig(outfile, dpi=300 if ext == 'png' else None, bbox_inches='tight')
        print(f"\nSaved: {outfile}")

    plt.close()

    return bin_stats


def plot_temporal_coverage(city):
    """Plot temporal coverage (months, seasons)."""

    print(f"\n{'='*70}")
    print(f"{city.upper()} - TEMPORAL COVERAGE")
    print('='*70)

    df = pd.read_csv(DATA_DIR / city / f"{city}_final_analysis_with_ipw_revised.csv")
    df = df[df['shadow_ratio'] >= 0.05].copy()

    # Parse dates
    df['datetime_local'] = pd.to_datetime(df['datetime_local'])
    df['year'] = df['datetime_local'].dt.year
    df['month_num'] = df['datetime_local'].dt.month
    df['day_of_year'] = df['datetime_local'].dt.dayofyear

    print(f"\nDate range: {df['datetime_local'].min()} to {df['datetime_local'].max()}")
    print(f"Years covered: {sorted(df['year'].unique())}")

    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'{city.replace("-", " ").title()} - Temporal Coverage',
                 fontsize=14, fontweight='bold')

    # Plot 1: Images by month
    ax = axes[0, 0]
    month_counts = df['month_num'].value_counts().sort_index()
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                   'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    ax.bar(month_counts.index, month_counts.values, color='steelblue', alpha=0.7, edgecolor='black')
    ax.set_xlabel('Month')
    ax.set_ylabel('Number of Images')
    ax.set_title('Sample Size by Month')
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(month_names, rotation=45)
    ax.grid(True, alpha=0.3, axis='y')

    # Plot 2: Images by season
    ax = axes[0, 1]
    season_counts = df['season'].value_counts()
    season_order = ['winter', 'spring', 'summer', 'fall']
    season_counts = season_counts.reindex(season_order, fill_value=0)
    colors_season = {'winter': 'lightblue', 'spring': 'lightgreen',
                     'summer': 'orange', 'fall': 'brown'}
    ax.bar(range(len(season_counts)), season_counts.values,
           color=[colors_season[s] for s in season_order], alpha=0.7, edgecolor='black')
    ax.set_xlabel('Season')
    ax.set_ylabel('Number of Images')
    ax.set_title('Sample Size by Season')
    ax.set_xticks(range(len(season_order)))
    ax.set_xticklabels([s.capitalize() for s in season_order])
    ax.grid(True, alpha=0.3, axis='y')

    # Print season stats
    print("\nSeason distribution:")
    for season in season_order:
        count = season_counts[season]
        pct = count / len(df) * 100
        print(f"  {season.capitalize():8s}: {count:7,} ({pct:5.1f}%)")

    # Plot 3: Shade preference by month
    ax = axes[1, 0]
    month_shade = df.groupby('month_num')['in_shade'].mean() * 100
    ax.plot(month_shade.index, month_shade.values, 'o-', linewidth=2, markersize=8)
    ax.set_xlabel('Month')
    ax.set_ylabel('Shade Preference (%)')
    ax.set_title('Shade Preference by Month')
    ax.set_xticks(range(1, 13))
    ax.set_xticklabels(month_names, rotation=45)
    ax.grid(True, alpha=0.3)

    # Plot 4: Calendar heatmap (day of year)
    ax = axes[1, 1]
    day_counts = df['day_of_year'].value_counts().sort_index()
    ax.scatter(day_counts.index, day_counts.values, s=10, alpha=0.5, c='steelblue')
    ax.set_xlabel('Day of Year')
    ax.set_ylabel('Number of Images')
    ax.set_title('Daily Image Count')
    ax.grid(True, alpha=0.3)

    # Add month boundaries
    month_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334, 365]
    for day in month_days:
        ax.axvline(day, color='red', linestyle='--', linewidth=0.5, alpha=0.3)

    plt.tight_layout()

    # Save
    for ext in ['png', 'pdf']:
        outfile = OUTPUT_DIR / f"data_quality_temporal_{city}.{ext}"
        plt.savefig(outfile, dpi=300 if ext == 'png' else None, bbox_inches='tight')
        print(f"\nSaved: {outfile}")

    plt.close()


def plot_spatial_weight_distribution(city):
    """Plot geographic distribution of weights."""

    print(f"\n{'='*70}")
    print(f"{city.upper()} - SPATIAL WEIGHT DISTRIBUTION")
    print('='*70)

    df = pd.read_csv(DATA_DIR / city / f"{city}_final_analysis_with_ipw_revised.csv")
    df = df[df['shadow_ratio'] >= 0.05].copy()

    print(f"\nLat range: {df['lat'].min():.4f} to {df['lat'].max():.4f}")
    print(f"Lon range: {df['lon'].min():.4f} to {df['lon'].max():.4f}")

    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'{city.replace("-", " ").title()} - Spatial Distribution',
                 fontsize=14, fontweight='bold')

    # Plot 1: Geographic scatter of images
    ax = axes[0, 0]
    ax.scatter(df['lon'], df['lat'], s=0.1, alpha=0.3, c='steelblue')
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('Image Locations')
    ax.set_aspect('equal')

    # Plot 2: Weight magnitude by location
    ax = axes[0, 1]
    scatter = ax.scatter(df['lon'], df['lat'], s=0.5, alpha=0.3,
                        c=df['w_combined'], cmap='RdYlBu_r', vmin=0, vmax=3)
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('IPW Weight by Location')
    ax.set_aspect('equal')
    plt.colorbar(scatter, ax=ax, label='Weight')

    # Plot 3: Shadow ratio by location
    ax = axes[1, 0]
    scatter = ax.scatter(df['lon'], df['lat'], s=0.5, alpha=0.3,
                        c=df['shadow_ratio'], cmap='Greens', vmin=0, vmax=1)
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('Shadow Ratio by Location')
    ax.set_aspect('equal')
    plt.colorbar(scatter, ax=ax, label='Shadow Ratio')

    # Plot 4: Shade preference by location
    ax = axes[1, 1]
    scatter = ax.scatter(df['lon'], df['lat'], s=0.5, alpha=0.3,
                        c=df['in_shade'], cmap='coolwarm', vmin=0, vmax=1)
    ax.set_xlabel('Longitude')
    ax.set_ylabel('Latitude')
    ax.set_title('In-Shade Indicator by Location')
    ax.set_aspect('equal')
    plt.colorbar(scatter, ax=ax, label='In Shade')

    plt.tight_layout()

    # Save
    for ext in ['png', 'pdf']:
        outfile = OUTPUT_DIR / f"data_quality_spatial_{city}.{ext}"
        plt.savefig(outfile, dpi=300 if ext == 'png' else None, bbox_inches='tight')
        print(f"\nSaved: {outfile}")

    plt.close()


def plot_variance_by_bin(city):
    """Plot variance estimates by UTCI bin."""

    print(f"\n{'='*70}")
    print(f"{city.upper()} - VARIANCE BY UTCI BIN")
    print('='*70)

    df = pd.read_csv(DATA_DIR / city / f"{city}_final_analysis_with_ipw_revised.csv")
    df = df[df['shadow_ratio'] >= 0.05].copy()

    # Create bins
    bins = np.arange(-40, 45, 2)
    df['utci_bin'] = pd.cut(df['utci_C'], bins=bins)

    # Compute weighted variance by bin
    bin_stats = []
    for bin_label, group in df.groupby('utci_bin', observed=False):
        if len(group) == 0:
            continue

        utci_center = bin_label.mid
        n = len(group)

        # Raw variance
        p = group['in_shade'].mean()
        var_raw = p * (1 - p) / n

        # Weighted variance
        weights = group['w_combined'].values
        p_weighted = (group['in_shade'] * weights).sum() / weights.sum()

        # Effective sample size
        n_eff = weights.sum()**2 / (weights**2).sum()

        # Variance with weights (approximate)
        var_weighted = p_weighted * (1 - p_weighted) / n_eff

        bin_stats.append({
            'utci_center': utci_center,
            'n': n,
            'n_eff': n_eff,
            'p_raw': p,
            'p_weighted': p_weighted,
            'var_raw': var_raw,
            'var_weighted': var_weighted,
            'se_raw': np.sqrt(var_raw),
            'se_weighted': np.sqrt(var_weighted)
        })

    bin_stats = pd.DataFrame(bin_stats)

    # Create figure
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f'{city.replace("-", " ").title()} - Variance by UTCI Bin',
                 fontsize=14, fontweight='bold')

    # Plot 1: Raw vs weighted shade preference
    ax = axes[0, 0]
    ax.plot(bin_stats['utci_center'], bin_stats['p_raw']*100, 'o-',
            label='Raw', linewidth=2, markersize=6)
    ax.plot(bin_stats['utci_center'], bin_stats['p_weighted']*100, 's-',
            label='IPW-weighted', linewidth=2, markersize=6)
    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Shade Preference (%)')
    ax.set_title('Raw vs Weighted Estimates by Bin')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 2: Standard errors
    ax = axes[0, 1]
    ax.plot(bin_stats['utci_center'], bin_stats['se_raw']*100, 'o-',
            label='Raw SE', linewidth=2, markersize=6)
    ax.plot(bin_stats['utci_center'], bin_stats['se_weighted']*100, 's-',
            label='Weighted SE', linewidth=2, markersize=6)
    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Standard Error (pp)')
    ax.set_title('Standard Errors by Bin')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 3: Variance inflation from weighting
    ax = axes[1, 0]
    variance_inflation = bin_stats['var_weighted'] / bin_stats['var_raw']
    ax.plot(bin_stats['utci_center'], variance_inflation, 'o-',
            linewidth=2, markersize=6, color='red')
    ax.axhline(1, color='black', linestyle='--', linewidth=1, alpha=0.5, label='No inflation')
    ax.set_xlabel('UTCI (°C)')
    ax.set_ylabel('Variance Inflation Factor')
    ax.set_title('Variance Inflation from IPW')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Plot 4: Effective N vs raw N
    ax = axes[1, 1]
    ax.scatter(bin_stats['n'], bin_stats['n_eff'], s=50, alpha=0.6)
    max_n = max(bin_stats['n'].max(), bin_stats['n_eff'].max())
    ax.plot([0, max_n], [0, max_n], 'k--', linewidth=1, alpha=0.5, label='1:1 line')
    ax.set_xlabel('Raw N')
    ax.set_ylabel('Effective N (weighted)')
    ax.set_title('Sample Size Loss from Weighting')
    ax.legend()
    ax.grid(True, alpha=0.3)

    plt.tight_layout()

    # Save
    for ext in ['png', 'pdf']:
        outfile = OUTPUT_DIR / f"data_quality_variance_{city}.{ext}"
        plt.savefig(outfile, dpi=300 if ext == 'png' else None, bbox_inches='tight')
        print(f"\nSaved: {outfile}")

    plt.close()

    return bin_stats


if __name__ == "__main__":
    print("="*70)
    print("DATA QUALITY DIAGNOSTIC PLOTS")
    print("="*70)

    for city in ['seattle', 'new-york-city']:
        # Sample size by UTCI
        bin_stats = plot_sample_size_by_utci(city)

        # Temporal coverage
        plot_temporal_coverage(city)

        # Spatial distribution
        plot_spatial_weight_distribution(city)

        # Variance by bin
        variance_stats = plot_variance_by_bin(city)

    print("\n" + "="*70)
    print("Done.")
    print("="*70)
