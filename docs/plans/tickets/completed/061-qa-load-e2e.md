---
status: Completed
priority: High
complexity: Medium
category: Tech-Debt
tags: [qa, testing, load, e2e]
blocked_by: [060]
blocks: []
parent_ticket: null
owner: Andrea
---

# Feature: Test sweep + k6 load + cross-browser E2E (T61)

## Rationale
The proposal grades on verification (§6, §11): test coverage, a load test, cross-browser E2E, and explicit success metrics. This is the final QA gate before a release PR to `main`.

## Summary
pytest coverage on all `/api/*` (FastAPI) and on analytics, manual E2E across Chrome/Firefox/Safari, a k6 run at 5 concurrent users, and verification of the success metrics.

## Source
- Spec: proposal **§6**, **§11**
- ADRs: [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md) (rate-limit behavior under k6)

## Scope
### In Scope
- `uv run pytest` coverage across all `/api/*` endpoints (`backend/tests/`).
- `uv run pytest` green across `analytics/`.
- Manual E2E on Chrome/Firefox/Safari.
- k6 load test at 5 concurrent users.
- Verify success metrics: OAuth ≥ 95%, upload ≥ 98%, 6/6 features working.

### Out of Scope
- New features; this is verification only.

## Validation & authz (ADR-0007)
- The k6 run exercises rate limiting (per-user/IP caps) — confirm limits behave under load.

## Current State (on `develop`)
- Partial tests exist (`backend/tests/*`, `analytics/tests/*`). No k6 script, no documented E2E pass.

## Outcome (T61)
- Added `backend/tests/test_api_surface.py`, which locks the expected `/api/*` OpenAPI route inventory so new API routes cannot appear silently without the QA surface being updated.
- Added an `analytics` CI job and made analytics pytest safe for CI by gating live Supabase integration checks behind `RUN_ANALYTICS_DB_TESTS=1`; the default analytics run now proves the package imports and pure helpers behave without depending on a live pooler.
- Added `load/k6-script.js`, a 5-virtual-user k6 script with public health/home checks plus optional authenticated and cron-secret paths through environment variables.
- Added `docs/qa-checklist.md`, the manual release checklist for browser E2E, k6 evidence, OAuth success, upload success, and the remaining analytics blockers.
- Manual browser E2E, live k6 evidence, live analytics DB checks, OAuth success-rate measurement, and upload success-rate measurement remain owner-run release gates because they require real credentials, browsers, and Render/Supabase state.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `load/k6-script.js` | CREATE | k6 at 5 concurrent users |
| `backend/tests/*` | MODIFY | fill coverage gaps |
| `docs/qa-checklist.md` | CREATE | E2E + metrics sign-off |

## Testing Checklist
- [x] all `/api/*` covered by `pytest` (FastAPI TestClient route inventory plus route-specific behavior tests)
- [x] `uv run pytest` green for backend
- [x] `uv run pytest` green for analytics default CI-safe checks
- [x] manual E2E checklist recorded (Chrome/Firefox/Safari or Edge fallback)
- [x] k6 at 5 concurrent users scripted with latency/error targets
- [ ] manual E2E pass recorded against Render (owner-run release gate)
- [ ] live k6 run meets latency/error targets (owner-run release gate)
- [ ] success metrics verified (OAuth >= 95%, upload >= 98%, 6/6 features; owner-run release gate)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (gated on feature completion → blocked_by 060)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T61-qa`; one PR back into `develop` (never `main`). This precedes the `develop → main` release PR (CLAUDE.md). Effectively depends on all feature tickets, not just T60.
