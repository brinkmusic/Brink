# Brink — Requirements & Traceability

The catalog of requirement IDs (`AUTH-*`, `BE-*`, …) and the **requirement → ticket** map. This replaces the old `brink-spec-design.md`: decisions now live in [`docs/decisions/`](../decisions/), the data model in [`backend/app/models.py`](../../backend/app/models.py) (SQLModel), and the implementation plan in [`tickets/`](tickets/). This file is the glue that proves the proposal's scope is covered.

**Status:** ✅ done · ◻ backlog · **†** = original spec text superseded by a later decision (see [Superseded](#superseded-spec-text)).

## Layer 1 — Identity & Auth (AUTH)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| AUTH-1 | Spotify login via Supabase provider; first login creates/links a `public.User`. | T02 | ✅ |
| AUTH-2 | Capture + encrypt the Spotify refresh token server-side in `SpotifyToken`. | T02 | ✅ |
| AUTH-3 † | Passwordless email magic-link/OTP signup (Supabase sends mail). | T03 | ◻ |
| AUTH-4 | Every `/api/*` mutation verifies the Supabase JWT. | T02 + every API ticket (ADR-0007) | ✅ base |
| AUTH-5 | Server owns Spotify token refresh for the snapshot job. | T02 | ✅ |
| AUTH-6 | Handle accounts work fully except Spotify-derived stats ("link Spotify"). | T03, T44 | ◻ |

## Layer 2 — Backend API + Data Model (BE)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| BE-1 | Supabase Postgres + schema (SQLModel/Alembic); pooled URLs in env. | T01, T05 | ✅ |
| BE-2 | Remove `apps/web/src/lib/backend.ts` (calls `/api/state`, 404s since T08) + dead front-end stubs. | T60 | ◻ |
| BE-3 | `POST /api/posts` — create post (manual/Spotify); upsert track. | T10 | ◻ |
| BE-4 | `GET /api/feed` — followees+self, newest, counts + viewer reaction. | T13 | ◻ |
| BE-5 | `POST/DELETE /api/posts/:id/reactions` — server-deduped toggle. | T11 | ◻ |
| BE-6 | `POST/GET /api/posts/:id/comments`. | T12 | ◻ |
| BE-7 | `POST/DELETE /api/follow/:userId` — feed respects the graph. | T13 | ◻ |
| BE-8 | `GET /api/users/:id/profile` — stats + cluster + compatibility. | T14 | ◻ |
| BE-9 | `POST /api/artist/posts` — create BTS post + optional track. | T50 | ◻ |
| BE-10 | All mutations: session-gated, validated, consistent error JSON. | every API ticket (ADR-0007) | ◻ |
| BE-11 | Connection pooling (Supabase pooler) configured. | T01, T05 | ✅ |

## Layer 3 — Spotify Integration (SP)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| SP-1 | Currently-playing endpoint + "now playing" surface. | T20 | ◻ |
| SP-2 † | Scheduled snapshot: refresh token, pull recently-played, upsert `Track`/`Play` (dedup). | T21 | ◻ |
| SP-3 | Upsert `Track` rows whenever tracks are seen. | T10 | ◻ |
| SP-4 | Graceful degradation: Spotify outage / unlinked user never breaks the app. | T20, T21 | ◻ |
| SP-5 | Respect rate limits; back off on 429; never block a request path. | T21 | ◻ |

## Layer 4 — Analytics & Data Science (AN)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| AN-1 | Ingest Kaggle audio features into a `Track`-joinable form; record coverage. | T31 | ◻ |
| AN-2 † | Per-user taste vector (standardized) + C4 genre fallback. *(now computed on read, no table)* | T33 | ◻ |
| AN-3 | K-means on Kaggle tracks; k via elbow+silhouette; persist `Cluster` + metrics. | T34 | ◻ |
| AN-4 † | Assign each user to nearest cluster. *(on-read TS; `User.clusterId` dropped)* | T33, T14 | ◻ |
| AN-5 † | Compatibility = cosine of full taste vectors. *(on-read TS; no pairwise table)* | T35 | ◻ |
| AN-6 | Popularity regression; persist R²/RMSE/feature-importances. | T36 | ◻ |
| AN-7 † | Aggregations: top tracks/genres/artists, streak, 30-day totals. *(live TS, no `UserStats` table)* | T14 | ◻ |
| AN-8 | Pipeline idempotent + re-runnable; logs coverage/k/silhouette/R²/RMSE. | T30, T38 | ◻ |
| AN-9 † | Analytics UI on real model data; no hardcoded constants. *(reads metrics/clusters + on-read values)* | T45 | ◻ |

## Layer 5 — Frontend / UX-UI (UI)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| UI-1 | Post composer with Spotify catalog search → publish. | T40 | ◻ |
| UI-2 | Feed reads `/api/feed`; manual + Spotify cards. | T41 | ◻ |
| UI-3 | Reactions call BE-5; counts reflect server truth. | T41 | ◻ |
| UI-4 | Comments become real input + list. | T42 | ◻ |
| UI-5 | Follow/unfollow buttons + follower counts. | T43 | ◻ |
| UI-6 | Profile renders stats + cluster + compatibility; link-Spotify prompt. | T44 | ◻ |
| UI-7 | Analytics page renders real metrics/clusters; remove `CLUSTER_POINTS`. | T45 | ◻ |
| UI-8 | Predict folded into Analytics; delete fabricated page/route. | T45 | ◻ |
| UI-9 | Loading/empty/error states; no silent mock fallback. | T41, T60 | ◻ |
| UI-10 | "Now playing" indicator on profile + feed. | T20, T44 | ◻ |

## Layer 6 — Artist BTS Portal & Media (MEDIA)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| MEDIA-1 | Supabase Storage private bucket + signed upload URL (service role). | T50 | ◻ |
| MEDIA-2 | Upload UI: ≤10 MB + JPEG/PNG validation (client+server); progress/error. | T51 | ◻ |
| MEDIA-3 | Create `ArtistPost` with Storage URL + optional linked track. | T50 | ◻ |
| MEDIA-4 | Per-post engagement analytics shown to the artist. | T52 | ◻ |
| MEDIA-5 | ≥98% upload success across 5 file types up to 10 MB. | T51 | ◻ |

## Layer 7 — Infrastructure & Scheduling (INFRA)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| INFRA-1 † | Vercel project: SPA + `/api/*` rewrite to Render; env vars set, no secrets in repo. | T01, T07 | ✅ |
| INFRA-2 | Supabase provisioned; pooled URLs; migrations in CI; Data API disabled. | T01 | ✅ |
| INFRA-3 † | Snapshot trigger on a fixed cadence. *(GitHub Actions, not Vercel Cron)* | T21 | ◻ |
| INFRA-4 | GitHub Actions runs the Python pipeline against Supabase. | T30, T38 | ◻ |
| INFRA-5 | Secret hygiene: `.gitignore` enforced; secrets in env only. | T00 | ✅ |

## Layer 8 — Data Sources & Seeding (DATA)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| DATA-1 | Load Kaggle audio-feature set; document source; join on `track_id`. | T31 | ◻ |
| DATA-2 | Seed ~100–200 synthetic users (genre-coherent personas). | T32 | ◻ |
| DATA-3 | Synthetic users disclosed; never inflate real-user metrics. | T32 | ◻ |
| DATA-4 | Retire `mocks/*` from production paths once live. | T60 | ◻ |

## Tickets without a legacy requirement ID
- **T39** — analytics schema migration (`ModelArtifact` + medallion bronze/silver/gold). Decision-driven (ADR-0003 / ADR-0009), no original spec req.
- **T61** — test sweep + k6 + cross-browser E2E. Maps to proposal §6/§11 below.

## Success-metric traceability (proposal §11)
| Proposal metric | Met by |
|-----------------|--------|
| Spotify OAuth ≥ 95% | AUTH-1, SP-* |
| Upload success ≥ 98% | MEDIA-5 (T51) |
| 6/6 core features working | BE-3..8, UI-1..6 |
| Real ML (clustering + regression) | AN-3, AN-5, AN-6 |
| Load test 5 concurrent users | T61 |

## Superseded spec text
The old `brink-spec-design.md` is **retired**; these acceptance criteria (flagged † above) evolved after it was written — defer to the ADRs:
- **INFRA-1** — original spec assumed Vercel serverless (`api/`) as the backend. ADR-0010 moved the API to FastAPI on Render; Vercel now serves only the SPA and rewrites `/api/*` to the Render URL ([ADR-0010](../decisions/adr/0010-fastapi-render-backend.md)).
- **AN-2/4/5/7/9** — per-user analytics are computed **on read in TS**, not materialized; `UserStats`/`TasteVector`/`Compatibility` tables and `User.clusterId` are dropped, `ModelArtifact` added ([ADR-0003](../decisions/adr/0003-analytics-runtime.md), [ADR-0009](../decisions/adr/0009-medallion-layering.md)).
- **SP-2 / INFRA-3** — snapshot is triggered by **GitHub Actions**, not Vercel Cron ([ADR-0006](../decisions/adr/0006-scheduling.md)).
- **AUTH-3** — handle is **auto-derived**; no signup form / custom-handle flow.
- Storage is **Supabase Storage** (not Cloudinary); Kaggle set is a genuine ~1M-track source (not `maharshipandya`) ([ADR-0002](../decisions/adr/0002-api-and-persistence.md), [ADR-0004](../decisions/adr/0004-analytics-data-strategy.md)).
