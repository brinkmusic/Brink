# WHAT THIS FILE IS
# Checks the reactions endpoints (app/routers/reactions.py): adding and removing a user's
# reaction on a post, and the fresh per-type counts they return (T11). Auth/validation cases
# use the mock-session `as_user` fixture; the cases whose correctness depends on real database
# behavior (idempotent add via the unique constraint, delete, grouped counts) use the real
# in-memory `db_session` fixture — see the NOTE FOR T10+ in conftest.py.

from datetime import datetime, timezone

from sqlmodel import select

from app.db import get_session
from app.deps import AuthError, require_user
from app.main import app
from app.models import Post, PostSource, Reaction, Track, User


def _user(id="user-1"):
    return User(id=id, handle="h", display_name="d", created_at=datetime.now(timezone.utc))


# Put a real Post (and its Track) in the database so the endpoint's post-exists check passes.
def _seed_post(session, post_id="post-1", author="author-1"):
    session.add(Track(spotify_id="spot-1", title="A", artist_name="X"))
    session.add(Post(id=post_id, user_id=author, track_id="spot-1", source=PostSource.MANUAL))
    session.commit()
    return post_id


# --- POST /api/posts/{id}/reactions ------------------------------------------------

# No login session -> the AuthError handler returns our 401 { error } envelope.
def test_react_unauthenticated_returns_401(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.post("/api/posts/post-1/reactions", json={"type": "HEART"})
    assert res.status_code == 401
    assert res.json() == {"error": "invalid session"}


# A type outside the ReactionType enum (HEART|FIRE|SPARKLE) -> 400 via the validation handler.
def test_react_invalid_type_returns_400(client, as_user):
    as_user(_user())
    res = client.post("/api/posts/post-1/reactions", json={"type": "THUMBS_UP"})
    assert res.status_code == 400
    assert res.json() == {"error": "invalid request"}


# Reacting to a post that doesn't exist -> 404 (not a 500 from a foreign-key violation).
def test_react_missing_post_returns_404(client, as_user, db_session):
    as_user(_user(), session=db_session)
    res = client.post("/api/posts/nope/reactions", json={"type": "HEART"})
    assert res.status_code == 404


# A valid reaction is saved and the response carries fresh per-type counts.
def test_react_adds_and_returns_counts(client, as_user, db_session):
    _seed_post(db_session)
    as_user(_user(), session=db_session)
    res = client.post("/api/posts/post-1/reactions", json={"type": "HEART"})

    assert res.status_code == 201
    data = res.json()["data"]
    assert data["postId"] == "post-1"
    assert data["counts"] == {"HEART": 1, "FIRE": 0, "SPARKLE": 0}
    assert len(db_session.exec(select(Reaction)).all()) == 1


# Reacting twice with the same type is a no-op: one row, counts unchanged (idempotent).
def test_double_react_is_idempotent(client, as_user, db_session):
    _seed_post(db_session)
    as_user(_user(), session=db_session)
    first = client.post("/api/posts/post-1/reactions", json={"type": "HEART"})
    second = client.post("/api/posts/post-1/reactions", json={"type": "HEART"})

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.json()["data"]["counts"]["HEART"] == 1
    assert len(db_session.exec(select(Reaction)).all()) == 1


# Different types from the same user coexist and are counted separately.
def test_counts_are_per_type(client, as_user, db_session):
    _seed_post(db_session)
    as_user(_user(), session=db_session)
    client.post("/api/posts/post-1/reactions", json={"type": "HEART"})
    res = client.post("/api/posts/post-1/reactions", json={"type": "FIRE"})

    assert res.json()["data"]["counts"] == {"HEART": 1, "FIRE": 1, "SPARKLE": 0}
    assert len(db_session.exec(select(Reaction)).all()) == 2


# Over the per-user cap -> 429 with our { error } envelope.
def test_react_over_rate_limit_returns_429(client, as_user, db_session, monkeypatch):
    from app.routers import reactions as reactions_router

    monkeypatch.setattr(reactions_router, "REACTION_RATE_LIMIT", 2)
    _seed_post(db_session)
    as_user(_user(), session=db_session)

    assert client.post("/api/posts/post-1/reactions", json={"type": "HEART"}).status_code == 201
    assert client.post("/api/posts/post-1/reactions", json={"type": "FIRE"}).status_code == 201
    third = client.post("/api/posts/post-1/reactions", json={"type": "SPARKLE"})
    assert third.status_code == 429
    assert "error" in third.json()


# --- DELETE /api/posts/{id}/reactions ----------------------------------------------

# Removing your reaction deletes the row and decrements the returned counts.
def test_delete_removes_reaction_and_decrements(client, as_user, db_session):
    _seed_post(db_session)
    as_user(_user(), session=db_session)
    client.post("/api/posts/post-1/reactions", json={"type": "HEART"})

    res = client.request("DELETE", "/api/posts/post-1/reactions", json={"type": "HEART"})
    assert res.status_code == 200
    assert res.json()["data"]["counts"]["HEART"] == 0
    assert len(db_session.exec(select(Reaction)).all()) == 0


# A user can only remove their OWN reaction: user-2 deleting doesn't touch user-1's row.
def test_delete_only_removes_own_reaction(client, as_user, db_session):
    _seed_post(db_session)
    # user-1 reacts.
    as_user(_user("user-1"), session=db_session)
    client.post("/api/posts/post-1/reactions", json={"type": "HEART"})
    # user-2 tries to remove the HEART.
    as_user(_user("user-2"), session=db_session)
    res = client.request("DELETE", "/api/posts/post-1/reactions", json={"type": "HEART"})

    assert res.status_code == 200
    # user-1's reaction is untouched; the count still shows it.
    assert res.json()["data"]["counts"]["HEART"] == 1
    assert len(db_session.exec(select(Reaction)).all()) == 1
