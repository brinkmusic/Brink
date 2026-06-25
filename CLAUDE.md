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
2. **Branch naming:** `feat/<ticket-id>-<slug>` (e.g. `feat/T10-posts-api`).
3. **Never commit secrets.** `.env` (root) and `apps/web/.env` are git-ignored and stay that way.
   Secrets live only in those files locally and in Vercel/GitHub env. If you ever see a secret
   in tracked files, stop and flag it.
4. **TDD.** Follow the `executing-plans` skill: failing test first, minimal code to pass,
   frequent small commits. Don't execute multiple tickets at once.
5. **Don't widen scope.** Build exactly what the ticket/requirement specifies — no extra
   features, abstractions, or error handling beyond what's asked.
6. **Auth:** validate Supabase JWTs server-side via `getUser()` (no JWT secret). We own
   Spotify token refresh; tokens are encrypted at rest (AES-256-GCM, `TOKEN_ENC_KEY`).

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

## Ownership (CODEOWNERS intent)

- **Andrea** — backend / API / Prisma / auth (`api/`, `prisma/`).
- **Sebastian** — frontend (`apps/web/`).
- **Jonah** — analytics (`analytics/`).

## Watch-outs

- Spotify `provider_token` from the browser lasts ~1h and is **not** refreshed by Supabase.
  Server/long-term Spotify access must go through our stored refresh token (snapshot job, T21).
- `tsx` struggles importing some `.ts` files with top-level await from ad-hoc scripts; prefer
  `.mjs` for throwaway checks, or `node --env-file=.env --import tsx`.
- Status: T00, T01, T02 are done. Auth verified end-to-end (Spotify login creates a `public.User`
  row + stores the encrypted refresh token).
