# ADR-0012: API response shape — per-endpoint camelCase DTOs, never raw table models

**Status:** Accepted
**Date:** 2026-07-03

## Context

Our database columns are camelCase (`createdAt`, `trackId`, `albumArtUrl`) because the schema was
originally created by Prisma, but our Python model attributes are snake_case (`created_at`,
`track_id`) — see the header of `backend/app/models.py` and the naming note carried since T06. The
React/TypeScript frontend expects camelCase JSON.

T06 deferred the question of how API responses get their casing. T10 is the first endpoint that
returns real domain objects (posts, tracks), so the question can't be deferred further — and
whatever T10 does becomes the pattern every later social endpoint (reactions, comments, feed,
profile) copies. The [2026-07-02 code review](../plans/reviews/2026-07-02-code-review-t00-t08.md)
(§5–6) flagged this as a precedent to set deliberately.

## Decision

Endpoints return **explicit Pydantic response models** ("DTOs" — data transfer objects) whose fields
are serialized in **camelCase**, defined in one shared place (`backend/app/schemas.py`). Endpoints
**never** return SQLModel table instances (`Post`, `Track`, `User`, …) raw.

- A shared `CamelModel` base applies a snake_case→camelCase alias generator, so DTO fields are
  written in idiomatic Python snake_case but serialize as camelCase JSON.
- Each endpoint maps its table rows into the relevant DTO before returning.
- Request bodies/queries are likewise typed Pydantic models with required, non-Optional fields where
  the field is required (envelope-shaped `400`s come from T70's global handler). Do not copy
  capture-spotify's all-Optional legacy-parity shape into new endpoints.

## Why not return table models directly

- **Casing leak.** Raw SQLModel serialization emits snake_case JSON the frontend doesn't expect.
- **Column leak / security.** A table model exposes *every* column. Returning `User` or any model
  that joins to secrets risks leaking fields that must never reach the browser — most critically,
  `SpotifyToken` (encrypted access/refresh tokens) must never be serializable out of an endpoint. An
  explicit DTO is an allow-list: only listed fields go out.
- **Decoupling.** The wire shape is chosen per endpoint, independent of how the table happens to be
  structured, so a schema change doesn't silently change the API.

## Consequences

- A little boilerplate per endpoint (define a DTO, map rows to it). Intentional — it's the allow-list
  that keeps responses safe and stable.
- One shared `schemas.py` + `CamelModel` base; every social endpoint from T11 on reuses it.
- If the underlying columns are ever renamed (the deferred snake_case DB migration), the DTOs
  insulate the API — clients see no change.
