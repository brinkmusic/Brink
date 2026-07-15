---
status: Completed
priority: Medium
complexity: Medium
category: Feature
tags: [frontend, backend, posts, spotify, validation]
blocked_by: [010]
blocks: []
parent_ticket: null
owner: Sebastian
---

# Feature: Post composer + Spotify catalog search (T40)

## Rationale
Users need a way to actually publish a post about a track. The composer pairs a Spotify catalog search (working even for handle users, via client-credentials) with the T10 posts endpoint.

## Summary
A `Composer` component plus a `GET /api/search` Spotify catalog-search endpoint (client-credentials, so handle users can search), wired into the feed so any user can search a track and publish a post.

## Source
- Spec reqs: **UI-1**
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md) (search is an expensive endpoint → rate-limited)

## Scope
### In Scope
- `backend/app/routers/search.py` — Spotify client-credentials catalog search (no user token needed).
- `apps/web/src/components/Composer.tsx` — search UI + caption + publish via `POST /api/posts` (T10).
- Wire into `FeedPage`.

### Out of Scope
- Posts endpoint (T10); the feed render (T41).

## Validation & authz (ADR-0007 — required on this ticket)
- **Schema (Pydantic):** validate the `q` query param; empty → 400.
- **Rate limiting:** catalog search is an expensive endpoint → per-user/IP cap via the shared store (ADR-0007 §5).
- **Authorization:** publishing goes through `POST /api/posts` (`require_user`); search itself may be open but rate-limited.

## Current State (on `develop`)
- `apps/web/src/pages/FeedPage.tsx` imports `getFeed` from `lib/data` (mock).
- `lib/spotify-api.ts` exists (client helpers). No search router (`backend/app/routers/search.py`), no `Composer.tsx`.
- Posts endpoint comes from T10 (`blocked_by: [010]`).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/search.py` | CREATE | Spotify client-credentials catalog search |
| `apps/web/src/components/Composer.tsx` | CREATE | search + caption + publish |
| `apps/web/src/pages/FeedPage.tsx` | MODIFY | mount the composer |
| `backend/tests/test_search.py` | CREATE | search endpoint tests |

## Testing Checklist
- [x] empty `q` → 400
- [x] search returns normalized track results
- [x] publishing from the composer creates a persisted `Post` (via T10)
- [x] a handle user (no Spotify) can still search and publish (search uses an app-level token)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T10 → blocked_by 010)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T40-composer`; one PR back into `develop` (never `main`). Owner: Sebastian (UI) + Andrea (`backend/app/routers/search.py`).

## Outcome (as built)
Both halves built in one PR (ADR-0013 Python frontend). Andrea gave the OK to build the backend
half.

- **Search endpoint (backend):** `backend/app/routers/search.py` — `GET /api/search?q=` (login
  required, per-user rate-limited, empty `q` → 400). It calls a new **client-credentials** path in
  `backend/app/spotify.py` (`_get_client_credentials_token` with an in-process cache +
  `search_tracks`) so search works with an **app-level** Spotify token — no user Spotify link
  needed (handle users can search). Returns normalized camelCase `TrackOut`. A Spotify outage /
  missing credentials returns a clean 502, never a 500. Tests: `backend/tests/test_search.py`.
- **Composer (frontend):** a card at the top of the feed (`feed.html` + `static/composer.js`):
  debounced search → pick a result → optional caption → Share, which `POST /api/posts` (T10, source
  MANUAL) then reloads the feed so the new post shows at the top. Track titles rendered with
  `textContent` (no HTML injection).
- **Files:** `backend/app/routers/search.py`, `backend/app/spotify.py`, `backend/app/main.py`,
  `backend/app/templates/feed.html`, `backend/app/static/composer.js`, `backend/app/static/brink.css`,
  `backend/tests/test_search.py`, `backend/tests/test_pages.py`. Satisfies **UI-1**. Full suite green (162).
