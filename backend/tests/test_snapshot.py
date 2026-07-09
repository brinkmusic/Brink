# WHAT THIS FILE IS
# Checks the scheduled snapshot (T21): the POST /api/snapshot endpoint (cron-authed by
# X-Cron-Secret) that, per Spotify-linked user, lands the raw recently-played payload into
# bronze and conforms it into silver Track/Play (deduped on userId+playedAt); plus the
# spotify.get_recently_played helper (429 backoff, no-token skip). The endpoint tests stub the
# helper and drive the real in-memory DB; the helper tests stub the Spotify HTTP call.

from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from sqlmodel import select

from app import spotify
from app.db import get_session
from app.main import app
from app.models import Play, SpotifyRecentlyPlayedRaw, SpotifyToken, Track, User
from app.routers import snapshot

CRON = "topsecret"


# The snapshot endpoint reads the expected secret from settings; stub it for every test here.
@pytest.fixture(autouse=True)
def _cron_secret(monkeypatch):
    monkeypatch.setattr(snapshot, "get_settings", lambda: SimpleNamespace(cron_secret=CRON))


def _linked_user(session, uid="u1"):
    session.add(User(id=uid, handle=uid, display_name=uid, created_at=datetime.now(timezone.utc)))
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
