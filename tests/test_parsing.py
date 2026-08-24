import pytest

from booking_analytics.data_cleaner import clean_currency, parse_timestamp


# Test 1: Parametrised test covering 3 different timestamp formats at once
@pytest.mark.parametrize(
    "ts_input, expected_year, expected_month, expected_day",
    [
        ("2026-05-15 14:30:00", 2026, 5, 15),
        ("15/05/2026 14:30:00", 2026, 5, 15),
        ("1778803200", 2026, 5, 15),
    ],
)
def test_parse_timestamp_formats(
    ts_input: str, expected_year: int, expected_month: int, expected_day: int
) -> None:
    parsed = parse_timestamp(ts_input)
    assert parsed.year == expected_year
    assert parsed.month == expected_month
    assert parsed.day == expected_day


# Test 2: Standard currency parsing
def test_clean_currency_standard() -> None:
    assert clean_currency("1500") == 1500.0


# Test 3: Currency parseing with commas
def test_clean_with_comma() -> None:
    assert clean_currency("1,500.50") == 1500.50


# Test 4: Currency parsing with text/currency prefix
def test_clean_currency_with_prefix() -> None:
    assert clean_currency("XAF 5,000") == 5000.0


# Test 5: Currency parsing given null or NaN inputs
def test_clean_currency_null_or_nan() -> None:
    assert clean_currency(None) == 0.0
    assert clean_currency(float("nan")) == 0.0


# Test 6: currency parsing given empty string
def clean_currency_empty_string() -> None:
    assert clean_currency("") == 0.0
