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
- ADRs: [ADR-0002](../../../decisions/adr/0002-api-and-persistence.md) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)

## Scope
### In Scope
- `POST /api/follow/[userId]` / `DELETE /api/follow/[userId]` — follow/unfollow.
- `GET /api/feed` — posts from followees + self, newest-first, with `Track`, reaction counts (per type), comment count, and the viewer's reaction flags.
- No-follow case: feed shows self (+ optional suggestions).

### Out of Scope
- Follow UI (T43), feed UI / optimistic reactions (T41).
- Profile API (T14).

## Validation & authz (ADR-0007 — required on this ticket)
- **Schema (zod):** `[userId]` path param validated; feed query params (pagination, if any) validated.
- **Business rule:** cannot follow yourself; following an unknown user → 404.
- **Authorization:** `requireUser` gates all three routes; `followerId` is the authenticated user, never client-supplied.
- **Integrity:** `Follow` composite PK `@@id([followerId, followingId])` makes duplicate follows structurally impossible; FKs cascade.
- **Rate limiting:** follow writes reuse the per-user cap helper from T10.

## Current State (on `develop`)
- `prisma/schema.prisma`: `Follow { followerId, followingId, createdAt }` with `@@id([followerId, followingId])`, `@@index([followingId])`; `Post` with `@@index([createdAt])`, relations to `reactions`/`comments`/`track`.
- `requireUser`, `ok`/`fail` helpers exist.
- No `api/follow/*` or `api/feed.ts` yet. Feed reads `Post` rows from T10 (`blocked_by: [010]`).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `api/follow/[userId].ts` | CREATE | `POST`/`DELETE` follow |
| `api/feed.ts` | CREATE | `GET` feed with counts + viewer reaction state |
| `api/__tests__/follow.test.ts` | CREATE | follow endpoint tests |
| `api/__tests__/feed.test.ts` | CREATE | feed query tests |

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
Branch off `develop` as `feat/T13-follow-feed`; one PR back into `develop` (never `main`). The feed query is the heaviest read path — make sure it uses the `@@index([createdAt])` / `@@index([followingId])` indexes and batches counts (avoid N+1 per post).
