# ADR-0003: Analytics runtime — batch training, on-demand inference, live stats

**Status:** Accepted (language note 2026-07-15: the "TS API" this ADR describes for on-read
inference became the FastAPI/**Python** API when the backend moved — [ADR-0010](0010-fastapi-render-backend.md),
[ADR-0013](0013-python-frontend.md). The decision itself — batch training / on-read inference /
live aggregation — is unchanged.)
**Date:** 2026-06-22 · **Revised:** 2026-06-25 (split training from inference; UserStats made live)
**First captured as:** spec decision-log row B

## Context

Real ML (K-means, regression, cosine similarity) is the graded centerpiece of Brink. Today there is none: K-means is a regex rule table, silhouette and feature-importance numbers are hardcoded strings, and forecasts are deterministic hash/sine math.

The work splits into three kinds of compute with very different constraints:
- **Training** — fitting K-means on the ~1M-track corpus and fitting the regression. Slow (seconds–minutes), needs scikit-learn, can't sit on a request path.
- **Inference** — applying a *trained* model to one user (assign to nearest cluster, score compatibility). This is a few float operations, not a Python concern.
- **Aggregation** — top tracks/genres, streaks, 30-day totals. Pure group-by over plays; no model at all.

The API is **TypeScript on Vercel**; only the training step actually needs Python.

## Decision

Run the three kinds of compute where each belongs:

1. **Training = batch, Python + scikit-learn.** A nightly job (GitHub Actions cron, [ADR-0006](0006-scheduling.md)) fits K-means and the regression over the corpus and **exports the trained parameters** — cluster centroids, the `StandardScaler` mean/std, regression coefficients — to a persisted `ModelArtifact` (plus corpus-level result rows). The pipeline reads Postgres directly over the Postgres wire protocol (psycopg/SQLAlchemy); **this requirement constrains the platform choice — it's why D1/SQLite was rejected in [ADR-0002](0002-api-and-persistence.md).**

2. **Inference = on-demand, in the TS API.** Cluster assignment, the per-user taste vector, and compatibility are computed on read from the exported `ModelArtifact` params + current play data — standardize → nearest centroid, cosine between vectors, linear predict. No live Python runtime. Profiles reflect a user's latest listening immediately.

3. **UserStats = live, on-read DB aggregation.** Top tracks/genres/artists, streaks, and 30-day totals are computed at request time via Prisma group-bys over the `Play` table — **no model, no batch table.** Like now-playing, but sourced from the DB (so it works for synthetic users too and keeps the "real aggregation pipeline" the proposal promised, just run on read instead of on cron).

The `ModelArtifact` (centroids + scaler + coefficients) is the **train→infer contract**; its exact shape is part of the open BE result-tables decision.

## Alternatives considered

- **All-batch (precompute everything to tables, incl. UserStats)** — staleness on every output, and a `UserStats` table with no model behind it is needless batching of a cheap group-by.
- **On-demand training / a live Python service the TS API calls** — can't train per request, and it reintroduces an always-on Python host (the very thing [ADR-0002](0002-api-and-persistence.md)/[ADR-0006](0006-scheduling.md) avoid) plus an HTTP/auth contract and a cold-start dependency on the profile path. High cost, no benefit — centroids/coefficients change slowly.
- **In-app JS for the ML itself** — no real ML libraries; can't defend as genuine ML.
- **MLflow for tracking/registry/serving** — overkill for two models fit once nightly. The `ModelArtifact` already serves as the param registry and `ModelMetrics` already tracks silhouette/k/R²/RMSE in Postgres (queryable by app and report); inference is TS-from-params, not MLflow serving. Adopting it would mean two systems of record for the same data plus a server/dependency on a fixed deadline. *Optional exception: local file-based MLflow (`./mlruns`, no server) purely to log K-selection/feature experiments for the report — does not touch the app architecture.*

## Consequences

- **Two contracts, not one:** corpus-level result rows *and* a `ModelArtifact` for train→infer. Both feed the open BE result-tables decision.
- **Inference math is reimplemented in TS** (standardize → nearest centroid; cosine; linear predict). Small, but must stay in sync with how the params were fit.
- **No `UserStats` table.** Aggregation logic lives in the API and runs on read — always fresh, still graded as the real pipeline.
- **Training freshness is bounded by the nightly cron;** `workflow_dispatch` gives a manual on-demand refresh before a demo with no extra infra.
- **Ticket ripples (to apply in the spec/tickets redo):** T37 becomes a TS aggregation endpoint (likely folded into the T14 profile API), and the `UserStats` table drops from the schema; T34/T36 gain a parameter-export step; T14/T44 gain TS inference reading the exported params.
