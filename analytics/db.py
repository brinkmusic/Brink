# WHAT THIS FILE IS
# The database connection helper for the analytics pipeline. It builds one
# SQLAlchemy "engine" (the object that knows how to reach Postgres) from the
# DATABASE_URL in the repo's root .env — the same Supabase database the FastAPI
# backend uses (ADR-0003: the pipeline reads/writes the one shared Postgres over
# the wire protocol; there is no separate analytics datastore).

import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from dotenv import load_dotenv
from sqlalchemy import Engine, create_engine

# This file lives at analytics/db.py, one folder below the repo root, so the
# root .env is one level up.
_ROOT_ENV = Path(__file__).resolve().parents[1] / ".env"
load_dotenv(_ROOT_ENV)


def normalize_url(url: str) -> str:
    # Same fix as backend/app/db.py: Supabase's URL is written for Prisma-style
    # tools, so we (1) name our Python driver explicitly and (2) drop the
    # "pgbouncer=true" hint, which our driver doesn't understand and rejects.
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    parts = urlsplit(url)
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "pgbouncer"]
    return urlunsplit(parts._replace(query=urlencode(kept)))


# Builds the engine once and reuses it (@lru_cache = build-once-then-reuse), the
# same pattern backend/app/db.py uses for its own engine.
@lru_cache
def get_engine() -> Engine:
    return create_engine(
        normalize_url(os.environ["DATABASE_URL"]),
        pool_pre_ping=True,
        # Turns off Postgres "prepared statements", which clash with the
        # connection pooler (pgbouncer) sitting in front of the database.
        connect_args={"prepare_threshold": None},
    )
