---
status: Backlog
priority: High
complexity: Medium
category: Feature
tags: [backend, ts, inference, analytics, validation]
blocked_by: [034, 039]
blocks: [014, 035]
parent_ticket: null
---

# Feature: TS on-demand inference core — taste vector + cluster assignment (T33)

## Rationale
Under ADR-0003 (option A), a user's taste vector and cluster are computed **live in the TS API** from the exported `ModelArtifact`, so profiles reflect the user's latest listening instantly. This ticket builds that shared inference core, which the profile API (T14), compatibility (T35), and profile UI (T44) all use.

## Summary
A TS module that builds a user's taste vector from their tracks' audio features (with the C4 genre-only fallback + coverage), standardizes it using the `ModelArtifact` scaler, and assigns the nearest K-means centroid — reading every parameter from the artifact, never hardcoding.

## Source
- Spec reqs: **AN-2**, ADR-0004 **C4**
- ADRs: [ADR-0003](../../../decisions/adr/0003-analytics-runtime.md) (inference on read from exported params) · [ADR-0004](../../../decisions/adr/0004-analytics-data-strategy.md) C2 (assign to track-centroid), C4 (fallback in the TS runtime too)

## ⚠ Changed from draft
The draft's T33 was a **Python** `features.py` writing a `TasteVector` table. Under option A there is no `TasteVector` table (T39); the taste vector is built **on read in TS**. This is the TS reimplementation of standardize → nearest-centroid that ADR-0003 calls out.

## Scope
### In Scope
- `api/_lib/inference/tasteVector.ts` — aggregate a user's `Play`/`Post` tracks into a vector in the K-means feature space (mean audio features, etc.); **C4 fallback:** genre-only vector for tracks where `kaggleMatched=false`; return coverage %.
- `api/_lib/inference/assign.ts` — load `ModelArtifact("kmeans")`; standardize the taste vector with `scalerMean/scalerStd` in `featureOrder`; return nearest centroid → `Cluster` (label).
- Graceful path when no `ModelArtifact` exists yet (returns null cluster, not 500).

### Out of Scope
- The profile endpoint itself (T14), compatibility (T35), UI (T44).

## Validation & authz (ADR-0007)
- **Integrity / correctness:** read `featureOrder` + scaler from the artifact and apply in that exact order — must match how T34 fit the model (the documented sync point).
- **Business rule:** report coverage % (ADR-0004 C4); a low-coverage user still gets a defensible fallback vector, never a crash.

## Current State (on `develop`)
- `ModelArtifact` schema (T39) + a written `ModelArtifact("kmeans")` and `Cluster` rows (T34).
- `Track.kaggleMatched` + audio-feature columns exist; `Play`/`Post` link users to tracks.
- No `api/_lib/inference/*` yet.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `api/_lib/inference/tasteVector.ts` | CREATE | build user taste vector + C4 fallback + coverage |
| `api/_lib/inference/assign.ts` | CREATE | standardize + nearest-centroid assignment |
| `api/__tests__/inference.test.ts` | CREATE | vector + fallback + assignment tests |

## Testing Checklist
- [ ] known fixture → expected taste vector (matches Python's feature definition)
- [ ] fallback path: track not in Kaggle → valid genre-only vector; coverage reflects it
- [ ] standardize uses artifact `scalerMean/Std` in `featureOrder` order
- [ ] nearest-centroid returns the correct `Cluster` for a planted vector
- [ ] no `ModelArtifact` present → null cluster, 200 (graceful), not 500

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T34, T39 → blocked_by 034, 039)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T33-taste-vectors`; one PR back into `develop` (never `main`). The feature definition here and in T34 must stay in lockstep — the `ModelArtifact` is the contract; treat any divergence as a bug. Owner: Andrea (TS), pairing with Jonah on the feature definition.
