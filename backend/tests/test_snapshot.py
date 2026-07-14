# WHAT THIS FILE IS
# Checks the scheduled snapshot (T21): the POST /api/snapshot endpoint (cron-authed by
# X-Cron-Secret) that, per Spotify-linked user, lands the raw recently-played payload into
# bronze and conforms it into silver Track/Play (deduped on userId+playedAt); plus the
# spotify.get_recently_played helper (429 backoff, no-token skip). The endpoint tests stub the
# helper and drive the real in-memory DB; the helper tests stub the Spotify HTTP call.

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import event
from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine, select

from app import spotify
from app.db import get_session
from app.main import app
from app.models import Play, SpotifyRecentlyPlayedRaw, SpotifyToken, Track, User
from app.routers import snapshot

CRON = "topsecret"


@pytest.fixture
def fk_session():
    # Like the shared `db_session` fixture, but with SQLite FOREIGN KEY enforcement turned ON.
    # WHY a separate fixture: SQLite ignores foreign keys unless you ask (`PRAGMA foreign_keys=ON`),
    # so the default fixture can't catch a foreign-key *ordering* bug — which is exactly how the
    # T23 snapshot-500 slipped through (a `Play` inserted before the `Track` it references). Turning
    # the pragma on makes SQLite behave like Postgres here, so the regression test below actually
    # reproduces the production failure. (Broader gap — enabling this in the shared fixture — is
    # noted as a follow-up in the T23 ticket.)
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_conn, _record):
        dbapi_conn.execute("PRAGMA foreign_keys=ON")

    engine = engine.execution_options(
        schema_translate_map={"bronze": None, "silver": None, "gold": None}
    )
    SQLModel.metadata.create_all(engine, tables=[
        m.__table__ for m in (User, Track, Play, SpotifyToken, SpotifyRecentlyPlayedRaw)
    ])
    with Session(engine) as session:
        yield session


# The snapshot endpoint reads the expected secret from settings; stub it for every test here.
@pytest.fixture(autouse=True)
def _cron_secret(monkeypatch):
    monkeypatch.setattr(snapshot, "get_settings", lambda: SimpleNamespace(cron_secret=CRON))


def _linked_user(session, uid="u1"):
    # Commit the User first, THEN the token. WHY the two commits: SpotifyToken.userId is a foreign
    # key to User.id, so under foreign-key enforcement (the fk_session fixture) the User row must
    # already exist before the token can reference it. (The default db_session fixture doesn't
    # enforce FKs, so this also works there.) In production these are always separate transactions
    # anyway — the user signs up, then their Spotify token is captured on a later request.
    session.add(User(id=uid, handle=uid, display_name=uid, created_at=datetime.now(timezone.utc)))
    session.commit()
    session.add(SpotifyToken(
        user_id=uid, access_token="a", refresh_token="r",
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None), scopes="s",
    ))
    session.commit()


def _recently_played(track_id="t1", played_at="2026-07-08T20:00:00.000Z"):
    return {"items": [{
        "track": {"id": track_id, "name": "Song", "artists": [{"name": "A"}],
                  "album": {"images": [{"url": "http://img"}]}, "popularity": 40},
        "played_at": played_at,
    }]}


# --- POST /api/snapshot (auth) -----------------------------------------------------

def test_snapshot_missing_secret_returns_401(client, db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    assert client.post("/api/snapshot").status_code == 401


def test_snapshot_wrong_secret_returns_401(client, db_session):
    app.dependency_overrides[get_session] = lambda: db_session
    assert client.post("/api/snapshot", headers={"X-Cron-Secret": "nope"}).status_code == 401


# --- POST /api/snapshot (behavior) -------------------------------------------------

# A linked user's recently-played is landed to bronze and conformed to silver Track+Play; a
# second run with the same play does NOT duplicate it (dedup on userId+playedAt), but bronze
# appends each run (immutable landing).
def test_snapshot_lands_bronze_and_conforms_silver_with_dedup(client, db_session, monkeypatch):
    _linked_user(db_session, "u1")
    monkeypatch.setattr(snapshot, "get_recently_played", lambda session, user_id: _recently_played())
    app.dependency_overrides[get_session] = lambda: db_session

    res = client.post("/api/snapshot", headers={"X-Cron-Secret": CRON})
    assert res.status_code == 200
    plays = db_session.exec(select(Play)).all()
    assert len(plays) == 1 and plays[0].user_id == "u1"
    assert db_session.get(Track, "t1") is not None                          # track upserted (silver)
    assert len(db_session.exec(select(SpotifyRecentlyPlayedRaw)).all()) == 1  # raw landed (bronze)

    res2 = client.post("/api/snapshot", headers={"X-Cron-Secret": CRON})
    assert res2.status_code == 200
    assert len(db_session.exec(select(Play)).all()) == 1                    # dedup: still one play
    assert len(db_session.exec(select(SpotifyRecentlyPlayedRaw)).all()) == 2  # bronze appends


# Regression (T23): a batch with MULTIPLE new tracks must not hit a foreign-key violation. Each
# Play FK-references a Track, so the ingest has to persist each Track before the Play that points at
# it. With SQLite's foreign keys enforced (matching Postgres), the pre-fix code inserted a Play
# before its Track during a batched autoflush -> ForeignKeyViolation -> the snapshot returned 500.
def test_snapshot_multiple_new_tracks_no_fk_violation(client, fk_session, monkeypatch):
    _linked_user(fk_session, "u1")
    payload = {"items": [
        {"track": {"id": f"trk{i}", "name": f"S{i}", "artists": [{"name": "A"}],
                   "album": {"images": []}},
         "played_at": f"2026-07-08T2{i}:00:00.000Z"}
        for i in range(3)
    ]}
    monkeypatch.setattr(snapshot, "get_recently_played", lambda session, user_id: payload)
    app.dependency_overrides[get_session] = lambda: fk_session

    res = client.post("/api/snapshot", headers={"X-Cron-Secret": CRON})
    assert res.status_code == 200
    assert len(fk_session.exec(select(Play)).all()) == 3                      # all three plays landed
    assert all(fk_session.get(Track, f"trk{i}") is not None for i in range(3))  # tracks persisted first


# Only Spotify-linked users are processed; a user without a token is never fetched.
def test_snapshot_skips_unlinked_user(client, db_session, monkeypatch):
    db_session.add(User(id="u2", handle="u2", display_name="u2", created_at=datetime.now(timezone.utc)))
    db_session.commit()
    fetched = []
    monkeypatch.setattr(snapshot, "get_recently_played",
                        lambda session, user_id: fetched.append(user_id) or _recently_played())
    app.dependency_overrides[get_session] = lambda: db_session

    res = client.post("/api/snapshot", headers={"X-Cron-Secret": CRON})
    assert res.status_code == 200
    assert fetched == []                                   # unlinked user never fetched
    assert db_session.exec(select(Play)).all() == []


# --- spotify.get_recently_played (helper) ------------------------------------------

class _Resp:
    def __init__(self, status, body=None, headers=None):
        self.status_code = status
        self._body = body or {}
        self.headers = headers or {}
    def json(self):
        return self._body


# A 429 triggers one backoff + retry; a subsequent 200 returns the payload (no crash).
def test_get_recently_played_429_then_200(monkeypatch):
    monkeypatch.setattr(spotify, "get_valid_access_token", lambda s, u: "AT")
    monkeypatch.setattr(spotify, "_sleep", lambda seconds: None)  # don't actually wait
    seq = [_Resp(429, headers={"Retry-After": "1"}), _Resp(200, {"items": []})]
    calls = {"n": 0}
    def fake_get(url, headers=None, timeout=None):
        r = seq[calls["n"]]
        calls["n"] += 1
        return r
    monkeypatch.setattr(spotify.httpx, "get", fake_get)

    assert spotify.get_recently_played(None, "u1") == {"items": []}
    assert calls["n"] == 2  # retried once after the backoff


# A persistent 429 gives up gracefully -> None.
def test_get_recently_played_persistent_429_returns_none(monkeypatch):
    monkeypatch.setattr(spotify, "get_valid_access_token", lambda s, u: "AT")
    monkeypatch.setattr(spotify, "_sleep", lambda seconds: None)
    monkeypatch.setattr(spotify.httpx, "get",
                        lambda *a, **k: _Resp(429, headers={"Retry-After": "1"}))
    assert spotify.get_recently_played(None, "u1") is None


# No linked token -> None, no Spotify call.
def test_get_recently_played_no_token(monkeypatch):
    monkeypatch.setattr(spotify, "get_valid_access_token", lambda s, u: None)
    def boom(*a, **k):
        raise AssertionError("must not call Spotify without a token")
    monkeypatch.setattr(spotify.httpx, "get", boom)
    assert spotify.get_recently_played(None, "u1") is None
