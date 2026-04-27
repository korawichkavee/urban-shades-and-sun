# ABOUTME: Applies triple IPW corrections WITHOUT spatial/temporal standardization (revised version)
# ABOUTME: Excludes w_spatial and w_temp_range to avoid weight instability issues

import sys
import logging
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d

# Setup logging
def setup_logging(log_file):
    """Configure logging to console and file."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file),
            logging.StreamHandler(sys.stdout),
        ]
    )
    return logging.getLogger(__name__)


# ── Shadow Ratio IPW ────────────────────────────────────────────────────────

def compute_sr_ipw(df, min_shadow_ratio=0.05):
    """
    Compute shadow ratio inverse probability weights.

    Args:
        df: DataFrame with 'shadow_ratio' column
        min_shadow_ratio: Minimum SR threshold (default 0.05)

    Returns:
        Series of SR-IPW weights (mean-scaled to 1.0)
    """
    # Filter: shadow_ratio >= 0.05 (logical requirement, not arbitrary)
    mask = df['shadow_ratio'] >= min_shadow_ratio

    # Compute raw weights
    w_sr_raw = 1.0 / df.loc[mask, 'shadow_ratio']

    # Winsorize at 95th percentile to prevent extreme leverage
    cap = w_sr_raw.quantile(0.95)
    w_sr_capped = np.minimum(w_sr_raw, cap)

    # Scale to mean = 1.0
    w_sr = w_sr_capped / w_sr_capped.mean()

    return w_sr


# ── Temperature Activity IPW ────────────────────────────────────────────────

def compute_temp_ipw(df, walk_rate_df, baseline_utci=20.0):
    """
    Compute temperature activity inverse probability weights (ASYMMETRIC).

    Args:
        df: SVI DataFrame with 'utci_C' column
        walk_rate_df: Walk rate function with columns:
                      ['utci_bin_center', 'walk_rate']
        baseline_utci: Baseline temperature in °C (default 20.0)

    Returns:
        Series of Temp-IPW weights
    """
    # Clip extreme values to avoid infinite weights
    walk_rate_df_clipped = walk_rate_df.copy()
    walk_rate_df_clipped['walk_rate'] = np.maximum(
        walk_rate_df_clipped['walk_rate'],
        0.1  # Minimum walk rate to avoid division by zero
    )

    # Create interpolation function with bounds-based extrapolation (constant outside range)
    f_lambda = interp1d(
        walk_rate_df_clipped['utci_bin_center'],
        walk_rate_df_clipped['walk_rate'],
        kind='linear',
        bounds_error=False,
        fill_value=(walk_rate_df_clipped['walk_rate'].iloc[0], walk_rate_df_clipped['walk_rate'].iloc[-1])
    )

    # Get lambda values for each observation
    lambda_T = f_lambda(df['utci_C'])
    lambda_baseline = f_lambda(baseline_utci)

    # Clip lambda_T to avoid extreme/negative weights from extrapolation
    lambda_T = np.maximum(lambda_T, 0.1)

    # Asymmetric weighting
    # T < 20°C: downweight (cold-hardy walkers non-representative)
    # T ≥ 20°C: upweight (heat-adapted walkers would prefer more shade)
    w_temp = np.where(
        df['utci_C'] < baseline_utci,
        lambda_T / lambda_baseline,      # < 20°C: downweight
        lambda_baseline / lambda_T       # ≥ 20°C: upweight
    )

    # Both branches equal 1.0 at baseline
    return pd.Series(w_temp, index=df.index)


# ── Distance-Conditioned Walk Preference ────────────────────────────────────

def compute_dcwp_adjustment(df, tau=20.0):
    """
    Compute distance-conditioned walk preference adjustments.

    This operates on OUTCOMES (shade preference ratios), not weights.

    Args:
        df: DataFrame with 'dist_to_shade_m', 'inshade_count', 'outshade_count'
        tau: Decay constant in meters (default 20.0)

    Returns:
        Series of DCWP-adjusted shade preference ratios
    """
    # DCWP adjustment: downweight sun-standing by distance to shade
    # Interpretation: People standing in sun far from shade may not have detoured
    effective_sun = df['outshade_count'] * np.exp(-df['dist_to_shade_m'] / tau)
    effective_shade = df['inshade_count']  # No adjustment for shade standing

    # Shade preference ratio
    shade_pref = effective_shade / (effective_shade + effective_sun + 1e-10)

    return shade_pref


# ── Season Assignment ───────────────────────────────────────────────────────

def assign_season(df):
    """
    Assign meteorological seasons based on capture month.

    Args:
        df: DataFrame with 'captured_at' column (milliseconds since epoch)

    Returns:
        DataFrame with 'season' and 'month' columns added
    """
    df['capture_date'] = pd.to_datetime(df['captured_at'], unit='ms', utc=True)
    df['month'] = df['capture_date'].dt.month

    season_map = {
        12: 'winter', 1: 'winter', 2: 'winter',
        3: 'spring', 4: 'spring', 5: 'spring',
        6: 'summer', 7: 'summer', 8: 'summer',
        9: 'fall', 10: 'fall', 11: 'fall'
    }
    df['season'] = df['month'].map(season_map)

    return df


# ── Seasonal Balance Check ──────────────────────────────────────────────────

def check_seasonal_balance(df, logger):
    """
    Check seasonal imbalance and return recommendation.

    Args:
        df: DataFrame with 'season' column
        logger: Logger instance

    Returns:
        Tuple of (balance_level, dominant_pct)
    """
    season_counts = df['season'].value_counts()
    dominant_season = season_counts.idxmax()
    dominant_pct = season_counts.max() / len(df) * 100

    logger.info(f"Season distribution:")
    for season, count in season_counts.items():
        pct = count / len(df) * 100
        logger.info(f"  {season:>6}: {count:>8,} ({pct:>5.1f}%)")

    logger.info(f"Dominant season: {dominant_season} ({dominant_pct:.1f}%)")

    if dominant_pct <= 60:
        level = 'balanced'
        logger.info("✓ Balanced seasonal distribution (≤60% dominant)")
    elif dominant_pct <= 70:
        level = 'moderate'
        logger.warning("⚠ Moderate seasonal imbalance (60-70% dominant) - use caution with overall estimates")
    else:
        level = 'severe'
        logger.warning("✗ Severe seasonal imbalance (>70% dominant) - recommend seasonal-specific plots only")

    return level, dominant_pct


# ── Effective Sample Size ───────────────────────────────────────────────────

def effective_sample_size(weights):
    """
    Compute effective sample size for weighted data.

    N_eff = (sum w)^2 / sum(w^2)

    Args:
        weights: Series of weights

    Returns:
        Effective sample size (float)
    """
    valid_weights = weights[np.isfinite(weights) & (weights > 0)]
    if len(valid_weights) == 0:
        return 0
    return (valid_weights.sum() ** 2) / (valid_weights ** 2).sum()


# ── Summary Statistics ──────────────────────────────────────────────────────

def generate_summary_stats(df, df_filtered, logger):
    """
    Generate and log summary statistics.

    Args:
        df: Original unfiltered DataFrame
        df_filtered: Filtered DataFrame with IPW weights
        logger: Logger instance

    Returns:
        Dictionary of summary statistics
    """
    stats = {}

    # Data retention
    stats['total_images'] = len(df)
    stats['images_after_sr_filter'] = len(df_filtered)
    stats['data_retention_pct'] = len(df_filtered) / len(df) * 100

    # Effective sample sizes
    stats['n_eff_sr_ipw'] = effective_sample_size(df_filtered['w_sr_ipw'])
    stats['n_eff_temp_ipw'] = effective_sample_size(df_filtered['w_temp_ipw'])
    stats['n_eff_combined'] = effective_sample_size(df_filtered['w_combined'])

    # Shade preference estimates (only on images with people)
    df_with_people = df_filtered[df_filtered['person_count'] > 0].copy()

    if len(df_with_people) > 0:
        # Raw (unweighted)
        total_shade = df_with_people['inshade_count'].sum()
        total_sun = df_with_people['outshade_count'].sum()
        stats['shade_pref_raw'] = total_shade / (total_shade + total_sun) if (total_shade + total_sun) > 0 else np.nan

        # DCWP-adjusted (no IPW)
        stats['shade_pref_dcwp'] = (
            (df_with_people['shade_pref_dcwp'] * df_with_people['person_count']).sum() /
            df_with_people['person_count'].sum()
        )

        # Full IPW (revised: SR-IPW × Temp-IPW only, no spatial/temporal)
        stats['shade_pref_ipw'] = (
            (df_with_people['shade_pref_dcwp'] * df_with_people['w_combined'] * df_with_people['person_count']).sum() /
            (df_with_people['w_combined'] * df_with_people['person_count']).sum()
        )

        # Effect sizes (percentage points)
        stats['dcwp_effect_pp'] = (stats['shade_pref_dcwp'] - stats['shade_pref_raw']) * 100
        stats['combined_effect_pp'] = (stats['shade_pref_ipw'] - stats['shade_pref_raw']) * 100

    else:
        logger.warning("No images with people detected - cannot compute shade preference")
        stats['shade_pref_raw'] = np.nan
        stats['shade_pref_dcwp'] = np.nan
        stats['shade_pref_ipw'] = np.nan
        stats['dcwp_effect_pp'] = np.nan
        stats['combined_effect_pp'] = np.nan

    # Log summary
    logger.info("=" * 60)
    logger.info("SUMMARY STATISTICS (REVISED: NO SPATIAL/TEMPORAL)")
    logger.info("=" * 60)
    logger.info(f"Total images:                {stats['total_images']:>12,}")
    logger.info(f"After SR filter (≥0.05):     {stats['images_after_sr_filter']:>12,}")
    logger.info(f"Data retention:              {stats['data_retention_pct']:>12.1f}%")
    logger.info("")
    logger.info(f"Effective N (SR-IPW):        {stats['n_eff_sr_ipw']:>12,.0f}")
    logger.info(f"Effective N (Temp-IPW):      {stats['n_eff_temp_ipw']:>12,.0f}")
    logger.info(f"Effective N (combined):      {stats['n_eff_combined']:>12,.0f}")
    logger.info(f"Combined N_eff % of total:   {100*stats['n_eff_combined']/stats['images_after_sr_filter']:>12.1f}%")
    logger.info("")

    if not np.isnan(stats['shade_pref_raw']):
        logger.info(f"Shade preference (raw):      {stats['shade_pref_raw']:>12.3f} ({stats['shade_pref_raw']*100:.1f}%)")
        logger.info(f"Shade preference (DCWP):     {stats['shade_pref_dcwp']:>12.3f} ({stats['shade_pref_dcwp']*100:.1f}%)")
        logger.info(f"Shade preference (IPW):      {stats['shade_pref_ipw']:>12.3f} ({stats['shade_pref_ipw']*100:.1f}%)")
        logger.info("")
        logger.info(f"DCWP effect:                 {stats['dcwp_effect_pp']:>12.2f} pp")
        logger.info(f"Combined IPW effect:         {stats['combined_effect_pp']:>12.2f} pp")

    logger.info("=" * 60)

    return stats


# ── Main Pipeline ───────────────────────────────────────────────────────────

def apply_combined_ipw(df, walk_rate_df, logger):
    """
    Apply revised IPW pipeline: SR-IPW × Temp-IPW only (NO spatial/temporal).

    Args:
        df: Input DataFrame (shadow + UTCI annotated)
        walk_rate_df: Walk rate function DataFrame
        logger: Logger instance

    Returns:
        Filtered DataFrame with all weight columns and adjusted metrics
    """
    logger.info("Applying REVISED triple IPW corrections...")
    logger.info("NOTE: Excluding spatial and temporal standardization for stability")

    # FIX: Compute person_count from inshade + outshade counts
    logger.info("Computing person_count from shade counts...")
    df['person_count'] = df['inshade_count'] + df['outshade_count']
    n_with_people = (df['person_count'] > 0).sum()
    total_people = df['person_count'].sum()
    logger.info(f"  Images with people: {n_with_people:,} / {len(df):,} ({100*n_with_people/len(df):.1f}%)")
    logger.info(f"  Total people observed: {total_people:,.0f}")

    # Assign seasons
    logger.info("Assigning seasons...")
    df = assign_season(df)

    # Check seasonal balance
    balance_level, dominant_pct = check_seasonal_balance(df, logger)

    # Filter: shadow_ratio >= 0.05
    logger.info(f"Filtering: shadow_ratio >= 0.05...")
    initial_count = len(df)
    df_filtered = df[df['shadow_ratio'] >= 0.05].copy()
    filtered_count = len(df_filtered)
    retention_pct = filtered_count / initial_count * 100

    logger.info(f"  Retained: {filtered_count:,} / {initial_count:,} ({retention_pct:.1f}%)")

    if filtered_count == 0:
        logger.error("No data remaining after shadow_ratio filter!")
        return None

    # 1. Shadow Ratio IPW
    logger.info("Computing Shadow Ratio IPW...")
    df_filtered['w_sr_ipw'] = compute_sr_ipw(df_filtered)
    logger.info(f"  Mean: {df_filtered['w_sr_ipw'].mean():.3f}")
    logger.info(f"  Std:  {df_filtered['w_sr_ipw'].std():.3f}")
    logger.info(f"  Max:  {df_filtered['w_sr_ipw'].max():.3f}")
    logger.info(f"  N_eff: {effective_sample_size(df_filtered['w_sr_ipw']):,.0f}")

    # 2. Temperature Activity IPW
    logger.info("Computing Temperature Activity IPW (asymmetric)...")
    df_filtered['w_temp_ipw'] = compute_temp_ipw(df_filtered, walk_rate_df)
    logger.info(f"  Mean: {df_filtered['w_temp_ipw'].mean():.3f}")
    logger.info(f"  Std:  {df_filtered['w_temp_ipw'].std():.3f}")
    logger.info(f"  Max:  {df_filtered['w_temp_ipw'].max():.3f}")
    logger.info(f"  N_eff: {effective_sample_size(df_filtered['w_temp_ipw']):,.0f}")

    # 3. DCWP adjustment (operates on outcomes, not weights)
    logger.info("Computing DCWP adjustment...")
    df_filtered['shade_pref_dcwp'] = compute_dcwp_adjustment(df_filtered)
    logger.info(f"  Mean shade pref (DCWP): {df_filtered['shade_pref_dcwp'].mean():.3f}")

    # 4. Combined weight (REVISED: SR-IPW × Temp-IPW only)
    logger.info("Computing combined weights (SR-IPW × Temp-IPW only)...")
    df_filtered['w_combined'] = (
        df_filtered['w_sr_ipw'] *
        df_filtered['w_temp_ipw']
    )
    logger.info(f"  Mean: {df_filtered['w_combined'].mean():.3f}")
    logger.info(f"  Std:  {df_filtered['w_combined'].std():.3f}")
    logger.info(f"  Max:  {df_filtered['w_combined'].max():.3f}")
    logger.info(f"  N_eff: {effective_sample_size(df_filtered['w_combined']):,.0f}")

    # Add raw shade preference for comparison
    df_filtered['shade_pref_raw'] = (
        df_filtered['inshade_count'] /
        (df_filtered['inshade_count'] + df_filtered['outshade_count'] + 1e-10)
    )

    return df_filtered


# ── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='Apply REVISED triple IPW corrections (no spatial/temporal)')
    parser.add_argument('--city', required=True, choices=['seattle', 'new-york-city'],
                        help='City to process')
    args = parser.parse_args()

    city = args.city

    project_root = Path(__file__).parent.parent.parent

    # Input: shadow + UTCI annotated data
    input_path = project_root / 'final_run_outputs' / city / f'{city}_with_shadow_and_utci.csv'
    output_path = project_root / 'final_run_outputs' / city / f'{city}_final_analysis_with_ipw_revised.csv'

    # Walk rate function
    walk_rate_path = project_root / 'outputs' / 'analysis' / f'{city.replace("-", "")}_walking_by_utci.csv'

    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = project_root / 'logs' / f'ipw_revised_{city}_{timestamp}.log'

    logger = setup_logging(log_file)

    logger.info('=' * 60)
    logger.info(f'{city.upper()} REVISED IPW APPLICATION')
    logger.info('REVISION: Excludes spatial/temporal standardization')
    logger.info(f'Input:     {input_path}')
    logger.info(f'Walk rate: {walk_rate_path}')
    logger.info(f'Output:    {output_path}')
    logger.info(f'Log:       {log_file}')
    logger.info('=' * 60)

    # Check inputs exist
    if not input_path.exists():
        logger.error(f'Input file does not exist: {input_path}')
        logger.error('Please run shadow + UTCI annotation first.')
        return

    if not walk_rate_path.exists():
        logger.error(f'Walk rate file does not exist: {walk_rate_path}')
        return

    # Load data
    logger.info(f'Loading input data...')
    df = pd.read_csv(input_path, low_memory=False)
    logger.info(f'  Loaded {len(df):,} rows')

    logger.info(f'Loading walk rate function...')
    walk_rate_df = pd.read_csv(walk_rate_path)
    logger.info(f'  Loaded {len(walk_rate_df)} UTCI bins')
    logger.info(f'  UTCI range: {walk_rate_df["utci_bin_center"].min():.1f}°C to {walk_rate_df["utci_bin_center"].max():.1f}°C')

    # Apply IPW
    df_filtered = apply_combined_ipw(df, walk_rate_df, logger)

    if df_filtered is None:
        logger.error('IPW application failed.')
        return

    # Generate summary statistics
    stats = generate_summary_stats(df, df_filtered, logger)

    # Save results
    logger.info(f'Saving results to {output_path}...')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df_filtered.to_csv(output_path, index=False)
    logger.info(f'Saved {len(df_filtered):,} rows')

    # Save summary stats
    stats_path = output_path.parent / f'{city}_ipw_revised_summary_stats.csv'
    pd.DataFrame([stats]).to_csv(stats_path, index=False)
    logger.info(f'Saved summary statistics to {stats_path}')

    logger.info('=' * 60)
    logger.info('Done.')
    logger.info('=' * 60)


if __name__ == '__main__':
    main()
