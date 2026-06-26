---
status: Backlog
priority: High
complexity: Medium
category: Tech-Debt
tags: [backend, sqlmodel, alembic, schema, analytics, migration]
blocked_by: [005]
blocks: [033, 034, 036]
parent_ticket: null
---

# Feature: Analytics schema migration — apply the ADR-0003 on-demand contract (T39)

## Rationale
ADR-0003 (option A, chosen) makes per-user analytics **on-demand in the FastAPI backend**, not batch tables. The current schema still carries batch tables (`TasteVector`, `Compatibility`, `UserStats`) and a stored `User.clusterId`, and has **no `ModelArtifact`** — the train→infer contract. This ticket aligns the schema to the decision before any analytics code is written, in one reviewed migration (schema changes have wide blast radius — CLAUDE.md). It runs on the SQLModel + Alembic foundation from T05 (`blocked_by: [005]`).

## Summary
Add a self-describing `ModelArtifact` table; drop `TasteVector`, `Compatibility`, `UserStats`, and `User.clusterId` (+ their `User` relations). Keep `Cluster` and `ModelMetrics`.

## Source
- ADRs: [ADR-0003](../../../decisions/adr/0003-analytics-runtime.md) (train→infer; live stats) · [ADR-0004](../../../decisions/adr/0004-analytics-data-strategy.md) C2 (K-means on tracks) · [ADR-0009](../../../decisions/adr/0009-medallion-layering.md) (bronze/silver/gold schemas) · [ADR-0001](../../../decisions/adr/0001-use-architecture-decision-records.md) (resolves the open "result-table contract incl. ModelArtifact")

## Scope
### In Scope
- **Add `ModelArtifact`** (self-describing so the on-read inference reads every parameter, never hardcodes one):
  ```python
  class ModelArtifact(SQLModel, table=True):
      model_name: str = Field(primary_key=True)   # "kmeans" | "popularity_regression"
      feature_order: list = Field(sa_column=Column(JSON))  # ordered feature names
      scaler_mean: list = Field(sa_column=Column(JSON))    # per-feature StandardScaler mean
      scaler_std: list = Field(sa_column=Column(JSON))     # per-feature StandardScaler std
      params: dict = Field(sa_column=Column(JSON))         # kmeans: {centroids: [[...]]}; regression: {coefficients, intercept}
      computed_at: datetime
  ```
- **Drop** models `TasteVector`, `Compatibility`, `UserStats`; drop field `User.clusterId` and the `User.stats`/`User.tasteVector` relations. (Cluster assignment, compatibility, taste vector, and stats are all computed on read — T33/T14.)
- **Keep** `Cluster` (label/centroid/size) and `ModelMetrics`.
- **Medallion layering (ADR-0009):** use SQLAlchemy multi-schema (`__table_args__ = {"schema": ...}`); create `bronze`/`silver`/`gold` schemas; place `Track`+`Play` in **silver**, `Cluster`+`ModelMetrics`+`ModelArtifact` in **gold**; add bronze raw tables `bronze.spotify_recently_played_raw` + `bronze.kaggle_tracks_raw`.

### Out of Scope
- Writing the artifact (T34/T36) or reading it (T33/T14).

## Migration procedure (Alembic — replaces the old Prisma `migrate diff` workaround)
1. Edit `backend/app/models.py` as above (add `ModelArtifact`; drop the listed models/fields; set schemas).
2. Autogenerate the revision: `cd backend && uv run alembic revision --autogenerate -m "analytics contract"`; review the generated SQL (create `bronze`/`silver`/`gold` schemas; the table moves/drops are intentional).
3. Apply with `uv run alembic upgrade head`.

## Validation & authz (ADR-0007)
- **Integrity:** the DB remains the source of truth for what can exist; `ModelArtifact.modelName` PK enforces one row per model. No request surface.

## Current State (on `develop`)
- `backend/app/models.py`: `UserStats`, `TasteVector`, `Cluster`, `Compatibility`, `ModelMetrics`; `User.clusterId` + `cluster` relation present; **no `ModelArtifact`.**
- Nothing reads/writes these analytics tables yet (analytics layer unbuilt), so the drops are safe.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/models.py` | MODIFY | add `ModelArtifact`; drop `TasteVector`/`Compatibility`/`UserStats`/`User.clusterId` |
| `backend/alembic/versions/<rev>_analytics_contract.py` | CREATE | generated Alembic migration |

## Testing Checklist
- [ ] `uv run alembic upgrade head` applies cleanly on `brink-dev`
- [ ] models import; metadata reflects the new `ModelArtifact` and removed models; `bronze`/`silver`/`gold` schemas created
- [ ] `uv run pytest` still green (no code referenced the dropped models)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T01 done)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T39-analytics-schema`; one PR back into `develop` (never `main`). Wide-blast-radius schema change → owner Andrea, deliberate review. Update the data-model section of the spec in the same PR (CLAUDE.md docs-in-sync rule).
