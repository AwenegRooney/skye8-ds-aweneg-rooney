import pandas as pd

from delivery_challenger.evaluation import get_metrics


def add_distance_bucket(df: pd.DataFrame) -> pd.DataFrame:
    df["distance_bucket"] = df["distance_km"] // 5
    return df


def add_hour_of_day(df: pd.DataFrame) -> pd.DataFrame:
    df["hour_of_day"] = df["requested_at"].dt.hour
    return df


def get_group_metrics(df: pd.DataFrame, column: str) -> pd.DataFrame:
    df_grouped = df.groupby(column).apply(get_metrics)

    return df_grouped


def get_all_group_data(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = add_distance_bucket(df)
    df = add_hour_of_day(df)
    column_names = [
        "distance_bucket",
        "hour_of_day",
        "package_type",
        "raining",
        "pickup_zone",
    ]
    data = {}

    for col in column_names:
        data[col] = get_group_metrics(df, col)

    return data
