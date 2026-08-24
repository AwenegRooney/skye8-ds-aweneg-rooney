import sys
import pandas as pd
from pathlib import Path

from .data_cleaner import parse_timestamp, clean_currency
from .db import get_engine
from .loader import load_data


def main() -> None:
    if len(sys.argv) < 4:
        print("Usage: booking-analytics load --raw <path_to_raw_data>")
        sys.exit(1)
    args = sys.argv
    raw_data_path = args[args.index("--raw") + 1]
    raw_path = Path(raw_data_path)

    engine = get_engine()

    # Reading raw csv files
    bookings_df = pd.read_csv(f"{raw_path}/bookings.csv")
    customers_df = pd.read_csv(f"{raw_path}/customers.csv")
    routes_df = pd.read_csv(f"{raw_path}/routes.csv")

    # Cleaning data
    bookings_df["booked_ts"] = bookings_df["booked_ts"].map(
        lambda x: parse_timestamp(x)
    )
    bookings_df["travel_ts"] = bookings_df["travel_ts"].map(
        lambda x: parse_timestamp(x)
    )
    bookings_df["amount_xaf"] = bookings_df["amount_xaf"].map(
        lambda x: clean_currency(x)
    )
    customers_df["signed_up_on"] = customers_df["signed_up_on"].map(
        lambda x: parse_timestamp(x)
    )
    routes_df["base_fare_xaf"] = routes_df["base_fare_xaf"].map(
        lambda x: clean_currency(x)
    )

    load_data(customers_df, routes_df, bookings_df, engine)
    print("Successfully loaded data")


if __name__ == "__main__":
    main()
