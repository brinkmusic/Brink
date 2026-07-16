---
status: Backlog
priority: Medium
complexity: Low
category: Docs
tags: [docs, drift, review-remediation, tickets]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Docs: 2026-07-15 coherence sweep — reviews landed, easy drift fixed, gaps ticketed (T79)

## Rationale
Owner-requested follow-up to the 2026-07-02 review, same idea: don't drag errors along. Four
parallel investigations ran on 2026-07-15 — docs↔code coherence, email-auth feasibility,
frontend-enablement gaps, and a Supabase schema audit — and this ticket lands their reports,
fixes every EASY (docs-only / comment-only / config-text) finding in one PR, and files proper
backlog tickets for everything bigger.

## Summary
One chore PR carrying: the four review reports (`docs/plans/reviews/2026-07-15-*.md`); fixes for
the stale-doc findings (CLAUDE.md CI/branch-check/close-session claims, close-session skill
description, `render.yaml` branch + missing `CRON_SECRET`, `responses.py`/`auth.py` stale React
comments, ADR-0003 language note, requirements.md "on-read TS" wording, `home.html` copy that
contradicted ADR-0014, tracked `apps/web/tsconfig.tsbuildinfo` leftover); T75/T76 marked
Obsolete (their target SPA files were deleted in T60); and new tickets T03 (rewritten), T15,
T16, T46, T47, T53, T54, T63.

## Source
- Reviews: [coherence](../../reviews/2026-07-15-docs-code-coherence.md) ·
  [auth](../../reviews/2026-07-15-auth-email-signup-investigation.md) ·
  [enablement gaps](../../reviews/2026-07-15-frontend-enablement-gaps.md) ·
  [schema audit](../../reviews/2026-07-15-supabase-schema-audit.md)
- Spec reqs: **INFRA-2** (docs consistency)

## Scope
### In Scope
Everything in the Summary — docs, comments, config text, ticket bookkeeping. The only
code-adjacent edits are comment headers (`responses.py`, `auth.py`), landing-page copy
(`home.html`), and `render.yaml` (branch now matches the live dashboard setting; `CRON_SECRET`
added to the env-var record).

### Out of Scope
- All behavior changes — those are the new tickets (T03/T15/T16/T46/T47/T53/T54/T63).
- Dropping `public._prisma_migrations` (schema audit verdict: harmless, optional forever).

## Validation & authz (ADR-0007)
N/A — no endpoint behavior changes.

## Current State (on `develop`)
Each finding verified against the working tree on 2026-07-15 before editing (T30/T31 landing
mid-review voided the "analytics/ doesn't exist" finding — dropped).

## Files to Create/Modify
See the PR diff — reports (4 CREATE), tickets (8 CREATE/rewrite + 2 obsoleted), CLAUDE.md,
`.claude/skills/close-session/SKILL.md`, `render.yaml`, `requirements.md`, ADR-0003 status note,
`responses.py`, `routers/auth.py`, `templates/home.html`, deleted `apps/web/tsconfig.tsbuildinfo`.

## Testing Checklist
- [x] full backend suite green (comment/template edits only)
- [x] every command/claim in the touched docs is now true of the repo
- [x] ADR-0003 body untouched (status note only — append-only rule respected)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (none)
- [x] Scope boundaries defined

## Notes
Branch `chore/T79-coherence-sweep`. Assumption flagged for the owner in the PR: `render.yaml`
`branch: develop → main` matches the file's own "switch once the release lands" comment and the
live dashboard, but say if the dashboard was never flipped.
