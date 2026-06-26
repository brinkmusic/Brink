from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok_envelope():
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"data": {"ok": True}}
