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
- **[`docs/plans/requirements.md`](./docs/plans/requirements.md)** — requirement catalog (`AUTH-*`, `BE-*`, …) + requirement→ticket traceability. (Data model: `prisma/schema.prisma`, becoming `backend/app/models.py` SQLModel in T05.)
- **[`docs/plans/tickets/`](./docs/plans/tickets/)** — one file per ticket (`backlog/`, `completed/`) + a dependency-waves index.
- **`docs/decisions/adr/`** — architecture decision records (why we chose what we chose).

---

## 2. Architecture

> **⚠ Backend migration in progress ([ADR-0010](./docs/decisions/adr/0010-fastapi-render-backend.md)).**
> The API is moving from **TypeScript / Vercel serverless + Prisma** to **FastAPI / Python on
> Render + SQLModel / Alembic** (the team works in Python). The new backend is in `backend/`
> (scaffolded); the legacy TS `api/` still serves production until the cutover. Frontend stays
> React/TS and Supabase is unchanged. The diagram below shows the **target** state.

```
Browser (React + Vite SPA, Supabase Auth)
        │  fetch /api/*   (Vercel rewrites /api/* → Render)
        ▼
FastAPI app (Python, backend/, on Render) ── SQLModel ──▶ Supabase Postgres
        │                                                  (Auth + Storage too)
        ▼
We own Spotify token refresh (encrypted at rest)

Analytics: Python / scikit-learn batch job (analytics/, GitHub Actions cron) ──▶ same Postgres
```

- **`apps/web/`** — React + TypeScript + Vite SPA (frontend), deployed on Vercel.
- **`backend/`** — FastAPI app (Python, `uv`-managed); the API's new home (ADR-0010).
- **`api/`** — *legacy* Vercel serverless functions (TypeScript); serves prod until the cutover, then removed.
- **`prisma/`** — `schema.prisma` (legacy 14-table model; becomes `backend/app/models.py` SQLModel).
- **`analytics/`** — Python pipeline, `uv`-managed (added in T30).
- **`docs/`** — requirements, tickets, and decision records.

**Auth & data:** users sign in via Supabase Auth (Spotify OAuth). The backend validates the
Supabase JWT server-side and owns long-term Spotify access by storing an encrypted refresh
token (AES-256-GCM). The Supabase Data API is disabled — tables are reached only through the ORM.

---

## 3. Running it locally

Local dev needs **two terminals**. Do **not** run `vercel dev` (it would disturb the live
deployment). You need a root `.env` and `apps/web/.env` — secrets are git-ignored and shared
separately; copy `.env.example` and ask Andrea / pull from the Vercel project for the values.

```bash
# Terminal 1 — frontend (Vite on 127.0.0.1:5173, proxies /api -> :3001)
cd apps/web && npm install && npm run dev

# Terminal 2 — API on :3001
#   FastAPI (new backend, use for backend work):
cd backend && uv run uvicorn app.main:app --reload --port 3001
#   legacy TS handlers (still serving until the cutover): npm install && npm run dev:api
```

- **Test:** `cd backend && uv run pytest` (FastAPI); `npm test` (Jest — legacy TS).
  Analytics: `cd analytics && uv run pytest`.
- **Build frontend:** `cd apps/web && npm run build`

See CLAUDE.md for the env-var list and migration details (SQLModel + Alembic).

---

## 4. Branching & deploying

- **`develop`** is the integration branch — every change goes through a PR into `develop`.
- **`main`** is production — Vercel deploys the frontend (and, after the ADR-0010 cutover, the
  FastAPI backend runs on Render). `develop` reaches `main` only via a release PR (and only once
  env vars are set). **Never push to `main` or `develop` directly.**
- Branch naming: `<type>/<ticket-id>-<slug>` (e.g. `feat/T10-posts-api`). One ticket = one PR.

CI (`.github/workflows/ci.yml`) runs tests, the web build, and a secret scan on every PR.

---

## 5. Contributing

1. Read [`CLAUDE.md`](./CLAUDE.md) and the relevant ticket in `docs/plans/`.
2. Branch off `develop`, write the test first, keep the change scoped to one ticket.
3. Open a PR into `develop` (the template walks you through the checklist).
4. Record architecture decisions as ADRs in `docs/decisions/adr/`; keep docs in sync in the
   same PR.
