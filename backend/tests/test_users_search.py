# WHAT THIS FILE IS
# Automated checks for the user-search endpoint (T15): GET /api/users/search?q=. These verify the
# ENDPOINT's behavior against a real in-memory SQLite database (so the case-insensitive ILIKE match
# and the "cap at 20" ordering are genuinely exercised, not faked): it requires login, validates
# the query, matches handle AND display name case-insensitively, caps + orders results, and is
# rate-limited like every social endpoint.

from datetime import datetime, timezone

from app.db import get_session
from app.deps import AuthError, require_user
from app.main import app
from app.models import User


def _add_user(db_session, handle, display_name, *, is_artist=False):
    # Insert one real User row. WHY a helper: several tests seed a handful of users to search over,
    # and each needs a created_at (the column is NOT NULL) — this keeps each test short.
    user = User(
        handle=handle,
        display_name=display_name,
        is_artist=is_artist,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


def _caller(db_session):
    # The logged-in user doing the searching. The endpoint's rate-limit check writes a row keyed on
    # this user's id, so it must be a real persisted row.
    return _add_user(db_session, "caller", "Caller")


# Matching on the HANDLE substring returns the user, with the camelCase DTO fields (ADR-0012).
def test_search_matches_handle_substring(client, db_session, as_user):
    caller = _caller(db_session)
    target = _add_user(db_session, "andrea", "Andrea V", is_artist=True)
    as_user(caller, session=db_session)

    res = client.get("/api/users/search?q=ndre")
    assert res.status_code == 200
    data = res.json()["data"]
    handles = [u["handle"] for u in data]
    assert "andrea" in handles
    hit = next(u for u in data if u["handle"] == "andrea")
    # Exactly the allow-listed, camelCase fields — never a raw row.
    assert hit == {
        "id": target.id,
        "handle": "andrea",
        "displayName": "Andrea V",
        "isArtist": True,
    }


# Matching on the DISPLAY NAME substring also returns the user (even when the handle doesn't match).
def test_search_matches_display_name_substring(client, db_session, as_user):
    caller = _caller(db_session)
    _add_user(db_session, "seb", "Sebastian K")
    as_user(caller, session=db_session)

    res = client.get("/api/users/search?q=bastian")
    assert res.status_code == 200
    handles = [u["handle"] for u in res.json()["data"]]
    assert "seb" in handles


# The match is case-insensitive (ILIKE): an uppercase query still finds a lowercase handle.
def test_search_is_case_insensitive(client, db_session, as_user):
    caller = _caller(db_session)
    _add_user(db_session, "jonah", "Jonah W")
    as_user(caller, session=db_session)

    res = client.get("/api/users/search?q=JON")
    assert res.status_code == 200
    handles = [u["handle"] for u in res.json()["data"]]
    assert "jonah" in handles


# An empty query is rejected up front as a 400 (standard { error } envelope), before any DB work.
def test_search_empty_query_is_400(client, db_session, as_user):
    caller = _caller(db_session)
    as_user(caller, session=db_session)
    res = client.get("/api/users/search?q=")
    assert res.status_code == 400
    assert "error" in res.json()


# A too-short query (1 char, below our 2-char minimum) is likewise rejected as a 400.
def test_search_too_short_query_is_400(client, db_session, as_user):
    caller = _caller(db_session)
    as_user(caller, session=db_session)
    res = client.get("/api/users/search?q=a")
    assert res.status_code == 400
    assert "error" in res.json()


# A query that is only whitespace is rejected as a 400 too (we trim before checking the length).
def test_search_whitespace_query_is_400(client, db_session, as_user):
    caller = _caller(db_session)
    as_user(caller, session=db_session)
    res = client.get("/api/users/search?q=%20%20")
    assert res.status_code == 400


# Search requires a login (Brink is private). We override require_user to raise, matching how the
# other endpoints' unauthenticated tests are written (no dependence on a real DB session).
def test_search_requires_login(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.get("/api/users/search?q=andrea")
    assert res.status_code == 401


# At most 20 results come back even when more users match (the cap protects the payload).
def test_search_caps_at_20(client, db_session, as_user):
    caller = _caller(db_session)
    # 25 users that all share the "match" substring in their handle.
    for i in range(25):
        _add_user(db_session, f"match{i:02d}", f"Match {i}")
    as_user(caller, session=db_session)

    res = client.get("/api/users/search?q=match")
    assert res.status_code == 200
    assert len(res.json()["data"]) == 20


# Over the per-user cap -> 429 with our { error } envelope (rate-limited like every social endpoint).
def test_search_over_rate_limit_returns_429(client, db_session, as_user, monkeypatch):
    from app.routers import users as users_router

    monkeypatch.setattr(users_router, "USER_SEARCH_RATE_LIMIT", 2)
    caller = _caller(db_session)
    _add_user(db_session, "andrea", "Andrea V")
    as_user(caller, session=db_session)

    assert client.get("/api/users/search?q=and").status_code == 200
    assert client.get("/api/users/search?q=and").status_code == 200
    third = client.get("/api/users/search?q=and")
    assert third.status_code == 429
    assert "error" in third.json()
