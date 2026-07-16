# WHAT THIS FILE IS
# The auth routes for Brink's server-rendered frontend, in three parts:
#   1. Server-side Spotify LOGIN (T09, ADR-0013): GET /auth/login → /auth/callback →
#      /auth/logout. We run the OAuth handshake ourselves (no browser Supabase client),
#      set an encrypted session cookie, and capture the user's Spotify tokens on the way.
#   2. Email + PASSWORD signup/login (T03, ADR-0015): GET/POST /auth/signup,
#      GET/POST /auth/login-email, GET /auth/confirm. The "front door" for people WITHOUT a
#      Spotify account — it reuses the same session cookie + get_or_create_user as the Spotify
#      flow, so a handle-only account works everywhere the app already tolerates unlinked users.
#   3. The LEGACY browser capture endpoint POST /api/auth/capture-spotify — how the old
#      React SPA (retired in T60) forwarded its Spotify tokens. Nothing calls it anymore;
#      removing it is tracked as ticket T63.
# The Spotify paths store tokens ENCRYPTED so background jobs (the snapshot, T21) can later
# fetch the user's listening history. The password path never sees or stores a password —
# Supabase hashes it (ADR-0015).

import json
import re
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.deps import get_or_create_user, require_user
from app.models import SpotifyToken, User
from app.rate_limit import RateLimitError, enforce_rate_limit
from app.responses import fail, ok
from app.security import session as login_session
from app.security import supabase
from app.security.crypto import decrypt, encrypt

router = APIRouter()

# Jinja renders the email signup/login pages, the same way routers/pages.py renders the rest of
# the site (ADR-0013). We point at the same templates/ folder (parent.parent = app/).
_TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))

# ---- Email + password auth knobs (T03, ADR-0015) ----
# Password minimum is 6 characters (owner decision — matches Supabase's default). We check it
# in our form too so the user gets a friendly error before the round-trip to Supabase.
PASSWORD_MIN_LENGTH = 6

# First IP-keyed rate limits in the codebase (signup/login are unauthenticated, so there is no
# user id to key on — we key on client IP AND email). Module-level so tests can lower them.
# Caps are deliberately generous for a course demo but bound brute-force / signup abuse.
SIGNUP_RATE_LIMIT = 5          # sign-up attempts...
SIGNUP_RATE_WINDOW = 3600      # ...per hour, per IP and per email
LOGIN_RATE_LIMIT = 10          # log-in attempts...
LOGIN_RATE_WINDOW = 300        # ...per 5 minutes, per IP and per email

# CSRF cookie for the unauthenticated signup/login FORMS. The session cookie is SameSite=Lax
# (which already blocks most cross-site POSTs), but the forms themselves are anonymous POSTs, so
# we add a token: the GET form sets this encrypted cookie AND embeds the same token in a hidden
# field; the POST handler requires the two to match. Same pattern as the OAuth `state` cookie.
CSRF_COOKIE = "brink_csrf"
CSRF_COOKIE_MAX_AGE = 3600

# The Spotify permissions the login asks for. These are the scopes the snapshot (T21) and
# now-playing (T20) features depend on: read the user's email, recently-played, top tracks,
# and currently-playing. (Kept identical to what the old React SPA requested before T60.)
SPOTIFY_SCOPES = (
    "user-read-email user-read-recently-played user-top-read user-read-currently-playing"
)

# Short-lived cookie that carries the login handshake (the PKCE verifier + a CSRF state)
# from /auth/login to /auth/callback. Encrypted, httpOnly, and expires in minutes.
OAUTH_COOKIE = "brink_oauth"
OAUTH_COOKIE_MAX_AGE = 600  # seconds — the login round-trip should take well under this


def _set_cookie(response, name: str, value: str, max_age: int, secure: bool) -> None:
    # One place for our cookie hardening: httpOnly (JS can't read it → mitigates XSS token
    # theft), Secure in production (HTTPS only), SameSite=Lax (sent on top-level navigations
    # like the OAuth redirect, but not on cross-site sub-requests → CSRF defense).
    response.set_cookie(
        name, value, max_age=max_age, httponly=True, secure=secure, samesite="lax"
    )


def _login_failed(reason: str) -> HTMLResponse:
    # A friendly, self-contained "login didn't work" page. WHY not a 500: OAuth can fail for
    # ordinary reasons (the user hit "cancel", a stale/replayed callback), and those must
    # not look like a server crash. 400 = "this request was bad", with a link to retry.
    html = (
        "<!doctype html><html><head><meta charset='utf-8'><title>Login failed · Brink</title>"
        "<link rel='stylesheet' href='/static/brink.css'></head><body><main class='container'>"
        f"<h1>Couldn't sign you in</h1><p>{reason}</p>"
        "<p><a class='btn btn-spotify' href='/auth/login'>Try again</a></p>"
        "</main></body></html>"
    )
    return HTMLResponse(html, status_code=400)


@router.get("/auth/login")
def auth_login(request: Request):
    # Step 1 of server-side Spotify login: send the browser to Spotify's consent screen.
    # The callback URL is derived from the current origin, so this works unchanged on
    # localhost and on Render (the derived URL must be in Supabase's redirect allow-list).
    # We put the CSRF state IN the callback URL as a query param: Supabase preserves it and
    # echoes it back to the callback, giving us a value to check against the cookie below.
    state = secrets.token_urlsafe(32)
    redirect_to = f"{str(request.base_url).rstrip('/')}/auth/callback?state={state}"
    authorize_url, verifier = supabase.oauth_authorize(redirect_to, SPOTIFY_SCOPES)

    # Stash the state + the PKCE verifier in an encrypted handshake cookie so the callback
    # can (a) confirm the state matches and (b) complete the PKCE code exchange.
    handshake = encrypt(json.dumps({"state": state, "verifier": verifier}))

    # 307 keeps the method a GET as the browser follows the redirect to Spotify.
    response = RedirectResponse(authorize_url, status_code=307)
    _set_cookie(
        response,
        OAUTH_COOKIE,
        handshake,
        max_age=OAUTH_COOKIE_MAX_AGE,
        secure=request.url.scheme == "https",
    )
    return response


@router.get("/auth/callback")
def auth_callback(request: Request, session: Session = Depends(get_session)):
    # Step 2: Spotify (via Supabase) sends the browser back here with ?code=...&state=...
    # We verify the handshake, exchange the code for a session, provision the user, capture
    # their Spotify tokens, and set the login cookie. Any failure renders _login_failed,
    # never a 500 (ADR-0007).
    secure = request.url.scheme == "https"
    params = request.query_params

    # The user cancelled, or Spotify/Supabase reported a problem: show the friendly page.
    if params.get("error"):
        return _login_failed(params.get("error_description") or "Spotify sign-in was cancelled.")

    # The handshake cookie must be present and decryptable — without it this isn't a login
    # round-trip we started (or it's expired). Reject rather than trust the query alone.
    raw = request.cookies.get(OAUTH_COOKIE)
    if not raw:
        return _login_failed("Your login session expired. Please try again.")
    try:
        handshake = json.loads(decrypt(raw))
    except Exception:
        return _login_failed("Your login session was invalid. Please try again.")

    # CSRF check: the state echoed back by Supabase must match the one we stored.
    if not params.get("state") or params.get("state") != handshake.get("state"):
        return _login_failed("Your login session didn't match. Please try again.")

    code = params.get("code")
    if not code:
        return _login_failed("Spotify didn't return a login code. Please try again.")

    # Exchange the one-time code for a Supabase session (carries the Spotify provider
    # tokens). A failure here (bad/expired code, verifier mismatch) → friendly page.
    try:
        sb_session = supabase.exchange_code(code, handshake["verifier"])
    except Exception:
        return _login_failed("We couldn't complete your Spotify sign-in. Please try again.")
    if sb_session is None or getattr(sb_session, "user", None) is None:
        return _login_failed("We couldn't complete your Spotify sign-in. Please try again.")

    # Provision (or fetch) the Brink user from the Supabase identity — same handle policy
    # as the JSON API's require_user (reused, not re-implemented).
    user = get_or_create_user(session, sb_session.user)

    # Capture the Spotify provider tokens so background jobs can use them. Only if the
    # provider refresh token is present (it is on the initial OAuth exchange).
    provider_refresh = getattr(sb_session, "provider_refresh_token", None)
    provider_access = getattr(sb_session, "provider_token", None)
    if provider_refresh and provider_access:
        _store_spotify_token(session, user.id, provider_access, provider_refresh, SPOTIFY_SCOPES)
        session.commit()

    # Set the login cookie: the encrypted Supabase session tokens (require_user reads these
    # and re-verifies with Supabase on each request). 303 → the browser does a plain GET to
    # /feed after the POST-like OAuth exchange.
    response = RedirectResponse("/feed", status_code=303)
    login_session.set_cookie(
        response,
        sb_session.access_token,
        sb_session.refresh_token,
        getattr(sb_session, "expires_at", None),
        secure,
    )
    response.delete_cookie(OAUTH_COOKIE)  # handshake is single-use; clear it
    return response


@router.get("/auth/logout")
def auth_logout():
    # Clear the login cookie and return to the landing page. 303 → plain GET of "/".
    response = RedirectResponse("/", status_code=303)
    login_session.clear_cookie(response)
    return response


# ======================================================================================
# Email + password signup / login (T03, ADR-0015)
# ======================================================================================

# A minimal "looks like an email" check. WHY not a strict RFC validator: Supabase does the
# authoritative validation — this only catches obvious typos so we can show a friendly error
# before the round-trip. Requires text, an "@", and a dot in the domain part.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _client_ip(request: Request) -> str:
    # Best-effort client IP for the anonymous rate limits. Behind Render's proxy the socket peer
    # is the PROXY, not the user, so the real client IP is the FIRST entry of X-Forwarded-For
    # (each proxy appends the address it received from). Fall back to the direct socket peer for
    # local dev. SECURITY: this header can be spoofed, so IP limits are best-effort — they pair
    # with the per-email limit below and Supabase's own GoTrue limits (defense in depth, ADR-0015).
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _issue_csrf(response, secure: bool) -> str:
    # Mint a CSRF token, store it ENCRYPTED in a short-lived cookie, and return the plain token
    # for the form's hidden field. The POST handler compares the two (see _csrf_ok).
    token = secrets.token_urlsafe(32)
    _set_cookie(response, CSRF_COOKIE, encrypt(token), CSRF_COOKIE_MAX_AGE, secure)
    return token


def _csrf_ok(request: Request, submitted: str) -> bool:
    # The submitted hidden-field token must decrypt-match the value in the CSRF cookie. Any
    # missing/undecryptable/mismatched case is a fail. compare_digest avoids timing leaks.
    raw = request.cookies.get(CSRF_COOKIE)
    if not raw or not submitted:
        return False
    try:
        expected = decrypt(raw)
    except Exception:
        return False
    return secrets.compare_digest(expected, submitted)


def _auth_page(
    request: Request,
    template_name: str,
    *,
    status: int = 200,
    error: Optional[str] = None,
    info: Optional[str] = None,
    email: str = "",
    sent: bool = False,
):
    # Render a signup/login page in ONE pass with a fresh CSRF token, and set the matching
    # encrypted CSRF cookie on the response. This is the helper the routes actually call.
    secure = request.url.scheme == "https"
    token = secrets.token_urlsafe(32)
    response = templates.TemplateResponse(
        request,
        template_name,
        {
            "page_title": "Brink",
            "viewer": None,
            "error": error,
            "info": info,
            "email": email,
            "sent": sent,
            "csrf_token": token,
        },
        status_code=status,
    )
    _set_cookie(response, CSRF_COOKIE, encrypt(token), CSRF_COOKIE_MAX_AGE, secure)
    return response


@router.get("/auth/signup")
def auth_signup_form(request: Request):
    # The "create an account" page (a GET renders the empty form + a fresh CSRF token).
    return _auth_page(request, "signup.html")


@router.post("/auth/signup")
def auth_signup_submit(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    csrf_token: str = Form(""),
    session: Session = Depends(get_session),
):
    # Create an email/password account. Order: CSRF → validate → rate-limit → Supabase sign_up.
    # With email confirmations ON (ADR-0015), a successful sign-up does NOT log the person in —
    # we show a "check your inbox" state so they confirm before their first login.
    if not _csrf_ok(request, csrf_token):
        return _auth_page(request, "signup.html", status=400,
                          error="Your form session expired. Please try again.")

    email = email.strip().lower()
    problem = _validate_credentials(email, password)
    if problem:
        return _auth_page(request, "signup.html", status=400, error=problem, email=email)

    # Rate-limit by IP (broad abuse from one source) AND by email (repeated signups for one
    # address). enforce_rate_limit raises RateLimitError → we show a friendly 429, not a crash.
    try:
        enforce_rate_limit(session, subject=f"ip:{_client_ip(request)}", action="auth_signup",
                           limit=SIGNUP_RATE_LIMIT, window_seconds=SIGNUP_RATE_WINDOW)
        enforce_rate_limit(session, subject=f"email:{email}", action="auth_signup",
                           limit=SIGNUP_RATE_LIMIT, window_seconds=SIGNUP_RATE_WINDOW)
    except RateLimitError:
        return _auth_page(request, "signup.html", status=429, email=email,
                          error="Too many attempts. Please wait a bit and try again.")

    # Where Supabase's confirmation email should send the browser back (our /auth/confirm).
    redirect_to = f"{str(request.base_url).rstrip('/')}/auth/confirm"
    try:
        supabase.sign_up_email(email, password, email_redirect_to=redirect_to)
    except Exception:
        # Non-enumerating: Supabase's default enumeration protection returns success (no raise)
        # for an already-registered email, so reaching here is a genuine error, not "email taken".
        return _auth_page(request, "signup.html", status=400, email=email,
                          error="We couldn't create that account. Please try again.")

    # Success (including the enumeration-protected "already registered" case): show the inbox
    # state. We deliberately do NOT set a session cookie — the account isn't usable until
    # confirmed.
    return _auth_page(request, "signup.html", email=email, sent=True)


@router.get("/auth/login-email")
def auth_login_email_form(request: Request):
    # The email/password sign-in page (a GET renders the empty form + a fresh CSRF token).
    return _auth_page(request, "login_email.html")


@router.post("/auth/login-email")
def auth_login_email_submit(
    request: Request,
    email: str = Form(""),
    password: str = Form(""),
    csrf_token: str = Form(""),
    session: Session = Depends(get_session),
):
    # Log in with an email/password. On success: reuse the T09 machinery exactly —
    # get_or_create_user + login_session.set_cookie — and 303 to /feed.
    secure = request.url.scheme == "https"
    if not _csrf_ok(request, csrf_token):
        return _auth_page(request, "login_email.html", status=400,
                          error="Your form session expired. Please try again.")

    email = email.strip().lower()
    if not email or not password:
        return _auth_page(request, "login_email.html", status=400, email=email,
                          error="Enter your email and password.")

    try:
        enforce_rate_limit(session, subject=f"ip:{_client_ip(request)}", action="auth_login",
                           limit=LOGIN_RATE_LIMIT, window_seconds=LOGIN_RATE_WINDOW)
        enforce_rate_limit(session, subject=f"email:{email}", action="auth_login",
                           limit=LOGIN_RATE_LIMIT, window_seconds=LOGIN_RATE_WINDOW)
    except RateLimitError:
        return _auth_page(request, "login_email.html", status=429, email=email,
                          error="Too many attempts. Please wait a bit and try again.")

    # The SDK RAISES on bad credentials or an unconfirmed email. We catch everything and show ONE
    # generic message — never revealing whether the email exists (enumeration defense, ADR-0015).
    try:
        result = supabase.sign_in_password(email, password)
    except Exception:
        return _auth_page(request, "login_email.html", status=400, email=email,
                          error="Invalid email or password, or your email isn't confirmed yet.")

    sb_session = getattr(result, "session", None)
    sb_user = getattr(sb_session, "user", None) if sb_session else None
    if sb_session is None or sb_user is None or not getattr(sb_session, "access_token", None):
        return _auth_page(request, "login_email.html", status=400, email=email,
                          error="Invalid email or password, or your email isn't confirmed yet.")

    # Provision/fetch the Brink user from the Supabase identity (creates a handle account with
    # spotify_id = NULL on first login) and set the encrypted session cookie — same as Spotify.
    user = get_or_create_user(session, sb_user)
    response = RedirectResponse("/feed", status_code=303)
    login_session.set_cookie(
        response,
        sb_session.access_token,
        sb_session.refresh_token,
        getattr(sb_session, "expires_at", None),
        secure,
    )
    response.delete_cookie(CSRF_COOKIE)  # form is done; clear its single-use token
    return response


@router.get("/auth/confirm")
def auth_confirm(request: Request):
    # Where Supabase's confirmation email lands after the user clicks it. Supabase delivers the
    # confirmed session tokens in the URL FRAGMENT (after "#"), which browsers never send to the
    # server — so we can't auto-log-them-in here. Instead we render the sign-in page with a
    # friendly "you're confirmed, now sign in" banner. (Auto-login-on-confirm would need client
    # JS and is a deliberate follow-up, not in T03's scope.)
    return _auth_page(request, "login_email.html",
                      info="Your email is confirmed — sign in to continue.")


def _validate_credentials(email: str, password: str) -> Optional[str]:
    # Friendly, pre-round-trip validation for signup. Returns an error string, or None if OK.
    # Supabase re-validates authoritatively; this just gives a clean message before we call it.
    if not email or not _EMAIL_RE.match(email):
        return "Enter a valid email address."
    if len(password) < PASSWORD_MIN_LENGTH:
        return f"Password must be at least {PASSWORD_MIN_LENGTH} characters."
    return None


# The expected request body. All fields Optional so we can return our own clear 400
# below when a token is missing, rather than a generic validation error.
# LEGACY-PARITY EXCEPTION — do not copy this into new endpoints. The all-Optional shape
# exists only to reproduce the old backend's exact 400 message. Per ADR-0007 (layer 1)
# and T70's handlers, T10+ request schemas declare required, typed fields and let the
# RequestValidationError handler return the clean 400.
class CaptureBody(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    scopes: Optional[str] = None


def _store_spotify_token(
    session: Session, user_id: str, access_token: str, refresh_token: str, scopes: str
) -> None:
    # "Upsert" the user's Spotify tokens: update the row if it exists, else create it.
    # Keyed by user id; both tokens are ENCRYPTED before saving. Shared by the login
    # callback and the legacy capture endpoint so the encrypt-and-store logic lives once.
    # NOTE: the caller commits — this only stages the change on the session.
    # Spotify access tokens last ~1 hour; store the expiry as a naive UTC timestamp to
    # match how the existing rows (written by the old backend) were saved.
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)
    row = session.get(SpotifyToken, user_id)
    if row is None:
        row = SpotifyToken(user_id=user_id)
        session.add(row)
    row.access_token = encrypt(access_token)
    row.refresh_token = encrypt(refresh_token)
    row.expires_at = expires_at
    row.scopes = scopes or ""


@router.post("/api/auth/capture-spotify")
def capture_spotify(
    body: CaptureBody,
    user: User = Depends(require_user),  # ensures the caller is logged in; gives us their record
    session: Session = Depends(get_session),
):
    # Both tokens are required. WHY check here (not via the model): we want the exact
    # same 400 + message the old backend returned.
    if not body.refresh_token or not body.access_token:
        return fail("missing spotify tokens", 400)

    _store_spotify_token(session, user.id, body.access_token, body.refresh_token, body.scopes or "")
    session.commit()
    return ok({"captured": True})
