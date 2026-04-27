#!/usr/bin/env python3
"""
Apply seasonal standardization to shade preference estimates.

Creates two versions:
1. WITH Temp-IPW: w_final = w_SR × w_Temp × w_DCWP × w_season
2. WITHOUT Temp-IPW: w_final = w_SR × w_DCWP × w_season

Purpose: Remove Street View seasonal sampling artifacts while preserving
temperature-based selection bias corrections.

Estimand: Average shade preference across the calendar year, assuming
season effects operate entirely through UTCI distribution.
"""

import pandas as pd
import numpy as np
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

def assign_seasons(df):
    """Assign meteorological seasons based on month.

    Winter: Dec, Jan, Feb (12, 1, 2)
    Spring: Mar, Apr, May (3, 4, 5)
    Summer: Jun, Jul, Aug (6, 7, 8)
    Fall: Sep, Oct, Nov (9, 10, 11)

    Parameters
    ----------
    df : pd.DataFrame
        Must have 'captured_at' column (timestamp in milliseconds)

    Returns
    -------
    pd.Series
        Season labels
    """
    # Parse timestamp
    capture_date = pd.to_datetime(df['captured_at'], unit='ms', utc=True)
    month = capture_date.dt.month

    conditions = [
        month.isin([12, 1, 2]),
        month.isin([3, 4, 5]),
        month.isin([6, 7, 8]),
        month.isin([9, 10, 11])
    ]

    seasons = ['winter', 'spring', 'summer', 'fall']

    return np.select(conditions, seasons, default='unknown')

def compute_dcwp_weight(df, tau=20.0):
    """Compute DCWP weights from distance to shade.

    DCWP adjusts for access costs by downweighting people standing in sun
    far from shade (they may not have had a choice).

    Parameters
    ----------
    df : pd.DataFrame
        Must have 'dist_to_shade_m', 'inshade_count', 'outshade_count', 'in_shade'
    tau : float
        Decay constant in meters (default 20.0)

    Returns
    -------
    pd.Series
        DCWP weights (mean-scaled to 1.0)
    """
    # For people in shade: no adjustment (weight = 1.0)
    # For people in sun: downweight by exp(-dist/tau)

    # Create weight based on in_shade status
    w_dcwp = np.where(
        df['in_shade'] == 1,
        1.0,  # Shade-standers: full weight
        np.exp(-df['dist_to_shade_m'] / tau)  # Sun-standers: distance discount
    )

    # Scale to mean = 1.0
    w_dcwp_scaled = w_dcwp / w_dcwp.mean()

    return w_dcwp_scaled

def compute_seasonal_weights(df, city_name):
    """Compute seasonal reweighting factors to achieve uniform 25% per season.

    Parameters
    ----------
    df : pd.DataFrame
        Must have 'season' column
    city_name : str
        For reporting

    Returns
    -------
    dict
        Mapping from season to weight factor
    """
    # Current proportions
    season_counts = df.groupby('season').size()
    season_props = season_counts / len(df)

    # Target uniform
    target = 0.25

    # Compute weights
    season_weights = {}
    for season in ['winter', 'spring', 'summer', 'fall']:
        if season in season_props.index:
            season_weights[season] = target / season_props[season]
        else:
            # Edge case: no data in this season
            season_weights[season] = 0.0
            print(f"WARNING: {city_name} has no {season} data!")

    # Report
    print(f"\n{city_name} Seasonal Distribution")
    print("=" * 70)
    print("\nOriginal seasonal proportions:")
    for season in ['winter', 'spring', 'summer', 'fall']:
        if season in season_props.index:
            print(f"  {season:8s}: {season_props[season]:.3f} ({season_counts[season]:,} images)")

    print("\nSeasonal reweighting factors:")
    for season in ['winter', 'spring', 'summer', 'fall']:
        weight = season_weights[season]
        direction = "downweight" if weight < 1.0 else "upweight" if weight > 1.0 else "no change"
        print(f"  {season:8s}: {weight:.3f} ({direction})")

    return season_weights

def apply_seasonal_reweighting(df, city_name, include_temp_ipw=True):
    """Apply seasonal standardization and create final weights.

    Parameters
    ----------
    df : pd.DataFrame
        Must have: w_sr_ipw, w_temp_ipw, dist_to_shade_m, in_shade, season
    city_name : str
        For reporting
    include_temp_ipw : bool
        If True: w_final = w_SR × w_Temp × w_DCWP × w_season
        If False: w_final = w_SR × w_DCWP × w_season

    Returns
    -------
    pd.DataFrame
        With additional columns: w_dcwp, w_season, w_final
    """
    # Compute DCWP weights (not stored in file, need to recompute)
    print(f"\nComputing DCWP weights (tau=20m)...")
    df['w_dcwp'] = compute_dcwp_weight(df, tau=20.0)
    print(f"  Mean w_dcwp: {df['w_dcwp'].mean():.3f}")
    print(f"  Std w_dcwp:  {df['w_dcwp'].std():.3f}")

    # Compute seasonal weights
    season_weights = compute_seasonal_weights(df, city_name)

    # Apply seasonal weights
    df['w_season'] = df['season'].map(season_weights)

    # Create final weights
    if include_temp_ipw:
        # Version 1: WITH Temp-IPW
        df['w_final'] = df['w_sr_ipw'] * df['w_temp_ipw'] * df['w_dcwp'] * df['w_season']
        version = "WITH Temp-IPW"
    else:
        # Version 2: WITHOUT Temp-IPW
        df['w_final'] = df['w_sr_ipw'] * df['w_dcwp'] * df['w_season']
        version = "WITHOUT Temp-IPW"

    # Verify seasonal balance
    print(f"\n{version} - Weighted seasonal proportions (target: 0.25 each):")
    weighted_props = df.groupby('season').apply(
        lambda x: x['w_final'].sum() / df['w_final'].sum()
    )
    for season in ['winter', 'spring', 'summer', 'fall']:
        if season in weighted_props.index:
            prop = weighted_props[season]
            error = abs(prop - 0.25)
            status = "✓" if error < 0.01 else "⚠" if error < 0.02 else "✗"
            print(f"  {season:8s}: {prop:.4f} {status}")

    # Compute effective sample size
    n_eff_final = (df['w_final'].sum() ** 2) / (df['w_final'] ** 2).sum()
    n_eff_pct = n_eff_final / len(df) * 100

    # Compare to previous N_eff (from w_combined)
    n_eff_combined = (df['w_combined'].sum() ** 2) / (df['w_combined'] ** 2).sum()
    n_eff_combined_pct = n_eff_combined / len(df) * 100

    print(f"\nEffective sample size:")
    print(f"  Before seasonal reweighting: {n_eff_combined:,.0f} ({n_eff_combined_pct:.1f}%)")
    print(f"  After seasonal reweighting:  {n_eff_final:,.0f} ({n_eff_pct:.1f}%)")
    print(f"  Change: {n_eff_final - n_eff_combined:+,.0f} ({n_eff_pct - n_eff_combined_pct:+.1f} pp)")

    # Weight distribution diagnostics
    print(f"\nFinal weight distribution:")
    print(f"  Mean:   {df['w_final'].mean():.3f}")
    print(f"  Median: {df['w_final'].median():.3f}")
    print(f"  Std:    {df['w_final'].std():.3f}")
    print(f"  Min:    {df['w_final'].min():.3f}")
    print(f"  Max:    {df['w_final'].max():.3f}")
    print(f"  P95:    {df['w_final'].quantile(0.95):.3f}")
    print(f"  P99:    {df['w_final'].quantile(0.99):.3f}")

    # Flag extremes
    n_extreme_high = (df['w_final'] > 10).sum()
    n_extreme_low = (df['w_final'] < 0.1).sum()
    if n_extreme_high > 0:
        print(f"  ⚠ {n_extreme_high} weights > 10 ({n_extreme_high/len(df)*100:.2f}%)")
    if n_extreme_low > 0:
        print(f"  ⚠ {n_extreme_low} weights < 0.1 ({n_extreme_low/len(df)*100:.2f}%)")

    return df

def compute_aggregate_estimates(df, city_name, version_label):
    """Compute aggregate shade preference estimates with final weights."""

    print(f"\n{city_name} - {version_label} - Aggregate Estimates")
    print("=" * 70)

    # Raw (unweighted)
    raw = df['in_shade'].mean()

    # DCWP only (no IPW, no seasonal)
    # Use aggregate formula
    inshade_sum = df['inshade_count'].sum()
    outshade_sum = df['outshade_count'].sum()
    total_people = inshade_sum + outshade_sum

    # Walk-adjusted (DCWP aggregate formula)
    inshade_dcwp = (df['inshade_count'] * df['w_dcwp']).sum()
    outshade_dcwp = (df['outshade_count'] * df['w_dcwp']).sum()
    total_dcwp = inshade_dcwp + outshade_dcwp
    dcwp_agg = inshade_dcwp / total_dcwp

    # Final weighted (using w_final)
    final = (df['in_shade'] * df['w_final']).sum() / df['w_final'].sum()

    print(f"  Raw (unweighted):     {raw:.4f} ({raw*100:.2f}%)")
    print(f"  DCWP (aggregate):     {dcwp_agg:.4f} ({dcwp_agg*100:.2f}%)")
    print(f"  Final (w_final):      {final:.4f} ({final*100:.2f}%)")
    print(f"  DCWP effect:          {dcwp_agg - raw:+.4f} ({(dcwp_agg - raw)*100:+.2f} pp)")
    print(f"  Combined IPW effect:  {final - dcwp_agg:+.4f} ({(final - dcwp_agg)*100:+.2f} pp)")
    print(f"  Total correction:     {final - raw:+.4f} ({(final - raw)*100:+.2f} pp)")

    return {
        'city': city_name,
        'version': version_label,
        'raw': raw,
        'dcwp': dcwp_agg,
        'final': final,
        'dcwp_effect': dcwp_agg - raw,
        'ipw_effect': final - dcwp_agg,
        'total_effect': final - raw
    }

def main():
    """Main processing pipeline."""

    print("=" * 70)
    print("SEASONAL REWEIGHTING - IPW SHADE PREFERENCE ESTIMATES")
    print("=" * 70)
    print("\nPurpose: Remove Street View seasonal sampling artifacts")
    print("Target: Uniform 25% per season (winter, spring, summer, fall)")
    print("\nCreates two versions:")
    print("  1. WITH Temp-IPW:    w_final = w_SR × w_Temp × w_DCWP × w_season")
    print("  2. WITHOUT Temp-IPW: w_final = w_SR × w_DCWP × w_season")

    cities = ['seattle', 'new-york-city']
    results = []

    for city in cities:
        print("\n" + "=" * 70)
        print(f"PROCESSING: {city.upper()}")
        print("=" * 70)

        # Load revised data
        input_path = f"final_run_outputs/{city}/{city}_final_analysis_with_ipw_revised.csv"
        print(f"\nLoading: {input_path}")

        df = pd.read_csv(input_path)
        print(f"Loaded {len(df):,} images")

        # Assign seasons (will parse captured_at internally)
        df['season'] = assign_seasons(df)

        # Check for unknown seasons
        n_unknown = (df['season'] == 'unknown').sum()
        if n_unknown > 0:
            print(f"WARNING: {n_unknown} images with unknown season!")

        # Version 1: WITH Temp-IPW
        print("\n" + "-" * 70)
        print("VERSION 1: WITH Temp-IPW")
        print("-" * 70)

        df_with_temp = df.copy()
        df_with_temp = apply_seasonal_reweighting(df_with_temp, city, include_temp_ipw=True)

        # Compute estimates
        est_with_temp = compute_aggregate_estimates(df_with_temp, city, "WITH Temp-IPW")
        results.append(est_with_temp)

        # Save
        output_path_with = f"final_run_outputs/{city}/{city}_final_analysis_with_seasonal_and_temp.csv"
        df_with_temp.to_csv(output_path_with, index=False)
        print(f"\nSaved: {output_path_with}")

        # Version 2: WITHOUT Temp-IPW
        print("\n" + "-" * 70)
        print("VERSION 2: WITHOUT Temp-IPW")
        print("-" * 70)

        df_without_temp = df.copy()
        df_without_temp = apply_seasonal_reweighting(df_without_temp, city, include_temp_ipw=False)

        # Compute estimates
        est_without_temp = compute_aggregate_estimates(df_without_temp, city, "WITHOUT Temp-IPW")
        results.append(est_without_temp)

        # Save
        output_path_without = f"final_run_outputs/{city}/{city}_final_analysis_with_seasonal_no_temp.csv"
        df_without_temp.to_csv(output_path_without, index=False)
        print(f"\nSaved: {output_path_without}")

    # Summary comparison table
    print("\n" + "=" * 70)
    print("SUMMARY COMPARISON")
    print("=" * 70)

    df_results = pd.DataFrame(results)

    print("\nShade Preference Estimates:")
    print("-" * 70)
    for city in cities:
        print(f"\n{city.upper()}:")
        city_results = df_results[df_results['city'] == city]
        for _, row in city_results.iterrows():
            print(f"  {row['version']:18s}: {row['final']:.4f} ({row['final']*100:.2f}%)")

    print("\nCross-City Differences:")
    print("-" * 70)
    for version in ["WITH Temp-IPW", "WITHOUT Temp-IPW"]:
        version_results = df_results[df_results['version'] == version]
        seattle_val = version_results[version_results['city'] == 'seattle']['final'].values[0]
        nyc_val = version_results[version_results['city'] == 'new-york-city']['final'].values[0]
        diff = seattle_val - nyc_val
        print(f"  {version:18s}: {diff:+.4f} ({diff*100:+.2f} pp) [Seattle - NYC]")

    # Save summary table
    summary_path = "final_run_outputs/seasonal_reweighting_summary.csv"
    df_results.to_csv(summary_path, index=False)
    print(f"\nSummary table saved: {summary_path}")

    print("\n" + "=" * 70)
    print("DONE")
    print("=" * 70)

if __name__ == "__main__":
    main()
