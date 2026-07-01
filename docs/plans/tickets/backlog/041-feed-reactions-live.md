---
status: Backlog
priority: High
complexity: Medium
category: Feature
tags: [frontend, feed, reactions]
blocked_by: [010, 011, 013]
blocks: [060]
parent_ticket: null
owner: Sebastian
---

# Feature: Feed + reactions live (T41)

## Rationale
The feed is the home screen and currently renders mock data via `lib/data.getFeed`. This wires it to the real `/api/feed` with live reactions, the first fully-real user-facing surface.

## Summary
`FeedPage` reads `GET /api/feed`; `PostCard` posts reactions to T11 with optimistic UI reconciled against the server; proper loading/empty/error states; the mock feed path is removed.

## Source
- Spec reqs: **UI-2**, **UI-3**, **UI-9**
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)

## Scope
### In Scope
- `FeedPage.tsx` — fetch `/api/feed` (replace `lib/data.getFeed`); loading/empty/error states.
- `PostCard.tsx` — reaction buttons → `POST/DELETE /api/posts/[id]/reactions` (T11); optimistic update reconciled with server counts.
- Remove the mock feed fallback on this path.

### Out of Scope
- Comments UI (T42); composer (T40); final mock-file deletion (T60).

## Validation & authz (ADR-0007)
- Client sends only the reaction `type`; the server attributes it to the authenticated user (T11).

## Current State (on `develop`)
- `FeedPage.tsx` imports `getFeed` from `lib/data` (mock); `components/PostCard.tsx` exists.
- Real `/api/feed` (T13) + reactions (T11) provide data.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `apps/web/src/pages/FeedPage.tsx` | MODIFY | read `/api/feed`; states |
| `apps/web/src/components/PostCard.tsx` | MODIFY | live optimistic reactions |

## Testing Checklist
- [ ] feed renders real posts from `/api/feed` (no mock import on this path)
- [ ] reacting updates optimistically, reconciles with server counts
- [ ] un-reacting decrements correctly
- [ ] loading / empty / error states render

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T10, T11, T13 → blocked_by 010, 011, 013)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T41-feed-live`; one PR back into `develop` (never `main`). Owner: Sebastian.
