# WHAT THIS FILE IS
# The database "connection" layer. It builds the single object (the "engine") that
# knows how to reach our database, and hands out short-lived "sessions" that other
# code uses to run queries. WHY keep it in one file: everything talks to the
# database the same way, and the tricky connection setup lives in exactly one place.

from functools import lru_cache
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy import Engine, text
from sqlmodel import Session, create_engine

from app.config import get_settings


def normalize_url(url: str) -> str:
    # The database address Supabase gives us is written for the old Prisma tool, so
    # we tweak it for our Python driver:
    #  1. tell it to use "psycopg" (our Python-to-Postgres driver).
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://") :]
    #  2. remove the "pgbouncer=true" flag, which is a Prisma-only hint our driver
    #     doesn't understand. We rebuild the address from its parts and drop just
    #     that one setting, so any OTHER settings stay intact and correctly joined
    #     (a plain text delete could leave a broken "&" behind if it weren't last).
    parts = urlsplit(url)
    kept = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != "pgbouncer"]
    return urlunsplit(parts._replace(query=urlencode(kept)))


# Builds the database engine once and reuses it (@lru_cache = build-once-then-reuse).
# The engine is the app's shared "phone line" to the database.
@lru_cache
def get_engine() -> Engine:
    return create_engine(
        normalize_url(get_settings().database_url),
        # pool_pre_ping: quietly check a connection is still alive before using it,
        # so a dropped connection doesn't cause a random error.
        pool_pre_ping=True,
        # prepare_threshold=None: turn OFF a Postgres optimization ("prepared
        # statements"). WHY: it clashes with the connection pooler (pgbouncer) that
        # sits in front of our database and causes intermittent errors.
        connect_args={"prepare_threshold": None},
    )


# Hands out a database session (a temporary workspace for reading/writing data) and
# automatically closes it when the caller is done. FastAPI endpoints will use this.
def get_session():
    with Session(get_engine()) as session:
        yield session


# A tiny health check: ask the database to compute "SELECT 1" and confirm it answers
# with 1. If this works, the database is reachable. Used by the /api/health endpoint.
def db_ping() -> bool:
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT 1")).scalar() == 1
