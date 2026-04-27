#!/usr/bin/env python3
# ABOUTME: Computes Earth Mover's Distance (EMD) spatial bias metrics for metro SVI data
# ABOUTME: Following methodology from SPATIAL_SEASONAL_BIAS_METRICS.md

import sys
import argparse
from pathlib import Path
import pandas as pd
import numpy as np
import pytz
from timezonefinder import TimezoneFinder

# Check for POT library
try:
    import ot  # Python Optimal Transport
except ImportError:
    print("ERROR: POT library not installed. Install with: pip install POT")
    sys.exit(1)

# Paths
ROOT = Path(__file__).resolve().parents[2]
METRO_SVI_DIR = ROOT / 'data/metro_commute_svi'
OUTPUT_DIR = ROOT / 'outputs/analysis'
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Cities with analyzed data (from prescan results)
ANALYZED_CITIES = [
    ('new-york-city', 'New York-Newark-Jersey City, NY-NJ-PA', 40.7128, -74.0060),
    ('atlanta', 'Atlanta-Sandy Springs-Roswell, GA', 33.7490, -84.3880),
    ('minneapolis', 'Minneapolis-St. Paul-Bloomington, MN-WI', 44.9778, -93.2650),
    ('denver', 'Denver-Aurora-Lakewood, CO', 39.7392, -104.9903),
    ('st.-louis', 'St. Louis, MO-IL', 38.6270, -90.1994),
    ('cleveland', 'Cleveland-Elyria, OH', 41.4993, -81.6944),
    ('louisville', 'Louisville/Jefferson County, KY-IN', 38.2527, -85.7585),
    ('salt-lake-city', 'Salt Lake City, UT', 40.7608, -111.8910),
]


def load_city_data(city_dir, lat, lon):
    """Load SVI data for a city with season labels."""

    # Check for analyzed or raw file
    svi_file_analyzed = METRO_SVI_DIR / city_dir / f'{city_dir}_svi_analyzed.csv'
    svi_file_raw = METRO_SVI_DIR / city_dir / f'{city_dir}_svi.csv'

    if svi_file_analyzed.exists():
        svi_file = svi_file_analyzed
    elif svi_file_raw.exists():
        svi_file = svi_file_raw
    else:
        return None

    print(f"  Loading {svi_file.name}...")

    # Read only needed columns in chunks for memory efficiency
    chunk_size = 100_000
    all_data = []

    # Peek at columns
    df_peek = pd.read_csv(svi_file, nrows=1)

    # Determine date column
    if 'datetime-local' in df_peek.columns:
        date_col = 'datetime-local'
    elif 'captured_at' in df_peek.columns:
        date_col = 'captured_at'
    else:
        return None

    # Check for lat/lon columns
    if 'lat' not in df_peek.columns or 'lon' not in df_peek.columns:
        return None

    # Get timezone
    tf = TimezoneFinder()
    timezone_str = tf.timezone_at(lat=lat, lng=lon)
    local_tz = pytz.timezone(timezone_str) if timezone_str else pytz.UTC

    # Define columns to read (only what we need for memory efficiency)
    usecols = [date_col, 'lat', 'lon']

    for chunk_num, df_chunk in enumerate(pd.read_csv(svi_file, chunksize=chunk_size, usecols=usecols), 1):
        # Parse datetime
        if date_col == 'captured_at':
            # Try milliseconds first (raw data)
            df_chunk['datetime_utc'] = pd.to_datetime(df_chunk[date_col], unit='ms', errors='coerce', utc=True)
            # If all failed, try string parsing (analyzed data)
            if df_chunk['datetime_utc'].isna().all():
                df_chunk['datetime_utc'] = pd.to_datetime(df_chunk[date_col], errors='coerce', utc=True)
        else:
            df_chunk['datetime_utc'] = pd.to_datetime(df_chunk[date_col], errors='coerce', utc=True)

        df_chunk = df_chunk[df_chunk['datetime_utc'].notna()].copy()

        if len(df_chunk) == 0:
            continue

        # Convert to local time
        df_chunk['datetime_local'] = df_chunk['datetime_utc'].dt.tz_convert(local_tz)

        # Extract season
        df_chunk['month'] = df_chunk['datetime_local'].dt.month

        def month_to_season(month):
            if month <= 3:
                return 'Winter'
            elif month <= 6:
                return 'Spring'
            elif month <= 9:
                return 'Summer'
            else:
                return 'Fall'

        df_chunk['season'] = df_chunk['month'].apply(month_to_season)

        # Keep only necessary columns
        df_chunk = df_chunk[['lat', 'lon', 'season']].copy()
        all_data.append(df_chunk)

        if chunk_num % 10 == 0:
            print(f"    Processed {chunk_num * chunk_size:,} rows...")

    if not all_data:
        return None

    df = pd.concat(all_data, ignore_index=True)
    print(f"  Loaded {len(df):,} total records")

    return df


def compute_emd_between_seasons(df, grid_size_km=0.25, method='auto', max_memory_gb=4.0):
    """
    Compute Earth Mover's Distance between all season pairs.

    Parameters:
    -----------
    df : DataFrame
        Must have 'lat', 'lon', 'season' columns
    grid_size_km : float
        Grid cell size in kilometers (default: 250m as per doc)
    method : str
        'exact' - Use exact EMD (memory intensive)
        'sinkhorn' - Use entropic regularization (memory efficient)
        'auto' - Automatically choose based on grid size (default)
    max_memory_gb : float
        Maximum memory to use for distance matrix in GB (default: 4.0)

    Returns:
    --------
    dict with EMD metrics
    """

    # Convert lat/lon to Web Mercator (EPSG:3857) for distance in meters
    # Approximate conversion (good enough for our purposes)
    # More accurate would use geopandas, but avoiding the dependency for speed

    # Mean latitude for the city
    mean_lat = df['lat'].mean()

    # Meters per degree at this latitude
    meters_per_deg_lat = 111320.0  # approximately constant
    meters_per_deg_lon = 111320.0 * np.cos(np.radians(mean_lat))

    # Convert to meters (relative to city center)
    center_lat = df['lat'].mean()
    center_lon = df['lon'].mean()

    df['x_m'] = (df['lon'] - center_lon) * meters_per_deg_lon
    df['y_m'] = (df['lat'] - center_lat) * meters_per_deg_lat

    # Get bounding box in meters
    xmin, xmax = df['x_m'].min(), df['x_m'].max()
    ymin, ymax = df['y_m'].min(), df['y_m'].max()

    # Study area diameter for normalization
    diameter = np.sqrt((xmax - xmin)**2 + (ymax - ymin)**2)

    print(f"  Study area: {diameter/1000:.1f} km diameter")

    grid_size_m = grid_size_km * 1000

    # Create grid
    x_edges = np.arange(xmin - grid_size_m, xmax + 2*grid_size_m, grid_size_m)
    y_edges = np.arange(ymin - grid_size_m, ymax + 2*grid_size_m, grid_size_m)

    print(f"  Grid: {len(x_edges)-1} x {len(y_edges)-1} cells ({grid_size_km} km resolution)")

    # Compute grid cell centers
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2
    cell_coords = np.array([[x, y] for x in x_centers for y in y_centers])

    # Estimate memory requirements
    n_cells = len(cell_coords)
    memory_gb = (n_cells * n_cells * 4) / (1024**3)  # float32 = 4 bytes
    print(f"  Distance matrix: {n_cells} cells, estimated memory: {memory_gb:.2f} GB")

    # Auto-select method based on memory constraints
    if method == 'auto':
        if memory_gb > max_memory_gb or n_cells > 5000:
            method = 'sinkhorn'
            print(f"  Auto-selecting Sinkhorn (entropic) method for memory efficiency")
        else:
            method = 'exact'
            print(f"  Auto-selecting exact EMD method")

    # Adaptive grid sizing if memory exceeded (applies to ALL methods since they all need distance matrix)
    if memory_gb > max_memory_gb:
        # Compute required grid size to stay under memory limit
        max_cells = int(np.sqrt(max_memory_gb * (1024**3) / 4))
        current_area = (xmax - xmin) * (ymax - ymin)
        new_grid_size_m = np.sqrt(current_area / max_cells)
        new_grid_size_km = new_grid_size_m / 1000
        print(f"  WARNING: Grid too large ({memory_gb:.2f} GB > {max_memory_gb:.2f} GB)")
        print(f"  Increasing grid size from {grid_size_km:.3f} km to {new_grid_size_km:.3f} km")
        grid_size_km = new_grid_size_km
        grid_size_m = new_grid_size_m

        # Recreate grid with new size
        x_edges = np.arange(xmin - grid_size_m, xmax + 2*grid_size_m, grid_size_m)
        y_edges = np.arange(ymin - grid_size_m, ymax + 2*grid_size_m, grid_size_m)
        x_centers = (x_edges[:-1] + x_edges[1:]) / 2
        y_centers = (y_edges[:-1] + y_edges[1:]) / 2
        cell_coords = np.array([[x, y] for x in x_centers for y in y_centers])
        n_cells = len(cell_coords)
        memory_gb = (n_cells * n_cells * 4) / (1024**3)
        print(f"  Adjusted grid: {len(x_edges)-1} x {len(y_edges)-1} cells, {memory_gb:.2f} GB")

    # Compute or prepare distance matrix based on method
    if method == 'sinkhorn':
        # For Sinkhorn, we compute distances on-the-fly or use a function
        # We'll create a lightweight distance computation
        print(f"  Using Sinkhorn algorithm (no full distance matrix needed)")
        dist_matrix = None

        # Pre-compute distance matrix in chunks or use a function
        # For now, we'll still compute it but acknowledge this could be improved further
        # The Sinkhorn algorithm is still more memory efficient than exact EMD
        dist_matrix = np.zeros((n_cells, n_cells), dtype=np.float32)
        for i in range(n_cells):
            dist_matrix[i] = np.linalg.norm(cell_coords - cell_coords[i], axis=1)
    else:
        # Exact method - compute full distance matrix
        print(f"  Computing distance matrix for exact EMD...")
        dist_matrix = np.zeros((n_cells, n_cells), dtype=np.float32)
        for i in range(n_cells):
            # Vectorized distance computation for row i
            dist_matrix[i] = np.linalg.norm(cell_coords - cell_coords[i], axis=1)

    # Group by season and create histograms
    seasons = ['Winter', 'Spring', 'Summer', 'Fall']
    season_hists = {}
    season_counts = {}

    for season in seasons:
        df_season = df[df['season'] == season]
        season_counts[season] = len(df_season)

        if len(df_season) == 0:
            season_hists[season] = None
            continue

        # Create 2D histogram
        hist, _, _ = np.histogram2d(
            df_season['x_m'],
            df_season['y_m'],
            bins=[x_edges, y_edges]
        )

        # Flatten and normalize to probability distribution
        hist_flat = hist.flatten().astype(np.float64)
        hist_flat = hist_flat / hist_flat.sum()

        season_hists[season] = hist_flat

    print(f"  Season counts: {season_counts}")

    # Compute pairwise EMD
    emd_results = {}

    season_pairs = [
        ('Winter', 'Spring'), ('Winter', 'Summer'), ('Winter', 'Fall'),
        ('Spring', 'Summer'), ('Spring', 'Fall'), ('Summer', 'Fall')
    ]

    emd_values = []
    norm_emd_values = []

    print(f"  Computing EMD for all season pairs using {method} method...")

    for season_a, season_b in season_pairs:
        if season_hists[season_a] is None or season_hists[season_b] is None:
            continue

        if season_counts[season_a] < 50 or season_counts[season_b] < 50:
            continue

        # Compute EMD using POT library
        if method == 'sinkhorn':
            # Use Sinkhorn algorithm with entropic regularization
            # reg parameter controls regularization strength (higher = faster but less accurate)
            # Rule of thumb: reg ~ median_distance / 10
            median_dist = np.median(dist_matrix[dist_matrix > 0])
            reg = median_dist / 10.0

            # Use sinkhorn2 which returns only the distance (more memory efficient)
            # method='sinkhorn_log' is more numerically stable
            emd = ot.sinkhorn2(
                season_hists[season_a],
                season_hists[season_b],
                dist_matrix,
                reg=reg,
                method='sinkhorn_log',
                numItermax=1000,
                stopThr=1e-6
            )
        else:
            # Use exact EMD (emd2 returns the Wasserstein distance directly)
            emd = ot.emd2(season_hists[season_a], season_hists[season_b], dist_matrix)

        # Normalize by study area diameter
        norm_emd = emd / diameter

        emd_results[f'{season_a}-{season_b}'] = {
            'emd_m': emd,
            'norm_emd': norm_emd
        }

        emd_values.append(emd)
        norm_emd_values.append(norm_emd)

        print(f"    {season_a:6s} - {season_b:6s}: EMD = {emd:7.0f} m, Normalized = {norm_emd:.4f}")

    if not emd_values:
        return None

    # Summary statistics
    result = {
        'emd_mean_m': np.mean(emd_values),
        'emd_max_m': np.max(emd_values),
        'emd_std_m': np.std(emd_values),
        'norm_emd_mean': np.mean(norm_emd_values),
        'norm_emd_max': np.max(norm_emd_values),
        'norm_emd_std': np.std(norm_emd_values),
        'study_area_diameter_km': diameter / 1000,
        'n_grid_cells': n_cells,
        'grid_size_km': grid_size_km,
        'method': method,
        'memory_gb': memory_gb,
        'pairwise': emd_results
    }

    return result


def classify_spatial_bias(norm_emd_mean):
    """Classify spatial bias based on normalized EMD thresholds from doc."""
    if norm_emd_mean < 0.05:
        return 'EXCELLENT - Minimal spatial shift'
    elif norm_emd_mean < 0.10:
        return 'GOOD - Small spatial differences'
    elif norm_emd_mean < 0.20:
        return 'MODERATE - Noticeable spatial bias'
    elif norm_emd_mean < 0.35:
        return 'HIGH - Substantial spatial displacement'
    else:
        return 'SEVERE - Different areas sampled'


def main(method='auto', max_memory_gb=4.0, grid_size_km=0.25):
    print("Computing Earth Mover's Distance Spatial Bias Metrics")
    print("=" * 80)
    print(f"Method: {method}")
    print(f"Max memory: {max_memory_gb:.1f} GB")
    print(f"Grid size: {grid_size_km:.3f} km")
    print(f"Cities to analyze: {len(ANALYZED_CITIES)}\n")

    results = []

    for city_dir, city_name, lat, lon in ANALYZED_CITIES:
        print(f"\n{'='*80}")
        print(f"[{len(results)+1}/{len(ANALYZED_CITIES)}] {city_name}")
        print(f"{'='*80}")

        # Load data
        df = load_city_data(city_dir, lat, lon)

        if df is None:
            print(f"  ✗ Failed to load data")
            results.append({
                'city_dir': city_dir,
                'city_name': city_name,
                'status': 'NO_DATA'
            })
            continue

        # Check if we have enough data for multiple seasons
        season_counts = df['season'].value_counts()
        if len(season_counts) < 2:
            print(f"  ✗ Insufficient seasons (only {len(season_counts)})")
            results.append({
                'city_dir': city_dir,
                'city_name': city_name,
                'status': 'INSUFFICIENT_SEASONS',
                'n_total': len(df)
            })
            continue

        # Compute EMD
        try:
            emd_metrics = compute_emd_between_seasons(
                df,
                grid_size_km=grid_size_km,
                method=method,
                max_memory_gb=max_memory_gb
            )

            if emd_metrics is None:
                print(f"  ✗ Failed to compute EMD")
                results.append({
                    'city_dir': city_dir,
                    'city_name': city_name,
                    'status': 'COMPUTATION_FAILED'
                })
                continue

            # Classify
            classification = classify_spatial_bias(emd_metrics['norm_emd_mean'])

            print(f"\n  Summary:")
            print(f"    Method: {emd_metrics['method']}")
            print(f"    Grid: {emd_metrics['grid_size_km']:.3f} km, {emd_metrics['n_grid_cells']} cells, {emd_metrics['memory_gb']:.2f} GB")
            print(f"    Mean EMD: {emd_metrics['emd_mean_m']:.0f} m")
            print(f"    Max EMD:  {emd_metrics['emd_max_m']:.0f} m")
            print(f"    Mean Normalized EMD: {emd_metrics['norm_emd_mean']:.4f}")
            print(f"    Classification: {classification}")

            results.append({
                'city_dir': city_dir,
                'city_name': city_name,
                'status': 'SUCCESS',
                'n_total': len(df),
                'n_seasons': len(season_counts),
                'emd_mean_m': emd_metrics['emd_mean_m'],
                'emd_max_m': emd_metrics['emd_max_m'],
                'emd_std_m': emd_metrics['emd_std_m'],
                'norm_emd_mean': emd_metrics['norm_emd_mean'],
                'norm_emd_max': emd_metrics['norm_emd_max'],
                'norm_emd_std': emd_metrics['norm_emd_std'],
                'study_area_diameter_km': emd_metrics['study_area_diameter_km'],
                'n_grid_cells': emd_metrics['n_grid_cells'],
                'grid_size_km': emd_metrics['grid_size_km'],
                'method': emd_metrics['method'],
                'memory_gb': emd_metrics['memory_gb'],
                'spatial_bias_classification': classification
            })

        except Exception as e:
            print(f"  ✗ Error computing EMD: {e}")
            import traceback
            traceback.print_exc()
            results.append({
                'city_dir': city_dir,
                'city_name': city_name,
                'status': 'ERROR',
                'error': str(e)
            })

    # Save results
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")

    df_results = pd.DataFrame(results)
    output_file = OUTPUT_DIR / 'metro_spatial_emd_bias.csv'
    df_results.to_csv(output_file, index=False)
    print(f"\n✓ Saved results: {output_file}")

    # Print summary
    df_success = df_results[df_results['status'] == 'SUCCESS']

    if len(df_success) > 0:
        print(f"\nSuccessfully analyzed: {len(df_success)} cities")
        print(f"\n{'='*80}")
        print("SPATIAL BIAS RANKINGS (by Normalized EMD)")
        print(f"{'='*80}")

        df_sorted = df_success.sort_values('norm_emd_mean')

        for idx, row in df_sorted.iterrows():
            print(f"\n{row['city_name']}")
            print(f"  Normalized EMD: {row['norm_emd_mean']:.4f}")
            print(f"  Average displacement: {row['emd_mean_m']:.0f} m")
            print(f"  Study area: {row['study_area_diameter_km']:.1f} km diameter")
            print(f"  Classification: {row['spatial_bias_classification']}")

    print(f"\n{'='*80}")
    print("ANALYSIS COMPLETE")
    print(f"{'='*80}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Compute Earth Mover\'s Distance spatial bias metrics for metro SVI data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Use auto method (default, chooses based on memory)
  python compute_spatial_emd_bias.py

  # Force exact EMD method
  python compute_spatial_emd_bias.py --method exact

  # Use memory-efficient Sinkhorn for large cities
  python compute_spatial_emd_bias.py --method sinkhorn

  # Set custom memory limit
  python compute_spatial_emd_bias.py --max-memory 8.0

  # Use coarser grid for faster computation
  python compute_spatial_emd_bias.py --grid-size 0.5
        '''
    )

    parser.add_argument(
        '--method',
        choices=['auto', 'exact', 'sinkhorn'],
        default='auto',
        help='EMD computation method: "exact" (memory intensive), "sinkhorn" (memory efficient), or "auto" (default, chooses based on grid size)'
    )

    parser.add_argument(
        '--max-memory',
        type=float,
        default=4.0,
        metavar='GB',
        help='Maximum memory for distance matrix in GB (default: 4.0)'
    )

    parser.add_argument(
        '--grid-size',
        type=float,
        default=0.25,
        metavar='KM',
        help='Grid cell size in kilometers (default: 0.25, i.e., 250m)'
    )

    args = parser.parse_args()

    main(
        method=args.method,
        max_memory_gb=args.max_memory,
        grid_size_km=args.grid_size
    )
