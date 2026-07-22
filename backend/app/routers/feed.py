# WHAT THIS FILE IS
# The feed endpoint — the app's home surface (T13, T049):
#   GET /api/feed -> posts from the people the caller follows PLUS the caller's own posts,
#                    newest-first, each with its track, per-type reaction counts, a comment
#                    count, and which reactions the CALLER left. Login required (private app).
#                    Since T049 it ALSO includes the behind-the-scenes ArtistPosts (T50/T51) of the
#                    artists the caller follows, interleaved with the song posts by time. Each item
#                    carries a "kind" field ("song" or "artist") so the frontend knows which card to
#                    render.
# It reads the follow graph from app/routers/follow.py and the posts/reactions/comments created by
# T10–T12 (and the artist-post engagement from T52). Satisfies BE-7.
#
# WHY the query is written in batches: a naive version would loop over each post and run a
# separate count query per post ("N+1 queries") — slow as the feed grows. Instead we fetch the
# posts once, then fetch ALL their reaction counts, comment counts, and the viewer's reactions in
# one grouped query each (a fixed handful of queries, no matter how many posts). The artist posts
# are batched the same way against the ArtistReaction/ArtistComment tables.

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from app.db import get_session
from app.deps import require_user
from app.models import (
    ArtistComment,
    ArtistPost,
    ArtistReaction,
    Comment,
    Follow,
    Post,
    Reaction,
    ReactionType,
    Track,
    User,
)
from app.responses import ok
from app.schemas import ArtistFeedPostOut, AuthorOut, FeedPostOut, TrackOut
from app.security.supabase import create_signed_read_url

# The private Supabase Storage bucket that holds artist promo images (same one artist.py uploads
# into). Its objects aren't publicly readable, so each stored image PATH must be turned into a
# short-lived signed read URL before the browser can load it (T53).
ARTIST_IMAGE_BUCKET = "artist-images"

router = APIRouter(tags=["feed"])


# A fresh map with every reaction type set to its zero value. Used so reaction_counts and
# viewer_reactions always carry every type (HEART/FIRE/SPARKLE) — a stable shape for the frontend.
def _zero_counts() -> dict[str, int]:
    return {rt.value: 0 for rt in ReactionType}


def _no_viewer_reactions() -> dict[str, bool]:
    return {rt.value: False for rt in ReactionType}


@router.get("/api/feed")
def get_feed(
    user: User = Depends(require_user),   # ensures the caller is logged in; gives us their record
    session: Session = Depends(get_session),
):
    # Thin wrapper: build the feed data and wrap it in the standard { data } envelope. The building
    # logic lives in build_feed() below so the server-rendered feed PAGE (ADR-0013, in
    # app/routers/pages.py) can reuse the exact same feed without duplicating any of it.
    return ok(build_feed(session, user))


# Build the feed as a list of plain dicts (camelCase, ready for JSON or an HTML template): the song
# posts of everyone `user` follows plus their own, INTERLEAVED with the behind-the-scenes ArtistPosts
# of the artists they follow, newest-first. Each item carries a "kind" ("song" or "artist"), the
# author, per-type reaction counts, a comment count, and which reactions `user` left. Shared by the
# JSON endpoint above and the feed page — the single source of truth for "what's in the feed".
def build_feed(session: Session, user: User) -> list[dict]:
    # Whose posts to show: everyone the caller follows, plus the caller themselves (so a brand-new
    # user with no follows still sees their own posts). The same set of author ids drives BOTH the
    # song posts and the artist posts below.
    followee_ids = session.exec(
        select(Follow.following_id).where(Follow.follower_id == user.id)
    ).all()
    author_ids = set(followee_ids) | {user.id}

    # Build each half of the feed, then merge. Each helper returns a list of (created_at, item) pairs
    # so we can sort the combined list by time regardless of which kind an item is.
    song_items = _build_song_items(session, user, author_ids)
    artist_items = _build_artist_items(session, user, author_ids)

    # Merge and sort newest-first by the raw datetime (NOT the serialized string), then drop the sort
    # key and return just the item dicts.
    merged = sorted(song_items + artist_items, key=lambda pair: pair[0], reverse=True)
    return [item for _, item in merged]


# The song-share half of the feed (the original T13 behaviour). Returns (created_at, item) pairs so
# build_feed can interleave them with the artist posts by time.
def _build_song_items(session: Session, user: User, author_ids: set[str]) -> list[tuple]:
    # The posts themselves, joined to their track and their author (the User who posted). Joining the
    # author here avoids a separate lookup per post when we build the response.
    rows = session.exec(
        select(Post, Track, User)
        .join(Track, Track.spotify_id == Post.track_id)
        .join(User, User.id == Post.user_id)
        .where(Post.user_id.in_(author_ids))
        .order_by(Post.created_at.desc())
    ).all()
    if not rows:
        return []

    post_ids = [post.id for post, _, _ in rows]

    # Reaction counts for all these posts in one grouped query: (postId, type) -> count.
    reaction_counts: dict[str, dict[str, int]] = {}
    for post_id, rtype, n in session.exec(
        select(Reaction.post_id, Reaction.type, func.count())
        .where(Reaction.post_id.in_(post_ids))
        .group_by(Reaction.post_id, Reaction.type)
    ).all():
        reaction_counts.setdefault(post_id, _zero_counts())[ReactionType(rtype).value] = n

    # Comment counts for all these posts in one grouped query: postId -> count.
    comment_counts: dict[str, int] = dict(
        session.exec(
            select(Comment.post_id, func.count())
            .where(Comment.post_id.in_(post_ids))
            .group_by(Comment.post_id)
        ).all()
    )

    # Which of these posts the CALLER reacted to, and with what: postId -> {type -> True}.
    viewer_reactions: dict[str, dict[str, bool]] = {}
    for post_id, rtype in session.exec(
        select(Reaction.post_id, Reaction.type)
        .where(Reaction.post_id.in_(post_ids), Reaction.user_id == user.id)
    ).all():
        viewer_reactions.setdefault(post_id, _no_viewer_reactions())[ReactionType(rtype).value] = True

    # Assemble each post's response from the batched lookups (falling back to the zero/empty shapes
    # for a post that has no reactions/comments yet).
    items = []
    for post, track, author in rows:
        out = FeedPostOut(
            id=post.id,
            user_id=post.user_id,
            author=AuthorOut(
                display_name=author.display_name,
                handle=author.handle,
                avatar_url=author.avatar_url,
            ),
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
            reaction_counts=reaction_counts.get(post.id, _zero_counts()),
            comment_count=comment_counts.get(post.id, 0),
            viewer_reactions=viewer_reactions.get(post.id, _no_viewer_reactions()),
        )
        # by_alias=True -> emit camelCase field names (reactionCounts, commentCount, ...).
        items.append((post.created_at, out.model_dump(by_alias=True, mode="json")))
    return items


# The artist behind-the-scenes half of the feed (T049). Same batched, no-N+1 shape as the song half,
# but against ArtistPost + the ArtistReaction/ArtistComment engagement tables (T52). Returns
# (created_at, item) pairs so build_feed can interleave them with the song posts by time.
def _build_artist_items(session: Session, user: User, author_ids: set[str]) -> list[tuple]:
    # The followed artists' posts, joined to their author (the artist User). We reuse author_ids, so
    # only artists the caller follows (or the caller themselves, if they're an artist) appear.
    rows = session.exec(
        select(ArtistPost, User)
        .join(User, User.id == ArtistPost.artist_user_id)
        .where(ArtistPost.artist_user_id.in_(author_ids))
        .order_by(ArtistPost.created_at.desc())
    ).all()
    if not rows:
        return []

    post_ids = [post.id for post, _ in rows]

    # Reaction counts for all these artist posts in one grouped query: (postId, type) -> count.
    reaction_counts: dict[str, dict[str, int]] = {}
    for post_id, rtype, n in session.exec(
        select(ArtistReaction.artist_post_id, ArtistReaction.type, func.count())
        .where(ArtistReaction.artist_post_id.in_(post_ids))
        .group_by(ArtistReaction.artist_post_id, ArtistReaction.type)
    ).all():
        reaction_counts.setdefault(post_id, _zero_counts())[ReactionType(rtype).value] = n

    # Comment counts for all these artist posts in one grouped query: postId -> count.
    comment_counts: dict[str, int] = dict(
        session.exec(
            select(ArtistComment.artist_post_id, func.count())
            .where(ArtistComment.artist_post_id.in_(post_ids))
            .group_by(ArtistComment.artist_post_id)
        ).all()
    )

    # Which of these artist posts the CALLER reacted to, and with what: postId -> {type -> True}.
    viewer_reactions: dict[str, dict[str, bool]] = {}
    for post_id, rtype in session.exec(
        select(ArtistReaction.artist_post_id, ArtistReaction.type)
        .where(ArtistReaction.artist_post_id.in_(post_ids), ArtistReaction.user_id == user.id)
    ).all():
        viewer_reactions.setdefault(post_id, _no_viewer_reactions())[ReactionType(rtype).value] = True

    items = []
    for post, author in rows:
        # The image is stored as a bare path in the PRIVATE artist-images bucket, so sign a
        # short-lived read URL (T53) before it reaches the browser.
        out = ArtistFeedPostOut(
            id=post.id,
            author=AuthorOut(
                display_name=author.display_name,
                handle=author.handle,
                avatar_url=author.avatar_url,
            ),
            caption=post.caption,
            image_url=create_signed_read_url(ARTIST_IMAGE_BUCKET, post.image_url),
            created_at=post.created_at,
            reaction_counts=reaction_counts.get(post.id, _zero_counts()),
            comment_count=comment_counts.get(post.id, 0),
            viewer_reactions=viewer_reactions.get(post.id, _no_viewer_reactions()),
        )
        items.append((post.created_at, out.model_dump(by_alias=True, mode="json")))
    return items
