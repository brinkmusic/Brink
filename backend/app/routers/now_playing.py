# WHAT THIS FILE IS
# The "now playing" endpoint (T20):
#   GET /api/me/now-playing -> the authenticated user's currently-playing Spotify track, or null.
# Login required. It reads playback through the server-refreshed token (spotify.get_currently_playing,
# built on T22), and NEVER errors on the normal empty cases — nothing playing, or a handle account
# with no linked Spotify both return { data: null }. Backs the now-playing badge wired up in T44.

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.deps import require_user
from app.models import User
from app.responses import ok
from app.schemas import NowPlayingOut
from app.spotify import get_currently_playing

router = APIRouter(tags=["now-playing"])


@router.get("/api/me/now-playing")
def now_playing(
    user: User = Depends(require_user),   # ensures the caller is logged in; gives us their record
    session: Session = Depends(get_session),
):
    # Ask Spotify what this user is playing. None covers every empty/degraded case (nothing playing,
    # no linked Spotify, refresh failure, Spotify outage) — all of which are a normal { data: null },
    # not an error.
    current = get_currently_playing(session, user.id)
    if current is None:
        return ok(None)

    # Build the response through the DTO so we only ever emit the allow-listed camelCase fields.
    out = NowPlayingOut(**current)
    return ok(out.model_dump(by_alias=True, mode="json"))
