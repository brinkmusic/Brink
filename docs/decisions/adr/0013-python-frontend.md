# ADR-0013: Frontend served from FastAPI (Jinja2 + HTMX), retiring the React/Vite SPA

**Status:** Accepted
**Date:** 2026-07-07
**Amends:** [ADR-0010](0010-fastapi-render-backend.md) (which kept the frontend on React/TypeScript)

## Context

[ADR-0010](0010-fastapi-render-backend.md) moved the API from TypeScript/Vercel to
FastAPI/Python because **all three of us work in Python and none of us are fluent in
TypeScript** — and for a graded project we must be able to read, review, and defend our own
system. That ADR deliberately drew the line at the API and left the frontend on React/Vite,
reasoning that "React is a JavaScript framework" so the browser layer stays TypeScript
regardless.

Two things have changed since then that make it worth revisiting that line:

1. **The exact same ownership argument applies to the frontend.** The React/TypeScript SPA is
   code none of us can comfortably read or defend either — it is effectively AI-written and
   AI-maintained, the same liability ADR-0010 rejected for the backend.
2. **The frontend's real work has not been built yet.** T08 has removed the last TypeScript
   backend, so the SPA is now the *only* TypeScript left in the repo. The live-data screens
   (T40–T45, T51) are all still in the backlog — only the login shell and mock-driven pages
   exist. As with ADR-0010's timing argument, this is the cheapest point to change stacks:
   we build the screens in Python instead of rewriting finished ones.

The deliverable bar for the UI is **"functional, presentable"**, not a polished consumer app —
which removes the main reason to keep a heavyweight SPA framework. The team agreed to proceed
on 2026-07-07.

## Decision

Serve the frontend **from the existing FastAPI backend** using **Jinja2 server-rendered HTML
templates**, with **HTMX** for the interactive bits (reacting to a post, submitting the
composer, live-updating a feed) instead of a client-side React app. **Retire the React/Vite SPA
in `apps/web/`** once the Python pages reach parity.

- **One language, one codebase, one host.** The UI lives beside the API in `backend/`
  (`backend/app/templates/`, `backend/app/static/`, `backend/app/routers/pages.py`), so the
  whole product is Python + HTML the team can read and defend.
- **Reuse everything ADR-0010 built.** Auth (`deps.py` / Supabase JWT validation), the models,
  the posts API, the `{data}|{error}` envelope, rate limiting — all unchanged. Page routes call
  the same internal logic the JSON API does.
- **Deployment simplifies.** The frontend no longer deploys separately to Vercel; Render serves
  both the API and the pages, so the `apps/web/vercel.json` `/api/*` rewrite is no longer needed.
- **Supabase is unchanged** — Postgres, Auth, and Storage all stay exactly as-is.

The frontend tickets (T40–T45, T51, T60) move from "React component" to "Jinja template + HTMX +
a FastAPI page route," and their owner (Sebastian) works in Python from here. **Tracked follow-up:**
re-pointing the wording in those individual ticket files is done as each ticket is picked up, not in
this ADR's first PR (same pattern as deferred ticket close-outs), so the claim here is not stranded.

This ADR is delivered incrementally. The first slice is the landing page + a read-only feed (this
PR): the Jinja + static-file plumbing plus `/` and `/feed` routes, touching none of the backend's
data-writing, auth, or models. **Server-side Spotify login is deferred to [T09](../../plans/tickets/backlog/009-server-side-spotify-login.md)**
(owned by Andrea, auth/crypto area) — ADR-0013 removes the SPA's Supabase JS client, so login is
rebuilt server-side there; T09 is blocked by this PR merging. The remaining live-data screens follow
in subsequent PRs.

## Alternatives considered

- **Keep the React/Vite SPA (status quo, ADR-0010's line).** Zero migration, already deployed.
  Rejected for the same reason ADR-0010 rejected the TS backend: it is a core part of a graded
  system that no team member can own or defend, and its real screens are unbuilt so the sunk
  cost is low.
- **Streamlit (pure Python, no HTML).** Fastest to write and no HTML at all. Rejected: it is
  built for single-user data dashboards and fights exactly our hard cases — Supabase/Spotify
  OAuth login and a multi-user social feed with per-user sessions.
- **Reflex (React-like apps written in Python).** Keeps richer interactivity in pure Python, but
  it is newer, compiles to a React app under the hood (reintroducing the JS build toolchain we
  are trying to drop), and is a larger dependency to defend. Rejected for a server-rendered
  approach that is simpler to explain.

## Consequences

- **Auth flow needs re-work (the main risk).** Spotify sign-in currently runs client-side via
  `supabase-js` in the browser. A server-rendered app must either keep a *small* amount of JS
  for the Supabase OAuth handshake, or move to a server-side OAuth exchange. This is the biggest
  unknown and is spiked before the login button is wired. Serving pages from a new origin also
  means the Spotify/Supabase **redirect-URL allow-lists must be updated**, or sign-in breaks.
- **`apps/web/` is removed** once parity is reached; the Vercel project and its `/api/*` rewrite
  are decommissioned (a follow-up like the T08 backend teardown). Until then the SPA stays as a
  fallback so we are never without a working UI.
- **Scope should be trimmed to protect the 2026-07-30 deadline** — the artist portal (T51/T52)
  and the fancy analytics visuals (T45) are the first candidates to cut so the core social +
  profile experience lands solid.
- **`backend/` gains a web-page dependency** (`jinja2`; HTMX is a single static file, no build
  step) and a `templates/` + `static/` layer. The API's JSON contract is unaffected — pages and
  JSON endpoints coexist.
- **The repo fully unifies on Python** (+ HTML/HTMX). There is no longer any TypeScript in the
  project once `apps/web/` is retired.

## Update — 2026-07-15 (T60): SPA retired

The retirement this ADR planned is done. The Jinja/HTMX frontend reached parity (landing, server-side
Spotify login, feed with composer/reactions/comments, profile with follow + listening summary, artist
page) and is the live production frontend on Render. **T60 deleted `apps/web/` entirely**, removed the
`web` CI build job (and its branch-protection required check), the `apps/web` Dependabot group, the
`/api/state` legacy path, and the Vercel deployment. The repo now has no TypeScript. The only feature
that never had a real implementation on either frontend — the analytics page — remains open as T45.
