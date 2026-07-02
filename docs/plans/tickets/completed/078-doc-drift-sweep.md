---
status: Completed
priority: Medium
complexity: Low
category: Docs
tags: [docs, drift, review-remediation]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Docs: Post-T08 doc-drift sweep + T60 rewrite (T78)

## Rationale
Findings **MI5**, **L10** (doc half), **L12** of the [2026-07-02 code review](../../reviews/2026-07-02-code-review-t00-t08.md).
"Stale docs are a bug" is a project norm, and T07/T08 left a trail: T60's file table still plans
to delete `api/state.js` (T08 already did) while omitting `apps/web/src/lib/backend.ts` — the
only remaining `/api/state` code and the exact file CLAUDE.md says T60 removes; CLAUDE.md/README
carry pre-cutover phrasing; `requirements.md` has two rows pointing at deleted files or lacking
the `†` superseded marker.

## Summary
One docs-only PR that re-syncs every stale statement found by the review and makes T60 executable
as written.

## Source
- Review findings: **MI5**, **L10** (docs), **L12**
- Spec reqs: **INFRA-2** (docs consistency)
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md). ADRs themselves are
  append-only — nothing in this ticket touches them.

## Scope
### In Scope
- `docs/plans/tickets/backlog/060-retire-mocks.md`: rewrite Current State + file table —
  `lib/backend.ts` (DELETE) in, `api/state.js` out; fix the grep checklist (no `api/` dir
  anymore); delete the moot "must land before T07" sequencing note; add "prune orphaned
  `spotify-api.ts` exports (`getTopTracks`/`getTopArtists`/`getRecentlyPlayed`; `getMe` survives)"
  to its checklist (**L12**).
- `CLAUDE.md`: `:43` annotate the analytics test command "(after T30)"; `:130` secrets live in
  "Render (backend) / Vercel (frontend) / GitHub" env.
- `README.md:36,87` (+ `apps/web/README.md` if same phrasing): TS backend "was removed in T08"
  (past tense; cutover complete).
- `docs/plans/requirements.md`: `:80` INFRA-1 gets the `†` superseded marker + a Superseded-section
  line pointing at ADR-0010; `:21` BE-2 reworded to the surviving client path
  (`apps/web/src/lib/backend.ts` + callers) instead of the two deleted files.

### Out of Scope
- Code changes of any kind. ADR edits. The backend comment fixes (T74 — they ride with code).

## Validation & authz (ADR-0007)
N/A (docs only).

## Current State (on `develop`)
- Each stale statement verified against the repo during the review (file:line in the findings).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `docs/plans/tickets/backlog/060-retire-mocks.md` | MODIFY | make executable post-T08 |
| `CLAUDE.md` | MODIFY | two stale statements |
| `README.md` / `apps/web/README.md` | MODIFY | past-tense the migration |
| `docs/plans/requirements.md` | MODIFY | INFRA-1 marker + BE-2 reword |

## Testing Checklist
- [ ] every command shown in the touched docs runs as written (or is explicitly future-marked)
- [ ] `git grep "api/state.js"` in docs matches only historical records (completed tickets/ADRs)
- [ ] T60 readable end-to-end as an executable ticket against today's `develop`

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (none)
- [x] Scope boundaries defined

## Notes
Branch `docs/T78-doc-drift-sweep`. Pure docs; quick review.
