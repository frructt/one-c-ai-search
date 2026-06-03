from fastapi.testclient import TestClient

from api.app import app


def test_health_endpoint_starts_without_external_services():
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
