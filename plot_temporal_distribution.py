# ABOUTME: Analyzes and visualizes the temporal distribution of street view images from metadata CSV.
# ABOUTME: Creates plots showing year range, monthly patterns, day of week bias, and time of day distribution.

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

# Set style for better-looking plots
sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (15, 10)

# Load the data
data_path = Path(__file__).parent / "data" / "boston_metadata.csv"
df = pd.read_csv(data_path)

# Convert captured_at to datetime
df['captured_at'] = pd.to_datetime(df['captured_at'])

# Extract temporal components
df['year'] = df['captured_at'].dt.year
df['month'] = df['captured_at'].dt.month
df['month_name'] = df['captured_at'].dt.month_name()
df['day_of_week'] = df['captured_at'].dt.dayofweek
df['day_name'] = df['captured_at'].dt.day_name()
df['hour'] = df['captured_at'].dt.hour
df['time_of_day'] = df['captured_at'].dt.hour + df['captured_at'].dt.minute / 60

# Create a figure with subplots
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('Temporal Distribution of Street View Images - Boston', fontsize=16, fontweight='bold')

# 1. Distribution by Year
ax1 = axes[0, 0]
year_counts = df['year'].value_counts().sort_index()
ax1.bar(year_counts.index, year_counts.values, color='steelblue', edgecolor='black', alpha=0.7)
ax1.set_xlabel('Year', fontsize=12)
ax1.set_ylabel('Number of Images', fontsize=12)
ax1.set_title('Image Availability by Year', fontsize=13, fontweight='bold')
ax1.grid(axis='y', alpha=0.3)
# Add count labels on bars
for i, (year, count) in enumerate(year_counts.items()):
    ax1.text(year, count, f'{count:,}', ha='center', va='bottom', fontsize=9)
# Add summary statistics
total_images = len(df)
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
# Create hourly bins
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
plt.savefig('temporal_distribution_boston_svi.png', dpi=300, bbox_inches='tight')
print(f"Plot saved as 'temporal_distribution_boston_svi.png'")
plt.show()

# Print detailed statistics
print("\n" + "="*60)
print("TEMPORAL DISTRIBUTION SUMMARY")
print("="*60)

print(f"\nTotal Images: {total_images:,}")
print(f"Date Range: {df['captured_at'].min()} to {df['captured_at'].max()}")

print("\n--- Year Distribution ---")
for year, count in year_counts.items():
    pct = (count / total_images) * 100
    print(f"{year}: {count:,} images ({pct:.2f}%)")

print("\n--- Month Distribution (All Years) ---")
for month in range(1, 13):
    count = month_counts.get(month, 0)
    pct = (count / total_images) * 100
    print(f"{month_names[month-1]}: {count:,} images ({pct:.2f}%)")

print("\n--- Day of Week Distribution ---")
for i, day in enumerate(day_names):
    count = dow_counts.get(i, 0)
    pct = (count / total_images) * 100
    print(f"{day}: {count:,} images ({pct:.2f}%)")

print("\n--- Time of Day Statistics ---")
print(f"Peak Hour: {peak_hour}:00 with {peak_count:,} images")
print(f"Mean Hour: {mean_hour:.2f}")
print(f"Median Hour: {median_hour:.0f}")
print(f"Morning (6-12): {len(df[(df['hour'] >= 6) & (df['hour'] < 12)]):,} images")
print(f"Afternoon (12-18): {len(df[(df['hour'] >= 12) & (df['hour'] < 18)]):,} images")
print(f"Evening (18-24): {len(df[(df['hour'] >= 18)]):,} images")
print(f"Night (0-6): {len(df[df['hour'] < 6]):,} images")
