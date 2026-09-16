import time
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from delivery_challenger.api.app import app


def test_health_check_healthy():
    with TestClient(app) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


def test_canary_routing_challenger(sample_challenger_payload):
    mock_model = MagicMock()
    mock_model.predict.return_value = [18.42]

    # Patch load_model so the startup lifespan uses our mock model cleanly
    with (
        patch("mlflow.pyfunc.load_model", return_value=mock_model),
        TestClient(app) as client,
    ):
        response = client.post("/predict", json=sample_challenger_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["routed_to_challenger"] is True
        assert data["model_version"] == "challenger_lgbm_v1"
        assert data["predicted_minutes"] == 18.42


def test_canary_routing_incumbent_fallback(sample_incumbent_payload):
    with TestClient(app) as client:
        response = client.post("/predict", json=sample_incumbent_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["routed_to_challenger"] is False
        assert data["model_version"] == "incumbent_v1.4.2"


def test_single_command_rollback_execution_time(sample_challenger_payload):
    mock_model = MagicMock()
    mock_model.predict.return_value = [18.42]

    with (
        patch("mlflow.pyfunc.load_model", return_value=mock_model),
        TestClient(app) as client,
    ):
        # 1. Verify normal routing before rollback
        res_before = client.post("/predict", json=sample_challenger_payload).json()
        assert res_before["routed_to_challenger"] is True

        # 2. Execute single rollback command & measure latency
        start_time = time.perf_counter()
        rollback_res = client.post("/rollback")
        execution_time_ms = (time.perf_counter() - start_time) * 1000

        assert rollback_res.status_code == 200
        assert execution_time_ms < 50.0  # Sub-50ms constraint

        # 3. Verify immediate traffic switch to Incumbent
        res_after = client.post("/predict", json=sample_challenger_payload).json()
        assert res_after["routed_to_challenger"] is False
        assert res_after["model_version"] == "incumbent_v1.4.2"

        # 4. Health endpoint degrades to 503
        health_res = client.get("/health")
        assert health_res.status_code == 503
        assert health_res.json()["status"] == "unhealthy"
