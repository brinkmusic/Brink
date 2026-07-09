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

from app.routers import auth as auth_router
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

    # The callback URL is derived from the request origin, so it adapts to local vs prod.
    assert captured["redirect_to"].endswith("/auth/callback")
    assert captured["scopes"] == EXPECTED_SCOPES
