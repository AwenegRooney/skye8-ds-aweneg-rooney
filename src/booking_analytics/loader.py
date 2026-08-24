import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


def load_data(
    customers_df: pd.DataFrame,
    routes_df: pd.DataFrame,
    bookings_df: pd.DataFrame,
    engine: Engine,
) -> None:
    with engine.begin() as conn:
        print("\n ================ Loading data ================= \n\n")
        # 1. Routes (Staging -> Upsert)
        routes_df.to_sql("temp_routes", con=conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT INTO routes (route_id, agency, origin_city, destination_city, distance_km, base_fare_xaf, vehicle_class, daily_departures)
            SELECT route_id, agency, origin_city, destination_city, distance_km, base_fare_xaf, vehicle_class, daily_departures FROM temp_routes
            ON CONFLICT (route_id) DO NOTHING;
            DROP TABLE temp_routes;
        """))
        print("Routes loaded...\n")

        # 2. Customers (Staging -> Upsert)
        customers_df.to_sql(
            "temp_customers", con=conn, if_exists="replace", index=False
        )
        conn.execute(text("""
            INSERT INTO customers (customer_id, home_city, signed_up_on, segment, loyalty_tier, preferred_channel)
            SELECT customer_id, home_city, signed_up_on, segment, loyalty_tier, preferred_channel FROM temp_customers
            ON CONFLICT (customer_id) DO NOTHING;
            DROP TABLE temp_customers;
        """))
        print("Customers loaded...\n")

        # 3. Handle Orphaned Customers (Stage D Decision)
        known_customers = set(customers_df["customer_id"])
        booking_customers = set(bookings_df["customer_id"])
        orphaned_ids = booking_customers - known_customers

        if orphaned_ids:
            placeholders = pd.DataFrame(
                {
                    "customer_id": list(orphaned_ids),
                    "home_city": "UNKNOWN",
                    "signed_up_on": pd.NaT,
                    "segment": "UNKNOWN",
                    "loyalty_tier": "UNKNOWN",
                    "preferred_channel": "UNKNOWN",
                }
            )
            placeholders.to_sql(
                "temp_placeholders", con=conn, if_exists="replace", index=False
            )
            conn.execute(text("""
                INSERT INTO customers (customer_id, home_city, signed_up_on, segment, loyalty_tier, preferred_channel)
                SELECT customer_id, home_city, signed_up_on, segment, loyalty_tier, preferred_channel FROM temp_placeholders
                ON CONFLICT (customer_id) DO NOTHING;
                DROP TABLE temp_placeholders;
            """))

        # 4. Bookings (Staging -> Upsert)
        bookings_df.to_sql("temp_bookings", con=conn, if_exists="replace", index=False)
        conn.execute(text("""
            INSERT INTO bookings (booking_id, customer_id, route_id, booked_ts, travel_ts, seats, amount_xaf, channel, status)
            SELECT booking_id, customer_id, route_id, booked_ts, travel_ts, seats, amount_xaf, channel, status FROM temp_bookings
            ON CONFLICT (booking_id) DO NOTHING;
            DROP TABLE temp_bookings;
        """))
        print("Bookings loaded...\n")

        print("\n================= Done ================")
