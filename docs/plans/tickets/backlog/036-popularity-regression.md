---
status: Backlog
priority: Medium
complexity: Medium
category: Feature
tags: [analytics, python, regression, ml]
blocked_by: [031, 039]
blocks: [038, 045]
parent_ticket: null
owner: Jonah
---

# Feature: Popularity regression + coefficient export (T36)

## Rationale
A second real model strengthens the analytics story cheaply: a linear regression of audio features → track popularity, reported with R²/RMSE + feature importances (labeled exploratory per ADR-0004 C5).

## Summary
Fit a linear regression on Kaggle-joined track features predicting `popularity`, with a train/test split; write `ModelMetrics(popularity_regression)`; export `ModelArtifact("popularity_regression")` (feature order + scaler + coefficients/intercept) so any prediction widget runs on-demand in TS.

## Source
- Spec reqs: **AN-6**, ADR-0004 **C5**
- ADRs: [ADR-0004](../../../decisions/adr/0004-analytics-data-strategy.md) C5 · [ADR-0003](../../../decisions/adr/0003-analytics-runtime.md) (export params; TS predicts on read)

## Scope
### In Scope
- `analytics/regression.py` — assemble feature matrix from Kaggle-matched tracks; train/test split; fit linear regression; compute R²/RMSE + per-feature importances.
- Write `ModelMetrics(modelName="popularity_regression": r2, rmse, featureImportances)`.
- Export `ModelArtifact("popularity_regression")`: `featureOrder`, `scalerMean`, `scalerStd`, `params = { coefficients, intercept }`.

### Out of Scope
- Any UI prediction widget — that's TS linear-predict from this artifact, built in T45.

## Validation & authz (ADR-0007)
- **Integrity:** metrics persisted are finite; `ModelArtifact` coefficients align 1:1 with `featureOrder`.

## Current State (on `develop`)
- `analytics/db.py` (T30); Kaggle features on `Track` (T31); `ModelArtifact`/`ModelMetrics` schema (T39).
- No `regression.py` yet.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `analytics/regression.py` | CREATE | fit + metrics + export coefficients |
| `analytics/tests/test_regression.py` | CREATE | regression tests |

## Testing Checklist
- [ ] runs on a fixture; persists finite R²/RMSE
- [ ] `featureImportances` has one entry per feature
- [ ] `ModelArtifact("popularity_regression")` round-trips: coefficients length == len(featureOrder)
- [ ] train/test split is deterministic (seeded)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T31, T39 → blocked_by 031, 039)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T36-regression`; one PR back into `develop` (never `main`). Owner: Jonah. Reads **silver** (`Track`), writes **gold** (`ModelMetrics`/`ModelArtifact`) per ADR-0009. Labeled exploratory in the report (ADR-0004 C5).
