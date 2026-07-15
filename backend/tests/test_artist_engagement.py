# WHAT THIS FILE IS
# Checks the artist-post engagement endpoints (app/routers/artist.py, T52):
#   POST/DELETE /api/artist/posts/{id}/reactions -> any logged-in user reacts (idempotent add /
#                                                    own-only remove), returns fresh per-type counts
#   POST/GET    /api/artist/posts/{id}/comments   -> any logged-in user comments / lists them
#   GET         /api/artist/posts/{id}/engagement -> OWNER-ONLY: the owning artist sees counts
# The asymmetry is the point (MEDIA-4): anyone may engage with an artist post, but only the artist
# who made it may read its aggregated engagement. These tests use the real in-memory db_session
# because correctness depends on real DB behavior (the reaction unique constraint, counting, the
# ownership check) that a MagicMock can't fake.

from datetime import datetime, timedelta, timezone

from app.deps import AuthError, require_user
from app.db import get_session
from app.main import app
from app.models import ArtistComment, ArtistPost, ArtistReaction, User


def _artist(id="artist-1"):
    return User(id=id, handle=id, display_name="d", is_artist=True,
                created_at=datetime.now(timezone.utc))


def _listener(id="listener-1"):
    return User(id=id, handle=id, display_name="d", is_artist=False,
                created_at=datetime.now(timezone.utc))


# Seed an artist + one of their posts straight into the DB and return the post id. Parents before
# children: the owner User must exist before the ArtistPost that foreign-keys to it (the test DB
# enforces foreign keys).
def _seed_post(session, owner=None, post_id="ap-1"):
    owner = owner or _artist()
    session.merge(owner)
    session.commit()
    session.add(ArtistPost(id=post_id, artist_user_id=owner.id,
                           image_url="https://store/x.jpg", caption="bts"))
    session.commit()
    return post_id


# --- reactions ---------------------------------------------------------------------

# A listener reacts to an artist post: 201 with fresh counts; a repeat of the same type is
# idempotent (still 1), and a different type is counted separately.
def test_react_add_is_idempotent_and_counts(client, as_user, db_session):
    post_id = _seed_post(db_session)
    as_user(_listener(), session=db_session)

    res = client.post(f"/api/artist/posts/{post_id}/reactions", json={"type": "HEART"})
    assert res.status_code == 201
    counts = res.json()["data"]["counts"]
    assert counts == {"HEART": 1, "FIRE": 0, "SPARKLE": 0}

    # Same reaction again -> no duplicate (unique constraint), still 1.
    again = client.post(f"/api/artist/posts/{post_id}/reactions", json={"type": "HEART"})
    assert again.json()["data"]["counts"]["HEART"] == 1

    # A different type is a separate reaction.
    fire = client.post(f"/api/artist/posts/{post_id}/reactions", json={"type": "FIRE"})
    assert fire.json()["data"]["counts"] == {"HEART": 1, "FIRE": 1, "SPARKLE": 0}


# Removing the caller's own reaction drops the count back to zero; removing one that isn't there is
# a no-op (not an error).
def test_remove_reaction(client, as_user, db_session):
    post_id = _seed_post(db_session)
    as_user(_listener(), session=db_session)
    client.post(f"/api/artist/posts/{post_id}/reactions", json={"type": "HEART"})

    res = client.request("DELETE", f"/api/artist/posts/{post_id}/reactions", json={"type": "HEART"})
    assert res.status_code == 200
    assert res.json()["data"]["counts"]["HEART"] == 0

    # Removing again is a harmless no-op.
    noop = client.request("DELETE", f"/api/artist/posts/{post_id}/reactions", json={"type": "HEART"})
    assert noop.status_code == 200


def test_reactions_require_login(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.post("/api/artist/posts/ap-1/reactions", json={"type": "HEART"})
    assert res.status_code == 401


def test_react_missing_post_404(client, as_user, db_session):
    as_user(_listener(), session=db_session)
    res = client.post("/api/artist/posts/nope/reactions", json={"type": "HEART"})
    assert res.status_code == 404


# --- comments ----------------------------------------------------------------------

# A listener comments: the created comment comes back with its body and author.
def test_comment_create(client, as_user, db_session):
    post_id = _seed_post(db_session)
    as_user(_listener(), session=db_session)

    res = client.post(f"/api/artist/posts/{post_id}/comments", json={"body": "first"})
    assert res.status_code == 201
    assert res.json()["data"]["body"] == "first"
    assert res.json()["data"]["author"]["handle"] == "listener-1"


# The list returns comments newest-first, each with its author, and excludes other posts' comments.
# Seeded with explicit timestamps because SQLite's CURRENT_TIMESTAMP is only second-resolution, so
# two rows created in the same second would tie (mirrors the T12 comment-list test).
def test_comment_list_newest_first(client, as_user, db_session):
    post_id = _seed_post(db_session)
    other_id = _seed_post(db_session, owner=_artist("artist-2"), post_id="ap-2")
    commenter = _listener()
    as_user(commenter, session=db_session)  # persists commenter (FK) + logs them in
    now = datetime.now(timezone.utc)

    db_session.add(ArtistComment(artist_post_id=post_id, user_id=commenter.id, body="older",
                                 created_at=now - timedelta(minutes=5)))
    db_session.add(ArtistComment(artist_post_id=post_id, user_id=commenter.id, body="newer",
                                 created_at=now))
    db_session.add(ArtistComment(artist_post_id=other_id, user_id=commenter.id, body="elsewhere",
                                 created_at=now))
    db_session.commit()

    listed = client.get(f"/api/artist/posts/{post_id}/comments")
    assert listed.status_code == 200
    assert [c["body"] for c in listed.json()["data"]] == ["newer", "older"]


def test_comments_require_login(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.post("/api/artist/posts/ap-1/comments", json={"body": "hi"})
    assert res.status_code == 401


def test_comment_missing_post_404(client, as_user, db_session):
    as_user(_listener(), session=db_session)
    res = client.post("/api/artist/posts/nope/comments", json={"body": "hi"})
    assert res.status_code == 404


def test_comment_blank_body_400(client, as_user, db_session):
    post_id = _seed_post(db_session)
    as_user(_listener(), session=db_session)
    res = client.post(f"/api/artist/posts/{post_id}/comments", json={"body": "   "})
    assert res.status_code == 400


# --- engagement (owner-only) -------------------------------------------------------

# The owning artist sees aggregated engagement: reaction counts (from two different listeners) and
# the comment count.
def test_engagement_owner_sees_counts(client, as_user, db_session):
    owner = _artist("owner-1")
    post_id = _seed_post(db_session, owner=owner)

    as_user(_listener("l1"), session=db_session)
    client.post(f"/api/artist/posts/{post_id}/reactions", json={"type": "HEART"})
    as_user(_listener("l2"), session=db_session)
    client.post(f"/api/artist/posts/{post_id}/reactions", json={"type": "HEART"})
    client.post(f"/api/artist/posts/{post_id}/comments", json={"body": "love it"})

    as_user(owner, session=db_session)
    res = client.get(f"/api/artist/posts/{post_id}/engagement")
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["postId"] == post_id
    assert data["reactionCounts"] == {"HEART": 2, "FIRE": 0, "SPARKLE": 0}
    assert data["commentCount"] == 1


# A user who does not own the post (even another artist) cannot read its engagement -> 403.
def test_engagement_non_owner_403(client, as_user, db_session):
    post_id = _seed_post(db_session, owner=_artist("owner-1"))
    as_user(_artist("someone-else"), session=db_session)
    res = client.get(f"/api/artist/posts/{post_id}/engagement")
    assert res.status_code == 403


def test_engagement_missing_post_404(client, as_user, db_session):
    as_user(_artist(), session=db_session)
    res = client.get("/api/artist/posts/nope/engagement")
    assert res.status_code == 404


def test_engagement_requires_login(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.get("/api/artist/posts/ap-1/engagement")
    assert res.status_code == 401
