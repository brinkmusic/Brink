# ADR-0002: API and persistence on Vercel serverless + Supabase + Prisma

**Status:** Accepted
**Date:** 2026-06-22
**First captured as:** spec decision-log row A

## Context

Brink needs real relational data and a schema, a single clean deploy, and no cold-start stall on the read paths the UI depends on. The starting point was a Vercel function writing to jsonblob.com — a public, unauthenticated JSON store with no Postgres, Prisma, or Express. The proposal specified "Express on Render."

## Decision

Serve the API from **Vercel serverless functions** backed by **Supabase (Postgres)** through **Prisma**. Supabase is chosen over Neon to consolidate database, auth, and storage on one platform.

## Alternatives considered

- **Express on Render (proposal's choice)** — separate host to operate, cold-start stall, no consolidation benefit; deviating is deliberate and documented.
- **Neon for Postgres** (an alternative we weighed, not the proposal's choice) — solid DB, but leaves auth and storage as separate vendors. Supabase folds DB + Auth + Storage into one.
- **Cloudflare (Pages + Workers + D1/R2)** — strong platform, but its native DB is **D1 (SQLite)**, not Postgres: the Python analytics pipeline reads the DB over the Postgres wire protocol ([ADR-0003](0003-analytics-runtime.md)), which D1 can't serve, so we'd still need Supabase/Neon for Postgres — Cloudflare can't consolidate, only add compute. Workers' V8-isolate runtime also complicates Prisma (needs the edge driver adapter + Hyperdrive) versus Vercel's plain Node runtime where Prisma is frictionless. R2 storage is good, but doesn't outweigh the above.
- **Firebase / self-hosted (Postgres + MinIO + Keycloak)** — Firebase is a document store, not real relational Postgres (fails the graded requirement); self-hosting is far more ops than the timeline allows.
- **ORM: raw SQL (`pg`/postgres.js) or Drizzle instead of Prisma** — raw SQL drifts types from the schema and needs hand-rolled migrations; Drizzle is lighter but the team knows Prisma, and Prisma's schema file doubles as the documented data model + a versioned `migrate` workflow.
- **Compute: Railway/Fly/EC2 or Supabase Edge Functions instead of Vercel** — a dedicated Node host adds ops/cost for this small API; Edge Functions would consolidate vendors but the SPA already deploys to Vercel with stronger preview-deploy DX, and the API lives next to the app.

## Consequences

- One vendor for DB + Auth + Storage, versus both the proposal's split (Postgres + Express on Render, Cloudinary for storage) and the multi-vendor alternative we considered (Neon + Cloudinary + Resend).
- Supabase free tier lacks Neon-style branching, so dev/prod separation uses **two projects** (`brink-dev`, `brink-prod`).
- **Deviation from the proposal's "Express on Render"** — must be defended in the final report.

## Notes — runtime vs. local dev (don't confuse the two)

- **Production API = Vercel serverless functions only.** Handlers are `export default (req, res) => …` in `api/*.ts`; Vercel invokes them directly. There is no deployed Express server and nothing on Render.
- **The `express` dependency is local-dev only.** `scripts/dev-api.ts` (run via `npm run dev:api`) mounts the same `api/*.ts` handlers on `127.0.0.1:3001`; Vite proxies `/api` → `:3001`. It exists because the handlers are plain `(req, res)` functions, so a ~30-line Express shim reproduces Vercel's routing exactly. Seeing `express` in `package.json` does **not** mean the proposal's Express/Render backend was used.
- **Local always targets `brink-dev`.** `npm run dev:api` loads the root `.env` (`SUPABASE_URL` → the `brink-dev` project), so local runs can never touch `brink-prod` data.
- **`vercel dev` is forbidden** (CLAUDE.md). It links the repo to the cloud Vercel project and pulls **prod** env vars down, so "local" code could silently run against `brink-prod`. The Express harness reads only the on-disk `.env`, so it structurally can't do that.
