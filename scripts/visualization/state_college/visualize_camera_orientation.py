# ABOUTME: Visualizes camera orientation distribution relative to road bearing
# ABOUTME: Shows angular PDF/distribution with road as true north (0°)

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

INPUT_PATH = Path(__file__).parent.parent.parent.parent / 'data' / 'state-college' / 'state-college_svi_with_road_bearing.csv'
OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / 'outputs' / 'plots' / 'state_college' / 'camera_orientation'

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def normalize_angle(angle):
    """Normalize angle to [-180, 180] range"""
    return ((angle + 180) % 360) - 180

def main():
    print('=' * 70)
    print('VISUALIZE CAMERA ORIENTATION RELATIVE TO ROAD')
    print(f'Input:  {INPUT_PATH}')
    print(f'Output: {OUTPUT_DIR}')
    print('=' * 70)
    print()

    # Load data
    print('Loading data...')
    df = pd.read_csv(INPUT_PATH, low_memory=False)
    print(f'  Loaded {len(df):,} rows')
    print()

    # Filter to valid orientations
    df_valid = df[df['camera_facing_side'].isin(['left', 'right'])].copy()
    print(f'Valid camera orientations: {len(df_valid):,}')
    print()

    # Compute relative angle (camera angle - road bearing)
    # Positive = camera rotated clockwise from road direction
    # Negative = camera rotated counter-clockwise from road direction
    df_valid['relative_angle'] = df_valid.apply(
        lambda row: normalize_angle(row['compass_angle'] - row['road_bearing_deg']),
        axis=1
    )

    # Statistics
    print('Camera Orientation Statistics:')
    print(f'  Mean relative angle: {df_valid["relative_angle"].mean():.2f}°')
    print(f'  Median relative angle: {df_valid["relative_angle"].median():.2f}°')
    print(f'  Std dev: {df_valid["relative_angle"].std():.2f}°')
    print(f'  Min: {df_valid["relative_angle"].min():.2f}°')
    print(f'  Max: {df_valid["relative_angle"].max():.2f}°')
    print()

    print('By camera facing side:')
    for side in ['left', 'right']:
        subset = df_valid[df_valid['camera_facing_side'] == side]
        print(f'  {side.capitalize()}: n={len(subset):,}, mean={subset["relative_angle"].mean():.2f}°, '
              f'median={subset["relative_angle"].median():.2f}°, std={subset["relative_angle"].std():.2f}°')
    print()

    # Create visualization
    fig, axes = plt.subplots(2, 2, figsize=(14, 12))

    # Plot 1: Polar histogram of relative angles
    ax_polar = plt.subplot(2, 2, 1, projection='polar')

    # Convert to radians for polar plot
    angles_rad = np.deg2rad(df_valid['relative_angle'])

    # Create bins (36 bins = 10° each)
    n_bins = 36
    counts, bin_edges = np.histogram(angles_rad, bins=n_bins, range=(-np.pi, np.pi))
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

    # Width of each bar
    width = 2 * np.pi / n_bins

    # Color by facing side
    colors = []
    for center in bin_centers:
        angle_deg = np.rad2deg(center)
        if -90 <= angle_deg < 90:
            colors.append('#2E86AB')  # Blue for right
        else:
            colors.append('#A23B72')  # Purple for left

    bars = ax_polar.bar(bin_centers, counts, width=width, color=colors, alpha=0.7, edgecolor='black', linewidth=0.5)

    # Mark cardinal directions
    ax_polar.set_theta_zero_location('N')
    ax_polar.set_theta_direction(-1)  # Clockwise
    ax_polar.set_xticks(np.deg2rad([0, 90, 180, -90]))
    ax_polar.set_xticklabels(['Road Direction\n(0°)', 'Right\n(90°)', 'Opposite\n(±180°)', 'Left\n(-90°)'])
    ax_polar.set_title('Camera Orientation Relative to Road\n(Polar View)', fontsize=12, fontweight='bold', pad=20)

    # Add legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2E86AB', alpha=0.7, label='Faces Right Sidewalk'),
        Patch(facecolor='#A23B72', alpha=0.7, label='Faces Left Sidewalk')
    ]
    ax_polar.legend(handles=legend_elements, loc='upper right', bbox_to_anchor=(1.3, 1.1))

    # Plot 2: Linear histogram
    ax1 = axes[0, 1]
    ax1.hist(df_valid['relative_angle'], bins=72, range=(-180, 180),
             color='#2E86AB', alpha=0.7, edgecolor='black', linewidth=0.5)
    ax1.axvline(0, color='red', linestyle='--', linewidth=2, label='Road Direction')
    ax1.axvline(-90, color='purple', linestyle='--', linewidth=1.5, alpha=0.7, label='Perpendicular Left')
    ax1.axvline(90, color='purple', linestyle='--', linewidth=1.5, alpha=0.7, label='Perpendicular Right')
    ax1.set_xlabel('Camera Angle Relative to Road (degrees)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Count', fontsize=11, fontweight='bold')
    ax1.set_title('Distribution of Camera Orientations\n(Linear View)', fontsize=12, fontweight='bold')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Plot 3: KDE by facing side
    ax2 = axes[1, 0]
    for side, color in [('right', '#2E86AB'), ('left', '#A23B72')]:
        subset = df_valid[df_valid['camera_facing_side'] == side]['relative_angle']
        subset.plot.kde(ax=ax2, color=color, linewidth=2, label=f'{side.capitalize()} sidewalk (n={len(subset):,})')

    ax2.axvline(0, color='red', linestyle='--', linewidth=2, alpha=0.7, label='Road Direction')
    ax2.axvline(-90, color='gray', linestyle=':', linewidth=1.5, alpha=0.5)
    ax2.axvline(90, color='gray', linestyle=':', linewidth=1.5, alpha=0.5)
    ax2.set_xlabel('Camera Angle Relative to Road (degrees)', fontsize=11, fontweight='bold')
    ax2.set_ylabel('Density', fontsize=11, fontweight='bold')
    ax2.set_title('Probability Density by Camera Facing Side', fontsize=12, fontweight='bold')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(-180, 180)

    # Plot 4: Absolute angle difference (from assignment logic)
    ax3 = axes[1, 1]

    # Separate by facing side
    right_diff = df_valid[df_valid['camera_facing_side'] == 'right']['camera_road_angle_diff']
    left_diff = df_valid[df_valid['camera_facing_side'] == 'left']['camera_road_angle_diff']

    ax3.hist([right_diff, left_diff], bins=90, range=(0, 180),
             color=['#2E86AB', '#A23B72'], alpha=0.7, label=['Right sidewalk', 'Left sidewalk'],
             edgecolor='black', linewidth=0.5)
    ax3.axvline(90, color='red', linestyle='--', linewidth=2, label='Assignment Threshold (90°)')
    ax3.set_xlabel('Absolute Angular Difference (degrees)', fontsize=11, fontweight='bold')
    ax3.set_ylabel('Count', fontsize=11, fontweight='bold')
    ax3.set_title('Camera-Road Angle Difference\n(Used for Left/Right Assignment)', fontsize=12, fontweight='bold')
    ax3.legend()
    ax3.grid(True, alpha=0.3)

    # Add text annotation
    ax3.text(45, ax3.get_ylim()[1] * 0.9, '← Faces Right', ha='center', fontsize=10, color='#2E86AB', fontweight='bold')
    ax3.text(135, ax3.get_ylim()[1] * 0.9, 'Faces Left →', ha='center', fontsize=10, color='#A23B72', fontweight='bold')

    plt.tight_layout()

    # Save
    output_path = OUTPUT_DIR / 'camera_orientation_distribution.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f'Saved plot -> {output_path}')

    # Create a second plot: simplified polar plot with clearer interpretation
    fig2, ax = plt.subplots(1, 1, figsize=(10, 10), subplot_kw={'projection': 'polar'})

    # Convert to radians for polar plot
    angles_rad = np.deg2rad(df_valid['relative_angle'])

    # Create finer bins (72 bins = 5° each)
    n_bins = 72
    counts, bin_edges = np.histogram(angles_rad, bins=n_bins, range=(-np.pi, np.pi))
    bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
    width = 2 * np.pi / n_bins

    # Color by facing side
    colors = []
    for center in bin_centers:
        angle_deg = np.rad2deg(center)
        if -90 <= angle_deg < 90:
            colors.append('#2E86AB')  # Blue for right
        else:
            colors.append('#A23B72')  # Purple for left

    bars = ax.bar(bin_centers, counts, width=width, color=colors, alpha=0.7, edgecolor='black', linewidth=0.3)

    # Configure polar plot
    ax.set_theta_zero_location('N')
    ax.set_theta_direction(-1)  # Clockwise
    ax.set_xticks(np.deg2rad([0, 45, 90, 135, 180, -135, -90, -45]))
    ax.set_xticklabels(['Road\nDirection\n0°', '45°', 'Right\n90°', '135°',
                        'Opposite\n±180°', '-135°', 'Left\n-90°', '-45°'], fontsize=10)
    ax.set_title('Camera Orientation Distribution Relative to Road Bearing\n(Road Direction = North/0°)',
                 fontsize=14, fontweight='bold', pad=30)

    # Add radial grid labels
    ax.set_ylim(0, counts.max() * 1.1)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor='#2E86AB', alpha=0.7, label=f'Faces Right Sidewalk (n={len(df_valid[df_valid["camera_facing_side"]=="right"]):,})'),
        Patch(facecolor='#A23B72', alpha=0.7, label=f'Faces Left Sidewalk (n={len(df_valid[df_valid["camera_facing_side"]=="left"]):,})')
    ]
    ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(1.15, 1.05), fontsize=11)

    plt.tight_layout()

    # Save
    output_path2 = OUTPUT_DIR / 'camera_orientation_polar_simple.png'
    plt.savefig(output_path2, dpi=300, bbox_inches='tight')
    print(f'Saved plot -> {output_path2}')
    print()
    print('Done.')


if __name__ == '__main__':
    main()
