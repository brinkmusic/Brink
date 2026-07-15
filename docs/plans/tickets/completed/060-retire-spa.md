---
status: Completed
priority: Medium
complexity: Medium
category: Tech-Debt
tags: [cleanup, frontend, infra, spa-retirement]
blocked_by: []
blocks: [061]
parent_ticket: null
owner: Sebastian
---

# Feature: Retire the React/Vite SPA (T60, re-scoped from "retire mocks")

## ✅ Done (2026-07-15) — code/docs; two owner infra steps remain
Deleted `apps/web/` entirely (35 files: SPA source, mocks, lib, pages, components, `vercel.json`).
Removed the `web` CI job, the `apps/web/src/` docs-sync path, the `apps/web` Dependabot group, and the
PR-template frontend checkbox. Confirmed the git-hooks secret guard survives (the `prepare` script was
already in the **root** `package.json`). Synced README, root `package.json`, `.env.example`,
`.gitignore`, the `close-session`/`get-me-started` skills, and `CLAUDE.md`; flipped **BE-2 / DATA-4 /
UI-9** ✅; appended a dated "SPA retired" note to ADR-0013. Backend suite green (179). Also fixed a
dangling comment in `backend/app/routers/auth.py` (comment-only).
**⚠ Still needs Andrea (infra — can't be done in the PR):** (1) drop the required **`web`** status
check from `develop` + `main` branch protection so PRs don't hang; (2) **decommission the Vercel
project**. **Follow-up flagged:** ticket **T003** (email auth) still references deleted `apps/web`
files and needs its own re-scope to Jinja.

## ⚠ Re-scoped (2026-07-15)
Originally "delete the mock data files from `apps/web/`." That framing is obsolete: the SPA pages
(`FeedPage`, `ProfilePage`, `AnalyticsPage`, `PredictPage`, `ArtistPage`, `PostCard`) *import* those
mock files and were **never wired to the real API** — under [ADR-0013](../../../decisions/adr/0013-python-frontend.md)
the SPA was replaced wholesale by the Jinja frontend, which is now **live in production** (feed,
profile+listening, artist page, server-side login). So the mocks aren't the dead weight — the **whole
`apps/web/` SPA is** — and you can't delete the mocks without deleting the pages that use them. This
ticket therefore becomes the ADR-0013 endgame: **retire the SPA entirely.** T45 no longer blocks it
(that block assumed we'd wire live analytics *into* the SPA; we're deleting it instead), so
`blocked_by` drops to `[]`.

## Rationale
The Jinja/HTMX frontend (`backend/app/templates|static|routers/pages.py`) has reached parity for
everything that actually works and is the live production frontend. The React/Vite SPA in `apps/web/`
is now unreferenced, mock-driven dead weight and a correctness/security risk (it can still render fake
data). ADR-0013 always planned to retire it "once the Python pages reach parity" — that point is here.

## Summary
Delete the `apps/web/` SPA, decommission its Vercel deployment, remove the frontend-build CI job, and
sync the docs/ADR that describe the two-frontend transition. No feature is lost: the SPA's analytics
and predict pages were mock (fake) data, and every real feature has a live Jinja equivalent.

## Source
- Spec reqs: **BE-2** (final), **DATA-4**, **UI-9**
- ADRs: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (SPA retirement — this executes it) ·
  [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md) (TS backend retired in T08) ·
  [ADR-0002](../../../decisions/adr/0002-api-and-persistence.md) (jsonblob `/api/state` superseded)

## Scope
### In Scope (this PR)
- **Delete the entire `apps/web/` directory** (SPA source, `mocks/`, `lib/` incl. `data.ts`/
  `analytics.ts`/`backend.ts` (the `/api/state` stub), all `pages/`, `components/`, `vercel.json`,
  `package.json`, `package-lock.json`, `.env.example`).
- **CI:** remove the `web` (lint + build) job from `.github/workflows/ci.yml`; remove the
  `apps/web/src/` branch from the `docs-sync.yml` "substantive code" regex; drop the `apps/web` entry
  from `.github/dependabot.yml`; drop the frontend-build checkbox from `pull_request_template.md`.
- **Git hooks:** the pre-commit secret guard is currently enabled by `apps/web/package.json`'s
  `prepare` script (`git config core.hooksPath .githooks`, run by `npm install`). Deleting `apps/web`
  removes that wiring — **move the `prepare` script to the root `package.json`** so the guard still
  auto-installs (don't silently drop the secret guard).
- **Docs:** update `README.md` (remove SPA layout/commands), root `package.json` description, and
  `CLAUDE.md` (Commands, Layout, Deployment topology, Ownership, Watch-outs — drop the SPA and the
  `/api/state` note; state that Render serves the sole frontend). Flip **BE-2 / DATA-4 / UI-9** in
  `requirements.md`. Add a dated "**Update (T60): SPA retired**" note to ADR-0013 (append-only — do
  not rewrite its decision text).

### ⚠ Owner-only steps (cannot be done in the PR — Andrea)
These must happen *around* the merge or CI/deploys break:
- **Remove `web` from the required status checks** on `develop` **and** `main` branch protection.
  It's currently required, so once the job is deleted every future PR would hang forever waiting on a
  check that never runs. Do this as the PR merges.
- **Decommission the Vercel project** (or at least stop it deploying from `main`); the `apps/web`
  root-directory build no longer exists.
- *(Optional cleanup)* drop the `brink-theta.vercel.app` URLs from the Supabase Auth + Spotify
  redirect allow-lists.

### Out of Scope
- Any Jinja frontend behavior change; the analytics page (T45) — separate ticket.

## Validation & authz (ADR-0007)
- Pure removal + infra. The guarantee: production (the Jinja app on Render) is unaffected, CI is green
  without the `web` job, and no tracked file still references `apps/web/` or `/api/state`.

## Current State (on `develop`)
- `apps/web/` present and still deployed to Vercel from `main` (the ADR-0013 "fallback"). Its pages
  import `mocks/feed.ts`, `mocks/stats.ts`, `lib/data.ts`, `lib/analytics.ts`, `lib/backend.ts`
  (`/api/state`, 404 since T08). The Jinja frontend is the live production UI.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `apps/web/` (whole dir) | DELETE | retire the SPA |
| `.github/workflows/ci.yml` | MODIFY | remove the `web` lint/build job |
| `.github/workflows/docs-sync.yml` | MODIFY | drop `apps/web/src/` from the code regex |
| `.github/dependabot.yml` | MODIFY | remove the `apps/web` npm ecosystem |
| `.github/pull_request_template.md` | MODIFY | remove the frontend-build checkbox |
| `package.json` (root) | MODIFY | move the `prepare` hooks script here; drop SPA mention |
| `README.md` | MODIFY | remove SPA layout + commands |
| `CLAUDE.md` | MODIFY | Commands / Layout / Deployment topology / Ownership / Watch-outs |
| `docs/plans/requirements.md` | MODIFY | flip BE-2, DATA-4, UI-9 |
| `docs/decisions/adr/0013-python-frontend.md` | MODIFY | append a dated "SPA retired (T60)" note |

## Testing Checklist
- [ ] `grep -rn "apps/web\|/api/state" .` returns nothing in tracked files (outside this ticket's history)
- [ ] backend suite green (`cd backend && uv run pytest`); production Jinja UI unaffected
- [ ] a test PR's CI passes with **no** `web` job (and branch protection no longer requires it)
- [ ] the pre-commit secret guard still installs from the root `prepare` script
- [ ] Vercel no longer deploys from `main` (owner-confirmed)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (parity reached; T45 decoupled → `blocked_by []`)
- [x] Scope boundaries defined (incl. owner-only infra steps)

## Notes
Branch off `develop` as `chore/T60-retire-spa`; one PR into `develop` (never `main`). Sequence the
branch-protection `web`-check removal with the merge so no PR gets stuck. Owner: Sebastian (frontend
deletion + CI/doc edits); Andrea does the Vercel + branch-protection infra steps.
