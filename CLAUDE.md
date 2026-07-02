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

**Source of truth — read these before planning any work:**
- `docs/plans/requirements.md` — requirement catalog (`AUTH-*`, `BE-*`, `SP-*`, `AN-*`, `UI-*`, `MEDIA-*`, `INFRA-*`, `DATA-*`) + requirement→ticket traceability. Data model: `backend/app/models.py` (SQLModel). Decisions: `docs/decisions/`.
- `docs/plans/tickets/` — one file per ticket (`backlog/`, `completed/`), derived from the ADRs in `docs/decisions/`. Start at `docs/plans/tickets/README.md` for the dependency waves and reading guide.

## Layout

- `backend/` — **the API: FastAPI app (Python, `uv`-managed)**. App code in `backend/app/`, tests
  in `backend/tests/`, DB migrations in `backend/alembic/`.
- `apps/web/` — React/Vite SPA frontend (TypeScript).
- `analytics/` — Python pipeline (`uv`-managed). Created in T30.
- `docs/plans/` — spec + tickets (source of truth above).

## Commands

Local dev needs **two terminals**. Local reads the root `.env` (the `brink-dev` Supabase project),
so it never touches production.

```
# Terminal 1 — frontend (Vite on 127.0.0.1:5173, proxies /api -> :3001)
cd apps/web && npm run dev

# Terminal 2 — API on :3001 (Vite proxies /api -> :3001)
cd backend && uv run uvicorn app.main:app --reload --port 3001
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

## Database migrations

Schema changes use **SQLModel + Alembic**: edit `backend/app/models.py`, then
`cd backend && uv run alembic revision --autogenerate -m "..."` and `uv run alembic upgrade head`.
Alembic was baselined against the live schema in T05 (stamped, not recreated), so `upgrade head`
is a no-op on the existing DB. `alembic check` reports any drift between the models and the DB.

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
`TOKEN_ENC_KEY` — need a deliberate second review; don't self-merge them.

## Watch-outs

- Spotify `provider_token` from the browser lasts ~1h and is **not** refreshed by Supabase.
  Server/long-term Spotify access must go through our stored refresh token (snapshot job, T21).
- The DB still has a `_prisma_migrations` table (Prisma's old bookkeeping); Alembic ignores it
  (`backend/alembic/env.py`). Harmless — it can be dropped whenever.
- Status: T00–T02, T04–T06, **T07–T08** done — the FastAPI/Render migration is complete and the
  legacy TypeScript backend is fully removed. The React SPA is on **Vercel**
  (`brink-theta.vercel.app`), FastAPI on **Render** (`brink-xg7p.onrender.com`, `/api/health` →
  `db: true`), and Spotify login works on the live site (Supabase OAuth → capture-spotify →
  encrypted token). Repo: **`brinkmusic/Brink`** (public). A 2026-07-02 code review of the shipped
  surface produced a remediation wave (T70–T78, see
  `docs/plans/reviews/2026-07-02-code-review-t00-t08.md`); **T70 blocks T10**. Next feature work:
  the social API (T10 posts → T11–T14) on FastAPI.

## Deployment topology (ADR-0010, T07)

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
