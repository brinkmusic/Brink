# WHAT THIS FILE IS
# Checks the artist BTS endpoints (app/routers/artist.py, T50):
#   POST /api/artist/sign-upload -> mint a Supabase Storage signed upload URL
#   POST /api/artist/posts       -> create an ArtistPost row
# Both are login-gated AND artist-only: the caller must be an artist account (User.isArtist
# == true), and the artist is ALWAYS the authenticated caller (never taken from the body), so
# it can't be spoofed. The sign-upload tests stub the storage helper so no test hits Supabase;
# the create test uses the real in-memory db_session so the ArtistPost is actually persisted.

from datetime import datetime, timezone

from sqlmodel import select

from app.db import get_session
from app.deps import AuthError, require_user
from app.main import app
from app.models import ArtistPost, User
from app.routers import artist


# handle is derived from id so distinct seeded users get distinct handles (User.handle is unique).
def _artist(id="artist-1"):
    return User(id=id, handle=id, display_name="d", is_artist=True,
                created_at=datetime.now(timezone.utc))


def _listener(id="listener-1"):
    return User(id=id, handle=id, display_name="d", is_artist=False,
                created_at=datetime.now(timezone.utc))


def _sign_body(**overrides):
    body = {"contentType": "image/jpeg", "sizeBytes": 1024}
    body.update(overrides)
    return body


def _post_body(**overrides):
    body = {"imageUrl": "https://store/artist-1/abc.jpg", "caption": "backstage"}
    body.update(overrides)
    return body


# --- POST /api/artist/sign-upload --------------------------------------------------

# No login session -> the AuthError handler returns our 401 { error } envelope.
def test_sign_upload_unauthenticated_returns_401(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.post("/api/artist/sign-upload", json=_sign_body())
    assert res.status_code == 401
    assert res.json() == {"error": "invalid session"}


# An artist gets a signed upload URL; the storage helper is called for the private bucket with a
# path namespaced under the CALLER's id, and the response echoes the helper's signed url + token.
def test_sign_upload_as_artist_returns_signed_url(client, as_user, monkeypatch):
    as_user(_artist())
    captured = {}

    def fake_sign(bucket, path):
        captured["bucket"] = bucket
        captured["path"] = path
        return {"signed_url": "https://store/upload?token=xyz", "token": "xyz", "path": path}

    monkeypatch.setattr(artist, "create_signed_upload_url", fake_sign)
    res = client.post("/api/artist/sign-upload", json=_sign_body())

    assert res.status_code == 200
    data = res.json()["data"]
    assert data["signedUrl"] == "https://store/upload?token=xyz"
    assert data["token"] == "xyz"
    # The upload lands in the private artist-images bucket, under the caller's own folder.
    assert captured["bucket"] == "artist-images"
    assert captured["path"].startswith("artist-1/")
    assert captured["path"].endswith(".jpg")  # image/jpeg -> .jpg
    assert data["path"] == captured["path"]


# A non-artist account (isArtist == false) cannot mint an upload -> 403, and the storage helper
# is never called.
def test_sign_upload_non_artist_returns_403(client, as_user, monkeypatch):
    as_user(_listener())

    def boom(*a, **k):
        raise AssertionError("must not mint an upload for a non-artist")

    monkeypatch.setattr(artist, "create_signed_upload_url", boom)
    res = client.post("/api/artist/sign-upload", json=_sign_body())
    assert res.status_code == 403
    assert "error" in res.json()


# Oversized upload intent (> 10 MB) is rejected at the contract level -> 400.
def test_sign_upload_oversized_returns_400(client, as_user):
    as_user(_artist())
    res = client.post("/api/artist/sign-upload", json=_sign_body(sizeBytes=10 * 1024 * 1024 + 1))
    assert res.status_code == 400
    assert res.json() == {"error": "invalid request"}


# A non-JPEG/PNG content type is rejected at the contract level -> 400.
def test_sign_upload_wrong_content_type_returns_400(client, as_user):
    as_user(_artist())
    res = client.post("/api/artist/sign-upload", json=_sign_body(contentType="image/gif"))
    assert res.status_code == 400


# --- POST /api/artist/posts --------------------------------------------------------

# No login session -> 401 { error } envelope.
def test_create_post_unauthenticated_returns_401(client):
    def raise_auth_error():
        raise AuthError("invalid session")

    app.dependency_overrides[require_user] = raise_auth_error
    app.dependency_overrides[get_session] = lambda: None
    res = client.post("/api/artist/posts", json=_post_body())
    assert res.status_code == 401


# An artist creates a post: it is really persisted, owned by the caller, with the optional track.
def test_create_post_persists_for_artist(client, as_user, db_session):
    as_user(_artist(), session=db_session)
    res = client.post("/api/artist/posts", json=_post_body(linkedTrackId="spot-1"))

    assert res.status_code == 201
    data = res.json()["data"]
    assert data["artistUserId"] == "artist-1"
    assert data["imageUrl"] == "https://store/artist-1/abc.jpg"
    assert data["caption"] == "backstage"
    assert data["linkedTrackId"] == "spot-1"

    saved = db_session.exec(select(ArtistPost)).all()
    assert len(saved) == 1
    assert saved[0].artist_user_id == "artist-1"


# linkedTrackId is optional: a post without one is still created.
def test_create_post_without_track(client, as_user, db_session):
    as_user(_artist(), session=db_session)
    res = client.post("/api/artist/posts", json=_post_body())
    assert res.status_code == 201
    assert res.json()["data"]["linkedTrackId"] is None


# A non-artist account cannot create an ArtistPost -> 403, nothing persisted.
def test_create_post_non_artist_returns_403(client, as_user, db_session):
    as_user(_listener(), session=db_session)
    res = client.post("/api/artist/posts", json=_post_body())
    assert res.status_code == 403
    assert db_session.exec(select(ArtistPost)).all() == []


# The artist is the caller, never the body: an artistUserId sent in the body is ignored.
def test_create_post_owner_cannot_be_spoofed(client, as_user, db_session):
    as_user(_artist("real-artist"), session=db_session)
    res = client.post("/api/artist/posts", json=_post_body(artistUserId="victim"))
    assert res.status_code == 201
    saved = db_session.exec(select(ArtistPost)).all()[0]
    assert saved.artist_user_id == "real-artist"


# A missing caption is rejected at the contract level -> 400.
def test_create_post_missing_caption_returns_400(client, as_user):
    as_user(_artist())
    body = _post_body()
    del body["caption"]
    res = client.post("/api/artist/posts", json=body)
    assert res.status_code == 400
