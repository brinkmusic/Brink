# Investigation: Email/Password signup + login as an alternative to Spotify

**Date:** 2026-07-15
**Author:** investigation (read-only; no code changed)
**Owner request:** add EMAIL/PASSWORD signup + login as an alternative to Spotify-only login, with
rate limiting and the usual hardening.

> **TL;DR** — Supabase Auth (already our provider) supports email/password natively; the Python
> `supabase` client (`supabase-auth` 2.31.0, already installed) exposes `sign_up` and
> `sign_in_with_password`. The cleanest fit for our server-rendered stack is to run those two calls
> **server-side** (mirroring the T09 Spotify flow), set the SAME encrypted `brink_session` cookie,
> and reuse `get_or_create_user`. A handle-only user already renders across the whole app because
> every Spotify code path degrades to `None`/empty — the snapshot cron already `JOIN`s on
> `SpotifyToken` and never touches unlinked users. **Two decision changes are needed before coding:**
> (1) ADR-0005 committed to email *magic-link/OTP*, not passwords — a new ADR must supersede that
> choice; (2) unauthenticated login/signup must be rate-limited by **IP**, but today's rate-limit
> helper keys on user id only.

---

## 1. Current auth flow, end to end

All server-side auth lives in four files. Bearer-header auth (JSON API) and cookie auth
(server-rendered pages) converge in `require_user`.

### Login start — `backend/app/routers/auth.py:67` `GET /auth/login`
- Generates a CSRF `state` (`secrets.token_urlsafe(32)`), derives the callback URL from
  `request.base_url` (so it works on localhost and Render), and calls
  `supabase.oauth_authorize(redirect_to, SPOTIFY_SCOPES)` (`supabase.py:41`).
- `oauth_authorize` builds a **fresh** PKCE client (`_pkce_client`, `supabase.py:26` — not cached, so
  concurrent logins don't clobber each other's verifier), calls
  `client.auth.sign_in_with_oauth({provider: "spotify", ...})`, and reads the one-time PKCE
  `code_verifier` back out of the client's in-memory storage.
- `{state, verifier}` is encrypted (`crypto.encrypt`) into a short-lived httpOnly cookie
  `brink_oauth` (`auth.py:40`, 600 s), and the browser is 307-redirected to Spotify.

### Callback — `auth.py:94` `GET /auth/callback`
1. If Spotify returned `?error`, render the friendly `_login_failed` page (400, never a 500).
2. Require + decrypt the `brink_oauth` handshake cookie; reject if missing/undecryptable.
3. CSRF: the echoed `?state` must equal the stored `state` (`auth.py:118`).
4. `supabase.exchange_code(code, verifier)` (`supabase.py:56`) swaps the one-time code for a Supabase
   `Session` carrying the user **and** `provider_token` / `provider_refresh_token`.
5. `get_or_create_user(session, sb_session.user)` (`deps.py:59`) provisions/fetches the `public.User`.
6. If both provider tokens are present, `_store_spotify_token` (`auth.py:181`) **encrypts** each token
   (`crypto.encrypt`) and upserts one `SpotifyToken` row keyed by `user_id`, expiry = now + 1 h
   (naive UTC).
7. `login_session.set_cookie` writes the encrypted `brink_session` cookie; 303 → `/feed`; the
   single-use `brink_oauth` cookie is deleted.

### Session cookie — `backend/app/security/session.py`
- One module owns the cookie's name/shape/lifetime (`SESSION_COOKIE = "brink_session"`, 30-day
  max-age). `encode`/`decode` = `crypto.encrypt`/`decrypt` of
  `{"access_token", "refresh_token", "expires_at"}`. `decode` returns `None` (never raises) on a
  tampered/undecodable cookie, so "can't read it" == "not logged in".
- Hardening (`session.py:42`): `httponly=True`, `secure=<https>`, `samesite="lax"`. No raw token is
  readable by the browser — the value is AES-256-GCM ciphertext.

### require_user + refresh — `backend/app/deps.py:180`
- Bearer header takes precedence (`_user_from_bearer`, JSON API unchanged); otherwise the session
  cookie path (`_user_from_session_cookie`, `deps.py:137`).
- Cookie path: decode → validate `access_token` via Supabase `get_user()`
  (`supabase.get_user_from_token`, `supabase.py:88`). If the access token is expired, use the stored
  `refresh_token` via `supabase.refresh_session` (`supabase.py:69`), then **re-set the cookie** with
  the rotated tokens (`deps.py:169`). Pages carry that refreshed `Set-Cookie` onto the page response
  (`pages.py:140`, the `refreshed` Response trick).
- `_verify_supabase_token` (`deps.py:111`): `ValueError` (missing SUPABASE_* config) propagates → 500
  (misconfig must be visible); any other exception → `None` (treated as invalid).
- Auth checks are done server-side via Supabase `getUser()`; **no JWT secret** is held (ADR-0010).

### Logout — `auth.py:161` `GET /auth/logout`
- `login_session.clear_cookie(response)`; 303 → `/`.

### Token capture + storage (encrypted)
- `SpotifyToken` model (`models.py:176`): PK = `user_id` (FK → `User.id`, CASCADE), `access_token`
  / `refresh_token` (both ciphertext), `expires_at`, `scopes`.
- Crypto (`security/crypto.py`): AES-256-GCM, `TOKEN_ENC_KEY` (32 bytes b64). Format is Node-compatible
  `base64(iv).base64(tag).base64(ct)` (inherited from the retired TS backend).
- `spotify.get_valid_access_token` (`spotify.py:74`) refreshes expired tokens via Spotify's
  `refresh_token` grant; `_safe_decrypt` (`spotify.py:59`) degrades an unreadable token to `None`
  rather than raising (so one bad `TOKEN_ENC_KEY` row can't 500 the snapshot).

---

## 2. What Supabase Auth offers for email/password (GoTrue) — and how we'd call it

### The client we already use
- `pyproject.toml` pins `supabase>=2.9`; `uv.lock` resolves **`supabase` 2.31.0 / `supabase-auth`
  2.31.0** (the GoTrue Python client). We do **not** use `supabase-js`; everything goes through this
  Python SDK, which itself wraps GoTrue's REST API over `httpx`.
- `security/supabase.py` builds two clients: `admin()` (service-role, cached) and `_pkce_client()`
  (fresh, PKCE). We call SDK methods (`auth.sign_in_with_oauth`, `auth.exchange_code_for_session`,
  `auth.refresh_session`, `auth.get_user`) — never raw REST. Email/password would follow the same
  pattern with **new thin wrappers**, not raw `httpx`.

### The SDK methods an email flow needs (all in `supabase-auth` 2.31.0)
| Purpose | SDK call (sync client) | GoTrue REST it wraps |
|---|---|---|
| Sign up | `client.auth.sign_up({"email", "password", "options": {"email_redirect_to": ...}})` | `POST /auth/v1/signup` |
| Log in | `client.auth.sign_in_with_password({"email", "password"})` | `POST /auth/v1/token?grant_type=password` |
| Password reset (request) | `client.auth.reset_password_for_email(email, {"redirect_to": ...})` | `POST /auth/v1/recover` |
| Password update (after reset link) | `client.auth.update_user({"password": ...})` (on a session) | `PUT /auth/v1/user` |
| Confirm email | handled by the link Supabase emails → hits our `redirect_to` with tokens | `GET /auth/v1/verify` |

Both `sign_up` and `sign_in_with_password` return an `AuthResponse` carrying a `Session` (access +
refresh tokens) and a `User` — the **exact same shapes** the Spotify callback already consumes, so
`get_or_create_user` + `login_session.set_cookie` are reused verbatim.

**IMPORTANT client choice:** run these on a **non-PKCE, non-admin** client (or the `admin()` client is
fine for `sign_in_with_password` — the service-role key just authenticates the request). Do **not**
reuse `_pkce_client()` (its `flow_type="pkce"` is OAuth-specific). Simplest: a small
`_password_client()` with default options, or route password sign-in through `admin()`.

### Is email auth enabled by default, and what dashboard config is needed?
- **Enabled by default:** on a new Supabase project the **Email** provider is ON, and
  **"Confirm email" is ON by default**. Consequence: with confirmations on, `sign_up` creates the user
  but returns a session with **no usable access** until the user clicks the confirmation link — so the
  signup handler must show a "check your inbox" state, not log them straight in.
- **Dashboard config required (Andrea, not code):**
  1. Auth → Providers → **Email**: confirm it's enabled; decide **Confirm email ON vs OFF**.
     - *ON* (default, recommended): must add our confirm/redirect URL to the allow-list and handle the
       "check your inbox" UX.
     - *OFF* (simplest for the course demo): signup logs the user in immediately, no email round-trip.
       Lower friction, weaker guarantee. **This is the primary decision to get from the owner.**
  2. Auth → URL Configuration → **Redirect URLs**: add the deployed confirm/reset redirect
     (e.g. `https://brink-xg7p.onrender.com/auth/confirm`) *and* the localhost equivalent — same
     allow-list the T09 `/auth/callback` already needs.
  3. Auth → Email Templates: default templates work; optional branding.
  4. (Prod) Supabase's built-in SMTP is rate-limited to a few mails/hour — fine for a course demo; a
     real launch needs a custom SMTP provider. **Out of scope** to configure that here.

---

## 3. What breaks for a user with NO linked Spotify — feature by feature

Design intent (ADR-0005 / ADR-0014): handle accounts "work fully except Spotify-derived stats."
Verified against the code — **the app is already handle-safe**; the Spotify paths degrade cleanly.

| Feature | Verdict | Why (evidence) |
|---|---|---|
| **Composer / catalog search** | ✅ Works | `GET /api/search` (`routers/search.py`) uses `search_tracks`, which uses `_get_client_credentials_token` — an **app-level** Spotify token, not the user's. Confirmed: no dependency on a linked account. Publishing via `POST /api/posts` never touches Spotify tokens. |
| **Feed** | ✅ Works | `build_feed` / `_feed_items` (`pages.py:87`) read only Post/Track/Reaction/Comment/Follow — no Spotify. `_feed_items` even wraps the build in try/except → empty feed, never a crash. |
| **Reactions** | ✅ Works | Pure DB writes; no Spotify. |
| **Comments** | ✅ Works | Pure DB writes; no Spotify. |
| **Follow** | ✅ Works | Pure DB; no Spotify. |
| **Profile listening summary** | ✅ Works (empty) | `app/stats.py` `listening_summary` reads `Play` rows; every sub-query degrades to `[]`/`0`/`0` for a user with no plays (comment at `stats.py:36` confirms). `_profile_data` sets `has_spotify = person.spotify_id is not None` (`pages.py:204`) to drive the "link Spotify" prompt; `profile.html:109` shows a "Link Spotify" button. |
| **Now-playing badge** | ✅ Works (hidden) | `pages.py:236` only calls `get_currently_playing` on your **own** profile; that returns `None` for an unlinked account (`spotify.py:122` → `get_valid_access_token` returns `None` when there's no `SpotifyToken` row, `spotify.py:78`). Badge simply hides. `GET /api/me/now-playing` returns `{data: null}` similarly. |
| **Snapshot cron** | ✅ Skips them | `routers/snapshot.py:119` selects `User` **INNER JOIN `SpotifyToken`** — unlinked users are never in the loop. Even if selected, `get_recently_played` → `None` → counted as `skipped`. No 500. |
| **Artist upload** | ✅ Gated separately | `/artist` page (`pages.py:256`) and the T50 API gate on `User.is_artist`, orthogonal to Spotify. A handle user who is also an artist can upload. |

### Places that *assume* Spotify — and whether any would break
- **`get_or_create_user` handle generation** (`deps.py:78`): display name falls back to
  `email.split("@")[0]` then `"Listener"`; handle = slug + 6 chars of the Supabase user id
  (`deps.py:84`). **No Spotify dependency** — already handles an email-only identity. `spotify_id`
  is set only when `app_metadata.provider == "spotify"` (`deps.py:74,92`), else `None`. ✅
- **Templates** (`base.html`, `home.html`): every login button points at `/auth/login` (Spotify).
  Not a crash — but there is **no email login entry point in the UI at all**. This is the real gap the
  feature fills (new form pages/buttons).
- **`User.spotify_id` unique index** (`models.py:138`): `Index("User_spotifyId_key", unique=True)`.
  Postgres treats multiple `NULL`s as distinct, so **many handle-only users (all `spotify_id = NULL`)
  do NOT collide.** ✅ (Confirmed safe — a common worry, but Postgres unique indexes allow repeated
  NULLs.)

**Conclusion:** no code path 500s or looks broken for a handle-only user today. The only missing piece
is the **front door** (an email signup/login UI + routes).

---

## 4. "Link Spotify later" for an email user

### Two options
1. **Supabase identity-linking** (`linkIdentity`, what ADR-0005 assumed): attaches the Spotify
   provider to the *existing* Supabase auth user, so there's one identity and our `public.User`
   (keyed by `supabaseUserId`) is untouched. This is the "correct" long-term design but requires
   Supabase "Manual Linking" enabled and a logged-in-user OAuth sub-flow — **more moving parts.**
2. **Our own simpler flow (recommended for the deadline):** a logged-in email user hits the existing
   `/auth/login` → `/auth/callback`. Two things must change vs. today:
   - The callback currently always `get_or_create_user`s from the **Spotify** identity. For a
     *same-email* Spotify login, Supabase's own email-based auto-linking may return the **same**
     `supabaseUserId`, so `get_or_create_user` finds the existing row and we'd just need to **set
     `spotify_id` + store the token on that row** (a small update, not a new user).
   - **Edge case (ADR-0005 already flags it):** a Spotify-first login and a later same-email signup
     must resolve to the **same** identity. This depends on Supabase's "link accounts with same email"
     setting; if it's off, you get two `supabaseUserId`s → two `public.User` rows → split data. Needs a
     test + a dashboard setting decision.

**Recommendation:** ship email/password **without** the link-later flow first (mark it a follow-up
ticket, as ADR-0005 already scoped it separately). The app is fully usable as a handle account today.

### Does `User` (models.py) need changes?
**No schema change required.** All the needed columns already exist and are already nullable for
handle accounts:
- `supabase_user_id` (nullable, unique) — set for every real login.
- `email` (nullable, unique) — populated from the email identity.
- `spotify_id` (nullable, unique) — stays `NULL` for handle users; set when Spotify links.
- `SpotifyToken` — simply absent for handle users (the join/lookup returns nothing).

The **only** thing worth noting: `get_or_create_user` currently derives display name from
`user_metadata.full_name/name` (Spotify) → `email` prefix → `"Listener"`. For email signup those meta
fields are empty, so new email users get a `Listener`-based or email-prefix handle. Acceptable
(matches the T03 "auto-derived handle, no signup form" decision), but confirm with the owner whether a
**user-chosen display name at signup** is wanted (that WOULD add a field to the signup form and a small
`update_user`/`User.display_name` write — a scope choice, not a schema change).

---

## 5. Rate limiting + abuse hardening

### How the existing helper works (`app/rate_limit.py`, ADR-0011)
`enforce_rate_limit(session, *, subject, action, limit, window_seconds)`:
- Counts rows in `RateLimitHit` matching `(subject, action)` newer than `now - window` (naive UTC).
- If `count >= limit` → raise `RateLimitError` (→ 429 via the handler in `main.py:78`).
- Else insert a hit row and allow.

`subject` is a free-form string. **Today every caller passes `user.id`** (posts/reactions/comments/
follow/search) — i.e. it keys on the authenticated user. Signup/login are **unauthenticated**, so
there is no `user.id` to key on.

### Keying strategy for anonymous endpoints
The helper is generic (`subject` is any string), so it works for anon endpoints **if we choose the
right subject**:
- **Primary key = client IP.** `subject = f"ip:{client_ip}"`, `action = "auth_login"` /
  `"auth_signup"`. Get the IP from `request.client.host`, but **on Render (behind a proxy) trust
  `X-Forwarded-For`'s first hop** — otherwise every request looks like the proxy IP and one bucket
  throttles everyone. This is a small, explicit helper (`_client_ip(request)`), and a **security
  callout**: header-spoofing means IP limits are best-effort, so pair them with Supabase's own limits.
- **Secondary key = email** (`subject = f"email:{normalized_email}"`, `action = "auth_login_email"`):
  bounds targeted password-guessing against one account regardless of source IP. Cheap to add.
- Suggested caps (tunable, module-level like the others): login ~5–10 / 5 min per IP **and** per
  email; signup ~3–5 / hour per IP.

**No change to `rate_limit.py` itself is needed** — only new callers with IP/email subjects + a
`_client_ip` helper. (Optional hardening: a tiny `subject` length guard, since IP/email are shorter
than a cuid — not required.)

### Password policy
Supabase enforces a **minimum length (default 6)**; the dashboard can raise it and require character
classes (Auth → Providers → Email → password requirements). Do the **primary** check server-side in our
handler too (e.g. ≥ 8 chars) via a Pydantic field constraint so we return our clean 400 envelope, and
optionally raise Supabase's minimum to match. Don't roll our own hashing — **Supabase stores the
password hash (bcrypt) itself**; we never see or store the password beyond forwarding it to GoTrue over
HTTPS. (Our `crypto.py` is for Spotify tokens only — not relevant here.)

### Does Supabase itself rate-limit auth endpoints?
Yes. GoTrue has built-in limits (e.g. token/`sign_in` requests per IP over a 5-min window, and a
strict email-send cap — a few sign-up/recover emails per hour on the default SMTP). These are a real
backstop, but they're coarse and shared, so our own IP/email limits give tighter, app-specific control
and a clean 429 in our envelope. **Defense in depth: keep both.**

### Other hardening callouts (this touches `deps.py` / `security/` — highest-risk area per CLAUDE.md)
- **Enumeration:** return a **generic** "invalid email or password" for login failures (don't reveal
  whether the email exists). For signup with confirmations on, show "check your inbox" regardless.
- **Same cookie hardening** as T09: reuse `login_session.set_cookie` verbatim (httpOnly, Secure,
  SameSite=Lax, encrypted) — no new cookie shape.
- **CSRF on the POST forms:** the session cookie is `SameSite=Lax`, which blocks cross-site POSTs, but
  the login/signup **forms themselves are unauthenticated POSTs** — add a CSRF token to the form (the
  same encrypted-cookie pattern `brink_oauth` uses for OAuth `state`) or rely on SameSite + origin
  check. Call this out explicitly in the ticket.
- **Never log passwords**; ensure the Pydantic model / error handler can't echo the body.
- **HTTPS only** in prod (already true on Render); passwords never travel to us except over TLS.

---

## 6. Ticket sketch

### Decision prerequisites (must resolve BEFORE coding — these are the ambiguities to raise)
1. **ADR change:** ADR-0005 chose email **magic-link/OTP**, not passwords. Email/password is a
   *different* decision → write a **new ADR** ("Email/password auth for handle accounts") that
   supersedes the relevant part of ADR-0005 (ADRs are append-only — don't edit 0005; set a
   "superseded-by" note). Update AUTH-3 wording in `requirements.md` and the existing backlog ticket
   `docs/plans/tickets/backlog/003-auth-email.md` (which is **stale** — it references the retired
   `apps/web/` SPA and OTP, not password).
2. **Confirm-email ON or OFF?** ON = "check your inbox" UX + redirect handling; OFF = instant login,
   simplest demo. Owner call.
3. **User-chosen display name at signup, or auto-derived** (like T03 decided)? Auto-derived = smaller.
4. **Password reset in scope now, or follow-up?** Recommend follow-up.
5. **Link-Spotify-later in scope now, or follow-up?** Recommend follow-up (ADR-0005 already separates
   it).

### Recommended breakdown

**Ticket A — Email/password signup + login (core)** — *owner: Andrea (auth) + Sebastian (Jinja forms)*
- **New ADR** superseding ADR-0005's OTP choice for password auth.
- **`security/supabase.py`**: add `sign_up_email(email, password)` and
  `sign_in_password(email, password)` wrappers (thin, over the SDK; not raw REST). Decide the client
  (`admin()` or a small default client — **not** `_pkce_client`).
- **`routers/auth.py`**: add `GET/POST /auth/signup`, `GET/POST /auth/login-email` (keep `/auth/login`
  = Spotify), plus `GET /auth/confirm` if confirmations are ON. Server-side: validate → call
  Supabase → on success `get_or_create_user` + `login_session.set_cookie` (reuse T09 machinery) →
  303 `/feed`. On failure → friendly, **non-enumerating** error page.
- **Rate limiting**: new `_client_ip(request)` helper; `enforce_rate_limit` with `ip:`/`email:`
  subjects on both routes. (No change to `rate_limit.py`.)
- **CSRF** token on the forms (encrypted-cookie pattern like `brink_oauth`).
- **Templates**: new `login_email.html` + `signup.html` (Jinja), and add "Sign in with email" /
  "Create an account" links to `home.html` / `base.html` next to the Spotify buttons.
- **Tests** (`backend/tests/test_auth_email.py`, new): signup creates a handle `User` (null
  `spotify_id`, unique handle); login sets the cookie and passes `require_user`; wrong password → 401
  generic message; rate limit → 429 after N attempts (per IP and per email); confirm-email path (if
  ON) shows the inbox state and doesn't log the user in early; existing Spotify + Bearer auth
  unaffected (no regression — `deps.py` is shared, run the full suite).
- **Security callouts in the PR**: touches `deps.py`/`security/` (highest-risk); second review
  encouraged (owner may self-merge per CLAUDE.md); enumeration, CSRF, IP-trust behind Render's proxy.
- **Docs**: update `requirements.md` (AUTH-3 → done for password; AUTH-6 handle accounts), the ticket
  file, CLAUDE.md status line, tickets README.
- **Deploy prereq (Andrea, not code)**: Supabase dashboard — Email provider on, confirm-email
  decision, redirect URL(s) added.
- **Size: Medium** (~1–1.5 days). Most of the session/cookie/user machinery already exists from T09;
  the new work is two form flows + IP rate-limiting + CSRF + tests + the ADR.

**Ticket B — Password reset (follow-up)** — *owner: Andrea*
- `reset_password_for_email` + an `/auth/reset` confirm/update flow + a form. Depends on Ticket A.
- **Size: Small–Medium** (~0.5 day). Recommend **out of scope** for the first ticket.

**Ticket C — Link Spotify to an existing email account (follow-up)** — *owner: Andrea*
- The ADR-0005 identity-linking edge case (same-email resolution → one account; set `spotify_id` +
  capture token on the existing row). Needs the "same email = same identity" Supabase setting + a test.
- **Size: Medium** (identity edge cases are fiddly). Recommend **out of scope** for the first ticket.

### Explicitly out of scope for Ticket A
Password reset (B), link-Spotify-later (C), custom SMTP provider, admin/user management,
"remember me" beyond the existing 30-day cookie, and any change to the token-encryption scheme.

---

## Appendix — bugs / gaps found in the CURRENT auth code (incidental to this investigation)

- **[TICKET] Stale backlog ticket `003-auth-email.md`.** It targets the retired `apps/web/` SPA
  (`AuthContext.tsx`, `LoginPage.tsx`) and OTP — none of which exist post-T60, and it doesn't match the
  now-requested password flow. It should be rewritten (or closed + replaced) as part of this work.
- **[TICKET] ADR-0005 vs. the request.** ADR-0005 commits to email *magic-link/OTP*; the owner now
  wants *passwords*. Not a code bug, but a documented decision that must be superseded by a new ADR
  before implementation (append-only rule).
- **[EASY] `capture_spotify` legacy endpoint still mounted.** `POST /api/auth/capture-spotify`
  (`auth.py:201`) was the SPA's token-forwarding path; the SPA was retired in T60. It's still wired in
  `main.py:58`. Marked legacy in-code (T75/T76 remediation territory) — harmless but dead surface;
  worth confirming it's intentionally kept or retiring it.
- **[EASY] `require_user` response injection is `None` in the Bearer path.** In `require_user`
  (`deps.py:180`) `response` defaults to `None`; for a Bearer request that expires mid-flight there's
  no cookie to refresh (correct), but if a future non-page caller relied on refresh it would silently
  not persist. Not a bug today (Bearer clients re-auth themselves) — just a sharp edge to remember when
  adding the email routes (make sure the new routes pass a real `Response` so refreshed cookies stick,
  exactly like `pages.py` does).
- **[EASY] No IP-based rate limiting exists yet.** Every `enforce_rate_limit` caller keys on
  `user.id`; there is no anon/IP path today. Not a bug in current features (all rate-limited endpoints
  are authenticated), but it's the one helper-adjacent gap the email login must fill (a `_client_ip`
  helper that trusts Render's `X-Forwarded-For`).

*(No correctness bugs found in the live Spotify/session/refresh paths — they degrade to `None`/empty
consistently and the handle-only story already holds end to end.)*
