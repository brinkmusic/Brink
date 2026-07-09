# WHAT THIS FILE IS
# Tests for the server-side Spotify login flow (T09): the /auth/login start route
# (and later /auth/callback + /auth/logout). These replace the old browser-driven
# OAuth removed with the SPA. We never touch real Spotify or Supabase — the OAuth
# wrappers in app.security.supabase are faked, so the tests exercise OUR logic
# (the redirect, the CSRF state, the encrypted handshake cookie) deterministically.
#
# Encryption is replaced with a visible stand-in `enc(...)` the same way test_auth.py
# does it, so a test can read the cookie payload back AND still prove the cookie is
# encrypted at rest — without needing a real TOKEN_ENC_KEY (so CI stays green).

import base64
import json
from types import SimpleNamespace
from unittest.mock import MagicMock

from sqlmodel import select

from app.db import get_session
from app.main import app
from app.models import SpotifyToken, User
from app.routers import auth as auth_router
from app.security import session as login_session
from app.security import supabase


# A stand-in for encrypt(): an opaque, cookie-safe transform (urlsafe base64, no padding)
# we can reverse in the test. WHY not identity: it lets us assert the cookie is NOT stored
# in the clear while still reading the payload back, without needing a real TOKEN_ENC_KEY.
def _enc(s: str) -> str:
    return base64.urlsafe_b64encode(s.encode()).decode().rstrip("=")


def _dec(s: str) -> str:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4)).decode()

# The exact scopes the old React SPA requested (AuthContext.tsx). T09 must preserve
# them so the server-side login grants the same Spotify access the snapshot (T21) and
# now-playing (T20) features already rely on.
EXPECTED_SCOPES = (
    "user-read-email user-read-recently-played user-top-read user-read-currently-playing"
)


def test_login_redirects_to_spotify_and_sets_handshake_cookie(client, monkeypatch):
    fake_url = "https://proj.supabase.co/auth/v1/authorize?provider=spotify&code_challenge=abc"
    # Stand in for the real SDK call: return a fixed authorize URL + PKCE verifier.
    monkeypatch.setattr(
        supabase, "oauth_authorize", lambda redirect_to, scopes: (fake_url, "verifier-xyz")
    )
    monkeypatch.setattr(auth_router, "encrypt", _enc)

    resp = client.get("/auth/login", follow_redirects=False)

    assert resp.status_code == 307
    assert resp.headers["location"] == fake_url
    raw = resp.cookies.get("brink_oauth")
    assert raw
    assert "verifier-xyz" not in raw  # handshake cookie is not stored in the clear
    payload = json.loads(_dec(raw))
    assert payload["verifier"] == "verifier-xyz"  # PKCE verifier stashed for the callback
    assert payload["state"]  # a CSRF state token was generated


def test_login_requests_spotify_scopes_and_callback_redirect(client, monkeypatch):
    captured = {}

    def fake(redirect_to, scopes):
        captured["redirect_to"] = redirect_to
        captured["scopes"] = scopes
        return ("https://x/authorize?provider=spotify", "v")

    monkeypatch.setattr(supabase, "oauth_authorize", fake)
    monkeypatch.setattr(auth_router, "encrypt", lambda s: s)

    client.get("/auth/login", follow_redirects=False)

    # The callback URL is derived from the request origin (adapts to local vs prod) and
    # carries the CSRF state as a query param — Supabase preserves it and echoes it back
    # to the callback so we can verify it there.
    assert "/auth/callback?state=" in captured["redirect_to"]
    assert captured["scopes"] == EXPECTED_SCOPES


# --- /auth/callback (slice 2) ----------------------------------------------------


def _su(**overrides):
    base = dict(
        id="abcdef12-3456-7890-abcd-ef1234567890",
        email="jane@example.com",
        user_metadata={"full_name": "Jane Doe", "provider_id": "spot1"},
        app_metadata={"provider": "spotify"},
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _fake_session(**overrides):
    # Stand-in for the supabase_auth Session returned by exchange_code: it carries the
    # Supabase session tokens AND the Spotify provider tokens.
    base = dict(
        user=_su(),
        access_token="sb-at",
        refresh_token="sb-rt",
        expires_at=9999999999,
        provider_token="sp-at",
        provider_refresh_token="sp-rt",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _handshake(state="S", verifier="V"):
    return _enc(json.dumps({"state": state, "verifier": verifier}))


def test_callback_happy_path_provisions_user_stores_token_sets_session(
    client, db_session, monkeypatch
):
    monkeypatch.setattr(auth_router, "encrypt", _enc)  # Spotify-token store (in auth.py)
    monkeypatch.setattr(auth_router, "decrypt", _dec)  # handshake cookie read (in auth.py)
    monkeypatch.setattr(login_session, "encrypt", _enc)  # brink_session cookie write
    captured = {}

    def fake_exchange(auth_code, code_verifier):
        captured["code"], captured["verifier"] = auth_code, code_verifier
        return _fake_session()

    monkeypatch.setattr(supabase, "exchange_code", fake_exchange)
    app.dependency_overrides[get_session] = lambda: db_session

    client.cookies.set("brink_oauth", _handshake(state="S", verifier="V"))
    resp = client.get("/auth/callback?state=S&code=THECODE", follow_redirects=False)

    # Redirected into the app, having consumed the exact code + verifier.
    assert resp.status_code == 303
    assert resp.headers["location"] == "/feed"
    assert captured == {"code": "THECODE", "verifier": "V"}

    # Session cookie set, encrypted, holding the Supabase session tokens.
    sess = resp.cookies.get("brink_session")
    assert sess and "sb-rt" not in sess
    payload = json.loads(_dec(sess))
    assert payload["access_token"] == "sb-at"
    assert payload["refresh_token"] == "sb-rt"

    # User provisioned from the Supabase identity (reusing the T02 handle policy).
    user = db_session.exec(select(User)).first()
    assert user and user.spotify_id == "spot1"

    # Spotify provider tokens stored ENCRYPTED (never in the clear).
    tok = db_session.get(SpotifyToken, user.id)
    assert tok is not None
    assert "sp-at" not in tok.access_token and "sp-rt" not in tok.refresh_token
    assert _dec(tok.access_token) == "sp-at" and _dec(tok.refresh_token) == "sp-rt"


def test_callback_rejects_state_mismatch(client, monkeypatch):
    monkeypatch.setattr(auth_router, "decrypt", _dec)
    called = {"exchange": False}
    monkeypatch.setattr(
        supabase, "exchange_code", lambda *a: called.__setitem__("exchange", True)
    )
    app.dependency_overrides[get_session] = lambda: MagicMock()

    client.cookies.set("brink_oauth", _handshake(state="GOOD", verifier="V"))
    resp = client.get("/auth/callback?state=BAD&code=X", follow_redirects=False)

    assert resp.status_code == 400  # CSRF guard: query state != cookie state
    assert called["exchange"] is False  # never attempted the code exchange


def test_callback_spotify_error_renders_friendly_page_not_500(client, monkeypatch):
    monkeypatch.setattr(
        supabase, "exchange_code", lambda *a: (_ for _ in ()).throw(AssertionError("no exchange"))
    )
    app.dependency_overrides[get_session] = lambda: MagicMock()

    resp = client.get(
        "/auth/callback?error=access_denied&error_description=denied", follow_redirects=False
    )

    assert resp.status_code == 400
    assert "text/html" in resp.headers["content-type"]


def test_callback_missing_handshake_cookie_is_rejected(client, monkeypatch):
    app.dependency_overrides[get_session] = lambda: MagicMock()

    resp = client.get("/auth/callback?state=S&code=X", follow_redirects=False)

    assert resp.status_code == 400  # no handshake cookie → can't be a real login round-trip
