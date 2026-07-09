# WHAT THIS FILE IS
# The encrypted login-session cookie for Brink's server-rendered frontend (T09). It is the
# ONE place that knows the cookie's name, shape, lifetime, and hardening, so everything that
# touches it agrees: the login callback SETS it, logout CLEARS it, and require_user READS and
# (on expiry) REFRESHES it. WHY its own module: require_user lives in deps.py and the callback
# in routers/auth.py, and those already import each other — putting the shared cookie logic
# here avoids a circular import between them.
#
# The cookie holds the user's Supabase session tokens (a short-lived access token + a long-lived
# refresh token), encrypted at rest with our AES-256-GCM key (TOKEN_ENC_KEY) — so even though
# the cookie sits in the browser, its contents are unreadable without the server's key.

import json
from typing import Optional

from app.security.crypto import decrypt, encrypt

# The cookie name and how long the browser keeps it. 30 days matches how long we expect the
# Supabase refresh token to stay usable; each request re-verifies with Supabase regardless.
SESSION_COOKIE = "brink_session"
SESSION_COOKIE_MAX_AGE = 60 * 60 * 24 * 30  # 30 days, in seconds


def encode(access_token: str, refresh_token: str, expires_at) -> str:
    # Pack the Supabase session tokens into one encrypted string for the cookie value.
    return encrypt(
        json.dumps(
            {"access_token": access_token, "refresh_token": refresh_token, "expires_at": expires_at}
        )
    )


def decode(raw: str) -> Optional[dict]:
    # Reverse of encode(). Returns None (rather than raising) for a missing/tampered/undecodable
    # cookie, so callers can treat "can't read it" the same as "not logged in".
    try:
        return json.loads(decrypt(raw))
    except Exception:
        return None


def set_cookie(response, access_token: str, refresh_token: str, expires_at, secure: bool) -> None:
    # Write the hardened session cookie: httpOnly (JS can't read it → mitigates XSS token theft),
    # Secure in production (HTTPS only), SameSite=Lax (sent on normal navigations, not cross-site
    # sub-requests → CSRF defense).
    response.set_cookie(
        SESSION_COOKIE,
        encode(access_token, refresh_token, expires_at),
        max_age=SESSION_COOKIE_MAX_AGE,
        httponly=True,
        secure=secure,
        samesite="lax",
    )


def clear_cookie(response) -> None:
    response.delete_cookie(SESSION_COOKIE)
