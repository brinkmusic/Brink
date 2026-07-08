# WHAT THIS FILE IS
# The server's Spotify access layer. Its one job today: hand back a *valid* Spotify access token for
# a given user, so other code (the "now playing" endpoint T20, the snapshot job T21) can call the
# Spotify Web API on that user's behalf.
#
# WHY this is needed: a Spotify access token expires after about an hour, and Supabase does NOT
# refresh it for us — that's our responsibility. When we first captured the user's login
# (routers/auth.py) we saved two things, both encrypted: a short-lived access token and a long-lived
# "refresh token". This file uses the refresh token to obtain a fresh access token from Spotify when
# the old one has expired, re-encrypts the result, and saves it back.
#
# A recurring idea below: tokens are stored ENCRYPTED in the database (security/crypto.py). We only
# ever decrypt them into memory for the moment we need them, and re-encrypt before saving.

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
from sqlmodel import Session

from app.config import get_settings
from app.models import SpotifyToken
from app.security.crypto import decrypt, encrypt

logger = logging.getLogger(__name__)

# Spotify's OAuth token endpoint — where a refresh token is exchanged for a new access token.
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"

# Refresh a little BEFORE the token truly expires, so we never hand back one that dies mid-request.
EXPIRY_BUFFER_SECONDS = 60

# Fallback lifetime if Spotify's response omits "expires_in" (it normally sends ~3600 = 1 hour).
DEFAULT_EXPIRES_IN_SECONDS = 3600


def _utcnow() -> datetime:
    # Stored expiries are naive UTC (see routers/auth.py), so compare against a naive UTC "now".
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_valid_access_token(session: Session, user_id: str) -> Optional[str]:
    # Return a usable Spotify access token for this user, or None if we can't get one.
    # None (never an exception) is deliberate: callers show a graceful empty state instead of a 500.
    row = session.get(SpotifyToken, user_id)
    if row is None:
        # The user never linked Spotify (e.g. a handle-only account) — nothing to return.
        return None

    # Still fresh (expiry is comfortably in the future)? Use the stored token as-is, no network call.
    if row.expires_at > _utcnow() + timedelta(seconds=EXPIRY_BUFFER_SECONDS):
        return decrypt(row.access_token)

    # Expired (or about to): exchange the stored refresh token for a new access token.
    refreshed = _request_refreshed_token(decrypt(row.refresh_token))
    if refreshed is None:
        # Spotify said no (revoked token / outage) or we have no client credentials — degrade to None.
        logger.warning("spotify token refresh failed for user %s", user_id)
        return None

    access_token = refreshed["access_token"]
    # Persist the new token (re-encrypted) and its new expiry so the next call reuses it.
    row.access_token = encrypt(access_token)
    row.expires_at = _utcnow() + timedelta(
        seconds=int(refreshed.get("expires_in", DEFAULT_EXPIRES_IN_SECONDS))
    )
    # Spotify SOMETIMES returns a new refresh token; when it does, replace the stored one.
    if refreshed.get("refresh_token"):
        row.refresh_token = encrypt(refreshed["refresh_token"])
    session.add(row)
    session.commit()
    return access_token


def _request_refreshed_token(refresh_token: str) -> Optional[dict]:
    # Ask Spotify for a fresh access token using the refresh_token grant. Returns the parsed JSON on
    # success, or None on any failure (missing credentials, network error, non-200) — the caller
    # turns None into a graceful empty state.
    settings = get_settings()
    client_id = settings.spotify_client_id
    client_secret = settings.spotify_client_secret
    if not client_id or not client_secret:
        # Without app credentials we can't authenticate the refresh call at all.
        return None

    try:
        # The refresh_token grant: Spotify authenticates the *app* via HTTP Basic auth
        # (client id + secret) and takes the grant parameters as form data.
        response = httpx.post(
            SPOTIFY_TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": refresh_token},
            auth=(client_id, client_secret),
            timeout=10,
        )
    except httpx.HTTPError:
        # Network/timeout problems must not crash the caller.
        logger.warning("spotify token endpoint request errored", exc_info=True)
        return None

    if response.status_code != 200:
        logger.warning("spotify token endpoint returned %s", response.status_code)
        return None

    return response.json()
