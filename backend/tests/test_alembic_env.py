# WHAT THIS FILE IS
# Checks the database-address handling our Alembic migrations depend on. Alembic's env.py
# can't be imported in a test (it runs migrations at import time), so the override check
# asserts on its SOURCE — the same technique the page tests use for browser scripts.

from pathlib import Path

from app.db import normalize_url

_ENV_PY = Path(__file__).resolve().parent.parent / "alembic" / "env.py"


# A pasted dashboard address says "postgresql://", which SQLAlchemy routes to the psycopg2
# driver by default. We install psycopg (version 3), so normalize_url must rewrite the
# scheme to name it explicitly.
def test_normalize_url_rewrites_scheme_for_our_driver():
    out = normalize_url("postgresql://user:pass@db.example:5432/postgres")
    assert out.startswith("postgresql+psycopg://")


# Regression for the T96 production-migration attempt (T98): a raw URL passed via
# `alembic -x dburl=...` skipped normalize_url entirely, so the command crashed with
# "No module named psycopg2". The override path must go through the same normalization
# as the settings path.
def test_alembic_dburl_override_is_normalized():
    source = _ENV_PY.read_text(encoding="utf-8")
    assert "normalize_url(override)" in source
