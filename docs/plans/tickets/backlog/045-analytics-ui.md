---
status: Backlog
priority: Medium
complexity: Medium
category: Feature
tags: [frontend, analytics, cleanup]
blocked_by: [034, 036]
blocks: [060]
parent_ticket: null
owner: Sebastian
---

# Feature: Analytics page on real tables + fold Predict (T45)

## Rationale
The analytics page currently shows hardcoded silhouette/feature-importance numbers and a fabricated `PredictPage`. This wires it to the real `ModelMetrics`/`Cluster` and migrates the only honest prediction (TS linear-predict from the regression artifact) into the analytics surface, deleting the fabricated page.

## Summary
`AnalyticsPage` reads real `ModelMetrics`/`Cluster`; remove `CLUSTER_POINTS` + hardcoded numbers; add a popularity-predict widget that runs TS linear-predict from `ModelArtifact("popularity_regression")`; delete `PredictPage` + its route + fabricated copy.

## Source
- Spec reqs: **UI-7**, **UI-8**, **AN-9**
- ADRs: [ADR-0003](../../../decisions/adr/0003-analytics-runtime.md) (TS predict from exported coefficients) · [ADR-0004](../../../decisions/adr/0004-analytics-data-strategy.md) C5

## Scope
### In Scope
- `AnalyticsPage.tsx` — read real silhouette/k/clusters/feature-importances (via an endpoint exposing `ModelMetrics`/`Cluster`, or a thin reader); remove `CLUSTER_POINTS` and all hardcoded analytics numbers.
- Popularity-predict widget: TS linear-predict from `ModelArtifact("popularity_regression")` (coefficients + scaler), labeled exploratory.
- Delete `PredictPage.tsx`, its route, and fabricated copy.

### Out of Scope
- Fitting the models (T34/T36); profile page (T44).

## Validation & authz (ADR-0007)
- Any new metrics-read endpoint passes `require_user` + Pydantic like every API route; predict input validated. (The linear-predict math runs client-side in the browser from the artifact coefficients the endpoint exposes — the frontend stays TS.)

## Current State (on `develop`)
- `apps/web/src/pages/AnalyticsPage.tsx` (hardcoded silhouette/feature-importance, `CLUSTER_POINTS`), `pages/PredictPage.tsx` (fabricated) both present.
- Real `ModelMetrics`/`Cluster` (T34/T36) + `ModelArtifact("popularity_regression")` (T36) provide the data.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `apps/web/src/pages/AnalyticsPage.tsx` | MODIFY | read real metrics/clusters; remove hardcoded values; add predict widget |
| `apps/web/src/pages/PredictPage.tsx` | DELETE | fabricated page removed |
| `backend/app/routers/analytics.py` | CREATE | thin authorized reader for `ModelMetrics`/`Cluster` (if no existing path) |
| `apps/web/src/App routes` | MODIFY | drop the `/predict` route |

## Testing Checklist
- [ ] analytics page shows real silhouette/k/feature-importances (no hardcoded constants remain)
- [ ] `CLUSTER_POINTS` and fabricated numbers removed (grep clean)
- [ ] predict widget computes from `ModelArtifact` coefficients; labeled exploratory
- [ ] `PredictPage` + `/predict` route deleted; no dead links

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T34, T36 → blocked_by 034, 036)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T45-analytics-ui`; one PR back into `develop` (never `main`). Owner: Sebastian (frontend), pairing with Jonah on the metrics shape.
