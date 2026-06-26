---
status: Backlog
priority: High
complexity: Low
category: Feature
tags: [auth, frontend, email, supabase]
blocked_by: []
blocks: []
parent_ticket: null
---

# Feature: Email (handle) accounts via Supabase OTP (T03)

## Rationale
Brink must honor the in-scope feature of **manual posting without a Spotify account**. On `develop`, login is Spotify-only — `AuthContext.login` calls `signInWithOAuth({ provider: 'spotify' })` and `LoginPage` offers no other path. The server already supports handle users (`requireUser` auto-creates a `User` with a derived unique `handle` and null `spotifyId`; `loadProfile` already branches for "email-only users"). This ticket adds the missing front-door: an email magic-link / OTP sign-in.

## Summary
Add an email OTP sign-in path (Supabase `signInWithOtp`) and surface it in `LoginPage`, so a user can create a handle account and use the app without Spotify.

## Source
- Spec reqs: **AUTH-3** (handle accounts), **AUTH-6**
- ADRs: [ADR-0005](../../../decisions/adr/0005-identity.md) (Supabase Auth; email magic-link/OTP for handle accounts) · [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md)

## Scope
### In Scope
- `AuthContext` — add `loginWithEmail(email)` → `supabase.auth.signInWithOtp({ email })` (Supabase sends the email; no external vendor).
- `LoginPage` — "continue with email" input + a "check your inbox" sent state.
- Confirm the existing `requireUser` sync creates a handle `User` (`spotifyId = null`) on first email login.

### Out of Scope
- Linking Spotify to an existing email account later — that is ADR-0005 identity-linking, a separate ticket.
- Resend / any external email vendor (Supabase Auth sends the OTP).
- **User-chosen handle/display-name signup form** — decided cut: handles are **auto-derived** by `requireUser`. No `SignupPage`, no handle-set endpoint. Users can rename later (separate ticket if ever needed).

## Validation & authz (ADR-0007)
- **Authorization:** our sync still verifies the Supabase JWT server-side via `get_user()` in `require_user` (Supabase owns the OTP exchange itself).
- **Business rule:** handle uniqueness is already enforced by the unique `handle` constraint plus the derived-handle policy in `require_user` — no new logic needed.
- **Integrity:** `User.handle`, `User.email`, `User.supabaseUserId` are each unique in `backend/app/models.py`.

## Current State (on `develop`)
- `apps/web/src/context/AuthContext.tsx` — `login` is Spotify OAuth only; `loadProfile` already tolerates email-only users (no Spotify provider token).
- `backend/app/deps.py` — `require_user` auto-creates a handle `User` (derived unique handle, null `spotifyId`) on first login.
- `apps/web/src/pages/LoginPage.tsx` — Spotify-only UI; no email entry. No `SignupPage.tsx`.
- No `lib/spotify-auth.ts` exists (the draft's deletion target); PKCE was already removed in T02.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `apps/web/src/context/AuthContext.tsx` | MODIFY | add `loginWithEmail(email)` via `signInWithOtp` |
| `apps/web/src/pages/LoginPage.tsx` | MODIFY | email input + "check your inbox" state |
| `backend/tests/test_auth.py` | MODIFY | assert `require_user` creates a handle user (null `spotifyId`) for an email JWT |

## Testing Checklist
- [ ] email OTP sign-in returns to the app authenticated
- [ ] first email login creates a `User` with null `spotifyId` and a unique handle
- [ ] a second email user whose derived handle collides still gets a unique handle (retry loop)
- [ ] a handle account can use the app; profile renders for a user with no Spotify

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T01, T02 done)
- [x] Scope boundaries defined

## Notes
Scope locked: email users get an **auto-derived handle** from `requireUser` (the draft's `SignupPage` + custom-handle flow is cut). This keeps T03 to the email front-door only.

Branch off `develop` as `feat/T03-auth-email`; one PR back into `develop` (never `main`).
