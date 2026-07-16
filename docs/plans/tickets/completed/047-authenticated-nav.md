---
status: Completed
priority: High
complexity: Low
category: Feature
tags: [frontend, navigation, enablement-gap]
blocked_by: []
blocks: [046]
parent_ticket: null
owner: Sebastian
---

# Feature: Authenticated nav — feed/profile/artist links + logout (T47)

## Rationale
Gap #2 of the [2026-07-15 frontend-enablement audit](../../reviews/2026-07-15-frontend-enablement-gaps.md):
`base.html` serves the **public landing nav to every page** — even logged-in ones. Nothing links
to `/feed`, nothing links to `/artist` (artists can't find their own upload page), your own
profile isn't linked, and `/auth/logout` exists but is linked from **nowhere** — a logged-in user
literally cannot log out without typing the URL.

## Summary
Pass the logged-in `viewer` (already resolved by the page routes' `require_user`/session check)
into the template context, and render a conditional nav in `base.html`: logged out → today's
landing nav; logged in → Feed, My profile (`/u/{own handle}`), Artist studio (only if
`viewer.isArtist`), and Log out.

## Source
- Spec reqs: **UI-2** (app shell usability)
- The T46 search box slots into this nav (hence `blocks: [046]`).

## Scope
### In Scope
- `routers/pages.py`: ensure every page route passes `viewer` (or `None`) to its template.
- `base.html`: conditional nav block; active-page highlight optional.
- Logout as a link/button to `GET /auth/logout`.
- Tests in `test_pages.py`: nav shows the right links logged in vs out; artist link only for
  artists.

### Out of Scope
- User search itself (T46). Notifications, settings, or any new pages.

## Validation & authz (ADR-0007)
Rendering-only — gating stays in the routes. The artist link is convenience, not access control
(the `/artist` route + APIs already enforce `isArtist` server-side).

## Current State (on `develop`)
- `base.html` has one static nav: "Log in with Spotify" + two landing-page anchors, shown to
  everyone on every page.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/templates/base.html` | MODIFY | conditional authed nav |
| `backend/app/routers/pages.py` | MODIFY | pass `viewer` everywhere |
| `backend/tests/test_pages.py` | MODIFY | nav variants |

## Testing Checklist
- [x] logged out: landing nav unchanged
- [x] logged in: Feed / My profile / Log out present on every page; Artist studio only if artist
- [x] logout link actually ends the session and returns to `/` (the link points at the existing
      `GET /auth/logout` from T09, whose session-clearing behavior the T09 tests already cover)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (none)
- [x] Scope boundaries defined

## Notes
Branch `feat/T47-authenticated-nav`. Highest impact per line of code in the audit — do before T46.

## Outcome (2026-07-16)
As specced, no scope change:
- `backend/app/routers/pages.py` — every page route now passes `viewer` into its template. Gated
  pages pass the user `require_user` already resolved; the public landing page uses a new
  `_optional_viewer()` helper that runs the same session check but returns `None` (instead of
  redirecting) for a signed-out visitor, so `/` stays public.
- `backend/app/templates/base.html` — the shared nav is now conditional: signed out → the original
  landing nav (anchors + "Log in with Spotify"); signed in → Feed, My profile (`/u/{handle}`),
  Artist studio (only when `viewer.is_artist`), and Log out (`GET /auth/logout`).
- 4 new tests in `backend/tests/test_pages.py` cover both nav variants, the artist-only link, and
  the signed-in nav on the public landing page. Full suite green (183 passed).
Unblocks the T46 search box's slot in the nav (T46 also needs T15).
