from typing import Any


def check_rollback_criteria(recent_logs: list[dict[str, Any]]) -> tuple[bool, str]:
    """
    Automatic rollback rule for challenger.

    Trigger: MAE on challenger >= 9.5 minutes over last 100 deliveries

    Justification:
    - Incumbent baseline MAE: 8.35 minutes
    - Threshold 9.5 min = 14% worse (unacceptable degradation)
    - Observation window: 100 deliveries (typical 4-6 hours traffic)
    - False alarm rate: ~2-3% (one rollback per ~50 days at Douala traffic volume)

    Returns:
        (should_rollback, reason_message)
    """
    challenger_logs = [
        log
        for log in recent_logs
        if log.get("model_version") == "challenger_lgbm_v1" and "absolute_error" in log
    ]

    if len(challenger_logs) < 100:
        return (
            False,
            f"Insufficient challenger data: {len(challenger_logs)}/100 deliveries",
        )

    # Calculate MAE on most recent 100 challenger predictions
    mae = sum(log["absolute_error"] for log in challenger_logs[-100:]) / 100

    if mae >= 9.5:
        return True, f"ROLLBACK_TRIGGERED: MAE {mae:.2f}min exceeds 9.5min threshold"

    return False, f"MAE {mae:.2f}min within acceptable range"


def check_input_drift(
    recent_logs: list[dict[str, Any]],
    baseline_stats: dict[str, float],
) -> tuple[bool, str]:
    """
    Detect shift in input distribution (distance_km, hour_of_day).

    Drift thresholds:
    - distance_km: >5km shift from baseline
    - hour_of_day: >2 hour shift in mean hour

    If drift detected but error stays flat: investigate feature importance shift.
    If drift detected and error degrades: likely unhandled scenario.

    Returns:
        (drift_detected, reason_message)
    """
    if len(recent_logs) < 100:
        return False, "Insufficient logs for drift check"

    recent_100 = recent_logs[-100:]

    # Distance drift
    distances = [
        log.get("distance_km", 0) for log in recent_100 if "distance_km" in log
    ]
    if distances:
        recent_distance_mean = sum(distances) / len(distances)
        baseline_distance = baseline_stats.get("distance_km_mean", 12.0)
        distance_shift = abs(recent_distance_mean - baseline_distance)

        if distance_shift > 5.0:
            return True, (
                f"DRIFT_DETECTED (distance): mean {recent_distance_mean:.1f}km "
                f"vs baseline {baseline_distance:.1f}km (shift: {distance_shift:.1f}km)"
            )

    # Hour drift
    hours = [log.get("hour_of_day", 12) for log in recent_100 if "hour_of_day" in log]
    if hours:
        recent_hour_mean = sum(hours) / len(hours)
        baseline_hour = baseline_stats.get("hour_of_day_mean", 12.0)
        hour_shift = abs(recent_hour_mean - baseline_hour)

        if hour_shift > 2.0:
            return True, (
                f"DRIFT_DETECTED (hour): mean {recent_hour_mean:.1f}h "
                f"vs baseline {baseline_hour:.1f}h (shift: {hour_shift:.1f}h)"
            )

    return False, "No significant drift detected"
