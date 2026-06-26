---
status: Backlog
priority: High
complexity: Medium
category: Feature
tags: [analytics, python, kaggle, data]
blocked_by: [030]
blocks: [032, 034, 036, 038]
parent_ticket: null
owner: Jonah
---

# Feature: Kaggle ingest + audio-feature join (T31)

## Rationale
The ML models need real audio features per track. Spotify's API no longer serves them, so we join a Kaggle audio-features dataset onto our `Track` rows. The `Track` model already has the feature columns + a `kaggleMatched` flag waiting to be populated.

## Summary
Load the Kaggle audio-features CSV, join to `Track` on `spotifyId` (= Kaggle `track_id`), set the audio-feature columns and `kaggleMatched`, and log match coverage %.

## Source
- Spec reqs: **AN-1**, **DATA-1**, ADR-0004 **C4**
- ADRs: [ADR-0004](../../../decisions/adr/0004-analytics-data-strategy.md) (≈1M-track set; coverage reported, not hidden) · [ADR-0009](../../../decisions/adr/0009-medallion-layering.md) (bronze raw → silver `Track`)

## Scope
### In Scope
- `analytics/ingest_kaggle.py` — **bronze:** load CSV into `bronze.kaggle_tracks_raw` (raw, append). **silver:** normalize columns, join to `Track` on `spotifyId`/`track_id`, set `danceability/energy/valence/tempo/loudness/popularity` + `kaggleMatched=true` on matches, log coverage % (ADR-0009).
- Non-matches left `kaggleMatched=false` (the C4 genre-only fallback is applied later, on read / in feature-building — not here).

### Out of Scope
- Building taste vectors / the fallback vector itself (T33).
- Choosing/storing the dataset file (manual step below).

## Validation & authz (ADR-0007)
- **Integrity:** writes only known `Track` columns; `kaggleMatched` boolean is the source of truth for whether features are real vs. fallback downstream.
- **Business rule:** coverage % is computed and logged (reported, never silently dropped — ADR-0004).

## Current State (on `develop`)
- `backend/app/models.py` `Track` has `danceability, energy, valence, tempo, loudness, popularity, kaggleMatched` columns ready.
- `analytics/db.py` exists from T30.
- No `ingest_kaggle.py` yet.

## Manual (user)
- Download the chosen **≈1M-track** Kaggle audio-features dataset (ADR-0004: a genuinely ~1M+ set, **not** `maharshipandya` ~114k — and correct the dataset name in the final report). Record the path/URL.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `analytics/ingest_kaggle.py` | CREATE | CSV load + join + coverage logging |
| `analytics/tests/test_ingest_kaggle.py` | CREATE | join + coverage tests |

## Testing Checklist
- [ ] join sets audio features on matching `Track` rows
- [ ] non-matching tracks remain `kaggleMatched=false`
- [ ] coverage % computed and logged
- [ ] idempotent: re-running doesn't duplicate or corrupt feature data

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T30 → blocked_by 030)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T31-kaggle-join`; one PR back into `develop` (never `main`). Owner: Jonah (analytics).
