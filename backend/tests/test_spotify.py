# WHAT THIS FILE IS
# Checks the server-side Spotify token helper (app/spotify.py): get_valid_access_token returns a
# usable access token for a user — the stored one while it's fresh, a refreshed one once it expires
# — and degrades to None (never raises) for an unlinked user or a failed refresh (T22). Correctness
# depends on real DB reads/writes (the token row is re-persisted after a refresh), so these use the
# real in-memory `db_session` fixture. Crypto is stubbed to the identity function so a test doesn't
# need a real TOKEN_ENC_KEY and can read the stored values directly; the network call is stubbed so
# no test hits Spotify.

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app import spotify
from app.models import SpotifyToken, User


def _naive_now():
    # Match how tokens are stored: naive UTC (see routers/auth.py).
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _seed_token(session, user_id="u1", access="AT", refresh="RT", expires_in_seconds=3600):
    session.add(User(id=user_id, handle=user_id, display_name=user_id,
                     created_at=datetime.now(timezone.utc)))
    session.add(SpotifyToken(
        user_id=user_id, access_token=access, refresh_token=refresh,
        expires_at=_naive_now() + timedelta(seconds=expires_in_seconds), scopes="s",
    ))
    session.commit()


# Stub encrypt/decrypt to identity for every test here, so stored values are readable as-is and no
# real key is needed. (The real crypto is exercised in test_auth.py / by security/crypto.py itself.)
@pytest.fixture(autouse=True)
def _identity_crypto(monkeypatch):
    monkeypatch.setattr(spotify, "decrypt", lambda blob: blob)
    monkeypatch.setattr(spotify, "encrypt", lambda text: text)


# --- get_valid_access_token --------------------------------------------------------

# A user with no linked Spotify (no SpotifyToken row) -> None, and no refresh attempt.
def test_no_token_returns_none(db_session, monkeypatch):
    def boom(*a, **k):
        raise AssertionError("must not attempt a refresh when there is no token")
    monkeypatch.setattr(spotify, "_request_refreshed_token", boom)
    assert spotify.get_valid_access_token(db_session, "ghost") is None


# A still-valid token is returned as-is, with no network refresh.
def test_valid_token_returned_without_refresh(db_session, monkeypatch):
    _seed_token(db_session, access="AT", expires_in_seconds=3600)
    def boom(*a, **k):
        raise AssertionError("must not refresh a still-valid token")
    monkeypatch.setattr(spotify, "_request_refreshed_token", boom)
    assert spotify.get_valid_access_token(db_session, "u1") == "AT"


# An expired token is refreshed; the new token + bumped expiry are persisted, and the new token
# is returned. The refresh is called with the (decrypted) stored refresh token.
def test_expired_token_is_refreshed_and_persisted(db_session, monkeypatch):
    _seed_token(db_session, access="OLD", refresh="RT", expires_in_seconds=-10)
    seen = {}
    def fake_refresh(refresh_token):
        seen["rt"] = refresh_token
        return {"access_token": "NEW", "expires_in": 3600}
    monkeypatch.setattr(spotify, "_request_refreshed_token", fake_refresh)

    assert spotify.get_valid_access_token(db_session, "u1") == "NEW"
    assert seen["rt"] == "RT"  # the stored refresh token, decrypted
    row = db_session.get(SpotifyToken, "u1")
    assert row.access_token == "NEW"          # re-stored (identity-encrypted here)
    assert row.expires_at > _naive_now()      # expiry moved into the future


# If Spotify rotates the refresh token, the new one is stored.
def test_rotated_refresh_token_is_stored(db_session, monkeypatch):
    _seed_token(db_session, refresh="OLDRT", expires_in_seconds=-10)
    monkeypatch.setattr(spotify, "_request_refreshed_token",
                        lambda rt: {"access_token": "NEW", "expires_in": 3600, "refresh_token": "NEWRT"})
    spotify.get_valid_access_token(db_session, "u1")
    assert db_session.get(SpotifyToken, "u1").refresh_token == "NEWRT"


# A failed refresh (helper returns None) degrades to None — the caller shows an empty state, no 500.
def test_refresh_failure_returns_none(db_session, monkeypatch):
    _seed_token(db_session, expires_in_seconds=-10)
    monkeypatch.setattr(spotify, "_request_refreshed_token", lambda rt: None)
    assert spotify.get_valid_access_token(db_session, "u1") is None


# --- _request_refreshed_token (the Spotify token-endpoint call) --------------------

# A 200 from Spotify returns the parsed JSON; the request uses the refresh_token grant + client auth.
def test_request_refreshed_token_success(monkeypatch):
    captured = {}
    class FakeResp:
        status_code = 200
        def json(self):
            return {"access_token": "X", "expires_in": 3600}
    def fake_post(url, data=None, auth=None, timeout=None):
        captured.update(url=url, data=data, auth=auth)
        return FakeResp()
    monkeypatch.setattr(spotify.httpx, "post", fake_post)
    monkeypatch.setattr(spotify, "get_settings",
                        lambda: SimpleNamespace(spotify_client_id="cid", spotify_client_secret="sec"))

    out = spotify._request_refreshed_token("RT")
    assert out == {"access_token": "X", "expires_in": 3600}
    assert captured["url"] == spotify.SPOTIFY_TOKEN_URL
    assert captured["data"]["grant_type"] == "refresh_token"
    assert captured["data"]["refresh_token"] == "RT"
    assert captured["auth"] == ("cid", "sec")


# A non-200 from Spotify -> None (no crash).
def test_request_refreshed_token_non_200_returns_none(monkeypatch):
    class FakeResp:
        status_code = 400
        def json(self):
            return {}
    monkeypatch.setattr(spotify.httpx, "post", lambda *a, **k: FakeResp())
    monkeypatch.setattr(spotify, "get_settings",
                        lambda: SimpleNamespace(spotify_client_id="cid", spotify_client_secret="sec"))
    assert spotify._request_refreshed_token("RT") is None


# Missing client credentials -> None (treated as "cannot refresh", not a crash).
def test_request_refreshed_token_missing_creds_returns_none(monkeypatch):
    monkeypatch.setattr(spotify, "get_settings",
                        lambda: SimpleNamespace(spotify_client_id=None, spotify_client_secret=None))
    assert spotify._request_refreshed_token("RT") is None
