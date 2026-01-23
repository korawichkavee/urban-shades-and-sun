"""
Script to plot the probability of people being captured in street view imagery
based on temperature and time of day.

This script analyzes the relationship between environmental conditions and
the presence of people in street view images.
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path
import seaborn as sns

# Set style
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (14, 6)

def load_all_city_data(data_dir):
    """Load and combine all city data from the processed folder."""
    data_path = Path(data_dir)
    csv_files = list(data_path.glob("city_estimate_outcomes/**/*.csv"))

    print(f"Found {len(csv_files)} CSV files")

    all_data = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file, low_memory=False)
            all_data.append(df)
        except Exception as e:
            print(f"Error loading {csv_file}: {e}")

    combined_df = pd.concat(all_data, ignore_index=True)
    print(f"Total records: {len(combined_df)}")

    return combined_df

def prepare_data(df):
    """Prepare data for analysis."""
    # Make a copy to avoid SettingWithCopyWarning
    df = df.copy()

    # Parse datetime with UTC to handle mixed timezones
    df['datetime'] = pd.to_datetime(df['datetime-local'], utc=True, errors='coerce')

    # Extract hour of day
    # The datetime-local column already contains local time
    df['hour'] = df['datetime'].dt.hour

    # Person count is split into inshade_count and outshade_count
    # Calculate total person count from these columns
    inshade = pd.to_numeric(df['inshade_count'], errors='coerce').fillna(0)
    outshade = pd.to_numeric(df['outshade_count'], errors='coerce').fillna(0)
    df['person_count'] = inshade + outshade

    # Create binary variable for person presence
    df['has_person'] = (df['person_count'] > 0).astype(int)

    # Use dbulb (dry bulb temperature) as primary temperature measure
    # Fall back to utci_C if dbulb is not available
    df['temperature'] = df['dbulb'].fillna(df['utci_C'])

    # Remove rows with missing critical data
    df_clean = df.dropna(subset=['temperature', 'hour']).copy()

    print(f"Records after cleaning: {len(df_clean)}")
    print(f"Images with at least one person: {df_clean['has_person'].sum()}")
    print(f"Total people detected: {df_clean['person_count'].sum():.0f}")
    print(f"Percentage of images with people: {100 * df_clean['has_person'].mean():.2f}%")
    print(f"Average people per image (all images): {df_clean['person_count'].mean():.3f}")
    print(f"Average people per image (when >0): {df_clean[df_clean['has_person'] > 0]['person_count'].mean():.3f}")

    return df_clean

def plot_probability_vs_temperature(df, ax):
    """Plot probability of person capture vs temperature."""
    # Make a copy to avoid SettingWithCopyWarning
    df = df.copy()

    # Create temperature bins
    temp_bins = np.arange(df['temperature'].min(), df['temperature'].max() + 2, 2)
    df['temp_bin'] = pd.cut(df['temperature'], bins=temp_bins)

    # Calculate probability for each bin
    prob_by_temp = df.groupby('temp_bin', observed=True).agg({
        'has_person': 'mean',  # Probability at least one person
        'person_count': 'mean',  # Average number of people
        'temperature': 'count'  # Sample size
    }).reset_index()

    prob_by_temp.columns = ['temp_bin', 'prob_any_person', 'avg_person_count', 'count']

    # Filter bins with at least 10 observations for statistical reliability
    prob_by_temp = prob_by_temp[prob_by_temp['count'] >= 10]

    # Get bin midpoints for plotting
    prob_by_temp['temp_mid'] = prob_by_temp['temp_bin'].apply(lambda x: x.mid)

    # Plot
    ax.plot(prob_by_temp['temp_mid'], prob_by_temp['prob_any_person'] * 100,
            marker='o', linewidth=2.5, markersize=7, color='#2E86AB', label='Any person present')

    ax.set_xlabel('Temperature (°C)', fontsize=12, fontweight='bold')
    ax.set_ylabel('Probability of Capturing People (%)', fontsize=12, fontweight='bold')
    ax.set_title('Probability of Capturing People vs Temperature', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=10)

    # Add sample size annotation
    total_samples = prob_by_temp['count'].sum()
    ax.text(0.02, 0.98, f'Total observations: {total_samples:,}',
            transform=ax.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Set y-axis limits to make curve visible
    y_min = max(0, prob_by_temp['prob_any_person'].min() * 100 - 1)
    y_max = min(100, prob_by_temp['prob_any_person'].max() * 100 + 1)
    ax.set_ylim(y_min, y_max)

def plot_probability_vs_hour(df, ax):
    """Plot probability of person capture vs hour of day."""
    # Calculate probability for each hour
    prob_by_hour = df.groupby('hour').agg({
        'has_person': 'mean',  # Probability at least one person
        'person_count': 'mean',  # Average number of people
        'temperature': 'count'  # Sample size (use a different column to avoid conflict)
    }).reset_index()

    prob_by_hour.columns = ['hour', 'prob_any_person', 'avg_person_count', 'count']

    # Plot
    ax.plot(prob_by_hour['hour'], prob_by_hour['prob_any_person'] * 100,
            marker='o', linewidth=2.5, markersize=7, color='#A23B72', label='Any person present')

    ax.set_xlabel('Hour of Day', fontsize=12, fontweight='bold')
    ax.set_ylabel('Probability of Capturing People (%)', fontsize=12, fontweight='bold')
    ax.set_title('Probability of Capturing People vs Time of Day', fontsize=14, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.set_xticks(range(0, 24, 2))
    ax.legend(fontsize=10)

    # Add sample size annotation
    total_samples = prob_by_hour['count'].sum()
    ax.text(0.02, 0.98, f'Total observations: {total_samples:,}',
            transform=ax.transAxes, fontsize=10, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # Set y-axis limits to make curve visible
    y_min = max(0, prob_by_hour['prob_any_person'].min() * 100 - 1)
    y_max = min(100, prob_by_hour['prob_any_person'].max() * 100 + 1)
    ax.set_ylim(y_min, y_max)

def main():
    """Main function to generate plots."""
    # Define paths relative to project root
    project_root = Path(__file__).parent.parent.parent
    data_dir = project_root / "data" / "processed"
    output_dir = project_root / "outputs" / "plots"

    # Create output directory if it doesn't exist
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load data
    print("Loading data...")
    df = load_all_city_data(data_dir)

    # Prepare data
    print("\nPreparing data...")
    df_clean = prepare_data(df)

    # Create figure with two subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6))

    # Plot probability vs temperature
    print("\nPlotting probability vs temperature...")
    plot_probability_vs_temperature(df_clean, ax1)

    # Plot probability vs hour
    print("Plotting probability vs hour of day...")
    plot_probability_vs_hour(df_clean, ax2)

    # Adjust layout and save
    plt.tight_layout()
    output_path = output_dir / "person_capture_probability.png"
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"\nPlot saved to: {output_path}")

    # Display summary statistics
    print("\n" + "="*70)
    print("SUMMARY STATISTICS")
    print("="*70)
    print(f"Temperature range: {df_clean['temperature'].min():.1f}°C to {df_clean['temperature'].max():.1f}°C")
    print(f"Mean temperature: {df_clean['temperature'].mean():.1f}°C")
    print(f"Overall probability of capturing at least one person: {100 * df_clean['has_person'].mean():.2f}%")
    print(f"Average number of people per image (all images): {df_clean['person_count'].mean():.3f}")
    print(f"Average number of people per image (when >0): {df_clean[df_clean['has_person'] > 0]['person_count'].mean():.2f}")
    print(f"Total images analyzed: {len(df_clean):,}")
    print(f"Images with people: {df_clean['has_person'].sum():,}")
    print(f"Total people detected: {df_clean['person_count'].sum():.0f}")
    print("="*70)

    plt.show()

if __name__ == "__main__":
    main()
