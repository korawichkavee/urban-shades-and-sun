#!/usr/bin/env python3
# ABOUTME: Explicit UTCI vs shade preference plotting with critical analysis
# ABOUTME: Computes shade preference at raw, IPW, and final adjustment levels

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

project_root = Path(__file__).parent.parent.parent

def load_and_prepare_data(city_key):
    """Load city data and compute shade preference from raw counts."""
    input_file = project_root / 'final_run_outputs' / city_key / f'{city_key}_final_analysis_with_ipw.csv'
    
    print(f"\nLoading {city_key}...")
    df = pd.read_csv(input_file, low_memory=False)
    
    # Compute total people and raw shade preference
    df['total_people'] = df['inshade_count'] + df['outshade_count']
    
    # Raw shade preference = fraction of people in shade
    df['shade_pref_computed'] = np.where(
        df['total_people'] > 0,
        df['inshade_count'] / df['total_people'],
        np.nan
    )
    
    # Filter to images with people
    df_people = df[df['total_people'] > 0].copy()
    
    print(f"  Loaded {len(df):,} total images")
    print(f"  Images with people: {len(df_people):,}")
    print(f"  Total people: {df_people['total_people'].sum():,.0f}")
    print(f"  Columns available: {df.columns.tolist()}")
    
    # Check what shade preference columns exist
    shade_cols = [c for c in df.columns if 'shade_pref' in c or 'dcwp' in c]
    print(f"  Shade pref columns: {shade_cols}")
    
    # Check weight columns
    weight_cols = [c for c in df.columns if 'w_' in c]
    print(f"  Weight columns: {weight_cols}")
    
    return df_people

def compute_binned_curve(df, utci_col, shade_col, weight_col, n_bins=20):
    """
    Compute binned shade preference curve.
    
    This approach:
    - Bins UTCI values into equal-width bins
    - For each bin, computes weighted mean shade preference
    - Weights by total_people (or IPW weights)
    - Computes standard error accounting for weights
    
    Potential issues:
    - Equal-width bins may have very different sample sizes
    - Weighted SE calculation assumes weights are sampling weights
    - Edge bins may be unreliable with few observations
    """
    # Remove NaN
    valid = df[[utci_col, shade_col, weight_col]].notna().all(axis=1)
    df_valid = df[valid].copy()
    
    if len(df_valid) == 0:
        print(f"    WARNING: No valid data for {shade_col} with {weight_col}")
        return None
    
    # Create bins
    utci_range = (df_valid[utci_col].min(), df_valid[utci_col].max())
    bins = np.linspace(utci_range[0], utci_range[1], n_bins + 1)
    df_valid['bin'] = pd.cut(df_valid[utci_col], bins=bins, include_lowest=True)
    
    results = []
    for bin_val, group in df_valid.groupby('bin', observed=True):
        if len(group) == 0:
            continue
        
        bin_center = (bin_val.left + bin_val.right) / 2
        weights = group[weight_col].values
        values = group[shade_col].values
        
        # Weighted mean
        weighted_mean = np.average(values, weights=weights)
        
        # Weighted SE (Kish's effective sample size method)
        n_eff = weights.sum()**2 / (weights**2).sum()
        if n_eff > 1:
            weighted_var = np.average((values - weighted_mean)**2, weights=weights)
            se = np.sqrt(weighted_var / n_eff)
        else:
            se = np.nan
        
        results.append({
            'bin_center': bin_center,
            'mean': weighted_mean,
            'se': se,
            'n_images': len(group),
            'n_people': weights.sum()
        })
    
    return pd.DataFrame(results)

def main():
    """
    CRITICAL ANALYSIS OF THIS APPROACH:
    
    REASONABLE ASPECTS:
    1. Weighting by total_people makes sense - each person is making a choice
    2. Binning UTCI allows us to see non-linear relationships
    3. Computing SE to show uncertainty is good practice
    4. Comparing cities helps identify generalizable patterns
    
    QUESTIONABLE/PROBLEMATIC ASPECTS:
    1. We only have 2 adjustment levels in the data, not 3:
       - shade_pref_raw (or computed from counts) - raw preference
       - shade_pref_dcwp - double-centered weighted preference
       BUT we don't have separate "IPW only" vs "mobility + IPW" columns
       
    2. The IPW weights (w_combined) combine MULTIPLE adjustments:
       - Shadow ratio IPW (w_sr_ipw)
       - Temperature activity IPW (w_temp_ipw)  
       - Spatial weights (w_spatial)
       - Temperature range weights (w_temp_range)
       So "IPW only" vs "final" distinction may not exist as separate columns
       
    3. Binning choices:
       - Equal-width bins ignore data density
       - 20 bins may be too many/few depending on data spread
       - Edge bins may have few observations -> unreliable estimates
       
    4. shade_pref_dcwp might be NaN if no adjustment was possible
       - The warning said "No images with people detected" for NYC
       - This suggests the DCWP column might be empty
       
    5. We're conflating individual-level (person) and image-level data
       - Each image has multiple people making choices
       - But we only observe the aggregated counts (inshade vs outshade)
       - Can't account for within-image correlation
    
    Let me check what's actually in the data first...
    """
    
    print("=" * 70)
    print("UTCI vs SHADE PREFERENCE ANALYSIS - CRITICAL REVIEW")
    print("=" * 70)
    
    # Load both cities
    seattle = load_and_prepare_data('seattle')
    nyc = load_and_prepare_data('new-york-city')
    
    print("\n" + "=" * 70)
    print("ISSUES IDENTIFIED:")
    print("=" * 70)
    
    # Check if shade_pref_dcwp exists and has values
    for city_name, df in [('Seattle', seattle), ('NYC', nyc)]:
        print(f"\n{city_name}:")
        if 'shade_pref_dcwp' in df.columns:
            n_valid = df['shade_pref_dcwp'].notna().sum()
            print(f"  shade_pref_dcwp: {n_valid:,} / {len(df):,} valid ({100*n_valid/len(df):.1f}%)")
        else:
            print(f"  shade_pref_dcwp: COLUMN MISSING")
        
        if 'shade_pref_raw' in df.columns:
            n_valid = df['shade_pref_raw'].notna().sum()
            print(f"  shade_pref_raw: {n_valid:,} / {len(df):,} valid ({100*n_valid/len(df):.1f}%)")
        else:
            print(f"  shade_pref_raw: COLUMN MISSING")
        
        # Check computed
        n_valid = df['shade_pref_computed'].notna().sum()
        print(f"  shade_pref_computed (from counts): {n_valid:,} / {len(df):,} valid ({100*n_valid/len(df):.1f}%)")

if __name__ == '__main__':
    main()
