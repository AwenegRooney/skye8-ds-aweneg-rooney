import json
import logging
import os
import time
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Any

import mlflow.pyfunc
import pandas as pd
from fastapi import FastAPI, Response, status
from pydantic import BaseModel, Field

from delivery_challenger.api.routing import (
    calculate_incumbent_prediction,
    should_route_to_challenger,
)
from delivery_challenger.monitoring import check_input_drift, check_rollback_criteria

# Configure logger
logger = logging.getLogger("delivery_challenger.routing")
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)

challenger_model: Any | None = None
is_circuit_breaker_open: bool = False

# In-memory log buffer for monitoring (in production: use database or external logging)
prediction_logs: list[dict[str, Any]] = []
MAX_LOG_BUFFER = 10000

# Baseline statistics for drift detection (from Stage A findings)
BASELINE_STATS = {
    "distance_km_mean": 12.5,
    "hour_of_day_mean": 12.0,
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    global challenger_model
    try:
        model_uri = os.getenv("MODEL_URI", "models:/delivery-challengers/Staging")
        challenger_model = mlflow.pyfunc.load_model(model_uri)
    except Exception:  # noqa: BLE001
        challenger_model = None
    yield


app = FastAPI(
    title="Delivery Time Prediction API",
    version="1.0.0",
    description="Canary-routed prediction service with audit logging & fast rollback.",
    lifespan=lifespan,
)


class PredictionRequest(BaseModel):
    distance_km: float = Field(..., gt=0, json_schema_extra={"example": 18.5})
    experience_months: float = Field(..., ge=0, json_schema_extra={"example": 24.0})
    hour_of_day: int = Field(..., ge=0, le=23, json_schema_extra={"example": 11})
    raining: int = Field(..., ge=0, le=1, json_schema_extra={"example": 0})
    congestion_index: float = Field(..., ge=0, json_schema_extra={"example": 0.65})
    tarred_share_pct: float = Field(
        ..., ge=0, le=100, json_schema_extra={"example": 80.0}
    )
    congestion_index_dropoff: float = Field(
        ..., ge=0, json_schema_extra={"example": 0.55}
    )
    tarred_share_pct_dropoff: float = Field(
        ..., ge=0, le=100, json_schema_extra={"example": 75.0}
    )
    package_type: str = Field(..., json_schema_extra={"example": "food"})
    pickup_zone: str = Field(..., json_schema_extra={"example": "Akwa"})
    vehicle: str = Field(..., json_schema_extra={"example": "motorbike"})
    dropoff_zone: str = Field(..., json_schema_extra={"example": "Bonanjo"})
    home_zone: str = Field(..., json_schema_extra={"example": "Bassa"})
    market_zone_dropoff: int = Field(..., json_schema_extra={"example": 1})
    market_zone: int = Field(..., json_schema_extra={"example": 0})


class PredictionResponse(BaseModel):
    predicted_minutes: float
    model_version: str
    routed_to_challenger: bool


class GroundTruthRequest(BaseModel):
    delivery_id: str
    actual_minutes: float
    predicted_minutes: float
    model_version: str


def log_routing_decision(
    payload: dict[str, Any],
    routed_to_challenger: bool,
    model_version: str,
    prediction: float,
    reason: str,
    latency_ms: float,
) -> None:
    """Logs structured JSON audit record for routing decision."""
    log_entry = {
        "timestamp": time.time(),
        "distance_km": payload.get("distance_km"),
        "hour_of_day": payload.get("hour_of_day"),
        "raining": payload.get("raining"),
        "routed_to_challenger": routed_to_challenger,
        "model_version": model_version,
        "prediction_minutes": prediction,
        "routing_reason": reason,
        "latency_ms": latency_ms,
    }
    logger.info(f"ROUTING_DECISION: {json.dumps(log_entry)}")


def log_ground_truth(
    delivery_id: str,
    actual_minutes: float,
    predicted_minutes: float,
    model_version: str,
) -> None:
    """Logs ground truth outcome and computes error."""
    absolute_error = abs(actual_minutes - predicted_minutes)
    log_entry = {
        "timestamp": time.time(),
        "delivery_id": delivery_id,
        "actual_minutes": actual_minutes,
        "predicted_minutes": predicted_minutes,
        "model_version": model_version,
        "absolute_error": absolute_error,
    }
    logger.info(f"GROUND_TRUTH: {json.dumps(log_entry)}")

    # Store in buffer for monitoring checks
    global prediction_logs
    prediction_logs.append(log_entry)
    if len(prediction_logs) > MAX_LOG_BUFFER:
        prediction_logs = prediction_logs[-MAX_LOG_BUFFER:]

    # Check rollback criteria every ground truth record
    should_rollback, reason = check_rollback_criteria(prediction_logs)
    if should_rollback:
        logger.error(f"MONITORING_ALERT: {reason}")

    # Check drift detection
    drift_detected, drift_reason = check_input_drift(prediction_logs, BASELINE_STATS)
    if drift_detected:
        logger.warning(f"DRIFT_ALERT: {drift_reason}")


@app.get("/health", status_code=status.HTTP_200_OK)  # type: ignore[untyped-decorator]
def health_check(response: Response) -> dict[str, Any]:
    global is_circuit_breaker_open  # noqa: PLW0602
    if is_circuit_breaker_open:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "unhealthy",
            "reason": "Circuit breaker active / forced rollback",
        }

    return {
        "status": "healthy",
        "challenger_loaded": challenger_model is not None,
    }


@app.post("/rollback", status_code=status.HTTP_200_OK)  # type: ignore[untyped-decorator]
def trigger_rollback() -> dict[str, str]:
    global is_circuit_breaker_open
    is_circuit_breaker_open = True
    logger.warning(
        "EMERGENCY_ROLLBACK_ACTIVATED: Circuit breaker locked OPEN. Force routing 100% Incumbent."
    )
    return {
        "message": "Rollback completed immediately. All traffic forced to Incumbent."
    }


@app.post("/predict", response_model=PredictionResponse)  # type: ignore[untyped-decorator]
def predict(request: PredictionRequest) -> PredictionResponse:
    start_time = time.perf_counter()
    payload = request.model_dump()

    if is_circuit_breaker_open or challenger_model is None:
        pred = calculate_incumbent_prediction(payload)
        latency = (time.perf_counter() - start_time) * 1000
        reason = (
            "Circuit breaker open / Rollback active"
            if is_circuit_breaker_open
            else "Challenger model unavailable"
        )
        log_routing_decision(payload, False, "incumbent_v1.4.2", pred, reason, latency)
        return PredictionResponse(
            predicted_minutes=pred,
            model_version="incumbent_v1.4.2",
            routed_to_challenger=False,
        )

    route_challenger = should_route_to_challenger(payload)

    if route_challenger:
        try:
            df = pd.DataFrame([payload])
            categorical_cols = [
                "package_type",
                "pickup_zone",
                "vehicle",
                "dropoff_zone",
                "home_zone",
                "market_zone_dropoff",
                "market_zone",
            ]
            for col in categorical_cols:
                df[col] = df[col].astype("category")

            pred = float(challenger_model.predict(df)[0])
            pred_rounded = round(pred, 2)
            latency = (time.perf_counter() - start_time) * 1000
            log_routing_decision(
                payload,
                True,
                "challenger_lgbm_v1",
                pred_rounded,
                "Matched conditional routing criteria",
                latency,
            )

            return PredictionResponse(
                predicted_minutes=pred_rounded,
                model_version="challenger_lgbm_v1",
                routed_to_challenger=True,
            )
        except Exception as e:  # noqa: BLE001
            pred = calculate_incumbent_prediction(payload)
            latency = (time.perf_counter() - start_time) * 1000
            log_routing_decision(
                payload,
                False,
                "incumbent_v1.4.2_fallback",
                pred,
                f"Inference exception: {e!s}",
                latency,
            )
            return PredictionResponse(
                predicted_minutes=pred,
                model_version="incumbent_v1.4.2_fallback",
                routed_to_challenger=False,
            )
    else:
        pred = calculate_incumbent_prediction(payload)
        latency = (time.perf_counter() - start_time) * 1000
        log_routing_decision(
            payload,
            False,
            "incumbent_v1.4.2",
            pred,
            "Did not satisfy conditional canary rules",
            latency,
        )
        return PredictionResponse(
            predicted_minutes=pred,
            model_version="incumbent_v1.4.2",
            routed_to_challenger=False,
        )


@app.post("/record_actual", status_code=status.HTTP_200_OK)  # type: ignore[untyped-decorator]
def record_actual(request: GroundTruthRequest) -> dict[str, str]:
    """
    Record ground truth after delivery completes.
    """
    log_ground_truth(
        request.delivery_id,
        request.actual_minutes,
        request.predicted_minutes,
        request.model_version,
    )
    return {"status": "recorded"}
