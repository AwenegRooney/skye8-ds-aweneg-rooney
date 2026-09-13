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


@pytest.fixture
def sample_deliveries() -> pd.DataFrame:
    """
    Provides sample data for deliveries.
    """
    return pd.DataFrame(
        {
            "delivery_id": ["DV-0054096", "DV-0054090", "Dv-0054094"],
            "requested_at": ["2026-05-01 10:00:00", "01/05/2026 10:00", "1761076800"],
            "rider_id": ["RD-029", "RD-030", "RD-032"],
            "pickup_zone": ["PK14", "Akwa", "Deido"],
            "dropoff_zone": ["Deido", "Bepanda", "Bonapriso"],
            "distance_km": [3.31, 7.43, 10.83],
            "package_type": ["groceries", "pharmacy", "groceries"],
            "raining": ["yes", "no", "False"],
            "actual_minutes": [38.5, 43.5, 44.6],
            "predicted_minutes_v1": [28.6, 50.8, 62.9],
            "model_version": ["v1.4.2", "v1.4.2", "v1.4.2"],
        }
    )


@pytest.fixture
def sample_riders() -> pd.DataFrame:
    """
    Sample riders data"
    """
    return pd.DataFrame(
        {
            "rider_id": ["RD-029", "RD-030", "RD-032"],
            "joined_on": ["2023-06-26", "2023-03-06", "2023-05-16"],
            "vehicle": ["tricycle", "motorbike", "bicycle"],
            "experience_months": [39, 24, 6],
            "home_zone": ["Deido", "Akwa", "PK14"],
        }
    )


@pytest.fixture
def sample_zones() -> pd.DataFrame:
    """
    Sample zones data
    """
    return pd.DataFrame(
        {
            "zone": ["Akwa", "Deido", "Bepanda", "PK14", "Bonapriso"],
            "congestion_index": [1.60, 1.80, 2.00, 2.4, 1.3],
            "tarred_share_pct": [77, 87, 85, 68, 84],
            "market_zone": [False, "yes", 1, 0, "true"],
        }
    )


@pytest.fixture
def typed_metrics_df() -> pd.DataFrame:
    """Provides a strictly typed DataFrame for evaluation and segment testing."""
    df = pd.DataFrame(
        {
            "actual_minutes": [20.0, 30.0, 45.0, 15.0],
            "predicted_minutes_v1": [20.0, 42.0, 40.0, 10.0],  # Errors: 0, -12, 5, 5
            "distance_km": [2.5, 7.1, 12.0, 4.9],
            "requested_at": [
                "2026-09-01 08:15:00",
                "2026-09-01 14:30:00",
                "2026-09-02 23:59:00",
                "2026-09-03 00:05:00",
            ],
            "package_type": ["groceries", "pharmacy", "groceries", "documents"],
            "raining": [0, 1, 0, 0],
            "pickup_zone": ["Akwa", "Deido", "Bonanjo", "Akwa"],
        }
    )

    # Explicit Type Casting
    df["actual_minutes"] = df["actual_minutes"].astype("float64")
    df["predicted_minutes_v1"] = df["predicted_minutes_v1"].astype("float64")
    df["distance_km"] = df["distance_km"].astype("float64")
    df["requested_at"] = pd.to_datetime(df["requested_at"])
    df["package_type"] = df["package_type"].astype("category")
    df["raining"] = df["raining"].astype("int8")
    df["pickup_zone"] = df["pickup_zone"].astype("string")

    return df
