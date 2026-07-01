# ADR-0009: Medallion-style layering for the analytics pipeline

**Status:** Accepted
**Date:** 2026-06-25
**Extends:** [ADR-0003](0003-analytics-runtime.md), [ADR-0006](0006-scheduling.md)

## Context

[ADR-0003](0003-analytics-runtime.md) chose batch training + on-read inference, but the *batch* data flows with no explicit staging: the snapshot job lands recently-played straight into `Play`, the Kaggle ingest joins straight onto `Track`, and the models write results inline. There is no raw landing zone and no legible bronze → silver → gold lineage, which makes the pipeline harder to debug and backfill and gives up an easy, defensible data-engineering story for the report. We want explicit data-quality layers **without leaving the free Supabase Postgres or adding a lakehouse** (Spark/Delta/Databricks would be the wrong scale, stack, and cost for ~MB of data).

## Decision

Organize the **batch** analytics data into **bronze / silver / gold Postgres schemas** inside the existing Supabase database (Prisma `multiSchema`), staged by the GitHub Actions pipeline ([ADR-0006](0006-scheduling.md)):

- **bronze** — raw, append-only, immutable landings: `bronze.spotify_recently_played_raw`, `bronze.kaggle_tracks_raw` (minimal typing + an ingest timestamp; never updated in place).
- **silver** — cleaned / conformed entities the app reads: `Track` (joined audio features + `kaggleMatched` + coverage) and deduped `Play`. *These are today's operational tables — they simply become the silver layer.*
- **gold** — analytical / model outputs: `Cluster`, `ModelMetrics`, `ModelArtifact`.

**Per-user serving stays on-read in TS ([ADR-0003](0003-analytics-runtime.md) option A).** Taste vector, cluster assignment, compatibility, and UserStats are computed at request time and are **not** gold tables. Medallion governs **batch lineage only** — the staleness ADR-0003 avoided stays avoided.

The pipeline runs explicit, idempotent **bronze → silver → gold** stages with per-stage logging, so each layer can be rebuilt or backfilled independently.

## Alternatives considered

- **Real lakehouse (Delta/Parquet + Spark/Databricks)** — the canonical medallion stack, but wrong scale (a few MB), wrong stack (we're on Postgres + serverless TS), real cost, and heavy ops against a fixed deadline.
- **DuckDB + dbt** — a clean, genuinely-free modern option (Parquet/DuckDB layers transformed by dbt on the Actions runner). Rejected *for now* only because it adds a new tool + scope; revisit if DE depth becomes a graded differentiator.
- **Status quo (no layering)** — simplest, but no lineage story and harder to debug where data degraded.
- **Materialize gold user-stats too** — would reintroduce the staleness [ADR-0003](0003-analytics-runtime.md) deliberately dropped; rejected.

## Consequences

- A clear, defensible DE lineage for the final report; the staged, idempotent pipeline is easier to debug and backfill.
- More tables/schemas. At a few-MB scale the **bronze raw layer is partly ceremonial** — its value is lineage/legibility, not performance. Accepted as the cost of an honest medallion story.
- Requires Prisma `multiSchema` and a migration that places `Track`/`Play` in `silver`, the result tables in `gold`, and adds the `bronze.*_raw` tables.
- **Reconciles with [ADR-0003](0003-analytics-runtime.md):** gold = corpus/model outputs only; user-facing values remain on-read.
- **Free** — same Supabase Postgres, same GitHub Actions runner; no new vendor or cost.
- **Ticket ripple (apply in the redo):** T39 gains the schemas + `multiSchema` + table placement; T21/T31 gain a bronze landing + a silver conform step; T34/T36 read silver / write gold; T38 becomes an explicit staged bronze→silver→gold pipeline.
