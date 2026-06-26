---
status: Backlog
priority: Medium
complexity: Low
category: Tech-Debt
tags: [cleanup, mocks, frontend, backend]
blocked_by: [041, 044, 045]
blocks: [061]
parent_ticket: null
---

# Feature: Retire mocks + dead paths (T60)

## Rationale
Once feed, profile, and analytics are live (T41/T44/T45), the mock data sources and the jsonblob backend are dead weight and a correctness risk. Remove them from production code.

## Summary
Delete `mocks/feed.ts`, `mocks/stats.ts`, the jsonblob `api/state.js`, the heuristic `lib/analytics.ts`, and the `lib/data.ts` mock path — anything no longer referenced after the live wiring.

## Source
- Spec reqs: **DATA-4**, **BE-2** (final), **UI-9**
- ADRs: [ADR-0002](../../../decisions/adr/0002-api-and-persistence.md) (jsonblob superseded)

## Scope
### In Scope
- Remove `apps/web/src/mocks/feed.ts`, `apps/web/src/mocks/stats.ts`.
- Remove `apps/web/src/lib/data.ts` (mock feed) and `apps/web/src/lib/analytics.ts` (heuristic) once unreferenced.
- Delete `api/state.js` (jsonblob).
- Grep-verify no remaining imports.

### Out of Scope
- Any feature behavior change — this is deletion only, after the live paths land.

## Validation & authz (ADR-0007)
- Pure removal; the guarantee is that nothing in production still imports the removed modules.

## Current State (on `develop`)
- Present: `mocks/feed.ts`, `mocks/stats.ts`, `lib/data.ts`, `lib/analytics.ts`, `api/state.js`. (`FeedPage` still imports `lib/data` until T41.)

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `apps/web/src/mocks/feed.ts` | DELETE | mock feed |
| `apps/web/src/mocks/stats.ts` | DELETE | mock stats |
| `apps/web/src/lib/data.ts` | DELETE | mock data path |
| `apps/web/src/lib/analytics.ts` | DELETE | heuristic analytics |
| `api/state.js` | DELETE | jsonblob backend |

## Testing Checklist
- [ ] `grep -r "lib/data\|mocks/\|lib/analytics\|state.js" apps/web/src api` returns nothing
- [ ] `npm run build` + `npm test` green
- [ ] app still works end-to-end (feed/profile/analytics) with no mock fallback

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T41, T44, T45 → blocked_by 041, 044, 045)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T60-retire-mocks`; one PR back into `develop` (never `main`).
