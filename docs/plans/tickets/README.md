# Brink — Implementation Tickets

One file per ticket. **Plain markdown — no tooling required** to read, review, or work them.

- **Backlog:** [`backlog/`](backlog/) — not yet done.
- **Latest completed:** **T96** — the "Liked by X and N others" line + reactors list.
- **Completed:** [`completed/`](completed/) — done (T00–T03, T04–T16, **T20**, **T22**, **T23**, **T30**, **T31**, **T37**, **T39**, **T40–T44**, **T46**, **T47**, **T048**, **T049**, **T50–T57**, **T60**, **T62–T64**, T70–T74, T77, T78, **T79**, **T80–T84**, **T90–T93**, **T96**). **T03** is the email + password front door for non-Spotify accounts ([ADR-0015](../decisions/adr/0015-email-password-auth.md), superseding ADR-0005's OTP choice): `/auth/signup` + `/auth/login-email` + `/auth/confirm`, confirmations ON, first IP+email rate limiting, CSRF — satisfies AUTH-3/AUTH-6. **T15/T16/T46** are user discovery end-to-end: user search plus follower/following list endpoints and profile links, so follow no longer depends on hand-typing `/u/{handle}`. **T47** is the authenticated nav — signed-in pages now link Feed / My profile / Artist studio (artists only) / Log out. **T53 + T54** make artist posts visible to audiences: signed READ urls for the private bucket plus an "Artist posts" section on artist profiles with reactions/comments and owner-only engagement totals. **T55** adds the missing in-app path to *become* an artist — `POST /api/me/become-artist` + a "Become an artist" button on your own profile — so the `isArtist` flag no longer needs a hand-edit in the database (new **MEDIA-6**). **T56** polishes that button: readable ghost buttons (fixes light-on-light), top-right placement, and a "cannot be undone" confirmation before the one-way flip. **T80** hardens the shared button system so bare buttons stay readable, moves the own-profile artist action into a visible responsive action row, and adds visible conversion failure feedback. **T81** adds accessible composer/comment feedback states, **T82** hardens responsive profile/listening layouts, **T83** polishes form controls and empty states, and **T84** prevents optional profile enrichments from turning `/u/{handle}` into a 500. **T57** hides the artist upload caption box until an image is picked (a post always needs an image, so a caption-first UI was misleading). **T049** puts the behind-the-scenes posts of the artists you follow into the feed, interleaved newest-first with song posts and with working like/comment controls (reuses the T52 engagement API + T54 artist card). **T048** makes the profile editable — a new `User.bio` column + three `/api/me` endpoints (`PATCH /profile`, `POST /avatar/sign-upload`, `POST /avatar`) behind an own-profile "Edit profile" form, so any user can set a bio and upload a profile picture to a public `avatars` bucket (new **UI-11**; owner must create the `avatars` bucket + run the migration). **T63** removed the dead browser `capture-spotify` token endpoint; server-side `/auth/callback` remains the only live Spotify-token capture path. **T64** keeps the free-tier Render service awake (10-min `keepalive.yml` health ping; activates from `main` at the next release). **T79** is the 2026-07-15 coherence sweep: four review reports landed (`docs/plans/reviews/2026-07-15-*.md`), easy doc drift fixed, T75/T76 obsoleted, and the **enablement wave** filed (T03 rewrite, T15, T16, T46, T47, T53, T54, T63 — see below). **T30** scaffolded the `analytics/` `uv` package + `db.py` Postgres access (AN-8/INFRA-4 stay partial pending T38's GitHub Actions workflow). **T31** joined a Kaggle audio-feature set onto `Track` (bronze → silver, ADR-0009); ran against a temporary ~114k dataset substitute rather than ADR-0004's ≈1M+ set (disclosed in its Outcome note, not an ADR change) — coverage 14/343 (4.1%) — unblocks **T32**. **T60 retired the React/Vite SPA** (`apps/web/` deleted, ADR-0013) — the frontend is now solely the Jinja/HTMX pages served by the FastAPI backend. **The Vercel project was decommissioned + disconnected from the repo on 2026-07-16** (its failing PR check is gone); the only leftover owner step is dropping the now-unused `web` branch-protection check. **T44 (profile listening summary)** ships the ADR-0014 listening surface (top tracks/artists, recent, streak, 30-day, own-profile now-playing, link-Spotify prompt); the analytics half (cluster/compat/genres) is deferred to the slimmed **T14**. The FastAPI/Render migration is complete; the legacy TS backend is removed. T70–T78 are the 2026-07-02 code-review remediation wave. **T10 (posts API) is the first social-API feature — its merge unblocks the frontend social UI and the rest of the backend social endpoints.** T90–T93 are the developer-tooling wave: the `get-me-started` session-warmup skill, the `docs-sync` CI gate that enforces "docs in the same PR," the `close-out` skill that runs the ticket close-out ritual **pre-merge** (folded into the feature PR, per T93), and the `close-session` end-of-session skill (final validation + branch cleanup + handoff).

## How these relate to the rest of the docs

`docs/decisions/` (the ADRs) is the **source of truth**. These tickets are *derived from* the ADRs and the spec — when an ADR changes, the tickets follow. Each ticket cites its requirement IDs (`AUTH-*`, `BE-*`, …) and the ADRs it implements.

This directory **supersedes** the old single-file `2026-06-22-brink-implementation-tickets.md`.

**T61 is completed:** the release QA gate now includes backend API route inventory coverage,
analytics pytest in CI-safe mode, a 5-user k6 script, and `docs/qa-checklist.md` for manual
browser/load/success-metric evidence.

## Reading a ticket

Each file has YAML frontmatter + sections:

- **frontmatter** — `status`, `priority`, `complexity`, `category`, `owner`, `tags`, `blocked_by`, `blocks`. `owner` is the default reviewer/assignee by code area: **Andrea** (backend — `backend/`, auth, Spotify, DB), **Jonah** (analytics — `analytics/`), **Sebastian** (frontend — the Jinja/HTMX pages under `backend/app/templates|static|routers/pages.py`; the `apps/web/` SPA was retired in T60).
- **Rationale / Summary** — why it exists, what it does.
- **Source** — requirement IDs + ADRs.
- **Scope (In / Out)** — explicit boundaries.
- **Validation & authz** — the ADR-0007 layers every API ticket must cover.
- **Current State** — what already exists on `develop`.
- **Files to Create/Modify** + **Testing / Readiness checklists**.

## Numbering

`NNN` = `epic-major . ticket-minor`, so the tens digit groups by system area (gaps are intentional slack to add tickets within an epic):

| Range | Epic |
|---|---|
| `00x` | Foundation + Auth |
| `01x` | Backend social API |
| `02x` | Spotify |
| `03x` | Analytics pipeline |
| `04x` | Frontend wiring |
| `05x` | Artist portal |
| `06x` | Cleanup + QA |
| `07x` | Review remediation (from the [2026-07-02 code review](../reviews/2026-07-02-code-review-t00-t08.md)) |
| `09x` | Developer tooling / automation |

## Dependency waves

Tickets in the same wave have no inter-dependencies and can run in parallel. A ticket starts once its `blocked_by` are merged.

| Wave | Tickets |
|---|---|
| **0 (ready)** | ~~`003`~~ ✅ ~~`030`~~ ✅ ~~`050`~~ ✅ |
| 1 | ~~`021`~~ ✅ ~~`031`~~ ✅ ~~`040`~~ ✅ ~~`051`~~ ✅ |
| 2 | `032` `034` `036` ~~`041`~~ ✅ ~~`042`~~ ✅ ~~`043`~~ ✅ ~~`052`~~ ✅ |
| 3 | `033` `038` `045` |
| 4 | `035` |
| 5 | `014` |
| 6 | ~~`044`~~ ✅ |
| 7 | ~~`060`~~ ✅ |
| 8 | ~~`061`~~ ✅ |

### Enablement wave (2026-07-15) — frontend doors for shipped backend features

The [2026-07-15 reviews](../reviews/) found the backend ahead of the frontend (features exist but
no page reaches them) plus one broken surface (artist images). Filed in T79:

| Ticket | What | Blocked by |
|---|---|---|
| ~~`047`~~ ✅ | authenticated nav + logout link | — |
| ~~`015`~~ ✅ | user search API | — |
| ~~`046`~~ ✅ | user search UI (the "find people" box) | ~~`015`~~ ✅, ~~`047`~~ ✅ |
| ~~`016`~~ ✅ | follower/following lists | — |
| ~~`053`~~ ✅ | signed READ urls (artist images can't display today) | — |
| ~~`054`~~ ✅ | audience view of artist posts + T52 engagement UI | ~~`053`~~ ✅ |
| ~~`063`~~ ✅ | retire the dead capture-spotify endpoint | — |
| ~~`003`~~ ✅ | (rewritten) email+password signup/login | — |

**Ready to start now** (all `blocked_by` merged, as of T79):
- No remaining enablement-wave blockers; `032` is ready for Jonah and analytics work, while T14 remains gated on T33/T35.
- **Done:** `003` — email + password signup/login (ADR-0015). `/auth/signup` +
  `/auth/login-email` + `/auth/confirm`, confirmations ON, first IP+email rate limiting, CSRF;
  reuses the T09 session cookie + `get_or_create_user`. Non-Spotify accounts now have a front door.
- **Done:** `015` — user search API (`GET /api/users/search?q=`, login-gated + rate-limited,
  ILIKE on handle/display name, cap 20).
- **Done:** `047` — authenticated nav + logout link. Every page route passes `viewer`;
  `base.html` renders the in-app nav (Feed / My profile / Artist studio / Log out) when signed
  in.
- **Done:** `046` — user search UI. The signed-in nav now has a "Find people" box that calls the
  T15 API and renders `/u/{handle}` profile links, making follow discoverable without pasted URLs.
- **Done:** `016` — follower/following lists. The users API returns capped follower/following DTOs,
  and profile counts link to server-rendered social-graph lists.
- **Done:** `053` — signed READ urls for artist images (`create_signed_read_url` +
  the `/artist` page signs each stored path; verified live on brink-dev).
- **Done:** `054` — audience artist posts. Artist profiles now render signed image posts with
  public reaction/comment controls and owner-only engagement totals, using the existing T52 APIs.
- **Done:** `063` — retired the dead browser Spotify-token capture endpoint. The server-side
  callback path remains the only live Spotify-token capture path.
- **Done:** `030` — analytics scaffold + DB access (Jonah).
- **Done:** `031` — Kaggle ingest + Track join (Jonah). Ran against a temporary ~114k dataset
  substitute, disclosed in the ticket's Outcome note (ADR-0004 calls for ≈1M+; not an ADR change).
  Unblocks `032` (seed synthetic users), now ready to start — both its blockers (`030`, `031`) are
  merged.
- **Done (with caveats):** `051` — artist upload UI (Sebastian). Built the `/artist` page + upload flow; the real Storage upload + private-image read URL still need a real environment / a T50 decision.
- **Done:** **`040` — composer + Spotify catalog search (Sebastian + Andrea).** `GET /api/search` (client-credentials) + a composer on the feed that publishes via `POST /api/posts`.
- **Done:** `041` — feed + live reactions, `042` — comments UI (Sebastian) — the feed page reuses `build_feed()` and reacts/comments via the T11/T12 APIs from the browser.
- **`009` (server-side Spotify login) done** — the ADR-0013 Jinja shell (PR #60) merged and this landed on top; the Python frontend can now sign users in and gate `/feed`.

### UI hardening wave (2026-07-22) — non-analytics polish work

The Impeccable UI audit found the T56 ghost-button contrast fix present on `develop`, but also found
follow-up UI quality gaps: the base button class is not safe by default, the "Become an artist" action
is easy to miss, interactive controls need clearer keyboard/loading/error states, profile/listening
layouts need mobile hardening, and forms/empty states need consistent polish.

| Ticket | What | Blocked by |
|---|---|---|
| ~~`080`~~ ✅ | button system + visible profile artist action | — |
| ~~`081`~~ ✅ | interaction feedback + keyboard accessibility pass | — |
| ~~`082`~~ ✅ | responsive profile + listening layouts | — |
| ~~`083`~~ ✅ | form controls + empty-state polish | — |
| ~~`084`~~ ✅ | profile render fallbacks for optional enrichment failures | — |

| ~~`085`~~ ✅ | static asset cache busting + revalidation | — |
| ~~`086`~~ ✅ | edit-profile disclosure state | — |

The 2026-07-22 UI hardening wave is complete, including T85's cache fix and T86's disclosure fix.

The wave numbers below are *dependency depth*, not live status — a ticket is startable as soon as its `blocked_by` are merged, which is what the "Ready to start now" list above reflects. Update that list whenever a wave of blockers merges.

Critical path: `039 → 034 → 033 → 035 → 014 → 044` (the analytics-to-profile spine). **Note (2026-07-15):** T44's *listening* half was decoupled from this spine and shipped ahead of it (ADR-0014 + the T44/T14 re-scope) — it needs only `Play` data (T21) + now-playing (T20). What still runs down this spine is the T14 analytics layer (cluster/compatibility/genres) that later augments the profile.

### Review-remediation wave (2026-07-02) — `070`–`078`

A full code review of the T00–T08 surface ([findings report](../reviews/2026-07-02-code-review-t00-t08.md))
produced nine remediation tickets. Each ticket cites its finding IDs (H*/MB*/MF*/MI*/L*) from the
report, which is the traceability root.

| Done ✅ | Remaining |
|---|---|
| `070` `071` `072` `073` `074` `077` `078` | none — `075` and `076` were marked **Obsolete** in T79 (their target files were the `apps/web/` SPA, deleted in T60; the surviving idea is `063`) |

### Backend migration spine (TS/Vercel → FastAPI/Render) — ✅ complete

Per [ADR-0010](../../decisions/adr/0010-fastapi-render-backend.md), the backend moved from
TypeScript/Vercel to FastAPI/Python on Render. This ran as a sequential chain, now finished:

`004 → 005 → 006 → 007 → 008` (all done)

`004` scaffold · `005` SQLModel + Alembic · `006` auth/crypto port · `007` Render deploy + Vercel
cutover · `008` retire the TS backend + doc sync. The FastAPI backend is live on Render and the
legacy TS `api/` is removed. The social-API tickets (`010`–`014`, `050`, `052`) target the FastAPI
pattern (`backend/app/...`).

## Working a ticket

Per `CLAUDE.md`: branch off `develop` as `<type>/T<NN>-<slug>`, **one ticket = one PR into `develop`** (never `main`), TDD with a failing test first. The owner of the touched area (Andrea = backend, Sebastian = the Jinja frontend in `backend/app/`, Jonah = analytics) is the default reviewer.

> The `.tdd/` directory (if present) is an optional local tooling workspace for the maintainer and is gitignored — it is **not** the source of truth. These files are.
