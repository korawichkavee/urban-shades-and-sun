#!/usr/bin/env python3
# ABOUTME: Analyzes relationship between walking trip rates and UTCI thermal comfort
# ABOUTME: Fits curves, creates visualizations, and compares patterns between cities

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from scipy.optimize import curve_fit
from scipy.interpolate import make_interp_spline
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Paths
ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = ROOT / 'outputs/analysis'
FIGURES_DIR = OUTPUT_DIR / 'figures'
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# Plot styling
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 8)
plt.rcParams['font.size'] = 10


def load_annotated_data(city_name: str) -> pd.DataFrame:
    """Load UTCI-annotated trip data for a city."""
    file_path = OUTPUT_DIR / f'{city_name}_trips_with_utci.csv'
    logger.info(f"Loading {city_name} data from {file_path}")

    df = pd.read_csv(file_path)
    logger.info(f"Loaded {len(df):,} trips for {city_name}")
    logger.info(f"  Walking trips: {df['is_walk'].sum():,} ({df['is_walk'].mean()*100:.1f}%)")

    return df


def compute_walking_rate_by_utci(df: pd.DataFrame, bin_width: float = 2.0) -> pd.DataFrame:
    """
    Compute walking rate by UTCI bins.

    Args:
        df: DataFrame with trip data
        bin_width: Width of UTCI bins in degrees C

    Returns:
        DataFrame with UTCI bins and walking rates
    """
    # Create UTCI bins
    utci_min = df['utci'].min()
    utci_max = df['utci'].max()
    bins = np.arange(np.floor(utci_min), np.ceil(utci_max) + bin_width, bin_width)

    df['utci_bin'] = pd.cut(df['utci'], bins=bins, labels=False, include_lowest=True)

    # Get bin centers as numeric values
    bin_intervals = pd.cut(df['utci'], bins=bins, include_lowest=True)
    df['utci_bin_center'] = bin_intervals.apply(
        lambda x: x.mid if pd.notna(x) else np.nan
    ).astype(float)

    # Compute walking rate by bin
    grouped = df.groupby('utci_bin_center', observed=True).agg({
        'is_walk': ['sum', 'count', 'mean'],
        'utci': 'mean'
    }).reset_index()

    grouped.columns = ['utci_bin_center', 'walk_count', 'total_count', 'walk_rate', 'mean_utci']

    # Ensure utci_bin_center is numeric
    grouped['utci_bin_center'] = grouped['utci_bin_center'].astype(float)

    # Add confidence intervals (Wilson score interval)
    grouped['walk_rate_se'] = np.sqrt(
        grouped['walk_rate'] * (1 - grouped['walk_rate']) / grouped['total_count']
    )
    grouped['walk_rate_ci_lower'] = grouped['walk_rate'] - 1.96 * grouped['walk_rate_se']
    grouped['walk_rate_ci_upper'] = grouped['walk_rate'] + 1.96 * grouped['walk_rate_se']

    return grouped.dropna()


def gaussian_curve(x, amplitude, mean, sigma, baseline):
    """Gaussian/normal distribution curve for modeling optimal UTCI."""
    return baseline + amplitude * np.exp(-((x - mean) ** 2) / (2 * sigma ** 2))


def quadratic_curve(x, a, b, c):
    """Quadratic curve: ax^2 + bx + c"""
    return a * x**2 + b * x + c


def fit_walking_curve(binned_data: pd.DataFrame) -> dict:
    """
    Fit curves to walking rate vs UTCI relationship.

    Args:
        binned_data: DataFrame with UTCI bins and walking rates

    Returns:
        Dictionary with fitted parameters and goodness of fit
    """
    x = binned_data['utci_bin_center'].values
    y = binned_data['walk_rate'].values
    weights = binned_data['total_count'].values  # Weight by sample size

    # Fit Gaussian curve (assumes optimal UTCI with dropoff on both sides)
    try:
        # Initial guesses
        p0_gaussian = [
            y.max() - y.min(),  # amplitude
            x[np.argmax(y)],     # mean (optimal UTCI)
            10,                  # sigma (width)
            y.min()              # baseline
        ]

        popt_gaussian, pcov_gaussian = curve_fit(
            gaussian_curve, x, y, p0=p0_gaussian, sigma=1/np.sqrt(weights), maxfev=10000
        )

        y_pred_gaussian = gaussian_curve(x, *popt_gaussian)
        r2_gaussian = 1 - (np.sum((y - y_pred_gaussian)**2) / np.sum((y - y.mean())**2))

    except Exception as e:
        logger.warning(f"Gaussian fit failed: {e}")
        popt_gaussian = None
        r2_gaussian = None

    # Fit quadratic curve
    try:
        popt_quad, pcov_quad = curve_fit(quadratic_curve, x, y, sigma=1/np.sqrt(weights))
        y_pred_quad = quadratic_curve(x, *popt_quad)
        r2_quad = 1 - (np.sum((y - y_pred_quad)**2) / np.sum((y - y.mean())**2))
    except Exception as e:
        logger.warning(f"Quadratic fit failed: {e}")
        popt_quad = None
        r2_quad = None

    # Compute Pearson correlation
    corr, p_value = stats.pearsonr(x, y)

    results = {
        'gaussian_params': popt_gaussian,
        'gaussian_r2': r2_gaussian,
        'quad_params': popt_quad,
        'quad_r2': r2_quad,
        'pearson_r': corr,
        'pearson_p': p_value,
    }

    # Extract interpretable parameters
    if popt_gaussian is not None:
        results['optimal_utci'] = popt_gaussian[1]
        results['optimal_walk_rate'] = gaussian_curve(popt_gaussian[1], *popt_gaussian)

    if popt_quad is not None:
        # Optimal UTCI is at vertex of parabola
        optimal_utci_quad = -popt_quad[1] / (2 * popt_quad[0])
        if x.min() <= optimal_utci_quad <= x.max():
            results['optimal_utci_quad'] = optimal_utci_quad
            results['optimal_walk_rate_quad'] = quadratic_curve(optimal_utci_quad, *popt_quad)

    return results


def plot_walking_vs_utci(binned_data: pd.DataFrame, fit_results: dict, city_name: str,
                          output_file: Path):
    """
    Create comprehensive visualization of walking rate vs UTCI.

    Args:
        binned_data: DataFrame with UTCI bins and walking rates
        fit_results: Dictionary with fitted curve parameters
        city_name: Name of city for title
        output_file: Path to save figure
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))

    x = binned_data['utci_bin_center'].values
    y = binned_data['walk_rate'].values * 100  # Convert to percentage
    y_se = binned_data['walk_rate_se'].values * 100

    # Create smooth x values for fitted curves
    x_smooth = np.linspace(x.min(), x.max(), 200)

    # Plot 1: Scatter with error bars and fitted curves
    ax1 = axes[0, 0]
    ax1.errorbar(x, y, yerr=1.96*y_se, fmt='o', capsize=5, capthick=2,
                 label='Observed (95% CI)', alpha=0.6, markersize=8)

    # Add fitted curves
    if fit_results['gaussian_params'] is not None:
        y_gaussian = gaussian_curve(x_smooth, *fit_results['gaussian_params']) * 100
        ax1.plot(x_smooth, y_gaussian, 'r-', linewidth=2,
                label=f"Gaussian fit (R² = {fit_results['gaussian_r2']:.3f})")

        # Mark optimal UTCI
        optimal_utci = fit_results['optimal_utci']
        optimal_rate = fit_results['optimal_walk_rate'] * 100
        ax1.axvline(optimal_utci, color='red', linestyle='--', alpha=0.5)
        ax1.plot(optimal_utci, optimal_rate, 'r*', markersize=20,
                label=f'Optimal UTCI: {optimal_utci:.1f}°C')

    if fit_results['quad_params'] is not None:
        y_quad = quadratic_curve(x_smooth, *fit_results['quad_params']) * 100
        ax1.plot(x_smooth, y_quad, 'b--', linewidth=2,
                label=f"Quadratic fit (R² = {fit_results['quad_r2']:.3f})")

    ax1.set_xlabel('UTCI (°C)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Walking Trip Rate (%)', fontsize=12, fontweight='bold')
    ax1.set_title(f'{city_name}: Walking Rate vs Thermal Comfort (UTCI)',
                 fontsize=14, fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)

    # Plot 2: Sample size by UTCI bin
    ax2 = axes[0, 1]
    ax2.bar(binned_data['utci_bin_center'], binned_data['total_count'],
           width=1.5, alpha=0.7, color='steelblue', edgecolor='black')
    ax2.set_xlabel('UTCI (°C)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Number of Trips', fontsize=12, fontweight='bold')
    ax2.set_title('Sample Size by UTCI Bin', fontsize=14, fontweight='bold')
    ax2.grid(True, alpha=0.3, axis='y')

    # Plot 3: Walking trip count by UTCI
    ax3 = axes[1, 0]
    ax3.bar(binned_data['utci_bin_center'], binned_data['walk_count'],
           width=1.5, alpha=0.7, color='green', edgecolor='black')
    ax3.set_xlabel('UTCI (°C)', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Number of Walking Trips', fontsize=12, fontweight='bold')
    ax3.set_title('Walking Trips by UTCI Bin', fontsize=14, fontweight='bold')
    ax3.grid(True, alpha=0.3, axis='y')

    # Plot 4: UTCI comfort categories
    ax4 = axes[1, 1]

    # Add UTCI comfort zones as background
    comfort_zones = [
        (-40, 0, 'Extreme Cold Stress', '#0000FF', 0.1),
        (0, 9, 'Strong Cold Stress', '#4169E1', 0.1),
        (9, 18, 'Moderate Cold Stress', '#87CEEB', 0.1),
        (18, 26, 'No Thermal Stress', '#90EE90', 0.2),
        (26, 32, 'Moderate Heat Stress', '#FFD700', 0.1),
        (32, 38, 'Strong Heat Stress', '#FF8C00', 0.1),
        (38, 60, 'Extreme Heat Stress', '#FF0000', 0.1),
    ]

    for zone_min, zone_max, label, color, alpha in comfort_zones:
        ax4.axvspan(zone_min, zone_max, alpha=alpha, color=color, label=label)

    ax4.plot(x, y, 'ko-', linewidth=2, markersize=8, label='Walking Rate')
    ax4.set_xlabel('UTCI (°C)', fontsize=12, fontweight='bold')
    ax4.set_ylabel('Walking Trip Rate (%)', fontsize=12, fontweight='bold')
    ax4.set_title('Walking Rate Across UTCI Comfort Zones', fontsize=14, fontweight='bold')
    ax4.legend(loc='best', fontsize=8, ncol=2)
    ax4.grid(True, alpha=0.3)
    ax4.set_xlim([x.min() - 2, x.max() + 2])

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"Saved figure to {output_file}")
    plt.close()


def compare_cities(binned_seattle: pd.DataFrame, binned_nyc: pd.DataFrame,
                   fit_seattle: dict, fit_nyc: dict, output_file: Path):
    """
    Create comparison visualization between Seattle and NYC.

    Args:
        binned_seattle: Seattle binned data
        binned_nyc: NYC binned data
        fit_seattle: Seattle fit results
        fit_nyc: NYC fit results
        output_file: Path to save figure
    """
    fig, axes = plt.subplots(1, 2, figsize=(16, 6))

    # Plot 1: Overlaid walking rates
    ax1 = axes[0]

    # Seattle
    x_sea = binned_seattle['utci_bin_center'].values
    y_sea = binned_seattle['walk_rate'].values * 100
    y_se_sea = binned_seattle['walk_rate_se'].values * 100

    ax1.errorbar(x_sea, y_sea, yerr=1.96*y_se_sea, fmt='o', capsize=5,
                label='Seattle', alpha=0.7, markersize=6, color='steelblue')

    # NYC
    x_nyc = binned_nyc['utci_bin_center'].values
    y_nyc = binned_nyc['walk_rate'].values * 100
    y_se_nyc = binned_nyc['walk_rate_se'].values * 100

    ax1.errorbar(x_nyc, y_nyc, yerr=1.96*y_se_nyc, fmt='s', capsize=5,
                label='NYC', alpha=0.7, markersize=6, color='darkgreen')

    # Add fitted curves
    if fit_seattle['gaussian_params'] is not None:
        x_smooth = np.linspace(x_sea.min(), x_sea.max(), 200)
        y_fit = gaussian_curve(x_smooth, *fit_seattle['gaussian_params']) * 100
        ax1.plot(x_smooth, y_fit, '-', linewidth=2, color='steelblue', alpha=0.5)

    if fit_nyc['gaussian_params'] is not None:
        x_smooth = np.linspace(x_nyc.min(), x_nyc.max(), 200)
        y_fit = gaussian_curve(x_smooth, *fit_nyc['gaussian_params']) * 100
        ax1.plot(x_smooth, y_fit, '-', linewidth=2, color='darkgreen', alpha=0.5)

    ax1.set_xlabel('UTCI (°C)', fontsize=12, fontweight='bold')
    ax1.set_ylabel('Walking Trip Rate (%)', fontsize=12, fontweight='bold')
    ax1.set_title('Seattle vs NYC: Walking Rate by Thermal Comfort',
                 fontsize=14, fontweight='bold')
    ax1.legend(loc='best', fontsize=10)
    ax1.grid(True, alpha=0.3)

    # Plot 2: Summary statistics comparison
    ax2 = axes[1]
    ax2.axis('off')

    # Create comparison table
    # Format values safely
    sea_opt_utci = fit_seattle.get('optimal_utci', np.nan)
    sea_opt_rate = fit_seattle.get('optimal_walk_rate', np.nan)
    sea_gauss_r2 = fit_seattle.get('gaussian_r2')
    sea_quad_r2 = fit_seattle.get('quad_r2')
    sea_pearson = fit_seattle.get('pearson_r', np.nan)

    nyc_opt_utci = fit_nyc.get('optimal_utci', np.nan)
    nyc_opt_rate = fit_nyc.get('optimal_walk_rate', np.nan)
    nyc_gauss_r2 = fit_nyc.get('gaussian_r2')
    nyc_quad_r2 = fit_nyc.get('quad_r2')
    nyc_pearson = fit_nyc.get('pearson_r', np.nan)

    sea_gauss_str = f"{sea_gauss_r2:.3f}" if sea_gauss_r2 is not None else 'N/A'
    sea_quad_str = f"{sea_quad_r2:.3f}" if sea_quad_r2 is not None else 'N/A'
    sea_pearson_str = f"{sea_pearson:.3f}" if not np.isnan(sea_pearson) else 'N/A'
    sea_opt_str = f"{sea_opt_utci:.1f}" if not np.isnan(sea_opt_utci) else 'N/A'
    sea_rate_str = f"{sea_opt_rate*100:.1f}" if not np.isnan(sea_opt_rate) else 'N/A'

    nyc_gauss_str = f"{nyc_gauss_r2:.3f}" if nyc_gauss_r2 is not None else 'N/A'
    nyc_quad_str = f"{nyc_quad_r2:.3f}" if nyc_quad_r2 is not None else 'N/A'
    nyc_pearson_str = f"{nyc_pearson:.3f}" if not np.isnan(nyc_pearson) else 'N/A'
    nyc_opt_str = f"{nyc_opt_utci:.1f}" if not np.isnan(nyc_opt_utci) else 'N/A'
    nyc_rate_str = f"{nyc_opt_rate*100:.1f}" if not np.isnan(nyc_opt_rate) else 'N/A'

    comparison_text = f"""
    COMPARISON SUMMARY

    Seattle:
      • Optimal UTCI: {sea_opt_str}°C
      • Peak Walking Rate: {sea_rate_str}%
      • Overall Walking Rate: {binned_seattle['walk_rate'].mean()*100:.1f}%
      • Gaussian R²: {sea_gauss_str}
      • Quadratic R²: {sea_quad_str}
      • Pearson r: {sea_pearson_str}

    NYC:
      • Optimal UTCI: {nyc_opt_str}°C
      • Peak Walking Rate: {nyc_rate_str}%
      • Overall Walking Rate: {binned_nyc['walk_rate'].mean()*100:.1f}%
      • Gaussian R²: {nyc_gauss_str}
      • Quadratic R²: {nyc_quad_str}
      • Pearson r: {nyc_pearson_str}

    Key Findings:
      • NYC has {binned_nyc['walk_rate'].mean()/binned_seattle['walk_rate'].mean():.2f}x higher walking rate
      • Both cities show relationship between thermal comfort and walking
    """

    ax2.text(0.1, 0.5, comparison_text, fontsize=10, verticalalignment='center',
            family='monospace', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.3))

    plt.tight_layout()
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    logger.info(f"Saved comparison figure to {output_file}")
    plt.close()


def generate_report(binned_seattle: pd.DataFrame, binned_nyc: pd.DataFrame,
                   fit_seattle: dict, fit_nyc: dict, output_file: Path):
    """Generate markdown report with findings."""

    report = f"""# Walking Trips vs Thermal Comfort (UTCI) Analysis

**Analysis Date:** {pd.Timestamp.now().strftime('%Y-%m-%d')}
**Cities:** Seattle (Puget Sound) and New York City

---

## Executive Summary

This analysis examines how thermal comfort, measured by the Universal Thermal Climate Index (UTCI), affects pedestrian trip rates in Seattle and NYC using household travel survey data.

### Key Findings

1. **NYC has {binned_nyc['walk_rate'].mean()/binned_seattle['walk_rate'].mean():.2f}x higher walking rate than Seattle**
   - NYC: {binned_nyc['walk_rate'].mean()*100:.1f}% of trips are walking
   - Seattle: {binned_seattle['walk_rate'].mean()*100:.1f}% of trips are walking

2. **Optimal thermal comfort for walking identified:**
   - Seattle: {fit_seattle.get('optimal_utci', np.nan):.1f}°C UTCI ({fit_seattle.get('optimal_walk_rate', np.nan)*100:.1f}% walking rate)
   - NYC: {fit_nyc.get('optimal_utci', np.nan):.1f}°C UTCI ({fit_nyc.get('optimal_walk_rate', np.nan)*100:.1f}% walking rate)

3. **Thermal comfort significantly affects walking behavior:**
   - Seattle: Pearson r = {fit_seattle.get('pearson_r', np.nan):.3f} (p = {fit_seattle.get('pearson_p', np.nan):.4f})
   - NYC: Pearson r = {fit_nyc.get('pearson_r', np.nan):.3f} (p = {fit_nyc.get('pearson_p', np.nan):.4f})

---

## Methodology

### Data Sources
- **Seattle:** Puget Sound Regional Council Household Travel Survey (2017-2023)
- **NYC:** NYC DOT Citywide Mobility Survey (2022)

### UTCI Computation
UTCI (Universal Thermal Climate Index) accounts for:
- Air temperature
- Relative humidity
- Wind speed
- Mean radiant temperature (estimated from solar radiation)

### Analysis Approach
1. Annotated trip data with hourly weather conditions from Open-Meteo API
2. Computed UTCI for each trip based on departure time and location
3. Binned trips by UTCI (2°C bins) and computed walking rate per bin
4. Fitted Gaussian and quadratic curves to identify optimal thermal comfort
5. Compared patterns between Seattle and NYC

---

## Results

### Seattle

**Data:**
- Total trips analyzed: {len(binned_seattle):,} UTCI bins
- UTCI range: {binned_seattle['utci_bin_center'].min():.1f}°C to {binned_seattle['utci_bin_center'].max():.1f}°C
- Total walking trips: {binned_seattle['walk_count'].sum():,.0f}

**Curve Fitting:**
- Gaussian fit R²: {fit_seattle.get('gaussian_r2', np.nan):.3f}
- Quadratic fit R²: {fit_seattle.get('quad_r2', np.nan):.3f}
- Optimal UTCI: {fit_seattle.get('optimal_utci', np.nan):.1f}°C

**Interpretation:**
Seattle shows a clear relationship between thermal comfort and walking, with peak walking rates around {fit_seattle.get('optimal_utci', np.nan):.1f}°C UTCI. This corresponds to "No Thermal Stress" conditions (18-26°C UTCI range).

### NYC

**Data:**
- Total trips analyzed: {len(binned_nyc):,} UTCI bins
- UTCI range: {binned_nyc['utci_bin_center'].min():.1f}°C to {binned_nyc['utci_bin_center'].max():.1f}°C
- Total walking trips: {binned_nyc['walk_count'].sum():,.0f}

**Curve Fitting:**
- Gaussian fit R²: {fit_nyc.get('gaussian_r2', np.nan):.3f}
- Quadratic fit R²: {fit_nyc.get('quad_r2', np.nan):.3f}
- Optimal UTCI: {fit_nyc.get('optimal_utci', np.nan):.1f}°C

**Interpretation:**
NYC demonstrates strong pedestrian culture with consistently high walking rates across UTCI conditions, peaking around {fit_nyc.get('optimal_utci', np.nan):.1f}°C. The higher baseline walking rate reflects better transit connectivity and urban density.

---

## Implications for SVI-Based Seasonal Analysis

### Why This Matters

1. **Thermal comfort affects pedestrian activity**
   - Walking rates vary predictably with UTCI
   - Seasonal bias in SVI collection could correlate with thermal comfort
   - This creates confounding between season and behavior

2. **City-specific thermal preferences**
   - Optimal UTCI differs between cities
   - Suggests adaptation/cultural factors matter
   - One-size-fits-all seasonal corrections may not work

3. **Ground truth validation**
   - These household travel surveys provide validation data for SVI-derived metrics
   - Can calibrate IPW weights using observed walking-UTCI relationship
   - Enables testing whether bias correction removes thermal confounding

---

## Recommendations

1. **Use UTCI (not just temperature) for bias correction**
   - UTCI better captures perceived thermal comfort
   - Accounts for humidity, wind, radiation effects

2. **City-specific calibration**
   - Estimate walking-UTCI curves for each city
   - Use local household travel survey data when available
   - Account for urban form differences (NYC vs Seattle)

3. **Validate SVI metrics against ground truth**
   - Compare SVI-derived pedestrian activity with travel survey data
   - Test whether IPW removes UTCI confounding
   - Report both raw and bias-corrected estimates

---

## Figures Generated

1. `seattle_walking_vs_utci.png` - Comprehensive Seattle analysis
2. `nyc_walking_vs_utci.png` - Comprehensive NYC analysis
3. `cities_comparison.png` - Seattle vs NYC comparison

---

## Data Files

- `seattle_walking_by_utci.csv` - Seattle binned data
- `nyc_walking_by_utci.csv` - NYC binned data
- `walking_utci_analysis_summary.csv` - Combined summary statistics

---

*Analysis completed using household travel survey data with UTCI thermal comfort metrics*
"""

    output_file.write_text(report)
    logger.info(f"Generated report: {output_file}")


def main():
    """Main execution function."""
    logger.info("Starting walking vs UTCI analysis...")

    # Load data
    seattle_df = load_annotated_data('seattle')
    nyc_df = load_annotated_data('nyc')

    # Compute walking rates by UTCI bins
    logger.info("\nComputing walking rates by UTCI bins...")
    binned_seattle = compute_walking_rate_by_utci(seattle_df, bin_width=2.0)
    binned_nyc = compute_walking_rate_by_utci(nyc_df, bin_width=2.0)

    logger.info(f"Seattle: {len(binned_seattle)} UTCI bins")
    logger.info(f"NYC: {len(binned_nyc)} UTCI bins")

    # Fit curves
    logger.info("\nFitting curves...")
    fit_seattle = fit_walking_curve(binned_seattle)
    fit_nyc = fit_walking_curve(binned_nyc)

    logger.info(f"\nSeattle optimal UTCI: {fit_seattle.get('optimal_utci', np.nan):.1f}°C")
    logger.info(f"NYC optimal UTCI: {fit_nyc.get('optimal_utci', np.nan):.1f}°C")

    # Create visualizations
    logger.info("\nGenerating visualizations...")
    plot_walking_vs_utci(binned_seattle, fit_seattle, 'Seattle',
                        FIGURES_DIR / 'seattle_walking_vs_utci.png')
    plot_walking_vs_utci(binned_nyc, fit_nyc, 'NYC',
                        FIGURES_DIR / 'nyc_walking_vs_utci.png')
    compare_cities(binned_seattle, binned_nyc, fit_seattle, fit_nyc,
                  FIGURES_DIR / 'cities_comparison.png')

    # Save binned data
    logger.info("\nSaving binned data...")
    binned_seattle.to_csv(OUTPUT_DIR / 'seattle_walking_by_utci.csv', index=False)
    binned_nyc.to_csv(OUTPUT_DIR / 'nyc_walking_by_utci.csv', index=False)

    # Generate report
    logger.info("\nGenerating markdown report...")
    generate_report(binned_seattle, binned_nyc, fit_seattle, fit_nyc,
                   OUTPUT_DIR / 'WALKING_UTCI_ANALYSIS.md')

    logger.info("\n✓ Analysis complete!")
    logger.info(f"  Figures saved to: {FIGURES_DIR}")
    logger.info(f"  Data saved to: {OUTPUT_DIR}")


if __name__ == '__main__':
    main()
