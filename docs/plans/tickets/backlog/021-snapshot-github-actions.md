---
status: Backlog
priority: Medium
complexity: High
category: Feature
tags: [spotify, snapshots, scheduling, github-actions]
blocked_by: [010]
blocks: []
parent_ticket: null
---

# Feature: Scheduled play snapshots, triggered by GitHub Actions (T21)

## Rationale
Spotify only returns the last 50 plays, so 30-day stats, streaks, and the live UserStats aggregation are only "real" if we snapshot recently-played into `Play` on a cadence. This is the data tap the whole analytics layer drinks from.

## Summary
A Vercel serverless function that — per Spotify-linked user — refreshes the stored token, pulls recently-played, upserts `Track`, and inserts `Play` rows (deduped on `userId+playedAt`); triggered every ~2h by a GitHub Actions workflow that curls the endpoint with `CRON_SECRET`.

## Source
- Spec reqs: **SP-2, SP-4, SP-5, INFRA-3**
- ADRs: [ADR-0006](../../../decisions/adr/0006-scheduling.md) (**GitHub Actions, not Vercel Cron**) · [ADR-0004](../../../decisions/adr/0004-analytics-data-strategy.md) C1 · [ADR-0005](../../../decisions/adr/0005-identity.md) (server-side token refresh) · [ADR-0009](../../../decisions/adr/0009-medallion-layering.md) (bronze landing → silver `Play`) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)

## ⚠ Changed from draft
The original T21 added a `crons` entry to `vercel.json`. **ADR-0006 supersedes that:** the team is on Vercel **Hobby** (Cron capped at once/day — too coarse for a 2h cadence). The snapshot stays a Vercel function, but its **trigger moves to a GitHub Actions workflow** that calls the endpoint URL with `CRON_SECRET`. `vercel.json` crons are not used.

## Scope
### In Scope
- `api/jobs/snapshot.ts` — iterate Spotify-linked users; refresh token; pull recently-played; **land raw rows into `bronze.spotify_recently_played_raw`** (append/immutable), then a **silver** step upserts `Track` + inserts `Play` deduped on `(userId, playedAt)` (ADR-0009); 429 backoff; skip unlinked users.
- Authenticate the trigger with `CRON_SECRET` (the endpoint is now a public URL).
- `.github/workflows/snapshot.yml` — schedule ~every 2h + `workflow_dispatch`; curls the endpoint with the secret.

### Out of Scope
- The analytics pipeline workflow (T38) — separate nightly job.
- Any `vercel.json` crons entry (explicitly dropped per ADR-0006).

## Validation & authz (ADR-0007)
- **Authorization of the trigger:** reject requests without the correct `CRON_SECRET` → 401 — the ownership story for a now-public URL.
- **Integrity:** dedup `@@unique` on `(userId, playedAt)` in `prisma/schema.prisma` makes duplicate plays structurally impossible even if the job double-runs.

## Current State (on `develop`)
- Present from T02: `api/_lib/spotify.ts` (server-side token refresh, `getValidAccessToken`), `api/_lib/auth.ts`, encrypted `SpotifyToken` storage.
- `Play` and `Track` already modeled in `prisma/schema.prisma`.
- No `api/jobs/*` endpoint and no `.github/workflows/snapshot.yml` yet.
- `upsertTrack` is introduced by T10 (hence `blocked_by: [010]`).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `api/jobs/snapshot.ts` | CREATE | snapshot serverless function |
| `api/_lib/spotify.ts` | MODIFY | add recently-played fetch alongside `getValidAccessToken` |
| `.github/workflows/snapshot.yml` | CREATE | ~2h cron + manual dispatch; curls endpoint with `CRON_SECRET` |
| `api/__tests__/snapshot.test.ts` | CREATE | tests |

## Testing Checklist
- [ ] mock recently-played → inserts new plays, skips duplicates (dedup on userId+playedAt)
- [ ] 429 from Spotify → backoff path, no crash
- [ ] user without a linked Spotify token is skipped
- [ ] request without `CRON_SECRET` → 401
- [ ] workflow file valid; schedules ~2h + `workflow_dispatch`

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T02 done; T10 track upsert → blocked_by 010)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T21-snapshot-cron`; one PR back into `develop` (never `main`).
