---
status: Backlog
priority: High
complexity: Medium
category: Feature
tags: [backend, api, feed, follow, validation]
blocked_by: [010]
blocks: [014, 041, 043]
parent_ticket: null
---

# Feature: Follow graph + Feed (T13)

## Rationale
The feed is the app's home surface, and it must be driven by a real follow graph rather than "show all users." This ticket builds both halves: the follow/unfollow endpoint and the feed query that joins a user's followees' posts with engagement state.

## Summary
`POST`/`DELETE` follow endpoints plus a `GET /api/feed` that returns posts from followed users + self, newest-first, each with track, reaction/comment counts, and the viewer's own reaction state.

## Source
- Spec reqs: **BE-4** (follow), **BE-7** (feed)
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)

## Scope
### In Scope
- `POST /api/follow/{userId}` / `DELETE /api/follow/{userId}` — follow/unfollow.
- `GET /api/feed` — posts from followees + self, newest-first, with `Track`, reaction counts (per type), comment count, and the viewer's reaction flags.
- No-follow case: feed shows self (+ optional suggestions).

### Out of Scope
- Follow UI (T43), feed UI / optimistic reactions (T41).
- Profile API (T14).

## Validation & authz (ADR-0007 — required on this ticket)
- **Schema (Pydantic):** `{userId}` path param validated; feed query params (pagination, if any) validated.
- **Business rule:** cannot follow yourself; following an unknown user → 404.
- **Authorization:** `require_user` gates all three routes; `followerId` is the authenticated user, never client-supplied.
- **Integrity:** `Follow` composite PK `@@id([followerId, followingId])` makes duplicate follows structurally impossible; FKs cascade.
- **Rate limiting:** follow writes reuse the per-user cap helper from T10.

## Current State (on `develop`)
- `backend/app/models.py`: `Follow { followerId, followingId, createdAt }` with a composite PK `(followerId, followingId)`, index on `followingId`; `Post` with an index on `createdAt`, relations to `reactions`/`comments`/`track`.
- `require_user` (`backend/app/deps.py`), `ok`/`fail` (`backend/app/responses.py`) helpers exist.
- No follow/feed routers (`backend/app/routers/follow.py`, `backend/app/routers/feed.py`) yet. Feed reads `Post` rows from T10 (`blocked_by: [010]`).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/follow.py` | CREATE | `POST`/`DELETE` follow |
| `backend/app/routers/feed.py` | CREATE | `GET` feed with counts + viewer reaction state |
| `backend/tests/test_follow.py` | CREATE | follow endpoint tests |
| `backend/tests/test_feed.py` | CREATE | feed query tests |

## Testing Checklist
- [ ] follow without a session → 401
- [ ] following yourself → 400
- [ ] following unknown user → 404
- [ ] follow then `GET /api/feed` includes the followee's posts; unfollow removes them
- [ ] feed posts carry correct per-type reaction counts, comment count, and viewer reaction flags
- [ ] duplicate follow is a no-op (composite PK)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T01, T02 done; T10 posts → blocked_by 010)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T13-follow-feed`; one PR back into `develop` (never `main`). The feed query is the heaviest read path — make sure it uses the `createdAt` / `followingId` indexes and batches counts (avoid N+1 per post).
