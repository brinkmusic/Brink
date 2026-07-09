# WHAT THIS FILE IS
# Checks the comments endpoints (app/routers/comments.py): creating a comment on a post and
# listing a post's comments newest-first with author info (T12). Auth/validation cases use the
# mock-session `as_user` fixture; the cases whose correctness depends on real database behavior
# (a comment is really saved and attributed, ordering, the author join) use the real in-memory
# `db_session` fixture — see the NOTE FOR T10+ in conftest.py.

from datetime import datetime, timedelta, timezone

from sqlmodel import select

from app.db import get_session
from app.deps import AuthError, require_user
from app.main import app
from app.models import Comment, Post, PostSource, Track, User


def _user(id="user-1", handle="h", display_name="d", avatar_url=None):
    return User(id=id, handle=handle, display_name=display_name, avatar_url=avatar_url,
                created_at=datetime.now(timezone.utc))


# Put a real Post (and its Track) in the database so the endpoint's post-exists check passes.
def _seed_post(session, post_id="post-1", author="author-1"):
    session.add(Track(spotify_id="spot-1", title="A", artist_name="X"))
    session.add(Post(id=post_id, user_id=author, track_id="spot-1", source=PostSource.MANUAL))
    session.commit()
    return post_id


# --- POST /api/posts/{id}/comments -------------------------------------------------

# No login session -> the AuthError handler returns our 401 { error } envelope.
def test_comment_unauthenticated_returns_401(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.post("/api/posts/post-1/comments", json={"body": "nice"})
    assert res.status_code == 401
    assert res.json() == {"error": "invalid session"}


# An empty or whitespace-only body -> 400 (non-empty-after-trim rule, enforced in the schema).
def test_comment_empty_body_returns_400(client, as_user):
    as_user(_user())
    assert client.post("/api/posts/post-1/comments", json={"body": ""}).status_code == 400
    assert client.post("/api/posts/post-1/comments", json={"body": "   "}).status_code == 400


# A body past the max length -> 400.
def test_comment_over_max_length_returns_400(client, as_user):
    as_user(_user())
    res = client.post("/api/posts/post-1/comments", json={"body": "x" * 2001})
    assert res.status_code == 400
    assert res.json() == {"error": "invalid request"}


# Commenting on a post that doesn't exist -> 404 (not a 500 from a foreign-key violation).
def test_comment_missing_post_returns_404(client, as_user, db_session):
    as_user(_user(), session=db_session)
    res = client.post("/api/posts/nope/comments", json={"body": "hello"})
    assert res.status_code == 404


# A valid comment is saved, attributed to the authenticated user, trimmed, with author fields.
def test_comment_persists_attributed_to_caller(client, as_user, db_session):
    _seed_post(db_session)
    as_user(_user("real-user", handle="andrea", display_name="Andrea", avatar_url="http://a/x.png"),
            session=db_session)
    res = client.post("/api/posts/post-1/comments", json={"body": "  love this  "})

    assert res.status_code == 201
    data = res.json()["data"]
    assert data["body"] == "love this"  # trimmed
    assert data["author"] == {"displayName": "Andrea", "handle": "andrea", "avatarUrl": "http://a/x.png"}

    saved = db_session.exec(select(Comment)).all()
    assert len(saved) == 1
    assert saved[0].user_id == "real-user"  # attributed to the caller, not client-supplied


# authorId cannot be spoofed: a userId in the body is ignored; the comment belongs to the caller.
def test_comment_author_cannot_be_spoofed(client, as_user, db_session):
    _seed_post(db_session)
    as_user(_user("real-user"), session=db_session)
    res = client.post("/api/posts/post-1/comments", json={"body": "hi", "userId": "victim"})

    assert res.status_code == 201
    assert db_session.exec(select(Comment)).all()[0].user_id == "real-user"


# Over the per-user cap -> 429 with our { error } envelope.
def test_comment_over_rate_limit_returns_429(client, as_user, db_session, monkeypatch):
    from app.routers import comments as comments_router

    monkeypatch.setattr(comments_router, "COMMENT_RATE_LIMIT", 2)
    _seed_post(db_session)
    as_user(_user(), session=db_session)

    assert client.post("/api/posts/post-1/comments", json={"body": "a"}).status_code == 201
    assert client.post("/api/posts/post-1/comments", json={"body": "b"}).status_code == 201
    third = client.post("/api/posts/post-1/comments", json={"body": "c"})
    assert third.status_code == 429
    assert "error" in third.json()


# --- GET /api/posts/{id}/comments --------------------------------------------------

# Listing also requires a login (Brink is private) -> 401 without a session.
def test_list_comments_unauthenticated_returns_401(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.get("/api/posts/post-1/comments")
    assert res.status_code == 401


# Returns a post's comments newest-first, each with its author's fields.
def test_list_comments_newest_first_with_author(client, as_user, db_session):
    _seed_post(db_session)
    db_session.add(_user("u1", handle="ann", display_name="Ann"))
    db_session.add(_user("u2", handle="bo", display_name="Bo", avatar_url="http://a/b.png"))
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db_session.add(Comment(post_id="post-1", user_id="u1", body="older", created_at=now - timedelta(minutes=5)))
    db_session.add(Comment(post_id="post-1", user_id="u2", body="newer", created_at=now))
    # A comment on a different post must not appear.
    db_session.add(Comment(post_id="other", user_id="u1", body="elsewhere", created_at=now))
    db_session.commit()

    as_user(_user(), session=db_session)
    res = client.get("/api/posts/post-1/comments")

    assert res.status_code == 200
    data = res.json()["data"]
    assert [c["body"] for c in data] == ["newer", "older"]  # newest first, other post excluded
    assert data[0]["author"] == {"displayName": "Bo", "handle": "bo", "avatarUrl": "http://a/b.png"}
