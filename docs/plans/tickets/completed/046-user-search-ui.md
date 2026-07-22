---
status: Completed
priority: High
complexity: Low
category: Feature
tags: [frontend, social, search, enablement-gap]
blocked_by: [015, 047]
blocks: []
parent_ticket: null
owner: Sebastian
---

# Feature: User search UI — find people to follow (T46)

## Rationale
The owner's exact complaint (2026-07-15): "I can follow someone, but I don't have a search bar
to find their user — I need to paste the correct URL to get to their profile." T15 supplies the
API; this ticket puts a search box in the authenticated nav (T47) so the follow feature (T13/T43)
is actually reachable. See the
[2026-07-15 frontend-enablement audit](../../reviews/2026-07-15-frontend-enablement-gaps.md), gap #1.

## Summary
A "Find people" search input in the logged-in nav (or on the feed page) that calls
`GET /api/users/search?q=` as you type (debounced) or on submit, and renders results as links to
`/u/{handle}` — where the existing Follow button (T43) already lives.

## Source
- Spec reqs: **UI-5** (profiles/follow surface)
- Depends on: **T15** (the API), **T47** (an authenticated nav to put the box in)

## Scope
### In Scope
- Search input + results dropdown/list (`backend/app/static/user-search.js`, new; pattern-match
  `composer.js`'s debounced Spotify search).
- Each result: display name, @handle, artist badge if `isArtist`, linking to `/u/{handle}`.
- Empty state ("no one found") and a hint at min query length.

### Out of Scope
- Any change to the search API. Follower/following lists (T16). Suggested-users/discovery feed.

## Validation & authz (ADR-0007)
Client-side only; the API enforces login + rate limits.

## Current State (as built)
- The authenticated nav has a "Find people" search box on every signed-in page. It calls the T15
  user-search API and renders profile links to `/u/{handle}`, where the existing follow button
  lives.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/static/user-search.js` | CREATE | debounced search + results rendering |
| `backend/app/templates/base.html` (nav) | MODIFY | the search box |
| `backend/tests/test_pages.py` | MODIFY | search box present when logged in |

## Testing Checklist
- [x] typing a handle fragment shows matching users; clicking goes to their profile
- [x] works from every authed page (box lives in the shared nav)
- [x] no results / short query states render sensibly

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T15, T47)
- [x] Scope boundaries defined

## Notes
Branch `feat/T46-user-search-ui`.

## Outcome
T46 added `backend/app/static/user-search.js`, a shared authenticated-nav search form in
`backend/app/templates/base.html`, and matching styles in `backend/app/static/brink.css`. The UI
debounces calls to `GET /api/users/search?q=`, shows a two-character hint, renders empty/error
states, and inserts user display names/handles with `textContent` so API data cannot inject HTML.
`backend/tests/test_pages.py` now asserts the signed-in nav renders and loads the user-search
script. No API behavior changed.
