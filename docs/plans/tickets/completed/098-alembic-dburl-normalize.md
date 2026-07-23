---
status: Completed
priority: Medium
complexity: Small
category: Fix
tags: [backend, db, migrations, tooling]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Fix: normalize the `alembic -x dburl=...` override (T98)

## Rationale
Running the T96 production migration with a URL pasted straight from the Render dashboard
(`uv run alembic -x dburl="postgresql://..." upgrade head`) crashed with
`No module named psycopg2`. The `-x dburl` override in `backend/alembic/env.py` returned the
raw URL, skipping the `normalize_url()` step the settings path gets — so SQLAlchemy routed a
plain `postgresql://` scheme to its default psycopg2 driver, which Brink doesn't install
(we use psycopg v3).

## Summary
Pass the override through the same `normalize_url()` as the settings path (driver scheme
rewrite + `pgbouncer=true` strip), so a raw dashboard URL works verbatim in one-off
migration commands.

## Source
- Spec reqs: **BE-1** (Postgres + schema via SQLModel/Alembic)
- Docs: `CLAUDE.md` § Database migrations

## Scope
### In Scope
- Normalize the `-x dburl` override in `env.py`.
- Regression coverage: `normalize_url` scheme rewrite + a source-level assert on the
  override path (env.py runs migrations at import, so it can't be imported in a test —
  same technique as the page tests' script-source asserts).

### Out of Scope
- Any change to migration content, settings loading, or the normalizer itself.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/alembic/env.py` | MODIFY | normalize the override URL |
| `backend/tests/test_alembic_env.py` | CREATE | regression coverage |
| `docs/plans/tickets/README.md` | MODIFY | record completion |

## Testing Checklist
- [x] `normalize_url` rewrites `postgresql://` to `postgresql+psycopg://`
- [x] the override path calls `normalize_url(override)`
- [x] full backend suite passes

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Outcome
T98 makes one-off migrations against another database (the exact production-release step
documented in CLAUDE.md's Watch-outs) work with a URL pasted as-is from a dashboard.
Validation: full backend suite **268 passed** (2 new tests).
