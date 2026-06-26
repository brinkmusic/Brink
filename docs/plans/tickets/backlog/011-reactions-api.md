---
status: Backlog
priority: Medium
complexity: Low
category: Feature
tags: [backend, api, reactions, validation]
blocked_by: [010]
blocks: [041, 052]
parent_ticket: null
---

# Feature: Reactions API (T11)

## Rationale
Reactions are the lightest-weight social signal on a post and feed the engagement counts the feed and artist-engagement views depend on. The `Reaction` model and its dedup constraint already exist in the schema; what's missing is the endpoint to add and remove a reaction.

## Summary
A `POST`/`DELETE` endpoint on a post to add or remove the authenticated user's reaction of a given type, server-deduped, returning fresh reaction counts.

## Source
- Spec reqs: **BE-5**
- ADRs: [ADR-0002](../../../decisions/adr/0002-api-and-persistence.md) (Prisma/Supabase) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md) (validation/authz on every API ticket)

## Scope
### In Scope
- `POST /api/posts/[id]/reactions` — add a reaction `{ type }` for the authenticated user (idempotent).
- `DELETE /api/posts/[id]/reactions` — remove that user's reaction of `{ type }`.
- Return fresh per-type reaction counts for the post.

### Out of Scope
- The reaction UI / optimistic updates (T41).
- Comments (T12), feed (T13).

## Validation & authz (ADR-0007 — required on this ticket)
- **Schema (zod):** `type` parsed against the `ReactionType` enum (`HEART | FIRE | SPARKLE`); `[id]` path param validated; bad shape → 400 via `fail()`.
- **Business rule:** one reaction per `(user, post, type)` — the app checks/upserts so a double-react is a no-op (idempotent), not an error.
- **Authorization:** `requireUser` gates both verbs; `userId` is the authenticated user, never client-supplied. (Removing only your own reaction.)
- **Integrity:** `@@unique([postId, userId, type])` makes duplicates structurally impossible even if the app check is skipped; FKs cascade-delete with the post/user.
- **Rate limiting:** write endpoint → reuse the per-user cap helper from T10.

## Current State (on `develop`)
- `prisma/schema.prisma`: `Reaction` with `@@unique([postId, userId, type])`; `enum ReactionType { HEART FIRE SPARKLE }`; FKs `onDelete: Cascade`.
- `api/_lib/respond.ts` exposes `ok(res, data, status)` / `fail(res, message, status)`.
- `api/_lib/auth.ts` `requireUser` exists.
- No `api/posts/[id]/reactions.ts` yet. The post target comes from T10 (`blocked_by: [010]`).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `api/posts/[id]/reactions.ts` | CREATE | `POST` add / `DELETE` remove + fresh counts |
| `api/__tests__/reactions.test.ts` | CREATE | endpoint tests |

## Testing Checklist
- [ ] `POST` without a session → 401
- [ ] invalid `type` (not in `ReactionType`) → 400
- [ ] double-react same type → single row (idempotent); response counts unchanged
- [ ] `DELETE` removes the user's reaction; counts decrement
- [ ] a user cannot remove another user's reaction
- [ ] response returns correct per-type counts for the post

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T01, T02 done; T10 post target → blocked_by 010)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T11-reactions-api`; one PR back into `develop` (never `main`). Reuses the rate-limit helper introduced in T10.
