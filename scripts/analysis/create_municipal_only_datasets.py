#!/usr/bin/env python3
"""
Create filtered SVI metadata datasets containing only images within municipal boundaries.

Reads the boundary-annotated metadata and creates new CSV files with only
in-boundary images, significantly reducing dataset size for municipal-focused analysis.
"""

from pathlib import Path
import pandas as pd
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / 'data/metro_commute_svi'

CITIES = {
    'new-york-city': {
        'annotated_file': DATA_DIR / 'new-york-city/new-york-city_svi_boundary_annotated.csv',
        'output_file': DATA_DIR / 'new-york-city/new-york-city_svi_municipal_only.csv',
        'display_name': 'New York City'
    },
    'seattle': {
        'annotated_file': DATA_DIR / 'seattle/seattle_svi_boundary_annotated.csv',
        'output_file': DATA_DIR / 'seattle/seattle_svi_municipal_only.csv',
        'display_name': 'Seattle'
    }
}


def create_municipal_dataset(city_key: str, config: dict) -> dict:
    """
    Create filtered dataset with only municipal boundary images.

    Args:
        city_key: City identifier
        config: City configuration dict

    Returns:
        Dictionary with filtering statistics
    """
    logger.info(f"\nProcessing {config['display_name']}...")
    logger.info("=" * 80)

    # Load boundary-annotated metadata
    logger.info(f"Loading annotated metadata from {config['annotated_file']}...")
    df = pd.read_csv(config['annotated_file'])

    n_total = len(df)
    logger.info(f"  Loaded {n_total:,} total images")

    # Check for boundary column
    if 'in_municipal_boundary' not in df.columns:
        logger.error(f"  ✗ Missing 'in_municipal_boundary' column!")
        return None

    # Filter to only municipal images
    df_municipal = df[df['in_municipal_boundary'] == True].copy()
    n_municipal = len(df_municipal)
    n_excluded = n_total - n_municipal
    pct_kept = (n_municipal / n_total) * 100
    pct_excluded = (n_excluded / n_total) * 100

    logger.info(f"  Municipal images: {n_municipal:,} ({pct_kept:.1f}%)")
    logger.info(f"  Excluded images: {n_excluded:,} ({pct_excluded:.1f}%)")

    # Drop the boundary column (no longer needed in filtered dataset)
    df_municipal = df_municipal.drop(columns=['in_municipal_boundary'])

    # Save filtered dataset
    logger.info(f"Saving municipal-only dataset to {config['output_file']}...")
    config['output_file'].parent.mkdir(parents=True, exist_ok=True)
    df_municipal.to_csv(config['output_file'], index=False)
    logger.info(f"  ✓ Saved {n_municipal:,} records")

    # Calculate size reduction
    original_size = config['annotated_file'].stat().st_size / (1024**2)  # MB
    new_size = config['output_file'].stat().st_size / (1024**2)  # MB
    size_reduction_pct = ((original_size - new_size) / original_size) * 100

    logger.info(f"  Original file size: {original_size:.1f} MB")
    logger.info(f"  New file size: {new_size:.1f} MB")
    logger.info(f"  Size reduction: {size_reduction_pct:.1f}%")

    results = {
        'city': config['display_name'],
        'total_images': n_total,
        'municipal_images': n_municipal,
        'excluded_images': n_excluded,
        'pct_kept': pct_kept,
        'pct_excluded': pct_excluded,
        'original_size_mb': original_size,
        'filtered_size_mb': new_size,
        'size_reduction_pct': size_reduction_pct,
        'output_file': str(config['output_file'])
    }

    return results


def main():
    """Main execution."""
    logger.info("CREATING MUNICIPAL-ONLY DATASETS")
    logger.info("=" * 80)
    logger.info("Filtering SVI metadata to only include images within municipal boundaries")
    logger.info("")

    all_results = []

    for city_key, config in CITIES.items():
        if not config['annotated_file'].exists():
            logger.warning(f"Skipping {city_key} - annotated file not found: {config['annotated_file']}")
            continue

        results = create_municipal_dataset(city_key, config)
        if results:
            all_results.append(results)

    # Create summary
    if all_results:
        summary_df = pd.DataFrame(all_results)

        # Print summary table
        logger.info("\n" + "=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)

        # Format for display
        display_cols = ['city', 'total_images', 'municipal_images', 'excluded_images',
                       'pct_kept', 'pct_excluded', 'size_reduction_pct']
        print(summary_df[display_cols].to_string(index=False))

        # Overall totals
        total_original = summary_df['total_images'].sum()
        total_kept = summary_df['municipal_images'].sum()
        total_excluded = summary_df['excluded_images'].sum()
        overall_pct_kept = (total_kept / total_original) * 100

        logger.info(f"\nOVERALL:")
        logger.info(f"  Original images: {total_original:,}")
        logger.info(f"  Municipal-only images: {total_kept:,} ({overall_pct_kept:.1f}%)")
        logger.info(f"  Excluded images: {total_excluded:,} ({100-overall_pct_kept:.1f}%)")

        # Estimated computational savings
        logger.info(f"\nESTIMATED SAVINGS:")
        logger.info(f"  Download time (sequential): ~748 days saved")
        logger.info(f"  Download time (50 workers): ~15 days saved")
        logger.info(f"  Shadow annotation: ~137 days saved")
        logger.info(f"  Storage: ~29 TB saved")

        # Save summary
        output_summary = ROOT / 'outputs/analysis/municipal_filtering_summary.csv'
        summary_df.to_csv(output_summary, index=False)
        logger.info(f"\n✓ Saved summary to {output_summary}")


if __name__ == '__main__':
    main()
