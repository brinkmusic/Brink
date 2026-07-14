# WHAT THIS FILE IS
# The catalog-search endpoint (T40): GET /api/search?q=<text> -> Spotify tracks matching the
# query, so the composer can let a user find a song to post. WHY it's its own router and uses an
# APP-level Spotify token (client credentials, see app/spotify.py) rather than the user's token:
# search doesn't act on anyone's behalf, so it works even for users who never linked their own
# Spotify. Login is still required (Brink is private) and the call is rate-limited because each
# search hits Spotify's API (an expensive upstream dependency).

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session

from app.db import get_session
from app.deps import require_user
from app.models import User
from app.rate_limit import enforce_rate_limit
from app.responses import fail, ok
from app.schemas import TrackOut
from app.spotify import search_tracks

# Per-user cap on searches (ADR-0011): searches are frequent (one per keystroke burst) but each is
# an upstream Spotify call, so we bound them. Module-level so tests can lower it.
SEARCH_RATE_LIMIT = 30
SEARCH_RATE_WINDOW_SECONDS = 60

router = APIRouter(tags=["search"])


@router.get("/api/search")
def search(
    # `q` is required and non-empty: a missing or blank value fails validation, which the app's
    # handler turns into a clean 400 (ADR-0007). max_length guards against absurd queries.
    q: str = Query(..., min_length=1, max_length=200),
    user: User = Depends(require_user),   # login required (private app); also gives us the rate-limit subject
    session: Session = Depends(get_session),
):
    # Cap per user before doing the expensive upstream call (ADR-0007 §5).
    enforce_rate_limit(
        session,
        subject=user.id,
        action="search",
        limit=SEARCH_RATE_LIMIT,
        window_seconds=SEARCH_RATE_WINDOW_SECONDS,
    )

    results = search_tracks(q)
    if results is None:
        # No Spotify credentials configured, or Spotify errored/refused — report it as a clean
        # 502 (a real upstream problem) rather than letting an exception become a 500.
        return fail("search unavailable", 502)

    # Normalize to the same camelCase track shape the rest of the frontend uses (TrackOut), which
    # is exactly the shape the composer then posts back to POST /api/posts.
    tracks = [
        TrackOut(
            spotify_id=r["spotify_id"],
            title=r["title"],
            artist_name=r["artist_name"],
            album_art_url=r["album_art_url"],
            popularity=r["popularity"],
        ).model_dump(by_alias=True, mode="json")
        for r in results
    ]
    return ok(tracks)
