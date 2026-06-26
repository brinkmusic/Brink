---
status: Backlog
priority: Medium
complexity: Medium
category: Feature
tags: [analytics, python, ci, github-actions, scheduling]
blocked_by: [031, 034, 036]
blocks: []
parent_ticket: null
---

# Feature: Pipeline orchestration + GitHub Actions nightly (T38)

## Rationale
The Python training steps need to run as one idempotent job on a schedule, with a manual trigger before demos. Per ADR-0006 this runs on GitHub Actions (managed-cron cadence is too coarse, and GitHub Actions keeps the scheduler in-repo).

## Summary
An idempotent `run_pipeline.py` structured as explicit **bronze → silver → gold** stages (land raw → conform `Track`/`Play` → train + export `Cluster`/`ModelMetrics`/`ModelArtifact`), each idempotent and logged, plus a GitHub Actions workflow that runs it nightly + on `workflow_dispatch`.

## Source
- Spec reqs: **AN-8**, **INFRA-4**
- ADRs: [ADR-0006](../../../decisions/adr/0006-scheduling.md) (GitHub Actions, nightly + dispatch) · [ADR-0009](../../../decisions/adr/0009-medallion-layering.md) (staged bronze/silver/gold) · [ADR-0003](../../../decisions/adr/0003-analytics-runtime.md)

## ⚠ Changed from draft
The draft pipeline also ran **compat + aggregate (UserStats)**. Under option A those are TS on-read (T35/T14), so the pipeline is **train-and-export only** — ingest, cluster, regression, write `Cluster`/`ModelMetrics`/`ModelArtifact`. No per-user steps.

## Scope
### In Scope
- `analytics/run_pipeline.py` — idempotent, **staged** (ADR-0009):
  - **bronze** — land raw Kaggle (T31) into `bronze.kaggle_tracks_raw` (snapshots land via T21).
  - **silver** — conform into `Track`/`Play` (join audio features, coverage, dedup).
  - **gold** — cluster+export (T34) → regression+export (T36); write `Cluster`/`ModelMetrics`/`ModelArtifact`.
  - structured per-stage logging of coverage/k/silhouette/R²/RMSE; each stage independently re-runnable/backfillable.
- `.github/workflows/analytics.yml` — `astral-sh/setup-uv`, `uv sync` + `uv run python run_pipeline.py`; `schedule` (nightly) + `workflow_dispatch`; `DATABASE_URL` secret.

### Out of Scope
- Synthetic seeding (T32 — a setup step, not nightly), per-user inference (TS), the Spotify snapshot job (T21).

## Validation & authz (ADR-0007)
- **Integrity:** idempotent — a re-run reproduces consistent artifacts/metrics; failures don't leave half-written model state.

## Current State (on `develop`)
- `analytics/` with `db.py`, `ingest_kaggle.py`, `cluster.py`, `regression.py` (T30/T31/T34/T36).
- No `run_pipeline.py` or `.github/workflows/analytics.yml` yet.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `analytics/run_pipeline.py` | CREATE | idempotent orchestration |
| `.github/workflows/analytics.yml` | CREATE | nightly + manual dispatch |
| `analytics/tests/test_run_pipeline.py` | CREATE | dry-run / idempotency test |

## Testing Checklist
- [ ] end-to-end dry run on a test DB completes
- [ ] re-run produces consistent artifacts/metrics (idempotent)
- [ ] logs coverage %, k, silhouette, R², RMSE
- [ ] workflow valid; nightly schedule + `workflow_dispatch`; uses `DATABASE_URL` secret

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T31, T34, T36 → blocked_by 031, 034, 036)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T38-pipeline-cron`; one PR back into `develop` (never `main`). Owner: Jonah. `workflow_dispatch` is the pre-demo refresh.
