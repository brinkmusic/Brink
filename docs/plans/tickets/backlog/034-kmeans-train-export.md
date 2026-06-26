---
status: Backlog
priority: High
complexity: High
category: Feature
tags: [analytics, python, kmeans, ml]
blocked_by: [031, 039]
blocks: [033, 038, 045]
parent_ticket: null
---

# Feature: K-means training on tracks + ModelArtifact export (T34)

## Rationale
K-means is the graded ML centerpiece. Per ADR-0004 C2 it is trained on the **Kaggle track audio-space** (real elbow/silhouette on ~1M tracks) — one model over tracks, not a weak second clustering over our few users. The trained parameters are exported so the FastAPI backend can assign any user on-demand.

## Summary
Fit K-means on Kaggle track audio features, select k via elbow + silhouette, write human-readable `Cluster` rows + `ModelMetrics(kmeans)`, and export the self-describing `ModelArtifact("kmeans")` (feature order + scaler mean/std + centroids) that the on-read inference (T33) reads.

## Source
- Spec reqs: **AN-3**, **AN-4**
- ADRs: [ADR-0004](../../../decisions/adr/0004-analytics-data-strategy.md) C2 · [ADR-0003](../../../decisions/adr/0003-analytics-runtime.md) (train→infer; export params)

## ⚠ Changed from draft
The draft also **assigned each user** to a cluster and wrote `User.clusterId`. Under option A that assignment is **on-demand in TS** (T33/T14), so this ticket does **not** touch users — it trains on tracks and exports params only.

## Scope
### In Scope
- `analytics/cluster.py` — standardize track features (`StandardScaler`); fit K-means; select k via elbow + silhouette; derive human-readable cluster labels.
- Write `Cluster` rows (label, centroid, size).
- Write `ModelMetrics(modelName="kmeans": silhouette, k)`.
- **Export `ModelArtifact("kmeans")`:** `featureOrder`, `scalerMean`, `scalerStd`, `params = { centroids }` (the guardrail — fully self-describing for the on-read inference).

### Out of Scope
- Assigning users / writing `User.clusterId` (dropped — T39; computed on read in T33/T14).
- Compatibility (T35), regression (T36).

## Validation & authz (ADR-0007)
- **Integrity:** `ModelArtifact("kmeans")` is the single source for inference params; centroids and scaler must be in the **same standardized space** and feature order the on-read inference (T33) will use.
- **Determinism:** fixed random seed so k/labels are stable and defensible in the report.

## Current State (on `develop`)
- `analytics/db.py` (T30); Kaggle-joined `Track` audio features (T31); `ModelArtifact` + `Cluster` + `ModelMetrics` schema (T39).
- No `cluster.py` yet.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `analytics/cluster.py` | CREATE | fit + select k + label + write Cluster/ModelMetrics + export ModelArtifact |
| `analytics/tests/test_cluster.py` | CREATE | clustering + export tests |

## Testing Checklist
- [ ] deterministic seed → stable k and labels
- [ ] `Cluster` rows written with label, centroid, size
- [ ] `ModelMetrics("kmeans")` has silhouette + k
- [ ] `ModelArtifact("kmeans")` round-trips: featureOrder + scalerMean/Std + centroids, all aligned
- [ ] centroid dimensionality == len(featureOrder)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T31, T39 → blocked_by 031, 039)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T34-kmeans`; one PR back into `develop` (never `main`). Owner: Jonah. Reads **silver** (`Track`), writes **gold** (`Cluster`/`ModelMetrics`/`ModelArtifact`) per ADR-0009. The on-read inference (T33) depends on the exact `featureOrder`/scaler stored here — keep them authoritative, never duplicate the constants in the backend.
