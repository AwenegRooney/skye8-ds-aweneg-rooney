import pandas as pd
import pytest


@pytest.fixture
def sample_bookings() -> pd.DataFrame:
    """
    Provides a standard sample bookings Dataframe.
    """
    return pd.DataFrame(
        {
            "booking_id": [101, 102, 103],
            "customer_id": [1, 2, 3],
            "amount": ["XAF 1,500", "2,000", 3000],
            "timestamp": ["2026-05-01 10:00:00", "01/05/2026 10:00", "1761076800"],
        }
    )


@pytest.fixture
def sample_customers() -> pd.DataFrame:
    """
    Provides a matching sample customers DataFrame.
    """
    return pd.DataFrame({"customer_id": [1, 2, 3], "name": ["Alice", "Bob", "Charlie"]})
