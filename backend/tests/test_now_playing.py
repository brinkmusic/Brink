# WHAT THIS FILE IS
# Checks the now-playing feature (T20): the spotify.get_currently_playing helper (normalizes
# Spotify's "currently playing" response, degrades to None on 204 / errors / unlinked user) and the
# GET /api/me/now-playing endpoint (login-gated; returns the normalized track or {data: null}, never
# a 500). The endpoint tests stub the helper; the helper tests stub the Spotify HTTP call + the T22
# token helper, so no test hits Spotify.

import pytest

from app import spotify
from app.db import get_session
from app.deps import AuthError, require_user
from app.main import app
from app.routers import now_playing


# A realistic Spotify "currently playing" payload (a track is playing).
def _spotify_playing_payload():
    return {
        "is_playing": True,
        "item": {
            "id": "track123",
            "name": "Song",
            "artists": [{"name": "Artist A"}, {"name": "Artist B"}],
            "album": {"images": [{"url": "http://img/large"}, {"url": "http://img/med"}]},
            "popularity": 55,
        },
    }


# --- GET /api/me/now-playing (router) ----------------------------------------------

# No login session -> the AuthError handler returns our 401 { error } envelope.
def test_now_playing_unauthenticated_returns_401(client):
    def raise_auth_error():
        raise AuthError("invalid session")
    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.get("/api/me/now-playing")
    assert res.status_code == 401


# A playing track -> 200 with the normalized track in camelCase.
def test_now_playing_returns_track(client, as_user, monkeypatch):
    as_user(_user_stub())
    monkeypatch.setattr(now_playing, "get_currently_playing", lambda session, user_id: {
        "is_playing": True,
        "track": {"spotify_id": "track123", "title": "Song", "artist_name": "Artist A, Artist B",
                  "album_art_url": "http://img/large", "popularity": 55},
    })
    res = client.get("/api/me/now-playing")
    assert res.status_code == 200
    assert res.json()["data"] == {
        "isPlaying": True,
        "track": {"spotifyId": "track123", "title": "Song", "artistName": "Artist A, Artist B",
                  "albumArtUrl": "http://img/large", "popularity": 55},
    }


# Nothing playing / unlinked / error (helper returns None) -> 200 with { data: null }, not an error.
def test_now_playing_empty_state_is_null(client, as_user, monkeypatch):
    as_user(_user_stub())
    monkeypatch.setattr(now_playing, "get_currently_playing", lambda session, user_id: None)
    res = client.get("/api/me/now-playing")
    assert res.status_code == 200
    assert res.json() == {"data": None}


# --- spotify.get_currently_playing (helper) ----------------------------------------

# A user with no valid token (unlinked / refresh failed) -> None, no Spotify call.
def test_get_currently_playing_no_token(monkeypatch):
    monkeypatch.setattr(spotify, "get_valid_access_token", lambda session, user_id: None)
    def boom(*a, **k):
        raise AssertionError("must not call Spotify without a token")
    monkeypatch.setattr(spotify.httpx, "get", boom)
    assert spotify.get_currently_playing(None, "u1") is None


# A 200 with a track is normalized to our small shape (multiple artists joined, first album image).
def test_get_currently_playing_normalizes_200(monkeypatch):
    monkeypatch.setattr(spotify, "get_valid_access_token", lambda session, user_id: "AT")
    class FakeResp:
        status_code = 200
        def json(self):
            return _spotify_playing_payload()
    captured = {}
    def fake_get(url, headers=None, timeout=None):
        captured["url"] = url; captured["headers"] = headers
        return FakeResp()
    monkeypatch.setattr(spotify.httpx, "get", fake_get)

    out = spotify.get_currently_playing(None, "u1")
    assert out == {
        "is_playing": True,
        "track": {"spotify_id": "track123", "title": "Song", "artist_name": "Artist A, Artist B",
                  "album_art_url": "http://img/large", "popularity": 55},
    }
    assert captured["headers"]["Authorization"] == "Bearer AT"


# 204 (nothing playing) -> None.
def test_get_currently_playing_204(monkeypatch):
    monkeypatch.setattr(spotify, "get_valid_access_token", lambda session, user_id: "AT")
    class FakeResp:
        status_code = 204
        def json(self):
            return {}
    monkeypatch.setattr(spotify.httpx, "get", lambda *a, **k: FakeResp())
    assert spotify.get_currently_playing(None, "u1") is None


# A 200 whose item is null (e.g. an ad or podcast) -> None.
def test_get_currently_playing_null_item(monkeypatch):
    monkeypatch.setattr(spotify, "get_valid_access_token", lambda session, user_id: "AT")
    class FakeResp:
        status_code = 200
        def json(self):
            return {"is_playing": True, "item": None}
    monkeypatch.setattr(spotify.httpx, "get", lambda *a, **k: FakeResp())
    assert spotify.get_currently_playing(None, "u1") is None


# A non-200/204 (e.g. Spotify hiccup) -> None (graceful, no crash).
def test_get_currently_playing_error_status(monkeypatch):
    monkeypatch.setattr(spotify, "get_valid_access_token", lambda session, user_id: "AT")
    class FakeResp:
        status_code = 503
        def json(self):
            return {}
    monkeypatch.setattr(spotify.httpx, "get", lambda *a, **k: FakeResp())
    assert spotify.get_currently_playing(None, "u1") is None


# Minimal fake logged-in user for the endpoint tests.
def _user_stub():
    from datetime import datetime, timezone
    from app.models import User
    return User(id="u1", handle="h", display_name="d", created_at=datetime.now(timezone.utc))
