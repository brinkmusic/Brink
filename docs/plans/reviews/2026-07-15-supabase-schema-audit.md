# Supabase Schema Audit — brink-dev

**Date:** 2026-07-15
**Scope:** Full inventory of every schema and table in the live `brink-dev` Supabase Postgres
database, classified as ours vs. Supabase-internal and useful vs. dead weight.
**Method:** Read-only only. Queries against `information_schema` / `pg_catalog` plus
`SELECT count(*)` per table, run through the backend's Python environment against `DIRECT_URL`
(port 5432). No writes, no schema changes, no secrets printed. `alembic check` was run (it is a
read-only drift check).

---

## Plain-English primer (for the owner)

- **What is a schema?** A schema is just a named folder *inside* one database that groups related
  tables together, so two tables can share a name if they live in different folders. Our database
  has both our own folders and folders that Supabase created and manages for itself.
- **Why the bronze / silver / gold folders?** This is a standard data-engineering layout called the
  "medallion" pattern (our ADR-0009 / ticket T39). Think of it as a kitchen: **bronze** is the raw
  groceries exactly as they arrived from Spotify/Kaggle (untouched, nothing lost); **silver** is the
  cleaned, chopped ingredients (our tidy `Track` and `Play` tables); **gold** is the finished dish —
  the analytics results the app actually serves (music-taste clusters and model outputs). Raw →
  cleaned → served. It keeps the messy source data separate from the polished data the app reads.
- **`public`** is the default folder and holds our everyday social/login tables (users, posts,
  follows, etc.).

---

## 1. All schemas found

| Schema | Ours or Supabase | One-line purpose |
|---|---|---|
| `public` | **Ours** | Default folder — social + auth-link tables (users, posts, reactions, follows, artist posts, rate-limit log). |
| `bronze` | **Ours** | Raw landing zone — untouched Spotify/Kaggle payloads as they arrived (T39). |
| `silver` | **Ours** | Cleaned, conformed data — the `Track` and `Play` tables (T39). |
| `gold` | **Ours** | Curated analytics outputs the app reads (clusters, model metrics/artifacts) (T39). |
| `auth` | Supabase-internal | Supabase Auth — user identities, sessions, refresh tokens. Platform-managed. |
| `storage` | Supabase-internal | Supabase Storage — buckets + object metadata (our `artist-images` bucket lives here). Platform-managed. |
| `realtime` | Supabase-internal | Supabase Realtime — websocket/change-broadcast bookkeeping. Platform-managed. |
| `vault` | Supabase-internal | Supabase Vault — encrypted secret storage. Platform-managed. |
| `extensions` | Supabase-internal | Home for installed Postgres extensions (uuid, crypto, etc.). Platform-managed. |
| `graphql` / `graphql_public` | Supabase-internal | Supabase's auto GraphQL layer (we don't use it — our Data API is disabled). Platform-managed. |
| `pgbouncer` | Supabase-internal | Connection-pooler bookkeeping. Platform-managed. |

**Do not touch any Supabase-internal schema.** Deleting or editing tables in them can break auth,
storage, or the whole project.

---

## 2. Our tables — full inventory with row counts

Row counts captured 2026-07-15 against `brink-dev` (a shared dev database, so counts are small).

| Schema.Table | Rows | In `models.py`? | Used by |
|---|---:|---|---|
| `public.User` | 2 | yes (`User`) | nearly every router (auth, posts, feed, follow, artist, search, snapshot…) |
| `public.SpotifyToken` | 2 | yes (`SpotifyToken`) | `routers/auth.py`, `routers/snapshot.py`, `spotify.py` |
| `public.Post` | 3 | yes (`Post`) | `routers/posts.py`, `feed.py`, `reactions.py`, `comments.py`, `pages.py` |
| `public.Reaction` | 0 | yes (`Reaction`) | `routers/reactions.py`, `feed.py` |
| `public.Comment` | 0 | yes (`Comment`) | `routers/comments.py`, `feed.py` |
| `public.Follow` | 1 | yes (`Follow`) | `routers/follow.py`, `feed.py`, `pages.py` |
| `public.ArtistPost` | 0 | yes (`ArtistPost`) | `routers/artist.py`, `pages.py` |
| `public.ArtistReaction` | 0 | yes (`ArtistReaction`) | `routers/artist.py` |
| `public.ArtistComment` | 0 | yes (`ArtistComment`) | `routers/artist.py` |
| `public.RateLimitHit` | 24 | yes (`RateLimitHit`) | `rate_limit.py` (spam guard for write endpoints) |
| `silver.Track` | 364 | yes (`Track`) | posts/feed/snapshot (song catalog) |
| `silver.Play` | 450 | yes (`Play`) | `routers/snapshot.py`, `stats.py` (listening history) |
| `bronze.spotify_recently_played_raw` | 66 | yes (`SpotifyRecentlyPlayedRaw`) | `routers/snapshot.py` (T21 raw landing) |
| `bronze.kaggle_tracks_raw` | 2 | yes (`KaggleTracksRaw`) | ingest job (T31, not built yet) |
| `gold.Cluster` | 0 | yes (`Cluster`) | analytics spine (T33/T35, not built yet) |
| `gold.ModelMetrics` | 0 | yes (`ModelMetrics`) | analytics spine (not built yet) |
| `gold.ModelArtifact` | 0 | yes (`ModelArtifact`) | analytics spine (not built yet) |
| `public._prisma_migrations` | 2 | no | leftover from the old Prisma stack (pre-FastAPI) |
| `public.alembic_version` | 1 | no | Alembic's own bookmark of which migration has run |

---

## 3. Classification (verdict table)

| Table | Classification | Verdict |
|---|---|---|
| `public.User` | OURS-ACTIVE | **keep** |
| `public.SpotifyToken` | OURS-ACTIVE | **keep** |
| `public.Post` | OURS-ACTIVE | **keep** |
| `public.Reaction` | OURS-ACTIVE (0 rows, live code path via reactions API) | **keep** |
| `public.Comment` | OURS-ACTIVE (0 rows, live code path via comments API) | **keep** |
| `public.Follow` | OURS-ACTIVE | **keep** |
| `public.ArtistPost` | OURS-ACTIVE (0 rows, artist portal wired) | **keep** |
| `public.ArtistReaction` | OURS-ACTIVE (0 rows, T52 engagement path) | **keep** |
| `public.ArtistComment` | OURS-ACTIVE (0 rows, T52 engagement path) | **keep** |
| `public.RateLimitHit` | OURS-ACTIVE | **keep** |
| `silver.Track` | OURS-ACTIVE | **keep** |
| `silver.Play` | OURS-ACTIVE | **keep** |
| `bronze.spotify_recently_played_raw` | OURS-ACTIVE | **keep** |
| `bronze.kaggle_tracks_raw` | OURS-EMPTY-BUT-PLANNED (2 seed rows; real ingest is T31) | **keep-empty** |
| `gold.Cluster` | OURS-EMPTY-BUT-PLANNED (analytics spine T33/T35) | **keep-empty** |
| `gold.ModelMetrics` | OURS-EMPTY-BUT-PLANNED (analytics spine) | **keep-empty** |
| `gold.ModelArtifact` | OURS-EMPTY-BUT-PLANNED (analytics spine) | **keep-empty** |
| `public._prisma_migrations` | LEGACY-BOOKKEEPING | **drop-candidate** (harmless; optional cleanup) |
| `public.alembic_version` | LEGACY-BOOKKEEPING | **keep** (Alembic needs it) |
| `auth.*`, `storage.*`, `realtime.*`, `vault.*`, `extensions.*`, `graphql*`, `pgbouncer.*` | SUPABASE-INTERNAL | **platform — don't touch** |

Note on the "0 rows" tables: several social tables (Reaction, Comment, ArtistPost, etc.) are empty
only because this is a lightly-used dev database, not because they're unused — each has a live
code path. They are **keep**, not keep-empty. "keep-empty" is reserved for the analytics tables
whose *code* doesn't exist yet (bronze Kaggle + all of gold).

---

## 4. Drift check

`cd backend && uv run alembic check` → **passes** ("No new upgrade operations detected", exit 0).
Current head: `3978f11ad4da` (T52 artist-engagement migration). This means the live database
schema and `models.py` are fully in sync — no undocumented columns, no missing tables, no drift.

---

## 5. Orphaned tables — none (only expected bookkeeping)

There are **no orphaned data tables**. Every table in `public`/`bronze`/`silver`/`gold` maps to a
model in `models.py`, except the two expected bookkeeping tables:

- **`public.alembic_version`** — this is Alembic's own single-row bookmark of "which migration has
  been applied." It is required; leave it.
- **`public._prisma_migrations`** — leftover from the retired Prisma stack. Alembic already ignores
  it (`alembic/env.py`). It is harmless (2 rows of old migration history) and **safe to drop**.

The old dropped models **`UserStats`, `TasteVector`, `Compatibility`** (and `User.clusterId`) that
T39 removed are **confirmed gone** from the live database — they appear only inside migration files
and comments, not as real tables. No cleanup needed there.

### If you want to drop `_prisma_migrations`

Per project convention (schema changes go through Alembic, hand-written where autogenerate can't
help), the clean way is a tiny hand-written migration:

```python
def upgrade():
    op.execute('DROP TABLE IF EXISTS public."_prisma_migrations"')

def downgrade():
    pass  # legacy table; not recreated
```

This is optional and cosmetic — it removes nothing the app uses. It's fine to leave it forever.

---

## Bottom line

The database is clean and well-organized. Nineteen of our tables all trace to `models.py`, the
medallion bronze/silver/gold layout is exactly as ADR-0009/T39 designed, `alembic check` reports
zero drift, and there are **no surprise/orphaned tables** — just the one harmless legacy Prisma
bookkeeping table you can optionally sweep away later. Everything else in the dashboard that isn't
in our four folders is Supabase's own platform plumbing and should be left alone.
