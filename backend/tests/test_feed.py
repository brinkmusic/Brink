# WHAT THIS FILE IS
# Checks the feed endpoint (app/routers/feed.py): GET /api/feed returns posts from the people the
# viewer follows plus the viewer's own posts, newest-first, each carrying its track, per-type
# reaction counts, a comment count, and which reactions the VIEWER left (T13). Correctness depends
# on real joins/aggregation/ordering, so every case here uses the real in-memory `db_session`
# fixture (a MagicMock can't fake grouped counts — see the NOTE FOR T10+ in conftest.py).

from datetime import datetime, timedelta, timezone

import app.routers.feed as feed_module
from app.db import get_session
from app.deps import AuthError, require_user
from app.main import app
from app.models import (
    ArtistComment,
    ArtistPost,
    ArtistReaction,
    Comment,
    Follow,
    Post,
    PostSource,
    Reaction,
    ReactionType,
    Track,
    User,
)


def _user(id, handle):
    return User(id=id, handle=handle, display_name=handle,
                created_at=datetime.now(timezone.utc))


NOW = datetime.now(timezone.utc).replace(tzinfo=None)


# Build a small world: viewer "me", a followee "friend", and an unfollowed "stranger", each with
# one post. Returns the post ids so tests can assert which appear in the feed.
def _seed_world(session):
    # Seed the parents (the three users + the Track) and commit them FIRST: the Posts and the Follow
    # foreign-key-reference them, and the test DB enforces foreign keys, so the parents must exist
    # before the children.
    session.add(Track(spotify_id="spot-1", title="A", artist_name="X"))
    for uid in ("me", "friend", "stranger"):
        session.add(_user(uid, uid))
    session.commit()
    session.add(Post(id="p-me", user_id="me", track_id="spot-1", source=PostSource.MANUAL,
                     created_at=NOW - timedelta(minutes=10)))
    session.add(Post(id="p-friend", user_id="friend", track_id="spot-1", source=PostSource.MANUAL,
                     created_at=NOW))
    session.add(Post(id="p-stranger", user_id="stranger", track_id="spot-1", source=PostSource.MANUAL,
                     created_at=NOW - timedelta(minutes=5)))
    session.add(Follow(follower_id="me", following_id="friend"))
    session.commit()


# Listing requires a login (Brink is private) -> 401 without a session.
def test_feed_unauthenticated_returns_401(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.get("/api/feed")
    assert res.status_code == 401


# A user who follows nobody still sees their own posts.
def test_feed_no_follows_shows_self(client, as_user, db_session):
    db_session.add(Track(spotify_id="spot-1", title="A", artist_name="X"))
    db_session.add(_user("me", "me"))
    db_session.commit()  # Track + author committed before the Post that references them (FK enforced)
    db_session.add(Post(id="p-me", user_id="me", track_id="spot-1", source=PostSource.MANUAL,
                        created_at=NOW))
    db_session.commit()
    as_user(_user("me", "me"), session=db_session)

    res = client.get("/api/feed")
    assert res.status_code == 200
    assert [p["id"] for p in res.json()["data"]] == ["p-me"]


# Feed = followees' posts + own posts, newest-first; unfollowed users are excluded.
def test_feed_includes_followees_and_self_newest_first(client, as_user, db_session):
    _seed_world(db_session)
    as_user(_user("me", "me"), session=db_session)

    res = client.get("/api/feed")
    assert res.status_code == 200
    ids = [p["id"] for p in res.json()["data"]]
    assert ids == ["p-friend", "p-me"]  # newest first, stranger excluded


# Each feed post carries per-type reaction counts, a comment count, and the viewer's own reactions.
def test_feed_post_carries_engagement_and_viewer_state(client, as_user, db_session):
    _seed_world(db_session)
    # On the friend's post: me leaves a HEART, friend leaves a FIRE; two comments exist.
    db_session.add(Reaction(post_id="p-friend", user_id="me", type=ReactionType.HEART))
    db_session.add(Reaction(post_id="p-friend", user_id="friend", type=ReactionType.FIRE))
    db_session.add(Comment(post_id="p-friend", user_id="me", body="one", created_at=NOW))
    db_session.add(Comment(post_id="p-friend", user_id="friend", body="two", created_at=NOW))
    db_session.commit()
    as_user(_user("me", "me"), session=db_session)

    res = client.get("/api/feed")
    friend_post = next(p for p in res.json()["data"] if p["id"] == "p-friend")

    assert friend_post["reactionCounts"] == {"HEART": 1, "FIRE": 1, "SPARKLE": 0}
    assert friend_post["commentCount"] == 2
    # viewerReactions: true only for the types the viewer (me) left -> HEART, not FIRE.
    assert friend_post["viewerReactions"] == {"HEART": True, "FIRE": False, "SPARKLE": False}


# Each feed post carries its author's public fields, so the frontend can show who posted.
def test_feed_post_includes_author(client, as_user, db_session):
    _seed_world(db_session)
    as_user(_user("me", "me"), session=db_session)

    res = client.get("/api/feed")
    friend_post = next(p for p in res.json()["data"] if p["id"] == "p-friend")
    assert friend_post["author"] == {"displayName": "friend", "handle": "friend", "avatarUrl": None}


# Unfollowing a user drops their posts from the feed.
def test_feed_drops_unfollowed(client, as_user, db_session):
    _seed_world(db_session)
    # Remove the follow edge me -> friend.
    edge = db_session.get(Follow, ("me", "friend"))
    db_session.delete(edge)
    db_session.commit()
    as_user(_user("me", "me"), session=db_session)

    res = client.get("/api/feed")
    assert [p["id"] for p in res.json()["data"]] == ["p-me"]  # only self remains


# Every song item now carries a "kind" discriminator so the template (and the frontend) can tell a
# song post from an artist post (T049).
def test_feed_song_items_tagged_kind_song(client, as_user, db_session):
    _seed_world(db_session)
    as_user(_user("me", "me"), session=db_session)

    res = client.get("/api/feed")
    assert all(item["kind"] == "song" for item in res.json()["data"])


# ---- T049: followed artists' ArtistPosts appear in the feed, interleaved newest-first ----


# Stub the signed-read helper so build_feed never touches Supabase. Returns a recognisable URL that
# embeds the raw path, so a test can prove the image was signed (mirrors how test_pages.py stubs it).
def _stub_signed_read(monkeypatch):
    monkeypatch.setattr(
        feed_module,
        "create_signed_read_url",
        lambda bucket, path: f"https://signed/{bucket}/{path}?token=readtok",
    )


# A followed artist's ArtistPost shows up in the feed, tagged kind == "artist", with its image
# signed and its author fields present.
def test_feed_includes_followed_artist_post(client, as_user, db_session, monkeypatch):
    _stub_signed_read(monkeypatch)
    db_session.add(_user("me", "me"))
    db_session.add(User(id="artist", handle="artist", display_name="The Artist",
                        is_artist=True, created_at=datetime.now(timezone.utc)))
    db_session.commit()
    db_session.add(Follow(follower_id="me", following_id="artist"))
    db_session.add(ArtistPost(id="ap-1", artist_user_id="artist",
                              image_url="artist/backstage.jpg", caption="backstage",
                              created_at=NOW))
    db_session.commit()
    as_user(_user("me", "me"), session=db_session)

    res = client.get("/api/feed")
    assert res.status_code == 200
    item = next(p for p in res.json()["data"] if p["id"] == "ap-1")
    assert item["kind"] == "artist"
    assert item["caption"] == "backstage"
    assert item["imageUrl"] == "https://signed/artist-images/artist/backstage.jpg?token=readtok"
    assert item["author"] == {"displayName": "The Artist", "handle": "artist", "avatarUrl": None}


# An artist you do NOT follow does not appear in your feed.
def test_feed_excludes_unfollowed_artist_post(client, as_user, db_session, monkeypatch):
    _stub_signed_read(monkeypatch)
    db_session.add(_user("me", "me"))
    db_session.add(User(id="artist", handle="artist", display_name="The Artist",
                        is_artist=True, created_at=datetime.now(timezone.utc)))
    db_session.commit()
    # No Follow edge me -> artist.
    db_session.add(ArtistPost(id="ap-1", artist_user_id="artist",
                              image_url="artist/x.jpg", caption="hidden", created_at=NOW))
    db_session.commit()
    as_user(_user("me", "me"), session=db_session)

    res = client.get("/api/feed")
    assert not any(p["id"] == "ap-1" for p in res.json()["data"])


# Song posts and artist posts are merged into ONE list sorted by createdAt DESC (interleaved).
def test_feed_interleaves_song_and_artist_by_created_at(client, as_user, db_session, monkeypatch):
    _stub_signed_read(monkeypatch)
    db_session.add(Track(spotify_id="spot-1", title="A", artist_name="X"))
    db_session.add(_user("me", "me"))
    db_session.add(User(id="artist", handle="artist", display_name="The Artist",
                        is_artist=True, created_at=datetime.now(timezone.utc)))
    db_session.commit()
    db_session.add(Follow(follower_id="me", following_id="artist"))
    # Song post oldest, artist post middle, song post newest.
    db_session.add(Post(id="p-old", user_id="me", track_id="spot-1", source=PostSource.MANUAL,
                        created_at=NOW - timedelta(minutes=10)))
    db_session.add(ArtistPost(id="ap-mid", artist_user_id="artist", image_url="artist/m.jpg",
                              caption="mid", created_at=NOW - timedelta(minutes=5)))
    db_session.add(Post(id="p-new", user_id="me", track_id="spot-1", source=PostSource.MANUAL,
                        created_at=NOW))
    db_session.commit()
    as_user(_user("me", "me"), session=db_session)

    res = client.get("/api/feed")
    order = [(p["id"], p["kind"]) for p in res.json()["data"]]
    assert order == [("p-new", "song"), ("ap-mid", "artist"), ("p-old", "song")]


# An artist feed item carries per-type reaction counts (zeros included), a comment count, and the
# viewer's own reactions — reusing the T52 engagement tables.
def test_feed_artist_item_carries_engagement(client, as_user, db_session, monkeypatch):
    _stub_signed_read(monkeypatch)
    db_session.add(_user("me", "me"))
    db_session.add(User(id="artist", handle="artist", display_name="The Artist",
                        is_artist=True, created_at=datetime.now(timezone.utc)))
    db_session.commit()
    db_session.add(Follow(follower_id="me", following_id="artist"))
    db_session.add(ArtistPost(id="ap-1", artist_user_id="artist", image_url="artist/x.jpg",
                              caption="clip", created_at=NOW))
    db_session.commit()
    # me leaves a HEART, artist leaves a FIRE; two comments exist.
    db_session.add(ArtistReaction(artist_post_id="ap-1", user_id="me", type=ReactionType.HEART))
    db_session.add(ArtistReaction(artist_post_id="ap-1", user_id="artist", type=ReactionType.FIRE))
    db_session.add(ArtistComment(artist_post_id="ap-1", user_id="me", body="one", created_at=NOW))
    db_session.add(ArtistComment(artist_post_id="ap-1", user_id="artist", body="two", created_at=NOW))
    db_session.commit()
    as_user(_user("me", "me"), session=db_session)

    res = client.get("/api/feed")
    item = next(p for p in res.json()["data"] if p["id"] == "ap-1")
    assert item["reactionCounts"] == {"HEART": 1, "FIRE": 1, "SPARKLE": 0}
    assert item["commentCount"] == 2
    assert item["viewerReactions"] == {"HEART": True, "FIRE": False, "SPARKLE": False}
