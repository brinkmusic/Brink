# Brink — Agent & Contributor Guide

Music-native social web app. MMA course project, team of 3, **deadline 2026-07-30**.
This file is the contract every AI agent and contributor reads first. Read it before
touching the repo.

## What Brink is

React/Vite SPA + Vercel serverless functions (TypeScript, Prisma) + **Supabase**
(Postgres + Auth + Storage) + a Python/scikit-learn analytics batch job (GitHub Actions cron).

**Source of truth — read these before planning any work:**
- `docs/plans/2026-06-22-brink-spec-design.md` — layered spec, target vs current, data model, requirement IDs (`AUTH-*`, `BE-*`, `SP-*`, `AN-*`, `UI-*`, `MEDIA-*`, `INFRA-*`, `DATA-*`).
- `docs/plans/2026-06-22-brink-implementation-tickets.md` — 27 tickets (T00–T61) with dependency waves.

## Layout

- `api/` — Vercel serverless functions (TypeScript). Shared helpers in `api/_lib/`.
- `apps/web/` — React/Vite SPA frontend.
- `prisma/` — `schema.prisma` + migrations.
- `analytics/` — Python pipeline (`uv`-managed). Created in T30.
- `docs/plans/` — spec + tickets (source of truth above).

## Commands

Local dev needs **two terminals** (the live deployment stays untouched — do not run `vercel dev`):

```
# Terminal 1 — frontend (Vite on 127.0.0.1:5173, proxies /api -> :3001)
cd apps/web && npm run dev

# Terminal 2 — API (serverless handlers on :3001, loads root .env)
npm run dev:api
```

- **Test:** `npm test` (root, Jest + Supertest). Python: `cd analytics && uv run pytest`.
- **Build frontend:** `cd apps/web && npm run build` · **Lint:** `npm run lint`.
- **Prisma generate:** `npm run prisma:generate`.

## Hard rules

1. **Never push to `main`.** Every change goes on a branch and through a PR. One ticket = one PR.
2. **Branches:** name them `<type>/<ticket-id>-<slug>` where type is
   `feat | fix | chore | docs | ci` (e.g. `feat/T10-posts-api`, `chore/repo-governance`).
   Branch off the latest `main`, keep them short-lived, and **delete the branch after its PR
   merges**. Don't let a branch drift far behind `main` — rebase or re-sync instead.
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
- **Comments: explain *why*, never *what*.** No docstrings or boilerplate comment blocks. Code
  should read on its own; add a comment only when the reason for something is non-obvious. Use
  JSDoc only on exported `api/_lib/` helpers where the types don't fully convey the contract.
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

## Database migrations (important workaround)

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

- **Andrea** — backend / API / Prisma / auth (`api/`, `prisma/`).
- **Sebastian** — frontend (`apps/web/`).
- **Jonah** — analytics (`analytics/`).

The owner of an area is the default reviewer for PRs touching it. **Auth and crypto changes**
(`api/_lib/auth.ts`, `api/_lib/crypto.ts`, `api/_lib/supabase.ts`, anything touching tokens or
`TOKEN_ENC_KEY`) need a deliberate second review — don't self-merge them.

## Watch-outs

- Spotify `provider_token` from the browser lasts ~1h and is **not** refreshed by Supabase.
  Server/long-term Spotify access must go through our stored refresh token (snapshot job, T21).
- `tsx` struggles importing some `.ts` files with top-level await from ad-hoc scripts; prefer
  `.mjs` for throwaway checks, or `node --env-file=.env --import tsx`.
- Status: T00, T01, T02 are done. Auth verified end-to-end (Spotify login creates a `public.User`
  row + stores the encrypted refresh token).
