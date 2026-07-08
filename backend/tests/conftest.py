# WHAT THIS FILE IS
# Shared pytest fixtures for the backend test suite. WHY: almost every endpoint test
# needs the same two things — a fake HTTP client, and a way to pretend "a specific user
# is logged in" while using a stand-in database — without a real Supabase or Postgres.
# Before this file that boilerplate was hand-copied into each test in two different
# styles; centralizing it keeps tests short, consistent, and leak-free (see the
# autouse teardown that always clears dependency overrides).
#
# NOTE FOR T10+ AUTHORS: as_user() overrides the auth + session dependencies with fakes,
# and the default session is a MagicMock. A mock is fine for endpoints whose correctness
# does not depend on real database behavior. But it CANNOT verify upsert-style logic that
# relies on a DB-enforced invariant (e.g. the reaction unique constraint) — a MagicMock
# happily "succeeds" on a duplicate insert, hiding the bug. For those endpoints, build a
# real in-memory SQLite session (SQLModel supports it) instead of the mock. The missed
# token-upsert update branch (now covered in test_auth.py) is exactly the kind of gap a
# mock session hides.

from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

from app.db import get_session
from app.deps import require_user
from app.main import app
from app.models import Comment, Post, RateLimitHit, Reaction, Track, User


@pytest.fixture
def db_session():
    # A real, throwaway SQLite database held in memory — used by tests whose correctness
    # depends on actual database behavior (upserts, ordering, rate-limit counting) that a
    # MagicMock can't fake (see the NOTE FOR T10+ above). We create ONLY the tables these
    # tests touch: the analytics tables use Postgres-only JSONB columns that SQLite can't
    # build, and we don't need them here.
    # StaticPool keeps ONE shared connection for this in-memory database. WHY: an in-memory
    # SQLite gives each connection its own private DB, and the endpoint under test runs in a
    # different thread than this fixture — without StaticPool the endpoint would open a second
    # connection and see an empty database ("no such table").
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    tables = [m.__table__ for m in (User, Track, Post, Reaction, Comment, RateLimitHit)]
    SQLModel.metadata.create_all(engine, tables=tables)
    with Session(engine) as session:
        yield session


@pytest.fixture
def client():
    # A fake HTTP client for the app — no real server or network. raise_server_exceptions
    # is False so responses built by our exception handlers come back as normal responses
    # (which is what tests assert on) instead of being re-raised out of the client.
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture(autouse=True)
def _clear_overrides():
    # Any test that swaps in a fake dependency must not let it leak into the next test.
    # autouse=True means this runs for EVERY test automatically, clearing after each one.
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def as_user():
    # Returns a helper. Call `as_user(user)` (optionally `as_user(user, session=...)`)
    # inside a test to make the app treat `user` as the logged-in caller and use `session`
    # for database access. If no session is given, a fresh MagicMock is created and
    # returned so the test can assert on it (e.g. session.commit.assert_called_once()).
    def _install(user, session=None):
        if session is None:
            session = MagicMock()
        app.dependency_overrides[require_user] = lambda: user
        app.dependency_overrides[get_session] = lambda: session
        return session

    return _install
