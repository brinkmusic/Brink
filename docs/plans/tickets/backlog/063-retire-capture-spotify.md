---
status: Backlog
priority: Low
complexity: Low
category: Chore
tags: [backend, auth, cleanup, review-remediation]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Chore: Retire the legacy `POST /api/auth/capture-spotify` endpoint (T63)

## Rationale
Finding of the [2026-07-15 coherence review](../../reviews/2026-07-15-docs-code-coherence.md)
and the [auth investigation](../../reviews/2026-07-15-auth-email-signup-investigation.md): this
endpoint existed so the React SPA's browser could forward Spotify tokens. The SPA was retired in
T60 and token capture moved server-side into `/auth/callback` (T09), so nothing calls it — it's
dead, login-gated attack surface on the highest-risk (token-handling) path. T75/T76, which
hardened the browser side of this flow, were obsoleted by T60.

## Summary
Delete the endpoint, its request model, and its tests; keep the server-side capture path
untouched. Verify with a grep that no template/JS/docs reference remains (outside historical
tickets/ADRs).

## Source
- Reviews above; hard-rule #6 area (auth) — small diff, but flag it in the PR.

## Scope
### In Scope
- Remove the route + schema from `routers/auth.py`, its tests, and the `main.py` mount if
  separate. Update the file's header comment (T79 already points it at this ticket).
- Docs sync: CLAUDE.md status line mention.

### Out of Scope
- Any change to `/auth/login`, `/auth/callback`, `/auth/logout`, session or crypto code.

## Validation & authz (ADR-0007)
Removal only; shrinks the auth surface.

## Current State (on `develop`)
- Endpoint mounted and functional; zero callers in templates/static JS.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/auth.py` | MODIFY | delete the legacy endpoint |
| `backend/tests/test_auth.py` (capture tests) | MODIFY | remove/retarget |

## Testing Checklist
- [ ] full suite green after removal
- [ ] `git grep capture-spotify` hits only historical docs
- [ ] Spotify login e2e still works (manual, one login on dev)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (none)
- [x] Scope boundaries defined

## Notes
Branch `chore/T63-retire-capture-spotify`. Auth-area change: second review encouraged, not
required.
