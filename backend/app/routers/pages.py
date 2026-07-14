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
from sqlmodel import Session

from app.db import get_session
from app.deps import AuthError, require_user
from app.routers.feed import build_feed

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
        {"page_title": "Feed · Brink", "posts": posts},
    )
    for key, value in refreshed.raw_headers:
        if key == b"set-cookie":
            page.raw_headers.append((key, value))
    return page
