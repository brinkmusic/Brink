---
status: Backlog
priority: Low
complexity: Low
category: Feature
tags: [backend, frontend, artist, engagement]
blocked_by: [050, 011, 012]
blocks: []
parent_ticket: null
---

# Feature: Artist engagement analytics (T52)

## Rationale
Artists should see how their BTS posts perform — reactions, comments, and views surfaced back to them.

## Summary
Per-`ArtistPost` engagement (reaction/comment counts + views) surfaced to the owning artist.

## Source
- Spec reqs: **MEDIA-4**
- ADRs: [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)

## Scope
### In Scope
- Aggregate reactions/comments (and a simple view count) per `ArtistPost`; expose to the owning artist; render on the artist page.

### Out of Scope
- Storage/upload (T50/T51).

## Validation & authz (ADR-0007)
- **Authorization + ownership:** only the owning artist sees their post engagement.

## Current State (on `develop`)
- `ArtistPost` exists (T50 creates them); reactions/comments models from T11/T12.
- No engagement read path yet.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/artist.py` | MODIFY | add per-post engagement route for the owning artist |
| `apps/web/src/pages/ArtistPage.tsx` | MODIFY | render engagement |

## Testing Checklist
- [ ] engagement counts correct per post
- [ ] only the owning artist can read their engagement (403 otherwise)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T50, T11, T12 → blocked_by 050, 011, 012)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T52-artist-engagement`; one PR back into `develop` (never `main`). View counting can be best-effort. Owner: Andrea + Sebastian.
