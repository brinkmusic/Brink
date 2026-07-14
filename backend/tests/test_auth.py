# WHAT THIS FILE IS
# Checks the login gatekeeper (app/deps.py) and the capture-spotify endpoint. The
# require_user unit tests call it directly with a fake (MagicMock) session; the endpoint
# tests use the shared `client` + `as_user` fixtures from conftest.py, which fake both
# the logged-in user and the database session so the tests are fast and network-free.

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app import deps
from app.db import get_session
from app.deps import AuthError, require_user
from app.main import app
from app.models import SpotifyToken, User
from app.security import session as login_session


def _request(auth_header=None, cookies=None):
    # A stand-in for a real web request, carrying the headers and cookies require_user reads.
    # `url` is needed only by the cookie-refresh path (to decide the Secure flag).
    headers = {}
    if auth_header is not None:
        headers["authorization"] = auth_header
    return SimpleNamespace(
        headers=headers,
        cookies=cookies or {},
        url=SimpleNamespace(scheme="https"),
    )


def _su(**overrides):
    # Build a fake Supabase user (what get_user_from_token returns). Defaults describe a
    # brand-new user with no metadata; pass overrides to exercise specific branches.
    base = dict(
        id="00000000-1111-2222-3333-444444444444",
        email=None,
        user_metadata={},
        app_metadata={},
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _new_user_session():
    # A fake DB session whose lookup finds no existing user, so require_user takes the
    # first-sign-in creation path.
    session = MagicMock()
    session.exec.return_value.first.return_value = None
    return session


# --- require_user (unit tests, called directly) ---------------------------------

# No "Authorization: Bearer ..." header -> rejected with 401.
def test_missing_bearer_raises_401():
    with pytest.raises(AuthError) as exc:
        require_user(_request(None), session=MagicMock())
    assert exc.value.status == 401


# A non-Bearer scheme ("Authorization: Token abc") is malformed -> 401, not a 500.
def test_non_bearer_authorization_header_raises_401():
    with pytest.raises(AuthError) as exc:
        require_user(_request("Token abc"), session=MagicMock())
    assert exc.value.status == 401


# A token Supabase doesn't recognize -> rejected with 401.
def test_invalid_token_raises_401(monkeypatch):
    monkeypatch.setattr(deps.supabase, "get_user_from_token", lambda token: None)
    with pytest.raises(AuthError) as exc:
        require_user(_request("Bearer bad"), session=MagicMock())
    assert exc.value.status == 401


# --- session-cookie auth for the server-rendered pages (T09) ---------------------

# No Bearer header AND no session cookie -> 401 (not a crash).
def test_no_bearer_and_no_cookie_raises_401():
    with pytest.raises(AuthError) as exc:
        require_user(_request(None), session=MagicMock())
    assert exc.value.status == 401


# A valid session cookie (fresh access token) authenticates the page request — no Bearer.
def test_valid_session_cookie_authenticates(monkeypatch):
    su = _su(id="abcdef12-3456-7890-abcd-ef1234567890")
    monkeypatch.setattr(login_session, "decode", lambda raw: {"access_token": "AT", "refresh_token": "RT"})
    monkeypatch.setattr(deps.supabase, "get_user_from_token", lambda token: su if token == "AT" else None)

    user = require_user(
        _request(None, cookies={login_session.SESSION_COOKIE: "x"}),
        session=_new_user_session(),
    )

    assert user.supabase_user_id == su.id


# An expired access token triggers a refresh, and the refreshed cookie is re-set.
def test_expired_session_cookie_is_refreshed(monkeypatch):
    su = _su(id="abcdef12-3456-7890-abcd-ef1234567890")
    monkeypatch.setattr(login_session, "decode", lambda raw: {"access_token": "OLD", "refresh_token": "RT"})
    monkeypatch.setattr(deps.supabase, "get_user_from_token", lambda token: None)  # OLD is expired
    new_session = SimpleNamespace(user=su, access_token="NEW", refresh_token="RT2", expires_at=1)
    monkeypatch.setattr(deps.supabase, "refresh_session", lambda rt: new_session if rt == "RT" else None)
    reset = {}
    monkeypatch.setattr(
        login_session, "set_cookie",
        lambda resp, access, refresh, expires_at, secure: reset.update(access=access, refresh=refresh),
    )

    user = require_user(
        _request(None, cookies={login_session.SESSION_COOKIE: "x"}),
        session=_new_user_session(),
        response=SimpleNamespace(),
    )

    assert user.supabase_user_id == su.id
    assert reset == {"access": "NEW", "refresh": "RT2"}  # cookie re-set with the fresh tokens


# A refresh that Supabase rejects -> 401 (the page will redirect to login).
def test_expired_cookie_failed_refresh_raises_401(monkeypatch):
    monkeypatch.setattr(login_session, "decode", lambda raw: {"access_token": "OLD", "refresh_token": "RT"})
    monkeypatch.setattr(deps.supabase, "get_user_from_token", lambda token: None)

    def boom(rt):
        raise RuntimeError("refresh token revoked")

    monkeypatch.setattr(deps.supabase, "refresh_session", boom)

    with pytest.raises(AuthError) as exc:
        require_user(
            _request(None, cookies={login_session.SESSION_COOKIE: "x"}),
            session=MagicMock(),
            response=SimpleNamespace(),
        )
    assert exc.value.status == 401


# First sign-in creates a User with the exact handle policy: slug + 6 chars of the id.
def test_first_signin_creates_user_with_handle_policy(monkeypatch):
    su = _su(
        id="abcdef12-3456-7890-abcd-ef1234567890",
        email="jane@example.com",
        # Spotify puts provider_id in user_metadata; the provider name in app_metadata.
        user_metadata={"full_name": "Jane Doe", "avatar_url": "http://img/a.png", "provider_id": "spot123"},
        app_metadata={"provider": "spotify"},
    )
    monkeypatch.setattr(deps.supabase, "get_user_from_token", lambda token: su)

    user = require_user(_request("Bearer good"), session=_new_user_session())

    assert user.handle == "jane-doe-abcdef"  # slug("Jane Doe") + first 6 of id (no hyphens)
    assert user.display_name == "Jane Doe"
    assert user.supabase_user_id == su.id
    assert user.email == "jane@example.com"
    assert user.avatar_url == "http://img/a.png"
    assert user.spotify_id == "spot123"


# --- display-name fallback chain (finding L4) ------------------------------------
# full_name -> name -> email prefix -> "Listener"; and an unslugifiable name -> "user".

# No full_name but a name -> use the name.
def test_display_name_falls_back_to_name(monkeypatch):
    su = _su(user_metadata={"name": "Only Name"})
    monkeypatch.setattr(deps.supabase, "get_user_from_token", lambda token: su)
    user = require_user(_request("Bearer x"), session=_new_user_session())
    assert user.display_name == "Only Name"


# No name at all but an email -> use the part before the "@".
def test_display_name_falls_back_to_email_prefix(monkeypatch):
    su = _su(email="alice@example.com")
    monkeypatch.setattr(deps.supabase, "get_user_from_token", lambda token: su)
    user = require_user(_request("Bearer x"), session=_new_user_session())
    assert user.display_name == "alice"


# No name and no email -> the constant fallback "Listener".
def test_display_name_falls_back_to_listener(monkeypatch):
    su = _su()
    monkeypatch.setattr(deps.supabase, "get_user_from_token", lambda token: su)
    user = require_user(_request("Bearer x"), session=_new_user_session())
    assert user.display_name == "Listener"


# A display name that slugifies to nothing (all punctuation) -> handle base "user".
def test_handle_uses_user_prefix_when_slug_empty(monkeypatch):
    su = _su(id="deadbeef-0000-1111-2222-333344445555", user_metadata={"full_name": "!!!"})
    monkeypatch.setattr(deps.supabase, "get_user_from_token", lambda token: su)
    user = require_user(_request("Bearer x"), session=_new_user_session())
    assert user.handle == "user-deadbe"  # "user" + first 6 of id (hyphens removed)


# --- require_user hardening (T71 findings H2, MB1) --------------------------------

# When two requests for the same brand-new user arrive simultaneously, the second
# INSERT hits the unique constraint. The fix: catch IntegrityError, rollback, and
# re-select the row the first request already created — no 500.
def test_concurrent_first_signin_race_is_handled(monkeypatch):
    from sqlalchemy.exc import IntegrityError

    su = _su(id="race-aabbcc", email="race@example.com")
    monkeypatch.setattr(deps.supabase, "get_user_from_token", lambda token: su)

    # The user that the "winner" request already created.
    existing = User(id="u-winner", handle="listener-raceaa", display_name="Listener",
                    created_at=datetime.now(timezone.utc))

    session = MagicMock()
    call_count = 0

    def exec_side_effect(stmt):
        nonlocal call_count
        result = MagicMock()
        # First select: user not found yet (both requests miss simultaneously).
        # Second select (after rollback): winner's row is now present.
        result.first.return_value = None if call_count == 0 else existing
        call_count += 1
        return result

    session.exec.side_effect = exec_side_effect
    # Simulate the loser's INSERT hitting the unique constraint.
    session.commit.side_effect = IntegrityError("stmt", {}, Exception("dup key"))

    user = require_user(_request("Bearer loser"), session=session)

    assert user is existing
    session.rollback.assert_called_once()


# When the Supabase client raises (e.g. network error, expired token), require_user
# should return 401 — same as returning None, but testing the exception code path.
def test_token_verification_exception_raises_401(monkeypatch):
    def raise_network_error(token):
        raise Exception("connection refused")
    monkeypatch.setattr(deps.supabase, "get_user_from_token", raise_network_error)
    with pytest.raises(AuthError) as exc:
        require_user(_request("Bearer x"), session=MagicMock())
    assert exc.value.status == 401


# When admin() raises ValueError (missing SUPABASE_URL/KEY), that is a server
# misconfiguration — it must NOT be swallowed into a silent 401. It should propagate
# so Render logs show the real problem (finding MB1).
def test_misconfiguration_propagates_not_401(monkeypatch):
    def raise_config_error(token):
        raise ValueError("SUPABASE_URL not set")
    monkeypatch.setattr(deps.supabase, "get_user_from_token", raise_config_error)
    with pytest.raises(ValueError):
        require_user(_request("Bearer any"), session=MagicMock())


# --- POST /api/auth/capture-spotify (endpoint tests, via the shared fixtures) -----


def _fake_logged_in_user():
    return User(id="user-1", handle="h", display_name="d", created_at=datetime.now(timezone.utc))


# Missing a token -> 400 with the exact legacy message.
def test_capture_missing_tokens_returns_400(client, as_user):
    as_user(_fake_logged_in_user())
    res = client.post("/api/auth/capture-spotify", json={"access_token": "only-one"})
    assert res.status_code == 400
    assert res.json() == {"error": "missing spotify tokens"}


# Success (no existing row) -> CREATE: adds an ENCRYPTED token row, returns captured:true.
def test_capture_success_upserts_encrypted_token(client, as_user, monkeypatch):
    from app.routers import auth as auth_router

    # Replace real encryption with a visible stand-in so we can assert it was applied.
    monkeypatch.setattr(auth_router, "encrypt", lambda s: f"enc({s})")
    session = MagicMock()
    session.get.return_value = None  # no existing token row -> create one
    as_user(_fake_logged_in_user(), session=session)

    res = client.post(
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


# Success (row already exists) -> UPDATE: overwrites fields in place, does NOT re-add.
# This is the path every login after the first takes (finding MB5). It also pins the
# expiry format: naive UTC (no tzinfo), ~1 hour ahead, matching legacy rows.
def test_capture_update_branch_overwrites_without_add(client, as_user, monkeypatch):
    from app.routers import auth as auth_router

    monkeypatch.setattr(auth_router, "encrypt", lambda s: f"enc({s})")
    existing = SpotifyToken(user_id="user-1", access_token="old", refresh_token="old", scopes="old")
    session = MagicMock()
    session.get.return_value = existing  # row already exists -> update path
    as_user(_fake_logged_in_user(), session=session)

    res = client.post(
        "/api/auth/capture-spotify",
        json={"access_token": "AT", "refresh_token": "RT", "scopes": "new-scope"},
    )

    assert res.status_code == 200
    session.add.assert_not_called()          # updated in place, not re-added
    session.commit.assert_called_once()
    assert existing.access_token == "enc(AT)"
    assert existing.refresh_token == "enc(RT)"
    assert existing.scopes == "new-scope"
    # Expiry stored naive (no timezone) and about an hour ahead — legacy-row parity.
    assert existing.expires_at.tzinfo is None
    now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
    delta = existing.expires_at - now_naive
    assert timedelta(minutes=55) < delta < timedelta(minutes=65)


# An unauthenticated request -> the AuthError handler returns our 401 { error } shape.
def test_capture_unauthenticated_returns_401_envelope(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: MagicMock()
    res = client.post(
        "/api/auth/capture-spotify", json={"access_token": "a", "refresh_token": "b"}
    )
    assert res.status_code == 401
    assert res.json() == {"error": "invalid session"}
