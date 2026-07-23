# WHAT THIS FILE IS
# The artist "behind-the-scenes" (BTS) endpoints — an artist account's promo posts (T50) plus the
# engagement on them (T52):
#   POST   /api/artist/sign-upload            -> mint a Supabase Storage signed upload URL (T50)
#   POST   /api/artist/posts                  -> create an ArtistPost (T50)
#   POST/DELETE /api/artist/posts/{id}/reactions -> react to an artist post / remove it (T52)
#   POST/GET    /api/artist/posts/{id}/comments  -> comment on an artist post / list them (T52)
#   GET    /api/artist/posts/{id}/engagement  -> the OWNING artist reads its engagement (T52)
#
# AUTHORIZATION (ADR-0007/ADR-0008). The two T50 routes are login-gated AND artist-only — the caller
# must be an artist account (User.isArtist == true), and the artist is ALWAYS the authenticated
# caller (never from the body), so it can't be spoofed. The T52 engagement is asymmetric (MEDIA-4):
# ANY logged-in user may react/comment on an artist post (that's the audience engaging), but the
# `engagement` summary is OWNER-ONLY — only the artist who made the post may read its numbers.
# There is NO content moderation (ADR-0008) — only the technical checks the request schemas enforce.

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from app.db import get_session
from app.deps import AuthError, require_user
from app.models import (
    ArtistComment,
    ArtistPost,
    ArtistReaction,
    ReactionType,
    User,
)
from app.rate_limit import enforce_rate_limit
from app.responses import fail, ok
from app.schemas import (
    ArtistEngagementOut,
    ArtistPostOut,
    AuthorOut,
    CommentBody,
    CommentOut,
    CreateArtistPostBody,
    ReactionBody,
    ReactionCountsOut,
    SignUploadBody,
    SignUploadOut,
)
from app.security.supabase import create_signed_upload_url

# The private Supabase Storage bucket that holds artist promo images (created manually by Andrea —
# see the ticket's "Manual (user)" step). "Private" means objects aren't publicly readable; uploads
# go through the short-lived signed URL minted below.
UPLOAD_BUCKET = "artist-images"

# Map each allowed image MIME type to the file extension we give the stored object. The request
# schema already guarantees content_type is one of these two, so this lookup can't miss.
_EXTENSION = {"image/jpeg": "jpg", "image/png": "png"}

# prefix=... puts every route below under /api/artist; tags=... groups them in the API docs.
router = APIRouter(prefix="/api/artist", tags=["artist"])


def _require_artist(user: User) -> None:
    # The artist-only gate. A logged-in but non-artist account (isArtist == false, the default for
    # normal listeners) is refused with 403 Forbidden — it's authenticated, just not allowed here.
    # Raising AuthError(status=403) reuses the app-wide handler that emits our { "error": ... }
    # envelope, so the response shape matches every other error.
    if not user.is_artist:
        raise AuthError("artist account required", status=403)


@router.post("/sign-upload")
def sign_upload(
    body: SignUploadBody,
    user: User = Depends(require_user),   # ensures the caller is logged in; gives us their record
):
    # No DB access here — this route only mints a storage URL — so it takes no session dependency.
    _require_artist(user)

    # Build the object path INSIDE the caller's own folder: "<artistUserId>/<random>.<ext>". WHY
    # namespace by the caller's id: it keeps each artist's uploads separate and means the signed
    # permission we mint can only ever target this artist's own space. uuid4 is a random,
    # collision-free name so two uploads never clash.
    extension = _EXTENSION[body.content_type]
    path = f"{user.id}/{uuid.uuid4().hex}.{extension}"

    # Ask Supabase (as the server, holding the service-role key) to sign a one-time upload URL for
    # exactly that path. The browser then uploads the file straight to storage with it.
    signed = create_signed_upload_url(UPLOAD_BUCKET, path)

    out = SignUploadOut(
        path=signed["path"],
        signed_url=signed["signed_url"],
        token=signed["token"],
    )
    return ok(out.model_dump(by_alias=True, mode="json"))


@router.post("/posts")
def create_artist_post(
    body: CreateArtistPostBody,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    _require_artist(user)

    # An artist post must carry SOMETHING (T104): a photo or some text. Trim the caption so a
    # whitespace-only one doesn't count as text. Neither a photo nor real text → 400, matching the
    # "you can't post nothing" rule the upload box enforces in the UI.
    caption = body.caption.strip() if body.caption else None
    if not body.image_url and not caption:
        return fail("a post needs a photo or some text", 400)

    # The author is ALWAYS the authenticated artist — never read from the body, so it can't be
    # spoofed. image_url/caption/linked_track_id come from the (already validated) request; either
    # image_url or caption may be None now (photo-only or text-only).
    post = ArtistPost(
        artist_user_id=user.id,
        image_url=body.image_url,
        caption=caption,
        linked_track_id=body.linked_track_id,
    )
    session.add(post)
    session.commit()
    session.refresh(post)

    out = ArtistPostOut(
        id=post.id,
        artist_user_id=post.artist_user_id,
        image_url=post.image_url,
        caption=post.caption,
        linked_track_id=post.linked_track_id,
        created_at=post.created_at,
    )
    # 201 Created is the standard "a new thing was made" status.
    return ok(out.model_dump(by_alias=True, mode="json"), status=201)


# =============================================================================
# T52 — engagement on artist posts (reactions, comments, owner-only summary).
# These mirror the regular-post reactions (T11) and comments (T12) endpoints, but against the
# separate ArtistReaction / ArtistComment tables (an FK points at one table, and ArtistPost is
# not Post). The per-user abuse caps reuse the shared rate-limit helper (ADR-0011) with their own
# action names so artist-post engagement is throttled independently of regular posts.
# =============================================================================

# Per-user caps, same shape as the T11/T12 caps. Module-level so tests can lower them.
ARTIST_REACTION_RATE_LIMIT = 30
ARTIST_COMMENT_RATE_LIMIT = 20
ARTIST_ENGAGEMENT_RATE_WINDOW_SECONDS = 60


# Count an artist post's reactions grouped by type, ALWAYS returning an entry for every type
# (zeros included) so the response shape never varies. Mirrors reactions._counts_for_post.
def _artist_reaction_counts(session: Session, post_id: str) -> dict[str, int]:
    rows = session.exec(
        select(ArtistReaction.type, func.count())
        .where(ArtistReaction.artist_post_id == post_id)
        .group_by(ArtistReaction.type)
    ).all()
    counts = {rt.value: 0 for rt in ReactionType}
    for rtype, n in rows:
        counts[ReactionType(rtype).value] = n
    return counts


# Build the standard counts response (camelCase, ADR-0012). `status` is 201 for add, 200 for remove.
def _artist_counts_response(session: Session, post_id: str, status: int):
    out = ReactionCountsOut(post_id=post_id, counts=_artist_reaction_counts(session, post_id))
    return ok(out.model_dump(by_alias=True, mode="json"), status=status)


# Look up THIS caller's reaction of a given type on an artist post (or None). Filtering on user_id
# is what makes it impossible to touch anyone else's reaction.
def _find_own_artist_reaction(session: Session, post_id: str, user_id: str, rtype: ReactionType):
    return session.exec(
        select(ArtistReaction).where(
            ArtistReaction.artist_post_id == post_id,
            ArtistReaction.user_id == user_id,
            ArtistReaction.type == rtype,
        )
    ).first()


@router.post("/posts/{post_id}/reactions")
def add_artist_reaction(
    post_id: str,
    body: ReactionBody,
    user: User = Depends(require_user),   # login required — but NOT artist-only; anyone may react
    session: Session = Depends(get_session),
):
    enforce_rate_limit(
        session,
        subject=user.id,
        action="artist_reaction",
        limit=ARTIST_REACTION_RATE_LIMIT,
        window_seconds=ARTIST_ENGAGEMENT_RATE_WINDOW_SECONDS,
    )

    # The post must exist — a clean 404 instead of a foreign-key 500 on insert.
    if session.get(ArtistPost, post_id) is None:
        return fail("artist post not found", 404)

    # Idempotent add: one reaction per (post, user, type). A double-tap is a no-op, not a 500 on the
    # unique constraint. The reactor is ALWAYS the authenticated user, never client-supplied.
    if _find_own_artist_reaction(session, post_id, user.id, body.type) is None:
        session.add(ArtistReaction(artist_post_id=post_id, user_id=user.id, type=body.type))
        session.commit()

    return _artist_counts_response(session, post_id, status=201)


@router.delete("/posts/{post_id}/reactions")
def remove_artist_reaction(
    post_id: str,
    body: ReactionBody,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    enforce_rate_limit(
        session,
        subject=user.id,
        action="artist_reaction",
        limit=ARTIST_REACTION_RATE_LIMIT,
        window_seconds=ARTIST_ENGAGEMENT_RATE_WINDOW_SECONDS,
    )

    if session.get(ArtistPost, post_id) is None:
        return fail("artist post not found", 404)

    # Remove only the CALLER'S own reaction of this type. Removing one that isn't there is a no-op.
    existing = _find_own_artist_reaction(session, post_id, user.id, body.type)
    if existing is not None:
        session.delete(existing)
        session.commit()

    return _artist_counts_response(session, post_id, status=200)


# Build the API response for one artist-post comment + its author. Mirrors comments._to_comment_out
# and reuses the SAME CommentOut/AuthorOut shapes, so a comment renders identically on either post.
def _to_artist_comment_out(comment: ArtistComment, author: User) -> dict:
    out = CommentOut(
        id=comment.id,
        body=comment.body,
        created_at=comment.created_at,
        author=AuthorOut(
            display_name=author.display_name,
            handle=author.handle,
            avatar_url=author.avatar_url,
        ),
    )
    return out.model_dump(by_alias=True, mode="json")


@router.post("/posts/{post_id}/comments")
def create_artist_comment(
    post_id: str,
    body: CommentBody,   # validated (non-empty after trim, <= 2000) before we get here
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    enforce_rate_limit(
        session,
        subject=user.id,
        action="artist_comment_create",
        limit=ARTIST_COMMENT_RATE_LIMIT,
        window_seconds=ARTIST_ENGAGEMENT_RATE_WINDOW_SECONDS,
    )

    if session.get(ArtistPost, post_id) is None:
        return fail("artist post not found", 404)

    # The author is ALWAYS the authenticated user — never from the body. `body.body` is trimmed.
    comment = ArtistComment(artist_post_id=post_id, user_id=user.id, body=body.body)
    session.add(comment)
    session.commit()
    session.refresh(comment)  # loads the database-filled createdAt

    return ok(_to_artist_comment_out(comment, user), status=201)


@router.get("/posts/{post_id}/comments")
def list_artist_comments(
    post_id: str,
    user: User = Depends(require_user),   # listing requires a login too (private app)
    session: Session = Depends(get_session),
):
    if session.get(ArtistPost, post_id) is None:
        return fail("artist post not found", 404)

    # Join each comment to its author, newest-first.
    rows = session.exec(
        select(ArtistComment, User)
        .join(User, User.id == ArtistComment.user_id)
        .where(ArtistComment.artist_post_id == post_id)
        .order_by(ArtistComment.created_at.desc())
    ).all()
    return ok([_to_artist_comment_out(comment, author) for comment, author in rows])


@router.get("/posts/{post_id}/engagement")
def get_artist_post_engagement(
    post_id: str,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    # OWNER-ONLY (MEDIA-4): only the artist who made the post may read its engagement. We load the
    # post first so a missing one is a clean 404, and a real one owned by someone else is a 403.
    post = session.get(ArtistPost, post_id)
    if post is None:
        return fail("artist post not found", 404)
    if post.artist_user_id != user.id:
        # Authenticated but not the owner — reuse the app-wide 403 envelope, same as _require_artist.
        raise AuthError("not your post", status=403)

    # One grouped query for reactions, one count for comments — no per-row loops.
    comment_count = session.exec(
        select(func.count()).select_from(ArtistComment).where(
            ArtistComment.artist_post_id == post_id
        )
    ).one()

    out = ArtistEngagementOut(
        post_id=post_id,
        reaction_counts=_artist_reaction_counts(session, post_id),
        comment_count=comment_count,
    )
    return ok(out.model_dump(by_alias=True, mode="json"))
