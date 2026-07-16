# WHAT THIS FILE IS
# The user-search endpoint (T15): GET /api/users/search?q=<text> -> Brink users whose handle or
# display name contains the query, so someone can FIND a person to follow. WHY it exists: the follow
# feature (T13) shipped with no way to discover users — the only path to a profile was clicking a
# feed author, but your feed only shows people you already follow, so a new user could never find
# anyone. This is the missing "search box" backend the T46 UI will render as links to /u/{handle}.
#
# WHY its own router (not folded into routers/search.py): that file searches SPOTIFY TRACKS, a
# totally different data source; and T16 will add follower/following-list endpoints for users, which
# belong next to this. Keeping user-facing lookups here keeps each router about one thing.
#
# Login is required (Brink is private, so search can't be scraped anonymously) and the call is
# rate-limited like every social endpoint (ADR-0011), keyed on the searching user.

from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from app.db import get_session
from app.deps import require_user
from app.models import User
from app.rate_limit import enforce_rate_limit
from app.responses import fail, ok
from app.schemas import UserSearchOut

# Per-user cap on user searches (ADR-0011). Like the catalog search, a search box fires often (one
# per keystroke burst), so we bound it. Module-level so a test can lower it to force the limit.
USER_SEARCH_RATE_LIMIT = 30
USER_SEARCH_RATE_WINDOW_SECONDS = 60

# The most results we ever return. A small cap keeps the response light and stops a broad query
# (e.g. a single common letter) from dumping the whole user table (per the ticket: "cap 20").
MAX_RESULTS = 20

router = APIRouter(tags=["users"])


@router.get("/api/users/search")
def search_users(
    # `q` is the search text. WHY min_length=2 (not 1): a single character matches almost every
    # user, which is a near-useless result and a needlessly large payload; two characters is still
    # permissive but meaningfully narrows the match. A missing/blank/too-short value fails
    # validation, which the app's handler turns into a clean 400 (ADR-0007). max_length guards
    # against absurd queries.
    q: str = Query(..., min_length=2, max_length=100),
    user: User = Depends(require_user),   # login required (private app); also the rate-limit subject
    session: Session = Depends(get_session),
):
    # Query()'s min_length runs BEFORE trimming, so a value like "  " (two spaces) would slip
    # past it. Trim here and re-check, returning the same clean 400 envelope, so an all-whitespace
    # query is rejected exactly like an empty one.
    q = q.strip()
    if len(q) < 2:
        return fail("q must be at least 2 characters", 400)

    # Cap per user before the query (ADR-0007 §5).
    enforce_rate_limit(
        session,
        subject=user.id,
        action="user_search",
        limit=USER_SEARCH_RATE_LIMIT,
        window_seconds=USER_SEARCH_RATE_WINDOW_SECONDS,
    )

    # Wrap the query in %...% so it matches the text ANYWHERE in the value (a substring), not just at
    # the start. `.ilike()` is a case-insensitive LIKE — on Postgres it becomes ILIKE, and on the
    # SQLite test DB it is case-insensitive for ASCII too, so the same code works in both places.
    # We escape the SQL wildcards (%, _) in the user's text so a query like "50%" is treated as
    # literal characters, not "match anything".
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    pattern = f"%{escaped}%"

    # Match against handle OR display name, ordered by handle for a stable list, capped at MAX_RESULTS.
    rows = session.exec(
        select(User)
        .where(
            User.handle.ilike(pattern, escape="\\")
            | User.display_name.ilike(pattern, escape="\\")
        )
        .order_by(User.handle)
        .limit(MAX_RESULTS)
    ).all()

    # Shape each row into the small camelCase DTO (ADR-0012) — never the raw User row.
    results = [
        UserSearchOut(
            id=u.id,
            handle=u.handle,
            display_name=u.display_name,
            is_artist=u.is_artist,
        ).model_dump(by_alias=True, mode="json")
        for u in rows
    ]
    return ok(results)
