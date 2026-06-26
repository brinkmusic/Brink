---
status: Backlog
priority: Medium
complexity: Medium
category: Chore
tags: [cleanup, docs, prisma, ci, migration]
blocked_by: [007]
blocks: []
parent_ticket: null
owner: Andrea
---

# Chore: Decommission TS backend + sync docs (T08)

## Rationale
Once Render serves production (T07), the TypeScript `api/`, Prisma, and Node backend tooling are
dead weight and a source of confusion. Remove them and bring every doc and backlog ticket in line
with the FastAPI stack ([ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md)).

## Summary
Delete the TS backend (`api/*.ts`, `scripts/dev-api.ts`, `prisma/`) and the Node backend deps;
drop the Node `test` CI job; update `CLAUDE.md` and re-point the backlog API tickets to the
FastAPI patterns.

## Source
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md)
- Reqs: INFRA-2 (tooling/docs consistency)

- Remove the entire legacy TS backend: the `api/` directory (handlers, `_lib/`, `__tests__/`,
  and the jsonblob `state.js`), `scripts/dev-api.ts`, `prisma/`, and root `package.json`
  backend deps (`jest`, `ts-jest`, `supertest`, `@vercel/node`, `tsx`, `prisma`,
  `@prisma/client`, `express`, `@supabase/supabase-js`). Remove the `dev:api` / `prisma:*` scripts.
  (The frontend's `/api/state` mock path must already be retired — that's T60, which must precede
  the T07 cutover; see T60's cutover-sequencing note.)
- `.github/workflows/ci.yml`: delete the Node `test` job (keep `api` Python, `web`, `secrets`).
- `CLAUDE.md`: Layout (`backend/` FastAPI/Python), Commands (uvicorn, `uv run pytest`), the
  Database-migrations section (Alembic — **delete the Prisma `migrate dev` hang workaround**),
  the stack one-liner, and ownership note (api/ → backend/).
- **Verify** no downstream ticket or doc still references the TS stack. The backlog API tickets
  were already re-pointed to the FastAPI pattern in T04's PR (#4); this ticket just confirms that
  and fixes any stragglers.

### Out of Scope
- Frontend code (unchanged throughout). Analytics tickets (already Python).

## Validation & authz (ADR-0007)
- N/A (removal + docs). Confirm no remaining import of the deleted helpers anywhere.

## Current State (on `develop` after T07)
- Render serves production; Vercel rewrites `/api/*` to it. The TS `api/` is no longer used.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `api/`, `scripts/dev-api.ts`, `prisma/` | DELETE | retire TS backend |
| `package.json` (root) | MODIFY | drop backend deps + scripts |
| `.github/workflows/ci.yml` | MODIFY | remove Node `test` job |
| `CLAUDE.md` | MODIFY | layout, commands, migrations, stack |
| `docs/plans/tickets/backlog/01x,05x` | MODIFY | re-point to FastAPI patterns |

## Testing Checklist
- [ ] repo builds/tests with only the Python `api`, `web`, `secrets` CI jobs green
- [ ] no references to `api/_lib/*`, Prisma, or `dev:api` remain in code or docs
- [ ] `CLAUDE.md` commands/layout match the FastAPI reality (manual read-through)
- [ ] re-pointed tickets reference real `backend/app/...` paths

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T07 → blocked_by 007)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `chore/T08-decommission-ts-backend`; one PR into `develop`.
Do this only after T07's Render cutover is verified — it's the point of no return for the TS path.
Re-pointing many tickets can also be done incrementally as each is picked up; at minimum fix the
shared helper/"Current State" references here.
