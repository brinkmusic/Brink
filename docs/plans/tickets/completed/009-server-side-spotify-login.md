---
status: Completed
priority: High
complexity: High
category: Feature
tags: [auth, supabase, spotify, oauth, crypto, frontend, session]
blocked_by: [002]
blocks: []
parent_ticket: null
owner: Andrea
---

# Feature: Server-side Spotify login for the Jinja frontend (T09)

## Rationale
ADR-0013 retires the React/Vite SPA and serves the frontend from FastAPI (Jinja2 + HTMX). The
current login flow is **browser-side**: the Supabase JS client runs the Spotify OAuth handshake,
exchanges the code for a session in the browser, and then the browser POSTs the one-time Spotify
provider tokens to `POST /api/auth/capture-spotify`. Once the SPA (and its Supabase JS client) is
gone, nothing in the browser drives OAuth or holds a session — so the "Continue with Spotify"
button on the new Jinja landing page (PR #60) is visual only. This ticket rebuilds login as a
**server-side OAuth flow** owned by our FastAPI app: initiate → callback → session cookie → capture
the encrypted Spotify refresh token, so the new frontend can actually sign a user in and gate the
feed. This is the auth half of the ADR-0013 frontend transition that PR #60 explicitly deferred to
the backend owner.

## Summary
Add server-driven Spotify login to the FastAPI app: a route that starts the OAuth handshake, a
callback route that exchanges the code for a Supabase session and sets a secure session cookie, and
server-side capture of the encrypted Spotify refresh token — replacing the browser/Supabase-JS flow
removed with the SPA. `require_user` learns to read the session cookie in addition to the existing
`Authorization: Bearer` header so the Jinja pages can gate on login.

## Source
- Spec reqs: **AUTH-1** (Spotify login → `public.User`), **AUTH-2** (encrypt refresh token
  server-side), **AUTH-4** (JWT verified server-side), **AUTH-5** (server owns token refresh).
  This ticket **re-implements the AUTH-1/AUTH-2 login *surface*** for the server-rendered
  frontend; the underlying identity/crypto model from T02/T06 is reused, not rebuilt.
- ADRs: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (frontend served from FastAPI —
  the reason login must move server-side) · [ADR-0005](../../../decisions/adr/0005-identity.md)
  (identity / `User` auto-provision) · [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md)
  (auth validated via Supabase `getUser()`, no JWT secret) ·
  [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md) (validation/authz layers).

## Scope
### In Scope
- **Start route** — e.g. `GET /auth/login`: redirect the browser into Spotify OAuth via Supabase,
  with the correct redirect URL and scopes (reuse the scopes the SPA requested).
- **Callback route** — e.g. `GET /auth/callback`: exchange the returned code for a Supabase
  session server-side, provision/link the `public.User` (reusing T02's derive-handle logic), set a
  **secure, httpOnly, SameSite session cookie**, and capture + encrypt the Spotify refresh token
  server-side (reuse `app.security.crypto.encrypt` + the `SpotifyToken` upsert already in
  `routers/auth.py`, rather than the browser POST).
- **Logout route** — clear the session cookie.
- **`require_user` update** — accept the session cookie as an auth source in addition to the
  existing `Authorization: Bearer <jwt>` header, so both the Jinja pages and the JSON API keep
  working. Still validates the token via Supabase `getUser()` (no JWT secret — ADR-0010).
- **Wire the landing page** — point PR #60's "Continue with Spotify" button at the start route;
  gate `/feed` (and future pages) on the session, redirecting anonymous users to login.
- **Supabase + Spotify config** — add the server callback URL to Supabase Auth Site/Redirect URLs
  and the Spotify app's redirect allow-list (documented; the values live in Render/Supabase, never
  committed).

### Out of Scope
- Email/magic-link login (**T03**) and the "link Spotify to a handle account" flow (**T44**).
- The snapshot/refresh job that *consumes* the stored token (**T21**) — this ticket only captures
  and stores it.
- Retiring the SPA's own login files (`apps/web/src/pages/LoginPage.tsx`, `CallbackPage.tsx`,
  `context/AuthContext.tsx`) and the `/api/auth/capture-spotify` browser endpoint — that cleanup
  belongs to the mock/SPA retirement in **T60**. Keep the old endpoint until then.
- Any change to the token encryption scheme or `TOKEN_ENC_KEY`.

## Validation & authz (ADR-0007 — required on this ticket)
- **Schema (Pydantic):** callback query params (`code`, `state`, and any `error`/`error_description`)
  are validated/typed; a Spotify-returned error renders a friendly login-failed page, never a 500.
- **Business rule:** OAuth **`state` parameter** is generated on the start route and verified on
  the callback to prevent CSRF on the login flow.
- **Authorization:** the session cookie is the *only* thing that identifies the logged-in user;
  user identity is never read from a client-supplied form field. `require_user` continues to
  verify the token server-side via Supabase `getUser()`.
- **Integrity:** `SpotifyToken` is keyed by `user_id` (upsert), so a re-login refreshes the row
  rather than duplicating it (already true in `routers/auth.py`).
- **Cookie hardening:** session cookie is `httpOnly`, `Secure`, `SameSite=Lax` (or stricter), with
  a sensible expiry; nothing sensitive (raw tokens) is stored in the cookie itself.

## Current State (on `develop`)
- **Browser-side flow (being replaced):** `apps/web/src/pages/LoginPage.tsx` calls
  `supabase.auth.signInWithOAuth`; `CallbackPage.tsx` lets the Supabase JS client exchange the code
  for a session in-browser, then forwards the one-time provider tokens to the capture endpoint.
- **Capture endpoint:** `backend/app/routers/auth.py` — `POST /api/auth/capture-spotify` takes the
  tokens *from the browser*, encrypts them (`app.security.crypto.encrypt`), and upserts a
  `SpotifyToken` row. The encryption + upsert logic is reusable; only the *source* of the tokens
  changes (server-side callback instead of a browser POST).
- **Identity/authz:** `require_user` (`backend/app/deps.py`) validates a Supabase JWT from the
  `Authorization` header via `getUser()` and auto-provisions a `public.User` with a derived handle
  (T02). `app.security.supabase` wraps the Supabase client; `app.security.crypto` is AES-256-GCM.
- **Frontend shell:** the Jinja pages + `routers/pages.py` land in **PR #60** (ADR-0013). This
  ticket depends on that shell being merged — the login button and `/feed` gate live there.
- No session-cookie handling and no `/auth/login`|`/auth/callback` routes exist yet.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/auth.py` | MODIFY | add `GET /auth/login`, `GET /auth/callback`, `GET /auth/logout`; capture the token server-side (reuse existing encrypt + upsert) |
| `backend/app/deps.py` | MODIFY | `require_user` also reads the session cookie (not only the Bearer header) — **shared, wide blast radius; call out in the PR** |
| `backend/app/security/supabase.py` | MODIFY | helpers to run the OAuth code-exchange / read the session server-side, if needed |
| `backend/app/templates/home.html` | MODIFY | point "Continue with Spotify" at `/auth/login` (in PR #60) |
| `backend/app/routers/pages.py` | MODIFY | gate `/feed` on the session cookie; redirect anonymous → login (in PR #60) |
| `backend/tests/test_auth_login.py` | CREATE | start/callback/logout + cookie + `state` CSRF tests |

## Testing Checklist
- [x] `GET /auth/login` redirects to Spotify with the right redirect URL, scopes, and a `state`
- [x] callback with a valid code sets an httpOnly+Secure session cookie and provisions the `User`
- [x] callback stores an **encrypted** `SpotifyToken` (row is upserted, not duplicated on re-login)
- [x] callback with a mismatched/missing `state` is rejected (CSRF guard)
- [x] Spotify-returned `error` renders the friendly login-failed page, not a 500
- [x] a request with a valid session cookie passes `require_user`; existing Bearer-header auth
      still works (no regression to the JSON API)
- [x] `GET /feed` while logged out redirects to login; while logged in renders the feed
- [x] `GET /auth/logout` clears the cookie and de-gates the feed

## Outcome (as built)
Server-side Spotify login shipped as five slices (branch `feat/T09-server-side-spotify-login`):
- **`GET /auth/login`** (`routers/auth.py`) — starts Supabase PKCE OAuth; stores the PKCE verifier
  + a CSRF `state` in a short-lived **encrypted, httpOnly handshake cookie** (`brink_oauth`). State
  is carried in the `redirect_to` query param (verified Supabase preserves it) and matched on the
  callback.
- **`GET /auth/callback`** — verifies `state`, exchanges the code for a Supabase session
  (`supabase.exchange_code`), provisions the user (`deps.get_or_create_user`), encrypts + upserts
  the Spotify provider tokens (`auth._store_spotify_token`), sets the encrypted **`brink_session`**
  cookie, redirects to `/feed`. Every failure (cancel, bad code, state mismatch, missing cookie) →
  friendly `_login_failed` page, never a 500.
- **`GET /auth/logout`** — clears the session cookie.
- **`require_user`** (`deps.py`) now accepts the session cookie in addition to the Bearer header
  (Bearer takes precedence, JSON API unchanged), with **refresh-on-expiry**: an expired Supabase
  access token is refreshed via the stored refresh token and the cookie re-set.
- **New `app/security/session.py`** — single source of truth for the `brink_session` cookie
  (name / encode / decode / hardening), shared by callback, logout, and require_user (avoids a
  deps↔routers.auth circular import). New `supabase.oauth_authorize` / `exchange_code` /
  `refresh_session` wrappers.
- **Login buttons wired** (`home.html`, `base.html`) and **`/feed` gated** (`routers/pages.py`):
  anonymous → `/auth/login`. This intentionally reverses PR #60's temporary public feed
  (confirmed with owner).

Satisfies the **AUTH-1/AUTH-2/AUTH-4** login surface for the server-rendered frontend (the identity
/ crypto model from T02/T06 is reused, not rebuilt); those rows were already ✅ via T02/T22 — the
traceability now also points at T09 for the server-side path.

**Reused precedent for later work:** `app/security/session.py` is the cookie-session pattern any
future server-rendered gated page should reuse.

**Design decision (encrypted-cookie session vs server-side store) and the PKCE spike are recorded
in the Notes below; the second-review requirement was made optional mid-ticket (owner call).**

Tests: 15 in `tests/test_auth_login.py` + cookie-auth cases in `tests/test_auth.py` + gated-feed
cases in `tests/test_pages.py`. Full backend suite green (127 passed).

**Deploy prerequisite (Andrea, not code):** the deployed `/auth/callback` URL must be added to the
**Supabase Auth** Redirect URLs *and* the **Spotify app** redirect allow-list, or live login 401s.
**Still to validate live:** tests fake the Supabase code exchange; one real Spotify login should
confirm the server exchange returns `provider_refresh_token` end-to-end (the spike made this
low-risk, but it's the one path automated tests can't exercise).

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T02 auth foundation done; ADR-0013 Jinja shell / PR #60 must merge first)
- [x] Scope boundaries defined
- [x] Design decisions in Notes confirmed by owner before implementation (2026-07-09, see below)

## Notes
Branch off `develop` as `feat/T09-server-side-spotify-login`; one PR back into `develop`. **This is
an auth/crypto change** — `backend/app/deps.py` and `routers/auth.py` touch tokens and
`require_user`, so per CLAUDE.md a second review is encouraged where a reviewer is available, but it
is not required and the owner may self-merge (noting in the PR that it went in without one).
Run the full backend suite (`cd backend && uv run pytest`) — `deps.py` is shared code.

**Design decisions — CONFIRMED 2026-07-09** (a spike validated the server-side PKCE flow against the
`brink-dev` Supabase project before locking these in):
1. **Session mechanism — RESOLVED: encrypted cookie (owner's call).** After sign-in, the Supabase
   session (access + refresh tokens) is stored in an **httpOnly, Secure, SameSite=Lax cookie,
   encrypted at rest with the existing AES-256-GCM `crypto.encrypt` / `TOKEN_ENC_KEY`** — no new
   server-side session store or Redis. `require_user` decrypts the cookie, validates the access
   token via Supabase `getUser()`, and when that token is expired refreshes the Supabase session
   with the stored refresh token and re-sets the cookie. Chosen over a server-side store for the
   deadline + zero new infra; still fully server-verified, and no readable token reaches the browser.
2. **OAuth code exchange — RESOLVED: server-side PKCE via `supabase_auth` 2.31.0.** Spike confirmed
   `sign_in_with_oauth` builds the Spotify authorize URL against `brink-dev` and
   `exchange_code_for_session` returns a `Session` carrying `provider_refresh_token` — so no separate
   Spotify handshake is needed; we reuse the existing `encrypt` + `SpotifyToken` upsert. **Constraint
   the spike surfaced:** the PKCE `code_verifier` generated at `/auth/login` must survive to
   `/auth/callback` (the server is stateless/multi-worker), so it's carried — with the CSRF `state` —
   in a **short-lived encrypted handshake cookie**, not the SDK's default in-memory storage.
3. **Cookie scope / same-origin — RESOLVED.** Frontend + API share one FastAPI/Render origin under
   ADR-0013, so cookies are first-party: `SameSite=Lax`, `httpOnly`, host-only (no explicit domain).
   `Secure` is set in production and relaxed only for local `http://127.0.0.1` dev.

Prerequisite: this can only be worked once PR #60 (the ADR-0013 Jinja shell) is merged, since the
login button and the `/feed` gate live in `home.html` / `pages.py`.
