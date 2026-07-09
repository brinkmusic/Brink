# Brink — Agent & Contributor Guide

Music-native social web app. MMA course project, team of 3, **deadline 2026-07-30**.
This file is the contract every AI agent and contributor reads first. Read it before
touching the repo.

## What Brink is

React/Vite SPA (Vercel) + a **FastAPI/Python API** (Render) + **Supabase** (Postgres + Auth +
Storage) + a Python/scikit-learn analytics batch job (GitHub Actions cron).

> **Stack:** the API is a **FastAPI / Python** app (SQLModel + Alembic) on **Render**; the
> React/Vite SPA is on **Vercel** and calls it same-origin via an `/api/*` rewrite; **Supabase**
> provides Postgres, Auth, and Storage. See
> [ADR-0010](docs/decisions/adr/0010-fastapi-render-backend.md) for how the backend moved here from
> an earlier TypeScript/Vercel/Prisma stack (removed in T08). All backend work is in `backend/`.

> **⚠ Frontend transitioning ([ADR-0013](docs/decisions/adr/0013-python-frontend.md)).** The
> frontend is moving from the React/Vite SPA to **HTML pages served by the FastAPI backend**
> (Jinja2 templates + HTMX, in `backend/app/templates/` and `backend/app/routers/pages.py`), so the
> whole app is one Python codebase we can all read and defend. The React/Vite `apps/web/` SPA stays
> as a fallback until the Python pages reach parity, then it is retired. Server-side Spotify login
> for the new frontend is tracked in **T09**.

**Source of truth — read these before planning any work:**
- `docs/plans/requirements.md` — requirement catalog (`AUTH-*`, `BE-*`, `SP-*`, `AN-*`, `UI-*`, `MEDIA-*`, `INFRA-*`, `DATA-*`) + requirement→ticket traceability. Data model: `backend/app/models.py` (SQLModel). Decisions: `docs/decisions/`.
- `docs/plans/tickets/` — one file per ticket (`backlog/`, `completed/`), derived from the ADRs in `docs/decisions/`. Start at `docs/plans/tickets/README.md` for the dependency waves and reading guide.

## Layout

- `backend/` — **the API: FastAPI app (Python, `uv`-managed)**. App code in `backend/app/`, tests
  in `backend/tests/`, DB migrations in `backend/alembic/`.
- `backend/app/templates/` + `backend/app/static/` — the **Python frontend**: HTML pages
  (Jinja2 templates; HTMX to come) served by FastAPI, with routes in `backend/app/routers/pages.py` (ADR-0013).
- `apps/web/` — React/Vite SPA frontend (TypeScript). **Legacy**: being replaced by the Jinja/HTMX
  pages above per [ADR-0013](docs/decisions/adr/0013-python-frontend.md); kept as a fallback until parity.
- `analytics/` — Python pipeline (`uv`-managed). Created in T30.
- `docs/plans/` — spec + tickets (source of truth above).

## Commands

Local dev reads the root `.env` (the `brink-dev` Supabase project), so it never touches production.

```
# API + Python frontend — the FastAPI app serves BOTH the JSON API and the HTML pages
# (ADR-0013). Visit http://127.0.0.1:3001/ for the pages, /api/* for the API.
cd backend && uv run uvicorn app.main:app --reload --port 3001

# Legacy React/Vite SPA — only until it's retired per ADR-0013. Separate terminal,
# Vite on 127.0.0.1:5173, proxies /api -> :3001.
cd apps/web && npm run dev
```

- **Test:** `cd backend && uv run pytest` (backend). Analytics: `cd analytics && uv run pytest` (after T30 — `analytics/` does not exist yet).
- **Build frontend:** `cd apps/web && npm run build` · **Lint:** `cd apps/web && npm run lint`.

## Hard rules

1. **`develop` is the integration branch; `main` is production. Never push to either directly.**
   Every change goes on a branch and through a PR **into `develop`**. One ticket = one PR.
   `main` only receives `develop` via a release PR — and only once the Vercel env vars are set,
   because Vercel deploys production from `main`.
2. **Branches:** name them `<type>/<ticket-id>-<slug>` where type is
   `feat | fix | chore | docs | ci` (e.g. `feat/T10-posts-api`, `chore/repo-governance`).
   Branch off the latest `develop`, keep them short-lived, and **delete the branch after its PR
   merges**. Don't let a branch drift far behind `develop` — rebase or re-sync instead.
3. **Never commit secrets.** `.env` (root) and `apps/web/.env` are git-ignored and stay that way.
   Secrets live only in those files locally and in the Render (backend) / Vercel (frontend) / GitHub
   env. If you ever see a secret in tracked files, stop and flag it.
4. **TDD (expected practice).** Write a failing test first, then minimal code to pass,
   with frequent small commits. Claude Code agents should use the `test-driven-development`
   skill; everyone else follows the same loop by hand. This is the expected workflow, not an
   automated guarantee — CI (`.github/workflows/ci.yml`) runs the backend tests (`uv run pytest`),
   the frontend build, and a secret scan on every PR, and is what actually blocks untested code.
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
  logic lives in `backend/app/` (backend) and `apps/web/src` shared modules (frontend) — extend
  or import it; don't copy-paste or write a second version of something that already exists. If
  you find duplication, factor it out as part of the change.
- **Comments: explain both *what* and *why*, written for a reader new to the language/stack.**
  This repo is read by a mixed team including a non-technical owner, so code must be *followable
  by someone who doesn't already know* Python/SQLModel/FastAPI/React. This deliberately overrides
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
  bookend to `get-me-started`: runs the full backend suite + frontend build/lint, confirms the tree
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
- `apps/web/.env`: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
- **Getting the values (onboarding):** `.env` files are git-ignored and never shared in the
  repo. Copy `.env.example`, then get the real secret values from the Render (backend) /
  Vercel (frontend) / GitHub env or ask Andrea. Don't paste secrets into chat, issues, or commits.
- **Git hooks:** running `npm install` points git at `.githooks/` (a pre-commit secret guard).
  If you skipped install, run `git config core.hooksPath .githooks` once.

## Ownership & review (CODEOWNERS intent)

- **Andrea** — backend / API / auth / DB (`backend/`).
- **Sebastian** — frontend (`apps/web/`).
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
  author DTO), satisfies BE-6. The React SPA is on
  **Vercel** (`brink-theta.vercel.app`), FastAPI on **Render** (`brink-xg7p.onrender.com`,
  `/api/health` → `db: true`), Spotify login works end-to-end. Repo: **`brinkmusic/Brink`**
  (public). Remaining remediation: T75, T76 (see
  `docs/plans/reviews/2026-07-02-code-review-t00-t08.md`). **T90–T93 (developer tooling) done** —
  the committed `get-me-started` session-warmup skill, the `close-out` ticket-close-out skill, and
  (T93) the `close-session` end-of-session skill (`.claude/skills/`); **close-out now runs
  pre-merge** — its ticket/traceability/status bookkeeping is folded into the same PR that
  implements the ticket, so no separate follow-up PR (`close-session` owns the end-of-session
  validate + branch-cleanup + handoff). Plus the **`docs-sync` CI gate**
  (`.github/workflows/docs-sync.yml`) that fails any PR changing source without touching docs
  (`no-docs` label = escape hatch). `develop` and `main` are now branch-protected: PR required, up
  to date, checks `api/web/secrets/docs-sync` green, admins included. **T13 (follow + feed) done**
  — `POST`/`DELETE /api/follow/{userId}` (idempotent follow / own-only unfollow, rate-limited) +
  `GET /api/feed` (followees + self, newest-first, each with track, author, per-type reaction
  counts, comment count, and the viewer's own reactions; fixed 4 queries, no N+1), satisfying BE-4
  + BE-7. Its merge unblocks the follow/feed UIs (T41, T43). **T22 (Spotify token refresh) done** —
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
  (verified with `alembic check`: no drift); this clears the follow-up T39 flagged. **Next backend
  feature: T50 (artist storage) is ready; the analytics spine (031/033/034, Jonah) is unblocked;
  T14 (profile) still gated on T35.**

## Deployment topology (ADR-0010, T07)

> **⚠ In transition (ADR-0013).** The topology below describes the React/Vite SPA on Vercel, which
> is still the live frontend. As the Jinja/HTMX pages served by FastAPI reach parity, the frontend
> is served by **Render** (the same app as the API) and the separate Vercel SPA is retired. Until
> then both exist and this section still applies. When the new frontend goes live on Render, its URL
> (not just the Vercel URL) must be in the Supabase/Spotify redirect allow-lists (tracked in T09).

- **Frontend:** Vercel serves the React SPA at `brink-theta.vercel.app` (project root `apps/web`),
  deploying from `main`. Supabase Auth **URL config** must list the Vercel URL in Site URL +
  Redirect URLs, or Spotify login can't return to the deployed site.
- **Backend:** FastAPI on **Render** (`backend/`, config in `render.yaml`) — build `uv sync`,
  start `uvicorn app.main:app`. Env vars (`DATABASE_URL`, `DIRECT_URL`, `SUPABASE_*`,
  `SPOTIFY_*`, `TOKEN_ENC_KEY`) live only in Render, never committed.
- **Wiring:** the Vercel project's **root directory is `apps/web`** (it builds only the SPA).
  `apps/web/vercel.json` rewrites `/api/:path*` → the Render URL, so the browser still calls
  same-origin `/api/*` (no CORS). Vercel deploys the frontend from `main`; Render deploys the
  backend from `develop`.
- **Note:** the frontend still calls a legacy POC `/api/state` path (`apps/web/src/lib/backend.ts`)
  that FastAPI does not implement, so it 404s; those mock social features are replaced by the real
  API in T10–T14, and the `/api/state` calls are removed in T60.
