---
status: Completed
priority: Medium
complexity: Low
category: Feature
tags: [backend, api, comments, validation]
blocked_by: [010]
blocks: [042, 052]
parent_ticket: null
owner: Andrea
---

# Feature: Comments API (T12)

## Rationale
Comments are the threaded social signal on a post (heavier than a reaction) and back the comment UI and per-post engagement counts. The `Comment` model exists in the schema; what's missing is the endpoint to create and list comments.

## Summary
A `POST`/`GET` endpoint on a post to create the authenticated user's comment and list a post's comments newest-first with author info.

## Source
- Spec reqs: **BE-6**
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md) (FastAPI/SQLModel/Supabase) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md) (validation/authz on every API ticket)

## Scope
### In Scope
- `POST /api/posts/{id}/comments` — create a comment `{ body }` for the authenticated user.
- `GET /api/posts/{id}/comments` — list the post's comments newest-first, each with author (`displayName`, `handle`, `avatarUrl`).

### Out of Scope
- Editing/deleting comments.
- The comment UI (T42); feed (T13).

## Validation & authz (ADR-0007 — required on this ticket)
- **Schema (Pydantic):** `body` is a non-empty string with a sane max length (e.g. ≤ 2000 chars); `{id}` path param validated; bad shape → 400 via `fail()`. (`Comment.body` has no length constraint in the schema, so the cap is enforced here.)
- **Business rule:** non-empty body after trim; comment is attributed to the authenticated user.
- **Authorization:** `require_user` gates both verbs (Brink is a private app); `userId` is the authenticated user, never client-supplied.
- **Integrity:** FKs `Comment.postId → Post`, `Comment.userId → User` (`onDelete: Cascade`); `@@index([postId])` for list performance.
- **Rate limiting:** write endpoint → reuse the per-user cap helper from T10.

## Current State (on `develop`)
- `backend/app/models.py`: `Comment { id, postId, userId, body, createdAt }`, FKs cascade, index on `postId`. No length constraint on `body`.
- `backend/app/responses.py` (`ok`/`fail`) and `backend/app/deps.py` (`require_user`) exist.
- No comments router (`backend/app/routers/comments.py`) yet. The `{id}` path-param convention is first introduced by T10/T11; the post target comes from T10 (`blocked_by: [010]`).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/comments.py` | CREATE | `POST` create / `GET` list newest-first with author |
| `backend/tests/test_comments.py` | CREATE | endpoint tests |

## Testing Checklist
- [ ] `POST` without a session → 401
- [ ] empty / whitespace-only body → 400
- [ ] body over max length → 400
- [ ] valid `POST` persists a `Comment` attributed to the authenticated user
- [ ] `GET` returns the post's comments newest-first, each with author fields

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T01, T02 done; T10 post target → blocked_by 010)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T12-comments-api`; one PR back into `develop` (never `main`). Reuses the rate-limit helper introduced in T10.
