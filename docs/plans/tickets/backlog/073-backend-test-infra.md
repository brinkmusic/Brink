---
status: Backlog
priority: Medium
complexity: Low
category: Test
tags: [backend, tests, fixtures, review-remediation]
blocked_by: [070, 071]
blocks: []
parent_ticket: null
owner: Andrea
---

# Test: Shared test fixtures + missed branches (T73)

## Rationale
Findings **MB5** and **L4** of the [2026-07-02 code review](../../reviews/2026-07-02-code-review-t00-t08.md).
There is no `conftest.py`: the dependency-override + `TestClient` boilerplate is copy-pasted three
times in two different styles across a two-file suite. Coverage gaps with teeth: the token
upsert's **update** branch (the path every login after the first takes) is never tested,
`expires_at`'s naive-UTC parity is never asserted, and `require_user`'s display-name fallback
chain is untested. T10–T14 will need "authenticated client" in nearly every test — this is the
template they'll copy.

## Summary
Introduce `backend/tests/conftest.py` (shared `client` fixture + `as_user()` override helper +
the existing auto-clear teardown), migrate both test files onto it, and add the missed-branch
tests.

## Source
- Review findings: **MB5**, **L4**
- Spec reqs: **INFRA-2** (CI/testing consistency)
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md)

## Scope
### In Scope
- `conftest.py`: `client` fixture, `as_user(user)` helper installing/clearing
  `dependency_overrides`, teardown that always clears (keep the existing autouse pattern).
- Migrate `test_auth.py` + `test_health.py` (+ `test_main.py` from T70) to the fixtures.
- New tests: upsert **update** branch (existing `SpotifyToken` → fields overwritten, `session.add`
  NOT called, commit called, `expires_at.tzinfo is None` and ~1h ahead); display-name fallback
  chain (`name` → email prefix → `"Listener"`, empty slug → `user-XXXXXX`); malformed
  `Authorization: Token abc` header → 401.
- Note in `conftest.py`'s header for T10 authors: upsert-style logic with DB-enforced invariants
  (e.g. the reaction unique constraint) needs a real-session fixture (in-memory SQLite via
  SQLModel), not MagicMock — the mock style is exactly what missed the update branch.

### Out of Scope
- The race/misconfig tests themselves (added in T71 — this ticket only refactors them onto the
  fixtures). Building the SQLite fixture (do it in T010 where it's first needed).

## Validation & authz (ADR-0007)
Test-only; no production code changes.

## Current State (on `develop`)
- `test_auth.py` hand-installs overrides + fresh `TestClient` three times; `test_health.py` uses
  a module-level client — two conventions, no shared fixtures.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/tests/conftest.py` | CREATE | shared fixtures + T10 guidance header |
| `backend/tests/test_auth.py` | MODIFY | use fixtures; add missed-branch tests |
| `backend/tests/test_health.py` | MODIFY | use fixtures |

## Testing Checklist
- [ ] failing tests first for the upsert update branch and fallback chain
- [ ] no test installs overrides by hand anymore; overrides provably cleared between tests
- [ ] full suite passes (`cd backend && uv run pytest`)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (070, 071 — same-file collisions otherwise)
- [x] Scope boundaries defined

## Notes
Branch `test/T73-backend-test-infra`. Blocked by 070/071 purely to avoid rebase pain in
`test_auth.py`/`test_health.py`, not by logic.
