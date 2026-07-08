# WHAT THIS FILE IS
# The reactions endpoints — the lightest social signal on a post (T11):
#   POST   /api/posts/{id}/reactions -> add the caller's reaction of a given type (idempotent)
#   DELETE /api/posts/{id}/reactions -> remove the caller's reaction of that type
# Both return the post's fresh per-type reaction counts. Reactions feed the engagement numbers
# the feed (T41) and artist-engagement views (T52) show.

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from app.db import get_session
from app.deps import require_user
from app.models import Post, Reaction, ReactionType, User
from app.rate_limit import enforce_rate_limit
from app.responses import fail, ok
from app.schemas import ReactionBody, ReactionCountsOut

# The per-user cap on reaction writes: at most REACTION_RATE_LIMIT add/remove actions per
# window (ADR-0011). One shared "reaction" action covers both verbs, so rapidly toggling a
# reaction on and off (the real abuse pattern) is what the cap counts. Module-level names so
# they read clearly and tests can lower them.
REACTION_RATE_LIMIT = 30
REACTION_RATE_WINDOW_SECONDS = 60

# prefix=/api/posts so both routes hang off a post; tags just group them in the API docs.
router = APIRouter(prefix="/api/posts", tags=["reactions"])


# Count this post's reactions grouped by type, and return a map that ALWAYS has an entry for
# every type (zeros included) so the response shape never varies. Centralized so add and
# remove return the exact same thing.
def _counts_for_post(session: Session, post_id: str) -> dict[str, int]:
    # SQL: SELECT type, COUNT(*) FROM Reaction WHERE postId = ? GROUP BY type.
    rows = session.exec(
        select(Reaction.type, func.count())
        .where(Reaction.post_id == post_id)
        .group_by(Reaction.type)
    ).all()
    counts = {rt.value: 0 for rt in ReactionType}  # start every type at 0
    for rtype, n in rows:
        # rtype comes back as the ReactionType enum member; .value is the plain "HEART" string.
        counts[ReactionType(rtype).value] = n
    return counts


# Build the standard counts response (camelCase JSON, ADR-0012). `status` differs between the
# verbs: 201 for a create, 200 for a delete.
def _counts_response(session: Session, post_id: str, status: int):
    out = ReactionCountsOut(post_id=post_id, counts=_counts_for_post(session, post_id))
    return ok(out.model_dump(by_alias=True, mode="json"), status=status)


# Both verbs apply the same per-user reaction cap; factored here so the limit is defined once.
def _enforce_reaction_cap(session: Session, user: User) -> None:
    enforce_rate_limit(
        session,
        subject=user.id,
        action="reaction",
        limit=REACTION_RATE_LIMIT,
        window_seconds=REACTION_RATE_WINDOW_SECONDS,
    )


# Look up THIS caller's reaction of a given type on a post (or None). Filtering on user_id is
# what makes it impossible to touch anyone else's reaction. Both verbs need this exact query.
def _find_own_reaction(session: Session, post_id: str, user_id: str, rtype: ReactionType):
    return session.exec(
        select(Reaction).where(
            Reaction.post_id == post_id,
            Reaction.user_id == user_id,
            Reaction.type == rtype,
        )
    ).first()


@router.post("/{post_id}/reactions")
def add_reaction(
    post_id: str,
    body: ReactionBody,
    user: User = Depends(require_user),   # ensures the caller is logged in; gives us their record
    session: Session = Depends(get_session),
):
    # Abuse guard first: refuse (429) if this user has reacted too many times recently.
    _enforce_reaction_cap(session, user)

    # The post must exist. Checking here returns a clean 404 instead of letting the insert
    # fail on the foreign key (which would surface as a 500).
    if session.get(Post, post_id) is None:
        return fail("post not found", 404)

    # Idempotent add: one reaction per (post, user, type). If this exact reaction already
    # exists, adding again is a no-op — not an error — so a double-tap doesn't 500 on the
    # unique constraint. The reactor is ALWAYS the authenticated user, never client-supplied.
    existing = _find_own_reaction(session, post_id, user.id, body.type)
    if existing is None:
        session.add(Reaction(post_id=post_id, user_id=user.id, type=body.type))
        session.commit()

    return _counts_response(session, post_id, status=201)


@router.delete("/{post_id}/reactions")
def remove_reaction(
    post_id: str,
    body: ReactionBody,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    _enforce_reaction_cap(session, user)

    if session.get(Post, post_id) is None:
        return fail("post not found", 404)

    # Remove only the CALLER'S own reaction of this type (the filter on user_id makes it
    # impossible to delete someone else's). Removing one that isn't there is a no-op.
    existing = _find_own_reaction(session, post_id, user.id, body.type)
    if existing is not None:
        session.delete(existing)
        session.commit()

    return _counts_response(session, post_id, status=200)
