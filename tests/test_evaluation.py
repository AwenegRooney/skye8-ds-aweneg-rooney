import numpy as np
import pandas as pd

from delivery_challenger.evaluation import (
    get_absolute_error,
    get_error,
    get_metrics,
    get_squared_error,
)


def test_get_error_calculations(typed_metrics_df: pd.DataFrame) -> None:
    df = get_error(typed_metrics_df.copy(), "actual_minutes", "predicted_minutes_v1")
    assert "error" in df.columns
    assert df["error"].dtype == "float64"
    np.testing.assert_array_equal(df["error"].values, np.array([0.0, -12.0, 5.0, 5.0]))

    df = get_absolute_error(df)
    assert "absolute_error" in df.columns
    np.testing.assert_array_equal(
        df["absolute_error"].values, np.array([0.0, 12.0, 5.0, 5.0])
    )

    df = get_squared_error(df)
    assert "squared_error" in df.columns
    np.testing.assert_array_equal(
        df["squared_error"].values, np.array([0.0, 144.0, 25.0, 25.0])
    )


def test_get_metrics_accuracy(typed_metrics_df: pd.DataFrame) -> None:
    metrics: dict[str, float] = get_metrics(
        typed_metrics_df.copy(), "actual_minutes", "predicted_minutes_v1"
    )

    expected_mae = (0 + 12 + 5 + 5) / 4.0
    expected_rmse = np.sqrt((0 + 144 + 25 + 25) / 4.0)
    expected_median = 5.0
    expected_pct_over_10 = (1.0 / 4.0) * 100

    assert np.isclose(metrics["Mean Absolute Error"], expected_mae)
    assert np.isclose(metrics["Root Mean Square Error"], expected_rmse)
    assert np.isclose(metrics["Median Absolute Error"], expected_median)
    assert np.isclose(
        metrics["Percentage of Errors above 10 minutes"], expected_pct_over_10
    )
