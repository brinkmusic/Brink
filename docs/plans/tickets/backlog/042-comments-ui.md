---
status: Backlog
priority: Medium
complexity: Low
category: Feature
tags: [frontend, comments]
blocked_by: [012]
blocks: []
parent_ticket: null
---

# Feature: Comments UI (T42)

## Rationale
The post card has a dead comment button; this gives it a real comment input + list backed by the T12 endpoint.

## Summary
Add a real comment input and newest-first comment list to `PostCard`, wired to `GET/POST /api/posts/[id]/comments`.

## Source
- Spec reqs: **UI-4**
- ADRs: [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)

## Scope
### In Scope
- `PostCard.tsx` — comment input (non-empty), list comments with author, post via T12.
- Remove the dead/placeholder comment button.

### Out of Scope
- Comments API (T12); reactions/feed (T41).

## Validation & authz (ADR-0007)
- Client enforces non-empty for UX; the server (T12) is the real gate (non-empty + max length).

## Current State (on `develop`)
- `components/PostCard.tsx` has a non-functional comment affordance.
- Comments API comes from T12 (`blocked_by: [012]`).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `apps/web/src/components/PostCard.tsx` | MODIFY | real comment input + list |

## Testing Checklist
- [ ] submitting a comment persists and appears in the list
- [ ] empty comment is blocked client-side (and server returns 400 if forced)
- [ ] list shows newest-first with author
- [ ] dead button removed

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T12 → blocked_by 012)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T42-comments-ui`; one PR back into `develop` (never `main`). Owner: Sebastian.
