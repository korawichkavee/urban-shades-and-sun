# ABOUTME: Generates temporal distribution plots for all metro cities in the dataset.
# ABOUTME: Creates individual city plots and an overall combined plot, saving to organized output directory.

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np
import warnings
warnings.filterwarnings('ignore')

# Set style for better-looking plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (15, 10)

def create_temporal_plot(df, city_name, output_path):
    """Create temporal distribution plot for a single city."""

    # Extract temporal components
    df['year'] = df['captured_at'].dt.year
    df['month'] = df['captured_at'].dt.month
    df['month_name'] = df['captured_at'].dt.month_name()
    df['day_of_week'] = df['captured_at'].dt.dayofweek
    df['day_name'] = df['captured_at'].dt.day_name()
    df['hour'] = df['captured_at'].dt.hour

    # Create a figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle(f'Temporal Distribution of Street View Images - {city_name}',
                 fontsize=16, fontweight='bold')

    total_images = len(df)

    # 1. Distribution by Year
    ax1 = axes[0, 0]
    year_counts = df['year'].value_counts().sort_index()
    ax1.bar(year_counts.index, year_counts.values, color='steelblue', edgecolor='black', alpha=0.7)
    ax1.set_xlabel('Year', fontsize=12)
    ax1.set_ylabel('Number of Images', fontsize=12)
    ax1.set_title('Image Availability by Year', fontsize=13, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    # Add count labels on bars
    for year, count in year_counts.items():
        ax1.text(year, count, f'{count:,}', ha='center', va='bottom', fontsize=9)
    # Add summary statistics
    year_range = f"{df['year'].min()} - {df['year'].max()}"
    ax1.text(0.02, 0.98, f'Total Images: {total_images:,}\nYear Range: {year_range}',
             transform=ax1.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # 2. Distribution by Month (across all years)
    ax2 = axes[0, 1]
    month_counts = df['month'].value_counts().sort_index()
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    colors = plt.cm.coolwarm(np.linspace(0.2, 0.8, 12))
    ax2.bar(range(1, 13), [month_counts.get(i, 0) for i in range(1, 13)],
            color=colors, edgecolor='black', alpha=0.7)
    ax2.set_xlabel('Month', fontsize=12)
    ax2.set_ylabel('Number of Images', fontsize=12)
    ax2.set_title('Image Availability by Month (All Years Combined)', fontsize=13, fontweight='bold')
    ax2.set_xticks(range(1, 13))
    ax2.set_xticklabels(month_names, rotation=45, ha='right')
    ax2.grid(axis='y', alpha=0.3)
    # Add percentage labels
    for i in range(1, 13):
        count = month_counts.get(i, 0)
        pct = (count / total_images) * 100
        ax2.text(i, count, f'{pct:.1f}%', ha='center', va='bottom', fontsize=8)

    # 3. Distribution by Day of Week
    ax3 = axes[1, 0]
    dow_counts = df['day_of_week'].value_counts().sort_index()
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    colors_dow = ['#3498db' if i < 5 else '#e74c3c' for i in range(7)]  # Blue for weekdays, red for weekends
    ax3.bar(range(7), [dow_counts.get(i, 0) for i in range(7)],
            color=colors_dow, edgecolor='black', alpha=0.7)
    ax3.set_xlabel('Day of Week', fontsize=12)
    ax3.set_ylabel('Number of Images', fontsize=12)
    ax3.set_title('Image Availability by Day of Week', fontsize=13, fontweight='bold')
    ax3.set_xticks(range(7))
    ax3.set_xticklabels(day_names)
    ax3.grid(axis='y', alpha=0.3)
    # Add count and percentage labels
    for i in range(7):
        count = dow_counts.get(i, 0)
        pct = (count / total_images) * 100
        ax3.text(i, count, f'{count:,}\n({pct:.1f}%)', ha='center', va='bottom', fontsize=8)
    # Add weekday vs weekend summary
    weekday_count = sum([dow_counts.get(i, 0) for i in range(5)])
    weekend_count = sum([dow_counts.get(i, 0) for i in range(5, 7)])
    ax3.text(0.02, 0.98, f'Weekdays: {weekday_count:,} ({weekday_count/total_images*100:.1f}%)\nWeekends: {weekend_count:,} ({weekend_count/total_images*100:.1f}%)',
             transform=ax3.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # 4. Distribution by Time of Day
    ax4 = axes[1, 1]
    bins = range(0, 25)
    ax4.hist(df['hour'], bins=bins, color='darkgreen', edgecolor='black', alpha=0.7)
    ax4.set_xlabel('Hour of Day', fontsize=12)
    ax4.set_ylabel('Number of Images', fontsize=12)
    ax4.set_title('Image Availability by Time of Day', fontsize=13, fontweight='bold')
    ax4.set_xticks(range(0, 24, 2))
    ax4.set_xticklabels([f'{h:02d}:00' for h in range(0, 24, 2)], rotation=45, ha='right')
    ax4.grid(axis='y', alpha=0.3)
    # Add statistics for peak hours
    hour_counts = df['hour'].value_counts()
    peak_hour = hour_counts.idxmax()
    peak_count = hour_counts.max()
    ax4.axvline(peak_hour, color='red', linestyle='--', linewidth=2, alpha=0.7, label=f'Peak: {peak_hour}:00')
    ax4.legend()
    # Add summary
    mean_hour = df['hour'].mean()
    median_hour = df['hour'].median()
    ax4.text(0.02, 0.98, f'Peak Hour: {peak_hour}:00 ({peak_count:,} images)\nMean: {mean_hour:.1f}:00\nMedian: {median_hour:.0f}:00',
             transform=ax4.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()

    return total_images


def create_overall_plot_from_aggregates(year_counts, month_counts, dow_counts, hour_counts,
                                       num_cities, total_images, output_path):
    """Create overall temporal distribution plot from aggregated counts."""

    # Create a figure with subplots
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle('Temporal Distribution of Street View Images - All Metro Cities Combined',
                 fontsize=16, fontweight='bold')

    # 1. Distribution by Year
    ax1 = axes[0, 0]
    sorted_years = sorted(year_counts.keys())
    year_values = [year_counts[y] for y in sorted_years]
    ax1.bar(sorted_years, year_values, color='steelblue', edgecolor='black', alpha=0.7)
    ax1.set_xlabel('Year', fontsize=12)
    ax1.set_ylabel('Number of Images', fontsize=12)
    ax1.set_title('Image Availability by Year', fontsize=13, fontweight='bold')
    ax1.grid(axis='y', alpha=0.3)
    # Add count labels on bars
    for year, count in zip(sorted_years, year_values):
        ax1.text(year, count, f'{count:,}', ha='center', va='bottom', fontsize=9)
    # Add summary statistics
    year_range = f"{min(sorted_years)} - {max(sorted_years)}"
    ax1.text(0.02, 0.98, f'Total Images: {total_images:,}\nCities: {num_cities}\nYear Range: {year_range}',
             transform=ax1.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # 2. Distribution by Month (across all years)
    ax2 = axes[0, 1]
    month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    colors = plt.cm.coolwarm(np.linspace(0.2, 0.8, 12))
    month_values = [month_counts.get(i, 0) for i in range(1, 13)]
    ax2.bar(range(1, 13), month_values, color=colors, edgecolor='black', alpha=0.7)
    ax2.set_xlabel('Month', fontsize=12)
    ax2.set_ylabel('Number of Images', fontsize=12)
    ax2.set_title('Image Availability by Month (All Years Combined)', fontsize=13, fontweight='bold')
    ax2.set_xticks(range(1, 13))
    ax2.set_xticklabels(month_names, rotation=45, ha='right')
    ax2.grid(axis='y', alpha=0.3)
    # Add percentage labels
    for i in range(1, 13):
        count = month_counts.get(i, 0)
        pct = (count / total_images) * 100
        ax2.text(i, count, f'{pct:.1f}%', ha='center', va='bottom', fontsize=8)

    # 3. Distribution by Day of Week
    ax3 = axes[1, 0]
    day_names = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
    colors_dow = ['#3498db' if i < 5 else '#e74c3c' for i in range(7)]  # Blue for weekdays, red for weekends
    dow_values = [dow_counts.get(i, 0) for i in range(7)]
    ax3.bar(range(7), dow_values, color=colors_dow, edgecolor='black', alpha=0.7)
    ax3.set_xlabel('Day of Week', fontsize=12)
    ax3.set_ylabel('Number of Images', fontsize=12)
    ax3.set_title('Image Availability by Day of Week', fontsize=13, fontweight='bold')
    ax3.set_xticks(range(7))
    ax3.set_xticklabels(day_names)
    ax3.grid(axis='y', alpha=0.3)
    # Add count and percentage labels
    for i in range(7):
        count = dow_counts.get(i, 0)
        pct = (count / total_images) * 100
        ax3.text(i, count, f'{count:,}\n({pct:.1f}%)', ha='center', va='bottom', fontsize=8)
    # Add weekday vs weekend summary
    weekday_count = sum([dow_counts.get(i, 0) for i in range(5)])
    weekend_count = sum([dow_counts.get(i, 0) for i in range(5, 7)])
    ax3.text(0.02, 0.98, f'Weekdays: {weekday_count:,} ({weekday_count/total_images*100:.1f}%)\nWeekends: {weekend_count:,} ({weekend_count/total_images*100:.1f}%)',
             transform=ax3.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    # 4. Distribution by Time of Day
    ax4 = axes[1, 1]
    hour_values = [hour_counts.get(h, 0) for h in range(24)]
    ax4.bar(range(24), hour_values, color='darkgreen', edgecolor='black', alpha=0.7, width=1.0)
    ax4.set_xlabel('Hour of Day', fontsize=12)
    ax4.set_ylabel('Number of Images', fontsize=12)
    ax4.set_title('Image Availability by Time of Day', fontsize=13, fontweight='bold')
    ax4.set_xticks(range(0, 24, 2))
    ax4.set_xticklabels([f'{h:02d}:00' for h in range(0, 24, 2)], rotation=45, ha='right')
    ax4.grid(axis='y', alpha=0.3)
    # Add statistics for peak hours
    peak_hour = max(hour_counts.keys(), key=lambda h: hour_counts[h])
    peak_count = hour_counts[peak_hour]
    ax4.axvline(peak_hour, color='red', linestyle='--', linewidth=2, alpha=0.7, label=f'Peak: {peak_hour}:00')
    ax4.legend()
    # Add summary
    total_hour_weighted = sum(h * count for h, count in hour_counts.items())
    mean_hour = total_hour_weighted / total_images
    ax4.text(0.02, 0.98, f'Peak Hour: {peak_hour}:00 ({peak_count:,} images)\nMean: {mean_hour:.1f}:00',
             transform=ax4.transAxes, fontsize=10, verticalalignment='top',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()


def main():
    # Set up paths
    base_dir = Path(__file__).parent
    data_dir = base_dir / "data" / "metro_cities_svi_test"
    output_dir = data_dir / "temporal_plots"
    output_dir.mkdir(exist_ok=True, parents=True)

    # Find all metadata CSV files
    metadata_files = sorted(data_dir.glob("*//*_metadata.csv"))

    print(f"Found {len(metadata_files)} cities with metadata")
    print("="*60)

    # Aggregate statistics for combined plot
    combined_year_counts = {}
    combined_month_counts = {}
    combined_dow_counts = {}
    combined_hour_counts = {}
    city_stats = []
    total_images_all = 0

    # Process each city
    for i, csv_file in enumerate(metadata_files, 1):
        city_name = csv_file.parent.name
        print(f"\n[{i}/{len(metadata_files)}] Processing {city_name}...")

        try:
            # Load data
            df = pd.read_csv(csv_file)
            df['captured_at'] = pd.to_datetime(df['captured_at'], format='mixed')

            # Create individual city plot
            output_path = output_dir / f"{city_name}_temporal_distribution.png"
            total_images = create_temporal_plot(df, city_name.title(), output_path)

            print(f"  ✓ Created plot: {output_path.name}")
            print(f"  Images: {total_images:,}")

            # Aggregate for combined plot (without keeping full dataframes)
            df['year'] = df['captured_at'].dt.year
            df['month'] = df['captured_at'].dt.month
            df['day_of_week'] = df['captured_at'].dt.dayofweek
            df['hour'] = df['captured_at'].dt.hour

            for year, count in df['year'].value_counts().items():
                combined_year_counts[year] = combined_year_counts.get(year, 0) + count
            for month, count in df['month'].value_counts().items():
                combined_month_counts[month] = combined_month_counts.get(month, 0) + count
            for dow, count in df['day_of_week'].value_counts().items():
                combined_dow_counts[dow] = combined_dow_counts.get(dow, 0) + count
            for hour, count in df['hour'].value_counts().items():
                combined_hour_counts[hour] = combined_hour_counts.get(hour, 0) + count

            total_images_all += total_images

            city_stats.append({
                'city': city_name,
                'images': total_images,
                'date_range': f"{df['captured_at'].min().date()} to {df['captured_at'].max().date()}"
            })

            # Free memory
            del df

        except Exception as e:
            print(f"  ✗ Error processing {city_name}: {e}")

    # Create overall combined plot using aggregated data
    if city_stats:
        print(f"\n{'='*60}")
        print("Creating overall combined plot...")
        overall_output = output_dir / "all_cities_temporal_distribution.png"
        create_overall_plot_from_aggregates(combined_year_counts, combined_month_counts,
                                           combined_dow_counts, combined_hour_counts,
                                           len(city_stats), total_images_all, overall_output)
        print(f"✓ Created overall plot: {overall_output.name}")
        print(f"  Total images across all cities: {total_images_all:,}")

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print("="*60)
    print(f"\nPlots saved to: {output_dir}/")
    print(f"\nCity Statistics:")
    print(f"{'City':<20} {'Images':>12} {'Date Range'}")
    print("-"*60)
    for stat in sorted(city_stats, key=lambda x: x['images'], reverse=True):
        print(f"{stat['city'].title():<20} {stat['images']:>12,} {stat['date_range']}")
    print("-"*60)
    print(f"{'TOTAL':<20} {sum(s['images'] for s in city_stats):>12,}")
    print(f"\nAll plots saved successfully!")


if __name__ == "__main__":
    main()
