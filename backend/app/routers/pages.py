# WHAT THIS FILE IS
# Serves Brink's actual web PAGES — the HTML a person sees in their browser — as
# opposed to the JSON API in the other routers (health, auth, posts). WHY this
# exists: per ADR-0013 we build the frontend in Python. Instead of a separate
# React/TypeScript app, FastAPI fills in HTML templates (in app/templates/) and
# sends whole pages to the browser. One language, one codebase.
#
# Pages so far:
#   GET /      -> the public landing page (what a visitor sees before signing in)
#   GET /feed  -> the feed of songs people have shared, read from the posts the
#                 T10 API creates (Post + Track rows). Read-only, no login needed.

import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select

from app.db import get_session
from app.deps import AuthError, require_user
from app.models import Post, Track

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


# When someone opens the site root ("/") in a browser, run this and return a web page.
# response_class=HTMLResponse tells FastAPI "this returns HTML, not JSON".
@router.get("/", response_class=HTMLResponse)
def home(request: Request):
    # Render templates/home.html. Jinja2Templates needs the incoming `request`, and
    # we hand it a small dictionary of values the template can drop in (here, the
    # browser-tab title). The template itself decides where each value goes.
    return templates.TemplateResponse(
        request,
        "home.html",
        {"page_title": "Brink"},
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


# Read the most recent shared songs from the database, newest first. This is the SAME
# data the T10 posts API creates (Post rows, each joined to its Track). We return plain
# dictionaries — not live database rows — so the template can safely use them after the
# database session has closed.
def _recent_posts(session: Session, limit: int = 20) -> list[dict]:
    try:
        rows = session.exec(
            # Post JOINed to its Track (same join the T10 GET /api/posts uses), newest
            # first, capped so the page never tries to render thousands of rows.
            select(Post, Track)
            .join(Track, Track.spotify_id == Post.track_id)
            .order_by(Post.created_at.desc())
            .limit(limit)
        ).all()
    except Exception as e:  # noqa: BLE001 — any DB problem should just show an empty feed
        # No database reachable (e.g. running locally without credentials) or a transient
        # outage: log it and show an empty feed rather than crashing the whole page.
        logger.warning("feed query failed, showing empty feed: %s", e)
        return []

    return [
        {
            "user_id": post.user_id,
            "caption": post.caption,
            "source": post.source.value,
            "title": track.title,
            "artist": track.artist_name,
            "album_art": track.album_art_url,
            "when": _ago(post.created_at),
        }
        for post, track in rows
    ]


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
        require_user(request, session=session, response=refreshed)
    except AuthError:
        return RedirectResponse("/auth/login", status_code=303)

    posts = _recent_posts(session)
    page = templates.TemplateResponse(
        request,
        "feed.html",
        {"page_title": "Feed · Brink", "posts": posts},
    )
    for key, value in refreshed.raw_headers:
        if key == b"set-cookie":
            page.raw_headers.append((key, value))
    return page
