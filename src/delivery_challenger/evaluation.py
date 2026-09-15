import numpy as np
import pandas as pd


def get_error(df: pd.DataFrame, actual_col: str, predicted_col: str) -> pd.DataFrame:
    df["error"] = df[actual_col] - df[predicted_col]
    return df


def get_absolute_error(df: pd.DataFrame) -> pd.DataFrame:
    df["absolute_error"] = df["error"].abs()
    return df


def get_squared_error(df: pd.DataFrame) -> pd.DataFrame:
    df["squared_error"] = df["error"] ** 2
    return df


def get_metrics(
    df: pd.DataFrame,
    actual_col: str = "actual_minutes",
    predicted_col: str = "predicted_minutes_v1",
) -> pd.Series:
    df = get_error(df, actual_col, predicted_col)
    df = get_absolute_error(df)
    df = get_squared_error(df)

    mae = df["absolute_error"].mean()
    rmse = np.sqrt(df["squared_error"].mean())
    median = df["absolute_error"].median()

    error_percentage = (df[df["absolute_error"] > 10].shape[0] / df.shape[0]) * 100

    return pd.Series(
        {
            "Mean Absolute Error": mae,
            "Root Mean Square Error": rmse,
            "Median Absolute Error": median,
            "Percentage of Errors above 10 minutes": error_percentage,
        }
    )
