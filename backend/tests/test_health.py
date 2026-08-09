from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok():
    """Health endpoint should return status ok and database connected."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"


def test_root_endpoint():
    """Root endpoint should return the welcome message."""
    response = client.get("/")
    assert response.status_code == 200
    assert "VoyageAI" in response.json()["message"]
