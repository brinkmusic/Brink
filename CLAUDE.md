# Brink — Agent & Contributor Guide

Music-native social web app. MMA course project, team of 3, **deadline 2026-07-30**.
This file is the contract every AI agent and contributor reads first. Read it before
touching the repo.

## What Brink is

React/Vite SPA + an **API backend** + **Supabase** (Postgres + Auth + Storage) + a
Python/scikit-learn analytics batch job (GitHub Actions cron).

> **⚠ Backend migration in progress ([ADR-0010](docs/decisions/adr/0010-fastapi-render-backend.md)).**
> The API is moving from **TypeScript / Vercel serverless + Prisma** to **FastAPI / Python on
> Render + SQLModel / Alembic** — the team works in Python, not TS. The new backend lives in
> `backend/` (scaffolded, T04 ✅); the **legacy TS `api/` still serves production** until the
> cutover (T07). **New backend work targets `backend/` (FastAPI), not `api/`.** Frontend stays
> React/TS; Supabase is unchanged. Migration spine: `004 → 005 → 006 → 007 → 008` in
> `docs/plans/tickets/`. This guide still documents the TS path where it's the live one; CLAUDE.md
> gets its full flip to FastAPI in **T08**.

**Source of truth — read these before planning any work:**
- `docs/plans/requirements.md` — requirement catalog (`AUTH-*`, `BE-*`, `SP-*`, `AN-*`, `UI-*`, `MEDIA-*`, `INFRA-*`, `DATA-*`) + requirement→ticket traceability. Data model: `prisma/schema.prisma` (moving to `backend/app/models.py` as SQLModel in T05). Decisions: `docs/decisions/`.
- `docs/plans/tickets/` — one file per ticket (`backlog/`, `completed/`), derived from the ADRs in `docs/decisions/`. Start at `docs/plans/tickets/README.md` for the dependency waves and reading guide.

## Layout

- `backend/` — **FastAPI app (Python, `uv`-managed)** — the API's new home (ADR-0010). App code
  in `backend/app/`, tests in `backend/tests/`, migrations in `backend/alembic/` (from T05).
- `api/` — *legacy* Vercel serverless functions (TypeScript), shared helpers in `api/_lib/`.
  Still serves production until the T07 cutover; removed wholesale in T08.
- `apps/web/` — React/Vite SPA frontend (stays TypeScript).
- `prisma/` — `schema.prisma` + migrations (legacy; replaced by SQLModel/Alembic in T05, removed in T08).
- `analytics/` — Python pipeline (`uv`-managed). Created in T30.
- `docs/plans/` — spec + tickets (source of truth above).

## Commands

Local dev needs **two terminals** (the live deployment stays untouched — do not run `vercel dev`):

```
# Terminal 1 — frontend (Vite on 127.0.0.1:5173, proxies /api -> :3001)
cd apps/web && npm run dev

# Terminal 2 — API on :3001 (Vite proxies /api -> :3001)
#   FastAPI (new backend, ADR-0010 — use this for backend work):
cd backend && uv run uvicorn app.main:app --reload --port 3001
#   legacy TS handlers (still serving until T07): npm run dev:api
```

- **Test:** `cd backend && uv run pytest` (FastAPI); `npm test` (root, Jest + Supertest — legacy
  TS, until T08). Analytics: `cd analytics && uv run pytest`.
- **Build frontend:** `cd apps/web && npm run build` · **Lint:** `npm run lint`.
- **Prisma generate (legacy):** `npm run prisma:generate`.

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
   Secrets live only in those files locally and in Vercel/GitHub env. If you ever see a secret
   in tracked files, stop and flag it.
4. **TDD (expected practice).** Write a failing test first, then minimal code to pass,
   with frequent small commits. Claude Code agents should use the `test-driven-development`
   skill; everyone else follows the same loop by hand. This is the expected workflow, not an
   automated guarantee — CI (`.github/workflows/ci.yml`) runs `npm test` on every PR and is
   what actually blocks untested code. Don't execute multiple tickets at once.
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
  logic lives in `api/_lib/` (backend) and `apps/web/src` shared modules (frontend) — extend
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
  then the fix. Changes to shared code (`api/_lib/`, `prisma/schema.prisma`) have a wide blast
  radius — call out in the PR what depends on them, and run the full suite (`npm test`).
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

**New backend work (T05+) uses SQLModel + Alembic** — edit `backend/app/models.py`, then
`cd backend && uv run alembic revision --autogenerate -m "..."` and `uv run alembic upgrade head`.
This replaces the Prisma workaround below.

**Legacy (Prisma) — only while the TS `api/` is still live (removed in T08):**
`prisma migrate dev` is **interactive and will hang** in this environment — do not use it.
To make a schema change:

1. Edit `prisma/schema.prisma`.
2. Generate a migration SQL file with a non-interactive diff:
   ```
   npx prisma migrate diff \
     --from-schema-datasource prisma/schema.prisma \
     --to-schema-datamodel prisma/schema.prisma \
     --script > prisma/migrations/<timestamp>_<name>/migration.sql
   ```
3. Apply with `npm run prisma:deploy` (`prisma migrate deploy`).

## Environment

- Supabase project `brink-dev` (ref `ljzwskfhiviunmqxerwu`). Data API disabled — tables are
  reached only through Prisma.
- Root `.env`: `DATABASE_URL`/`DIRECT_URL` (Supabase pooler 6543/5432), `SUPABASE_URL`,
  `SUPABASE_SERVICE_ROLE_KEY`, `SPOTIFY_CLIENT_ID`/`SECRET`, `TOKEN_ENC_KEY`.
- `apps/web/.env`: `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY`.
- **Getting the values (onboarding):** `.env` files are git-ignored and never shared in the
  repo. Copy `.env.example`, then get the real secret values from the Vercel/GitHub project
  env or ask Andrea. Don't paste secrets into chat, issues, or commits.
- **Git hooks:** running `npm install` points git at `.githooks/` (a pre-commit secret guard).
  If you skipped install, run `git config core.hooksPath .githooks` once.

## Ownership & review (CODEOWNERS intent)

- **Andrea** — backend / API / auth / DB (`backend/`, legacy `api/`, `prisma/`).
- **Sebastian** — frontend (`apps/web/`).
- **Jonah** — analytics (`analytics/`).

The owner of an area is the default reviewer for PRs touching it (every ticket also has an
`owner` in its frontmatter). **Auth and crypto changes** — the FastAPI successors
`backend/app/deps.py`, `backend/app/security/crypto.py`, `backend/app/security/supabase.py` (and
their legacy TS counterparts `api/_lib/auth.ts`/`crypto.ts`/`supabase.ts`), anything touching
tokens or `TOKEN_ENC_KEY` — need a deliberate second review; don't self-merge them.

## Watch-outs

- Spotify `provider_token` from the browser lasts ~1h and is **not** refreshed by Supabase.
  Server/long-term Spotify access must go through our stored refresh token (snapshot job, T21).
- `tsx` struggles importing some `.ts` files with top-level await from ad-hoc scripts; prefer
  `.mjs` for throwaway checks, or `node --env-file=.env --import tsx`.
- Status: T00, T01, T02, T04, **T05** done. Auth verified end-to-end (Spotify login creates a
  `public.User` row + stores the encrypted refresh token). **Backend migration to FastAPI/Render
  underway (ADR-0010).** T05 landed the 14 SQLModel tables (`backend/app/models.py`), the
  engine/session + config (`backend/app/db.py`, `config.py`), an Alembic baseline stamped against
  the live schema, and restored `db` reachability on `GET /api/health` — next is **T06** (auth/crypto
  port). The TS `api/` still serves the live app until the T07 cutover.
