# WHAT THIS FILE IS
# Automated checks for the browser-facing web pages (the HTML people see), as
# opposed to the JSON API. WHY: ADR-0013 serves the frontend from FastAPI via
# Jinja templates, so we want a test that confirms the landing page actually
# renders — returns a 200, is HTML (not JSON), and contains the real Brink copy —
# so a future change can't silently break the page without CI catching it.

# The `client` fixture (a fake HTTP client) comes from conftest.py.


# The landing page loads and comes back as an HTML document.
def test_home_page_renders_html(client):
    res = client.get("/")
    assert res.status_code == 200  # 200 = OK
    # It must be a web page, not the JSON envelope the API returns.
    assert res.headers["content-type"].startswith("text/html")


# The page actually contains Brink's landing content (not an empty shell). We
# check for the brand, the headline, and the sign-in call to action — the three
# things a visitor must see.
def test_home_page_shows_landing_content(client):
    body = client.get("/").text
    assert "brink" in body
    assert "Your listening, made social." in body
    assert "Continue with Spotify" in body


# The stylesheet the pages depend on is served (a broken link here would leave
# the page unstyled). We only assert it loads and is CSS.
def test_stylesheet_is_served(client):
    res = client.get("/static/brink.css")
    assert res.status_code == 200
    assert "text/css" in res.headers["content-type"]


# ---- Feed page (reads the posts the T10 API creates) ----

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.db import get_session
from app.main import app
from app.models import Post, PostSource, Track
from app.security import session as login_session
from app.security import supabase


def _login(client, monkeypatch):
    # Sign a fake user in for feed tests: the feed is login-gated (T09), so we plant a
    # valid session cookie and fake the Supabase token check the same way the auth unit
    # tests do — no real Spotify/Supabase.
    su = SimpleNamespace(
        id="abcdef12-3456-7890-abcd-ef1234567890",
        email=None,
        user_metadata={},
        app_metadata={},
    )
    monkeypatch.setattr(login_session, "decode", lambda raw: {"access_token": "AT", "refresh_token": "RT"})
    monkeypatch.setattr(supabase, "get_user_from_token", lambda t: su if t == "AT" else None)
    client.cookies.set(login_session.SESSION_COOKIE, "x")


# An anonymous visitor is redirected to Spotify login instead of seeing the feed (T09).
def test_feed_redirects_anonymous_to_login(client):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    res = client.get("/feed", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/auth/login"


# With real posts in the database, a LOGGED-IN user's feed renders them — proving the
# page is wired to the actual Post/Track data (not showing hardcoded content). We seed a
# throwaway in-memory database (the `db_session` fixture) and point the app at it.
def test_feed_shows_real_posts(client, db_session, monkeypatch):
    track = Track(spotify_id="t_redbone", title="Redbone", artist_name="Childish Gambino")
    post = Post(
        user_id="u_demo",
        track_id="t_redbone",
        caption="a whole vibe",
        source=PostSource.MANUAL,
    )
    db_session.add(track)
    db_session.add(post)
    db_session.commit()

    # Make the feed page use our seeded in-memory database for this test, and sign in.
    app.dependency_overrides[get_session] = lambda: db_session
    _login(client, monkeypatch)

    res = client.get("/feed")
    assert res.status_code == 200
    body = res.text
    assert "Redbone" in body            # the track title
    assert "Childish Gambino" in body   # the artist
    assert "a whole vibe" in body       # the caption


# With no posts, a logged-in user's feed still returns a page (never crashes) and shows
# the empty state — exactly what a brand-new or offline app looks like.
def test_feed_empty_state(client, db_session, monkeypatch):
    app.dependency_overrides[get_session] = lambda: db_session  # empty database
    _login(client, monkeypatch)
    res = client.get("/feed")
    assert res.status_code == 200
    assert "No songs shared yet" in res.text
