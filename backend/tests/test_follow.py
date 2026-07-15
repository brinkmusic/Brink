# WHAT THIS FILE IS
# Checks the follow endpoints (app/routers/follow.py): following and unfollowing another user
# (T13). Auth/validation cases use the mock-session `as_user` fixture; the cases whose
# correctness depends on real database behavior (a Follow row is really created, the composite
# primary key makes a duplicate follow a no-op, unfollow really deletes) use the real in-memory
# `db_session` fixture — see the NOTE FOR T10+ in conftest.py.

from datetime import datetime, timezone

from sqlmodel import select

from app.db import get_session
from app.deps import AuthError, require_user
from app.main import app
from app.models import Follow, User


def _user(id="user-1", handle="h", display_name="d"):
    return User(id=id, handle=handle, display_name=display_name,
                created_at=datetime.now(timezone.utc))


# Put a real target user in the database so the endpoint's "user exists" check passes.
def _seed_target(session, id="target-1", handle="t"):
    session.add(_user(id=id, handle=handle, display_name="Target"))
    session.commit()
    return id


# --- POST /api/follow/{userId} -----------------------------------------------------

# No login session -> the AuthError handler returns our 401 { error } envelope.
def test_follow_unauthenticated_returns_401(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.post("/api/follow/target-1")
    assert res.status_code == 401
    assert res.json() == {"error": "invalid session"}


# Following yourself is not allowed -> 400.
def test_follow_self_returns_400(client, as_user, db_session):
    as_user(_user("me"), session=db_session)
    res = client.post("/api/follow/me")
    assert res.status_code == 400


# Following a user who doesn't exist -> 404 (not a 500 from a foreign-key violation).
def test_follow_unknown_user_returns_404(client, as_user, db_session):
    as_user(_user("me"), session=db_session)
    res = client.post("/api/follow/nope")
    assert res.status_code == 404


# A valid follow creates a Follow row attributed to the caller and reports following=true.
def test_follow_persists_attributed_to_caller(client, as_user, db_session):
    _seed_target(db_session)
    as_user(_user("me"), session=db_session)
    res = client.post("/api/follow/target-1")

    assert res.status_code == 201
    assert res.json()["data"] == {"followingId": "target-1", "following": True}

    rows = db_session.exec(select(Follow)).all()
    assert len(rows) == 1
    assert rows[0].follower_id == "me"  # the caller, never client-supplied
    assert rows[0].following_id == "target-1"


# Following the same user twice is a no-op (composite PK) -> still 201, still one row.
def test_follow_is_idempotent(client, as_user, db_session):
    _seed_target(db_session)
    as_user(_user("me"), session=db_session)
    assert client.post("/api/follow/target-1").status_code == 201
    assert client.post("/api/follow/target-1").status_code == 201
    assert len(db_session.exec(select(Follow)).all()) == 1


# Over the per-user cap -> 429 with our { error } envelope.
def test_follow_over_rate_limit_returns_429(client, as_user, db_session, monkeypatch):
    from app.routers import follow as follow_router

    monkeypatch.setattr(follow_router, "FOLLOW_RATE_LIMIT", 2)
    db_session.add(_user("a", handle="a"))
    db_session.add(_user("b", handle="b"))
    db_session.commit()
    as_user(_user("me"), session=db_session)

    assert client.post("/api/follow/a").status_code == 201
    assert client.post("/api/follow/b").status_code == 201
    third = client.post("/api/follow/target-1")
    assert third.status_code == 429
    assert "error" in third.json()


# --- DELETE /api/follow/{userId} ---------------------------------------------------

# Unfollowing removes the Follow row and reports following=false.
def test_unfollow_removes_row(client, as_user, db_session):
    _seed_target(db_session)
    # Seed the caller "me" BEFORE the Follow row that references it — as_user persists "me", and the
    # test DB enforces the Follow.followerId foreign key.
    as_user(_user("me"), session=db_session)
    db_session.add(Follow(follower_id="me", following_id="target-1"))
    db_session.commit()

    res = client.delete("/api/follow/target-1")
    assert res.status_code == 200
    assert res.json()["data"] == {"followingId": "target-1", "following": False}
    assert db_session.exec(select(Follow)).all() == []


# Unfollowing someone you don't follow is a harmless no-op -> 200.
def test_unfollow_not_following_is_noop(client, as_user, db_session):
    _seed_target(db_session)
    as_user(_user("me"), session=db_session)
    res = client.delete("/api/follow/target-1")
    assert res.status_code == 200
    assert res.json()["data"] == {"followingId": "target-1", "following": False}
