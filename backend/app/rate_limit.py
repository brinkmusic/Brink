# WHAT THIS FILE IS
# The one place that enforces "you can't do this action too many times too fast" (a
# per-user cap on write endpoints, required by ADR-0007). Any endpoint that needs a limit
# calls enforce_rate_limit(); nothing else knows HOW the limit is tracked.
#
# HOW IT WORKS: we keep a row in the RateLimitHit table every time a limited action happens.
# To check the limit we count how many rows exist for this (subject, action) within the last
# `window_seconds`; if that count has reached `limit`, we refuse. Otherwise we record a new
# hit and allow it.
#
# WHY IT'S ALL IN THIS ONE FILE (the "swappable seam"): a real production app would keep
# these counts in Redis (an in-memory store) for speed, not in the main database. Because
# every endpoint only ever calls enforce_rate_limit(), swapping to Redis later means
# rewriting THIS FILE and nothing else. See ADR-0011.

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import RateLimitHit


# Raised when the cap is hit. Carries HTTP 429 ("Too Many Requests"); an app-wide handler
# in main.py turns it into our standard { "error": ... } envelope, like AuthError does.
class RateLimitError(Exception):
    def __init__(self, message: str = "rate limit exceeded", status: int = 429):
        super().__init__(message)
        self.message = message
        self.status = status


def enforce_rate_limit(
    session: Session,
    *,
    subject: str,
    action: str,
    limit: int,
    window_seconds: int,
) -> None:
    # The oldest moment that still counts as "recent". We store timestamps as naive UTC
    # (no timezone attached) to match how the rest of the app saves times, so we compare
    # against a naive-UTC cutoff here too.
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=window_seconds)

    # Count this subject's recent hits for this action. func.count() = the SQL COUNT(*).
    recent = session.exec(
        select(func.count())
        .select_from(RateLimitHit)
        .where(
            RateLimitHit.subject == subject,
            RateLimitHit.action == action,
            RateLimitHit.created_at > cutoff,
        )
    ).one()

    if recent >= limit:
        raise RateLimitError()

    # Under the cap: record this hit and allow the action to proceed.
    session.add(RateLimitHit(subject=subject, action=action))
    session.commit()
