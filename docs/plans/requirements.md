# Brink — Requirements & Traceability

The catalog of requirement IDs (`AUTH-*`, `BE-*`, …) and the **requirement → ticket** map. This replaces the old `brink-spec-design.md`: decisions now live in [`docs/decisions/`](../decisions/), the data model in [`backend/app/models.py`](../../backend/app/models.py) (SQLModel), and the implementation plan in [`tickets/`](tickets/). This file is the glue that proves the proposal's scope is covered.

**Status:** ✅ done · ◧ partially done (remainder tracked in the noted ticket) · ◻ backlog · **†** = original spec text superseded by a later decision (see [Superseded](#superseded-spec-text)).

## Layer 1 — Identity & Auth (AUTH)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| AUTH-1 | Spotify login via Supabase provider; first login creates/links a `public.User`. | T02 (browser), T09 (server-side) | ✅ |
| AUTH-2 | Capture + encrypt the Spotify refresh token server-side in `SpotifyToken`. | T02 (browser), T09 (server-side callback) | ✅ |
| AUTH-3 † | Email signup for handle accounts — now **email + password** server-side (was magic-link/OTP), per [ADR-0015](../decisions/adr/0015-email-password-auth.md): `/auth/signup` + `/auth/login-email`, confirmations ON, IP+email rate-limited. | T03 | ✅ |
| AUTH-4 | Every `/api/*` mutation verifies the Supabase JWT. | T02 + every API ticket (ADR-0007); T09 (session cookie) | ✅ base |
| AUTH-5 | Server owns Spotify token refresh for the snapshot job. | T22 | ✅ |
| AUTH-6 | Handle accounts work fully except Spotify-derived stats ("link Spotify"). | T03, T44 | ✅ (T03 gives the email/password front door; a handle user can post/react/comment/follow, and every Spotify surface degrades to empty states + a "link Spotify" prompt on the profile from T44. *Linking* Spotify to an existing email account is a stated follow-up.) |

## Layer 2 — Backend API + Data Model (BE)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| BE-1 | Supabase Postgres + schema (SQLModel/Alembic); pooled URLs in env. | T01, T05 | ✅ |
| BE-2 | Remove `apps/web/src/lib/backend.ts` (`/api/state`) + dead front-end stubs. *(satisfied by retiring the whole SPA — the entire `apps/web/` was deleted in T60, ADR-0013)* | T60 | ✅ |
| BE-3 | `POST /api/posts` — create post (manual/Spotify); upsert track. | T10 | ✅ |
| BE-4 | `GET /api/feed` — followees+self, newest, counts + viewer reaction. User search and follower/following lists make the graph discoverable. | T13, T15, T16 | ✅ |
| BE-5 | `POST/DELETE /api/posts/:id/reactions` — server-deduped toggle. | T11 | ✅ |
| BE-6 | `POST/GET /api/posts/:id/comments`. | T12 | ✅ |
| BE-7 | `POST/DELETE /api/follow/:userId` — feed respects the graph. | T13 | ✅ |
| BE-8 | `GET /api/users/:id/profile` — stats + cluster + compatibility. | T14 | ◻ |
| BE-9 | `POST /api/artist/posts` — create BTS post + optional track. | T50 | ✅ |
| BE-10 | All mutations: session-gated, validated, consistent error JSON. | every API ticket (ADR-0007) | ◻ |
| BE-11 | Connection pooling (Supabase pooler) configured. | T01, T05 | ✅ |

## Layer 3 — Spotify Integration (SP)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| SP-1 | Currently-playing endpoint + "now playing" surface. | T20 | ◻ |
| SP-2 † | Scheduled snapshot: refresh token, pull recently-played, upsert `Track`/`Play` (dedup). | T21 | ✅ |
| SP-3 | Upsert `Track` rows whenever tracks are seen. | T10 | ✅ |
| SP-4 | Graceful degradation: Spotify outage / unlinked user never breaks the app. | T20, T21 | ✅ |
| SP-5 | Respect rate limits; back off on 429; never block a request path. | T21 | ✅ |

## Layer 4 — Analytics & Data Science (AN)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| AN-1 | Ingest Kaggle audio features into a `Track`-joinable form; record coverage. | T31 | ✅ |
| AN-2 † | Per-user taste vector (standardized) + C4 genre fallback. *(now computed on read, no table)* | T33 | ◻ |
| AN-3 | K-means on Kaggle tracks; k via elbow+silhouette; persist `Cluster` + metrics. | T34 | ◻ |
| AN-4 † | Assign each user to nearest cluster. *(computed on read in the Python API; `User.clusterId` dropped)* | T33, T14 | ◻ |
| AN-5 † | Compatibility = cosine of full taste vectors. *(computed on read in the Python API; no pairwise table)* | T35 | ◻ |
| AN-6 | Popularity regression; persist R²/RMSE/feature-importances. | T36 | ◻ |
| AN-7 † | Aggregations: top tracks/genres/artists, streak, 30-day totals. *(computed live in the Python API, no `UserStats` table)* | T44, T14 | ◧ (T44: top **tracks/artists**, streak, 30-day totals done live over `Play` in `app/stats.py`; top **genres** deferred to T14, needs the T31 Kaggle genre join) |
| AN-8 | Pipeline idempotent + re-runnable; logs coverage/k/silhouette/R²/RMSE. | T30, T38 | ◻ |
| AN-9 † | Analytics UI on real model data; no hardcoded constants. *(reads metrics/clusters + on-read values)* | T45 | ◻ |

## Layer 5 — Frontend / UX-UI (UI)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| UI-1 | Post composer with Spotify catalog search → publish. | T40 | ✅ |
| UI-2 | Feed reads `/api/feed`; manually shared song cards, plus the behind-the-scenes posts of the artists you follow (interleaved newest-first, with like/comment controls). *(feed is manual-only — auto Spotify cards dropped per [ADR-0014](../decisions/adr/0014-feed-manual-posts-listening-summary.md); listening surfaces on the profile, not the feed; T47 added the app-shell nav — feed/profile/artist/logout links; T049 added followed artists' posts)* | T41, T47, T049 | ✅ |
| UI-3 | Reactions call BE-5; counts reflect server truth. | T41 | ✅ |
| UI-4 | Comments become real input + list. | T42 | ✅ |
| UI-5 | Follow/unfollow buttons + follower counts/lists + searchable profiles, including artist profile content. | T43, T46, T54, T16 | ✅ |
| UI-6 | Profile renders stats + cluster + compatibility; link-Spotify prompt. | T44, T14 | ◧ (T44: live listening **stats** + link-Spotify prompt done; **cluster + compatibility** deferred to T14, blocked on analytics) |
| UI-7 | Analytics page renders real metrics/clusters; remove `CLUSTER_POINTS`. | T45 | ◻ |
| UI-8 | Predict folded into Analytics; delete fabricated page/route. | T45 | ◻ |
| UI-9 | Loading/empty/error states; no silent mock fallback. | T41, T44, T60 | ✅ (the live Jinja pages render real empty/error states — feed, profile — and the mock-fallback SPA was deleted in T60) |
| UI-10 | "Now playing" indicator on profile + feed. | T20, T44 | ◧ (T44: own-profile badge done via me-scoped T20; **feed** badge + **other users'** now-playing need a new per-user endpoint — follow-up) |
| UI-11 | Editable profile: user bio + profile-picture upload. | T048 | ✅ |

## Layer 6 — Artist BTS Portal & Media (MEDIA)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| MEDIA-1 | Supabase Storage private bucket + signed upload URL (service role). | T50 | ✅ |
| MEDIA-2 | Upload UI: ≤10 MB + JPEG/PNG validation (client+server); progress/error. *(T53 made the uploaded images actually display — signed read URLs for the private bucket; T57 hides the caption box until an image is picked, since a post always needs one)* | T51, T53, T57 | ✅ |
| MEDIA-3 | Create `ArtistPost` with Storage URL + optional linked track. | T50 | ✅ |
| MEDIA-4 | Per-post engagement analytics shown to the artist. | T52, T54 | ✅ (reaction + comment counts, owner-only on artist profiles; view count deferred) |
| MEDIA-5 | ≥98% upload success across 5 file types up to 10 MB. | T51, T53 | ◧ (T53 verified the storage round-trip live on brink-dev: service-role upload → signed read URL → 200 with matching bytes, unsigned GET 400; the browser-upload half + the 5-file-type success-rate measurement remain) |
| MEDIA-6 | Self-serve artist designation in-app (no DB edit) — become an artist from your own profile. | T55, T56 | ✅ (`POST /api/me/become-artist` sets `isArtist` on the authenticated caller; own-profile "Become an artist" button; one-way, self-serve per ADR-0008. T56 polished the button: readable ghost buttons, top-right placement, "cannot be undone" confirmation) |

## Layer 7 — Infrastructure & Scheduling (INFRA)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| INFRA-1 † | Vercel project: SPA + `/api/*` rewrite to Render; env vars set, no secrets in repo. | T01, T07 | ✅ |
| INFRA-2 | Supabase provisioned; pooled URLs; migrations in CI; Data API disabled. | T01 | ✅ |
| INFRA-3 † | Snapshot trigger on a fixed cadence. *(GitHub Actions, not Vercel Cron)* | T21 | ✅ |
| INFRA-4 | GitHub Actions runs the Python pipeline against Supabase. | T30, T38 | ◻ |
| INFRA-5 | Secret hygiene: `.gitignore` enforced; secrets in env only. | T00 | ✅ |

## Layer 8 — Data Sources & Seeding (DATA)
| ID | Acceptance | Ticket(s) | Status |
|----|------------|-----------|--------|
| DATA-1 | Load Kaggle audio-feature set; document source; join on `track_id`. | T31 | ✅ |
| DATA-2 | Seed ~100–200 synthetic users (genre-coherent personas). | T32 | ◻ |
| DATA-3 | Synthetic users disclosed; never inflate real-user metrics. | T32 | ◻ |
| DATA-4 | Retire `mocks/*` from production paths once live. *(the whole SPA — mocks included — was deleted in T60)* | T60 | ✅ |

## Tickets without a legacy requirement ID
- **T39** — analytics schema migration (`ModelArtifact` + medallion bronze/silver/gold). Decision-driven (ADR-0003 / ADR-0009), no original spec req.
- **T37** — Alembic schema reflection (`include_schemas` + guards) so autogenerate sees the medallion schemas. Tooling follow-up to T39 (ADR-0009), no spec req.
- **T23** — snapshot-500 remediation: flush each upserted Track before its Play (FK insert-ordering) + guard token decryption so an unreadable token degrades to None. Production bug fix on T21/T22, no spec req.
- **T62** — FK-ordering hardening: enforce foreign keys in the shared test fixture, fix the posts endpoint's parent-before-child insert, correct the Render deploy-branch doc. Follow-up to T23, no spec req.
- **T61** — test sweep + k6 + cross-browser E2E. Completed the repeatable QA gate: backend API surface inventory, analytics pytest in CI-safe mode, k6 script, and `docs/qa-checklist.md` for manual browser/load/success-metric evidence. Maps to proposal §6/§11 below.

## Success-metric traceability (proposal §11)
| Proposal metric | Met by |
|-----------------|--------|
| Spotify OAuth ≥ 95% | AUTH-1, SP-* |
| Upload success ≥ 98% | MEDIA-5 (T51) |
| 6/6 core features working | BE-3..8, UI-1..6 |
| Real ML (clustering + regression) | AN-3, AN-5, AN-6 |
| Load test 5 concurrent users | T61 — k6 script and thresholds ready; live run is an owner-run release gate |

## Superseded spec text
The old `brink-spec-design.md` is **retired**; these acceptance criteria (flagged † above) evolved after it was written — defer to the ADRs:
- **INFRA-1** — original spec assumed Vercel serverless (`api/`) as the backend. ADR-0010 moved the API to FastAPI on Render; then **T60 retired the Vercel SPA entirely** ([ADR-0013](../decisions/adr/0013-python-frontend.md)), so **Render now serves both the API and the Jinja frontend** — Vercel is no longer used ([ADR-0010](../decisions/adr/0010-fastapi-render-backend.md)).
- **AN-2/4/5/7/9** — per-user analytics are computed **on read in the API** (written when the backend was TypeScript; since ADR-0010 that means the FastAPI/Python app), not materialized; `UserStats`/`TasteVector`/`Compatibility` tables and `User.clusterId` are dropped, `ModelArtifact` added ([ADR-0003](../decisions/adr/0003-analytics-runtime.md), [ADR-0009](../decisions/adr/0009-medallion-layering.md)).
- **SP-2 / INFRA-3** — snapshot is triggered by **GitHub Actions**, not Vercel Cron ([ADR-0006](../decisions/adr/0006-scheduling.md)).
- **AUTH-3** — the front door is **email + password** (not the spec's magic-link/OTP), server-side per [ADR-0015](../decisions/adr/0015-email-password-auth.md); the handle stays **auto-derived** (no custom-handle field on the signup form).
- Storage is **Supabase Storage** (not Cloudinary); Kaggle set is a genuine ~1M-track source (not `maharshipandya`) ([ADR-0002](../decisions/adr/0002-api-and-persistence.md), [ADR-0004](../decisions/adr/0004-analytics-data-strategy.md)).
