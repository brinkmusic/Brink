# WHAT THIS FILE IS
# The feed endpoint — the app's home surface (T13):
#   GET /api/feed -> posts from the people the caller follows PLUS the caller's own posts,
#                    newest-first, each with its track, per-type reaction counts, a comment
#                    count, and which reactions the CALLER left. Login required (private app).
# It reads the follow graph from app/routers/follow.py and the posts/reactions/comments created by
# T10–T12. Satisfies BE-7.
#
# WHY the query is written in batches: a naive version would loop over each post and run a
# separate count query per post ("N+1 queries") — slow as the feed grows. Instead we fetch the
# posts once, then fetch ALL their reaction counts, comment counts, and the viewer's reactions in
# one grouped query each (four queries total, no matter how many posts).

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from app.db import get_session
from app.deps import require_user
from app.models import Comment, Follow, Post, Reaction, ReactionType, Track, User
from app.responses import ok
from app.schemas import AuthorOut, FeedPostOut, TrackOut

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


# Build the feed as a list of plain dicts (camelCase, ready for JSON or an HTML template): posts
# from everyone `user` follows plus their own, newest-first, each with its track, author, per-type
# reaction counts, comment count, and which reactions `user` left. Shared by the JSON endpoint
# above and the feed page — the single source of truth for "what's in the feed".
def build_feed(session: Session, user: User) -> list[dict]:
    # Whose posts to show: everyone the caller follows, plus the caller themselves (so a brand-new
    # user with no follows still sees their own posts).
    followee_ids = session.exec(
        select(Follow.following_id).where(Follow.follower_id == user.id)
    ).all()
    author_ids = set(followee_ids) | {user.id}

    # The posts themselves, joined to their track and their author (the User who posted), newest
    # -first. Joining the author here avoids a separate lookup per post when we build the response.
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
    data = []
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
        data.append(out.model_dump(by_alias=True, mode="json"))
    return data
