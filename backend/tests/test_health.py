# WHAT THIS FILE IS
# Automated checks for the /api/health route. WHY: we want to confirm it reports
# success when the database is reachable AND reports an error when it isn't —
# without needing a real database during the test. To do that we "fake" the
# database check (see monkeypatch below).

from app import db

# The `client` fixture (a fake HTTP client) comes from conftest.py.


# Case 1: database is reachable.
def test_health_returns_ok_and_db_true(client, monkeypatch):
    # monkeypatch temporarily replaces the real db_ping with one that just returns
    # True, so this test doesn't touch a real database.
    monkeypatch.setattr(db, "db_ping", lambda: True)
    res = client.get("/api/health")
    assert res.status_code == 200  # 200 = OK
    assert res.json() == {"data": {"ok": True, "db": True}}


# Case 2: database is unreachable.
def test_health_returns_500_when_db_unreachable(client, monkeypatch):
    # Replace db_ping with one that raises an error, simulating a database outage.
    def boom() -> bool:
        raise RuntimeError("boom")

    monkeypatch.setattr(db, "db_ping", boom)
    res = client.get("/api/health")
    assert res.status_code == 500  # 500 = server error
    # Exact constant message — no raw driver details leaked (finding MB4).
    assert res.json() == {"error": "db unreachable"}
