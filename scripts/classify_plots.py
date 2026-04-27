#!/usr/bin/env python3
# ABOUTME: Classifies all plots in outputs/ directory for publication package organization
# ABOUTME: Generates manifest with keep/archive decisions for cleanup planning

import pandas as pd
from pathlib import Path
import re

# Load plot inventory
plots = []
outputs = Path('outputs/')

for plot_file in outputs.rglob('*.png'):
    plots.append((str(plot_file), plot_file.stat().st_size, 'png'))
for plot_file in outputs.rglob('*.pdf'):
    plots.append((str(plot_file), plot_file.stat().st_size, 'pdf'))
for plot_file in outputs.rglob('*.svg'):
    plots.append((str(plot_file), plot_file.stat().st_size, 'svg'))

df = pd.DataFrame(plots, columns=['path', 'size_bytes', 'format'])

# Classification functions
def classify_city(path):
    """Classify by city focus"""
    path_lower = path.lower()

    # Check for specific city mentions
    if 'nyc' in path_lower or 'new-york' in path_lower or 'new_york' in path_lower:
        return 'NYC'
    elif 'seattle' in path_lower:
        return 'Seattle'
    elif any(x in path_lower for x in ['cross_city', 'cross-city', 'comparative', 'comparison']) and \
         ('nyc' in path_lower or 'seattle' in path_lower or 'new' in path_lower):
        return 'NYC+Seattle'

    # Other cities
    elif 'phoenix' in path_lower:
        return 'Phoenix'
    elif 'state_college' in path_lower or 'state-college' in path_lower or 'university_park' in path_lower:
        return 'State College'
    elif any(x in path_lower for x in ['boston', 'chicago', 'dallas', 'los-angeles', 'la_']):
        return 'Other Metro'
    elif any(x in path_lower for x in ['global', 'multi_city', 'world', 'madrid', 'tokyo', 'mumbai', 'cape-town', 'istanbul', 'singapore', 'osaka', 'buenos-aires']):
        return 'Global/Multi-City'

    # Generic/methods
    elif any(x in path_lower for x in ['model', 'yolo', 'vit', 'sam', 'training']):
        return 'Methods (Model)'
    else:
        return 'Unknown/Generic'

def classify_purpose(path):
    """Classify by plot purpose"""
    path_lower = path.lower()

    # Final results indicators
    if 'final' in path_lower:
        return 'Main Results'

    # IPW/methodological
    if any(x in path_lower for x in ['ipw', 'weight', 'neff', 'effective_sample']):
        return 'Methods (IPW)'

    # Seasonal adjustment
    if any(x in path_lower for x in ['seasonal', 'bootstrap']):
        return 'Methods (Seasonal)'

    # Validation
    if any(x in path_lower for x in ['walk_rate', 'validation', 'quality', 'data_quality']):
        return 'Validation'

    # Sensitivity
    if any(x in path_lower for x in ['sensitivity', 'tau_', 'sr_threshold', 'threshold']):
        return 'Sensitivity'

    # Diagnostic/exploratory
    if any(x in path_lower for x in ['diagnostic', 'debug', 'investigate', 'prescan', 'emd', 'bias_correction', 'curve_pattern', 'residual']):
        return 'Diagnostic'

    # Binned estimates
    if 'binned' in path_lower:
        return 'Main Results (Binned)'

    # Model performance
    if any(x in path_lower for x in ['confusion', 'precision', 'recall', 'f1', 'accuracy', 'loss', 'train_batch', 'val_batch']):
        return 'Methods (Model Performance)'

    # Exploratory
    if any(x in path_lower for x in ['wind_filter', 'extreme', 'alternative_methods', 'comparison_filtered']):
        return 'Exploratory'

    return 'Unknown'

def recommend_action(city, purpose, fmt):
    """Recommend keep or archive"""

    # Archive all non-NYC/Seattle cities
    if city in ['Phoenix', 'State College', 'Other Metro', 'Global/Multi-City']:
        return 'ARCHIVE (other city)'

    # Archive diagnostics and exploratory
    if purpose in ['Diagnostic', 'Exploratory']:
        return 'ARCHIVE (exploratory)'

    # For NYC/Seattle content
    if city in ['NYC', 'Seattle', 'NYC+Seattle']:
        # Prefer vector formats
        if purpose in ['Main Results', 'Main Results (Binned)', 'Validation', 'Methods (IPW)', 'Methods (Seasonal)']:
            if fmt in ['pdf', 'svg']:
                return 'KEEP (publication-ready vector)'
            else:
                return 'REVIEW (raster, check if vector exists)'

        elif purpose == 'Sensitivity':
            if fmt in ['pdf', 'svg']:
                return 'KEEP (supplementary vector)'
            else:
                return 'REVIEW (raster, check if vector exists)'

        elif purpose == 'Methods (Model Performance)':
            if fmt in ['pdf', 'svg']:
                return 'KEEP (methods vector)'
            else:
                return 'ARCHIVE (raster model eval)'

        else:
            return 'REVIEW (unclear purpose)'

    # Generic/methods without clear city
    if city in ['Methods (Model)', 'Unknown/Generic']:
        if purpose in ['Methods (Model Performance)', 'Methods (IPW)', 'Methods (Seasonal)']:
            if fmt in ['pdf', 'svg']:
                return 'KEEP (methods vector)'
            else:
                return 'ARCHIVE (raster methods)'
        else:
            return 'REVIEW (unclear)'

    return 'REVIEW'

# Apply classifications
df['city'] = df['path'].apply(classify_city)
df['purpose'] = df['path'].apply(classify_purpose)
df['recommendation'] = df.apply(lambda row: recommend_action(row['city'], row['purpose'], row['format']), axis=1)

# Add size in MB
df['size_mb'] = df['size_bytes'] / (1024 * 1024)

# Sort by recommendation and city
df = df.sort_values(['recommendation', 'city', 'path'])

# Save manifest
df.to_csv('PLOT_MANIFEST.csv', index=False)

# Print summary
print("\n" + "="*80)
print("PLOT CLASSIFICATION SUMMARY")
print("="*80)

print(f"\nTotal plots: {len(df)}")
print(f"Total size: {df['size_mb'].sum():.1f} MB")

print("\n--- By Recommendation ---")
print(df['recommendation'].value_counts().to_string())

print("\n--- By City ---")
print(df['city'].value_counts().to_string())

print("\n--- By Purpose ---")
print(df['purpose'].value_counts().to_string())

print("\n--- By Format ---")
print(df['format'].value_counts().to_string())

# Publication-ready summary
keep_plots = df[df['recommendation'].str.startswith('KEEP')]
print(f"\n--- Publication Package ---")
print(f"Plots to KEEP: {len(keep_plots)}")
print(f"Size to KEEP: {keep_plots['size_mb'].sum():.1f} MB")

archive_plots = df[df['recommendation'].str.startswith('ARCHIVE')]
print(f"\nPlots to ARCHIVE: {len(archive_plots)}")
print(f"Size to ARCHIVE: {archive_plots['size_mb'].sum():.1f} MB")

review_plots = df[df['recommendation'].str.startswith('REVIEW')]
print(f"\nPlots to REVIEW: {len(review_plots)}")
print(f"Size to REVIEW: {review_plots['size_mb'].sum():.1f} MB")

print("\n--- KEEP Breakdown by City/Purpose ---")
keep_breakdown = keep_plots.groupby(['city', 'purpose']).agg({
    'path': 'count',
    'size_mb': 'sum'
}).rename(columns={'path': 'count'})
print(keep_breakdown.to_string())

print("\n" + "="*80)
print(f"Manifest saved to: PLOT_MANIFEST.csv")
print("="*80)
