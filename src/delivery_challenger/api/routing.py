from typing import Any


def should_route_to_challenger(payload: dict[str, Any]) -> bool:
    """
    Determines whether a prediction request should be routed to the Challenger model.
    Based on Stage C findings:
    - Distance must be between 15 km and 25 km (distance_bucket 3.0 or 4.0)
    - Hour of day must be in high-gain peak congestion slots (10, 11, 13, 14)
    - Weather must be clear (raining == 0)
    """
    distance_km = float(payload.get("distance_km", 0.0))
    hour_of_day = int(payload.get("hour_of_day", -1))
    raining = int(payload.get("raining", 0))

    # Reject if raining (underpowered / negligible gains)
    if raining == 1:
        return False

    # Allowed distance band: 15km <= distance < 25km
    valid_distance = 15.0 <= distance_km < 25.0

    # Allowed peak congestion hours
    valid_hour = hour_of_day in [10, 11, 13, 14]

    return valid_distance and valid_hour


def calculate_incumbent_prediction(payload: dict[str, Any]) -> float:
    """
    Fallback incumbent baseline rule prediction (v1.4.2).
    """
    distance_km = float(payload.get("distance_km", 0.0))
    raining = int(payload.get("raining", 0))

    base_time = 10.0 + (distance_km * 3.5)
    if raining == 1:
        base_time *= 1.25

    return round(base_time, 2)
