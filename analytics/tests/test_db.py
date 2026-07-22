# WHAT THIS FILE IS
# A smoke test proving the analytics package can actually reach the database.
# WHY: T30's whole job is "prove the Python pipeline can talk to Postgres" — this
# test is the acceptance criterion for that, and it should fail until db.py exists.

import os

import pytest
from sqlalchemy import text

from db import get_engine, normalize_url


def test_normalize_url_uses_psycopg_and_drops_pgbouncer_flag():
    raw = (
        "postgresql://user:pass@example.supabase.co:6543/postgres"
        "?pgbouncer=true&sslmode=require"
    )

    normalized = normalize_url(raw)

    assert normalized.startswith("postgresql+psycopg://")
    assert "pgbouncer=true" not in normalized
    assert "sslmode=require" in normalized


@pytest.mark.skipif(
    os.getenv("RUN_ANALYTICS_DB_TESTS") != "1",
    reason="live Supabase analytics DB check; set RUN_ANALYTICS_DB_TESTS=1 to run",
)
def test_can_read_track_count():
    # If the engine is wired up correctly, this query runs without raising and
    # returns a plain integer (0 or more) — we don't care about the exact count,
    # just that the connection + query round-trip works.
    with get_engine().connect() as conn:
        count = conn.execute(text('SELECT COUNT(*) FROM silver."Track"')).scalar()
    assert isinstance(count, int)
    assert count >= 0
