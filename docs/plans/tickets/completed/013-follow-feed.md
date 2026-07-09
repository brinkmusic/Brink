---
status: Completed
priority: High
complexity: Medium
category: Feature
tags: [backend, api, feed, follow, validation]
blocked_by: [010]
blocks: [014, 041, 043]
parent_ticket: null
owner: Andrea
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
- [x] follow without a session → 401
- [x] following yourself → 400
- [x] following unknown user → 404
- [x] follow then `GET /api/feed` includes the followee's posts; unfollow removes them
- [x] feed posts carry correct per-type reaction counts, comment count, and viewer reaction flags
- [x] duplicate follow is a no-op (composite PK)

## Implementation notes (as built)
- **Routers:** `backend/app/routers/follow.py` (`POST`/`DELETE /api/follow/{userId}`, idempotent via
  the `Follow` composite PK, own-only unfollow, `follow` rate-limit action) and
  `backend/app/routers/feed.py` (`GET /api/feed`). DTOs `FollowStateOut` + `FeedPostOut` added to
  `schemas.py`; both routers registered in `main.py`. Tests: `test_follow.py`, `test_feed.py`
  (conftest's in-memory DB now includes the `Follow` table).
- **No N+1:** the feed runs a fixed 4 queries regardless of post count — posts (joined to track +
  author), then grouped reaction counts, comment counts, and the viewer's own reactions.
- **Response shapes:** `reactionCounts` and `viewerReactions` always carry every reaction type
  (zeros / `false` included) for a stable frontend shape, mirroring T11's `ReactionCountsOut`.
- **Scope note — author added (agreed extension):** the feed post includes a nested `author`
  (`displayName`/`handle`/`avatarUrl`, reusing T12's `AuthorOut`) beyond the fields this ticket
  originally listed, so the T41 feed UI can show who posted without an N+1 author lookup. Approved
  during implementation.
- **Deliberately deferred:** feed **pagination** (the ticket's "if any" — not built; follow-up if
  the feed grows) and no-follow **suggestions** (out of scope — new users see only their own posts).
- **Close-out** (move backlog→completed, flip **BE-4**/**BE-7** in requirements.md, update the
  CLAUDE.md status line + tickets README) is folded into **this PR** (pre-merge close-out, per T93)
  rather than a separate follow-up.

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T01, T02 done; T10 posts → blocked_by 010)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T13-follow-feed`; one PR back into `develop` (never `main`). The feed query is the heaviest read path — make sure it uses the `createdAt` / `followingId` indexes and batches counts (avoid N+1 per post).
