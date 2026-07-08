---
status: Backlog
priority: Medium
complexity: Low
category: CI
tags: [ci, docs, governance, developer-experience]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# CI: Enforce "keep docs in sync in the same PR" (T91)

## Rationale
"Keep docs in sync in the same PR — stale docs are a bug" is a Brink hard rule, but until now it
lived only in `CLAUDE.md` and the PR template — both *soft*: they depend on the author (human or
AI agent) choosing to comply, which isn't reliable and doesn't apply to teammates who aren't using
Claude at all. The [T78 doc-drift sweep](../completed/078-doc-drift-sweep.md) and the review of
PR #60 (ADR-0013 landed with `CLAUDE.md` still describing the retired React SPA) both show the same
gap: intent without enforcement drifts. Reliability comes from a **prompt-independent gate in CI**
that blocks the merge regardless of who or what wrote the change.

## Summary
Add a CI job that fails a PR which changes substantive source code but touches no documentation,
plus the team-shared Claude hook that keeps the norm visible. Layered so each piece does what it's
good at: teach (CLAUDE.md/skills) → surface (Claude hook) → **gate (CI)**.

## Source
- Project norms: `CLAUDE.md` → "Keep docs in sync in the same PR", "ADRs are append-only".
- Spec reqs: **INFRA-2** (docs consistency).
- Prior art: [T78](../completed/078-doc-drift-sweep.md) (one-off manual sweep of the same drift),
  [T90](090-session-warmup-skill.md) (the get-me-started skill this hook points at).

## Scope
### In Scope
- `.github/workflows/docs-sync.yml` — the gate. On every PR, diff the changed files; if
  substantive code (`backend/app/`, `apps/web/src/`, `analytics/`, minus tests/lockfiles/assets)
  changed but no doc (`docs/**`, `CLAUDE.md`, any `README.md`) did, fail with a message pointing
  at the rule. Escape hatch: a `no-docs` label skips the job for genuine no-doc changes.
- `.claude/settings.json` (committed, team-shared) — a `SessionStart` hook that surfaces the
  doc-sync norm and points at the get-me-started skill, so every teammate's Claude agent gets it
  automatically with no per-machine setup.

### Out of Scope
- Judging doc *quality* or *correctness* — the gate only checks that *some* doc moved with the
  code. Review + the PR template cover the rest. Trying to semantically verify docs is a rabbit
  hole, deliberately avoided.
- A local pre-commit doc check — rejected: docs often land in a later commit of the same PR, so a
  per-commit check is noisy. PR-level (CI) is the right granularity.
- The PR template already has a doc-sync checklist item; no change needed there.

## Acceptance
- A PR that edits `backend/app/**` with no doc change fails the `docs-sync` check with a clear
  message; adding the `no-docs` label (or a doc change) makes it pass.
- Test-only, lockfile-only, and asset-only PRs do **not** trip the check.
- Dependabot PRs (manifests/lockfiles) do **not** trip the check.
- The committed `SessionStart` hook prints the norm at session start on a teammate's machine.

## Notes
- **Follow-up (needs repo admin):** to make this *block* merges, add `docs-sync` to the branch
  protection required checks on `develop`/`main`. Until then it still shows a red X on the PR —
  a strong signal, but not a hard block. Flag to whoever owns the org settings.
- The `no-docs` label must exist in the repo; create it once with
  `gh label create no-docs --description "PR change genuinely needs no docs (refactor/test-only)"`.
