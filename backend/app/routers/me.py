# WHAT THIS FILE IS
# Account actions on the LOGGED-IN user's own account, under /api/me. Today that's just:
#   POST /api/me/become-artist -> flip the caller's account to an artist account (T55).
# The artist portal (T50-T54) gates everything on User.is_artist, but nothing else in the app
# ever sets that flag, so before this endpoint the only way to become an artist was to edit the
# database by hand. Login is required, and the flag is ALWAYS set on the authenticated caller
# (from their session), never on a client-supplied id, so it can't be spoofed.
#
# (The other /api/me endpoint, GET /api/me/now-playing, lives in now_playing.py.)

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.deps import require_user
from app.models import User
from app.responses import ok
from app.schemas import ArtistStateOut

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
