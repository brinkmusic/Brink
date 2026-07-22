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
from app.security import supabase


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


# --- create_signed_read_url (T53) --------------------------------------------------

# A small fake standing in for the Supabase Storage client, so the helper's REST call is
# checked WITHOUT hitting the network (same "stub the storage helper" approach the sign-upload
# tests use). It records the (bucket, path, expires_in) it was asked to sign and returns
# Supabase's real response shape: {"signedURL": "/object/sign/<bucket>/<path>?token=..."}.
class _FakeStorage:
    def __init__(self):
        self.calls = []

    def from_(self, bucket):
        self.calls.append(("from_", bucket))
        return self

    def create_signed_url(self, path, expires_in):
        self.calls.append(("create_signed_url", path, expires_in))
        return {"signedURL": f"/object/sign/artist-images/{path}?token=readtok"}


class _FakeAdmin:
    def __init__(self, storage):
        self.storage = storage


# The helper signs the given path in the given bucket and returns a FULL, browser-usable URL:
# Supabase's relative signedURL prefixed with "{SUPABASE_URL}/storage/v1".
def test_create_signed_read_url_builds_full_url(monkeypatch):
    fake = _FakeStorage()
    monkeypatch.setattr(supabase, "admin", lambda: _FakeAdmin(fake))
    monkeypatch.setattr(
        supabase, "get_settings",
        lambda: type("S", (), {"supabase_url": "https://proj.supabase.co"})(),
    )

    url = supabase.create_signed_read_url("artist-images", "artist-1/pic.jpg")

    assert fake.calls[0] == ("from_", "artist-images")
    # a sensible ~1h default expiry is passed through to Supabase
    assert fake.calls[1] == ("create_signed_url", "artist-1/pic.jpg", 3600)
    assert url == (
        "https://proj.supabase.co/storage/v1"
        "/object/sign/artist-images/artist-1/pic.jpg?token=readtok"
    )


# If the library already returns a FULL absolute URL (the currently installed supabase-py does —
# verified live against brink-dev), the helper must NOT prefix the host again (that doubled URL
# 404s and every image breaks).
def test_create_signed_read_url_keeps_absolute_url(monkeypatch):
    class _AbsoluteStorage(_FakeStorage):
        def create_signed_url(self, path, expires_in):
            return {
                "signedURL": f"https://proj.supabase.co/storage/v1/object/sign/artist-images/{path}?token=readtok"
            }

    monkeypatch.setattr(supabase, "admin", lambda: _FakeAdmin(_AbsoluteStorage()))
    monkeypatch.setattr(
        supabase, "get_settings",
        lambda: type("S", (), {"supabase_url": "https://proj.supabase.co"})(),
    )

    url = supabase.create_signed_read_url("artist-images", "artist-1/pic.jpg")

    assert url == (
        "https://proj.supabase.co/storage/v1"
        "/object/sign/artist-images/artist-1/pic.jpg?token=readtok"
    )


# A caller can override the expiry (seconds); it is forwarded to Supabase unchanged.
def test_create_signed_read_url_honours_custom_expiry(monkeypatch):
    fake = _FakeStorage()
    monkeypatch.setattr(supabase, "admin", lambda: _FakeAdmin(fake))
    monkeypatch.setattr(
        supabase, "get_settings",
        lambda: type("S", (), {"supabase_url": "https://proj.supabase.co"})(),
    )

    supabase.create_signed_read_url("artist-images", "artist-1/pic.jpg", expires_in=60)

    assert fake.calls[1] == ("create_signed_url", "artist-1/pic.jpg", 60)


# --- public_object_url (T48) -------------------------------------------------------

# Builds the public object URL for a PUBLIC bucket (the avatars bucket, T48): no signing needed —
# the object is world-readable, so the URL is a plain, stable path off SUPABASE_URL.
def test_public_object_url_builds_public_path(monkeypatch):
    monkeypatch.setattr(
        supabase, "get_settings",
        lambda: type("S", (), {"supabase_url": "https://proj.supabase.co"})(),
    )
    url = supabase.public_object_url("avatars", "user-1/pic.jpg")
    assert url == "https://proj.supabase.co/storage/v1/object/public/avatars/user-1/pic.jpg"


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
