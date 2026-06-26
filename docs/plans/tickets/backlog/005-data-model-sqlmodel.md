---
status: Backlog
priority: High
complexity: High
category: Chore
tags: [infra, sqlmodel, alembic, database, migration]
blocked_by: [004]
blocks: [006]
parent_ticket: null
owner: Andrea
---

# Chore: SQLModel data model + Alembic baseline (T05)

## Rationale
The FastAPI backend needs to talk to the existing Supabase Postgres. The 14-table schema already
exists (built by Prisma in T01); this ticket maps it 1:1 in SQLModel and stands up Alembic for
future schema changes — replacing Prisma as the persistence layer per
[ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md).

## Summary
Translate the 14 models in `prisma/schema.prisma` to SQLModel in `backend/app/models.py`, add a
SQLModel engine/session (`backend/app/db.py`), baseline Alembic against the live schema, and
restore the `db` reachability field on `GET /api/health`.

## Source
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md)
- Reqs: INFRA-1, INFRA-2, BE-1 (re-implemented on the new stack)

## Scope
### In Scope
- `backend/app/models.py` — all 14 tables as SQLModel: `User`, `SpotifyToken`, `Track`, `Play`,
  `Post`, `Reaction`, `Comment`, `Follow`, `ArtistPost`, `UserStats`, `TasteVector`, `Cluster`,
  `Compatibility`, `ModelMetrics`. Preserve enums (`PostSource`, `ReactionType`), unique
  constraints (e.g. `@@unique([postId, userId, type])`), indexes, and `onDelete: Cascade`.
- `backend/app/db.py` — engine + session factory reading `DATABASE_URL` via
  `backend/app/config.py` (pydantic-settings, loads root `.env`).
- IDs: a `cuid2`-based default for `String @default(cuid())` columns (consistent with existing
  rows). Flag UUID as the alternative in the PR.
- Alembic baseline: generate the initial revision, then `alembic stamp head` against the live DB
  (tables already exist — **do not recreate**).
- Restore `GET /api/health` `db` field via a `SELECT 1` ping.

### Out of Scope
- Any new tables or schema changes (none — this mirrors the current schema).
- Auth/crypto/endpoints (T06); deploy (T07).

## Validation & authz (ADR-0007)
- N/A for authz (no user-facing endpoint beyond health). Integrity: constraints/indexes must
  match the live schema exactly so the app-level guarantees from the API tickets still hold.

## Current State (on `develop` after T04)
- `backend/` FastAPI app with `app/responses.py` and `routers/health.py` (liveness only).
- `prisma/schema.prisma` is the authoritative current schema to translate (still present; removed
  in T08).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/models.py` | CREATE | 14 SQLModel tables |
| `backend/app/db.py` | CREATE | engine/session |
| `backend/app/config.py` | CREATE | settings (root `.env`) |
| `backend/alembic/**`, `backend/alembic.ini` | CREATE | migration tooling + baseline |
| `backend/app/routers/health.py` | MODIFY | restore `db` reachability |
| `backend/tests/test_models.py` | CREATE | model/constraint sanity |

## Testing Checklist
- [ ] models import; metadata matches the 14 tables, enums, and unique constraints
- [ ] `alembic upgrade head` is a no-op against the baselined live DB (stamped, not recreated)
- [ ] `GET /api/health` returns `{ data: { ok: true, db: true } }` when the DB is reachable
- [ ] health returns 500 `{ error }` when the DB is unreachable (mirrors old `health.ts`)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T04 → blocked_by 004)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `chore/T05-data-model-sqlmodel`; one PR into `develop`.
Changes to the shared schema/persistence layer have wide blast radius — call out in the PR.
