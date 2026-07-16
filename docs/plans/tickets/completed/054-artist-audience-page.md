---
status: Completed
priority: Medium
complexity: Medium
category: Feature
tags: [frontend, artist, engagement, enablement-gap]
blocked_by: [053]
blocks: []
parent_ticket: null
owner: Sebastian
---

# Feature: Audience view of artist posts + engagement UI (T54)

## Rationale
Gaps #4–5 of the [2026-07-15 frontend-enablement audit](../../reviews/2026-07-15-frontend-enablement-gaps.md):
`/artist` shows only **your own** posts (`artist_user_id == user.id`), so fans have no page that
displays any artist's posts — which also means the entire T52 engagement API (audience reactions
+ comments on artist posts, owner-only engagement counts) is **shipped, tested, and 100% dead
code**: no template renders a single reaction button, comment box, or count for artist posts.

## Summary
A public-to-logged-in-users artist page (e.g. `/u/{handle}` gains an "Artist posts" section when
`isArtist`, or a dedicated `/artist/{handle}` — decide in the PR, say why) rendering the artist's
posts (signed image URLs from T53, caption, linked track) with the T52 reaction/comment UI
(reuse `reactions.js`/`comments.js` patterns pointed at `/api/artist/posts/{id}/...`), and an
engagement summary (counts) visible only to the owning artist on their own page.

## Source
- Spec reqs: **MEDIA-4** (engagement surface), **UI-5**
- APIs already live: `POST/DELETE /api/artist/posts/{id}/reactions`,
  `POST/GET /api/artist/posts/{id}/comments`, `GET /api/artist/posts/{id}/engagement` (T52).

## Scope
### In Scope
- Backend: one read endpoint or page-route query listing an artist's posts by handle
  (login-gated like the feed).
- The page/section + JS wiring for reactions and comments on artist posts.
- Owner-only engagement counts rendered from `GET .../engagement` (the API already 403s
  non-owners — the UI just hides it for them).
- The deferred T52 view count stays deferred unless trivially countable here.

### Out of Scope
- Changing any T52 API. Feed integration of artist posts. Image work beyond consuming T53.

## Validation & authz (ADR-0007)
All enforcement already server-side (T52); UI only reflects it.

## Current State (as built)
- Artist profiles (`/u/{handle}` for `isArtist` users) now render an "Artist posts" section with
  signed image URLs, captions, public reaction/comment controls, and owner-only engagement totals.
  `/artist` remains the own-post upload studio.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/pages.py` | MODIFY | audience artist page/section route |
| `backend/app/templates/` (profile or new artist page) | MODIFY/CREATE | render posts + engagement |
| `backend/app/static/artist-engagement.js` | CREATE | reactions/comments wiring |
| `backend/tests/test_pages.py` | MODIFY | page renders; owner-only counts hidden for others |

## Testing Checklist
- [x] a fan can see an artist's posts with images (T53 URLs) and react/comment
- [x] the artist sees engagement counts on their own posts; fans don't
- [x] non-artist profiles unaffected

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T53)
- [x] Scope boundaries defined

## Notes
Branch `feat/T54-artist-audience-page`.

## Outcome
T54 chose the existing profile URL (`/u/{handle}`) as the audience artist page because user search,
feed authors, and follow already resolve to profiles. `backend/app/routers/pages.py` now signs each
artist image path and builds public reaction/comment counts plus the viewer's own reactions for
artist posts. `backend/app/templates/profile.html` renders the artist-post section, public
reaction/comment controls, and owner-only engagement totals. `backend/app/static/artist-engagement.js`
calls the existing T52 endpoints without changing API behavior. The deferred view count remains out
of scope.
