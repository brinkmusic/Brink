# WHAT THIS FILE IS
# Serves Brink's actual web PAGES — the HTML a person sees in their browser — as
# opposed to the JSON API in the other routers (health, auth, posts). WHY this
# exists: per ADR-0013 we build the frontend in Python. Instead of a separate
# React/TypeScript app, FastAPI fills in HTML templates (in app/templates/) and
# sends whole pages to the browser. One language, one codebase.
#
# Pages so far:
#   GET /      -> the public landing page (what a visitor sees before signing in)
#   GET /feed  -> the feed page. Reuses the shared build_feed() (app/routers/feed.py) so it
#                 shows the SAME posts as GET /api/feed (people you follow + your own), each
#                 with live reaction counts. Login-gated (T09); the reaction buttons call the
#                 T11 reactions API from the browser (T41).

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func
from sqlmodel import Session, select

from app import spotify
from app.db import get_session
from app.deps import AuthError, require_user
from app.models import ArtistPost, Follow, Post, Track, User
from app.routers.artist import UPLOAD_BUCKET
from app.routers.feed import build_feed
from app.security.supabase import create_signed_read_url
from app.stats import listening_summary

logger = logging.getLogger(__name__)

# Where the HTML templates live (backend/app/templates/). We build the path relative
# to THIS file (parent.parent = app/), so it works no matter which folder the server
# was started from.
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"

# Jinja2 is the templating tool: it takes an .html file with placeholders and fills
# them in with values we pass. `templates` is the thing we call to render a page.
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# A router groups related routes; app/main.py plugs it into the app.
router = APIRouter()


# Figure out who (if anyone) is logged in, WITHOUT forcing a login. The gated pages call
# require_user, which redirects anonymous visitors to Spotify — but the landing page ("/") is
# public, so it must still render for a signed-out visitor. This helper reuses the SAME session
# check (require_user) but swallows the "not logged in" error and returns None instead, so the
# nav (T47) can show the logged-in links to a signed-in user who lands on "/" and the public nav
# to everyone else. It never raises: any auth problem just means "treat as logged out".
def _optional_viewer(request: Request, session: Session) -> User | None:
    try:
        # A scratch Response absorbs any refreshed-session cookie require_user might set; the
        # landing page doesn't need to persist it (the next gated page will), so we discard it.
        return require_user(request, session=session, response=Response())
    except Exception:  # noqa: BLE001 — an unauthenticated / undecodable session is simply "logged out"
        return None


# When someone opens the site root ("/") in a browser, run this and return a web page.
# response_class=HTMLResponse tells FastAPI "this returns HTML, not JSON".
@router.get("/", response_class=HTMLResponse)
def home(request: Request, session: Session = Depends(get_session)):
    # Render templates/home.html. Jinja2Templates needs the incoming `request`, and
    # we hand it a small dictionary of values the template can drop in (here, the
    # browser-tab title). The template itself decides where each value goes.
    # `viewer` lets the shared nav (base.html, T47) show the in-app links to a signed-in
    # visitor while staying public for everyone else.
    return templates.TemplateResponse(
        request,
        "home.html",
        {"page_title": "Brink", "viewer": _optional_viewer(request, session)},
    )


# Turn a timestamp into a friendly "3m ago" style label for the feed. WHY here (not
# in the template): Jinja has no built-in "time ago", so we compute the words in
# Python and pass a ready-to-show string.
def _ago(when: datetime) -> str:
    now = datetime.now(timezone.utc)
    # Posts are stored in UTC; if the value has no timezone attached, treat it as UTC
    # so the subtraction below doesn't error on mixing naive/aware datetimes.
    if when.tzinfo is None:
        when = when.replace(tzinfo=timezone.utc)
    minutes = int((now - when).total_seconds() // 60)
    if minutes < 1:
        return "just now"
    if minutes < 60:
        return f"{minutes}m ago"
    hours = minutes // 60
    if hours < 24:
        return f"{hours}h ago"
    return f"{hours // 24}d ago"


# Build the list of feed posts for the template. We REUSE the shared feed builder
# (app/routers/feed.build_feed) so the page shows EXACTLY the same feed as GET /api/feed
# (posts from people you follow plus your own, with reaction counts and which reactions are
# yours) — no duplicated query logic. Then we reshape each item for the template: flatten the
# nested track fields, turn the ISO timestamp into a friendly "3m ago", and collect the
# reaction types the viewer already tapped into a set the template can test with `in`.
def _feed_items(session: Session, user) -> list[dict]:
    try:
        raw = build_feed(session, user)
    except Exception as e:  # noqa: BLE001 — any DB problem shows an empty feed, never a crash
        # No database reachable (e.g. running locally without credentials) or a transient
        # outage: log it and show an empty feed rather than crashing the whole page.
        logger.warning("feed build failed, showing empty feed: %s", e)
        return []

    items = []
    for it in raw:
        # viewerReactions is {type: True/False}; keep just the types set to True.
        mine = {kind for kind, on in it["viewerReactions"].items() if on}
        items.append(
            {
                "id": it["id"],
                "author": it["author"]["displayName"],
                "author_handle": it["author"]["handle"],  # for linking to their profile (T43)
                "title": it["track"]["title"],
                "artist": it["track"]["artistName"],
                "album_art": it["track"]["albumArtUrl"],
                "caption": it["caption"],
                "when": _ago(datetime.fromisoformat(it["createdAt"])),
                "counts": it["reactionCounts"],
                "mine": mine,
                "comment_count": it["commentCount"],
            }
        )
    return items


# The feed page: a list of the songs people have shared. Read-only, so no login is
# required (matching the T10 GET /api/posts endpoint, which is also public).
@router.get("/feed", response_class=HTMLResponse)
def feed(request: Request, session: Session = Depends(get_session)):
    # Gate the feed on login (T09): a visitor who isn't signed in is sent to Spotify login.
    # We authenticate against a scratch Response so that if require_user REFRESHES the
    # session (Supabase rotates refresh tokens on refresh), we can carry its refreshed
    # session cookie onto the page response below — otherwise the browser would keep an
    # old, now-rotated token and eventually be logged out.
    refreshed = Response()
    try:
        user = require_user(request, session=session, response=refreshed)
    except AuthError:
        return RedirectResponse("/auth/login", status_code=303)

    # Reuse the shared feed builder so the page matches GET /api/feed exactly (T41).
    posts = _feed_items(session, user)
    page = templates.TemplateResponse(
        request,
        "feed.html",
        {"page_title": "Feed · Brink", "posts": posts, "viewer": user},
    )
    for key, value in refreshed.raw_headers:
        if key == b"set-cookie":
            page.raw_headers.append((key, value))
    return page


# Gather everything a profile page needs: the person, their follower/following counts, whether the
# viewer already follows them, and their own posts (newest-first). This is the minimal profile that
# gives the Follow button (T43) a home; the full "Wrapped"-style stats/cluster/compatibility come
# with T44 (which needs the profile API, T14). Returns None if there's no user with that handle.
def _profile_data(session: Session, handle: str, viewer_id: str) -> dict | None:
    person = session.exec(select(User).where(User.handle == handle)).first()
    if person is None:
        return None

    # follower_count = people who follow THEM; following_count = people THEY follow.
    follower_count = session.exec(
        select(func.count()).select_from(Follow).where(Follow.following_id == person.id)
    ).one()
    following_count = session.exec(
        select(func.count()).select_from(Follow).where(Follow.follower_id == person.id)
    ).one()
    # Does the viewer already follow this person? (Follow's PK is (follower_id, following_id).)
    is_following = session.get(Follow, (viewer_id, person.id)) is not None

    # Their posts, newest-first, joined to each track (simple read-only cards on the profile).
    rows = session.exec(
        select(Post, Track)
        .join(Track, Track.spotify_id == Post.track_id)
        .where(Post.user_id == person.id)
        .order_by(Post.created_at.desc())
    ).all()
    posts = [
        {
            "title": track.title,
            "artist": track.artist_name,
            "album_art": track.album_art_url,
            "caption": post.caption,
            "when": _ago(post.created_at),
        }
        for post, track in rows
    ]

    # The listening summary (T44): what this person actually plays, computed live from their Play
    # history (app/stats.py). The "recent" rows carry a raw played_at datetime; format it to a
    # friendly "3h ago" here, the same way posts do, so the template just prints a string.
    summary = listening_summary(session, person.id)
    recent = [
        {"title": r["title"], "artist": r["artist"], "album_art": r["album_art"],
         "when": _ago(r["played_at"])}
        for r in summary["recent"]
    ]

    return {
        "id": person.id,
        "display_name": person.display_name,
        "handle": person.handle,
        "avatar_url": person.avatar_url,
        "follower_count": follower_count,
        "following_count": following_count,
        "is_following": is_following,
        "is_self": person.id == viewer_id,  # hide the Follow button on your own profile
        # Does THIS person have a linked Spotify? Drives the "link Spotify" prompt on your own
        # profile when you haven't connected an account (a handle-only user has no plays to show).
        "has_spotify": person.spotify_id is not None,
        "top_tracks": summary["top_tracks"],
        "top_artists": summary["top_artists"],
        "recent": recent,
        "plays_30d": summary["plays_30d"],
        "streak": summary["streak"],
        "posts": posts,
    }


# A user's profile page: their header, a Follow/Unfollow button + follower counts (T43), and their
# posts. Login-gated like the rest of the app. `handle` comes from the URL, e.g. /u/andrea-ab12cd.
@router.get("/u/{handle}", response_class=HTMLResponse)
def profile(handle: str, request: Request, session: Session = Depends(get_session)):
    refreshed = Response()
    try:
        viewer = require_user(request, session=session, response=refreshed)
    except AuthError:
        return RedirectResponse("/auth/login", status_code=303)

    data = _profile_data(session, handle, viewer_id=viewer.id)
    if data is None:
        # No such handle — render a friendly 404 page rather than a raw error.
        page = templates.TemplateResponse(
            request,
            "profile_missing.html",
            {"page_title": "Not found · Brink", "viewer": viewer},
            status_code=404,
        )
    else:
        # Now-playing badge (T44/UI-10): only on your OWN profile. The now-playing lookup (T20) is
        # "me"-scoped — it uses the logged-in user's own Spotify token — so we can show the viewer
        # their own current track, but not someone else's. get_currently_playing returns None (never
        # raises) when nothing is playing / Spotify isn't linked, so the badge simply hides.
        now_playing = None
        if data["is_self"]:
            playing = spotify.get_currently_playing(session, viewer.id)
            if playing and playing.get("is_playing") and playing.get("track"):
                now_playing = playing["track"]
        page = templates.TemplateResponse(
            request,
            "profile.html",
            {"page_title": f"{data['display_name']} · Brink", "p": data,
             "now_playing": now_playing, "viewer": viewer},
        )
    for key, value in refreshed.raw_headers:
        if key == b"set-cookie":
            page.raw_headers.append((key, value))
    return page


# The artist "behind-the-scenes" page (T51): an artist account's promo posts, plus (for the artist
# themselves) an upload box to add a new one. Login-gated; the upload UI only shows for artist
# accounts (User.is_artist) — the T50 API is the real gate (403 for non-artists), this just hides
# the box for everyone else. The actual file upload goes browser -> Supabase Storage via a signed
# URL (see static/artist-upload.js).
@router.get("/artist", response_class=HTMLResponse)
def artist_page(request: Request, session: Session = Depends(get_session)):
    refreshed = Response()
    try:
        user = require_user(request, session=session, response=refreshed)
    except AuthError:
        return RedirectResponse("/auth/login", status_code=303)

    # This artist's existing promo posts, newest-first.
    rows = session.exec(
        select(ArtistPost)
        .where(ArtistPost.artist_user_id == user.id)
        .order_by(ArtistPost.created_at.desc())
    ).all()
    # T50 stores each post's image as a bare storage PATH (e.g. "user-id/pic.jpg") in the PRIVATE
    # artist-images bucket, which the browser cannot fetch directly. Sign a short-lived read URL
    # for each one here (T53), so the template gets an <img src> that actually displays.
    posts = [
        {
            "image_url": create_signed_read_url(UPLOAD_BUCKET, post.image_url),
            "caption": post.caption,
            "when": _ago(post.created_at),
        }
        for post in rows
    ]

    page = templates.TemplateResponse(
        request,
        "artist.html",
        {"page_title": "Artist · Brink", "is_artist": user.is_artist, "posts": posts,
         "viewer": user},
    )
    for key, value in refreshed.raw_headers:
        if key == b"set-cookie":
            page.raw_headers.append((key, value))
    return page
