# ADR-0001: Use Architecture Decision Records

**Status:** Accepted
**Date:** 2026-06-25

This ADR records the convention *and* serves as the index for `docs/decisions/`. The index and open-decisions sections below are **living** (updated as records are added); the Context/Decision/Consequences above them are the fixed decision itself.

## Context

The architectural forks were first sketched as a single table (rows A–E) inside [`brink-spec-design.md`](../../plans/2026-06-22-brink-spec-design.md). A table buried in the spec has no room for the alternatives weighed or the consequences accepted, and — worse — it inverts the dependency: it reads as if the spec decides and everything else follows. In reality the decisions come first and the spec is one of their outputs.

## Decision

**`docs/decisions/` is the source of truth for architectural decisions.** The spec design and the implementation tickets are *derived from* these records and must be kept consistent with them — never the reverse. When a decision changes, update the ADR here first, then propagate the change down into `brink-spec-design.md` and the tickets.

Records are **ADRs** (`adr/`) — a fork in the road, decided at a point in time, append-only. One file per decision (`NNNN-kebab-title.md`), using [`template.md`](../template.md). To reverse one, write a new ADR that supersedes it; don't edit the old one. Each ADR holds its own full reasoning (context, alternatives, consequences) inline.

## Index

| # | Decision | Layer |
|---|----------|-------|
| [0001](0001-use-architecture-decision-records.md) | Use Architecture Decision Records | — |
| [0002](0002-api-and-persistence.md) | API + persistence (Vercel + Supabase + Prisma) | BE |
| [0003](0003-analytics-runtime.md) | Analytics runtime — batch training, on-demand inference, live stats | AN |
| [0004](0004-analytics-data-strategy.md) | Analytics data strategy (C1–C5) | AN / DATA |
| [0005](0005-identity.md) | Identity via Supabase Auth | AUTH |
| [0006](0006-scheduling.md) | Scheduling — GitHub Actions cron times both jobs | INFRA |
| [0007](0007-validation-and-data-integrity.md) | Validation, authorization & data integrity (defense in depth) | BE |
| [0008](0008-no-content-moderation.md) | No artist-upload content moderation (out of scope) | MEDIA |

## Open decisions

Forks by layer. ✅ = resolved (where logged); ⬜ = still open; *(default)* = I'll take the noted default unless revisited.

- **AUTH** — ✅ token encryption (AES-256-GCM) · ✅ handle↔Spotify linking → merge into one account (ADR-0005) · ⬜ session strategy *(default: Supabase session defaults)*
- **BE** — ⬜ schema shape · ⬜ result-table contract incl. `ModelArtifact` (pipeline→app, [ADR-0003](0003-analytics-runtime.md)) · ⬜ API shape *(default: REST)* · ✅ validation/authz/integrity ([ADR-0007](0007-validation-and-data-integrity.md))
- **SP** — ✅ snapshot cadence (~2h) + dedup (`userId+playedAt`) · ✅ rate-limit handling ([ADR-0007](0007-validation-and-data-integrity.md))
- **AN** — ✅ k-selection (elbow + silhouette) · ✅ retrain frequency (nightly, [ADR-0003](0003-analytics-runtime.md)) · ⬜ distance metric *(default: Euclidean on standardized features)*
- **UI** — ⬜ state / data-fetching approach
- **MEDIA** — ⬜ signed-upload flow · ✅ size/format limits (≤10 MB JPEG/PNG) · ✅ moderation (none — [ADR-0008](0008-no-content-moderation.md))
- **INFRA** — ⬜ secrets management *(default: local `.env` + Vercel/GitHub env)* · ⬜ CI *(default: GitHub Actions lint+test on PR)*
- **DATA** — ✅ synthetic-user generation (genre-coherent personas, [ADR-0004](0004-analytics-data-strategy.md) C3)

## Alternatives considered

- **Keep everything in the spec table** — no space for alternatives/consequences; editing history is lost.
- **One growing decisions.md file** — merge conflicts and no stable per-decision anchors to link to.
- **Separate README index + 0001 convention** — the original split; folded together here to avoid two files stating the same conventions.

## Consequences

- Each meaningful call gets a defensible paper trail for the final report.
- Slight overhead per decision; reserved for *significant* choices, not every small one.
- This file is the single entry point — no `README.md`. The trade-off: opening the folder on GitHub won't auto-render a landing page; start at `adr/0001`.
