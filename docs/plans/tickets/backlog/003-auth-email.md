---
status: Backlog
priority: High
complexity: Medium
category: Feature
tags: [auth, backend, frontend, email, supabase, security]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Feature: Email/password signup + login, server-side (T03)

> **Rewritten 2026-07-15** (coherence sweep T79). The previous version of this ticket targeted
> the retired `apps/web/` React SPA and Supabase magic-link/OTP. The SPA is gone (T60) and the
> owner has since decided on **email + password**, so the flow is now server-side, mirroring the
> T09 Spotify login. Full investigation:
> [2026-07-15 auth investigation](../../reviews/2026-07-15-auth-email-signup-investigation.md).

## Rationale
Login today is Spotify-only. Brink must honor **manual posting without a Spotify account**
(AUTH-3/AUTH-6): a person without Spotify should still be able to sign up, post, react, comment,
and follow. The investigation confirmed the backend already tolerates handle-only users end to
end (search uses an app-level Spotify token, stats/now-playing degrade to empty states, the
snapshot cron skips unlinked users) — the only missing piece is the front door.

## Summary
Server-side email/password signup and login using Supabase Auth (the same provider and Python
SDK we already call for OAuth), reusing the existing encrypted `brink_session` cookie and
`get_or_create_user` sync. Plus the first **IP-keyed** rate limiting (signup/login are
unauthenticated, so the existing user-id-keyed helper needs an IP/email subject).

## Source
- Spec reqs: **AUTH-3** (handle accounts), **AUTH-6**
- ADRs: [ADR-0005](../../../decisions/adr/0005-identity.md) chose magic-link/OTP — this ticket
  **must open with a new ADR** superseding that choice with email+password (append-only rule).
  Also [ADR-0011](../../../decisions/adr/0011-rate-limiting.md) (rate-limit helper).
- Investigation: [2026-07-15](../../reviews/2026-07-15-auth-email-signup-investigation.md)

## Scope
### In Scope
- New ADR: email+password via Supabase Auth (supersedes ADR-0005's OTP choice for this surface).
- `security/supabase.py`: `sign_up_email(email, password)` + `sign_in_password(email, password)`
  wrappers (the installed `supabase-auth` client exposes both).
- `routers/auth.py`: `POST /auth/signup`, `POST /auth/login-email` (+ `GET /auth/confirm` landing
  if email confirmations are ON) — on success reuse `get_or_create_user` and
  `login_session.set_cookie` exactly as the Spotify callback does. Pass a real `Response` so
  refreshed cookies stick.
- Rate limiting: a `_client_ip` helper that trusts Render's `X-Forwarded-For`, then
  `enforce_rate_limit` keyed on `ip:<addr>` and `email:<addr>` for signup/login attempts
  (no change to the helper's table/logic — it already takes an arbitrary subject string).
- CSRF protection on the forms (same pattern as the T09 state cookie).
- Jinja: `signup.html` + email login form (new templates), links from `home.html`/`base.html`.
- Tests: `backend/tests/test_auth_email.py` — signup creates a handle `User`
  (`spotify_id = NULL`), login sets the session cookie, rate limits fire, wrong password fails
  cleanly.
- Docs sync: CLAUDE.md status line, requirements.md AUTH-3/AUTH-6 rows.

### Out of Scope (file as follow-up tickets when this lands)
- Password reset flow.
- Linking Spotify to an existing email account later (ADR-0005 identity-linking).
- User-chosen handles (auto-derived handle stays, per the existing AUTH-3 decision).

## Owner decisions (Andrea, 2026-07-15)
1. **Email confirmations ON** — signup requires clicking the confirmation email before login
   works. Implementation consequences: build the `GET /auth/confirm` landing route, turn on
   "Confirm email" in the Supabase dashboard (brink-dev first, prod at release), and add the
   deployed `/auth/confirm` URL to the Supabase redirect allow-list.
2. **Password minimum = 6 characters** — Supabase's default; enforce the same check in our form
   for a friendly error before the round-trip.

## Validation & authz (ADR-0007)
- Supabase owns password hashing/verification; we never see or store the password.
- Session semantics identical to Spotify login: JWT validated server-side via `get_user()`.
- This touches `routers/auth.py` + `security/` — **highest-risk area**; second review encouraged.

## Current State (on `develop`)
- `routers/auth.py`: Spotify-only PKCE flow (T09). `deps.py:get_or_create_user` already creates
  handle users with derived unique handles and `spotify_id = NULL`.
- `rate_limit.py`: generic subject string, but every caller keys on `user.id`; no IP extraction
  helper exists.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `docs/decisions/adr/00XX-email-password-auth.md` | CREATE | supersede ADR-0005's OTP choice |
| `backend/app/security/supabase.py` | MODIFY | sign-up / sign-in-password wrappers |
| `backend/app/routers/auth.py` | MODIFY | /auth/signup, /auth/login-email (+ /auth/confirm) |
| `backend/app/deps.py` or `routers/auth.py` | MODIFY | `_client_ip` helper for anon rate limits |
| `backend/app/templates/signup.html` (+ login form) | CREATE | the front door |
| `backend/app/templates/home.html`, `base.html` | MODIFY | entry links |
| `backend/tests/test_auth_email.py` | CREATE | signup/login/rate-limit/failure tests |

## Testing Checklist
- [ ] signup creates a Supabase user + a handle `User` row (`spotify_id` NULL, unique handle)
- [ ] login sets the encrypted session cookie; `/feed` accessible; logout works
- [ ] wrong password → clean error, no cookie
- [ ] signup/login rate limit fires per IP and per email
- [ ] an email-only user can post / react / comment / follow / view profiles (no 500s anywhere)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (none — T09 infra is in place)
- [x] Owner decisions recorded (confirmations ON; 6-char minimum) — ready to start

## Notes
Branch `feat/T03-auth-email`. Estimated ~1–1.5 days. Supabase dashboard config needed: enable
email provider (it is ON by default) and decide the confirm-email setting; if confirmations are
ON, add the deployed `/auth/confirm` URL to the redirect allow-list.
