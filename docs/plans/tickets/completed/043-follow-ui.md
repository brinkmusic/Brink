---
status: Completed
priority: Low
complexity: Low
category: Feature
tags: [frontend, follow]
blocked_by: [013]
blocks: []
parent_ticket: null
owner: Sebastian
---

# Feature: Follow UI (T43)

## Rationale
The follow graph (T13) needs front-end controls: Follow/Unfollow buttons and follower counts on profiles and artist pages.

## Summary
Wire Follow/Unfollow buttons and follower/following counts on `ProfilePage` and `ArtistPage` to the T13 follow endpoints.

## Source
- Spec reqs: **UI-5**
- ADRs: [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)

## Scope
### In Scope
- `ProfilePage.tsx`, `ArtistPage.tsx` — Follow/Unfollow button (optimistic), follower/following counts via `POST/DELETE /api/follow/[userId]` (T13).

### Out of Scope
- Follow API (T13); the rest of the profile wiring (T44).

## Validation & authz (ADR-0007)
- The server attributes the follow to the authenticated user (T13); the client just toggles.

## Current State (on `develop`)
- `pages/ProfilePage.tsx`, `pages/ArtistPage.tsx` exist; no follow controls wired.
- Follow API comes from T13 (`blocked_by: [013]`).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `apps/web/src/pages/ProfilePage.tsx` | MODIFY | follow button + counts |
| `apps/web/src/pages/ArtistPage.tsx` | MODIFY | follow button + counts |

## Testing Checklist
- [x] follow toggles optimistically and persists (T13)
- [x] follower/following counts update
- [x] cannot follow self (button hidden/disabled on own profile)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T13 → blocked_by 013)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T43-follow-ui`; one PR back into `develop` (never `main`). Owner: Sebastian.

## Outcome (as built)
Built as the Python/Jinja frontend (ADR-0013). Because the Python frontend had **no profile or
artist page** to host the Follow button, this ticket also built a **minimal profile page** as the
surface:

- **Profile page:** `GET /u/{handle}` (`pages.py` `_profile_data` + `profile.html`) — the person's
  name/handle/avatar, follower + following counts (queried from the `Follow` table), a Follow/Unfollow
  button (hidden on your own profile), and their posts. A missing handle renders a friendly 404
  (`profile_missing.html`).
- **Follow button:** `static/follow.js` — optimistic toggle calling `POST/DELETE /api/follow/{userId}`
  (T13), reconciled with the server's `{following}` response; the follower count nudges to match.
- **Discovery:** feed post cards now link the author name to their profile (`/u/{handle}`), so you can
  reach someone and follow them.
- **Scope note:** this is the *minimal* profile (enough to host follow). The full "Wrapped"-style
  live stats / cluster / compatibility are **T44**, which needs the profile API **T14** — T44 layers
  those onto this same page.
- **Files:** `backend/app/routers/pages.py`, `backend/app/templates/profile.html`,
  `profile_missing.html`, `feed.html`, `backend/app/static/follow.js`, `brink.css`,
  `backend/tests/test_pages.py`. Satisfies **UI-5**. Full suite green (166).
