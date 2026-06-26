---
status: Backlog
priority: High
complexity: Medium
category: Feature
tags: [backend, api, profile, analytics, validation]
blocked_by: [013, 033, 035]
blocks: [044]
parent_ticket: null
---

# Feature: Profile API — live stats + on-demand inference (T14, absorbs T37)

## Rationale
The profile is where the social and analytics layers meet. Under ADR-0003 it computes everything per-user on read: live listening stats (no `UserStats` table) plus taste vector / cluster / compatibility via the TS inference core. This is also where the old Python "T37 aggregation" now lives.

## Summary
`GET /api/users/[id]/profile` returns the user, their **live** stats (top tracks/genres/artists, streak, 30-day totals via Prisma group-bys over `Play`), follower/following counts, their cluster (T33), and compatibility vs the viewer (T35) — all degrading gracefully when empty.

## Source
- Spec reqs: **BE-8**, **AN-7** (absorbed from T37)
- ADRs: [ADR-0003](../../../decisions/adr/0003-analytics-runtime.md) (live UserStats; on-read inference) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)

## ⚠ Absorbs T37
ADR-0003 drops the `UserStats` table and folds aggregation into this endpoint as a TS group-by. **There is no standalone T37** — its AN-7 scope lives here.

## Scope
### In Scope
- `api/users/[id]/profile.ts` — assemble: user fields; **live stats** (top tracks/genres/artists, streak length, 30-day totals via Prisma group-bys over `Play`); follower/following counts; cluster label (T33 assignment); compatibility vs viewer (T35).
- Graceful empties: no plays → zeroed stats; no `ModelArtifact` → null cluster/compat. Always 200, never 500 on missing analytics.

### Out of Scope
- The profile UI (T44); now-playing endpoint (T20).

## Validation & authz (ADR-0007 — required on this ticket)
- **Schema (zod):** `[id]` param validated.
- **Authorization:** `requireUser`; compatibility is computed relative to the authenticated viewer.
- **Business rule:** an empty/synthetic/handle user renders gracefully (nulls/zeros), not an error.
- **Integrity:** reads only; live aggregation reflects current `Play` rows.

## Current State (on `develop`)
- `Play`, `Post`, `Follow` tables; T33 inference core + T35 compatibility helpers; `Cluster`/`ModelArtifact` (T39/T34). No `UserStats` table (dropped).
- No `api/users/[id]/profile.ts` yet.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `api/users/[id]/profile.ts` | CREATE | profile assembly: live stats + inference |
| `api/_lib/stats.ts` | CREATE | live aggregation group-bys (absorbs T37 logic) |
| `api/__tests__/profile.test.ts` | CREATE | profile + empty-state tests |

## Testing Checklist
- [ ] profile with no plays → zeroed stats, null cluster/compat, 200 (not 500)
- [ ] with seeded plays → correct top tracks/genres, streak, 30-day total
- [ ] cluster label present when `ModelArtifact` exists
- [ ] compatibility computed vs the authenticated viewer
- [ ] follower/following counts correct

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T13, T33, T35 → blocked_by 013, 033, 035)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T14-profile-api`; one PR back into `develop` (never `main`). The live-stats group-bys are the "real aggregation pipeline" the proposal promised — run on read (ADR-0003). Owner: Andrea.
