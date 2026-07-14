# WHAT THIS FILE IS
# The comments endpoints — the threaded (heavier-than-a-reaction) social signal on a post (T12):
#   POST /api/posts/{id}/comments -> add the caller's comment, login required
#   GET  /api/posts/{id}/comments -> list the post's comments newest-first, each with its author
# Both require a login (Brink is a private app). Comments back the comment UI (T42) and the
# per-post engagement counts.

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.db import get_session
from app.deps import require_user
from app.models import Comment, Post, User
from app.rate_limit import enforce_rate_limit
from app.responses import fail, ok
from app.schemas import AuthorOut, CommentBody, CommentOut

# The per-user cap on creating comments: at most COMMENT_RATE_LIMIT per window (ADR-0011).
# Module-level names so they read clearly and tests can lower them.
COMMENT_RATE_LIMIT = 20
COMMENT_RATE_WINDOW_SECONDS = 60

# prefix=/api/posts so both routes hang off a post; tags just group them in the API docs.
router = APIRouter(prefix="/api/posts", tags=["comments"])


# Build the API response for one comment + its author. Centralized so create and list return
# the exact same fields (ADR-0012: never return the raw table row — that would leak the
# author's email and internal ids).
def _to_comment_out(comment: Comment, author: User) -> dict:
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
    # by_alias=True -> emit camelCase field names (displayName, avatarUrl, createdAt).
    return out.model_dump(by_alias=True, mode="json")


@router.post("/{post_id}/comments")
def create_comment(
    post_id: str,
    body: CommentBody,   # body is validated (non-empty after trim, <=2000) before we get here
    user: User = Depends(require_user),   # ensures the caller is logged in; gives us their record
    session: Session = Depends(get_session),
):
    # Abuse guard first: refuse (429) if this user has commented too many times recently.
    enforce_rate_limit(
        session,
        subject=user.id,
        action="comment_create",
        limit=COMMENT_RATE_LIMIT,
        window_seconds=COMMENT_RATE_WINDOW_SECONDS,
    )

    # The post must exist. Checking here returns a clean 404 instead of letting the insert
    # fail on the foreign key (which would surface as a 500).
    if session.get(Post, post_id) is None:
        return fail("post not found", 404)

    # The author is ALWAYS the authenticated user — never taken from the request body, so it
    # can't be spoofed. `body.body` is already trimmed by the schema.
    comment = Comment(post_id=post_id, user_id=user.id, body=body.body)
    session.add(comment)
    session.commit()
    session.refresh(comment)  # loads the database-filled createdAt

    # 201 Created; the author is the caller, so we can build the response without a re-query.
    return ok(_to_comment_out(comment, user), status=201)


@router.get("/{post_id}/comments")
def list_comments(
    post_id: str,
    user: User = Depends(require_user),   # listing requires a login too (private app)
    session: Session = Depends(get_session),
):
    if session.get(Post, post_id) is None:
        return fail("post not found", 404)

    # Join each comment to its author so the response includes who wrote it, newest-first.
    rows = session.exec(
        select(Comment, User)
        .join(User, User.id == Comment.user_id)
        .where(Comment.post_id == post_id)
        .order_by(Comment.created_at.desc())
    ).all()
    return ok([_to_comment_out(comment, author) for comment, author in rows])
