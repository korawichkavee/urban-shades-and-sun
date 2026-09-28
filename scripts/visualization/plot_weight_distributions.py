# ABOUTME: Visualizes IPW weight distributions to show where corrections are concentrated
# ABOUTME: Creates diagnostic plots for SR-IPW, Temp-IPW, and combined weights

import sys
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import stats

# Setup paths
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'scripts'))

# Output directory
output_dir = project_root / 'outputs' / 'analysis' / 'figures'
output_dir.mkdir(parents=True, exist_ok=True)


def load_city_data(city):
    """Load IPW-adjusted data for a city."""
    data_path = project_root / 'final_run_outputs' / city / f'{city}_final_analysis_with_ipw.csv'

    print(f"Loading {city}...")
    df = pd.read_csv(data_path, low_memory=False)

    # Filter to images with people
    df = df[df['person_count'] > 0].copy()

    print(f"  {city}: {len(df):,} images with people")

    return df


def effective_sample_size(weights):
    """Compute effective sample size for weighted data."""
    valid_weights = weights[np.isfinite(weights) & (weights > 0)]
    if len(valid_weights) == 0:
        return 0
    return (valid_weights.sum() ** 2) / (valid_weights ** 2).sum()


def plot_weight_histograms(seattle_data, nyc_data, output_path):
    """
    Create 3-panel histogram plot for weight distributions.

    Panels: SR-IPW, Temp-IPW, Combined
    """
    fig, axes = plt.subplots(2, 3, figsize=(15, 10))

    weight_cols = ['w_sr_ipw', 'w_temp_ipw', 'w_combined']
    titles = ['Shadow Ratio IPW', 'Temperature IPW', 'Combined IPW']

    cities_data = [
        ('Seattle', seattle_data, '#2ca02c'),
        ('NYC', nyc_data, '#1f77b4')
    ]

    for col_idx, (weight_col, title) in enumerate(zip(weight_cols, titles)):
        for row_idx, (city_name, city_data, color) in enumerate(cities_data):
            ax = axes[row_idx, col_idx]

            # Get weights (filter valid)
            weights = city_data[weight_col].values
            weights = weights[np.isfinite(weights) & (weights > 0)]

            # Histogram
            ax.hist(weights, bins=50, color=color, alpha=0.7, edgecolor='black', linewidth=0.5)

            # Add KDE overlay
            if len(weights) > 10:
                kde = stats.gaussian_kde(weights)
                x_range = np.linspace(weights.min(), weights.max(), 200)
                kde_values = kde(x_range)
                # Scale KDE to match histogram height
                kde_scaled = kde_values * len(weights) * (weights.max() - weights.min()) / 50
                ax_kde = ax.twinx()
                ax_kde.plot(x_range, kde_values, color=color, linewidth=2, alpha=0.8)
                ax_kde.set_yticks([])

            # Statistics
            mean_w = weights.mean()
            median_w = np.median(weights)
            n_eff = effective_sample_size(city_data[weight_col])

            # Add vertical lines for mean/median
            ax.axvline(mean_w, color='red', linestyle='--', linewidth=2, label=f'Mean={mean_w:.2f}')
            ax.axvline(median_w, color='orange', linestyle=':', linewidth=2, label=f'Median={median_w:.2f}')

            # Formatting
            ax.set_xlabel('Weight', fontsize=10)
            ax.set_ylabel('Frequency', fontsize=10)
            ax.grid(True, alpha=0.3, axis='y')

            # Title with city name
            if row_idx == 0:
                ax.set_title(title, fontsize=11, fontweight='bold')

            # City label on left
            if col_idx == 0:
                ax.text(-0.3, 0.5, city_name, transform=ax.transAxes,
                       fontsize=12, fontweight='bold', rotation=90,
                       verticalalignment='center', horizontalalignment='right')

            # Add stats box
            textstr = f'N: {len(city_data):,}\nN_eff: {n_eff:,.0f}\nMean: {mean_w:.3f}\nStd: {weights.std():.3f}'
            props = dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray')
            ax.text(0.98, 0.98, textstr, transform=ax.transAxes, fontsize=8,
                   verticalalignment='top', horizontalalignment='right', bbox=props)

    plt.suptitle('IPW Weight Distributions', fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0.02, 0, 1, 0.97])

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nSaved: {output_path}")

    # PDF version
    pdf_path = output_path.with_suffix('.pdf')
    plt.savefig(pdf_path, bbox_inches='tight')
    print(f"Saved: {pdf_path}")

    plt.close()


def plot_temp_ipw_vs_utci(seattle_data, nyc_data, output_path):
    """
    Plot Temp-IPW weight vs UTCI to show asymmetric weighting pattern.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

    cities_data = [
        ('Seattle', seattle_data, '#2ca02c'),
        ('NYC', nyc_data, '#1f77b4')
    ]

    for ax, (city_name, city_data, color) in zip(axes, cities_data):
        # Filter valid data
        valid_mask = np.isfinite(city_data['w_temp_ipw']) & (city_data['w_temp_ipw'] > 0)
        df_plot = city_data[valid_mask].copy()

        # Compute binned means for cleaner visualization
        utci_bins = np.arange(-30, 31, 2)
        df_plot['utci_bin'] = pd.cut(df_plot['utci_C'], bins=utci_bins)

        binned = df_plot.groupby('utci_bin', observed=True).agg({
            'w_temp_ipw': ['mean', 'std', 'count'],
            'utci_C': 'mean'
        }).reset_index()

        binned.columns = ['utci_bin', 'weight_mean', 'weight_std', 'count', 'utci_center']

        # Filter bins with enough data
        binned = binned[binned['count'] >= 10]

        # Plot binned means with error bars
        ax.errorbar(binned['utci_center'], binned['weight_mean'],
                   yerr=binned['weight_std'] / np.sqrt(binned['count']),
                   fmt='o-', color=color, linewidth=2, markersize=6, alpha=0.8,
                   capsize=4, elinewidth=1.5)

        # Add baseline reference at weight=1.0, UTCI=20°C
        ax.axhline(1.0, color='gray', linestyle='--', alpha=0.5, linewidth=1.5)
        ax.axvline(20.0, color='gray', linestyle='--', alpha=0.5, linewidth=1.5)

        # Add shaded regions for interpretation
        ax.axvspan(-30, 20, alpha=0.1, color='blue', label='Cold: downweight')
        ax.axvspan(20, 30, alpha=0.1, color='red', label='Hot: upweight')

        # Formatting
        ax.set_xlabel('UTCI (°C)', fontsize=11, fontweight='bold')
        ax.set_title(f'{city_name}', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(-30, 30)

        if ax == axes[0]:
            ax.set_ylabel('Temperature IPW Weight', fontsize=11, fontweight='bold')

        # Add annotation
        textstr = 'Asymmetric weighting:\n• T < 20°C: w < 1.0\n• T = 20°C: w = 1.0\n• T > 20°C: w > 1.0'
        props = dict(boxstyle='round', facecolor='wheat', alpha=0.8, edgecolor='gray')
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
               verticalalignment='top', bbox=props, family='monospace')

    plt.suptitle('Temperature IPW Weight vs UTCI (Binned Means)', fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")

    # PDF version
    pdf_path = output_path.with_suffix('.pdf')
    plt.savefig(pdf_path, bbox_inches='tight')
    print(f"Saved: {pdf_path}")

    plt.close()


def plot_sr_ipw_vs_shadow_ratio(seattle_data, nyc_data, output_path):
    """
    Plot SR-IPW vs shadow_ratio to show hyperbolic relationship.
    """
    fig, axes = plt.subplots(1, 2, figsize=(14, 6), sharey=True)

    cities_data = [
        ('Seattle', seattle_data, '#2ca02c'),
        ('NYC', nyc_data, '#1f77b4')
    ]

    for ax, (city_name, city_data, color) in zip(axes, cities_data):
        # Filter valid data
        valid_mask = (np.isfinite(city_data['w_sr_ipw']) &
                     (city_data['w_sr_ipw'] > 0) &
                     (city_data['shadow_ratio'] > 0))
        df_plot = city_data[valid_mask].copy()

        # Sample if too many points
        if len(df_plot) > 10000:
            df_plot = df_plot.sample(10000, random_state=42)

        # Scatter plot
        ax.scatter(df_plot['shadow_ratio'], df_plot['w_sr_ipw'],
                  alpha=0.2, s=10, color=color)

        # Overlay theoretical relationship: w = 1/SR (capped)
        sr_range = np.linspace(0.05, 1.0, 200)
        w_theoretical = 1.0 / sr_range

        # Apply 95th percentile cap from data
        cap = df_plot['w_sr_ipw'].quantile(0.95)
        w_capped = np.minimum(w_theoretical, cap)

        ax.plot(sr_range, w_capped, 'r--', linewidth=2, label=f'w = 1/SR (capped at {cap:.1f})')

        # Formatting
        ax.set_xlabel('Shadow Ratio', fontsize=11, fontweight='bold')
        ax.set_title(f'{city_name}', fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0.0, 1.0)
        ax.legend(loc='upper right', framealpha=0.9, fontsize=9)

        if ax == axes[0]:
            ax.set_ylabel('Shadow Ratio IPW Weight', fontsize=11, fontweight='bold')

        # Add stats
        textstr = f'Filter: SR ≥ 0.05\nMean: {df_plot["w_sr_ipw"].mean():.2f}\nMedian: {df_plot["w_sr_ipw"].median():.2f}\nCap: {cap:.2f}'
        props = dict(boxstyle='round', facecolor='white', alpha=0.8, edgecolor='gray')
        ax.text(0.02, 0.98, textstr, transform=ax.transAxes, fontsize=9,
               verticalalignment='top', bbox=props)

    plt.suptitle('Shadow Ratio IPW Weight vs Shadow Ratio', fontsize=14, fontweight='bold')
    plt.tight_layout(rect=[0, 0, 1, 0.96])

    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Saved: {output_path}")

    # PDF version
    pdf_path = output_path.with_suffix('.pdf')
    plt.savefig(pdf_path, bbox_inches='tight')
    print(f"Saved: {pdf_path}")

    plt.close()


def main():
    print("=" * 60)
    print("PRIORITY 5: IPW Weight Distribution Plots")
    print("=" * 60)

    # Load data
    seattle = load_city_data('seattle')
    nyc = load_city_data('new-york-city')

    # 1. Weight histograms
    output_hist = output_dir / 'weight_distributions_histograms.png'
    plot_weight_histograms(seattle, nyc, output_hist)

    # 2. Temp-IPW vs UTCI
    output_temp = output_dir / 'temp_ipw_vs_utci.png'
    plot_temp_ipw_vs_utci(seattle, nyc, output_temp)

    # 3. SR-IPW vs Shadow Ratio
    output_sr = output_dir / 'sr_ipw_vs_shadow_ratio.png'
    plot_sr_ipw_vs_shadow_ratio(seattle, nyc, output_sr)

    print("\n" + "=" * 60)
    print("Done!")
    print("=" * 60)


if __name__ == '__main__':
    main()
