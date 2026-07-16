# ADR-0015: Email + password auth for handle accounts (server-side)

**Status:** Accepted
**Date:** 2026-07-16
**Supersedes:** the email magic-link/OTP part of [ADR-0005](0005-identity.md) (Spotify OAuth and the
one-account/identity-linking model from ADR-0005 stand unchanged).
**Relates to:** [ADR-0007](0007-validation-and-data-integrity.md) (validation/authz layers),
[ADR-0011](0011-rate-limiting-store.md) (rate-limit helper), [ADR-0013](0013-python-frontend.md)
(the server-rendered frontend this login lives in); requirements `AUTH-3`, `AUTH-6`.

## Context

Brink must honour **manual posting without a Spotify account** (AUTH-3/AUTH-6): a person with no
Spotify should still be able to sign up, post, react, comment, and follow. Today the only front
door is Spotify OAuth (T09), so there is no way to create a non-Spotify account at all.

Two things changed since [ADR-0005](0005-identity.md) was written:

1. **The stack.** ADR-0005 assumed a browser-side Supabase client in the React SPA. That SPA was
   retired in T60 ([ADR-0013](0013-python-frontend.md)); auth is now **server-side**, run by the
   FastAPI app itself (the T09 Spotify flow is the template: our server calls Supabase, sets an
   encrypted `brink_session` cookie, and reuses `get_or_create_user`).
2. **The owner's product decision.** ADR-0005 chose email **magic-link / OTP** (a code or link
   emailed each time). The owner has since decided on a conventional **email + password** account
   instead — the familiar "make an account" flow, and one that works even when email delivery is
   slow or unreliable (Supabase's built-in SMTP is rate-limited to a few mails/hour).

The [2026-07-15 investigation](../../plans/reviews/2026-07-15-auth-email-signup-investigation.md)
confirmed the rest of the app is **already handle-safe**: every Spotify code path degrades to
`None`/empty for an unlinked user (search uses an app-level token, stats/now-playing return empty
states, the snapshot cron inner-joins `SpotifyToken` so it never touches unlinked users), and no
schema change is needed (`User.email`, `User.spotify_id`, `User.supabase_user_id` are all already
nullable). The only missing piece is the front door.

## Decision

Add **server-side email + password signup and login via Supabase Auth**, mirroring the T09 Spotify
flow, superseding ADR-0005's magic-link/OTP choice for handle accounts.

- **Provider calls.** Two thin wrappers in `security/supabase.py` over the already-installed
  `supabase-auth` SDK: `sign_up_email(email, password)` → `auth.sign_up(...)`, and
  `sign_in_password(email, password)` → `auth.sign_in_with_password(...)`. Both run on a **default
  (non-PKCE, non-admin) client** — the PKCE client is OAuth-specific and must not be reused. Supabase
  owns password hashing (bcrypt); **we never see or store the password** beyond forwarding it to
  Supabase over TLS. Our AES-256-GCM `crypto.py` remains for Spotify tokens only.
- **Routes.** In `routers/auth.py`, add `GET`/`POST /auth/signup`, `GET`/`POST /auth/login-email`,
  and `GET /auth/confirm` (the email-confirmation landing). `/auth/login` stays Spotify. On success
  these reuse the **exact T09 machinery**: `get_or_create_user` (which already provisions a handle
  user with `spotify_id = NULL`) + `login_session.set_cookie`. Failures render a friendly,
  **non-enumerating** page (generic "invalid email or password"), never a 500 (ADR-0007).
- **Email confirmation is ON** (owner decision). `sign_up` creates the user but the session is not
  usable until they click the confirmation email, so the signup handler shows a "check your inbox"
  state rather than logging them straight in; `/auth/confirm` is where Supabase's link lands.
- **Password minimum = 6 characters** (owner decision; Supabase's default). Enforced in our form
  (a Pydantic constraint returning our clean 400) as well as by Supabase, so the user gets a
  friendly error before the round-trip.
- **First IP-keyed rate limiting.** Signup/login are unauthenticated, so there is no `user.id` to
  key on. We add a `_client_ip(request)` helper that trusts Render's `X-Forwarded-For` first hop,
  and call the **existing** `enforce_rate_limit` (ADR-0011, unchanged) with `subject = "ip:<addr>"`
  **and** `subject = "email:<addr>"` — bounding both broad abuse from one source and targeted
  password-guessing against one account. This is defense-in-depth on top of Supabase's own coarse
  GoTrue limits.
- **CSRF.** The signup/login forms are unauthenticated POSTs, so they carry a CSRF token using the
  same encrypted short-lived cookie pattern the T09 OAuth `state` already uses (`brink_oauth`).

**No schema change** and **no change to `rate_limit.py`, `session.py`, or `deps.py`'s core** — the
new routes reuse them. `deps.py` is only read, not modified (the `_client_ip` helper lives with the
auth routes).

## Alternatives considered

- **Email magic-link / OTP (ADR-0005's original choice).** A code/link emailed on every login.
  Rejected by the owner in favour of a conventional password account: OTP couples *every* login to
  email delivery, and Supabase's default SMTP is capped at a few mails/hour — fragile for a live
  demo. (Passwords still need *one* confirmation email at signup, but not on every login.)
- **Confirm-email OFF (instant login at signup).** Lower friction and no redirect handling, but a
  weaker guarantee (anyone can sign up under an address they don't own). The owner chose ON.
- **Build our own password hashing/session layer.** Unnecessary and a security liability — Supabase
  already stores the bcrypt hash and issues the same session tokens the Spotify flow consumes.
- **Change the rate-limit helper to be IP-aware.** Not needed: `enforce_rate_limit` already takes an
  arbitrary `subject` string, so an `ip:`/`email:` subject works with zero change to ADR-0011.
- **Ship link-Spotify-later and password-reset now.** Deferred to follow-up tickets (ADR-0005
  already scopes identity-linking separately); the account is fully usable as a handle account
  without them.

## Consequences

- **AUTH-3 is satisfied by password, not OTP.** `requirements.md` AUTH-3/AUTH-6 rows and their
  superseded-text note are updated in the same PR; the `†` marker points here.
- **A Supabase dashboard step is required at deploy** (owner, not code): confirm the Email provider
  is on, keep "Confirm email" ON, and add the deployed + localhost `/auth/confirm` URLs to the
  redirect allow-list — the same allow-list the T09 `/auth/callback` already needs. Missing this
  means confirmation links won't return to the app.
- **The first anonymous (IP-keyed) rate limiting enters the codebase.** IP limits are best-effort
  (a forwarded header can be spoofed), so they are paired with Supabase's own limits and per-email
  limits — noted as a security callout.
- **Two follow-up tickets are implied, not built here:** password reset
  (`reset_password_for_email` + an `/auth/reset` flow) and link-Spotify-to-an-existing-email-account
  (the ADR-0005 identity-linking edge case: a Spotify-first and a later same-email account must
  resolve to one identity — needs the Supabase "same email = same identity" setting + a test).
- **This touches the highest-risk area** (`routers/auth.py` + `security/`), so a second review is
  encouraged (the owner may still self-merge per CLAUDE.md); the PR calls out enumeration, CSRF, and
  the proxy IP-trust behaviour.
- **ADR-0005 stays the record** for Spotify OAuth and the one-account/identity-linking model; only
  its magic-link/OTP mechanism for handle accounts is superseded here (append-only: 0005 is not
  edited beyond a status pointer to this ADR).
