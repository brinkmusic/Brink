# WHAT THIS FILE IS
# A smoke test proving the analytics package can actually reach the database.
# WHY: T30's whole job is "prove the Python pipeline can talk to Postgres" — this
# test is the acceptance criterion for that, and it should fail until db.py exists.

from sqlalchemy import text

from db import get_engine


def test_can_read_track_count():
    # If the engine is wired up correctly, this query runs without raising and
    # returns a plain integer (0 or more) — we don't care about the exact count,
    # just that the connection + query round-trip works.
    with get_engine().connect() as conn:
        count = conn.execute(text('SELECT COUNT(*) FROM "Track"')).scalar()
    assert isinstance(count, int)
    assert count >= 0
