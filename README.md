# Brink — Music-Native Social

A social app that turns a user's real Spotify listening history into a feed friends can react
to, plus a compatibility match-score between users and a clustering/taste analytics layer.

Built as a course project for McGill University's Desautels Faculty of Management (MMA).

**Team:** Andrea Vreugdenhil · Sebastian Arguedas Soley · Jonah Walker
**Live demo:** <https://brink-self.vercel.app>

> **New here?** Read [`CLAUDE.md`](./CLAUDE.md) first — it's the contributor & agent contract
> (commands, conventions, hard rules, ownership). This README is just the high-level intro.

---

## 1. Source of truth

The detailed, authoritative docs live under `docs/` — read these before planning work:

- **[`CLAUDE.md`](./CLAUDE.md)** — how we work: commands, branch/PR rules, conventions, env, ownership.
- **`docs/plans/2026-06-22-brink-spec-design.md`** — layered spec, data model, requirement IDs.
- **`docs/plans/2026-06-22-brink-implementation-tickets.md`** — the 27 tickets (T00–T61) and waves.
- **`docs/decisions/adr/`** — architecture decision records (why we chose what we chose).

---

## 2. Architecture

```
Browser (React + Vite SPA, Supabase Auth)
        │  fetch /api/*
        ▼
Vercel serverless functions (TypeScript, api/) ── Prisma ──▶ Supabase Postgres
        │                                                    (Auth + Storage too)
        ▼
We own Spotify token refresh (encrypted at rest)

Analytics: Python / scikit-learn batch job (analytics/, GitHub Actions cron) ──▶ same Postgres
```

- **`apps/web/`** — React + TypeScript + Vite SPA (frontend).
- **`api/`** — Vercel serverless functions in TypeScript; shared helpers in `api/_lib/`.
- **`prisma/`** — `schema.prisma` + migrations (the 14-table data model).
- **`analytics/`** — Python pipeline, `uv`-managed (added in T30).
- **`docs/`** — spec, tickets, and decision records.

**Auth & data:** users sign in via Supabase Auth (Spotify OAuth). The backend validates the
Supabase JWT server-side and owns long-term Spotify access by storing an encrypted refresh
token (AES-256-GCM). The Supabase Data API is disabled — tables are reached only through Prisma.

---

## 3. Running it locally

Local dev needs **two terminals**. Do **not** run `vercel dev` (it would disturb the live
deployment). You need a root `.env` and `apps/web/.env` — secrets are git-ignored and shared
separately; copy `.env.example` and ask Andrea / pull from the Vercel project for the values.

```bash
# Terminal 1 — frontend (Vite on 127.0.0.1:5173, proxies /api -> :3001)
cd apps/web && npm install && npm run dev

# Terminal 2 — API (serverless handlers on :3001, loads root .env)
npm install        # first time; also wires the pre-commit hook
npm run dev:api
```

- **Test:** `npm test` (Jest + Supertest). Python: `cd analytics && uv run pytest`.
- **Build frontend:** `cd apps/web && npm run build`
- **Prisma client:** `npm run prisma:generate`

See CLAUDE.md for the env-var list and the (non-interactive) migration workaround.

---

## 4. Branching & deploying

- **`develop`** is the integration branch — every change goes through a PR into `develop`.
- **`main`** is production — Vercel deploys it. `develop` reaches `main` only via a release PR
  (and only once Vercel env vars are set). **Never push to `main` or `develop` directly.**
- Branch naming: `<type>/<ticket-id>-<slug>` (e.g. `feat/T10-posts-api`). One ticket = one PR.

CI (`.github/workflows/ci.yml`) runs tests, the web build, and a secret scan on every PR.

---

## 5. Contributing

1. Read [`CLAUDE.md`](./CLAUDE.md) and the relevant ticket in `docs/plans/`.
2. Branch off `develop`, write the test first, keep the change scoped to one ticket.
3. Open a PR into `develop` (the template walks you through the checklist).
4. Record architecture decisions as ADRs in `docs/decisions/adr/`; keep docs in sync in the
   same PR.
