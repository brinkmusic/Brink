---
status: Completed
priority: Medium
complexity: High
category: Feature
tags: [spotify, snapshots, scheduling, github-actions]
blocked_by: [010, 039]
blocks: []
parent_ticket: null
owner: Andrea
---

# Feature: Scheduled play snapshots, triggered by GitHub Actions (T21)

## Rationale
Spotify only returns the last 50 plays, so 30-day stats, streaks, and the live UserStats aggregation are only "real" if we snapshot recently-played into `Play` on a cadence. This is the data tap the whole analytics layer drinks from.

## Summary
A FastAPI endpoint (on Render) that — per Spotify-linked user — refreshes the stored token, pulls recently-played, upserts `Track`, and inserts `Play` rows (deduped on `userId+playedAt`); triggered every ~2h by a GitHub Actions workflow that curls the endpoint with `CRON_SECRET`.

## Source
- Spec reqs: **SP-2, SP-4, SP-5, INFRA-3**
- ADRs: [ADR-0006](../../../decisions/adr/0006-scheduling.md) (**GitHub Actions, not Vercel Cron**) · [ADR-0004](../../../decisions/adr/0004-analytics-data-strategy.md) C1 · [ADR-0005](../../../decisions/adr/0005-identity.md) (server-side token refresh) · [ADR-0009](../../../decisions/adr/0009-medallion-layering.md) (bronze landing → silver `Play`) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)

## ⚠ Changed from draft
The original T21 added a `crons` entry to `vercel.json`. **ADR-0006 supersedes that** (managed-cron cadence was too coarse for ~2h). Under ADR-0010 the snapshot is a **FastAPI endpoint on Render**, and its **trigger is a GitHub Actions workflow** that calls the endpoint URL with `CRON_SECRET`. No managed-cron entry is used.

## Scope
### In Scope
- `backend/app/routers/snapshot.py` — iterate Spotify-linked users; refresh token; pull recently-played; **land raw rows into `bronze.spotify_recently_played_raw`** (append/immutable), then a **silver** step upserts `Track` + inserts `Play` deduped on `(userId, playedAt)` (ADR-0009); 429 backoff; skip unlinked users.
- Authenticate the trigger with `CRON_SECRET` (the endpoint is now a public URL).
- `.github/workflows/snapshot.yml` — schedule ~every 2h + `workflow_dispatch`; curls the endpoint with the secret.

### Out of Scope
- The analytics pipeline workflow (T38) — separate nightly job.
- Any `vercel.json` crons entry (explicitly dropped per ADR-0006).

## Validation & authz (ADR-0007)
- **Authorization of the trigger:** reject requests without the correct `CRON_SECRET` → 401 — the ownership story for a now-public URL.
- **Integrity:** the unique constraint on `(userId, playedAt)` in `backend/app/models.py` makes duplicate plays structurally impossible even if the job double-runs.

## Current State (on `develop`)
- Present after **T22**: `backend/app/spotify.py` (server-side token refresh, `get_valid_access_token`); plus `backend/app/deps.py` and encrypted `SpotifyToken` storage (T06). (The refresh helper was built in T22, not T06 — earlier notes here misattributed it.)
- `Play` and `Track` already modeled in `backend/app/models.py`.
- No snapshot router (`backend/app/routers/snapshot.py`) and no `.github/workflows/snapshot.yml` yet.
- `upsert_track` is introduced by T10 (hence `blocked_by: [010]`).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/snapshot.py` | CREATE | snapshot FastAPI endpoint |
| `backend/app/spotify.py` | MODIFY | add recently-played fetch alongside `get_valid_access_token` |
| `.github/workflows/snapshot.yml` | CREATE | ~2h cron + manual dispatch; curls endpoint with `CRON_SECRET` |
| `backend/tests/test_snapshot.py` | CREATE | tests |

## Testing Checklist
- [x] mock recently-played → inserts new plays, skips duplicates (dedup on userId+playedAt)
- [x] 429 from Spotify → backoff path, no crash
- [x] user without a linked Spotify token is skipped
- [x] request without `CRON_SECRET` → 401
- [x] workflow file valid; schedules ~2h + `workflow_dispatch`

## Implementation notes (as built)
- `backend/app/routers/snapshot.py` — `POST /api/snapshot`, authed by the `X-Cron-Secret` header
  (fails closed with 401 if the header is wrong or `CRON_SECRET` isn't configured). Iterates
  Spotify-linked users (join on `SpotifyToken`), lands the raw payload into
  `bronze.spotify_recently_played_raw`, then conforms to silver: `upsert_track` + insert `Play`
  deduped on `(userId, playedAt)`; commits per user. Returns
  `{usersProcessed, usersSkipped, playsInserted}`.
- `backend/app/spotify.py` — `get_recently_played(session, user_id)` (uses `get_valid_access_token`);
  one bounded 429 backoff+retry via a patchable `_sleep`; returns `None` (skip) on no-token/error.
- `.github/workflows/snapshot.yml` — ~2h cron + `workflow_dispatch`; `curl -f` POSTs the endpoint
  with `X-Cron-Secret`. **Requires two GitHub repo secrets: `SNAPSHOT_URL` + `CRON_SECRET`**, and a
  matching `CRON_SECRET` env var on the Render backend — a manual deploy step (Andrea).
- Satisfies **SP-2, SP-4, SP-5, INFRA-3**. Tests in `test_snapshot.py`; full suite 110 passed.
- Bronze `payload` column is `JSONB` in Postgres, `JSON` under SQLite (`.with_variant`) so the
  in-memory test DB can build the table.

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T02 done; T10 track upsert → blocked_by 010)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T21-snapshot-cron`; one PR back into `develop` (never `main`).
