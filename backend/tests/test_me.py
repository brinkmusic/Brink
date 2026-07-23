# WHAT THIS FILE IS
# Checks the "me" account-action endpoints (app/routers/me.py):
#   POST  /api/me/become-artist      -> flip the LOGGED-IN account to an artist account (T55).
#   PATCH /api/me/profile            -> set the caller's own bio (T48).
#   POST  /api/me/avatar/sign-upload -> mint a signed upload URL for the caller's own avatar (T48).
#   POST  /api/me/avatar             -> set the caller's own avatar_url from an uploaded path (T48).
# All are login-gated, and every write is on the authenticated caller (never a client-supplied id),
# so they can't be spoofed. These use a real in-memory db_session (not a MagicMock) so we can assert
# the change was actually persisted.

from datetime import datetime, timezone

from sqlmodel import select

from app.db import get_session
from app.deps import AuthError, require_user
from app.main import app
from app.models import Play, User
from app.routers import me


# handle is derived from id so distinct seeded users get distinct handles (User.handle is unique).
def _listener(id="listener-1"):
    return User(id=id, handle=id, display_name="d", is_artist=False,
                created_at=datetime.now(timezone.utc))


def _artist(id="artist-1"):
    return User(id=id, handle=id, display_name="d", is_artist=True,
                created_at=datetime.now(timezone.utc))


# No login session -> the AuthError handler returns our 401 { error } envelope.
def test_become_artist_unauthenticated_returns_401(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.post("/api/me/become-artist")
    assert res.status_code == 401
    assert res.json() == {"error": "invalid session"}


# A normal listener account becomes an artist: 200, the response says isArtist=true, and the flag
# is actually persisted on their row in the database.
def test_become_artist_flips_the_flag(client, as_user, db_session):
    user = _listener()
    as_user(user, session=db_session)

    res = client.post("/api/me/become-artist")

    assert res.status_code == 200
    assert res.json()["data"]["isArtist"] is True
    refreshed = db_session.get(User, "listener-1")
    assert refreshed.is_artist is True


# Calling it when already an artist is a harmless no-op success (idempotent), still isArtist=true.
def test_become_artist_idempotent_for_existing_artist(client, as_user, db_session):
    user = _artist()
    as_user(user, session=db_session)

    res = client.post("/api/me/become-artist")

    assert res.status_code == 200
    assert res.json()["data"]["isArtist"] is True
    refreshed = db_session.get(User, "artist-1")
    assert refreshed.is_artist is True


# --- PATCH /api/me/profile (bio) — T48 ---------------------------------------------

# No login session -> the AuthError handler returns our 401 { error } envelope.
def test_patch_profile_unauthenticated_returns_401(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.patch("/api/me/profile", json={"bio": "hi"})
    assert res.status_code == 401
    assert res.json() == {"error": "invalid session"}


# Setting a bio persists it and returns the camelCase DTO.
def test_patch_profile_sets_bio(client, as_user, db_session):
    as_user(_listener(), session=db_session)

    res = client.patch("/api/me/profile", json={"bio": "just here for the tunes"})

    assert res.status_code == 200
    assert res.json()["data"]["bio"] == "just here for the tunes"
    refreshed = db_session.get(User, "listener-1")
    assert refreshed.bio == "just here for the tunes"


# The bio is trimmed of surrounding whitespace before storing.
def test_patch_profile_trims_bio(client, as_user, db_session):
    as_user(_listener(), session=db_session)

    res = client.patch("/api/me/profile", json={"bio": "   spaced out   "})

    assert res.status_code == 200
    assert res.json()["data"]["bio"] == "spaced out"
    assert db_session.get(User, "listener-1").bio == "spaced out"


# An empty (or whitespace-only) bio clears it back to None.
def test_patch_profile_empty_bio_clears_it(client, as_user, db_session):
    user = _listener()
    user.bio = "old bio"
    as_user(user, session=db_session)

    res = client.patch("/api/me/profile", json={"bio": "   "})

    assert res.status_code == 200
    assert res.json()["data"]["bio"] is None
    assert db_session.get(User, "listener-1").bio is None


# A bio longer than the 300-char limit is rejected at the contract level -> 400.
def test_patch_profile_overlong_bio_returns_400(client, as_user, db_session):
    as_user(_listener(), session=db_session)

    res = client.patch("/api/me/profile", json={"bio": "x" * 301})

    assert res.status_code == 400


# --- POST /api/me/avatar/sign-upload — T48 -----------------------------------------

def _avatar_sign_body(**overrides):
    body = {"contentType": "image/jpeg", "sizeBytes": 1024}
    body.update(overrides)
    return body


# No login session -> 401 { error } envelope.
def test_avatar_sign_upload_unauthenticated_returns_401(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.post("/api/me/avatar/sign-upload", json=_avatar_sign_body())
    assert res.status_code == 401


# Any logged-in user (artist-only is NOT required for avatars) gets a signed upload URL. The storage
# helper is called for the PUBLIC "avatars" bucket at a path under the caller's own id, and the
# response echoes the signed url + token + a public read URL.
def test_avatar_sign_upload_returns_signed_url_for_own_path(client, as_user, db_session, monkeypatch):
    as_user(_listener(), session=db_session)
    captured = {}

    def fake_sign(bucket, path):
        captured["bucket"] = bucket
        captured["path"] = path
        return {"signed_url": "https://store/upload?token=xyz", "token": "xyz", "path": path}

    monkeypatch.setattr(me, "create_signed_upload_url", fake_sign)
    monkeypatch.setattr(
        me, "public_object_url",
        lambda bucket, path: f"https://store/object/public/{bucket}/{path}",
    )
    res = client.post("/api/me/avatar/sign-upload", json=_avatar_sign_body())

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["signedUrl"] == "https://store/upload?token=xyz"
    assert data["token"] == "xyz"
    # The upload lands in the PUBLIC avatars bucket, under the caller's own folder.
    assert captured["bucket"] == "avatars"
    assert captured["path"].startswith("listener-1/")
    assert captured["path"].endswith(".jpg")  # image/jpeg -> .jpg
    assert data["path"] == captured["path"]
    assert data["publicUrl"] == f"https://store/object/public/avatars/{captured['path']}"


# Oversized upload intent (> 10 MB) is rejected at the contract level -> 400.
def test_avatar_sign_upload_oversized_returns_400(client, as_user, db_session):
    as_user(_listener(), session=db_session)
    res = client.post(
        "/api/me/avatar/sign-upload",
        json=_avatar_sign_body(sizeBytes=10 * 1024 * 1024 + 1),
    )
    assert res.status_code == 400


# A non-JPEG/PNG content type is rejected at the contract level -> 400.
def test_avatar_sign_upload_wrong_content_type_returns_400(client, as_user, db_session):
    as_user(_listener(), session=db_session)
    res = client.post("/api/me/avatar/sign-upload", json=_avatar_sign_body(contentType="image/gif"))
    assert res.status_code == 400


# --- POST /api/me/avatar — T48 -----------------------------------------------------

# No login session -> 401 { error } envelope.
def test_avatar_save_unauthenticated_returns_401(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.post("/api/me/avatar", json={"path": "listener-1/pic.jpg"})
    assert res.status_code == 401


# Saving an avatar sets the caller's avatar_url to the public object URL and persists it.
def test_avatar_save_sets_avatar_url(client, as_user, db_session, monkeypatch):
    as_user(_listener(), session=db_session)
    monkeypatch.setattr(
        me, "public_object_url",
        lambda bucket, path: f"https://store/object/public/{bucket}/{path}",
    )

    res = client.post("/api/me/avatar", json={"path": "listener-1/pic.jpg"})

    assert res.status_code == 200
    expected = "https://store/object/public/avatars/listener-1/pic.jpg"
    assert res.json()["data"]["avatarUrl"] == expected
    assert db_session.get(User, "listener-1").avatar_url == expected


# A path outside the caller's own folder is rejected (you can't point your avatar at someone else's
# object) -> 400, and nothing is persisted.
def test_avatar_save_rejects_foreign_path(client, as_user, db_session):
    as_user(_listener(), session=db_session)

    res = client.post("/api/me/avatar", json={"path": "someone-else/pic.jpg"})

    assert res.status_code == 400
    assert db_session.get(User, "listener-1").avatar_url is None


# --- POST /api/me/plays/refresh — T100 ---------------------------------------------
# Pulls the caller's OWN recently-played from Spotify and ingests it immediately, so opening
# your own profile shows up-to-the-minute history instead of waiting for the 30-min cron. It
# reuses the SHARED snapshot ingest (_ingest_user) — these tests stub only the Spotify HTTP
# boundary (get_recently_played) and let the real ingest run against the in-memory DB, per the
# ticket's anti-mock note.


# Build a minimal Spotify recently-played payload with one play, in the shape _ingest_user parses.
def _recently_played(track_id="track-1", played_at="2026-07-22T10:00:00.000Z"):
    return {
        "items": [
            {
                "played_at": played_at,
                "track": {
                    "id": track_id,
                    "name": "A Song",
                    "artists": [{"name": "An Artist"}],
                    "album": {"images": [{"url": "https://img/cover.jpg"}]},
                    "popularity": 50,
                },
            }
        ]
    }


# No login session -> the AuthError handler returns our 401 { error } envelope.
def test_plays_refresh_unauthenticated_returns_401(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.post("/api/me/plays/refresh")
    assert res.status_code == 401
    assert res.json() == {"error": "invalid session"}


# The happy path: the caller's recently-played is pulled and ingested through the shared pipeline,
# so a Play row lands in the DB and the response reports how many were inserted.
def test_plays_refresh_ingests_plays(client, as_user, db_session, monkeypatch):
    as_user(_listener(), session=db_session)
    monkeypatch.setattr(me, "get_recently_played", lambda session, user_id: _recently_played())

    res = client.post("/api/me/plays/refresh")

    assert res.status_code == 200
    assert res.json()["data"]["playsInserted"] == 1
    plays = db_session.exec(select(Play).where(Play.user_id == "listener-1")).all()
    assert len(plays) == 1
    assert plays[0].track_id == "track-1"


# Running it twice with the same play must NOT double-count — the shared ingest dedups on
# (userId, playedAt), so the second run inserts 0.
def test_plays_refresh_does_not_double_count(client, as_user, db_session, monkeypatch):
    as_user(_listener(), session=db_session)
    monkeypatch.setattr(me, "get_recently_played", lambda session, user_id: _recently_played())

    first = client.post("/api/me/plays/refresh")
    second = client.post("/api/me/plays/refresh")

    assert first.json()["data"]["playsInserted"] == 1
    assert second.json()["data"]["playsInserted"] == 0
    plays = db_session.exec(select(Play).where(Play.user_id == "listener-1")).all()
    assert len(plays) == 1


# A user with no linked Spotify (get_recently_played returns None) is a normal empty result, not an
# error: 200 with playsInserted 0 (matches the T20 degradation philosophy).
def test_plays_refresh_unlinked_user_returns_empty(client, as_user, db_session, monkeypatch):
    as_user(_listener(), session=db_session)
    monkeypatch.setattr(me, "get_recently_played", lambda session, user_id: None)

    res = client.post("/api/me/plays/refresh")

    assert res.status_code == 200
    assert res.json()["data"]["playsInserted"] == 0
    assert db_session.exec(select(Play).where(Play.user_id == "listener-1")).all() == []


# The endpoint is throttled (ADR-0011): 2 calls per window are allowed, the 3rd is refused with a
# 429 so a profile visit can refresh but a client can't hammer Spotify.
def test_plays_refresh_throttled_after_limit(client, as_user, db_session, monkeypatch):
    as_user(_listener(), session=db_session)
    monkeypatch.setattr(me, "get_recently_played", lambda session, user_id: None)

    assert client.post("/api/me/plays/refresh").status_code == 200
    assert client.post("/api/me/plays/refresh").status_code == 200
    assert client.post("/api/me/plays/refresh").status_code == 429
