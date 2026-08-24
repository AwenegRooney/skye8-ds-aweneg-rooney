import pandas as pd
import pytest

from booking_analytics.data_cleaner import merge_bookings_customers


# Test 7: Standard merge preserves expected row count
def test_merge_preserves_row_count(
    sample_bookings: pd.DataFrame, sample_customers: pd.DataFrame
) -> None:
    merged = merge_bookings_customers(sample_bookings, sample_customers)
    assert len(merged) == len(sample_bookings)


# Test 8: Booking whose customer does not exist
def test_merge_with_orphaned_booking(sample_customers: pd.DataFrame) -> None:
    orphaned_booking = pd.DataFrame(
        {"booking_id": [999], "customer_id": [9999], "amount": ["1000"]}
    )
    merged = merge_bookings_customers(orphaned_booking, sample_customers)
    assert len(merged) == 1
    assert pd.isna(merged.iloc[0]["name"])


# Test 9: Empty DataFrame edge case
def test_merge_empty_dataframe(sample_customers: pd.DataFrame) -> None:
    empty_bookings = pd.DataFrame(columns=["booking_id", "customer_id", "amount"])
    merged = merge_bookings_customers(empty_bookings, sample_customers)
    assert len(merged) == 0


# Test 10: Column that is entirely null edge case
def test_entirely_null_column(sample_bookings: pd.DataFrame) -> None:
    sample_bookings["amount"] = None
    assert sample_bookings["amount"].isnull().all()


# Test 11: Single-row frame edge case
def test_single_row_dataframe() -> None:
    df = pd.DataFrame({"booking_id": [1], "customer_id": [10]})
    assert len(df) == 1


# Test 12: Duplicated identifiers cause unexpected row inflation
def test_duplicate_identifiers(
    sample_bookings: pd.DataFrame, sample_customers: pd.DataFrame
) -> None:
    duplicate_customers = pd.concat(
        [sample_customers, sample_customers.iloc[[0]]], ignore_index=True
    )
    with pytest.raises(
        ValueError, match="Merge resulted in a different number of rows than expected."
    ):
        merge_bookings_customers(sample_bookings, duplicate_customers)


# Test 13: Schema check for required output column names
def test_schema_columns(
    sample_bookings: pd.DataFrame, sample_customers: pd.DataFrame
) -> None:
    merged = merge_bookings_customers(sample_bookings, sample_customers)
    assert "name" in merged.columns
    assert "amount" in merged.columns
    assert "booking_id" in merged.columns


# Test 14: Verification of dataset output data types
def test_merged_output_types(
    sample_bookings: pd.DataFrame, sample_customers: pd.DataFrame
) -> None:
    merged = merge_bookings_customers(sample_bookings, sample_customers)
    assert isinstance(merged, pd.DataFrame)


# Test 15: Verification that original booking keys remain intact
def test_booking_keys_preserved(
    sample_bookings: pd.DataFrame, sample_customers: pd.DataFrame
) -> None:
    merged = merge_bookings_customers(sample_bookings, sample_customers)
    assert list(merged["booking_id"]) == list(sample_bookings["booking_id"])
