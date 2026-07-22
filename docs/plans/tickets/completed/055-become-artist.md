---
status: Completed
priority: Medium
complexity: Small
category: Feature
tags: [backend, frontend, artist, account]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Feature: Self-serve "become an artist" (T55)

## Rationale
The artist portal (T50–T54) gates everything on `User.isArtist`, but **nothing in the app ever
sets that flag** — new accounts default to `isArtist=false`, and the only way to turn an account
into an artist today is to edit the `isArtist` column directly in the Supabase database. T50
explicitly deferred this "provisioning path" as out of scope. This ticket adds the missing in-app
path so an owner can become an artist without touching the database.

## Summary
A logged-in user can flip their own account to an artist account from their **own profile page**,
unlocking the `/artist` studio + upload UI and the "Artist posts" section. One account, one login —
the account gains artist abilities; it is **not** a separate/linked account.

## Source
- Spec reqs: **MEDIA-6** (new — self-serve artist designation)
- ADRs: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (Jinja/HTMX frontend) ·
  [ADR-0012](../../../decisions/adr/0012-camelcase-dtos.md) (camelCase DTO) ·
  [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md) (authz)

## Decisions (owner-confirmed)
- **Self-serve, no approval.** Any logged-in user can make themselves an artist — a closed,
  team-controlled demo needs no gatekeeping (consistent with ADR-0008).
- **One-way.** You can *become* an artist; there is no in-app "revert to listener" (avoids the
  "what happens to existing artist posts?" question). Reverting still needs a DB edit if ever wanted.
- **Button lives on the profile page** (own profile only), not the nav.

## Scope
### In Scope
- `POST /api/me/become-artist` — login-gated; sets `is_artist = true` on the **authenticated**
  caller (never a client-supplied id, so it can't be spoofed). Idempotent — calling it when already
  an artist is a no-op success.
- A "Become an artist" button on your **own** profile, shown only when you are not already an artist.
- The browser code that calls the endpoint and reloads so the nav + studio unlock.

### Out of Scope
- Reverting to a listener account (one-way by decision above).
- Choosing account type at signup (separate flow if ever wanted).
- Any separate/linked "artist account" identity — this is one account with a flag.
- Approval queues / moderation (ADR-0008).

## Validation & authz (ADR-0007)
- **Authorization:** `require_user` — the flag is set on the caller from their session, never from
  the request body.
- **Integrity:** idempotent write; already-artist stays artist.

## Current State (on `develop`)
- `User.is_artist` exists (`backend/app/models.py`), read across the app to gate the artist portal,
  but never written to `true` by any code path.
- `_profile_data` already returns `is_artist` and `is_self` to the profile template.
- Existing `/api/me/*` router: `backend/app/routers/now_playing.py` (`GET /api/me/now-playing`).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/me.py` | CREATE | `POST /api/me/become-artist` |
| `backend/app/schemas.py` | MODIFY | `ArtistStateOut` DTO (`isArtist`) |
| `backend/app/main.py` | MODIFY | register the router |
| `backend/app/templates/profile.html` | MODIFY | own-profile "Become an artist" button |
| `backend/app/static/become-artist.js` | CREATE | call the endpoint + reload |
| `backend/tests/test_me.py` | CREATE | endpoint tests |

## Testing Checklist
- [x] unauthenticated → 401 envelope
- [x] a listener account becomes an artist → 200, `isArtist=true` persisted in the DB
- [x] already an artist → idempotent 200, still `isArtist=true`
- [x] own non-artist profile renders the "Become an artist" button + loads its script
- [x] own artist profile hides the button

## Outcome (as built)
Adds the missing in-app path to become an artist — before this the `is_artist` flag could only be
set by editing the Supabase database by hand (T50 had explicitly deferred this provisioning path).

- `POST /api/me/become-artist` (`backend/app/routers/me.py`, new) — login-gated; flips
  `is_artist = true` on the **authenticated caller**, resolved from the request session by id (never
  a client-supplied id, so it can't be spoofed — same unspoofable-subject precedent as `Post`/
  `Follow`). **Idempotent**: already-an-artist is a no-op success. Returns the camelCase
  `ArtistStateOut` (`{ isArtist: true }`, ADR-0012).
- **Own-profile button** — `backend/app/templates/profile.html` shows a "Become an artist" button
  only when `p.is_self and not p.is_artist`; `backend/app/static/become-artist.js` (new) POSTs to the
  endpoint and reloads so the nav "Artist studio" link + the profile's artist surface unlock.
- **One-way by decision** — no in-app revert to listener (avoids the "what happens to existing
  artist posts?" question); reverting would still need a DB edit.
- **Files:** `backend/app/routers/me.py` (new) · `backend/app/schemas.py` (`ArtistStateOut`) ·
  `backend/app/main.py` (router registered) · `backend/app/templates/profile.html` (button + script) ·
  `backend/app/static/become-artist.js` (new) · `backend/tests/test_me.py` (new, 3 tests) ·
  `backend/tests/test_pages.py` (+2 button-render tests) ·
  `backend/tests/test_api_surface.py` (route added to the T61 inventory).
- **Tests:** 5 new; full backend suite **222 passed**. No DB migration (the `isArtist` column already
  exists — this only writes it).
- **Deliberate scope calls:** self-serve with no approval queue (closed team-controlled demo,
  ADR-0008); one-way; button on the profile page (owner's call), not the nav; no rate-limit (a
  one-way self-flip has no abuse pattern to cap).

## Notes
Branch off `develop` as `feat/T55-become-artist`; one PR back into `develop` (never `main`).
Owner: Andrea.
