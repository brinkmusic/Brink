# WHAT THIS FILE IS
# Checks the reusable rate-limit helper (app/rate_limit.py): it counts how many times a
# subject has done an action recently and refuses (raises RateLimitError -> 429) once the
# cap is hit. Uses a real in-memory SQLite database because the helper's whole job is to
# count real rows in a real table — a MagicMock can't verify counting.

import pytest

from app.rate_limit import RateLimitError, enforce_rate_limit


# Calls under the cap are allowed and each one records a hit.
def test_under_limit_is_allowed_and_records_hits(db_session):
    for _ in range(3):
        enforce_rate_limit(db_session, subject="u1", action="post_create", limit=5, window_seconds=60)
    # 3 hits recorded, still under the cap of 5 — no error raised.


# Once the cap is reached, the next call is refused with a 429-status RateLimitError.
def test_at_limit_raises_429(db_session):
    for _ in range(3):
        enforce_rate_limit(db_session, subject="u1", action="post_create", limit=3, window_seconds=60)
    with pytest.raises(RateLimitError) as exc:
        enforce_rate_limit(db_session, subject="u1", action="post_create", limit=3, window_seconds=60)
    assert exc.value.status == 429


# The cap is per (subject, action): a different subject is counted separately.
def test_limit_is_scoped_per_subject(db_session):
    for _ in range(3):
        enforce_rate_limit(db_session, subject="u1", action="post_create", limit=3, window_seconds=60)
    # A different user is unaffected by u1's hits.
    enforce_rate_limit(db_session, subject="u2", action="post_create", limit=3, window_seconds=60)
