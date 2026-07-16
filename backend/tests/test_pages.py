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


# ---- Feed page (reuses build_feed: posts from people you follow + your own) ----

from types import SimpleNamespace
from datetime import datetime, timezone
from unittest.mock import MagicMock

from app.db import get_session
from app.main import app
from app.models import (
    ArtistPost,
    Comment,
    Follow,
    Play,
    Post,
    PostSource,
    Reaction,
    ReactionType,
    Track,
    User,
)
from app.security import session as login_session
from app.security import supabase

# The Supabase user id _login signs in as. The feed only shows a viewer's own posts (plus the
# people they follow), so tests author their posts under the viewer that require_user returns —
# which is looked up by supabase_user_id, not the primary key.
_VIEWER_ID = "abcdef12-3456-7890-abcd-ef1234567890"


def _login(client, monkeypatch):
    # Sign a fake user in for feed tests: the feed is login-gated (T09), so we plant a
    # valid session cookie and fake the Supabase token check the same way the auth unit
    # tests do — no real Spotify/Supabase.
    su = SimpleNamespace(id=_VIEWER_ID, email=None, user_metadata={}, app_metadata={})
    monkeypatch.setattr(login_session, "decode", lambda raw: {"access_token": "AT", "refresh_token": "RT"})
    monkeypatch.setattr(supabase, "get_user_from_token", lambda t: su if t == "AT" else None)
    client.cookies.set(login_session.SESSION_COOKIE, "x")


def _seed_viewer(db_session):
    # Create the viewer's Brink user, keyed by supabase_user_id so require_user returns THIS
    # row (its .id then matches the posts/reactions we attribute to the viewer). Returns it.
    viewer = User(supabase_user_id=_VIEWER_ID, handle="viewer", display_name="Viewer",
                  created_at=datetime.now(timezone.utc))
    db_session.add(viewer)
    db_session.commit()
    db_session.refresh(viewer)
    return viewer


# An anonymous visitor is redirected to Spotify login instead of seeing the feed (T09).
def test_feed_redirects_anonymous_to_login(client):
    app.dependency_overrides[get_session] = lambda: MagicMock()
    res = client.get("/feed", follow_redirects=False)
    assert res.status_code == 303
    assert res.headers["location"] == "/auth/login"


# With a real post by the viewer, their feed renders it — proving the page is wired to the
# real feed data (not hardcoded). We seed a throwaway in-memory database and point the app
# at it.
def test_feed_shows_real_posts(client, db_session, monkeypatch):
    # Parents before children — the test DB enforces foreign keys. The post is the viewer's
    # own so it shows in their feed (which is follow + own).
    viewer = _seed_viewer(db_session)
    db_session.add(Track(spotify_id="t_redbone", title="Redbone", artist_name="Childish Gambino"))
    db_session.commit()
    db_session.add(Post(user_id=viewer.id, track_id="t_redbone", caption="a whole vibe",
                        source=PostSource.MANUAL))
    db_session.commit()

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


# ---- T41: feed shows live reaction counts + highlights the viewer's own reactions ----


def test_feed_shows_reaction_counts_and_marks_own(client, db_session, monkeypatch):
    # The viewer's own post, plus another user who also reacts to it (parents before children —
    # the test DB enforces foreign keys, and a Reaction references both a Post and a User).
    viewer = _seed_viewer(db_session)
    other = User(handle="other", display_name="Other", created_at=datetime.now(timezone.utc))
    db_session.add(other)
    db_session.add(Track(spotify_id="t_song", title="Song One", artist_name="Artist One"))
    db_session.commit()
    db_session.refresh(other)
    post = Post(user_id=viewer.id, track_id="t_song", source=PostSource.MANUAL)
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)

    # Two hearts (one is the VIEWER's own) and one fire. Sparkle stays at zero.
    db_session.add(Reaction(post_id=post.id, user_id=viewer.id, type=ReactionType.HEART))
    db_session.add(Reaction(post_id=post.id, user_id=other.id, type=ReactionType.HEART))
    db_session.add(Reaction(post_id=post.id, user_id=other.id, type=ReactionType.FIRE))
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session
    _login(client, monkeypatch)

    body = client.get("/feed").text

    # The reaction bar is wired to this post, with a button per type.
    assert f'data-post-id="{post.id}"' in body
    assert 'data-type="HEART"' in body
    assert 'data-type="FIRE"' in body
    assert 'data-type="SPARKLE"' in body
    # Counts render: heart 2, fire 1, sparkle 0 (the count is the span's text).
    assert ">2</span>" in body  # hearts
    assert ">1</span>" in body  # fire
    # The viewer's own heart is highlighted as already tapped.
    assert "reacted" in body


def test_feed_reactions_not_marked_for_other_viewer(client, db_session, monkeypatch):
    # The viewer's own post with a reaction left by SOMEONE ELSE: the count shows, but nothing
    # is marked as the viewer's.
    viewer = _seed_viewer(db_session)
    other = User(handle="other", display_name="Other", created_at=datetime.now(timezone.utc))
    db_session.add(other)
    db_session.add(Track(spotify_id="t_x", title="Track X", artist_name="Artist X"))
    db_session.commit()
    db_session.refresh(other)
    post = Post(user_id=viewer.id, track_id="t_x", source=PostSource.MANUAL)
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    db_session.add(Reaction(post_id=post.id, user_id=other.id, type=ReactionType.HEART))
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session
    _login(client, monkeypatch)  # signs in as _VIEWER_ID, who left no reactions

    body = client.get("/feed").text
    # The heart count shows (1), but the viewer hasn't tapped anything.
    assert 'aria-pressed="true"' not in body
    assert 'aria-pressed="false"' in body


# ---- T42: feed post cards carry a comment section with the live comment count ----


def test_feed_shows_comment_section_and_count(client, db_session, monkeypatch):
    viewer = _seed_viewer(db_session)
    db_session.add(Track(spotify_id="t_c", title="Commented Song", artist_name="Artist"))
    db_session.commit()
    post = Post(user_id=viewer.id, track_id="t_c", source=PostSource.MANUAL)
    db_session.add(post)
    db_session.commit()
    db_session.refresh(post)
    db_session.add(Comment(post_id=post.id, user_id=viewer.id, body="first!"))
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session
    _login(client, monkeypatch)

    body = client.get("/feed").text
    # The comment section is present and wired to this post, with an add-comment input.
    assert f'class="comments" data-post-id="{post.id}"' in body
    assert 'onclick="toggleComments(this)"' in body
    assert 'name="body"' in body
    # The comment count from build_feed renders (this post has one comment).
    assert 'class="comment-count">1<' in body


# ---- T40: the composer (search + share a song) renders on the feed ----


def test_feed_has_composer(client, db_session, monkeypatch):
    _seed_viewer(db_session)
    app.dependency_overrides[get_session] = lambda: db_session
    _login(client, monkeypatch)

    body = client.get("/feed").text
    assert 'class="composer' in body               # the composer block is present
    assert "composerSearch(this)" in body          # the search box is wired
    assert "/static/composer.js" in body           # the script is loaded


# ---- T43: profile page + follow button ----


def test_profile_page_shows_follow_button(client, db_session, monkeypatch):
    _seed_viewer(db_session)
    target = User(handle="artist-x", display_name="Artist X",
                  created_at=datetime.now(timezone.utc))
    db_session.add(target)
    db_session.commit()
    db_session.refresh(target)

    app.dependency_overrides[get_session] = lambda: db_session
    _login(client, monkeypatch)

    body = client.get("/u/artist-x").text
    assert "Artist X" in body
    assert "followers" in body
    assert f'data-user-id="{target.id}"' in body   # follow button wired to this user
    assert "toggleFollow(this)" in body


def test_profile_shows_following_state_and_counts(client, db_session, monkeypatch):
    viewer = _seed_viewer(db_session)
    target = User(handle="followed-one", display_name="Followed",
                  created_at=datetime.now(timezone.utc))
    db_session.add(target)
    db_session.commit()
    db_session.refresh(target)
    # The viewer already follows the target -> button reads "Following"; target has 1 follower.
    db_session.add(Follow(follower_id=viewer.id, following_id=target.id))
    db_session.commit()

    app.dependency_overrides[get_session] = lambda: db_session
    _login(client, monkeypatch)

    body = client.get("/u/followed-one").text
    assert 'data-following="true"' in body
    assert "Following" in body
    assert 'class="follower-count">1<' in body


def test_own_profile_has_no_follow_button(client, db_session, monkeypatch):
    _seed_viewer(db_session)  # the viewer's handle is "viewer"
    app.dependency_overrides[get_session] = lambda: db_session
    _login(client, monkeypatch)
    body = client.get("/u/viewer").text
    assert "toggleFollow(this)" not in body  # you can't follow yourself


def test_profile_missing_handle_is_404(client, db_session, monkeypatch):
    _seed_viewer(db_session)
    app.dependency_overrides[get_session] = lambda: db_session
    _login(client, monkeypatch)
    res = client.get("/u/nobody-here")
    assert res.status_code == 404
    assert "couldn't find that profile" in res.text


# ---- T44: profile listening summary + now-playing badge ----


def _seed_target_with_plays(db_session, handle="dj-nova"):
    # A user (not the viewer) with a couple of plays, so we can view THEIR profile and see the
    # listening summary. Track must be inserted before the Play that references it (FKs are on).
    target = User(handle=handle, display_name="DJ Nova", spotify_id="sp_nova",
                  created_at=datetime.now(timezone.utc))
    db_session.add(target)
    db_session.add(Track(spotify_id="t_pulse", title="Pulse", artist_name="Nova"))
    db_session.commit()
    db_session.refresh(target)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    db_session.add(Play(user_id=target.id, track_id="t_pulse", played_at=now))
    db_session.commit()
    return target


def test_profile_shows_listening_summary(client, db_session, monkeypatch):
    _seed_viewer(db_session)
    _seed_target_with_plays(db_session)
    app.dependency_overrides[get_session] = lambda: db_session
    _login(client, monkeypatch)

    body = client.get("/u/dj-nova").text
    assert "Listening" in body
    assert "Pulse" in body            # the played track shows in top tracks / recent
    assert "day streak" in body
    assert "plays" in body


def test_own_profile_without_spotify_shows_link_prompt(client, db_session, monkeypatch):
    # The viewer (handle "viewer") has no linked Spotify and no plays -> link-Spotify prompt.
    _seed_viewer(db_session)
    # No Spotify token exists, so now-playing resolves to None without any network call; stub it
    # anyway to keep the test hermetic.
    monkeypatch.setattr("app.spotify.get_currently_playing", lambda s, u: None)
    app.dependency_overrides[get_session] = lambda: db_session
    _login(client, monkeypatch)

    body = client.get("/u/viewer").text
    assert "Link Spotify" in body


def test_own_profile_shows_now_playing_badge(client, db_session, monkeypatch):
    _seed_viewer(db_session)
    # Pretend the viewer is currently playing a track (T20 shape: is_playing + normalized track).
    monkeypatch.setattr(
        "app.spotify.get_currently_playing",
        lambda s, u: {"is_playing": True,
                      "track": {"title": "Midnight", "artist_name": "Aurora",
                                "album_art_url": None}},
    )
    app.dependency_overrides[get_session] = lambda: db_session
    _login(client, monkeypatch)

    body = client.get("/u/viewer").text
    assert "Now playing" in body
    assert "Midnight" in body


# ---- T51: artist page + upload UI ----


def _ensure_artist_table(db_session):
    # The shared db_session fixture only builds a few tables; the artist page also reads ArtistPost.
    ArtistPost.__table__.create(db_session.get_bind(), checkfirst=True)


def _seed_artist(db_session):
    # An artist account (is_artist=True) keyed to the login id, so require_user returns them.
    artist = User(supabase_user_id=_VIEWER_ID, handle="the-artist", display_name="The Artist",
                  is_artist=True, created_at=datetime.now(timezone.utc))
    db_session.add(artist)
    db_session.commit()
    db_session.refresh(artist)
    return artist


def test_artist_page_shows_upload_for_artist(client, db_session, monkeypatch):
    _ensure_artist_table(db_session)
    _seed_artist(db_session)
    app.dependency_overrides[get_session] = lambda: db_session
    _login(client, monkeypatch)

    body = client.get("/artist").text
    assert 'class="artist-file"' in body            # the file picker is shown
    assert "/static/artist-upload.js" in body       # the upload script is loaded


def test_artist_page_hides_upload_for_non_artist(client, db_session, monkeypatch):
    _ensure_artist_table(db_session)
    _seed_viewer(db_session)  # a normal listener (is_artist defaults to False)
    app.dependency_overrides[get_session] = lambda: db_session
    _login(client, monkeypatch)

    body = client.get("/artist").text
    assert 'class="artist-file"' not in body        # no upload box for non-artists
    assert "Artist accounts only" in body


def test_artist_page_shows_existing_posts(client, db_session, monkeypatch):
    _ensure_artist_table(db_session)
    artist = _seed_artist(db_session)
    db_session.add(ArtistPost(artist_user_id=artist.id, image_url="the-artist/x.jpg",
                              caption="new EP out now"))
    db_session.commit()
    app.dependency_overrides[get_session] = lambda: db_session
    # The bucket is private, so the page must sign a READ url for each stored path (T53). Stub the
    # helper so no test hits Supabase — it just wraps the raw path into a recognisable signed URL.
    monkeypatch.setattr(
        "app.routers.pages.create_signed_read_url",
        lambda bucket, path: f"https://signed/{bucket}/{path}?token=readtok",
    )
    _login(client, monkeypatch)

    body = client.get("/artist").text
    assert "new EP out now" in body


# The private artist bucket rejects unauthenticated GETs, so the page must render a SIGNED read URL
# for each post's stored path — never the raw path (which would show a broken image). T53.
def test_artist_page_signs_image_read_urls(client, db_session, monkeypatch):
    _ensure_artist_table(db_session)
    artist = _seed_artist(db_session)
    db_session.add(ArtistPost(artist_user_id=artist.id, image_url="the-artist/x.jpg",
                              caption="cover art"))
    db_session.commit()
    app.dependency_overrides[get_session] = lambda: db_session
    captured = {}

    def fake_sign(bucket, path):
        captured["bucket"] = bucket
        captured["path"] = path
        return "https://signed/read-url?token=readtok"

    monkeypatch.setattr("app.routers.pages.create_signed_read_url", fake_sign)
    _login(client, monkeypatch)

    body = client.get("/artist").text
    # the helper was asked to sign the private bucket + the stored raw path
    assert captured == {"bucket": "artist-images", "path": "the-artist/x.jpg"}
    # the rendered <img> uses the signed URL, and the raw path is NOT emitted as an src
    assert 'src="https://signed/read-url?token=readtok"' in body
    assert 'src="the-artist/x.jpg"' not in body
