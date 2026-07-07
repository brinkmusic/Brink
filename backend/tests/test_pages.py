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

from app.db import get_session
from app.main import app
from app.models import Post, PostSource, Track


# With real posts in the database, the feed renders them — proving the page is wired
# to the actual Post/Track data (not showing hardcoded content). We seed a throwaway
# in-memory database (the `db_session` fixture) and point the app at it.
def test_feed_shows_real_posts(client, db_session):
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

    # Make the feed page use our seeded in-memory database for this test.
    app.dependency_overrides[get_session] = lambda: db_session

    res = client.get("/feed")
    assert res.status_code == 200
    body = res.text
    assert "Redbone" in body            # the track title
    assert "Childish Gambino" in body   # the artist
    assert "a whole vibe" in body       # the caption


# With no posts, the feed still returns a page (never crashes) and shows the empty
# state — important because that is exactly what a brand-new or offline app looks like.
def test_feed_empty_state(client, db_session):
    app.dependency_overrides[get_session] = lambda: db_session  # empty database
    res = client.get("/feed")
    assert res.status_code == 200
    assert "No songs shared yet" in res.text
