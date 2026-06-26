---
status: Backlog
priority: Medium
complexity: Low
category: Feature
tags: [backend, api, spotify, validation]
blocked_by: []
blocks: [044]
parent_ticket: null
---

# Feature: Currently-playing endpoint (T20)

## Rationale
The "now playing" badge is a small but high-visibility live touch on profiles and the feed. It needs a server endpoint that reads the user's current Spotify playback through our stored, server-refreshed token.

## Summary
A `GET /api/me/now-playing` endpoint that returns the authenticated user's currently-playing track (or an empty state), plus the `get_currently_playing` helper in the Spotify module.

## Source
- Spec reqs: **SP-1**, **UI-10** (backend half)
- ADRs: [ADR-0005](../../../decisions/adr/0005-identity.md) (server-side token refresh) · [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)

## Scope
### In Scope
- `backend/app/spotify.py` — add `get_currently_playing(user_id)` using `get_valid_access_token`.
- `backend/app/routers/now_playing.py` — `GET` returns the current track shape or an empty/`null` state on 204.

### Out of Scope
- The badge UI itself — wired in T44 (kept there to avoid overlapping `ProfilePage` edits).

## Validation & authz (ADR-0007 — required on this ticket)
- **Authorization:** `require_user` gates the route; it reads only the authenticated user's playback via their own stored token.
- **Schema:** normalize Spotify's response to a small typed shape; 204 (nothing playing) → `{ data: null }`, not an error.
- **Business rule:** handle a user with no linked Spotify (handle account) → graceful empty state, not 500.

## Current State (on `develop`)
- `backend/app/spotify.py` holds the server-side token refresh (`get_valid_access_token`, built on T06's encrypted `SpotifyToken` storage). No `get_currently_playing` yet.
- No now-playing router yet.
- `require_user` + encrypted `SpotifyToken` storage present.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/spotify.py` | MODIFY | add `get_currently_playing(user_id)` |
| `backend/app/routers/now_playing.py` | CREATE | `GET` currently-playing endpoint |
| `backend/tests/test_now_playing.py` | CREATE | tests |

## Testing Checklist
- [ ] no session → 401
- [ ] Spotify 200 (a track) → correct normalized shape
- [ ] Spotify 204 (nothing playing) → `{ data: null }`, 200
- [ ] handle user with no Spotify token → graceful empty state, not 500

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T02 done)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T20-now-playing`; one PR back into `develop` (never `main`).
