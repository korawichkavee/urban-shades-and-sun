#!/usr/bin/env python3
# ABOUTME: Plot UTCI vs shade preference curves for Seattle and NYC
# ABOUTME: Shows raw, IPW-only, and final (mobility + IPW) corrections at each adjustment level

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats

# Setup
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'scripts' / 'utils'))

# City configs
CITIES = {
    'seattle': {
        'name': 'Seattle',
        'color': '#2E7D32',  # green
    },
    'new-york-city': {
        'name': 'New York City',
        'color': '#1565C0',  # blue
    }
}

def load_city_data(city_key):
    """Load final IPW results for a city."""
    input_file = project_root / 'final_run_outputs' / city_key / f'{city_key}_final_analysis_with_ipw.csv'
    print(f"Loading {CITIES[city_key]['name']}...")
    df = pd.read_csv(input_file, low_memory=False)
    
    # Calculate total people per image
    df['total_people'] = df['inshade_count'] + df['outshade_count']
    
    # Filter to images with people
    df_people = df[df['total_people'] > 0].copy()
    
    print(f"  Total images: {len(df):,}")
    print(f"  Images with people: {len(df_people):,}")
    print(f"  Total people observed: {df_people['total_people'].sum():,.0f}")
    
    return df_people

def compute_binned_curve(df, utci_col='utci_C', shade_col='shade_pref_raw', 
                         weight_col='total_people', n_bins=20):
    """
    Compute binned shade preference curve.
    
    Args:
        df: DataFrame with UTCI and shade preference data
        utci_col: Column name for UTCI values
        shade_col: Column name for shade preference (0-1)
        weight_col: Column name for weights (total people per image)
        n_bins: Number of UTCI bins
    
    Returns:
        DataFrame with bin_center, shade_pref_mean, shade_pref_se, n_people
    """
    # Remove NaN values
    valid = df[[utci_col, shade_col, weight_col]].notna().all(axis=1)
    df_valid = df[valid].copy()
    
    if len(df_valid) == 0:
        return pd.DataFrame(columns=['bin_center', 'shade_pref_mean', 'shade_pref_se', 'n_people'])
    
    # Create UTCI bins
    utci_min = df_valid[utci_col].min()
    utci_max = df_valid[utci_col].max()
    bins = np.linspace(utci_min, utci_max, n_bins + 1)
    df_valid['utci_bin'] = pd.cut(df_valid[utci_col], bins=bins, include_lowest=True)
    
    # Compute weighted mean and SE per bin
    results = []
    for bin_interval, group in df_valid.groupby('utci_bin'):
        if len(group) == 0:
            continue
            
        bin_center = (bin_interval.left + bin_interval.right) / 2
        
        # Weighted mean
        weights = group[weight_col]
        shade_pref_mean = np.average(group[shade_col], weights=weights)
        
        # Weighted standard error
        n_people = weights.sum()
        if n_people > 1:
            # Weighted variance
            weighted_var = np.average((group[shade_col] - shade_pref_mean)**2, weights=weights)
            # SE = sqrt(var / n_eff) where n_eff accounts for weights
            n_eff = weights.sum()**2 / (weights**2).sum()  # Kish's effective sample size
            shade_pref_se = np.sqrt(weighted_var / n_eff)
        else:
            shade_pref_se = np.nan
        
        results.append({
            'bin_center': bin_center,
            'shade_pref_mean': shade_pref_mean,
            'shade_pref_se': shade_pref_se,
            'n_people': n_people
        })
    
    return pd.DataFrame(results)

def plot_curves(seattle_data, nyc_data, output_dir):
    """Plot UTCI vs shade preference curves for both cities."""
    
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    
    # Define the three adjustment levels
    adjustments = [
        ('Raw (no corrections)', 'shade_pref_raw', 'total_people'),
        ('IPW only', 'shade_pref_dcwp', 'w_combined'),
        ('Final (Mobility + IPW)', 'shade_pref_dcwp', 'w_combined'),  # Same as IPW for now
    ]
    
    for idx, (title, shade_col, weight_col) in enumerate(adjustments):
        ax = axes[idx]
        
        for city_key in ['seattle', 'new-york-city']:
            df = seattle_data if city_key == 'seattle' else nyc_data
            config = CITIES[city_key]
            
            # Skip if columns don't exist
            if shade_col not in df.columns:
                print(f"Warning: {shade_col} not found for {config['name']}, skipping")
                continue
            
            # Compute binned curve
            curve_df = compute_binned_curve(
                df, 
                utci_col='utci_C', 
                shade_col=shade_col,
                weight_col=weight_col,
                n_bins=20
            )
            
            if len(curve_df) == 0:
                continue
            
            # Plot with error bands
            ax.plot(curve_df['bin_center'], curve_df['shade_pref_mean'], 
                   color=config['color'], linewidth=2.5, label=config['name'], alpha=0.9)
            
            # Add confidence bands (±1 SE)
            ax.fill_between(
                curve_df['bin_center'],
                curve_df['shade_pref_mean'] - curve_df['shade_pref_se'],
                curve_df['shade_pref_mean'] + curve_df['shade_pref_se'],
                color=config['color'], alpha=0.2
            )
        
        # Formatting
        ax.set_xlabel('UTCI (°C)', fontsize=11)
        ax.set_ylabel('Shade Preference\n(fraction choosing shade)', fontsize=11)
        ax.set_title(title, fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.legend(loc='best', framealpha=0.9)
        ax.set_ylim(-0.05, 1.05)
        
        # Add reference line at 0.5
        ax.axhline(0.5, color='gray', linestyle='--', linewidth=1, alpha=0.5)
    
    plt.tight_layout()
    
    # Save
    output_file = output_dir / 'utci_shade_preference_curves.png'
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    print(f"\nSaved plot to {output_file}")
    
    plt.show()

def main():
    """Main analysis."""
    print("=" * 70)
    print("UTCI vs SHADE PREFERENCE CURVES")
    print("=" * 70)
    print()
    
    # Load data
    seattle_data = load_city_data('seattle')
    nyc_data = load_city_data('new-york-city')
    
    print()
    
    # Create output directory
    output_dir = project_root / 'outputs' / 'analysis'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Plot
    plot_curves(seattle_data, nyc_data, output_dir)
    
    print()
    print("=" * 70)
    print("Done.")
    print("=" * 70)

if __name__ == '__main__':
    main()
