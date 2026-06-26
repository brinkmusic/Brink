---
status: Backlog
priority: High
complexity: Medium
category: Feature
tags: [backend, api, posts, validation]
blocked_by: []
blocks: [011, 012, 013, 021, 040, 041]
parent_ticket: null
---

# Feature: Posts API + Track upsert (T10)

## Rationale
The feed, reactions, comments, and composer all read and write `Post` rows, so the posts endpoint is the spine of the social layer — nothing in EPIC C/F works until a post can be created and listed against a real `Track`. On `develop` the Supabase + Prisma + auth foundation is already in place (T01/T02), but there is **no posts endpoint yet**; the frontend still renders mock feed data from `apps/web/src/lib/data.ts`. T10 introduces the first real `Post`/`Track` write path on that foundation.

## Summary
Serverless endpoints to create a post and list a user's posts, upserting the referenced `Track` so every post links to a real track row.

## Source
- Spec reqs: **BE-3** (posts), **SP-3** (track upsert)
- ADRs: [ADR-0002](../../../decisions/adr/0002-api-and-persistence.md) (Vercel + Supabase + Prisma) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md) (validation/authz required on every API ticket)

## Scope
### In Scope
- `POST /api/posts` — create a post (auth required); `source ∈ {MANUAL, SPOTIFY}`.
- `GET /api/posts?userId=` — list a user's posts, newest-first, with linked track.
- `upsertTrack` helper — ensure a `Track` row exists from supplied Spotify metadata.
- The ADR-0007 layers for these two routes (below).

### Out of Scope
- Reactions (T11), comments (T12), the feed join (T13), the composer UI (T40).
- Editing/deleting posts.
- Retiring the legacy jsonblob (`api/state.js`) and frontend mock (`lib/data.ts`) — that is T60.

## Validation & authz (ADR-0007 — required on this ticket)
- **Schema (zod):** request body/query parsed at handler top; bad shape → 400 via `api/_lib/respond.ts`. No handler trusts raw `req.body`.
- **Business rules:** `source` is a valid enum; track metadata present for a SPOTIFY-source post; reject empty/oversized payloads.
- **Authorization:** `POST` passes through `requireUser` (`api/_lib/auth.ts`); `authorId` is the authenticated user, never client-supplied.
- **Integrity:** FKs `Post.trackId → Track`, `Post.authorId → User`, and the `source` enum enforced in `prisma/schema.prisma`.
- **Rate limiting:** write endpoint → shared-store per-user cap (ADR-0007 §5; the middleware is not yet present in `api/_lib/`, so implement the per-user cap behind a small helper here).

## Current State (on `develop`)
- Present from T01/T02: `api/_lib/prisma.ts`, `api/_lib/respond.ts` (`{data}|{error}`), `api/_lib/auth.ts` (`requireUser`).
- `Post`, `Track`, and `PostSource` already modeled in `prisma/schema.prisma`.
- No `api/posts/*` endpoint and no `api/_lib/tracks.ts` yet.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `api/posts/index.ts` | CREATE | `POST` create + `GET` list-by-user |
| `api/_lib/tracks.ts` | CREATE | `upsertTrack(metadata)` |
| `api/__tests__/posts.test.ts` | CREATE | endpoint tests |

## Testing Checklist
- [ ] `POST /api/posts` without a session → 401
- [ ] valid `POST` creates a `Post` + upserts the `Track`
- [ ] malformed track payload → 400 (zod)
- [ ] invalid `source` value → 400
- [ ] `authorId` cannot be spoofed via body (always the authenticated user)
- [ ] `GET /api/posts?userId=` returns that user's posts newest-first with track

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T01, T02 done; rate-limit helper implemented here)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T10-posts-api`; one PR back into `develop` (never `main`). Rate-limit middleware (ADR-0007 §5, Postgres-backed store) is cross-cutting — factor the per-user cap into an `api/_lib` helper so later endpoints reuse it.
