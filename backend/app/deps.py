# WHAT THIS FILE IS
# The "who is this request from?" gatekeeper. require_user() reads the login token
# a request carries, checks it with Supabase, and returns the matching Brink user —
# creating that user the first time they ever sign in. Any endpoint that needs a
# logged-in user asks for this (via FastAPI's Depends), so the check lives in one place.
#
# Ported from the old api/_lib/auth.ts (removed in T08; see ADR-0010). The handle-
# generation logic is preserved exactly. Two deliberate differences from the TS version:
#   1. ValueError from admin() (missing SUPABASE_URL/KEY) propagates as 500 rather than
#      being swallowed into a silent 401 — misconfiguration must be visible in logs.
#   2. The first-sign-in INSERT is wrapped to handle a concurrent-request race: if two
#      requests arrive simultaneously for the same new user, the losing INSERT hits the
#      unique constraint; we roll back and return the winner's row instead of 500ing.

import logging
import re
import unicodedata

from fastapi import Depends, Request
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from app.db import get_session
from app.models import User
from app.security import supabase

logger = logging.getLogger(__name__)


# A small error type carrying an HTTP status. When raised, an app-wide handler
# (registered in main.py) turns it into our standard { "error": ... } response.
class AuthError(Exception):
    def __init__(self, message: str, status: int = 401):
        super().__init__(message)
        self.message = message
        self.status = status


def _bearer_token(request: Request) -> str:
    # Login tokens arrive in the header "Authorization: Bearer <token>". Pull out the
    # token part; if it's missing or malformed, the request isn't authenticated.
    header = request.headers.get("authorization") or ""
    match = re.match(r"^Bearer (.+)$", header, re.IGNORECASE)
    if not match:
        raise AuthError("missing bearer token")
    return match.group(1)


def _slugify(s: str) -> str:
    # Turn a display name into a URL-safe handle piece: lowercase, strip accents and
    # punctuation down to letters/numbers/dashes, trim stray dashes, cap at 20 chars.
    s = unicodedata.normalize("NFKD", s.lower())
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = re.sub(r"^-+|-+$", "", s)
    return s[:20]


def get_or_create_user(session: Session, su) -> User:
    # Given a validated Supabase user (`su`), return their Brink `User` row, creating it
    # on first sign-in. Extracted from require_user so the server-side login callback
    # (T09) can provision a user from the SAME identity data without re-implementing the
    # handle policy. `su` is any object exposing id/email/user_metadata/app_metadata —
    # the real supabase_auth User, or a session's `.user`.

    # Already have this person? Return their existing record.
    existing = session.exec(select(User).where(User.supabase_user_id == su.id)).first()
    if existing:
        return existing

    # First sign-in: build their Brink profile from the info Supabase gives us.
    meta = getattr(su, "user_metadata", None) or {}
    app_meta = getattr(su, "app_metadata", None) or {}
    is_spotify = app_meta.get("provider") == "spotify"
    email = getattr(su, "email", None)

    # Pick the best available display name, falling back to "Listener".
    display_name = meta.get("full_name") or meta.get("name") or (
        email.split("@")[0] if email else "Listener"
    )
    # Handle = a readable slug + 6 characters of the (unique) Supabase user id. WHY
    # the id suffix: it guarantees the handle is unique with no database retry loop.
    base = _slugify(display_name) or "user"
    handle = f"{base}-{su.id.replace('-', '')[:6]}"

    user = User(
        supabase_user_id=su.id,
        email=email,
        display_name=display_name,
        handle=handle,
        avatar_url=meta.get("avatar_url") or meta.get("picture"),
        spotify_id=(meta.get("provider_id") or meta.get("sub")) if is_spotify else None,
    )
    try:
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    except IntegrityError:
        # Two concurrent requests for the same new user both passed the select above
        # (both saw "no row"), then both tried to INSERT. The DB correctly rejected
        # the second one via the supabaseUserId unique constraint. Roll back our failed
        # transaction and return the row the first request already created.
        session.rollback()
        existing = session.exec(select(User).where(User.supabase_user_id == su.id)).first()
        if existing:
            return existing
        raise  # genuinely unexpected — re-raise for a 500


def require_user(request: Request, session: Session = Depends(get_session)) -> User:
    token = _bearer_token(request)

    # Ask Supabase to validate the token and tell us who it belongs to.
    # - ValueError means a configuration problem (e.g. SUPABASE_URL not set) — let it
    #   propagate so the server 500s and the missing config is visible in Render logs.
    # - Any other exception (network error, bad/expired token) means "not a valid
    #   session" → 401. We log the original error at DEBUG so it's diagnosable without
    #   leaking details to the caller.
    try:
        su = supabase.get_user_from_token(token)
    except ValueError:
        raise  # misconfiguration — must surface as 500, not a silent 401
    except Exception:
        logger.debug("token verification failed", exc_info=True)
        raise AuthError("invalid session")
    if su is None:
        raise AuthError("invalid session")

    return get_or_create_user(session, su)
