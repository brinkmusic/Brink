# WHAT THIS FILE IS
# Automated checks for the /api/health route. WHY: we want to confirm it reports
# success when the database is reachable AND reports an error when it isn't —
# without needing a real database during the test. To do that we "fake" the
# database check (see monkeypatch below).

from fastapi.testclient import TestClient

from app import db
from app.main import app

# A test client that can send fake requests to our app, no real server needed.
client = TestClient(app)


# Case 1: database is reachable.
def test_health_returns_ok_and_db_true(monkeypatch):
    # monkeypatch temporarily replaces the real db_ping with one that just returns
    # True, so this test doesn't touch a real database.
    monkeypatch.setattr(db, "db_ping", lambda: True)
    res = client.get("/api/health")
    assert res.status_code == 200  # 200 = OK
    assert res.json() == {"data": {"ok": True, "db": True}}


# Case 2: database is unreachable.
def test_health_returns_500_when_db_unreachable(monkeypatch):
    # Replace db_ping with one that raises an error, simulating a database outage.
    def boom() -> bool:
        raise RuntimeError("boom")

    monkeypatch.setattr(db, "db_ping", boom)
    res = client.get("/api/health")
    assert res.status_code == 500  # 500 = server error
    assert "error" in res.json()
