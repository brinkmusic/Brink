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
from sqlalchemy import func, tuple_
from sqlmodel import Session, select

from app.db import get_session
from app.deps import require_user
from app.models import (
    ArtistComment,
    ArtistPost,
    ArtistReaction,
    Comment,
    Follow,
    Play,
    Post,
    Reaction,
    ReactionType,
    Track,
    User,
)
from app.responses import ok
from app.schemas import ArtistFeedPostOut, AuthorOut, CommentOut, FeedPostOut, TrackOut
from app.security.supabase import create_signed_read_url_or_blank

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


# How many of a post's newest comments the feed shows inline on the card (T95). The rest stay
# behind the existing "💬" panel, which loads the full list from the comments API.
LATEST_COMMENTS_CAP = 3


# The newest comments for a batch of posts, in ONE query (no N+1): postId -> up to CAP
# CommentOut DTOs, chronological within each post's subset (oldest of the shown ones first —
# the Instagram reading order, so the newest sits closest to the comment box).
#
# WHY the generic (comment_model, post_id_attr) parameters: song posts and artist posts store
# their comments in mirrored tables (Comment.post_id vs ArtistComment.artist_post_id — a foreign
# key can only point at one table, see models.py), so the same logic runs against either table.
# getattr(x, "name") is Python for "read the attribute called name" — it lets one function work
# with both column names.
def _latest_comments(session: Session, comment_model, post_id_attr: str, post_ids) -> dict[str, list[CommentOut]]:
    id_column = getattr(comment_model, post_id_attr)
    rows = session.exec(
        select(comment_model, User)
        .join(User, User.id == comment_model.user_id)
        .where(id_column.in_(post_ids))
        .order_by(comment_model.created_at.desc())
    ).all()

    # Walk newest-first and keep only the first CAP per post, building the same CommentOut DTO
    # the comments API returns (ADR-0012: an explicit allow-list, never the raw rows).
    latest: dict[str, list[CommentOut]] = {}
    for comment, author in rows:
        bucket = latest.setdefault(getattr(comment, post_id_attr), [])
        if len(bucket) < LATEST_COMMENTS_CAP:
            bucket.append(CommentOut(
                id=comment.id,
                body=comment.body,
                created_at=comment.created_at,
                author=AuthorOut(
                    display_name=author.display_name,
                    handle=author.handle,
                    avatar_url=author.avatar_url,
                ),
            ))
    # Flip each post's kept comments from newest-first to chronological for display.
    for bucket in latest.values():
        bucket.reverse()
    return latest


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
        # LEFT (outer) join to Track so TEXT-ONLY posts (no track, T104) still appear — an INNER
        # join would silently drop them. `track` is None for those rows.
        .join(Track, Track.spotify_id == Post.track_id, isouter=True)
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

    # The newest few comments per post, shown inline on the card (T95) — one batched query.
    latest_comments = _latest_comments(session, Comment, "post_id", post_ids)

    # How many times each post's AUTHOR has played the track THEY shared (T102) — the "played N
    # times by {author}" endorsement line. One grouped query over Play for the EXACT (author, track)
    # pairs in this batch (no N+1). tuple_(a, b).in_([...]) is a row-value IN — "(userId, trackId) is
    # one of these pairs" — and works on both Postgres and the SQLite test DB. We match on the pair
    # (not just author, not just track) so a post only ever counts the author's plays of that one
    # track. Missing pair -> 0 via the .get default below.
    # Only song posts have a track to count plays for — skip TEXT-ONLY posts (track_id is None, T104).
    author_track_pairs = {
        (post.user_id, post.track_id) for post, _, _ in rows if post.track_id is not None
    }
    play_counts: dict[tuple, int] = {}
    if author_track_pairs:
        for uid, tid, n in session.exec(
            select(Play.user_id, Play.track_id, func.count())
            .where(tuple_(Play.user_id, Play.track_id).in_(list(author_track_pairs)))
            .group_by(Play.user_id, Play.track_id)
        ).all():
            play_counts[(uid, tid)] = n

    # Each post's MOST RECENT reactor (T96) — backs the "Liked by X and N others" line. One
    # batched query: every reaction on these posts joined to its reactor, newest first; the
    # first row we see per post wins (dict "not in" check), so it's their newest reactor.
    liked_by: dict[str, AuthorOut] = {}
    for post_id, display_name, handle, avatar_url in session.exec(
        select(Reaction.post_id, User.display_name, User.handle, User.avatar_url)
        .join(User, User.id == Reaction.user_id)
        .where(Reaction.post_id.in_(post_ids))
        .order_by(Reaction.created_at.desc())
    ).all():
        if post_id not in liked_by:
            liked_by[post_id] = AuthorOut(
                display_name=display_name, handle=handle, avatar_url=avatar_url
            )

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
            # None for a TEXT-ONLY post (T104) → the card renders a note instead of a song row.
            track=TrackOut(
                spotify_id=track.spotify_id,
                title=track.title,
                artist_name=track.artist_name,
                album_art_url=track.album_art_url,
                popularity=track.popularity,
            ) if track is not None else None,
            reaction_counts=reaction_counts.get(post.id, _zero_counts()),
            comment_count=comment_counts.get(post.id, 0),
            viewer_reactions=viewer_reactions.get(post.id, _no_viewer_reactions()),
            latest_comments=latest_comments.get(post.id, []),
            liked_by=liked_by.get(post.id),  # None when the post has no reactions (T96)
            # The author's own play count for this track (T102); 0 when they've never played it, and
            # always 0 for a text-only post (no track_id → the key can't match).
            author_play_count=play_counts.get((post.user_id, post.track_id), 0),
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

    # The newest few comments per artist post, shown inline on the card (T95) — the same
    # batched helper as the song half, run against the mirrored ArtistComment table.
    latest_comments = _latest_comments(session, ArtistComment, "artist_post_id", post_ids)

    items = []
    for post, author in rows:
        # image_url is TRI-STATE (T104): None for a TEXT-ONLY post (no photo → the card renders a
        # note), otherwise the signed read URL. For posts that DO have a photo, the image is stored
        # as a bare path in the PRIVATE artist-images bucket, so we sign a short-lived read URL (T53)
        # before it reaches the browser; resilient signing (T103) returns "" on failure so one
        # un-signable image can't blank the whole feed — the card shows a placeholder for that "".
        image_url = (
            create_signed_read_url_or_blank(ARTIST_IMAGE_BUCKET, post.image_url)
            if post.image_url
            else None
        )
        out = ArtistFeedPostOut(
            id=post.id,
            author=AuthorOut(
                display_name=author.display_name,
                handle=author.handle,
                avatar_url=author.avatar_url,
            ),
            caption=post.caption,
            image_url=image_url,
            created_at=post.created_at,
            reaction_counts=reaction_counts.get(post.id, _zero_counts()),
            comment_count=comment_counts.get(post.id, 0),
            viewer_reactions=viewer_reactions.get(post.id, _no_viewer_reactions()),
            latest_comments=latest_comments.get(post.id, []),
        )
        items.append((post.created_at, out.model_dump(by_alias=True, mode="json")))
    return items
