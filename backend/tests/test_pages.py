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
