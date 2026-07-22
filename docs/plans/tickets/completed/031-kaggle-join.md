---
status: Completed
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
- [x] join sets audio features on matching `Track` rows
- [x] non-matching tracks remain `kaggleMatched=false`
- [x] coverage % computed and logged
- [x] idempotent: re-running doesn't duplicate or corrupt feature data

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T30 → blocked_by 030)
- [x] Scope boundaries defined

## Outcome
`analytics/ingest_kaggle.py` lands the CSV raw into `bronze.kaggle_tracks_raw` (delete-then-insert
each run, so it never accumulates duplicates) and joins onto `silver.Track` by `spotifyId` ==
Kaggle `track_id`, filling in `danceability/energy/valence/tempo/loudness/popularity` +
`kaggleMatched` on matches; non-matches are left alone. Coverage is computed and logged
(ADR-0004: reported, never hidden). Tests (`analytics/tests/test_ingest_kaggle.py`) use a
disposable Track row + an on-the-fly fixture CSV, not the real dataset, so they don't depend on a
gitignored local file and don't touch real listening data.

**Scope deviation (disclosed):** the "Manual (user)" step above called for a genuinely ≈1M+-track
Kaggle set per ADR-0004. That set wasn't available in time, so this ticket ran against a **~114k
interim substitute** (`SpotifyAudioFeaturesApril2019.csv`, gitignored under `analytics/data/`,
sourced manually — not committed). This is a **temporary stand-in, not a scope decision** — no ADR
change was made. Coverage against brink-dev's real `Track` rows was **14/343 matched (4.1%)**,
honestly logged rather than hidden. Swapping in the real ~1M+ set later just means re-running
`ingest_kaggle.py` against the new file — no code change needed. Downstream tickets (T33's K-means
training in particular) should be aware coverage is currently low until the dataset is upgraded.

## Update (2026-07-22) — real ≈1M+ dataset swapped in
The interim substitute above has been replaced with `tracks_features.csv` (1,204,025 unique
tracks, no duplicate ids) — a genuinely ≈1M+ set, satisfying ADR-0004 as originally written; no
further scope deviation. Cumulative coverage against brink-dev's real `Track` rows is now
**67/551 matched (12.2%)** (up from 4.1%), combining this dataset's 55 new matches with the 14
already matched by the earlier interim file — `ingest_kaggle.py` never un-matches a track just
because a newer file doesn't happen to contain it.

This also surfaced and fixed two real issues, worth recording:
- **Landing every raw Kaggle row into `bronze.kaggle_tracks_raw` doesn't scale.** At ~1.2M rows
  this filled `brink-dev`'s disk and caused a multi-day outage. `ingest_kaggle.py` now only lands
  the rows that actually matched a `Track` (currently 67, not 1.2M) — the CSV file itself remains
  the full archive (T34 reads it directly for training), so nothing is lost by not duplicating the
  other 99.99% of it into the database too.
- **Coverage reporting was accidentally per-run, not cumulative.** The tool used to report only
  the current run's match count, which would understate true coverage once more than one dataset
  has ever been ingested (ADR-0004 requires honest reporting). It now always counts every
  `kaggleMatched = true` row in the database, regardless of which run set it.

New dataset's schema differs from the old one: id column is `id` (not `track_id`), and it has no
`popularity` column (harmless — `Track.popularity` always came from live Spotify data, not
Kaggle).

## Notes
Branch off `develop` as `feat/T31-kaggle-join`; one PR back into `develop` (never `main`). Owner: Jonah (analytics).
