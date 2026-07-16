# Brink — Music-Native Social

**What Brink will be:** a music-native social network built on your *real* listening. You sign in
with Spotify, and your actual play history becomes a feed your friends can react to and comment on.
On top of that sit a per-user "taste profile" (top tracks, artists, and genres, plus a listening
streak), a **compatibility score** that tells any two people how similar their taste is, and a
clustering layer that groups listeners into taste communities. Artists get a lightweight portal to
post to fans. The goal is a feed that feels like *who you actually are musically*, not what you
manually share.

Built as a course project for McGill University's Desautels Faculty of Management (MMA).

**Team:** Andrea Vreugdenhil · Sebastian Arguedas Soley · Jonah Walker
**Status & live URLs:** in active development — see [`CLAUDE.md`](./CLAUDE.md).

> **New here?** Read [`CLAUDE.md`](./CLAUDE.md) first — it's the contributor & agent contract
> (commands, conventions, hard rules, ownership). This README is just the high-level intro.

---

## 1. Source of truth

The detailed, authoritative docs live under `docs/` — read these before planning work:

- **[`CLAUDE.md`](./CLAUDE.md)** — how we work: commands, branch/PR rules, conventions, env, ownership.
- **[`docs/plans/requirements.md`](./docs/plans/requirements.md)** — requirement catalog (`AUTH-*`, `BE-*`, …) + requirement→ticket traceability. (Data model: `backend/app/models.py`, SQLModel.)
- **[`docs/plans/tickets/`](./docs/plans/tickets/)** — one file per ticket (`backlog/`, `completed/`) + a dependency-waves index.
- **`docs/decisions/adr/`** — architecture decision records (why we chose what we chose).

---

## 2. Architecture

> **Stack:** a single **FastAPI / Python** app (SQLModel + Alembic) on **Render** that serves
> **both** the JSON API and the **HTML frontend** (Jinja2 templates + HTMX, server-rendered), with
> **Supabase** for Postgres, Auth, and Storage. Analytics is a Python/scikit-learn batch job. (An
> earlier TypeScript/Vercel backend was removed in T08, and the separate React/Vite SPA was retired
> in T60 — see [ADR-0010](./docs/decisions/adr/0010-fastapi-render-backend.md) and
> [ADR-0013](./docs/decisions/adr/0013-python-frontend.md).) Current build status lives in
> [`CLAUDE.md`](./CLAUDE.md).

```
Browser (HTML pages served by FastAPI, server-side Supabase Auth)
        │  same-origin /api/* and /pages
        ▼
FastAPI app (Python, backend/, on Render) ── SQLModel ──▶ Supabase Postgres
        │                                                  (Auth + Storage too)
        ▼
We own Spotify token refresh (encrypted at rest)

Analytics: Python / scikit-learn batch job (analytics/, GitHub Actions cron) ──▶ same Postgres
```

- **`backend/`** — the whole app: FastAPI (Python, `uv`-managed) serving the JSON API **and** the
  Jinja/HTMX HTML frontend, on Render. (The old React/Vite SPA under `apps/web/` was retired in T60.)
- **`analytics/`** — Python pipeline, `uv`-managed (added in T30).
- **`docs/`** — requirements, tickets, and decision records.

**Auth & data:** users sign in via Supabase Auth (Spotify OAuth). The backend validates the
Supabase JWT server-side and owns long-term Spotify access by storing an encrypted refresh
token (AES-256-GCM). The Supabase Data API is disabled — tables are reached only through the ORM.

---

## 3. Running it locally

Local dev needs **one terminal** — the FastAPI app serves both the API and the HTML pages. You need
a root `.env` (secrets are git-ignored and shared separately; copy `.env.example` and ask Andrea for
the values).

```bash
# API + HTML frontend on :3001 (FastAPI). Visit http://127.0.0.1:3001/ for the pages, /api/* for the API.
cd backend && uv run uvicorn app.main:app --reload --port 3001
```

- **Test:** `cd backend && uv run pytest` (backend). Analytics: `cd analytics && uv run pytest`.

See CLAUDE.md for the env-var list and migration details (SQLModel + Alembic).

---

## 4. Branching & deploying

- **`develop`** is the integration branch — every change goes through a PR into `develop`.
- **`main`** is production — **Render** deploys the whole app (API + Jinja frontend) from `main`.
  `develop` reaches `main` only via a release PR (and only once env vars are set). **Never push to
  `main` or `develop` directly.** (The old Vercel SPA host was retired in T60.)
- Branch naming: `<type>/<ticket-id>-<slug>` (e.g. `feat/T10-posts-api`). One ticket = one PR.

CI (`.github/workflows/ci.yml`) runs the backend tests and a secret scan on every PR (the frontend
`web` build job was removed in T60 with the SPA).

---

## 5. Contributing

1. Read [`CLAUDE.md`](./CLAUDE.md) and the relevant ticket in `docs/plans/`.
2. Branch off `develop`, write the test first, keep the change scoped to one ticket.
3. Open a PR into `develop` (the template walks you through the checklist).
4. Record architecture decisions as ADRs in `docs/decisions/adr/`; keep docs in sync in the
   same PR.
