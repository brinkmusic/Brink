# WHAT THIS FILE IS
# The auth routes for Brink's server-rendered frontend, in two parts:
#   1. Server-side Spotify LOGIN (T09, ADR-0013): GET /auth/login → /auth/callback →
#      /auth/logout. We run the OAuth handshake ourselves (no browser Supabase client),
#      set an encrypted session cookie, and capture the user's Spotify tokens on the way.
#   2. The LEGACY browser capture endpoint POST /api/auth/capture-spotify — how the old
#      React SPA (retired in T60) forwarded its Spotify tokens. Nothing calls it anymore;
#      removing it is tracked as ticket T63.
# Both store the Spotify tokens ENCRYPTED so background jobs (the snapshot, T21) can
# later fetch the user's listening history.

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.deps import get_or_create_user, require_user
from app.models import SpotifyToken, User
from app.responses import fail, ok
from app.security import session as login_session
from app.security import supabase
from app.security.crypto import decrypt, encrypt

router = APIRouter()

# The Spotify permissions the login asks for. These are the scopes the snapshot (T21) and
# now-playing (T20) features depend on: read the user's email, recently-played, top tracks,
# and currently-playing. (Kept identical to what the old React SPA requested before T60.)
SPOTIFY_SCOPES = (
    "user-read-email user-read-recently-played user-top-read user-read-currently-playing"
)

# Short-lived cookie that carries the login handshake (the PKCE verifier + a CSRF state)
# from /auth/login to /auth/callback. Encrypted, httpOnly, and expires in minutes.
OAUTH_COOKIE = "brink_oauth"
OAUTH_COOKIE_MAX_AGE = 600  # seconds — the login round-trip should take well under this


def _set_cookie(response, name: str, value: str, max_age: int, secure: bool) -> None:
    # One place for our cookie hardening: httpOnly (JS can't read it → mitigates XSS token
    # theft), Secure in production (HTTPS only), SameSite=Lax (sent on top-level navigations
    # like the OAuth redirect, but not on cross-site sub-requests → CSRF defense).
    response.set_cookie(
        name, value, max_age=max_age, httponly=True, secure=secure, samesite="lax"
    )


def _login_failed(reason: str) -> HTMLResponse:
    # A friendly, self-contained "login didn't work" page. WHY not a 500: OAuth can fail for
    # ordinary reasons (the user hit "cancel", a stale/replayed callback), and those must
    # not look like a server crash. 400 = "this request was bad", with a link to retry.
    html = (
        "<!doctype html><html><head><meta charset='utf-8'><title>Login failed · Brink</title>"
        "<link rel='stylesheet' href='/static/brink.css'></head><body><main class='container'>"
        f"<h1>Couldn't sign you in</h1><p>{reason}</p>"
        "<p><a class='btn btn-spotify' href='/auth/login'>Try again</a></p>"
        "</main></body></html>"
    )
    return HTMLResponse(html, status_code=400)


@router.get("/auth/login")
def auth_login(request: Request):
    # Step 1 of server-side Spotify login: send the browser to Spotify's consent screen.
    # The callback URL is derived from the current origin, so this works unchanged on
    # localhost and on Render (the derived URL must be in Supabase's redirect allow-list).
    # We put the CSRF state IN the callback URL as a query param: Supabase preserves it and
    # echoes it back to the callback, giving us a value to check against the cookie below.
    state = secrets.token_urlsafe(32)
    redirect_to = f"{str(request.base_url).rstrip('/')}/auth/callback?state={state}"
    authorize_url, verifier = supabase.oauth_authorize(redirect_to, SPOTIFY_SCOPES)

    # Stash the state + the PKCE verifier in an encrypted handshake cookie so the callback
    # can (a) confirm the state matches and (b) complete the PKCE code exchange.
    handshake = encrypt(json.dumps({"state": state, "verifier": verifier}))

    # 307 keeps the method a GET as the browser follows the redirect to Spotify.
    response = RedirectResponse(authorize_url, status_code=307)
    _set_cookie(
        response,
        OAUTH_COOKIE,
        handshake,
        max_age=OAUTH_COOKIE_MAX_AGE,
        secure=request.url.scheme == "https",
    )
    return response


@router.get("/auth/callback")
def auth_callback(request: Request, session: Session = Depends(get_session)):
    # Step 2: Spotify (via Supabase) sends the browser back here with ?code=...&state=...
    # We verify the handshake, exchange the code for a session, provision the user, capture
    # their Spotify tokens, and set the login cookie. Any failure renders _login_failed,
    # never a 500 (ADR-0007).
    secure = request.url.scheme == "https"
    params = request.query_params

    # The user cancelled, or Spotify/Supabase reported a problem: show the friendly page.
    if params.get("error"):
        return _login_failed(params.get("error_description") or "Spotify sign-in was cancelled.")

    # The handshake cookie must be present and decryptable — without it this isn't a login
    # round-trip we started (or it's expired). Reject rather than trust the query alone.
    raw = request.cookies.get(OAUTH_COOKIE)
    if not raw:
        return _login_failed("Your login session expired. Please try again.")
    try:
        handshake = json.loads(decrypt(raw))
    except Exception:
        return _login_failed("Your login session was invalid. Please try again.")

    # CSRF check: the state echoed back by Supabase must match the one we stored.
    if not params.get("state") or params.get("state") != handshake.get("state"):
        return _login_failed("Your login session didn't match. Please try again.")

    code = params.get("code")
    if not code:
        return _login_failed("Spotify didn't return a login code. Please try again.")

    # Exchange the one-time code for a Supabase session (carries the Spotify provider
    # tokens). A failure here (bad/expired code, verifier mismatch) → friendly page.
    try:
        sb_session = supabase.exchange_code(code, handshake["verifier"])
    except Exception:
        return _login_failed("We couldn't complete your Spotify sign-in. Please try again.")
    if sb_session is None or getattr(sb_session, "user", None) is None:
        return _login_failed("We couldn't complete your Spotify sign-in. Please try again.")

    # Provision (or fetch) the Brink user from the Supabase identity — same handle policy
    # as the JSON API's require_user (reused, not re-implemented).
    user = get_or_create_user(session, sb_session.user)

    # Capture the Spotify provider tokens so background jobs can use them. Only if the
    # provider refresh token is present (it is on the initial OAuth exchange).
    provider_refresh = getattr(sb_session, "provider_refresh_token", None)
    provider_access = getattr(sb_session, "provider_token", None)
    if provider_refresh and provider_access:
        _store_spotify_token(session, user.id, provider_access, provider_refresh, SPOTIFY_SCOPES)
        session.commit()

    # Set the login cookie: the encrypted Supabase session tokens (require_user reads these
    # and re-verifies with Supabase on each request). 303 → the browser does a plain GET to
    # /feed after the POST-like OAuth exchange.
    response = RedirectResponse("/feed", status_code=303)
    login_session.set_cookie(
        response,
        sb_session.access_token,
        sb_session.refresh_token,
        getattr(sb_session, "expires_at", None),
        secure,
    )
    response.delete_cookie(OAUTH_COOKIE)  # handshake is single-use; clear it
    return response


@router.get("/auth/logout")
def auth_logout():
    # Clear the login cookie and return to the landing page. 303 → plain GET of "/".
    response = RedirectResponse("/", status_code=303)
    login_session.clear_cookie(response)
    return response


# The expected request body. All fields Optional so we can return our own clear 400
# below when a token is missing, rather than a generic validation error.
# LEGACY-PARITY EXCEPTION — do not copy this into new endpoints. The all-Optional shape
# exists only to reproduce the old backend's exact 400 message. Per ADR-0007 (layer 1)
# and T70's handlers, T10+ request schemas declare required, typed fields and let the
# RequestValidationError handler return the clean 400.
class CaptureBody(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    scopes: Optional[str] = None


def _store_spotify_token(
    session: Session, user_id: str, access_token: str, refresh_token: str, scopes: str
) -> None:
    # "Upsert" the user's Spotify tokens: update the row if it exists, else create it.
    # Keyed by user id; both tokens are ENCRYPTED before saving. Shared by the login
    # callback and the legacy capture endpoint so the encrypt-and-store logic lives once.
    # NOTE: the caller commits — this only stages the change on the session.
    # Spotify access tokens last ~1 hour; store the expiry as a naive UTC timestamp to
    # match how the existing rows (written by the old backend) were saved.
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
    row = session.get(SpotifyToken, user_id)
    if row is None:
        row = SpotifyToken(user_id=user_id)
        session.add(row)
    row.access_token = encrypt(access_token)
    row.refresh_token = encrypt(refresh_token)
    row.expires_at = expires_at
    row.scopes = scopes or ""


@router.post("/api/auth/capture-spotify")
def capture_spotify(
    body: CaptureBody,
    user: User = Depends(require_user),  # ensures the caller is logged in; gives us their record
    session: Session = Depends(get_session),
):
    # Both tokens are required. WHY check here (not via the model): we want the exact
    # same 400 + message the old backend returned.
    if not body.refresh_token or not body.access_token:
        return fail("missing spotify tokens", 400)

    _store_spotify_token(session, user.id, body.access_token, body.refresh_token, body.scopes or "")
    session.commit()
    return ok({"captured": True})
