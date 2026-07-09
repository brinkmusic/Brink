---
status: Completed
priority: Medium
complexity: Low
category: Tech-Debt
tags: [backend, alembic, schema, medallion, autogenerate]
blocked_by: [039]
blocks: []
parent_ticket: 039
owner: Andrea
---

# Tech-Debt: Alembic schema reflection for the medallion schemas (T37)

## Rationale
T39 (ADR-0009) moved `Track`/`Play` into the `silver` schema, `Cluster`/`ModelMetrics`/`ModelArtifact` into `gold`, and the raw landing tables into `bronze`. Alembic's `env.py` was **not** updated to reflect non-default schemas, so the *next* `alembic revision --autogenerate` would not see those schema-qualified tables in the database and would generate a wrong migration (proposing to create/drop them). T39 flagged this as a follow-up because T39's own migration was hand-written and unaffected. This ticket makes autogenerate correct before anyone relies on it again.

## Summary
Turn on `include_schemas` in `env.py` and add the two guards that become necessary once it's on: (1) restrict reflection to the schemas our models actually declare so Supabase-managed schemas (`auth`, `storage`, …) aren't seen, and (2) fix the existing "ignore unmanaged tables" filter to build the schema-qualified key, so our own `silver`/`gold`/`bronze` tables aren't mistaken for unmanaged and dropped.

## Source
- ADRs: [ADR-0009](../../../decisions/adr/0009-medallion-layering.md) (bronze/silver/gold schemas)
- Parent: [T39](../completed/039-analytics-schema-migration.md) — "Follow-up flagged: `env.py` needs `include_schemas=True` before the next `--autogenerate`."

## Scope
### In Scope
- `backend/alembic/env.py`, online migration path only (autogenerate connects to the DB):
  - `include_schemas=True` on `context.configure(...)`.
  - An `include_name` hook that reflects only the schemas our models declare (derived from `SQLModel.metadata`, so a future schema is covered automatically — nothing to keep in sync by hand).
  - Update `include_object` to compare the **schema-qualified** table key (`schema.table`), not the bare name, so schema-qualified model tables are recognized as managed.

### Out of Scope
- Any new migration. This only fixes the tooling so the *next* autogenerate is correct.
- The offline (`--sql`) path — it emits SQL literally and does no metadata↔DB comparison.

## Validation & authz (ADR-0007)
- No request surface. Correctness is verified by running `alembic check` against `brink-dev`: with the models and DB in sync, it must report **no** new operations (in particular, it must not propose dropping `silver`/`gold`/`bronze` or any Supabase-managed table).

## Current State (on `develop`)
- `backend/alembic/env.py`: no `include_schemas`; `include_object` compares the unqualified `name` against `target_metadata.tables` (whose keys for medallion tables are `schema.table`).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/alembic/env.py` | MODIFY | `include_schemas=True` + `include_name` schema allow-list + schema-qualified `include_object` |

## Testing Checklist
- [x] `cd backend && uv run alembic check` against `brink-dev` reports no drift — **"No new upgrade operations detected"** (no spurious create/drop of medallion or Supabase tables)
- [x] `cd backend && uv run pytest` still green — **127 passed** (SQLite path via `schema_translate_map` unaffected)

## Implementation notes (as built)
- `backend/alembic/env.py` online path: added `include_schemas=True` + `include_name=include_name`;
  `include_name` allows only the schemas the models declare (`{table.schema for ...}`, so `None`/
  public + `bronze`/`silver`/`gold`) and rejects Supabase-managed schemas (`auth`, `storage`, …).
- Fixed `include_object` to build the schema-qualified key (`f"{schema}.{name}"`) before the
  "is this table managed?" check — required because `include_schemas` passes unqualified table
  names while `SQLModel.metadata` keys medallion tables as `schema.table`. Without this the fix
  would have flipped the bug from "invisible tables" to "our own schema tables look unmanaged."
- Verified against the live `brink-dev` schema with `alembic check`: models and DB agree, no
  operations proposed. Resolves the follow-up flagged in T39's "as built" notes + CLAUDE.md.

## Notes
- `env.py` runs its migration dispatch on import (it is an Alembic bootstrap script, not an importable module), and the CI test DB is schemaless SQLite — so the change is **not** unit-testable in pytest. Verification is `alembic check` against Postgres, per hard-rule #4's "CI is what actually blocks" (the SQLite suite guards that nothing regressed). This is a stated TDD exception.
- Branch off `develop` as `chore/T37-alembic-schema-reflection`; one PR into `develop`.
