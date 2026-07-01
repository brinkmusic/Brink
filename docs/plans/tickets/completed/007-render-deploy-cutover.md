---
status: Completed
priority: High
complexity: Medium
category: Chore
tags: [infra, deploy, render, vercel, migration]
blocked_by: [006]
blocks: [008]
parent_ticket: null
owner: Andrea
---

# Chore: Deploy FastAPI to Render + Vercel /api cutover (T07)

## Rationale
With the FastAPI app at parity for health + auth (T04–T06), production traffic must move to it.
FastAPI is a persistent server, so it runs on Render; the Vercel SPA rewrites `/api/*` to the
Render URL so the browser keeps calling same-origin `/api/*` with no frontend change
([ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md)).

## Summary
Stand up the Render web service for `backend/`, set its env vars, and update `vercel.json` to
build the frontend only and rewrite `/api/:path*` to the Render backend. Verify Spotify login
end-to-end against the new backend.

## Source
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md)
- Reqs: INFRA-1 (deploy), AUTH-* (login still works post-cutover)

## Scope
### In Scope
- Render web service: Build `uv sync`; Start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`;
  root directory `backend/`. Env vars set in Render: `DATABASE_URL`, `DIRECT_URL`, `SUPABASE_URL`,
  `SUPABASE_SERVICE_ROLE_KEY`, `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET`, `TOKEN_ENC_KEY`.
- `vercel.json`: frontend-only build (drop `prisma generate`); rewrite `/api/:path*` →
  `https://<render-app>/api/:path*`; keep the SPA catch-all rewrite.
- README/CLAUDE.md note of the new dev command (`uvicorn ... --port 3001`); Vite proxy unchanged.

### Out of Scope
- Removing the TS `api/` + Prisma (T08 — done only after the Render cutover is verified).
- Production Supabase project switch (separate concern; uses existing env wiring).

## Validation & authz (ADR-0007)
- Same-origin `/api/*` via the Vercel rewrite → no CORS surface added. Secrets live only in
  Render env (never committed). Service-role key stays server-side.

## Current State (on `develop` after T06)
- FastAPI app serves `/api/health` + `/api/auth/capture-spotify` at parity, tested.
- `vercel.json` currently builds the monorepo and serves the TS `api/` functions.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `vercel.json` | MODIFY | frontend-only build + `/api` rewrite to Render |
| Render dashboard | EXTERNAL | web service + env vars (not in repo) |
| `CLAUDE.md` / `README.md` | MODIFY | dev command + deploy topology note |

## Testing Checklist
- [ ] Render service boots; `GET <render-app>/api/health` → `{ data: { ok: true, db: true } }`
- [ ] Vercel preview: `/api/health` (proxied) returns OK from the browser origin
- [ ] Spotify login end-to-end against Render: creates `public.User` + encrypted `SpotifyToken`
- [ ] no CORS errors in the browser console (rewrite keeps same-origin)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T06 → blocked_by 006)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `chore/T07-render-deploy-cutover`; one PR into `develop`.
Production deploys from `main` (CLAUDE.md) — the Render env + `main` release PR are coordinated
so the cutover and the env vars land together. Keep the TS `api/` until this is verified (T08).

**⚠ `/api/state` coordination:** the rewrite sends **all** `/api/*` to Render, but the legacy
jsonblob `/api/state` (still used by the frontend mock path) is not reimplemented in FastAPI.
Before this cutover, either retire that path (T60) or keep `/api/state` on Vercel via a narrower
rewrite as a temporary shim. Decide with the team; don't cut over while the frontend still calls
`/api/state` or it will 404.
