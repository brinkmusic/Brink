# WHAT THIS FILE IS
# The endpoint the browser calls right after a user logs in with Spotify:
#   POST /api/auth/capture-spotify
# Supabase hands the browser the Spotify tokens once (just after login). The browser
# forwards them here, and we store them ENCRYPTED so a background job can later use
# them to fetch the user's listening history. Ported from the old
# api/auth/capture-spotify.ts (removed in T08; see ADR-0010).

import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.deps import require_user
from app.models import SpotifyToken, User
from app.responses import fail, ok
from app.security import supabase
from app.security.crypto import encrypt

router = APIRouter()

# The Spotify permissions the login asks for. Kept identical to what the old React SPA
# requested (apps/web/src/context/AuthContext.tsx) so the server-side login grants the
# same access the snapshot (T21) and now-playing (T20) features already depend on.
SPOTIFY_SCOPES = (
    "user-read-email user-read-recently-played user-top-read user-read-currently-playing"
)

# Short-lived cookie that carries the login handshake (the PKCE verifier + a CSRF state)
# from /auth/login to /auth/callback. Encrypted, httpOnly, and expires in minutes.
OAUTH_COOKIE = "brink_oauth"
OAUTH_COOKIE_MAX_AGE = 600  # seconds — the login round-trip should take well under this


@router.get("/auth/login")
def auth_login(request: Request):
    # Step 1 of server-side Spotify login: send the browser to Spotify's consent screen.
    # The callback URL is derived from the current origin, so this works unchanged on
    # localhost and on Render (the derived URL must be in Supabase's redirect allow-list).
    redirect_to = str(request.base_url).rstrip("/") + "/auth/callback"
    authorize_url, verifier = supabase.oauth_authorize(redirect_to, SPOTIFY_SCOPES)

    # A random CSRF state we generate and stash alongside the PKCE verifier; the callback
    # checks it to reject login attempts that didn't originate from this browser.
    state = secrets.token_urlsafe(32)
    handshake = encrypt(json.dumps({"state": state, "verifier": verifier}))

    # 307 keeps the method a GET as the browser follows the redirect to Spotify.
    response = RedirectResponse(authorize_url, status_code=307)
    response.set_cookie(
        OAUTH_COOKIE,
        handshake,
        max_age=OAUTH_COOKIE_MAX_AGE,
        httponly=True,  # JavaScript can't read it — mitigates XSS token theft
        secure=request.url.scheme == "https",  # HTTPS-only in prod; off for local http dev
        samesite="lax",
    )
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

    # Spotify access tokens last ~1 hour. Store an expiry as a plain UTC timestamp to
    # match how the existing rows (written by the old backend) were saved.
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)

    # "Upsert": update the user's token row if it exists, otherwise create it. The row
    # is keyed by user id, and both tokens are encrypted before saving.
    row = session.get(SpotifyToken, user.id)
    if row is None:
        row = SpotifyToken(user_id=user.id)
        session.add(row)
    row.access_token = encrypt(body.access_token)
    row.refresh_token = encrypt(body.refresh_token)
    row.expires_at = expires_at
    row.scopes = body.scopes or ""

    session.commit()
    return ok({"captured": True})
