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
The feed, reactions, comments, and composer all read and write `Post` rows, so the posts endpoint is the spine of the social layer — nothing in EPIC C/F works until a post can be created and listed against a real `Track`. On `develop` the Supabase + SQLModel + auth foundation is already in place (T01/T02 + the FastAPI port T04–T06), but there is **no posts endpoint yet**; the frontend still renders mock feed data from `apps/web/src/lib/data.ts`. T10 introduces the first real `Post`/`Track` write path on that foundation.

## Summary
FastAPI routes to create a post and list a user's posts, upserting the referenced `Track` so every post links to a real track row.

## Source
- Spec reqs: **BE-3** (posts), **SP-3** (track upsert)
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md) (FastAPI + Render + Supabase + SQLModel) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md) (validation/authz required on every API ticket)

## Scope
### In Scope
- `POST /api/posts` — create a post (auth required); `source ∈ {MANUAL, SPOTIFY}`.
- `GET /api/posts?userId=` — list a user's posts, newest-first, with linked track.
- `upsert_track` helper — ensure a `Track` row exists from supplied Spotify metadata.
- The ADR-0007 layers for these two routes (below).

### Out of Scope
- Reactions (T11), comments (T12), the feed join (T13), the composer UI (T40).
- Editing/deleting posts.
- Retiring the legacy jsonblob (`api/state.js`) and frontend mock (`lib/data.ts`) — that is T60.

## Validation & authz (ADR-0007 — required on this ticket)
- **Schema (Pydantic):** request body/query parsed by Pydantic models at the route boundary; bad shape → 400 via `backend/app/responses.py` (`fail()`). No route trusts the raw request body.
- **Business rules:** `source` is a valid enum; track metadata present for a SPOTIFY-source post; reject empty/oversized payloads.
- **Authorization:** `POST` depends on `require_user` (`backend/app/deps.py`); `authorId` is the authenticated user, never client-supplied.
- **Integrity:** FKs `Post.trackId → Track`, `Post.authorId → User`, and the `source` enum enforced in `backend/app/models.py`.
- **Rate limiting:** write endpoint → shared-store per-user cap (ADR-0007 §5; the helper is not yet present in `backend/app/`, so implement the per-user cap behind a small helper here).

## Current State (on `develop`)
- Present from T04–T06: `backend/app/db.py` (SQLModel session), `backend/app/responses.py` (`{data}|{error}`), `backend/app/deps.py` (`require_user`).
- `Post`, `Track`, and `PostSource` already modeled in `backend/app/models.py`.
- No posts router (`backend/app/routers/posts.py`) and no track-upsert helper yet.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/posts.py` | CREATE | `POST` create + `GET` list-by-user |
| `backend/app/tracks.py` | CREATE | `upsert_track(metadata)` |
| `backend/tests/test_posts.py` | CREATE | endpoint tests |

## Testing Checklist
- [ ] `POST /api/posts` without a session → 401
- [ ] valid `POST` creates a `Post` + upserts the `Track`
- [ ] malformed track payload → 400 (Pydantic)
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
Branch off `develop` as `feat/T10-posts-api`; one PR back into `develop` (never `main`). Rate-limit middleware (ADR-0007 §5, Postgres-backed store) is cross-cutting — factor the per-user cap into a `backend/app/` helper so later endpoints reuse it.
