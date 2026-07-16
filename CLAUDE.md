# Brink — Agent & Contributor Guide

Music-native social web app. MMA course project, team of 3, **deadline 2026-07-30**.
This file is the contract every AI agent and contributor reads first. Read it before
touching the repo.

## What Brink is

A single **FastAPI/Python app** (Render) serving both the JSON API and the **HTML frontend** (Jinja2
templates + HTMX) + **Supabase** (Postgres + Auth + Storage) + a Python/scikit-learn analytics batch
job (GitHub Actions cron).

> **Stack:** one **FastAPI / Python** app (SQLModel + Alembic) on **Render** serves **both** the
> `/api/*` JSON endpoints and the server-rendered HTML pages (Jinja2 + HTMX, in
> `backend/app/templates/` + `backend/app/routers/pages.py`); **Supabase** provides Postgres, Auth,
> and Storage. See [ADR-0010](docs/decisions/adr/0010-fastapi-render-backend.md) (backend moved here
> from an earlier TypeScript/Vercel/Prisma stack, removed in T08) and
> [ADR-0013](docs/decisions/adr/0013-python-frontend.md) (the frontend became these Python-served
> pages). **The separate React/Vite SPA (`apps/web/`) was retired in T60** — the whole app is now one
> Python codebase we can all read and defend. All work is in `backend/` (+ `analytics/`).

**Source of truth — read these before planning any work:**
- `docs/plans/requirements.md` — requirement catalog (`AUTH-*`, `BE-*`, `SP-*`, `AN-*`, `UI-*`, `MEDIA-*`, `INFRA-*`, `DATA-*`) + requirement→ticket traceability. Data model: `backend/app/models.py` (SQLModel). Decisions: `docs/decisions/`.
- `docs/plans/tickets/` — one file per ticket (`backlog/`, `completed/`), derived from the ADRs in `docs/decisions/`. Start at `docs/plans/tickets/README.md` for the dependency waves and reading guide.

## Layout

- `backend/` — **the API: FastAPI app (Python, `uv`-managed)**. App code in `backend/app/`, tests
  in `backend/tests/`, DB migrations in `backend/alembic/`.
- `backend/app/templates/` + `backend/app/static/` — the **Python frontend**: HTML pages
  (Jinja2 templates; HTMX to come) served by FastAPI, with routes in `backend/app/routers/pages.py` (ADR-0013).
- `analytics/` — Python pipeline (`uv`-managed). Created in T30.

*(The `apps/web/` React/Vite SPA was retired in T60 — [ADR-0013](docs/decisions/adr/0013-python-frontend.md).
The frontend is the Jinja/HTMX pages under `backend/app/` above.)*
- `docs/plans/` — spec + tickets (source of truth above).

## Commands

Local dev reads the root `.env` (the `brink-dev` Supabase project), so it never touches production.

```
# The whole app — one process. The FastAPI app serves BOTH the JSON API and the HTML pages
# (ADR-0013). Visit http://127.0.0.1:3001/ for the pages, /api/* for the API.
cd backend && uv run uvicorn app.main:app --reload --port 3001
```

- **Test:** `cd backend && uv run pytest` (backend). Analytics: `cd analytics && uv run pytest`.
- **Frontend** is server-rendered Jinja/HTMX in `backend/` — no separate build/lint step (the
  React/Vite SPA was retired in T60).

## Hard rules

1. **`develop` is the integration branch; `main` is production. Never push to either directly.**
   Every change goes on a branch and through a PR **into `develop`**. One ticket = one PR.
   `main` only receives `develop` via a release PR, and Render deploys production from `main`.
2. **Branches:** name them `<type>/<ticket-id>-<slug>` where type is
   `feat | fix | chore | docs | ci` (e.g. `feat/T10-posts-api`, `chore/repo-governance`).
   Branch off the latest `develop`, keep them short-lived, and **delete the branch after its PR
   merges**. Don't let a branch drift far behind `develop` — rebase or re-sync instead.
3. **Never commit secrets.** The root `.env` is git-ignored and stays that way. Secrets live only in
   that file locally and in the Render (app) / GitHub (CI + cron) env. If you ever see a secret in
   tracked files, stop and flag it.
4. **TDD (expected practice).** Write a failing test first, then minimal code to pass,
   with frequent small commits. Claude Code agents should use the `test-driven-development`
   skill; everyone else follows the same loop by hand. This is the expected workflow, not an
   automated guarantee — CI (`.github/workflows/ci.yml`) runs the backend tests (`uv run pytest`)
   and a secret scan on every PR, and is what actually blocks untested code.
   Don't execute multiple tickets at once.
5. **Don't widen scope.** Build exactly what the ticket/requirement specifies — no extra
   features, abstractions, or error handling beyond what's asked.
6. **Auth:** validate Supabase JWTs server-side via `getUser()` (no JWT secret). We own
   Spotify token refresh; tokens are encrypted at rest (AES-256-GCM, `TOKEN_ENC_KEY`).

## Working norms (expected of humans and agents)

These are expectations, not automated guarantees — they set how we work.

- **State assumptions and risks explicitly** — in the PR description and when proposing a
  plan. If you had to guess at anything, say so.
- **Stop on ambiguity.** If a ticket or requirement is underspecified or unclear, ask —
  don't invent scope, data shapes, or behavior to fill the gap. A wrong guess costs more
  than a question. (Pairs with hard rule #5.)
- **Smallest change that satisfies the ticket.** Surface follow-ups as notes; don't silently
  build them.
- **Reuse before reinventing.** Search for an existing helper before writing a new one. Shared
  logic lives in `backend/app/` (API + Jinja page routes/templates) — extend or import it; don't
  copy-paste or write a second version of something that already exists. If you find duplication,
  factor it out as part of the change.
- **Comments: explain both *what* and *why*, written for a reader new to the language/stack.**
  This repo is read by a mixed team including a non-technical owner, so code must be *followable
  by someone who doesn't already know* Python/SQLModel/FastAPI/Jinja/HTMX. This deliberately overrides
  the usual "why, not what" convention. Concretely:
  - Every file that does real work opens with a short **`WHAT THIS FILE IS`** comment (2–5 lines,
    plain English) covering its purpose and why it exists.
  - Add a brief plain-language note on each non-trivial block: what it does, why it's there, and
    what any unfamiliar syntax/concept means (e.g. foreign keys, decorators, `Optional`). Explain
    a recurring idea *once* (e.g. in a file header) rather than repeating it on every line.
  - Favor clarity over brevity — stating the *what* is expected here, not a smell. But don't
    narrate truly trivial lines, and keep comments **accurate**: a stale/wrong comment is worse
    than none, so update comments in the same change as the code.
  This is a project standard for Brink; individual contributors' global preferences don't override it.
- **Guard against regressions.** A bug fix starts with a failing test that reproduces the bug,
  then the fix. Changes to shared code (`backend/app/db.py`, `backend/app/models.py`,
  `backend/app/deps.py`) have a wide blast radius — call out in the PR what depends on them, and
  run the full suite (`cd backend && uv run pytest`).
- **Commit messages:** Conventional Commits — `type(scope): summary`
  (`feat`, `fix`, `chore`, `docs`, `ci`, `test`, `refactor`). Scope is usually the ticket id,
  e.g. `feat(T10): add posts endpoint`.
- **Keep docs in sync in the same PR.** Code and its docs change together — stale docs are a
  bug. When a PR changes behavior, update the relevant doc in the same PR:
  - Architecture/decision changes -> add or supersede an ADR in `docs/decisions/adr/`.
  - Spec/ticket scope changes -> update `docs/plans/`.
  - Commands, env, conventions, or status -> update this file (`CLAUDE.md`).
- **ADRs are append-only history.** Never rewrite or delete an accepted ADR. To change a past
  decision, write a new ADR and set the old one's status to
  `Superseded by [ADR-NNNN](NNNN-...md)`. This is *why* the log doesn't go stale: history is
  preserved, the current decision is always the latest non-superseded ADR.

## Developer skills (Claude Code)

Three committed skills (in `.claude/skills/`) bookend a unit of work. Invoke one by typing
`/<name>` in Claude Code, or just describe the situation. They're **guided checklists, not
auto-runners** — they do the steps and flag problems, but stop for your judgement and never bypass
review or push to `develop`/`main`.

The work cycle:

> **`get-me-started`** (begin session) → work a ticket → **`close-out`** (finish the *ticket*) →
> repeat → **`close-session`** (finish the *session*).

- **`get-me-started` — start of a session.** Pulls in what changed, lists open PRs, audits whether
  each kept its docs in sync with its code, and briefs you on where things stand + what's next. It
  **flags, doesn't fix.** Use it whenever you sit down or feel out of the loop ("catch me up",
  "what's ready to review", "where am I").
- **`close-out` — finishing a *ticket* (pre-merge).** The per-ticket bookkeeping: move the ticket
  `backlog → completed`, flip its `status` + the `requirements.md` rows it satisfied, sync the
  Status line below, and refresh the tickets README. Since **T93 this runs *before* merge** — the
  edits are committed onto your feature branch so they ride the **same PR** as the code (no separate
  follow-up PR). Run it as the **last step before you open/finalize a feature PR**, once the code is
  done and tests are green. Deferring to a follow-up PR is still allowed but only as a **stated**
  exception (e.g. a very large PR). Say "close out T<NN>".
- **`close-session` — end of a *session* (final validation).** The "am I safe to stop?" gate and
  bookend to `get-me-started`: runs the full backend suite (no frontend build step — the frontend
  is server-rendered Jinja), confirms the tree
  is clean and pushed and open PRs are green, prunes already-merged branches, and writes the
  handoff. Use it when wrapping up ("sign off", "I'm done", "final validation").

**Key distinction:** `close-out` is per **ticket** (its docs, folded into the feature PR);
`close-session` is per **work session** (validate + clean up + handoff). You may run `close-out`
several times in a session, `close-session` once at the end.

## Database migrations

Schema changes use **SQLModel + Alembic**: edit `backend/app/models.py`, then
`cd backend && uv run alembic revision --autogenerate -m "..."` and `uv run alembic upgrade head`.
Alembic was baselined against the live schema in T05 (stamped, not recreated), so `upgrade head`
is a no-op on the existing DB. `alembic check` reports any drift between the models and the DB.

**Medallion schemas (T39, ADR-0009).** Tables live in Postgres schemas: `silver` (`Track`, `Play`),
`gold` (`Cluster`, `ModelMetrics`, `ModelArtifact`), `bronze` (raw `*_raw` landing tables); the
social/auth tables stay in the default `public` schema. Two consequences: (1) **autogenerate runs
with schema reflection on** — `env.py` sets `include_schemas=True` (+ an `include_name` allow-list
so only our schemas are reflected, not Supabase's `auth`/`storage`, and a schema-qualified
`include_object` check), so `--autogenerate` sees the medallion tables correctly (done in **T37**;
verified with `alembic check`). (2) SQLite tests map the schemas to none via a
`schema_translate_map` in `tests/conftest.py`. A migration that **moves** a table between schemas
must use `ALTER TABLE ... SET SCHEMA` (preserves rows) — never autogenerate's drop+recreate.

## Environment

- Supabase project `brink-dev` (ref `ljzwskfhiviunmqxerwu`). Data API disabled — tables are
  reached only through the backend's ORM (SQLModel/SQLAlchemy).
- Root `.env`: `DATABASE_URL`/`DIRECT_URL` (Supabase pooler 6543/5432), `SUPABASE_URL`,
  `SUPABASE_SERVICE_ROLE_KEY`, `SPOTIFY_CLIENT_ID`/`SECRET`, `TOKEN_ENC_KEY`.
- **Getting the values (onboarding):** the `.env` file is git-ignored and never shared in the
  repo. Copy `.env.example`, then get the real secret values from the Render (app) / GitHub env or
  ask Andrea. Don't paste secrets into chat, issues, or commits.
- **Git hooks:** running `npm install` (root `package.json`'s `prepare` script) points git at
  `.githooks/` (a pre-commit secret guard). If you skipped it, run
  `git config core.hooksPath .githooks` once.

## Ownership & review (CODEOWNERS intent)

- **Andrea** — backend / API / auth / DB (`backend/`).
- **Sebastian** — frontend: the Jinja/HTMX page layer (`backend/app/templates|static|routers/pages.py`).
- **Jonah** — analytics (`analytics/`).

The owner of an area is the default reviewer for PRs touching it (every ticket also has an
`owner` in its frontmatter). **Auth and crypto changes** — `backend/app/deps.py`,
`backend/app/security/crypto.py`, `backend/app/security/supabase.py`, anything touching tokens or
`TOKEN_ENC_KEY` — are the highest-risk area, so a second review is **encouraged** where a reviewer
is available. It is **not required**, though: the area owner may self-merge them (call out in the
PR that it went in without a second review).

## Watch-outs

- Spotify `provider_token` from the browser lasts ~1h and is **not** refreshed by Supabase.
  Server/long-term Spotify access must go through our stored refresh token (snapshot job, T21).
- The DB still has a `_prisma_migrations` table (Prisma's old bookkeeping); Alembic ignores it
  (`backend/alembic/env.py`). Harmless — it can be dropped whenever.
- Status: T00–T02, T04–T08, **T70–T74, T77–T78** done — FastAPI/Render migration complete, TS
  backend removed, error envelope hardened, auth race fixed, CI hygiene done, review-remediation
  test/polish landed. **T10 (posts API) done** — `POST /api/posts` + `GET /api/posts?userId=`,
  track upsert, and the reusable Postgres-backed rate-limit helper (ADR-0011) + camelCase response
  DTOs (ADR-0012) are the first social-API precedents. **T11 (reactions) done** —
  `POST`/`DELETE /api/posts/{id}/reactions` (idempotent add / own-only remove) returning fresh
  per-type counts (`ReactionCountsOut`), reusing the T10 rate-limit + DTO patterns (satisfies
  BE-5). **T12 (comments) done** — `POST`/`GET /api/posts/{id}/comments` (both login-gated;
  create is rate-limited + trims/length-validates `body`, list returns newest-first with nested
  author DTO), satisfies BE-6. The app (API + Jinja frontend) runs on **Render**
  (`brink-xg7p.onrender.com`, `/api/health` → `db: true`), Spotify login works end-to-end. Repo:
  **`brinkmusic/Brink`** (public). The 2026-07-02 review's remaining remediation
  tickets T75/T76 were **obsoleted by T60** (they targeted the retired SPA's `apps/web/` files);
  the one surviving idea — retiring the legacy `POST /api/auth/capture-spotify` endpoint — is now
  tracked as T63. **T90–T93 (developer tooling) done** —
  the committed `get-me-started` session-warmup skill, the `close-out` ticket-close-out skill, and
  (T93) the `close-session` end-of-session skill (`.claude/skills/`); **close-out now runs
  pre-merge** — its ticket/traceability/status bookkeeping is folded into the same PR that
  implements the ticket, so no separate follow-up PR (`close-session` owns the end-of-session
  validate + branch-cleanup + handoff). Plus the **`docs-sync` CI gate**
  (`.github/workflows/docs-sync.yml`) that fails any PR changing source without touching docs
  (`no-docs` label = escape hatch). `develop` and `main` are now branch-protected: PR required, up
  to date, checks `api/secrets/docs-sync` green, admins included (the `web` check was retired with
  the SPA in T60). **T13 (follow + feed) done**
  — `POST`/`DELETE /api/follow/{userId}` (idempotent follow / own-only unfollow, rate-limited) +
  `GET /api/feed` (followees + self, newest-first, each with track, author, per-type reaction
  counts, comment count, and the viewer's own reactions; fixed 4 queries, no N+1), satisfying BE-4
  + BE-7. Its merge unblocks the follow/feed UIs (T41, T43). **Frontend (Python, ADR-0013): the
  landing page + login-gated feed shipped (#60), and T41 (feed + live reactions) done** — the feed
  page reuses the shared `build_feed()` (extracted in `backend/app/routers/feed.py`) so it matches
  `GET /api/feed`, and `backend/app/static/reactions.js` calls the T11 reactions API from the
  browser (optimistic, reconciled with server counts), satisfying UI-2/UI-3. **T42 (comments UI) done**
  — each feed post card has a comment toggle + panel that lists and adds comments via the T12 API
  (`backend/app/static/comments.js`), satisfying UI-4. **T40 (composer + catalog search) done** —
  `GET /api/search?q=` (`backend/app/routers/search.py`, login-gated + rate-limited) backed by a new
  client-credentials path in `backend/app/spotify.py` (app-level token, so handle users can search),
  plus a composer card on the feed (`backend/app/static/composer.js`) that searches, then publishes
  via `POST /api/posts`, satisfying UI-1. **T43 (follow UI) done** — a minimal profile page
  `GET /u/{handle}` (`backend/app/templates/profile.html`) with follower counts + a Follow/Unfollow
  button (`backend/app/static/follow.js` → T13 API); feed authors link to it. Full "Wrapped" stats
  are still T44 (needs T14). Satisfies UI-5. **T51 (artist upload UI) done (with caveats)** — an `/artist` page (`backend/app/templates/artist.html`) with a JPEG/PNG≤10MB upload box for artist accounts that runs the T50 signed-upload flow (`backend/app/static/artist-upload.js`); satisfies MEDIA-2. NOTE: both of T51's caveats were cleared by **T53** — the storage round-trip is verified live on brink-dev and the signed read URL now exists (see the T53 entry below). **T22 (Spotify token refresh) done** —
  `backend/app/spotify.py` `get_valid_access_token(session, user_id)` returns a fresh access token
  (reusing the stored encrypted refresh token via Spotify's token endpoint) or `None` for an
  unlinked / refresh-failed user, satisfying the real **AUTH-5** (which was mis-marked done against
  T02). This was a missing prerequisite discovered while starting T20 — both **T20 (now-playing)**
  and **T21 (snapshot)** build on it and are now genuinely unblocked. **T20 (now-playing) done** —
  `GET /api/me/now-playing` (login-gated) + `spotify.get_currently_playing`, returning the
  normalized currently-playing track or `{ data: null }` for the empty/degraded cases (nothing
  playing, no linked Spotify, Spotify error) — the backend half of SP-1/UI-10 (the surface is T44).
  **T39 (analytics contract + medallion schemas) done** — added `ModelArtifact` + bronze `*_raw`
  landing tables, moved `Track`/`Play` → `silver` and `Cluster`/`ModelMetrics` → `gold`, dropped
  the unused `UserStats`/`TasteVector`/`Compatibility` + `User.clusterId` (ADR-0003/0009). The
  migration is **hand-written and applied manually by Andrea on `brink-dev`** (SET SCHEMA preserves
  rows). This unblocks **T21** (bronze/silver now exist) and the analytics spine (033/034/036).
  **T21 (Spotify play snapshot) done** — `POST /api/snapshot` (cron-authed by `X-Cron-Secret`)
  lands each Spotify-linked user's recently-played into `bronze.spotify_recently_played_raw`, then
  conforms to silver (`upsert_track` + `Play` deduped on `userId+playedAt`); one bounded 429
  backoff; `.github/workflows/snapshot.yml` triggers it ~every 2h (satisfies SP-2/SP-4/SP-5/
  INFRA-3). **Deploy step for Andrea:** set `CRON_SECRET` on Render + add `SNAPSHOT_URL`/
  `CRON_SECRET` GitHub repo secrets, or the cron 401s. **T09 (server-side Spotify login) done** —
  server-side OAuth for the Jinja frontend: `GET /auth/login` → `/auth/callback` → `/auth/logout`
  (PKCE via Supabase; encrypted `brink_oauth` handshake cookie carrying the verifier + CSRF state;
  encrypted `brink_session` cookie holding the Supabase session). `require_user` now also reads the
  session cookie with **refresh-on-expiry** (Bearer path unchanged); the Spotify tokens are captured
  server-side in the callback. New `app/security/session.py` owns the session cookie (reuse it for
  any future gated page). Login buttons wired and `/feed` gated (anon → login), reversing PR #60's
  temporary public feed. Re-implements the **AUTH-1/2/4** login surface server-side (identity/crypto
  from T02/T06 reused). **Deploy step for Andrea:** add the deployed `/auth/callback` URL to the
  Supabase Auth Redirect URLs *and* the Spotify app redirect allow-list, then do one real login to
  confirm the server exchange returns the Spotify refresh token (the only path not covered by tests).
  **Policy change (owner):** a second review on auth/crypto changes is now *encouraged, not
  required* — the owner may self-merge. **T37 (Alembic schema reflection) done** — `env.py` now sets
  `include_schemas=True` + an `include_name` schema allow-list + a schema-qualified `include_object`
  check, so `--autogenerate` sees the T39 medallion schemas and ignores Supabase's own schemas
  (verified with `alembic check`: no drift); this clears the follow-up T39 flagged. **First
  `develop → main` release (#79) shipped** — Render (which builds `main`) was 64 commits stale, so
  T09 login, the Jinja pages, and the snapshot endpoint were 404 in production and the snapshot cron
  couldn't fire (GitHub runs `schedule` only from the default branch). Post-release, `/` (200),
  `/auth/login` (307), and gated `/feed` (303) are live. **T23 (snapshot-500 remediation) done** —
  the release surfaced the snapshot cron 500-ing; two fixes: (1) the real cause — `_ingest_user`
  inserted each `Play` before the `Track` it FK-references, so on Postgres a batch of new tracks hit
  a `ForeignKeyViolation`; now it `session.flush()`es each upserted Track first (the SQLite suite
  missed this because SQLite doesn't enforce FKs — a new `fk_session` test fixture turns them on).
  (2) hardening — `get_valid_access_token` decrypted stored tokens unguarded, so a `TOKEN_ENC_KEY`
  mismatch (`InvalidTag`) would crash the whole run; it now degrades an unreadable token to `None`
  (skip that user) via `_safe_decrypt`. Verified end-to-end against `brink-dev` (50 plays ingested).
  **T62 (FK-ordering hardening) done** — confirmed that follow-up: `db_session` now enforces FKs
  (`PRAGMA foreign_keys=ON`) suite-wide, which surfaced 30 failures = 1 real bug (the T10 posts
  endpoint had the same parent-before-child insert — now `flush()`es the Track before the Post) + 29
  test-seed conveniences SQLite's lax default had hidden (fixed to commit parents before children;
  `as_user` now persists the caller). Root cause: the models use FK columns without ORM
  `relationship()`, so SQLAlchemy doesn't insert in FK order — parents must be flushed/committed
  first. Also corrected the CLAUDE.md line that wrongly said Render deploys from `develop` (it's
  `main`). **T50 (artist storage backend) done** — the artist BTS portal's server half:
  `POST /api/artist/sign-upload` mints a Supabase Storage signed upload URL (service role) for the
  private `artist-images` bucket at a caller-namespaced path, and `POST /api/artist/posts` creates an
  `ArtistPost` (image URL + caption + optional `linkedTrackId`). Both are **artist-only** (caller must
  be `User.isArtist == true`, else 403) with the artist always taken from the login (unspoofable, like
  T10's `Post`); JPEG/PNG ≤ 10 MB is enforced at the request-contract level (ADR-0007/0008, technical
  validation only — no moderation), satisfying BE-9/MEDIA-1/MEDIA-3. New `app/routers/artist.py` +
  `create_signed_upload_url` in `security/supabase.py`. The private `artist-images` bucket has been
  created in `brink-dev` (done). Its merge unblocks **T51** (artist upload UI) and **T52**
  (per-post engagement). **T52 (artist engagement) done** — engagement on artist posts, under
  `/api/artist`: `POST`/`DELETE /posts/{id}/reactions` and `POST`/`GET /posts/{id}/comments` are
  login-gated but open to **any** user (the audience), while `GET /posts/{id}/engagement` is
  **owner-only** (403 for a non-owner) and returns the owning artist's reaction + comment counts
  (satisfies MEDIA-4). Because a foreign key targets one table and `ArtistPost` is not `Post`, this
  added **new `ArtistReaction` + `ArtistComment` tables** (mirrors of `Reaction`/`Comment`, reusing
  the `ReactionType` enum + rate-limit helper) rather than making the existing social tables
  polymorphic — keeping the blast radius off the T10–T13 path. **Scope note:** the ticket assumed
  T11/T12's reactions/comments already attached to artist posts (they don't), so with owner sign-off
  it was widened to also build that write path; a **view count is deferred** (no artist-post read
  path to count from yet — T51). **Deploy step for Andrea:** apply the migration to `brink-dev` —
  `cd backend && uv run alembic upgrade head` (creates the two tables; reuses the existing
  `ReactionType` enum, so no `CREATE TYPE`), same manual-apply pattern as T39. Its merge readies the
  engagement API for **T51** to render. **T40–T43 + T51 frontend and T44 shipped; released to
  production (`develop → main` #97, back-merged #98) — the composer/reactions/comments/follow and the
  profile are now live on Render.** **T44 (profile listening summary) done** — per
  [ADR-0014](docs/decisions/adr/0014-feed-manual-posts-listening-summary.md) a user's Spotify
  listening surfaces on their profile (`/u/{handle}`), not the feed: new `app/stats.py` computes top
  tracks/artists, recent listens, 30-day count, and listening streak live over `Play` (ADR-0003, no
  `UserStats` table), rendered with an own-profile now-playing badge (me-scoped T20), a "link Spotify"
  prompt, and empty states. T44 was **re-scoped** (ADR-0014): the feed stays manual-only, and the
  analytics half — cluster/compatibility (UI-6) + top genres (AN-7) + feed/other-user now-playing
  (UI-10) — is deferred to the slimmed **T14**, still blocked on the analytics spine (T33/T35) and the
  Kaggle genre join (T31); UI-6/UI-10/AN-7 are marked **◧ partial**. **T30 (analytics scaffold) done**
  — `uv init` an `analytics/` package (scikit-learn, pandas, SQLAlchemy, psycopg) with `analytics/db.py`
  (SQLAlchemy engine off the root `.env`'s `DATABASE_URL`, normalizing the Supabase pooler URL like
  `backend/app/db.py` does) and a passing smoke test reading a `silver."Track"` row count
  (schema-qualified after T39 moved `Track` into `silver`); `uv.lock` committed. AN-8/INFRA-4 stay
  **◧ partial** — both also need T38's GitHub Actions pipeline workflow, out of scope here. Its merge
  unblocks **T31** (Kaggle genre join). **T31 (Kaggle ingest + Track join) done** —
  `analytics/ingest_kaggle.py` lands the CSV raw into `bronze.kaggle_tracks_raw` (replaced each
  run, so re-running never duplicates) and joins onto `silver.Track` by `spotifyId`/`track_id`,
  filling in `danceability/energy/valence/tempo/loudness/popularity` + `kaggleMatched` on matches;
  non-matches are left alone (the fallback is T33). Coverage is logged, not hidden (ADR-0004).
  **Scope note (disclosed, not an ADR change):** ran against a **temporary ~114k substitute**
  (`SpotifyAudioFeaturesApril2019.csv`, gitignored under `analytics/data/`) instead of the ≈1M+ set
  ADR-0004 calls for, since that set wasn't available — coverage against brink-dev is currently
  **14/343 (4.1%)**. Swapping in the real set later is just re-running the script against the new
  file. AN-1/DATA-1 marked **✅ interim dataset**. Its merge unblocks **T32**. **T79 (2026-07-15
  coherence sweep) done** — four parallel reviews (docs↔code coherence, email-auth investigation,
  frontend-enablement gap audit, Supabase schema audit; reports in
  `docs/plans/reviews/2026-07-15-*.md`) landed in one chore PR with every easy drift fix (CI/
  branch-check claims, `render.yaml` branch + `CRON_SECRET` record, stale React-era comments,
  ADR-0003 language note, `home.html` copy aligned with ADR-0014's manual-posting feed); T75/T76
  marked **Obsolete** (their target files died with the SPA in T60). The reviews also filed the
  **enablement wave**: the backend is ahead of the frontend, so **T47** (authenticated nav +
  logout link — today no page links to /feed, /artist, your profile, or logout), **T15/T46**
  (user search API/UI — today you can't find a user to follow without hand-typing their URL),
  **T53** (signed READ urls — artist images upload into a private bucket and currently cannot
  render at all), **T54** (audience view of artist posts — the whole T52 engagement API is dead
  code until a page renders it), **T16** (follower/following lists), **T63** (retire the dead
  capture-spotify endpoint), and a rewritten **T03** (email+password signup/login server-side;
  needs a new ADR superseding ADR-0005's OTP choice + first IP-keyed rate limiting). Schema audit
  verdict: no orphaned tables, no drift (`alembic check` clean); bronze/silver/gold + Supabase
  schemas all accounted for; only optional cleanup is dropping `_prisma_migrations`. **T64 (Render
  keep-alive) done** — `.github/workflows/keepalive.yml` pings `/api/health` every 10 min so the
  free-tier service stops spinning down behind Render's ~50s "waking up" screen; like snapshot.yml
  it **only fires from `main`**, so it activates at the next release (owner: one manual
  `workflow_dispatch` run to verify, and the durable alternative if drift still bites is the paid
  Starter plan). **T47 (authenticated nav) done** — every page route passes the signed-in `viewer`
  into its template (public `/` uses a new `_optional_viewer()` that returns `None` instead of
  redirecting), and `base.html` renders a conditional nav: signed out → the landing nav; signed in
  → Feed, My profile, Artist studio (artists only), Log out. Before this nothing linked to /feed,
  /artist, your profile, or logout. Fills the audit's gap #2 (UI-2 app shell).
  **T15 (user search API) done** — `GET /api/users/search?q=` (new
  `backend/app/routers/users.py`; T16's follower/following lists belong there too): login-gated +
  rate-limited (ADR-0011), case-insensitive `ILIKE %q%` on handle + display name with SQL
  wildcards escaped, `q` trimmed with a 2-char minimum, ordered by handle, capped at 20, returning
  the `UserSearchOut` allow-list DTO (ADR-0012). Fixes the audit's top gap: follow (T13) shipped
  with no way to *find* a user (`/api/search` is Spotify tracks, not people). Satisfies the
  discoverability half of BE-4.
  **T46 (user search UI) done** — `base.html` now renders a signed-in "Find people" search box in
  the shared nav, loading `backend/app/static/user-search.js` to debounce calls to T15's
  `/api/users/search` and render safe text-only links to `/u/{handle}`. This completes the
  user-discovery path for follow/profile browsing and satisfies the UI-5 reachability gap.
  **T16 (follower/following lists) done** — `GET /api/users/{userId}/followers` and
  `/following` return capped, login-gated `UserSearchOut` DTOs, and profile follower/following
  counts link to server-rendered list sections (`?list=followers|following`). This completes the
  basic social-graph browse path after T15/T46.
  **T53 (artist image signed reads) done** — artist images finally display:
  `create_signed_read_url(bucket, path, expires_in=3600)` in `security/supabase.py` (the read
  sibling of T50's upload helper, service role, 1-hour expiry), and the `/artist` page signs each
  post's stored path before rendering (the private `artist-images` bucket rejects raw paths, so
  every image was broken — the T51 caveat). Live-verified against brink-dev storage: upload →
  signed GET 200 byte-identical, unsigned GET 400. That verification also caught that the
  installed supabase-py returns an *absolute* signed URL (older releases returned a relative
  path) — the helper handles both.
  **T54 (artist audience page) done** — artist profiles (`/u/{handle}` for artist accounts) now
  render signed artist-image posts with public reaction/comment controls wired to the T52
  `/api/artist/posts/{id}/...` endpoints, plus owner-only engagement totals on the artist's own
  profile. `/artist` remains the upload studio; no artist API behavior changed. Satisfies MEDIA-4's
  visible engagement surface; view count remains deferred.
  **T47 + T15 + T53 released to production (`develop → main` #117, back-merged #118).**
  **T03 (email + password auth) done** — the front door for people **without** Spotify
  ([ADR-0015](docs/decisions/adr/0015-email-password-auth.md), which supersedes ADR-0005's
  magic-link/OTP choice). New `GET`/`POST /auth/signup`, `GET`/`POST /auth/login-email`,
  `GET /auth/confirm` in `routers/auth.py`; `sign_up_email`/`sign_in_password` wrappers on a fresh
  default Supabase client in `security/supabase.py`. Success reuses the T09 session cookie +
  `get_or_create_user` (a handle account, `spotify_id = NULL`). **Email confirmations ON**
  (signup → "check your inbox", no session until confirmed); **6-char password min**; **first
  IP-keyed rate limiting** (`_client_ip` trusts Render's `X-Forwarded-For`; `enforce_rate_limit`
  keyed on `ip:` **and** `email:`, no change to `rate_limit.py`); **CSRF** token on the forms;
  generic non-enumerating errors. New `signup.html`/`login_email.html` + entry links; added the
  `python-multipart` dep for form parsing. Satisfies AUTH-3 (now password, not OTP) + AUTH-6.
  **Deploy step for Andrea:** keep Supabase Email + Confirm-email ON (defaults) and add the
  deployed + localhost `/auth/confirm` URLs to the Supabase redirect allow-list, then do one real
  signup→confirm→login. Follow-ups (not built): password reset, link-Spotify-to-an-email-account,
  auto-login-on-confirm. **Next:
  T63 (retire capture-spotify); T32 (Jonah)
  unblocked; T14 still gated on T33/T35.**

## Deployment topology (ADR-0010, T07, ADR-0013, T60)

> **One app, one host (since T60).** The separate React/Vite SPA on Vercel was retired ([ADR-0013](docs/decisions/adr/0013-python-frontend.md)),
> so the frontend and API are the **same FastAPI app on Render**. The deployed Render `/auth/callback`
> URL must be in the Supabase Auth + Spotify redirect allow-lists, or Spotify login can't return.

- **App (API + frontend):** one FastAPI service on **Render** (`backend/`, config in `render.yaml`)
  — build `uv sync`, start `uvicorn app.main:app`. It serves the `/api/*` JSON endpoints **and** the
  server-rendered Jinja/HTMX pages (`/`, `/feed`, `/u/{handle}`, `/artist`, `/auth/*`), same-origin,
  so there's no CORS and no rewrite layer. Env vars (`DATABASE_URL`, `DIRECT_URL`, `SUPABASE_*`,
  `SPOTIFY_*`, `TOKEN_ENC_KEY`, `CRON_SECRET`) live only in Render, never committed. The service
  is on the **free plan**, which spins down after ~15 idle minutes (→ a ~50s "waking up" screen);
  `.github/workflows/keepalive.yml` (T64) pings `/api/health` every 10 min from `main` to prevent
  that.
- **Release flow:** **Render deploys production from `main`**, so changes reach production only via a
  `develop → main` release PR, and each release must be followed by a back-merge of `main` into
  `develop` (or the next release PR is blocked as BEHIND, since `main` protection is `strict`).
- **Retired in T60:** the Vercel project, `apps/web/vercel.json`'s `/api/*` rewrite, the legacy
  `/api/state` POC path, and the `web` CI build job (also removed from branch-protection required
  checks). If a separate JS frontend is ever reintroduced, restore the CI job + required check.
