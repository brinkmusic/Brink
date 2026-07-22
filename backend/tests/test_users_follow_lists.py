# WHAT THIS FILE IS
# Automated checks for T16's follower/following list endpoints:
#   GET /api/users/{userId}/followers
#   GET /api/users/{userId}/following
# These are read-only social-graph endpoints. They require login, return the same allow-listed
# camelCase user DTO as search, cap results, and order by handle so the UI is stable.

from datetime import datetime, timezone

from app.db import get_session
from app.deps import AuthError, require_user
from app.main import app
from app.models import Follow, User


def _user(id, handle, display_name=None, *, is_artist=False):
    return User(
        id=id,
        handle=handle,
        display_name=display_name or handle.title(),
        is_artist=is_artist,
        created_at=datetime.now(timezone.utc),
    )


def _seed_users(session, *users):
    for user in users:
        session.add(user)
    session.commit()


def test_followers_returns_users_who_follow_target(client, db_session, as_user):
    caller = _user("caller", "caller")
    target = _user("target", "target")
    ada = _user("ada", "ada", "Ada", is_artist=True)
    zed = _user("zed", "zed", "Zed")
    _seed_users(db_session, caller, target, zed, ada)
    db_session.add(Follow(follower_id=zed.id, following_id=target.id))
    db_session.add(Follow(follower_id=ada.id, following_id=target.id))
    db_session.commit()
    as_user(caller, session=db_session)

    res = client.get("/api/users/target/followers")

    assert res.status_code == 200
    assert res.json()["data"] == [
        {"id": "ada", "handle": "ada", "displayName": "Ada", "isArtist": True},
        {"id": "zed", "handle": "zed", "displayName": "Zed", "isArtist": False},
    ]


def test_following_returns_users_target_follows(client, db_session, as_user):
    caller = _user("caller", "caller")
    target = _user("target", "target")
    beta = _user("beta", "beta", "Beta")
    alpha = _user("alpha", "alpha", "Alpha")
    _seed_users(db_session, caller, target, beta, alpha)
    db_session.add(Follow(follower_id=target.id, following_id=beta.id))
    db_session.add(Follow(follower_id=target.id, following_id=alpha.id))
    db_session.commit()
    as_user(caller, session=db_session)

    res = client.get("/api/users/target/following")

    assert res.status_code == 200
    assert [u["handle"] for u in res.json()["data"]] == ["alpha", "beta"]


def test_follow_lists_require_login(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None

    assert client.get("/api/users/target/followers").status_code == 401
    assert client.get("/api/users/target/following").status_code == 401


def test_follow_lists_unknown_user_is_404(client, db_session, as_user):
    caller = _user("caller", "caller")
    _seed_users(db_session, caller)
    as_user(caller, session=db_session)

    assert client.get("/api/users/missing/followers").status_code == 404
    assert client.get("/api/users/missing/following").status_code == 404


def test_follow_lists_cap_at_50(client, db_session, as_user):
    caller = _user("caller", "caller")
    target = _user("target", "target")
    users = [caller, target]
    for i in range(55):
        users.append(_user(f"u{i:02d}", f"user{i:02d}", f"User {i:02d}"))
    _seed_users(db_session, *users)
    for i in range(55):
        db_session.add(Follow(follower_id=f"u{i:02d}", following_id=target.id))
    db_session.commit()
    as_user(caller, session=db_session)

    res = client.get("/api/users/target/followers")

    assert res.status_code == 200
    assert len(res.json()["data"]) == 50
