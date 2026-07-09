# WHAT THIS FILE IS
# Checks the posts endpoints (app/routers/posts.py): creating a post and listing a user's
# posts. Tests that don't depend on real database behavior (auth, request validation) use a
# MagicMock session via the shared `as_user` fixture; tests that DO depend on it (a post is
# really saved, the track is really upserted, ordering, rate limiting) use the real in-memory
# `db_session` fixture — see the NOTE FOR T10+ in conftest.py.

from datetime import datetime, timedelta, timezone

from sqlmodel import select

from app.deps import AuthError, require_user
from app.db import get_session
from app.main import app
from app.models import Post, PostSource, Track, User


# handle is derived from id so distinct seeded users get distinct handles (User.handle is unique).
def _user(id="user-1"):
    return User(id=id, handle=id, display_name="d", created_at=datetime.now(timezone.utc))


def _valid_body(**overrides):
    body = {
        "track": {
            "spotifyId": "spot-1",
            "title": "Mystery of Love",
            "artistName": "Sufjan Stevens",
            "albumArtUrl": "http://img/a.png",
            "popularity": 42,
        },
        "source": "MANUAL",
        "caption": "on repeat",
    }
    body.update(overrides)
    return body


# --- POST /api/posts ---------------------------------------------------------------

# No login session -> the AuthError handler returns our 401 { error } envelope.
def test_create_unauthenticated_returns_401(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.post("/api/posts", json=_valid_body())
    assert res.status_code == 401
    assert res.json() == {"error": "invalid session"}


# A valid request creates a Post row AND upserts the referenced Track.
def test_create_post_persists_post_and_upserts_track(client, as_user, db_session):
    as_user(_user(), session=db_session)
    res = client.post("/api/posts", json=_valid_body())

    assert res.status_code == 201
    data = res.json()["data"]
    assert data["source"] == "MANUAL"
    assert data["caption"] == "on repeat"
    assert data["userId"] == "user-1"
    assert data["track"]["spotifyId"] == "spot-1"
    assert data["track"]["albumArtUrl"] == "http://img/a.png"

    # Really persisted: one Post row and the upserted Track exist in the database.
    assert len(db_session.exec(select(Post)).all()) == 1
    assert db_session.get(Track, "spot-1") is not None


# A malformed track payload (missing required title) -> 400 via the validation handler.
def test_create_malformed_track_returns_400(client, as_user):
    as_user(_user())
    body = _valid_body()
    del body["track"]["title"]
    res = client.post("/api/posts", json=body)
    assert res.status_code == 400
    assert res.json() == {"error": "invalid request"}


# An invalid source value (not MANUAL/SPOTIFY) -> 400.
def test_create_invalid_source_returns_400(client, as_user):
    as_user(_user())
    res = client.post("/api/posts", json=_valid_body(source="LINKEDIN"))
    assert res.status_code == 400


# authorId cannot be spoofed: even if the body carries a userId, the saved post belongs to
# the authenticated caller.
def test_author_cannot_be_spoofed_via_body(client, as_user, db_session):
    as_user(_user("real-user"), session=db_session)
    body = _valid_body()
    body["userId"] = "victim"  # attacker tries to post as someone else
    res = client.post("/api/posts", json=body)

    assert res.status_code == 201
    saved = db_session.exec(select(Post)).all()[0]
    assert saved.user_id == "real-user"


# Over the per-user cap -> 429 with our { error } envelope.
def test_create_over_rate_limit_returns_429(client, as_user, db_session, monkeypatch):
    from app.routers import posts as posts_router

    monkeypatch.setattr(posts_router, "POST_RATE_LIMIT", 2)
    as_user(_user(), session=db_session)

    assert client.post("/api/posts", json=_valid_body()).status_code == 201
    assert client.post("/api/posts", json=_valid_body()).status_code == 201
    third = client.post("/api/posts", json=_valid_body())
    assert third.status_code == 429
    assert "error" in third.json()


# --- GET /api/posts?userId= --------------------------------------------------------

# Missing the required userId query param -> 400.
def test_list_missing_userid_returns_400(client):
    app.dependency_overrides[get_session] = lambda: None
    res = client.get("/api/posts")
    assert res.status_code == 400


# Returns a user's posts newest-first, each with its linked track.
def test_list_returns_user_posts_newest_first_with_track(client, db_session):
    # Seed the authors (u1, u2) and the Track FIRST, then commit — the Posts foreign-key-reference
    # both, and the test DB enforces foreign keys, so the parents must exist before the Posts.
    db_session.add(_user("u1"))
    db_session.add(_user("u2"))
    db_session.add(Track(spotify_id="spot-1", title="A", artist_name="X"))
    db_session.commit()
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    older = Post(user_id="u1", track_id="spot-1", caption="older",
                 source=PostSource.MANUAL, created_at=now - timedelta(minutes=10))
    newer = Post(user_id="u1", track_id="spot-1", caption="newer",
                 source=PostSource.SPOTIFY, created_at=now)
    other = Post(user_id="u2", track_id="spot-1", caption="other",
                 source=PostSource.MANUAL, created_at=now)
    db_session.add_all([older, newer, other])
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session
    res = client.get("/api/posts", params={"userId": "u1"})

    assert res.status_code == 200
    data = res.json()["data"]
    assert [p["caption"] for p in data] == ["newer", "older"]  # newest first, u2 excluded
    assert data[0]["track"]["title"] == "A"
