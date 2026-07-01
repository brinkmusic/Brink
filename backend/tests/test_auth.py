# WHAT THIS FILE IS
# Checks the login gatekeeper (app/deps.py) and the capture-spotify endpoint. These
# run without a real database or a real Supabase by "faking" those pieces (see the
# MagicMock sessions and the monkeypatched Supabase lookup), so they're fast and safe.

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import deps
from app.db import get_session
from app.deps import AuthError, require_user
from app.main import app
from app.models import SpotifyToken, User


def _request(auth_header=None):
    # A stand-in for a real web request, carrying just the headers require_user reads.
    headers = {}
    if auth_header is not None:
        headers["authorization"] = auth_header
    return SimpleNamespace(headers=headers)


# --- require_user (unit tests, called directly) ---------------------------------

# No "Authorization: Bearer ..." header -> rejected with 401.
def test_missing_bearer_raises_401():
    with pytest.raises(AuthError) as exc:
        require_user(_request(None), session=MagicMock())
    assert exc.value.status == 401


# A token Supabase doesn't recognize -> rejected with 401.
def test_invalid_token_raises_401(monkeypatch):
    monkeypatch.setattr(deps.supabase, "get_user_from_token", lambda token: None)
    with pytest.raises(AuthError) as exc:
        require_user(_request("Bearer bad"), session=MagicMock())
    assert exc.value.status == 401


# First sign-in creates a User with the exact handle policy: slug + 6 chars of the id.
def test_first_signin_creates_user_with_handle_policy(monkeypatch):
    su = SimpleNamespace(
        id="abcdef12-3456-7890-abcd-ef1234567890",
        email="jane@example.com",
        # Spotify puts provider_id in user_metadata; the provider name in app_metadata.
        user_metadata={"full_name": "Jane Doe", "avatar_url": "http://img/a.png", "provider_id": "spot123"},
        app_metadata={"provider": "spotify"},
    )
    monkeypatch.setattr(deps.supabase, "get_user_from_token", lambda token: su)
    session = MagicMock()
    session.exec.return_value.first.return_value = None  # no existing user found

    user = require_user(_request("Bearer good"), session=session)

    assert user.handle == "jane-doe-abcdef"  # slug("Jane Doe") + first 6 of id (no hyphens)
    assert user.display_name == "Jane Doe"
    assert user.supabase_user_id == su.id
    assert user.email == "jane@example.com"
    assert user.avatar_url == "http://img/a.png"
    assert user.spotify_id == "spot123"
    session.add.assert_called_once()
    session.commit.assert_called_once()


# --- POST /api/auth/capture-spotify (endpoint tests, via a fake HTTP client) -----


@pytest.fixture(autouse=True)
def _clear_overrides():
    # Undo any dependency fakes after each test so they don't leak into other tests.
    yield
    app.dependency_overrides.clear()


def _fake_logged_in_user():
    return User(id="user-1", handle="h", display_name="d", created_at=datetime.now(timezone.utc))


# Missing a token -> 400 with the exact legacy message.
def test_capture_missing_tokens_returns_400():
    app.dependency_overrides[require_user] = _fake_logged_in_user
    app.dependency_overrides[get_session] = lambda: MagicMock()
    res = TestClient(app).post("/api/auth/capture-spotify", json={"access_token": "only-one"})
    assert res.status_code == 400
    assert res.json() == {"error": "missing spotify tokens"}


# Success -> stores an ENCRYPTED token row and returns { data: { captured: true } }.
def test_capture_success_upserts_encrypted_token(monkeypatch):
    from app.routers import auth as auth_router

    # Replace real encryption with a visible stand-in so we can assert it was applied.
    monkeypatch.setattr(auth_router, "encrypt", lambda s: f"enc({s})")
    session = MagicMock()
    session.get.return_value = None  # no existing token row -> create one

    app.dependency_overrides[require_user] = _fake_logged_in_user
    app.dependency_overrides[get_session] = lambda: session

    res = TestClient(app).post(
        "/api/auth/capture-spotify",
        json={"access_token": "AT", "refresh_token": "RT", "scopes": "user-read"},
    )

    assert res.status_code == 200
    assert res.json() == {"data": {"captured": True}}
    added = session.add.call_args[0][0]  # the SpotifyToken we saved
    assert isinstance(added, SpotifyToken)
    assert added.user_id == "user-1"
    assert added.access_token == "enc(AT)"    # stored encrypted, never in the clear
    assert added.refresh_token == "enc(RT)"
    assert added.scopes == "user-read"
    session.commit.assert_called_once()


# An unauthenticated request -> the AuthError handler returns our 401 { error } shape.
def test_capture_unauthenticated_returns_401_envelope():
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: MagicMock()
    res = TestClient(app).post(
        "/api/auth/capture-spotify", json={"access_token": "a", "refresh_token": "b"}
    )
    assert res.status_code == 401
    assert res.json() == {"error": "invalid session"}
