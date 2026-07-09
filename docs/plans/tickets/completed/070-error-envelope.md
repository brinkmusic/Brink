---
status: Completed
priority: High
complexity: Low
category: Fix
tags: [backend, api, errors, review-remediation]
blocked_by: []
blocks: [010, 073]
parent_ticket: null
owner: Andrea
---

# Fix: Envelope-complete error handling + health leak (T70)

## Rationale
Findings **H1** and **MB4** of the [2026-07-02 code review](../../reviews/2026-07-02-code-review-t00-t08.md).
Only `AuthError` currently returns the `{data}/{error}` envelope: Pydantic validation failures
escape as raw 422 `{"detail":[...]}` and unknown paths as 404 `{"detail":"Not Found"}`, violating
the contract ADR-0010 says was preserved and ADR-0007's schema-failure-as-400 rule. Every T10+
endpoint with required fields will hit this constantly — two independent review streams ranked it
the top pre-T10 blocker, so this ticket **blocks T010**. Also: `/api/health` interpolates the raw
driver exception into a public response, which can leak host/user/db details from the DSN.

## Summary
Register global exception handlers in `main.py` so *every* error response uses `fail()`;
return a constant message from `/api/health` on DB failure and log the real exception server-side.

## Source
- Review findings: **H1**, **MB4**
- Spec reqs: **BE-1** (API foundation), **INFRA-2** (consistency)
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md) (envelope contract) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md) (layer 1: schema failures → 400 via the envelope)

## Scope
### In Scope
- `RequestValidationError` handler → `fail(<message>, 400)`.
- `StarletteHTTPException` handler → `fail(exc.detail, exc.status_code)` (covers 404/405).
- Optional catch-all `Exception` handler → `fail("internal error", 500)` (decide in PR; state the choice).
- `health.py`: log the exception, return constant `fail("db unreachable", 500)`.
- Tests asserting the exact envelope shape for 400/404/500 paths; tighten `test_health.py:35`'s
  weak `"error" in json` assert to the exact message.

### Out of Scope
- Any new endpoints (T010+). Rate limiting (scoped in T010). Router prefix refactor — but **note
  for T010**: new routers should use `APIRouter(prefix="/api/<resource>", tags=[...])` instead of
  hard-coded literal paths.

## Validation & authz (ADR-0007)
This ticket *implements* the layer-1 failure shape that all future endpoint tickets rely on.
No new authz surface.

## Current State (on `develop`)
- `backend/app/main.py` registers only the `AuthError` handler.
- `backend/app/responses.py` provides `ok()`/`fail()` and documents the envelope as universal —
  the docs are right, the wiring is incomplete.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/main.py` | MODIFY | register the exception handlers |
| `backend/app/routers/health.py` | MODIFY | constant error message + server-side log |
| `backend/tests/test_main.py` | CREATE | envelope-shape tests for 400/404/(500) |
| `backend/tests/test_health.py` | MODIFY | exact-message assert |

## Testing Checklist
- [ ] failing test first: malformed JSON body → 400 `{"error": ...}` (currently 422 `{"detail"}`)
- [ ] wrong-typed field → 400 `{"error": ...}`
- [ ] unknown path → 404 `{"error": ...}`
- [ ] health with DB down → 500 `{"error": "db unreachable"}` exactly; exception visible in logs
- [ ] existing 18 tests still pass (`cd backend && uv run pytest`)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (none; blocks 010, 073)
- [x] Scope boundaries defined

## Notes
Branch `fix/T70-error-envelope`; one PR into `develop`. `main.py` is shared code — call out the
blast radius in the PR and run the full suite.
