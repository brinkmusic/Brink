# WHAT THIS FILE IS
# Checks the "me" account-action endpoint (app/routers/me.py, T55):
#   POST /api/me/become-artist -> flip the LOGGED-IN account to an artist account.
# It is login-gated, and the flag is always set on the authenticated caller (never a
# client-supplied id), so it can't be spoofed. Becoming an artist unlocks the /artist studio.
# These use a real in-memory db_session (not a MagicMock) so we can assert the isArtist flag
# was actually persisted.

from datetime import datetime, timezone

from app.db import get_session
from app.deps import AuthError, require_user
from app.main import app
from app.models import User


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
