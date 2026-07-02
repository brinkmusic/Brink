---
status: Backlog
priority: Low
complexity: Low
category: Chore
tags: [backend, comments, config, review-remediation]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Chore: Backend comment accuracy + config fail-fast + model helper (T74)

## Rationale
Findings **MB6**, **MB7**, **L1**, **L5**, **L6** of the [2026-07-02 code review](../../reviews/2026-07-02-code-review-t00-t08.md).
This repo's comment standard makes a *wrong* comment a bug: `models.py` says camelCase columns
stay because "the old code still reads it" (deleted in T08 — the real reason is live data + the
deferred rename), and `routers/auth.py` cites `api/auth/capture-spotify.ts` without noting it was
removed. `config.py` asserts settings are "all required in a real run" but never enforces it, so
a misdeployed Render instance boots green (health only checks the DB) and fails per-request.
Plus two small consistency items for the T10 template.

## Summary
Fix the stale comments, fail fast at startup on missing required settings, add a `_created_at()`
column helper, and document that capture-spotify's all-Optional body pattern is a legacy-parity
exception new endpoints must not copy.

## Source
- Review findings: **MB6**, **MB7**, **L1**, **L5**, **L6**
- Spec reqs: **INFRA-2**
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md) (strict schemas are layer 1 — the parity exception needs labeling)

## Scope
### In Scope
- `models.py:14-15`: reword the header (existing data created under these names; rename
  deliberately deferred post-T08, still open — see the T08 notes).
- `models.py`: `_created_at()` helper next to `_pk_cuid()`/`_fk()`; use it in the 5 models that
  hand-repeat the `createdAt` definition (no schema change — `alembic check` must stay clean).
- `config.py` (or app startup in `main.py`): fail fast when `supabase_url`,
  `supabase_service_role_key`, or `token_enc_key` are missing outside tests; state the
  test-environment escape hatch explicitly.
- `routers/auth.py:6`: "…ported from the old `api/auth/capture-spotify.ts` (removed in T08; see
  ADR-0010)". Add a note above `CaptureBody` that the all-Optional pattern exists only for legacy
  400-message parity — T10+ bodies declare required, typed fields (per ADR-0007 layer 1 + T70's
  handlers).

### Out of Scope
- The actual DB column rename (still deferred). Any behavior change to the endpoint itself.

## Validation & authz (ADR-0007)
No new surface. The fail-fast makes layer-adjacent misconfiguration visible at deploy time.

## Current State (on `develop`)
- All four files as described in the review findings; `createdAt` repeated at `models.py:154`,
  `248`, `281`, `300`, `320`.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/models.py` | MODIFY | comment fix + `_created_at()` helper |
| `backend/app/config.py` / `main.py` | MODIFY | startup fail-fast |
| `backend/app/routers/auth.py` | MODIFY | comment fixes |
| `backend/tests/` | MODIFY | fail-fast test (missing setting → startup error) |

## Testing Checklist
- [ ] failing test first: app startup with `token_enc_key` unset (non-test env) raises clearly
- [ ] `cd backend && uv run alembic check` reports no drift after the helper refactor
- [ ] full suite passes

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (none; touches auth.py comments only — coordinate if T71 in flight)
- [x] Scope boundaries defined

## Notes
Branch `chore/T74-backend-polish`. `models.py` is shared code — run the full suite and note the
blast radius in the PR.
