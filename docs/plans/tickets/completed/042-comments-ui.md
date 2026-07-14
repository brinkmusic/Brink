---
status: Completed
priority: Medium
complexity: Low
category: Feature
tags: [frontend, comments]
blocked_by: [012]
blocks: []
parent_ticket: null
owner: Sebastian
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
- [x] submitting a comment persists and appears in the list
- [x] empty comment is blocked client-side (and server returns 400 if forced)
- [x] list shows newest-first with author
- [x] dead button removed (n/a — the Python feed had no comment affordance; added fresh)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T12 → blocked_by 012)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T42-comments-ui`; one PR back into `develop` (never `main`). Owner: Sebastian.

## Outcome (as built)
Built as the **Python/Jinja frontend** (ADR-0013). Each feed post card gained a `💬 <count>`
toggle (the count comes from `build_feed`'s `commentCount`) that opens a panel. On first open
`static/comments.js` lazily fetches `GET /api/posts/{id}/comments` and renders each comment
(author, text, "time ago") newest-first; the add-comment form POSTs to `POST /api/posts/{id}/comments`
(T12), prepends the new comment, and bumps the count. Non-empty is enforced client-side; the server
is the real gate. User text is inserted with `textContent` (never `innerHTML`) so it can't inject
HTML. Files: `backend/app/templates/feed.html`, `backend/app/static/comments.js`,
`backend/app/static/brink.css`, `backend/tests/test_pages.py`. Satisfies **UI-4**. Full suite green (157).
