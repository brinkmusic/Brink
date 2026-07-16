# WHAT THIS FILE IS
# Automated checks for the email + password signup/login front door (T03, ADR-0015):
# GET/POST /auth/signup, GET/POST /auth/login-email, GET /auth/confirm. These verify the
# real routes against a real in-memory SQLite database (so the handle-user creation and the
# per-IP/per-email rate-limit counting are genuinely exercised, not faked), while the Supabase
# network calls are stubbed. They cover: the forms render with a CSRF token; signup validates,
# rate-limits, and shows "check your inbox" (confirmations ON) without logging you in; login
# sets the encrypted session cookie and provisions a handle User (spotify_id = NULL); wrong
# credentials give ONE generic error and no cookie; and both routes reject a missing CSRF token.

import re
from types import SimpleNamespace

import pytest

from app.db import get_session
from app.main import app
from app.models import User
from app.routers import auth as auth_router
from app.security import crypto
from app.security import session as login_session
from app.security import supabase


@pytest.fixture(autouse=True)
def _test_enc_key(monkeypatch):
    # These routes use REAL encryption for the CSRF cookie (and the session cookie on login).
    # CI has no TOKEN_ENC_KEY, so the real encrypt/decrypt would raise ValueError → a 500 on
    # every form render (this is exactly what green-locally/red-in-CI looked like). Pin a fixed
    # 32-byte key so encryption genuinely works here — the CSRF round-trip is then exercised for
    # real, not stubbed. Patching crypto._key covers everything that imports encrypt/decrypt.
    monkeypatch.setattr(crypto, "_key", lambda: b"\x00" * 32)


# ---- helpers -------------------------------------------------------------------------

def _use_db(db_session):
    # Point the app's get_session at the throwaway SQLite session for this test.
    app.dependency_overrides[get_session] = lambda: db_session


def _csrf_from(html: str) -> str:
    # Pull the hidden csrf_token value out of a rendered form so a follow-up POST can submit it
    # (exactly what a real browser does — the GET set both the cookie and this field).
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "no csrf token found in the rendered form"
    return m.group(1)


def _get_form(client, path: str) -> str:
    # GET a form page; this also plants the encrypted brink_csrf cookie on the client.
    res = client.get(path)
    assert res.status_code == 200
    return res.text


def _fake_session(user_id="sb-user-1", email="nova@example.com"):
    # A stand-in for the Supabase AuthResponse a successful password login returns: it carries a
    # `.session` (access/refresh tokens + expiry) and that session's `.user` (the shape
    # get_or_create_user consumes). app_metadata has NO spotify provider → a handle account.
    sb_user = SimpleNamespace(
        id=user_id, email=email, user_metadata={}, app_metadata={}
    )
    sb_session = SimpleNamespace(
        access_token="access-tok", refresh_token="refresh-tok", expires_at=None, user=sb_user
    )
    return SimpleNamespace(session=sb_session, user=sb_user)


# ---- form rendering ------------------------------------------------------------------

def test_signup_page_renders_with_csrf(client):
    body = _get_form(client, "/auth/signup")
    assert "Create your account" in body
    assert 'name="csrf_token"' in body
    # The GET also set the encrypted CSRF cookie.
    assert auth_router.CSRF_COOKIE in client.cookies


def test_login_email_page_renders_with_csrf(client):
    body = _get_form(client, "/auth/login-email")
    assert "Sign in" in body
    assert 'name="csrf_token"' in body


def test_confirm_page_shows_signin_with_banner(client):
    body = _get_form(client, "/auth/confirm")
    # /auth/confirm reuses the login page with a friendly "you're confirmed" banner.
    assert "confirmed" in body.lower()
    assert 'action="/auth/login-email"' in body


# ---- signup --------------------------------------------------------------------------

def test_signup_shows_check_inbox_and_sets_no_session(client, db_session, monkeypatch):
    _use_db(db_session)
    called = {}
    monkeypatch.setattr(supabase, "sign_up_email",
                        lambda email, password, email_redirect_to=None: called.update(
                            email=email, password=password, redirect=email_redirect_to))

    token = _csrf_from(_get_form(client, "/auth/signup"))
    res = client.post("/auth/signup", data={
        "email": "Nova@Example.com", "password": "hunter2", "csrf_token": token,
    })

    assert res.status_code == 200
    assert "Check your inbox" in res.text
    # Email is normalized to lowercase before Supabase sees it.
    assert called["email"] == "nova@example.com"
    # Confirmations ON: signup must NOT log the person in.
    assert login_session.SESSION_COOKIE not in client.cookies


def test_signup_short_password_rejected_before_supabase(client, db_session, monkeypatch):
    _use_db(db_session)
    called = {"n": 0}
    monkeypatch.setattr(supabase, "sign_up_email",
                        lambda *a, **k: called.update(n=called["n"] + 1))

    token = _csrf_from(_get_form(client, "/auth/signup"))
    res = client.post("/auth/signup", data={
        "email": "nova@example.com", "password": "short", "csrf_token": token,
    })

    assert res.status_code == 400
    assert "at least 6" in res.text
    assert called["n"] == 0  # never reached Supabase


def test_signup_invalid_email_rejected(client, db_session, monkeypatch):
    _use_db(db_session)
    monkeypatch.setattr(supabase, "sign_up_email", lambda *a, **k: None)
    token = _csrf_from(_get_form(client, "/auth/signup"))
    res = client.post("/auth/signup", data={
        "email": "not-an-email", "password": "hunter2", "csrf_token": token,
    })
    assert res.status_code == 400
    assert "valid email" in res.text.lower()


def test_signup_missing_csrf_rejected(client, db_session, monkeypatch):
    _use_db(db_session)
    called = {"n": 0}
    monkeypatch.setattr(supabase, "sign_up_email", lambda *a, **k: called.update(n=called["n"] + 1))
    # POST without ever GETting the form → no CSRF cookie, and a blank token.
    res = client.post("/auth/signup", data={
        "email": "nova@example.com", "password": "hunter2", "csrf_token": "",
    })
    assert res.status_code == 400
    assert called["n"] == 0


def test_signup_rate_limited_per_ip(client, db_session, monkeypatch):
    _use_db(db_session)
    monkeypatch.setattr(auth_router, "SIGNUP_RATE_LIMIT", 2)
    monkeypatch.setattr(supabase, "sign_up_email", lambda *a, **k: None)

    def _attempt(email):
        token = _csrf_from(_get_form(client, "/auth/signup"))
        return client.post("/auth/signup", data={
            "email": email, "password": "hunter2", "csrf_token": token,
        })

    # Different emails so the EMAIL bucket never trips first — we're proving the IP bucket fires.
    assert _attempt("a@example.com").status_code == 200
    assert _attempt("b@example.com").status_code == 200
    third = _attempt("c@example.com")
    assert third.status_code == 429
    assert "Too many attempts" in third.text


# ---- login ---------------------------------------------------------------------------

def test_login_sets_session_cookie_and_redirects_to_feed(client, db_session, monkeypatch):
    _use_db(db_session)
    monkeypatch.setattr(supabase, "sign_in_password",
                        lambda email, password: _fake_session())

    token = _csrf_from(_get_form(client, "/auth/login-email"))
    res = client.post("/auth/login-email", data={
        "email": "nova@example.com", "password": "hunter2", "csrf_token": token,
    }, follow_redirects=False)

    assert res.status_code == 303
    assert res.headers["location"] == "/feed"
    assert login_session.SESSION_COOKIE in client.cookies


def test_login_provisions_handle_user(client, db_session, monkeypatch):
    _use_db(db_session)
    monkeypatch.setattr(supabase, "sign_in_password",
                        lambda email, password: _fake_session(user_id="sb-42", email="jo@example.com"))

    token = _csrf_from(_get_form(client, "/auth/login-email"))
    client.post("/auth/login-email", data={
        "email": "jo@example.com", "password": "hunter2", "csrf_token": token,
    }, follow_redirects=False)

    from sqlmodel import select
    row = db_session.exec(select(User).where(User.supabase_user_id == "sb-42")).first()
    assert row is not None
    assert row.email == "jo@example.com"
    assert row.spotify_id is None          # a handle account, not a Spotify one
    assert row.handle                       # a unique handle was derived


def test_login_wrong_password_generic_error_no_cookie(client, db_session, monkeypatch):
    _use_db(db_session)

    def _raise(email, password):
        raise Exception("AuthApiError: invalid credentials")
    monkeypatch.setattr(supabase, "sign_in_password", _raise)

    token = _csrf_from(_get_form(client, "/auth/login-email"))
    res = client.post("/auth/login-email", data={
        "email": "nova@example.com", "password": "wrong", "csrf_token": token,
    }, follow_redirects=False)

    assert res.status_code == 400
    assert "Invalid email or password" in res.text
    assert login_session.SESSION_COOKIE not in client.cookies


def test_login_unconfirmed_email_no_session_generic_error(client, db_session, monkeypatch):
    # sign_in returns a response with no usable session (e.g. email not confirmed) → generic error.
    _use_db(db_session)
    monkeypatch.setattr(supabase, "sign_in_password",
                        lambda email, password: SimpleNamespace(session=None, user=None))
    token = _csrf_from(_get_form(client, "/auth/login-email"))
    res = client.post("/auth/login-email", data={
        "email": "nova@example.com", "password": "hunter2", "csrf_token": token,
    }, follow_redirects=False)
    assert res.status_code == 400
    assert login_session.SESSION_COOKIE not in client.cookies


def test_login_rate_limited_per_email(client, db_session, monkeypatch):
    _use_db(db_session)
    monkeypatch.setattr(auth_router, "LOGIN_RATE_LIMIT", 2)

    def _raise(email, password):
        raise Exception("bad creds")
    monkeypatch.setattr(supabase, "sign_in_password", _raise)

    def _attempt():
        token = _csrf_from(_get_form(client, "/auth/login-email"))
        return client.post("/auth/login-email", data={
            "email": "target@example.com", "password": "guess", "csrf_token": token,
        }, follow_redirects=False)

    assert _attempt().status_code == 400   # wrong password, under the cap
    assert _attempt().status_code == 400
    third = _attempt()
    assert third.status_code == 429        # same email hammered → limited
    assert "Too many attempts" in third.text


def test_login_missing_csrf_rejected(client, db_session, monkeypatch):
    _use_db(db_session)
    called = {"n": 0}
    monkeypatch.setattr(supabase, "sign_in_password",
                        lambda *a, **k: called.update(n=called["n"] + 1) or _fake_session())
    res = client.post("/auth/login-email", data={
        "email": "nova@example.com", "password": "hunter2", "csrf_token": "",
    }, follow_redirects=False)
    assert res.status_code == 400
    assert called["n"] == 0  # never reached Supabase
