import numpy as np
import pandas as pd


def get_error(df: pd.DataFrame) -> pd.DataFrame:
    df["error"] = df["actual_minutes"] - df["predicted_minutes_v1"]
    return df


def get_absolute_error(df: pd.DataFrame) -> pd.DataFrame:
    df["absolute_error"] = df["error"].abs()
    return df


def get_squared_error(df: pd.DataFrame) -> pd.DataFrame:
    df["squared_error"] = df["error"] ** 2
    return df


def get_metrics(df: pd.DataFrame) -> pd.Series:
    df = get_error(df)
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
            "Percentage of Errors > 10": error_percentage,
        }
    )
