---
status: Backlog
priority: High
complexity: Small
category: Feature
tags: [backend, spotify, listening, cron]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Feature: fresher listening history — tighter cron + sync-on-profile-visit (T100)

## Rationale
Listening history currently updates only when the snapshot cron fires (every 2 hours), so
your profile's "recent" list is stale most of the day. Worse, Spotify's recently-played API
only ever returns the **last 50 plays** — a heavy listener can burn through 50 plays in
under 2 hours, so plays are being silently LOST at the current cadence. This is partly a
correctness fix, and it's the data-freshness enabler for the rest of Wave 2 (T101's
share-now-playing fallback and T102's play counts read the `Play` table).

## Summary
Two independent halves:
1. **Tighten the cron** in `.github/workflows/snapshot.yml` from `0 */2 * * *` to
   `*/30 * * * *` (every 30 minutes). One-line change; the endpoint's dedup on
   `(userId, playedAt)` makes extra runs harmless.
2. **Sync on profile visit:** a new `POST /api/me/plays/refresh` endpoint that pulls the
   caller's own recently-played from Spotify and ingests it immediately — so opening your
   own profile shows up-to-the-minute history instead of waiting for the cron. The profile
   page fires it in the background after load (fire-and-forget).

## Source
- Spec reqs: **SP-2** (scheduled snapshot), **SP-5** (rate limits), **AN-7** (aggregations
  read `Play`)
- ADR: [ADR-0006](../../decisions/adr/0006-github-actions-cron.md) (GitHub Actions cron),
  [ADR-0011](../../decisions/adr/0011-rate-limiting.md) (rate limiting)

## Current State (verified 2026-07-23)
- `backend/app/routers/snapshot.py` already contains the full ingest pipeline:
  `_ingest_user(session, user_id, payload)` lands the raw payload in bronze and conforms
  Track/Play into silver with dedup. **Reuse it — do not write a second ingest.** It is
  module-level and takes exactly what the new endpoint has.
- `app.spotify.get_recently_played(session, user_id)` returns the payload or `None` on any
  degraded case (no linked Spotify, refresh failure, outage).
- Rate limiting: `app.rate_limit.enforce_rate_limit(session, subject, action, limit,
  window_seconds)` backed by the `RateLimitHit` table (ADR-0011) — see
  `routers/comments.py` for the canonical usage pattern.
- `/api/me/*` endpoints live in `backend/app/routers/me.py` (require_user pattern).
- The T61 route-inventory gate: add the new route to
  `backend/tests/test_api_surface.py` `EXPECTED_API_ROUTES` or the suite fails.

## Scope
### In Scope
- Cron cadence `0 */2 * * *` → `*/30 * * * *` (update the comment in the workflow too).
- `POST /api/me/plays/refresh` (in `me.py`): login required; throttled via
  `enforce_rate_limit` (suggested: action `"plays_refresh"`, limit 2 per 600s — Spotify-
  friendly and enough for a profile visit); calls `get_recently_played` then
  `_ingest_user` + commit; returns `{ data: { playsInserted: N } }`. A user with no linked
  Spotify (payload `None`) returns `{ data: { playsInserted: 0 } }` — a normal empty, not
  an error (matches the T20 degradation philosophy).
- Own-profile page: fire the refresh in the background after load (a few lines in an
  existing profile script or a tiny new one; only when viewing YOUR OWN profile — the
  template already knows `is_own`/viewer state). Fire-and-forget: no DOM update needed;
  the next render shows fresh data.
- Tests: endpoint auth (401), throttle (429 on the 3rd call within the window), inserts
  plays via the shared ingest (seed a stubbed `get_recently_played`), unlinked-user empty
  case, route inventory.

### Out of Scope
- Live-updating the listening section DOM after the background refresh (follow-up polish).
- Any change to the ingest/dedup logic itself.
- Now-playing (T20 already covers it; T101 consumes it).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `.github/workflows/snapshot.yml` | MODIFY | 30-minute cadence |
| `backend/app/routers/me.py` | MODIFY | the refresh endpoint |
| `backend/app/templates/profile.html` (+ a static js file) | MODIFY | background refresh on own profile |
| `backend/tests/test_me.py` | MODIFY | endpoint coverage |
| `backend/tests/test_api_surface.py` | MODIFY | route inventory (T61 gate) |
| `docs/plans/requirements.md` | MODIFY | SP-2 row note (at close-out) |
| `docs/plans/tickets/README.md` | MODIFY | record completion (at close-out) |

## Testing Checklist
- [ ] 401 without a session
- [ ] refresh ingests plays through the SHARED `_ingest_user` (no duplicated logic)
- [ ] double-run doesn't double-count (dedup holds through this path)
- [ ] 3rd call inside the window → 429 envelope
- [ ] unlinked user → `playsInserted: 0`, status 200
- [ ] own profile page includes the background-refresh call; other profiles don't
- [ ] full backend suite passes

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Notes / Risks
- **Shared dev/prod DB (T99 watch-out):** any manual testing writes real plays — use your
  own account, nothing destructive.
- GitHub cron is best-effort; `*/30` often fires late. Fine — the visit-triggered refresh
  is the freshness path, the cron is the completeness path.
- Do NOT mock `_ingest_user` in tests (testing-anti-patterns): stub only the Spotify HTTP
  boundary (`get_recently_played`), let the real ingest run against the test DB.
