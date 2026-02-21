# ABOUTME: Plots UTCI temperature vs photo count for State College, PA.
# ABOUTME: Shows overall distribution and per-creator breakdown using histogram/KDE plots.

import sys
from pathlib import Path

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.stats import gaussian_kde

INPUT_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_utci.csv'
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / 'outputs' / 'plots' / 'state_college' / 'photo_counts'

# Minimum photos a creator needs to get their own panel
MIN_PHOTOS_FOR_PANEL = 200

# Colorblind-friendly palette
PALETTE = [
    '#1f77b4', '#ff7f0e', '#2ca02c', '#d62728',
    '#9467bd', '#8c564b', '#e377c2', '#17becf',
]


def load_data():
    """Load CSV and keep rows with valid UTCI."""
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    df = df[df['utci_C'].notna()].copy()
    df['captured_at'] = pd.to_datetime(df['captured_at'], format='mixed')
    return df


def _bin_utci(series, bin_width=2.0):
    """Return bin centres and counts for a UTCI series."""
    vmin = np.floor(series.min() / bin_width) * bin_width
    vmax = np.ceil(series.max() / bin_width) * bin_width
    bins = np.arange(vmin, vmax + bin_width, bin_width)
    counts, edges = np.histogram(series, bins=bins)
    centres = (edges[:-1] + edges[1:]) / 2
    return centres, counts


def plot_overall(df, out_dir):
    """Bar histogram of UTCI vs photo count (all photos), with KDE overlay."""
    out_dir.mkdir(parents=True, exist_ok=True)

    utci = df['utci_C'].values
    centres, counts = _bin_utci(pd.Series(utci))

    fig, axes = plt.subplots(2, 1, figsize=(12, 10),
                              gridspec_kw={'height_ratios': [3, 1]})

    # Top: histogram bars
    ax = axes[0]
    ax.bar(centres, counts, width=2.0 * 0.85, color='steelblue', alpha=0.7,
           label=f'Photo count (n={len(df):,})')

    # KDE overlay (scaled to match bar heights)
    if len(utci) > 10:
        kde = gaussian_kde(utci, bw_method=0.15)
        x_kde = np.linspace(utci.min(), utci.max(), 300)
        y_kde = kde(x_kde) * len(utci) * 2.0  # scale to bar units
        ax.plot(x_kde, y_kde, color='red', linewidth=2, label='KDE')

    ax.set_ylabel('Number of Photos', fontsize=14)
    ax.set_title('UTCI Temperature vs Photo Count — State College, PA (All Photos)',
                 fontsize=15, fontweight='bold')
    ax.legend(fontsize=12)
    ax.grid(True, alpha=0.3)

    # Bottom: cumulative fraction
    ax2 = axes[1]
    sorted_utci = np.sort(utci)
    cdf = np.arange(1, len(sorted_utci) + 1) / len(sorted_utci)
    ax2.plot(sorted_utci, cdf, color='steelblue', linewidth=2)
    ax2.set_xlabel('UTCI Temperature (°C)', fontsize=14)
    ax2.set_ylabel('Cumulative\nFraction', fontsize=11)
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 1)

    plt.tight_layout()
    path = out_dir / 'state_college_utci_photo_count_overall.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path}')


def plot_per_creator(df, out_dir):
    """Grid of per-creator UTCI histograms for creators with enough photos."""
    out_dir.mkdir(parents=True, exist_ok=True)

    creator_counts = df['creator_id'].value_counts()
    top_creators = creator_counts[creator_counts >= MIN_PHOTOS_FOR_PANEL].index.tolist()

    if not top_creators:
        print(f'  No creators with >= {MIN_PHOTOS_FOR_PANEL} photos — skipping per-creator plot')
        return

    print(f'  Plotting {len(top_creators)} creators (>= {MIN_PHOTOS_FOR_PANEL} photos each)')

    # Add an "Other" group for remaining creators
    other_mask = ~df['creator_id'].isin(top_creators)
    n_other = other_mask.sum()
    groups = [(str(cid), df[df['creator_id'] == cid]) for cid in top_creators]
    if n_other > 0:
        groups.append((f'Other ({n_other:,} photos)', df[other_mask]))

    n_cols = min(3, len(groups))
    n_rows = (len(groups) + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols,
                              figsize=(7 * n_cols, 5 * n_rows),
                              squeeze=False)

    for idx, (label, gdf) in enumerate(groups):
        row, col = divmod(idx, n_cols)
        ax = axes[row][col]
        color = PALETTE[idx % len(PALETTE)]

        utci = gdf['utci_C'].values
        centres, counts = _bin_utci(pd.Series(utci))
        ax.bar(centres, counts, width=2.0 * 0.85, color=color, alpha=0.7)

        if len(utci) > 10 and np.std(utci) > 0:
            kde = gaussian_kde(utci, bw_method=0.2)
            x_kde = np.linspace(utci.min(), utci.max(), 200)
            y_kde = kde(x_kde) * len(utci) * 2.0
            ax.plot(x_kde, y_kde, color='black', linewidth=1.5)
        elif np.std(utci) == 0:
            # Creator photographed under a single UTCI condition (e.g. one day's shoot)
            ax.text(0.5, 0.95, 'Note: all photos at one UTCI value\n(possible single-day collection)',
                    transform=ax.transAxes, ha='center', va='top', fontsize=8,
                    color='gray', style='italic')

        ax.set_title(f'Creator {label}\n(n={len(gdf):,})', fontsize=11, fontweight='bold')
        ax.set_xlabel('UTCI (°C)', fontsize=10)
        ax.set_ylabel('Photo count', fontsize=10)
        ax.grid(True, alpha=0.3)

    # Hide empty subplots
    for idx in range(len(groups), n_rows * n_cols):
        row, col = divmod(idx, n_cols)
        axes[row][col].set_visible(False)

    fig.suptitle('UTCI Temperature vs Photo Count by Creator — State College, PA',
                 fontsize=15, fontweight='bold', y=1.01)
    plt.tight_layout()
    path = out_dir / 'state_college_utci_photo_count_per_creator.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path}')


def plot_creators_overlaid(df, out_dir):
    """All top creators overlaid on one axes for direct comparison."""
    out_dir.mkdir(parents=True, exist_ok=True)

    creator_counts = df['creator_id'].value_counts()
    top_creators = creator_counts[creator_counts >= MIN_PHOTOS_FOR_PANEL].index.tolist()

    if len(top_creators) < 2:
        return  # Not interesting to overlay a single creator

    fig, ax = plt.subplots(figsize=(12, 8))

    for i, cid in enumerate(top_creators):
        gdf = df[df['creator_id'] == cid]
        utci = gdf['utci_C'].values
        color = PALETTE[i % len(PALETTE)]

        if len(utci) > 10 and np.std(utci) > 0:
            kde = gaussian_kde(utci, bw_method=0.2)
            x_kde = np.linspace(utci.min(), utci.max(), 300)
            y_kde = kde(x_kde)
            ax.fill_between(x_kde, y_kde, alpha=0.3, color=color)
            ax.plot(x_kde, y_kde, color=color, linewidth=2,
                    label=f'Creator {cid} (n={len(gdf):,})')
        elif np.std(utci) == 0:
            print(f'  Note: Creator {cid} has zero UTCI variance (possible single-day collection) — skipped from overlay')

    ax.set_xlabel('UTCI Temperature (°C)', fontsize=14)
    ax.set_ylabel('Density', fontsize=14)
    ax.set_title('UTCI Distribution by Creator — State College, PA', fontsize=15, fontweight='bold')
    ax.legend(fontsize=11)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    path = out_dir / 'state_college_utci_photo_count_creators_overlaid.png'
    plt.savefig(path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {path}')


def main():
    print('=' * 60)
    print('State College — UTCI vs Photo Count')
    print('=' * 60)

    if not INPUT_PATH.exists():
        print(f'ERROR: Input file not found: {INPUT_PATH}')
        print('Run scripts/processing/add_utci_to_state_college.py first.')
        return

    df = load_data()
    print(f'Loaded {len(df):,} rows with valid UTCI')
    print(f'Unique creators: {df["creator_id"].nunique()}')
    print(f'UTCI range: {df["utci_C"].min():.1f}°C to {df["utci_C"].max():.1f}°C')

    out_dir = OUTPUT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    print('\n-- Overall photo count vs UTCI --')
    plot_overall(df, out_dir)

    print('\n-- Per-creator photo count vs UTCI --')
    plot_per_creator(df, out_dir)
    plot_creators_overlaid(df, out_dir)

    print('\nDone.')


if __name__ == '__main__':
    main()
