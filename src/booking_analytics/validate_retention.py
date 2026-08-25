import pandas as pd

from .db import get_engine

# 1. Pull the data from Postgres
engine = get_engine()
with engine.begin() as conn:
    customers = pd.read_sql(
        "SELECT customer_id, signed_up_on FROM customers WHERE signed_up_on IS NOT NULL;",
        conn,
        parse_dates=["signed_up_on"],
    )
    bookings = pd.read_sql(
        "SELECT customer_id, booked_ts, status FROM bookings;",
        conn,
        parse_dates=["booked_ts"],
    )

# 2. Get the cohort month (signup month) and booking month
customers["signup_month"] = customers["signed_up_on"].dt.to_period("M")

# Make sure we check only confirmed bookings to match what SQL is doing
confirmed_bookings = bookings[bookings["status"].str.lower() == "confirmed"].copy()
confirmed_bookings["booked_month"] = confirmed_bookings["booked_ts"].dt.to_period("M")

# 3. Merge them together on customer_id
merged = pd.merge(customers, confirmed_bookings, on="customer_id", how="left")

# Calculate the month difference (offset)
merged["month_offset"] = (
    merged["booked_month"].dt.year - merged["signup_month"].dt.year
) * 12 + (merged["booked_month"].dt.month - merged["signup_month"].dt.month)

# 4. Build the retention table
# Base cohort size (Month 0)
cohort_sizes = (
    customers.groupby("signup_month")["customer_id"].nunique().rename("month_0_cohort")
)

# Filter for relative months 1 through 6
retention_data = merged[merged["month_offset"].between(1, 6)]

# Count unique customers per cohort for each month offset
retention_matrix = (
    retention_data.groupby(["signup_month", "month_offset"])["customer_id"]
    .nunique()
    .unstack(fill_value=0)
    .reindex(columns=range(1, 7), fill_value=0)
)
retention_matrix.columns = [f"month_{i}_retention" for i in range(1, 7)]

# Combine Month 0 with months 1-6
final_retention = (
    pd.concat([cohort_sizes, retention_matrix], axis=1).fillna(0).astype(int)
)

print("--- PANDAS COHORT RETENTION MATRIX ---")
print(final_retention.head(10))

# Save output to docs folder
final_retention.to_csv("data/processed/pandas_retention_validation.csv")
print(
    "\nDone! Exported validation results to data/processed/pandas_retention_validation.csv"
)
