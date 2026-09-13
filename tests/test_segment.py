import numpy as np
import pandas as pd

from delivery_challenger.segment import (
    add_distance_bucket,
    add_hour_of_day,
    get_all_group_data,
)


def test_add_distance_bucket(typed_metrics_df: pd.DataFrame) -> None:
    df = add_distance_bucket(typed_metrics_df.copy())
    assert "distance_bucket" in df.columns
    # Distances: [2.5, 7.1, 12.0, 4.9] // 5 -> [0.0, 1.0, 2.0, 0.0]
    np.testing.assert_array_equal(
        df["distance_bucket"].values, np.array([0.0, 1.0, 2.0, 0.0])
    )


def test_add_hour_of_day(typed_metrics_df: pd.DataFrame) -> None:
    df = add_hour_of_day(typed_metrics_df.copy())
    assert "hour_of_day" in df.columns
    assert df["hour_of_day"].dtype in ["int64", "int32"]
    # Hours from mock data: 8, 14, 23, 0
    np.testing.assert_array_equal(df["hour_of_day"].values, np.array([8, 14, 23, 0]))


def test_get_all_group_data(typed_metrics_df: pd.DataFrame) -> None:
    result = get_all_group_data(typed_metrics_df.copy())

    expected_keys = [
        "distance_bucket",
        "hour_of_day",
        "package_type",
        "raining",
        "pickup_zone",
    ]

    # Check that all dictionary keys exist
    for key in expected_keys:
        assert key in result, f"Missing key: {key} in segmented results."

    # Verify that the groupby operation actually occurred (length > 0)
    assert len(result["pickup_zone"]) > 0
