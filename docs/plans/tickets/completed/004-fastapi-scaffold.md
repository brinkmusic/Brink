---
status: Completed
priority: High
complexity: Low
category: Chore
tags: [infra, fastapi, python, ci, migration]
blocked_by: []
blocks: [005]
parent_ticket: null
owner: Andrea
---

# Chore: FastAPI backend scaffold + ADR-0010 (T04)

## Summary
First ticket of the backend migration from TypeScript/Vercel to **FastAPI/Python on Render**
([ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md)). Adds the `backend/` uv
project, a FastAPI app with `GET /api/health` (liveness), the `{data}`/`{error}` envelope
(`backend/app/responses.py`, mirroring `api/_lib/respond.ts`), and a Python CI job.

## Source
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md) (supersedes
  [ADR-0002](../../../decisions/adr/0002-api-and-persistence.md))
- Reqs: INFRA-1, INFRA-2 (re-implemented on the new stack)

## Outcome
Completed ✅ (PR #4). `uv run pytest` green; `uvicorn app.main:app` serves
`GET /api/health` → `200 {"data":{"ok":true}}`. CI `api` job (uv + pytest) passes alongside
the existing Node `test`, `web`, `secrets` jobs. Purely additive — the TS `api/` still serves
the live app until the T07 cutover.

## Notes
The health `db` reachability field is intentionally deferred to T05 (needs the SQLModel engine).
The Node `test` CI job and the TS `api/` are removed in T08.
