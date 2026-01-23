# ABOUTME: Unit tests for visualize_shade_ratios.py visualization functions.
# ABOUTME: Tests data processing and plot generation functionality.

import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import os
from visualize_shade_ratios import (
    load_city_data,
    calculate_shade_percentage,
    create_overall_time_of_day_plot,
    create_people_count_vs_time_plot,
    create_people_count_vs_temp_plot,
    prepare_all_rows_data,
    create_all_rows_people_vs_time_plot,
    create_all_rows_people_vs_temp_plot,
    prepare_sunny_rows_data,
    create_sunny_people_vs_time_plot,
    create_sunny_people_vs_temp_plot,
    calculate_city_weights
)


def test_create_overall_time_of_day_plot(tmp_path):
    """Test that time-of-day LOESS plot is created with correct data."""
    # Create test data
    city_data = {
        'TestCity': pd.DataFrame({
            'datetime-local': [
                '2024-08-24 08:00:00-03:00',
                '2024-08-24 12:00:00-03:00',
                '2024-08-24 16:00:00-03:00',
                '2024-08-24 18:00:00-03:00'
            ],
            'is_sunny_x': [True, True, True, True],
            'inshade_count_x': [5, 8, 10, 7],
            'outshade_count_x': [5, 2, 5, 3]
        })
    }

    output_file = tmp_path / "test_time_plot.png"

    # This should create a plot
    create_overall_time_of_day_plot(
        city_data,
        'Time of Day (Hour)',
        str(output_file)
    )

    # Verify the file was created
    assert output_file.exists(), "Plot file should be created"
    assert output_file.stat().st_size > 0, "Plot file should not be empty"


def test_create_people_count_vs_time_plot(tmp_path):
    """Test that people count vs time of day LOESS plot is created."""
    # Create test data
    city_data = {
        'TestCity': pd.DataFrame({
            'datetime-local': [
                '2024-08-24 08:00:00-03:00',
                '2024-08-24 12:00:00-03:00',
                '2024-08-24 16:00:00-03:00',
                '2024-08-24 18:00:00-03:00'
            ],
            'is_sunny_x': [True, True, True, True],
            'inshade_count_x': [5, 8, 10, 7],
            'outshade_count_x': [5, 2, 5, 3]
        })
    }

    output_file = tmp_path / "test_people_time_plot.png"

    # This should create a plot
    create_people_count_vs_time_plot(
        city_data,
        'Time of Day (Hour)',
        str(output_file)
    )

    # Verify the file was created
    assert output_file.exists(), "Plot file should be created"
    assert output_file.stat().st_size > 0, "Plot file should not be empty"


def test_create_people_count_vs_temp_plot(tmp_path):
    """Test that people count vs temperature LOESS plot is created."""
    # Create test data
    city_data = {
        'TestCity': pd.DataFrame({
            'datetime-local': [
                '2024-08-24 08:00:00-03:00',
                '2024-08-24 12:00:00-03:00',
                '2024-08-24 16:00:00-03:00',
                '2024-08-24 18:00:00-03:00'
            ],
            'is_sunny_x': [True, True, True, True],
            'inshade_count_x': [5, 8, 10, 7],
            'outshade_count_x': [5, 2, 5, 3],
            'wbulb': [25.0, 28.0, 30.0, 27.0]
        })
    }

    output_file = tmp_path / "test_people_temp_plot.png"

    # This should create a plot
    create_people_count_vs_temp_plot(
        city_data,
        'wbulb',
        'Wet Bulb Temperature (°C)',
        str(output_file)
    )

    # Verify the file was created
    assert output_file.exists(), "Plot file should be created"
    assert output_file.stat().st_size > 0, "Plot file should not be empty"


def test_prepare_all_rows_data():
    """Test that prepare_all_rows_data includes all valid rows regardless of sunny status or people count."""
    # Create test data with mix of sunny/not sunny, 0 people/with people
    df = pd.DataFrame({
        'is_sunny_x': [True, False, True, True],
        'inshade_count_x': [5, 0, 0, np.nan],  # Last row has error
        'outshade_count_x': [5, 0, 3, 8],
        'datetime-local': [
            '2024-08-24 08:00:00-03:00',
            '2024-08-24 12:00:00-03:00',
            '2024-08-24 16:00:00-03:00',
            '2024-08-24 18:00:00-03:00'
        ]
    })

    result = prepare_all_rows_data(df)

    # Should include first 3 rows (excluding the one with NaN)
    assert len(result) == 3, "Should include all rows except those with NaN counts"
    assert 'total_people' in result.columns
    assert list(result['total_people']) == [10, 0, 3], "Should calculate total people correctly"


def test_create_all_rows_people_vs_time_plot(tmp_path):
    """Test that all-rows people count vs time plot is created."""
    city_data = {
        'TestCity': pd.DataFrame({
            'datetime-local': [
                '2024-08-24 08:00:00-03:00',
                '2024-08-24 12:00:00-03:00',
                '2024-08-24 16:00:00-03:00',
                '2024-08-24 18:00:00-03:00'
            ],
            'is_sunny_x': [True, False, True, False],  # Mix of sunny/not sunny
            'inshade_count_x': [5, 0, 10, 0],
            'outshade_count_x': [5, 0, 5, 2]
        })
    }

    output_file = tmp_path / "test_all_rows_people_time_plot.png"

    create_all_rows_people_vs_time_plot(
        city_data,
        'Time of Day (Hour)',
        str(output_file)
    )

    assert output_file.exists(), "Plot file should be created"
    assert output_file.stat().st_size > 0, "Plot file should not be empty"


def test_create_all_rows_people_vs_temp_plot(tmp_path):
    """Test that all-rows people count vs temp plot is created."""
    city_data = {
        'TestCity': pd.DataFrame({
            'datetime-local': [
                '2024-08-24 08:00:00-03:00',
                '2024-08-24 12:00:00-03:00',
                '2024-08-24 16:00:00-03:00',
                '2024-08-24 18:00:00-03:00'
            ],
            'is_sunny_x': [True, False, True, False],  # Mix of sunny/not sunny
            'inshade_count_x': [5, 0, 10, 0],
            'outshade_count_x': [5, 0, 5, 2],
            'wbulb': [25.0, 28.0, 30.0, 27.0]
        })
    }

    output_file = tmp_path / "test_all_rows_people_temp_plot.png"

    create_all_rows_people_vs_temp_plot(
        city_data,
        'wbulb',
        'Wet Bulb Temperature (°C)',
        str(output_file)
    )

    assert output_file.exists(), "Plot file should be created"
    assert output_file.stat().st_size > 0, "Plot file should not be empty"


def test_prepare_sunny_rows_data():
    """Test that prepare_sunny_rows_data includes only sunny rows regardless of people count."""
    # Create test data with mix of sunny/not sunny, 0 people/with people
    df = pd.DataFrame({
        'is_sunny_x': [True, False, True, True, True],
        'inshade_count_x': [5, 0, 0, 3, np.nan],  # Last row has error
        'outshade_count_x': [5, 0, 3, 0, 8],
        'datetime-local': [
            '2024-08-24 08:00:00-03:00',
            '2024-08-24 12:00:00-03:00',
            '2024-08-24 16:00:00-03:00',
            '2024-08-24 18:00:00-03:00',
            '2024-08-24 20:00:00-03:00'
        ]
    })

    result = prepare_sunny_rows_data(df)

    # Should include first, third, and fourth rows (sunny=True and valid counts)
    assert len(result) == 3, "Should include only sunny rows with valid counts"
    assert 'total_people' in result.columns
    assert list(result['total_people']) == [10, 3, 3], "Should calculate total people correctly"
    # Verify all rows are sunny
    assert all(result['is_sunny_x'] == True), "All rows should be sunny"


def test_create_sunny_people_vs_time_plot(tmp_path):
    """Test that sunny-only people count vs time plot is created."""
    city_data = {
        'TestCity': pd.DataFrame({
            'datetime-local': [
                '2024-08-24 08:00:00-03:00',
                '2024-08-24 12:00:00-03:00',
                '2024-08-24 16:00:00-03:00',
                '2024-08-24 18:00:00-03:00'
            ],
            'is_sunny_x': [True, False, True, True],  # Mix of sunny/not sunny
            'inshade_count_x': [5, 0, 0, 7],
            'outshade_count_x': [5, 0, 5, 3]
        })
    }

    output_file = tmp_path / "test_sunny_people_time_plot.png"

    create_sunny_people_vs_time_plot(
        city_data,
        'Time of Day (Hour)',
        str(output_file)
    )

    assert output_file.exists(), "Plot file should be created"
    assert output_file.stat().st_size > 0, "Plot file should not be empty"


def test_create_sunny_people_vs_temp_plot(tmp_path):
    """Test that sunny-only people count vs temp plot is created."""
    city_data = {
        'TestCity': pd.DataFrame({
            'datetime-local': [
                '2024-08-24 08:00:00-03:00',
                '2024-08-24 12:00:00-03:00',
                '2024-08-24 16:00:00-03:00',
                '2024-08-24 18:00:00-03:00'
            ],
            'is_sunny_x': [True, False, True, True],  # Mix of sunny/not sunny
            'inshade_count_x': [5, 0, 0, 7],
            'outshade_count_x': [5, 0, 5, 3],
            'wbulb': [25.0, 28.0, 30.0, 27.0]
        })
    }

    output_file = tmp_path / "test_sunny_people_temp_plot.png"

    create_sunny_people_vs_temp_plot(
        city_data,
        'wbulb',
        'Wet Bulb Temperature (°C)',
        str(output_file)
    )

    assert output_file.exists(), "Plot file should be created"
    assert output_file.stat().st_size > 0, "Plot file should not be empty"


def test_calculate_city_weights():
    """Test that city weights are calculated so each city has equal total weight."""
    # Create data points with city labels
    city_labels = ['CityA', 'CityA', 'CityA', 'CityB', 'CityB', 'CityC']

    weights = calculate_city_weights(city_labels)

    # Verify we got the right number of weights
    assert len(weights) == 6, "Should have one weight per data point"

    # Verify weights are correct
    # CityA has 3 points, so each should have weight 1/3
    # CityB has 2 points, so each should have weight 1/2
    # CityC has 1 point, so it should have weight 1
    expected = [1/3, 1/3, 1/3, 1/2, 1/2, 1.0]
    assert np.allclose(weights, expected), f"Weights should be {expected}, got {weights}"

    # Verify each city has total weight of 1
    city_a_weight = sum(weights[i] for i, city in enumerate(city_labels) if city == 'CityA')
    city_b_weight = sum(weights[i] for i, city in enumerate(city_labels) if city == 'CityB')
    city_c_weight = sum(weights[i] for i, city in enumerate(city_labels) if city == 'CityC')

    assert np.isclose(city_a_weight, 1.0), "CityA total weight should be 1.0"
    assert np.isclose(city_b_weight, 1.0), "CityB total weight should be 1.0"
    assert np.isclose(city_c_weight, 1.0), "CityC total weight should be 1.0"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
