# ADR-0010: API on FastAPI (Python) + Render, persistence via SQLModel/Alembic

**Status:** Accepted (frontend decision later amended by [ADR-0013](0013-python-frontend.md))
**Date:** 2026-06-26
**Supersedes:** [ADR-0002](0002-api-and-persistence.md)

## Context

[ADR-0002](0002-api-and-persistence.md) put the API on Vercel serverless functions in
TypeScript, backed by Supabase Postgres through Prisma. That decision optimized for a single
Vercel deploy and zero-ops compute. It assumed a team that works in TypeScript.

That assumption is wrong for this team: **all three of us work in Python and none of us are
fluent in TypeScript.** Under ADR-0002 the entire backend — including the security-critical
auth and token-encryption code (T02) — is effectively written and maintained by AI, with no
team member able to read, review, or defend it. For a graded course project where we must
explain and own our system, a backend none of us can review is a liability, not a convenience.

Only three tickets are built (T00–T02); the ~30 remaining API tickets are specified but not yet
implemented. This is the cheapest point at which to change the backend stack.

The React frontend stays in TypeScript regardless — React is a JavaScript framework. So the
real choice is not "TypeScript vs Python" but "rely on AI for one language across the whole
stack" vs "own the backend in a language the whole team reads, and rely on AI only for the
React frontend." Auth/crypto is exactly the code we most need to be able to review.

## Decision

Serve the API from a **FastAPI** application (Python) hosted on **Render**, with persistence via
**SQLModel/SQLAlchemy** and migrations via **Alembic**. The React/Vite SPA continues to deploy
to **Vercel**, which rewrites `/api/*` to the Render backend so the browser still calls a
same-origin `/api/*` (no CORS).

**Supabase is unchanged** — Postgres, Auth, and Storage all stay. Only the middle layer (the API
runtime, the ORM, and the migration tool) changes:

- **Auth:** validate Supabase JWTs server-side with `supabase-py` `auth.get_user(token)` — same
  policy as before (no JWT secret), preserving the `Authorization: Bearer` contract.
- **Crypto:** AES-256-GCM via the `cryptography` package, reusing `TOKEN_ENC_KEY` and the exact
  `base64(iv).base64(tag).base64(ct)` encoding, so tokens written under ADR-0002 still decrypt.
- **DB:** the existing 14-table schema is mapped 1:1 in SQLModel; Alembic is baselined against
  the live schema (stamp, not recreate).

The frontend's API contract is preserved exactly: same `/api/*` paths, same request/response
shapes, same `{ data }` / `{ error }` envelope. No frontend code changes.

## Alternatives considered

- **Stay on ADR-0002 (Vercel TS + Prisma).** Lowest immediate effort, but leaves the whole
  backend — including auth/crypto — unreviewable by the team. Rejected: ownership and
  defensibility outweigh the rewrite cost while only 3 tickets exist.
- **Keep Prisma for migrations, read from Python via SQLAlchemy.** Less upfront translation, but
  keeps a Node toolchain nobody on the team understands and defines the schema twice. Rejected
  in favor of a single Python source of truth (removes the Prisma `migrate dev` hang workaround).
- **FastAPI on Vercel's Python serverless runtime.** Keeps one platform, but FastAPI is designed
  as a persistent ASGI app; running it serverless is an awkward, non-standard fit with cold
  starts. Rejected for a conventional persistent host.
- **Railway / Fly instead of Render.** Equivalent; Render chosen for the simplest dashboard-driven
  setup and a free tier adequate for a course project.

## Consequences

- **Two hosts instead of one:** frontend on Vercel, backend on Render. Backend env vars
  (`DATABASE_URL`, `DIRECT_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`,
  `SPOTIFY_CLIENT_ID/SECRET`, `TOKEN_ENC_KEY`) move to Render; the Vercel `/api/*` rewrite keeps
  the browser same-origin.
- **Render free tier sleeps** after inactivity (~30s cold start on first hit). Acceptable here;
  the Spotify snapshot job (T21) is cron-driven and tolerant.
- **The repo unifies on Python + React.** Backend and analytics ([ADR-0003](0003-analytics-runtime.md))
  share one language and the `uv` toolchain.
- **The ~30 backlog API tickets and CLAUDE.md are re-pointed** from Vercel-TS handlers to FastAPI
  routers + a `require_user` dependency. The Prisma migration workaround is replaced by standard
  Alembic.
- **Partial return to the original proposal.** ADR-0002 records that the project proposal wanted
  "Express on Render" before deviating to Vercel. This moves the API back onto a dedicated host
  (Render), now in Python/FastAPI rather than Express — still a deliberate deviation from
  ADR-0002 to defend in the final report, but one that re-converges with the proposal's host.

## Notes — runtime vs. local dev

- **Production API = a FastAPI server on Render** (`uvicorn app.main:app`). The Vercel deploy is
  the static SPA plus a rewrite of `/api/*` to the Render URL.
- **Local dev** mirrors ADR-0002's two-terminal model: Vite on `127.0.0.1:5173` proxies `/api` →
  `127.0.0.1:3001`, where `uvicorn --reload --port 3001` runs the same FastAPI app. Local reads
  the root `.env` (the `brink-dev` Supabase project), so local never touches prod data.
