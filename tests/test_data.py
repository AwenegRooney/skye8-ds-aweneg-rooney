import numpy as np
import pandas as pd

from delivery_challenger.data import clean_data, get_chronological_split, merge_data


def test_clean_data_transformations(
    sample_deliveries: pd.DataFrame,
    sample_riders: pd.DataFrame,
    sample_zones: pd.DataFrame,
) -> None:
    sample_deliveries = pd.concat(
        [sample_deliveries, sample_deliveries.iloc[[0]]], ignore_index=True
    )
    initial_length = len(sample_deliveries)

    clean_deliv, clean_riders, clean_zones = clean_data(
        sample_deliveries, sample_riders, sample_zones
    )

    assert len(clean_deliv) == initial_length - 1
    assert clean_deliv["delivery_id"].is_unique

    assert pd.api.types.is_datetime64_any_dtype(clean_deliv["requested_at"])
    assert pd.api.types.is_datetime64_any_dtype(clean_riders["joined_on"])

    assert set(clean_deliv["raining"].unique()).issubset({0, 1})
    assert set(clean_zones["market_zone"].unique()).issubset({0, 1})


def test_merge_data_relational_joins(
    sample_deliveries: pd.DataFrame,
    sample_riders: pd.DataFrame,
    sample_zones: pd.DataFrame,
) -> None:
    merged_df = merge_data(sample_deliveries, sample_riders, sample_zones)

    assert len(merged_df) == len(sample_deliveries)

    assert "vehicle" in merged_df.columns
    assert "experience_months" in merged_df.columns

    assert "zone_dropoff" not in merged_df.columns


def test_get_chronological_split() -> None:
    dates = pd.date_range(start="2026-09-01", periods=10, freq="D")
    df = pd.DataFrame(
        {"requested_at": np.random.permutation(dates), "value": range(10)}
    )

    train_df, test_df = get_chronological_split(df, holdout_ratio=0.2)

    assert len(train_df) == 8
    assert len(test_df) == 2

    assert train_df["requested_at"].max() < test_df["requested_at"].min()

    assert list(train_df.index) == list(range(8))
    assert list(test_df.index) == list(range(2))
