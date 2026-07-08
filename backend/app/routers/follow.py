# WHAT THIS FILE IS
# The follow endpoints — the "who sees whose posts" graph behind the feed (T13):
#   POST   /api/follow/{userId} -> the caller starts following that user (idempotent)
#   DELETE /api/follow/{userId} -> the caller stops following that user
# Both require a login. A Follow row means "follower_id follows following_id"; the feed
# (app/routers/feed.py) reads these edges to decide whose posts to show. Satisfies BE-4.

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.deps import require_user
from app.models import Follow, User
from app.rate_limit import enforce_rate_limit
from app.responses import fail, ok
from app.schemas import FollowStateOut

# The per-user cap on follow writes: at most FOLLOW_RATE_LIMIT follow/unfollow actions per window
# (ADR-0011). One shared "follow" action covers both verbs, so rapidly follow/unfollow toggling
# (the abuse pattern) is what the cap counts. Module-level names so tests can lower them.
FOLLOW_RATE_LIMIT = 30
FOLLOW_RATE_WINDOW_SECONDS = 60

# prefix=/api/follow so both verbs hang off a target user id; tags group them in the API docs.
router = APIRouter(prefix="/api/follow", tags=["follow"])


# Build the standard follow-state response (camelCase JSON, ADR-0012). `following` is where the
# caller ends up: true after a follow, false after an unfollow. `status` differs per verb.
def _state_response(following_id: str, following: bool, status: int):
    out = FollowStateOut(following_id=following_id, following=following)
    return ok(out.model_dump(by_alias=True, mode="json"), status=status)


# Both verbs apply the same per-user follow cap; factored here so the limit is defined once.
def _enforce_follow_cap(session: Session, user: User) -> None:
    enforce_rate_limit(
        session,
        subject=user.id,
        action="follow",
        limit=FOLLOW_RATE_LIMIT,
        window_seconds=FOLLOW_RATE_WINDOW_SECONDS,
    )


@router.post("/{user_id}")
def follow_user(
    user_id: str,
    user: User = Depends(require_user),   # ensures the caller is logged in; gives us their record
    session: Session = Depends(get_session),
):
    # Abuse guard first: refuse (429) if this user has followed too many times recently.
    _enforce_follow_cap(session, user)

    # You can't follow yourself. Checking the ids up front returns a clean 400.
    if user_id == user.id:
        return fail("cannot follow yourself", 400)

    # The target must exist. Checking here returns a clean 404 instead of letting the insert fail
    # on the foreign key (which would surface as a 500).
    if session.get(User, user_id) is None:
        return fail("user not found", 404)

    # Idempotent follow: the Follow table's composite primary key (follower_id, following_id) means
    # one edge per pair. If the edge already exists, following again is a no-op — not an error — so
    # a double-tap doesn't 500 on the unique constraint. The follower is ALWAYS the authenticated
    # caller, never client-supplied, so it can't be spoofed.
    if session.get(Follow, (user.id, user_id)) is None:
        session.add(Follow(follower_id=user.id, following_id=user_id))
        session.commit()

    return _state_response(user_id, following=True, status=201)


@router.delete("/{user_id}")
def unfollow_user(
    user_id: str,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    _enforce_follow_cap(session, user)

    # Remove only the CALLER'S own edge (keyed by their id as follower). Removing one that isn't
    # there is a harmless no-op, so unfollowing someone you don't follow still succeeds.
    edge = session.get(Follow, (user.id, user_id))
    if edge is not None:
        session.delete(edge)
        session.commit()

    return _state_response(user_id, following=False, status=200)
