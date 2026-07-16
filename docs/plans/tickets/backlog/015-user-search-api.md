---
status: Backlog
priority: High
complexity: Low
category: Feature
tags: [backend, social, search, enablement-gap]
blocked_by: []
blocks: [046]
parent_ticket: null
owner: Andrea
---

# Feature: User search API — `GET /api/users/search?q=` (T15)

## Rationale
Top finding of the [2026-07-15 frontend-enablement audit](../../reviews/2026-07-15-frontend-enablement-gaps.md):
the follow feature (T13) shipped with **no way to find a user**. The only path to a profile is
clicking a feed author — but your feed only shows people you already follow (plus yourself), so a
new user can never discover anyone (chicken-and-egg). `/api/search` cannot be reused: it searches
**Spotify tracks**, not Brink users.

## Summary
A login-gated, rate-limited `GET /api/users/search?q=` that matches `q` case-insensitively
against `User.handle` and `User.display_name` (prefix/substring via `ILIKE`), returning a small
list of user DTOs (id, handle, displayName, isArtist) capped at ~20, for the T46 search UI to
render as links to `/u/{handle}`.

## Source
- Spec reqs: **BE-4** (follow needs discoverability to be usable), **UI-5**
- Patterns: T10's rate-limit helper (ADR-0011) + camelCase DTOs (ADR-0012); T40's
  `routers/search.py` as the structural template for a search endpoint.

## Scope
### In Scope
- `GET /api/users/search?q=` in a new `routers/users.py` (or extend `routers/search.py` — pick
  one, say which in the PR): login-gated (`require_user`), rate-limited, `q` trimmed with a
  minimum length of 1–2 chars, `ILIKE '%q%'` on handle + display name, exclude no one (finding
  yourself is fine), cap 20, order by handle.
- `UserSearchOut` DTO (camelCase per ADR-0012).
- Tests: match on handle, match on display name, case-insensitivity, empty query rejected,
  login required, rate limit fires.

### Out of Scope
- The search box UI (T46). Follower/following lists (T16). Any ranking/fuzzy matching.

## Validation & authz (ADR-0007)
- Login-gated so it can't be scraped anonymously; rate-limited like every social endpoint.
- Read-only — no ownership concerns.

## Current State (on `develop`)
- No user-lookup endpoint of any kind. `routers/search.py` = Spotify track search only.
- Profile page `/u/{handle}` + follow API (T13/T43) both work once you can reach a profile.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/users.py` | CREATE | the search endpoint + DTO |
| `backend/app/main.py` | MODIFY | mount the router |
| `backend/tests/test_users_search.py` | CREATE | behavior + gating + rate-limit tests |

## Testing Checklist
- [ ] finds by handle substring and display-name substring, case-insensitive
- [ ] anonymous request → 401 envelope; rate limit fires on hammering
- [ ] cap respected; short/empty `q` rejected with the standard error envelope

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (none)
- [x] Scope boundaries defined

## Notes
Branch `feat/T15-user-search-api`. Small; pairs with T46 for the visible feature.
