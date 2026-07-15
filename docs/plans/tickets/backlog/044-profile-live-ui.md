---
status: Backlog
priority: High
complexity: Medium
category: Feature
tags: [frontend, backend, profile, spotify, listening]
blocked_by: []
blocks: [060]
parent_ticket: null
owner: Andrea
---

# Feature: Profile page — your listening summary (T44, re-scoped)

## Rationale
Per [ADR-0014](../../../decisions/adr/0014-feed-manual-posts-listening-summary.md), a user's Spotify
listening surfaces as a **compact summary on their profile** (not auto-posted to the feed). This turns
the bare `/u/{handle}` page (which today shows only display name + posts, from T43) into the real
"what this person actually listens to" surface — built entirely from data we **already have** (the
snapshot `Play` rows, T21) plus the now-playing endpoint (T20). No analytics engine required.

## Re-scope note (why this ticket changed)
This ticket previously targeted a **React SPA** (`ProfilePage.tsx`, `StreakHeatmap`, `CompatDonut`)
and bundled the listening stats together with **cluster + compatibility**. Two corrections:
- **Stack:** per [ADR-0013](../../../decisions/adr/0013-python-frontend.md) the frontend is now
  **Jinja templates + a `pages.py` route** served by FastAPI — not React.
- **Split:** cluster/compatibility (and top *genres*) need the analytics spine (T31/T33/T35), which is
  unbuilt. Those are **deferred** (see below) so the listening summary — the ADR-0014 deliverable —
  can ship now. Per owner decision, the minimal live-stats aggregation (formerly T14/AN-7) is folded
  **into this one server-rendered ticket** rather than a separate backend API.

## Summary
Server-render `/u/{handle}` to show: a now-playing badge (own profile), top tracks, top artists,
recent listens, 30-day play total, listening streak, follower/following counts, and the user's posts —
with graceful empty and "link Spotify" states. A small shared `stats.py` computes the aggregations as
SQLModel/SQLAlchemy group-bys over `Play` (ADR-0003: computed live on read, no `UserStats` table).

## Source
- Spec reqs: **UI-6** (listening-stats portion), **UI-10** (now-playing on profile), **AN-7** (live
  listening aggregation, moved here from T14)
- ADRs: [ADR-0014](../../../decisions/adr/0014-feed-manual-posts-listening-summary.md) ·
  [ADR-0013](../../../decisions/adr/0013-python-frontend.md) ·
  [ADR-0003](../../../decisions/adr/0003-analytics-runtime.md) (on-read stats) ·
  [ADR-0005](../../../decisions/adr/0005-identity.md) (handle users)

## Scope
### In Scope (all buildable now — no analytics dependency)
- `backend/app/stats.py` — live aggregation helpers over `Play` (joined to `silver.Track`):
  top tracks, top artists, recent listens, 30-day play count, listening streak (consecutive days).
- `backend/app/routers/pages.py` — extend the `/u/{handle}` route to assemble the stats +
  follower/following counts + (own profile only) the now-playing track.
- `backend/app/templates/profile.html` — render the summary, a now-playing badge, the existing posts
  list, and graceful **empty** (no plays) + **"link Spotify"** (handle-only user) states.
- Now-playing badge on **your own** profile via `GET /api/me/now-playing` (T20).

### Out of Scope / Deferred (blocked on the analytics spine — build when it lands)
- **Top genres** — needs the Kaggle genre join (T31); `silver.Track` has no `genre` column yet.
- **Cluster / "taste" label** (T33) and **compatibility** vs the viewer (T35). These remain in a
  slimmed **T14** (backend, still `blocked_by [033, 035]`); the template is laid out to slot them in.
- **Now-playing on *other people's* profiles** — T20 is "me"-scoped; showing another user's live
  track needs a new per-user endpoint. Small follow-up, not required for this ticket.

## Validation & authz (ADR-0007)
- `{handle}` resolves to a user or renders the existing "profile not found" page (no 500).
- Reads only; aggregation reflects current `Play` rows. Now-playing degrades to hidden when nothing
  is playing / the user has no linked Spotify (reuses T20's graceful-empty contract).
- An empty or handle-only user renders zeros/prompts, never an error.

## Current State (on `develop`, now in production)
- `/u/{handle}` route + `profile.html` exist (T43) — render display name, follow button, and the
  user's posts only. `profile_missing.html` handles unknown handles.
- `Play` (snapshot data, T21), `Follow` (T43), and `GET /api/me/now-playing` (T20) all exist. No
  `stats.py` yet.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/stats.py` | CREATE | live listening group-bys over `Play` (top tracks/artists, recent, 30-day, streak) |
| `backend/app/routers/pages.py` | MODIFY | `/u/{handle}` assembles stats + counts + own-profile now-playing |
| `backend/app/templates/profile.html` | MODIFY | render summary + now-playing badge + empty / link-Spotify states |
| `backend/tests/test_stats.py` | CREATE | aggregation correctness + empty-state tests (FK-enforced fixture) |

## Testing Checklist
- [ ] no plays → zeroed/empty summary, page renders 200 (not 500)
- [ ] seeded plays → correct top tracks, top artists, recent-listens order, 30-day count, streak
- [ ] follower/following counts correct
- [ ] own profile shows now-playing badge (current track) / badge hidden when nothing playing
- [ ] handle-only user (no linked Spotify) sees the "link Spotify" prompt
- [ ] unknown handle → "profile not found" page, no crash

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T20/T13/T21 all done → `blocked_by []`; analytics parts deferred to T14)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T44-profile-listening-summary`; one PR back into `develop` (never
`main`). TDD: write the `stats.py` aggregation tests first (use the FK-enforcing `db_session`/`fk_session`
fixture — see T62). Reuse `build_feed`'s track/author DTO shaping where it fits rather than
re-deriving. Owner: Andrea (folded backend stats + server-rendered page into one ticket per ADR-0013).
