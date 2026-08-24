import re
from typing import Any

import pandas as pd


def parse_timestamp(ts: str) -> pd.Timestamp:
    """
    Parse a timestamp string into a pandas Timestamp object.
    """
    if (isinstance(ts, str) and ts.isdigit()) or isinstance(ts, (int, float)):
        return pd.to_datetime(int(ts), unit="s")

    return pd.to_datetime(ts, format="mixed")


def clean_currency(amount: Any) -> float:
    """
    Clean a currency string and convert it to a float.
    """
    if pd.isna(amount):
        return 0.0
    cleaned = re.sub(r"[^\d.-]", "", str(amount))
    return float(cleaned) if cleaned else 0.0


def merge_bookings_customers(
    df_bookings: pd.DataFrame, df_customers: pd.DataFrame
) -> pd.DataFrame:
    """
    Merge bookings and customers DataFrames on the 'customer_id' column.
    """
    merge = pd.merge(df_bookings, df_customers, on="customer_id", how="left")
    if len(merge) != len(df_bookings):
        raise ValueError("Merge resulted in a different number of rows than expected.")
    return merge
