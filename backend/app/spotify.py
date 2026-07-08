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
import time
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

# Spotify Web API endpoint for the user's currently-playing track.
CURRENTLY_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"

# Spotify Web API endpoint for the user's recently-played tracks (last 50 max) — the snapshot tap.
RECENTLY_PLAYED_URL = "https://api.spotify.com/v1/me/player/recently-played"

# If Spotify says "too many requests" (429), wait at most this long before the single retry, so a
# rate-limit never turns into a long hang.
MAX_BACKOFF_SECONDS = 10

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


def get_currently_playing(session: Session, user_id: str) -> Optional[dict]:
    # Return what this user is currently playing on Spotify as a small normalized dict, or None when
    # there's nothing to show. None (never an exception) is deliberate — the endpoint turns it into a
    # friendly empty state, so a Spotify outage / unlinked account never becomes a 500.
    #
    # The returned shape (snake_case, so the router can build its response DTO directly):
    #   {"is_playing": bool, "track": {"spotify_id", "title", "artist_name", "album_art_url",
    #                                  "popularity"}}
    token = get_valid_access_token(session, user_id)
    if token is None:
        # No linked Spotify (or a failed refresh) — nothing to play.
        return None

    try:
        response = httpx.get(
            CURRENTLY_PLAYING_URL,
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
    except httpx.HTTPError:
        logger.warning("spotify currently-playing request errored", exc_info=True)
        return None

    # 204 = "nothing is playing right now"; anything other than 200 = an error we degrade past.
    if response.status_code == 204 or response.status_code != 200:
        return None

    data = response.json()
    item = data.get("item")
    if not item:
        # `item` is null when the user is playing something without a track (e.g. an ad or a
        # podcast episode) — we only surface real tracks.
        return None

    # Pull the fields our "now playing" badge needs out of Spotify's larger response.
    artist_name = ", ".join(a.get("name", "") for a in item.get("artists", []))
    images = item.get("album", {}).get("images", [])
    album_art_url = images[0]["url"] if images else None
    return {
        "is_playing": bool(data.get("is_playing", False)),
        "track": {
            "spotify_id": item["id"],
            "title": item["name"],
            "artist_name": artist_name,
            "album_art_url": album_art_url,
            "popularity": item.get("popularity"),
        },
    }


def _sleep(seconds: float) -> None:
    # Thin wrapper around time.sleep so tests can patch it out (no real waiting in the suite).
    time.sleep(seconds)


def get_recently_played(session: Session, user_id: str, limit: int = 50) -> Optional[dict]:
    # Return this user's recently-played tracks as Spotify's raw JSON, or None when we can't get it
    # (no linked Spotify, a failed refresh, or a persistent error). None (never an exception) lets
    # the snapshot job simply skip that user and move on. Handles Spotify's 429 "too many requests"
    # with a single bounded backoff+retry instead of crashing.
    token = get_valid_access_token(session, user_id)
    if token is None:
        return None

    headers = {"Authorization": f"Bearer {token}"}
    url = f"{RECENTLY_PLAYED_URL}?limit={limit}"
    for attempt in range(2):  # one initial try, plus one retry after a 429 backoff
        try:
            response = httpx.get(url, headers=headers, timeout=10)
        except httpx.HTTPError:
            logger.warning("spotify recently-played request errored", exc_info=True)
            return None

        if response.status_code == 200:
            return response.json()

        if response.status_code == 429 and attempt == 0:
            # Respect Spotify's Retry-After (seconds) if present, capped so we never hang long.
            retry_after = response.headers.get("Retry-After")
            delay = min(int(retry_after), MAX_BACKOFF_SECONDS) if (retry_after or "").isdigit() else MAX_BACKOFF_SECONDS
            logger.warning("spotify recently-played 429; backing off %ss then retrying", delay)
            _sleep(delay)
            continue

        logger.warning("spotify recently-played returned %s", response.status_code)
        return None

    return None  # exhausted the retry (still rate-limited)


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
