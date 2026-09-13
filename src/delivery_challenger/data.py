from pathlib import Path

import pandas as pd

from booking_analytics.data_cleaner import parse_timestamp


def load_data(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    deliveries_path = data_dir / "raw/deliveries.csv"
    riders_path = data_dir / "raw/riders.csv"
    zones_path = data_dir / "raw/zones.csv"

    deliveries = pd.read_csv(deliveries_path)
    riders = pd.read_csv(riders_path)
    zones = pd.read_csv(zones_path)

    return deliveries, riders, zones


def clean_data(
    deliveries: pd.DataFrame, riders: pd.DataFrame, zones: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    category_map = {"FALSE": 0, "TRUE": 1, "YES": 1, "NO": 0, "1": 1, "0": 0}
    deliveries = deliveries.drop_duplicates(subset=["delivery_id"])
    deliveries["requested_at"] = deliveries["requested_at"].map(
        lambda x: parse_timestamp(x)
    )
    deliveries["raining"] = deliveries["raining"].map(
        lambda x: category_map.get(str(x).upper())
    )
    riders["joined_on"] = riders["joined_on"].map(lambda x: parse_timestamp(x))
    zones["market_zone"] = zones["market_zone"].map(
        lambda x: category_map.get(str(x).upper())
    )
    return deliveries, riders, zones


def merge_data(
    deliveries: pd.DataFrame, riders: pd.DataFrame, zones: pd.DataFrame
) -> pd.DataFrame:
    new_deliveries = deliveries.merge(riders, how="left", on="rider_id")

    new_deliveries = new_deliveries.merge(
        zones,
        how="left",
        left_on="pickup_zone",
        right_on="zone",
        suffixes=(None, "_pickup"),
    )

    new_deliveries = new_deliveries.merge(
        zones,
        how="left",
        left_on="dropoff_zone",
        right_on="zone",
        suffixes=(None, "_dropoff"),
    )

    return new_deliveries.drop(columns=["zone_dropoff"])


def get_chronological_split(
    df: pd.DataFrame, holdout_ratio: float = 0.2
) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = df.sort_values("requested_at").reset_index(drop=True)

    size = int(len(df) * (1 - holdout_ratio))

    return df.iloc[:size].reset_index(), df.iloc[size:].reset_index()


def get_processed_data(data_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame]:
    df_deliveries, df_riders, df_zones = load_data(data_dir)

    df_deliveries, df_riders, df_zones = clean_data(df_deliveries, df_riders, df_zones)

    df = merge_data(df_deliveries, df_riders, df_zones)

    history, holdout = get_chronological_split(df)

    history.to_csv(data_dir / "processed/history.csv", index=False)
    holdout.to_csv(data_dir / "processed/holdout.csv", index=False)

    return history, holdout
