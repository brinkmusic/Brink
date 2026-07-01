# WHAT THIS FILE IS
# The "who is this request from?" gatekeeper. require_user() reads the login token
# a request carries, checks it with Supabase, and returns the matching Brink user —
# creating that user the first time they ever sign in. Any endpoint that needs a
# logged-in user asks for this (via FastAPI's Depends), so the check lives in one place.
#
# Ported 1:1 from the old api/_lib/auth.ts so behavior (and the generated handle) is
# identical to what production already does.

import re
import unicodedata

from fastapi import Depends, Request
from sqlmodel import Session, select

from app.db import get_session
from app.models import User
from app.security import supabase


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


def require_user(request: Request, session: Session = Depends(get_session)) -> User:
    token = _bearer_token(request)

    # Ask Supabase to validate the token and tell us who it belongs to. Any failure
    # (bad token, network error, no user) means "not a valid session" -> 401.
    try:
        su = supabase.get_user_from_token(token)
    except Exception:
        raise AuthError("invalid session")
    if su is None:
        raise AuthError("invalid session")

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
    session.add(user)
    session.commit()
    session.refresh(user)
    return user
