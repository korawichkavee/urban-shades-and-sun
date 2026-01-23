"""
Helper module to calculate inverse probability weights for person presence.

This module calculates the probability of capturing a person in a street view image
based on temperature and time of day, and provides inverse probability weights
for reweighting analyses to account for differential person presence.
"""

import pandas as pd
import numpy as np
from scipy.interpolate import interp1d


def calculate_person_probabilities(df):
    """
    Calculate probability of person presence based on temperature and hour.

    Args:
        df: DataFrame with columns 'temperature', 'hour', 'has_person', 'person_count'

    Returns:
        DataFrame with added columns:
        - prob_person_temp: probability based on temperature
        - prob_person_hour: probability based on hour
        - prob_person_combined: combined probability
        - ipw_temp: inverse probability weight based on temperature
        - ipw_hour: inverse probability weight based on hour
        - ipw_combined: combined inverse probability weight
    """
    df = df.copy()

    # Calculate probabilities by temperature (2°C bins)
    temp_bins = np.arange(df['temperature'].min() - 1, df['temperature'].max() + 3, 2)
    df['temp_bin'] = pd.cut(df['temperature'], bins=temp_bins)

    prob_by_temp = df.groupby('temp_bin', observed=True).agg({
        'has_person': 'mean',
        'temperature': 'count'
    }).reset_index()
    prob_by_temp.columns = ['temp_bin', 'prob', 'count']

    # Filter bins with at least 10 observations
    prob_by_temp = prob_by_temp[prob_by_temp['count'] >= 10]

    # Get bin midpoints for interpolation
    prob_by_temp['temp_mid'] = prob_by_temp['temp_bin'].apply(lambda x: x.mid)

    # Create interpolation function for temperature-based probability
    # Add small epsilon to avoid division by zero
    epsilon = 0.001
    prob_by_temp['prob_safe'] = prob_by_temp['prob'].clip(lower=epsilon)

    temp_prob_func = interp1d(
        prob_by_temp['temp_mid'].values,
        prob_by_temp['prob_safe'].values,
        kind='linear',
        bounds_error=False,
        fill_value=(prob_by_temp['prob_safe'].iloc[0], prob_by_temp['prob_safe'].iloc[-1])
    )

    # Calculate probabilities by hour
    prob_by_hour = df.groupby('hour').agg({
        'has_person': 'mean',
        'temperature': 'count'  # Use different column to avoid conflict
    }).reset_index()
    prob_by_hour.columns = ['hour', 'prob', 'count']
    prob_by_hour['prob_safe'] = prob_by_hour['prob'].clip(lower=epsilon)

    # Create interpolation function for hour-based probability
    hour_prob_func = interp1d(
        prob_by_hour['hour'].values,
        prob_by_hour['prob_safe'].values,
        kind='linear',
        bounds_error=False,
        fill_value=(prob_by_hour['prob_safe'].iloc[0], prob_by_hour['prob_safe'].iloc[-1])
    )

    # Apply probability functions to get individual probabilities
    df['prob_person_temp'] = temp_prob_func(df['temperature'])
    df['prob_person_hour'] = hour_prob_func(df['hour'])

    # Combined probability (assuming independence)
    # P(person | temp, hour) ≈ P(person | temp) * P(person | hour) / P(person)
    overall_prob = df['has_person'].mean()
    df['prob_person_combined'] = (df['prob_person_temp'] * df['prob_person_hour']) / max(overall_prob, epsilon)

    # Clip combined probability to reasonable range
    df['prob_person_combined'] = df['prob_person_combined'].clip(upper=1.0, lower=epsilon)

    # Calculate inverse probability weights
    df['ipw_temp'] = 1.0 / df['prob_person_temp']
    df['ipw_hour'] = 1.0 / df['prob_person_hour']
    df['ipw_combined'] = 1.0 / df['prob_person_combined']

    # Normalize weights to have mean of 1 (for interpretability)
    df['ipw_temp'] = df['ipw_temp'] / df['ipw_temp'].mean()
    df['ipw_hour'] = df['ipw_hour'] / df['ipw_hour'].mean()
    df['ipw_combined'] = df['ipw_combined'] / df['ipw_combined'].mean()

    # Cap extreme weights to avoid instability (e.g., 95th percentile)
    for weight_col in ['ipw_temp', 'ipw_hour', 'ipw_combined']:
        cap = df[weight_col].quantile(0.95)
        df[weight_col] = df[weight_col].clip(upper=cap)

    return df


def prepare_data_with_weights(all_data):
    """
    Prepare combined dataset with person probability weights.

    Args:
        all_data: List of DataFrames from different CSV files

    Returns:
        Combined DataFrame with probability weights added
    """
    # Standardize column names for each dataframe before combining
    standardized_data = []
    for df in all_data:
        df = df.copy()
        # Handle both regular and _x/_y suffixed columns
        if 'inshade_count_x' in df.columns:
            # Use _x columns (primary)
            df['inshade_count'] = df['inshade_count_x']
            df['outshade_count'] = df['outshade_count_x']
            df['is_sunny'] = df['is_sunny_x']
        # If only base names exist, they're already correct
        standardized_data.append(df)

    # Combine all data
    combined_df = pd.concat(standardized_data, ignore_index=True)

    # Parse datetime
    combined_df['datetime'] = pd.to_datetime(combined_df['datetime-local'], utc=True, errors='coerce')
    combined_df['hour'] = combined_df['datetime'].dt.hour

    # Calculate person counts
    inshade = pd.to_numeric(combined_df['inshade_count'], errors='coerce').fillna(0)
    outshade = pd.to_numeric(combined_df['outshade_count'], errors='coerce').fillna(0)
    combined_df['person_count'] = inshade + outshade
    combined_df['has_person'] = (combined_df['person_count'] > 0).astype(int)

    # Use dbulb as temperature, fall back to utci_C
    combined_df['temperature'] = combined_df['dbulb'].fillna(combined_df['utci_C'])

    # Remove rows with missing critical data
    combined_df = combined_df.dropna(subset=['temperature', 'hour']).copy()

    # Calculate probability weights
    combined_df = calculate_person_probabilities(combined_df)

    return combined_df


def get_weight_statistics(df):
    """Print statistics about the calculated weights."""
    print("\n" + "="*70)
    print("INVERSE PROBABILITY WEIGHT STATISTICS")
    print("="*70)

    for weight_col in ['ipw_temp', 'ipw_hour', 'ipw_combined']:
        print(f"\n{weight_col}:")
        print(f"  Mean: {df[weight_col].mean():.3f}")
        print(f"  Median: {df[weight_col].median():.3f}")
        print(f"  Std: {df[weight_col].std():.3f}")
        print(f"  Min: {df[weight_col].min():.3f}")
        print(f"  Max: {df[weight_col].max():.3f}")
        print(f"  95th percentile: {df[weight_col].quantile(0.95):.3f}")

    print("\n" + "="*70)
