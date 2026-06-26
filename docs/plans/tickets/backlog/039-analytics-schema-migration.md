---
status: Backlog
priority: High
complexity: Medium
category: Tech-Debt
tags: [backend, prisma, schema, analytics, migration]
blocked_by: []
blocks: [033, 034, 036]
parent_ticket: null
---

# Feature: Analytics schema migration — apply the ADR-0003 on-demand contract (T39)

## Rationale
ADR-0003 (option A, chosen) makes per-user analytics **on-demand in TS**, not batch tables. The current schema still carries batch tables (`TasteVector`, `Compatibility`, `UserStats`) and a stored `User.clusterId`, and has **no `ModelArtifact`** — the train→infer contract. This ticket aligns the schema to the decision before any analytics code is written, in one reviewed migration (schema changes have wide blast radius — CLAUDE.md).

## Summary
Add a self-describing `ModelArtifact` table; drop `TasteVector`, `Compatibility`, `UserStats`, and `User.clusterId` (+ their `User` relations). Keep `Cluster` and `ModelMetrics`.

## Source
- ADRs: [ADR-0003](../../../decisions/adr/0003-analytics-runtime.md) (train→infer; live stats) · [ADR-0004](../../../decisions/adr/0004-analytics-data-strategy.md) C2 (K-means on tracks) · [ADR-0009](../../../decisions/adr/0009-medallion-layering.md) (bronze/silver/gold schemas) · [ADR-0001](../../../decisions/adr/0001-use-architecture-decision-records.md) (resolves the open "result-table contract incl. ModelArtifact")

## Scope
### In Scope
- **Add `ModelArtifact`** (self-describing so TS inference reads every parameter, never hardcodes one):
  ```prisma
  model ModelArtifact {
    modelName    String   @id   // "kmeans" | "popularity_regression"
    featureOrder Json           // ordered feature names
    scalerMean   Json           // per-feature StandardScaler mean
    scalerStd    Json           // per-feature StandardScaler std
    params       Json           // kmeans: { centroids: number[][] }; regression: { coefficients, intercept }
    computedAt   DateTime
  }
  ```
- **Drop** models `TasteVector`, `Compatibility`, `UserStats`; drop field `User.clusterId` and the `User.stats`/`User.tasteVector` relations. (Cluster assignment, compatibility, taste vector, and stats are all computed on read — T33/T14.)
- **Keep** `Cluster` (label/centroid/size) and `ModelMetrics`.
- **Medallion layering (ADR-0009):** enable Prisma `multiSchema`; create `bronze`/`silver`/`gold` schemas; place `Track`+`Play` in **silver**, `Cluster`+`ModelMetrics`+`ModelArtifact` in **gold**; add bronze raw tables `bronze.spotify_recently_played_raw` + `bronze.kaggle_tracks_raw`.

### Out of Scope
- Writing the artifact (T34/T36) or reading it (T33/T14).

## Migration procedure (CLAUDE.md — `prisma migrate dev` hangs here)
1. Edit `prisma/schema.prisma` as above.
2. Generate SQL non-interactively:
   `npx prisma migrate diff --from-schema-datasource prisma/schema.prisma --to-schema-datamodel prisma/schema.prisma --script > prisma/migrations/<ts>_analytics_contract/migration.sql`
3. Apply with `npm run prisma:deploy`.

## Validation & authz (ADR-0007)
- **Integrity:** the DB remains the source of truth for what can exist; `ModelArtifact.modelName` PK enforces one row per model. No request surface.

## Current State (on `develop`)
- `prisma/schema.prisma` lines ~154–199: `UserStats`, `TasteVector`, `Cluster`, `Compatibility`, `ModelMetrics`; `User.clusterId` + `cluster` relation present; **no `ModelArtifact`.**
- Nothing reads/writes these analytics tables yet (analytics layer unbuilt), so the drops are safe.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `prisma/schema.prisma` | MODIFY | add `ModelArtifact`; drop `TasteVector`/`Compatibility`/`UserStats`/`User.clusterId` |
| `prisma/migrations/<ts>_analytics_contract/migration.sql` | CREATE | generated migration |

## Testing Checklist
- [ ] `npm run prisma:deploy` applies cleanly on `brink-dev`
- [ ] `npx prisma generate` succeeds; types reflect the new `ModelArtifact` and removed models
- [ ] `npm test` still green (no code referenced the dropped models)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T01 done)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T39-analytics-schema`; one PR back into `develop` (never `main`). Wide-blast-radius schema change → owner Andrea, deliberate review. Update the data-model section of the spec in the same PR (CLAUDE.md docs-in-sync rule).
