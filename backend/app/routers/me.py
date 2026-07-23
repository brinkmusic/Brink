# WHAT THIS FILE IS
# Account actions on the LOGGED-IN user's own account, under /api/me:
#   POST  /api/me/become-artist      -> flip the caller's account to an artist account (T55).
#   PATCH /api/me/profile            -> set the caller's own bio (T48).
#   POST  /api/me/avatar/sign-upload -> mint a signed upload URL for a new profile picture (T48).
#   POST  /api/me/avatar             -> point the caller's avatar at an uploaded image (T48).
#   POST  /api/me/plays/refresh      -> pull the caller's own recently-played from Spotify NOW (T100).
# Login is required on all of them, and every write is ALWAYS applied to the authenticated caller
# (resolved from their session), never to a client-supplied id, so nothing here can be spoofed.
#
# (The other /api/me endpoint, GET /api/me/now-playing, lives in now_playing.py.)

import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.deps import require_user
from app.models import User
from app.rate_limit import enforce_rate_limit
from app.responses import fail, ok
# Reuse the SNAPSHOT ingest pipeline (T21) rather than writing a second one: _ingest_user lands the
# raw Spotify payload in bronze and conforms Track/Play into silver with the same (userId, playedAt)
# dedup the cron uses. get_recently_played is the Spotify HTTP boundary (returns None on any degraded
# case: no linked account, refresh failure, outage).
from app.routers.snapshot import _ingest_user
from app.schemas import (
    ArtistStateOut,
    AvatarOut,
    AvatarSaveBody,
    AvatarSignUploadOut,
    ProfileBioOut,
    SignUploadBody,
    UpdateProfileBody,
)
from app.security.supabase import create_signed_upload_url, public_object_url
from app.spotify import get_recently_played

# How often one user may force a self-refresh (ADR-0011). The profile page fires this once per visit,
# so a small cap (2 per 10 minutes) is plenty for a real visitor yet stops a client hammering Spotify.
# Module-level so it reads clearly and tests can reason about it.
PLAYS_REFRESH_RATE_LIMIT = 2
PLAYS_REFRESH_RATE_WINDOW_SECONDS = 600

# The PUBLIC Supabase Storage bucket that holds profile pictures (created manually by Andrea — see
# the ticket's "Manual (user)" step). "Public" (unlike the artist-images bucket) means objects are
# world-readable by URL, so an avatar can render in an <img> without a signed read URL.
AVATAR_BUCKET = "avatars"

# Map each allowed image MIME type to the file extension we give the stored object. The request
# schema already guarantees content_type is one of these two, so this lookup can't miss.
_EXTENSION = {"image/jpeg": "jpg", "image/png": "png"}

router = APIRouter(tags=["me"])


@router.post("/api/me/become-artist")
def become_artist(
    user: User = Depends(require_user),   # ensures the caller is logged in; gives us their record
    session: Session = Depends(get_session),
):
    # Load the caller's own row through THIS request's session so the update is attached to the same
    # session we commit (avoids a detached-instance error). require_user already proved they exist.
    account = session.get(User, user.id)

    # Idempotent: if they're already an artist this is a no-op success — no error, no second write —
    # so a double-tap can't fail. Otherwise set the flag and save. This is a one-way switch by design
    # (T55): there is no in-app path back to a listener account.
    if account is not None and not account.is_artist:
        account.is_artist = True
        session.add(account)
        session.commit()

    # Return the resulting state through the DTO so we only emit the allow-listed camelCase field.
    out = ArtistStateOut(is_artist=True)
    return ok(out.model_dump(by_alias=True, mode="json"))


@router.patch("/api/me/profile")
def update_profile(
    body: UpdateProfileBody,   # bio is already trimmed + length-checked (<= 300) by the schema
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    # Load the caller's own row through THIS request's session so the update is attached to the
    # session we commit (same pattern as become_artist).
    account = session.get(User, user.id)

    # An empty bio (after the schema's whitespace trim) means "clear it" — store NULL rather than an
    # empty string, so a blank bio and a never-set bio look the same everywhere.
    bio = body.bio or None
    if account is not None:
        account.bio = bio
        session.add(account)
        session.commit()

    out = ProfileBioOut(bio=bio)
    return ok(out.model_dump(by_alias=True, mode="json"))


@router.post("/api/me/avatar/sign-upload")
def sign_avatar_upload(
    body: SignUploadBody,   # contentType (jpeg/png) + sizeBytes (<= 10 MB) validated by the schema
    user: User = Depends(require_user),   # login required; any user may set an avatar (not artist-only)
):
    # No DB access here — this route only mints a storage URL — so it takes no session dependency.
    # Build the object path INSIDE the caller's own folder: "<userId>/<random>.<ext>". Namespacing by
    # the caller's id keeps each user's uploads separate, and the /api/me/avatar step below only
    # accepts a path in this same folder, so a user can only ever set their OWN uploaded object.
    extension = _EXTENSION[body.content_type]
    path = f"{user.id}/{uuid.uuid4().hex}.{extension}"

    # Ask Supabase (as the server, holding the service-role key) to sign a one-time upload URL for
    # exactly that path in the PUBLIC avatars bucket. The browser then uploads the file with it.
    signed = create_signed_upload_url(AVATAR_BUCKET, path)

    out = AvatarSignUploadOut(
        path=signed["path"],
        signed_url=signed["signed_url"],
        token=signed["token"],
        # The permanent public URL the object will have — returned now so the browser can send it
        # back (via the path) and we store it on the user; also handy for an optimistic preview.
        public_url=public_object_url(AVATAR_BUCKET, signed["path"]),
    )
    return ok(out.model_dump(by_alias=True, mode="json"))


@router.post("/api/me/avatar")
def set_avatar(
    body: AvatarSaveBody,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    # Security check: the path MUST be inside the caller's own folder ("<userId>/..."). Without this,
    # a caller could point their avatar at any object path — including someone else's — so we reject
    # anything that doesn't start with their id + "/". A clean 400, no write.
    if not body.path.startswith(f"{user.id}/"):
        return fail("path outside your own folder", 400)

    account = session.get(User, user.id)
    # Store the PUBLIC object URL (not the bare path) so the avatar renders directly in an <img src>.
    avatar_url = public_object_url(AVATAR_BUCKET, body.path)
    if account is not None:
        account.avatar_url = avatar_url
        session.add(account)
        session.commit()

    out = AvatarOut(avatar_url=avatar_url)
    return ok(out.model_dump(by_alias=True, mode="json"))


@router.post("/api/me/plays/refresh")
def refresh_plays(
    user: User = Depends(require_user),   # login required; the caller can only refresh their OWN plays
    session: Session = Depends(get_session),
):
    # Abuse/Spotify guard first: refuse (429) if this user has forced a refresh too many times
    # recently. enforce_rate_limit raises RateLimitError on the cap, which the app-wide handler turns
    # into the standard 429 { error } envelope.
    enforce_rate_limit(
        session,
        subject=user.id,
        action="plays_refresh",
        limit=PLAYS_REFRESH_RATE_LIMIT,
        window_seconds=PLAYS_REFRESH_RATE_WINDOW_SECONDS,
    )

    # Pull the caller's last 50 plays from Spotify. None means we couldn't get them (no linked
    # account, token refresh failed, Spotify outage) — that's a NORMAL empty result, not an error
    # (T20 degradation philosophy), so we report 0 inserted rather than failing the request.
    payload = get_recently_played(session, user.id)
    inserted = 0
    if payload is not None:
        # Same ingest the cron runs: land raw -> conform Track/Play with (userId, playedAt) dedup, so
        # firing this repeatedly (or alongside the cron) can never double-count. Commit once, here.
        inserted = _ingest_user(session, user.id, payload)
        session.commit()

    return ok({"playsInserted": inserted})
