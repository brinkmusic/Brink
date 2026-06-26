---
status: Backlog
priority: High
complexity: Low
category: Tech-Debt
tags: [analytics, python, uv, infra]
blocked_by: []
blocks: [031, 032]
parent_ticket: null
---

# Feature: Python analytics scaffold + DB access (T30)

## Rationale
The whole analytics layer (the graded ML centerpiece) lives in a Python package that doesn't exist yet. This ticket creates the `uv`-managed project and the database access helper everything else builds on. It also proves the architectural constraint from ADR-0003: the pipeline reads Postgres directly over the wire protocol (the reason D1/SQLite was rejected — see ADR-0002, retained under ADR-0010; Supabase Postgres is unchanged).

## Summary
`uv init` an `analytics/` package with scikit-learn/pandas/SQLAlchemy/psycopg, a `db.py` that connects to Supabase via `DATABASE_URL`, and a passing `pytest` that reads a table count.

## Source
- Spec reqs: **AN-8** (partial), **INFRA-4** (partial)
- ADRs: [ADR-0003](../../../decisions/adr/0003-analytics-runtime.md) (Python batch reads Postgres over the wire) · [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md)

## Scope
### In Scope
- `uv init analytics`; `uv add scikit-learn pandas sqlalchemy "psycopg[binary]"`; `uv add --dev pytest`; commit `uv.lock`.
- `analytics/db.py` — engine/connection helpers reading `DATABASE_URL` (the Supabase direct connection).
- `analytics/tests/test_db.py` — connects and reads a `Track` count.

### Out of Scope
- Any model/feature/aggregation logic (later analytics tickets).
- The GitHub Actions pipeline workflow (T38).

## Validation & authz (ADR-0007)
- Not a request-facing endpoint; the relevant integrity guarantee is that the pipeline reads/writes the **same Postgres** the API uses (single source of truth), via `DATABASE_URL` only — no separate datastore.

## Current State (on `develop`)
- No `analytics/` directory exists.
- `DATABASE_URL`/`DIRECT_URL` already configured for Supabase (`brink-dev`) in root `.env`.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `analytics/pyproject.toml` | CREATE | `uv` project + deps |
| `analytics/uv.lock` | CREATE | pinned lockfile |
| `analytics/db.py` | CREATE | DB engine/read/write helpers |
| `analytics/tests/test_db.py` | CREATE | connection + read test |

## Testing Checklist
- [ ] `uv run pytest` connects to the DB and reads a `Track` count
- [ ] `db.py` reads `DATABASE_URL` from env (no hardcoded creds)
- [ ] `uv.lock` committed; `uv sync` reproduces the env

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T01 done)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T30-analytics-scaffold`; one PR back into `develop` (never `main`). All Python runs via `uv run ...`; deps pinned in `uv.lock`. Owner: Jonah (analytics).
