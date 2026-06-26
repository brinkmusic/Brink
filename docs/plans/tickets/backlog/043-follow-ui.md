---
status: Backlog
priority: Low
complexity: Low
category: Feature
tags: [frontend, follow]
blocked_by: [013]
blocks: []
parent_ticket: null
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
- [ ] follow toggles optimistically and persists (T13)
- [ ] follower/following counts update
- [ ] cannot follow self (button hidden/disabled on own profile)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T13 → blocked_by 013)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T43-follow-ui`; one PR back into `develop` (never `main`). Owner: Sebastian.
