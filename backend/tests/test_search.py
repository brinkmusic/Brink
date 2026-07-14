# WHAT THIS FILE IS
# Automated checks for the catalog-search endpoint (T40): GET /api/search?q=. We fake the Spotify
# call (`search_tracks`) so the tests never hit the network — they verify the ENDPOINT's behavior:
# it requires login, validates the query, normalizes results to camelCase, and reports an upstream
# failure cleanly.

from datetime import datetime, timezone

from app.db import get_session
from app.main import app
from app.models import User


def _make_user(db_session):
    # A real user row + a real session, because the endpoint's rate-limit check writes to the DB.
    user = User(handle="searcher", display_name="Searcher", created_at=datetime.now(timezone.utc))
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# A signed-in user searching gets normalized, camelCase track results.
def test_search_returns_normalized_tracks(client, db_session, as_user, monkeypatch):
    user = _make_user(db_session)
    as_user(user, session=db_session)
    # Fake Spotify: return one snake_case track (the shape spotify.search_tracks produces).
    monkeypatch.setattr(
        "app.routers.search.search_tracks",
        lambda q, limit=10: [
            {"spotify_id": "t1", "title": "Redbone", "artist_name": "Childish Gambino",
             "album_art_url": "http://img/x.jpg", "popularity": 80}
        ],
    )
    res = client.get("/api/search?q=redbone")
    assert res.status_code == 200
    data = res.json()["data"]
    assert len(data) == 1
    # camelCase out (matches what the composer posts back to POST /api/posts).
    assert data[0]["spotifyId"] == "t1"
    assert data[0]["title"] == "Redbone"
    assert data[0]["artistName"] == "Childish Gambino"


# An empty query is rejected up front as a 400 (never reaches Spotify).
def test_search_empty_query_is_400(client, db_session, as_user):
    user = _make_user(db_session)
    as_user(user, session=db_session)
    res = client.get("/api/search?q=")
    assert res.status_code == 400


# Search requires a login (Brink is private).
def test_search_requires_login(client):
    res = client.get("/api/search?q=redbone")
    assert res.status_code == 401


# When Spotify is unavailable (no credentials / upstream error), search_tracks returns None and the
# endpoint reports a clean 502 rather than a 500.
def test_search_unavailable_is_502(client, db_session, as_user, monkeypatch):
    user = _make_user(db_session)
    as_user(user, session=db_session)
    monkeypatch.setattr("app.routers.search.search_tracks", lambda q, limit=10: None)
    res = client.get("/api/search?q=redbone")
    assert res.status_code == 502
