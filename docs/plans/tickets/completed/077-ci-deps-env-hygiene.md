---
status: Completed
priority: Medium
complexity: Low
category: Chore
tags: [infra, ci, dependabot, env, review-remediation]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Chore: CI / dependency / env-file hygiene (T77)

## Rationale
Findings **MI1–MI4**, **L7**, **L8**, and the env-example half of **L10** from the
[2026-07-02 code review](../../reviews/2026-07-02-code-review-t00-t08.md). Individually small,
collectively they weaken the guardrails: `.env.example` advertises a `SUPABASE_JWT_SECRET` nothing
consumes (contradicting hard rule 6 — and inviting someone to paste a real secret into a var
nothing reads); Dependabot has no ecosystem for the backend's Python deps (including
`cryptography`); the pre-commit secret guard is never installed on the documented onboarding path
(`cd apps/web && npm install` doesn't trigger the root-only `prepare`); CI can test on a Python
version prod never runs (Render pins 3.12, CI is unpinned) with an unfrozen `uv sync` that
silently re-locks on drift; gitleaks is curl-pinned to an early-2024 version invisible to
Dependabot.

## Summary
One infra PR: clean both `.env.example`s, add a `uv` Dependabot block, make hook install work on
the documented path, pin Python, lock CI installs, and lift the gitleaks version to a maintained
variable.

## Source
- Review findings: **MI1**, **MI2**, **MI3**, **MI4**, **L7**, **L8**, **L10** (env part)
- Spec reqs: **INFRA-2** (tooling consistency), **DATA-2** (secret hygiene)
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md)

## Scope
### In Scope
- `.env.example`: delete `SUPABASE_JWT_SECRET`; move the `VITE_*` lines out (they live only in
  `apps/web/.env.example` — one home per var).
- `.github/dependabot.yml`: `package-ecosystem: uv` block for `/backend` (monthly, grouped,
  target `develop`, no major bumps — mirror the npm block).
- Hooks: add `"prepare": "git config core.hooksPath .githooks || true"` to
  `apps/web/package.json` so the documented onboarding path installs the secret guard; keep the
  root script.
- `backend/.python-version` containing `3.12` (uv and setup-uv both respect it → CI = Render).
- `ci.yml`: `uv sync --locked`; hoist the gitleaks version to a `GITLEAKS_VERSION` env at the top
  of the workflow and bump it to a current release.

### Out of Scope
- Adding a backend linter (ruff) or putting eslint in CI — real gap (**L9**) but a tooling
  decision for the team, not a hygiene fix; decide separately.
- History-mode gitleaks scan (tree-only is a known, accepted tradeoff — noted here for the record).
- Any change to what secrets exist or where they live.

## Validation & authz (ADR-0007)
N/A (infra). The hook fix and JWT-secret removal directly serve hard rule 3 (never commit
secrets).

## Current State (on `develop`)
- As per findings; verified clean already: ports/URLs consistent across configs, render.yaml env
  list matches T07, pre-commit regexes correct, `.gitleaks.toml` allowlists only the test vector.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `.env.example` | MODIFY | drop dead vars |
| `.github/dependabot.yml` | MODIFY | uv ecosystem for /backend |
| `apps/web/package.json` | MODIFY | prepare hook (flag to Sebastian in review) |
| `backend/.python-version` | CREATE | pin 3.12 |
| `.github/workflows/ci.yml` | MODIFY | --locked + gitleaks version variable |

## Testing Checklist
- [ ] fresh clone + `cd apps/web && npm install` → `git config core.hooksPath` returns `.githooks`
- [ ] CI green on the PR; backend job logs show Python 3.12 and a locked sync
- [ ] deliberately drifting `pyproject.toml` locally makes `uv sync --locked` fail (spot check)
- [ ] gitleaks step still passes and prints the new version

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (none)
- [x] Scope boundaries defined

## Notes
Branch `chore/T77-ci-deps-env-hygiene`. Touches `apps/web/package.json` (one script) — Sebastian
reviews that hunk.
