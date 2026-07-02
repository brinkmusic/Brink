---
status: Backlog
priority: High
complexity: Low
category: Fix
tags: [backend, auth, race, review-remediation, second-review]
blocked_by: []
blocks: [073]
parent_ticket: null
owner: Andrea
---

# Fix: `require_user` sign-in race + misconfig masking (T71)

## Rationale
Findings **H2** and **MB1** of the [2026-07-02 code review](../../reviews/2026-07-02-code-review-t00-t08.md).
(1) Two concurrent requests for a brand-new user both miss the user-row select and both INSERT;
the loser hits the `User_supabaseUserId_key` unique violation and 500s. Harmless today with one
authenticated endpoint, near-certain once T10+ fires capture-spotify + feed + profile in parallel
on a fresh login. (2) The bare `except Exception → 401` around token verification masks server
misconfiguration (missing `SUPABASE_URL` raises `ValueError` from `admin()`) as "invalid session"
— indistinguishable from a bad token and invisible in logs; the file-header "ported 1:1" claim is
wrong for this path.

## Summary
Handle the insert race (`IntegrityError` → rollback → re-select), narrow the exception handling so
misconfiguration surfaces as a 500 with a log line instead of a silent 401, and correct the header
comment.

## Source
- Review findings: **H2**, **MB1**
- Spec reqs: **AUTH-2** (server-side session validation)
- ADRs: [ADR-0005](../../../decisions/adr/0005-identity.md) (one account per person; `User` keyed by `supabaseUserId`) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md) (layer 4: the unique constraint is authoritative — the app check just fails friendlier)

## Scope
### In Scope
- `deps.py`: wrap the first-sign-in INSERT in `try/except IntegrityError` → `session.rollback()`
  → re-run the select and return that row.
- `deps.py`: catch the Supabase auth failure narrowly (auth error → 401); let configuration errors
  propagate (or log-and-500) so a misdeployed instance is visible.
- Fix the "ported 1:1"/behavior-identical header comment to describe actual behavior.

### Out of Scope
- Any caching of `getUser()` (per-request round-trip is mandated by CLAUDE.md rule 6; a TTL cache
  would itself be an auth change needing its own ticket + second review).
- Startup-time settings validation (T74, L1).

## Validation & authz (ADR-0007)
- **Integrity:** relies on the existing `User_supabaseUserId_key` unique constraint as the
  authoritative guard; the fix makes the app layer converge on it instead of 500ing.
- **Authorization:** no change to the JWT policy (`getUser()`, no JWT secret).

## Current State (on `develop`)
- `backend/app/deps.py:61-92` select-then-insert with no race handling; `:54-57` blanket
  `except Exception` → 401.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/deps.py` | MODIFY | race handling + narrow exception + comment fix |
| `backend/tests/test_auth.py` | MODIFY | failing tests first (see checklist) |

## Testing Checklist
- [ ] failing test first: simulate the race (session mock raising `IntegrityError` on commit, then
      returning the row on re-select) → request succeeds, no 500
- [ ] auth-service failure (stub **raises**, mirroring real `AuthApiError`) → 401
- [ ] misconfiguration (`admin()` raises `ValueError`) → 500 (not 401) and the error is logged
- [ ] full suite passes (`cd backend && uv run pytest`)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (none; blocks 073 to avoid test_auth.py collisions)
- [x] Scope boundaries defined

## Notes
Branch `fix/T71-require-user-hardening`. **`deps.py` is on the auth/crypto second-review list —
do not self-merge.** Wide blast radius (every authenticated route depends on it): run the full
suite and say so in the PR.
