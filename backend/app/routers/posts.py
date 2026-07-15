# WHAT THIS FILE IS
# The posts endpoints — the first real read/write path of Brink's social layer (T10):
#   POST /api/posts        -> create a post (share a song), login required
#   GET  /api/posts?userId -> list one user's posts, newest first, each with its track
# The feed, reactions and comments (later tickets) all build on the Post rows created here.

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.deps import require_user
from app.models import Post, Track, User
from app.rate_limit import enforce_rate_limit
from app.responses import ok
from app.schemas import CreatePostBody, PostOut, TrackOut
from app.tracks import upsert_track

# The per-user cap on creating posts: at most POST_RATE_LIMIT posts per window (ADR-0011).
# Kept as module-level names so they read clearly and tests can lower them.
POST_RATE_LIMIT = 10
POST_RATE_WINDOW_SECONDS = 60

# prefix=... means every route below is under /api/posts, so we don't repeat the path.
# tags=... just groups these routes together in the auto-generated API docs.
router = APIRouter(prefix="/api/posts", tags=["posts"])


# Build the API response shape for one post + its track. Centralized so both endpoints
# return the exact same fields (ADR-0012: never return the raw table row).
def _to_post_out(post: Post, track: Track) -> dict:
    out = PostOut(
        id=post.id,
        user_id=post.user_id,
        caption=post.caption,
        source=post.source,
        created_at=post.created_at,
        track=TrackOut(
            spotify_id=track.spotify_id,
            title=track.title,
            artist_name=track.artist_name,
            album_art_url=track.album_art_url,
            popularity=track.popularity,
        ),
    )
    # by_alias=True -> emit camelCase field names (trackId, albumArtUrl, ...) for the frontend.
    return out.model_dump(by_alias=True, mode="json")


@router.post("")
def create_post(
    body: CreatePostBody,
    user: User = Depends(require_user),   # ensures the caller is logged in; gives us their record
    session: Session = Depends(get_session),
):
    # Abuse guard first: refuse (429) if this user has created too many posts recently.
    enforce_rate_limit(
        session,
        subject=user.id,
        action="post_create",
        limit=POST_RATE_LIMIT,
        window_seconds=POST_RATE_WINDOW_SECONDS,
    )

    # Make sure the song exists (or is refreshed) before the post links to it.
    track = upsert_track(session, body.track)
    # Write the Track to the database NOW, before adding the Post that foreign-key-references it.
    # WHY: our models declare FK columns but no ORM relationships, so SQLAlchemy inserts rows in the
    # order they were added, NOT in foreign-key dependency order — so without this flush a brand-new
    # Track and its Post could be sent to Postgres in an order that violates Post.trackId's FK (the
    # same failure mode as the T23 snapshot-500). flush() sends the pending Track in this same
    # transaction; the commit below still finalizes everything together.
    session.flush()

    # The author is ALWAYS the authenticated user — never taken from the request body, so it
    # can't be spoofed. source/caption come from the (already validated) body.
    post = Post(
        user_id=user.id,
        track_id=body.track.spotify_id,
        caption=body.caption,
        source=body.source,
    )
    session.add(post)
    session.commit()
    session.refresh(post)

    # 201 Created is the standard "a new thing was made" status.
    return ok(_to_post_out(post, track), status=201)


@router.get("")
def list_posts(userId: str, session: Session = Depends(get_session)):
    # userId is a REQUIRED query parameter (no default), so a missing one is rejected as a
    # 400 by the global validation handler. We join each post to its track so the response
    # includes the song, and order newest-first for feed-style display.
    rows = session.exec(
        select(Post, Track)
        .join(Track, Track.spotify_id == Post.track_id)
        .where(Post.user_id == userId)
        .order_by(Post.created_at.desc())
    ).all()
    return ok([_to_post_out(post, track) for post, track in rows])
