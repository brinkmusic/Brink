---
status: Backlog
priority: High
complexity: Small
category: Feature
tags: [frontend, backend, feed, composer, spotify]
blocked_by: []
blocks: []
parent_ticket: null
owner: Sebastian
---

# Feature: one-tap "Share what you're hearing" (T101)

## Rationale
BeReal's core insight: effortless, in-the-moment, *authentic* posting beats composed
posting. Brink's version — a single tap that shares the song you're playing right now —
is the most music-native action the app can offer, and it feeds the feed: more posts with
zero typing. All the plumbing exists (T20 now-playing + T10 posts API); this ticket is the
glue and the button.

## Summary
A "🎧 Share what you're hearing" button in the feed's composer area. Tapping it calls
`GET /api/me/now-playing`; if a track is playing, it drops that track into the EXISTING
composer's selected state (title/artist shown, optional caption box, Share button) so the
user confirms with one more tap — same publish path, no new posting code. If nothing is
playing (or Spotify isn't linked), the composer status line explains why, and nothing
breaks.

## Source
- Spec reqs: **UI-1** (composer), **SP-1/UI-10** (now-playing surface), **BE-3** (create post)
- ADR: [ADR-0013](../../decisions/adr/0013-python-frontend.md) (buildless Jinja/JS frontend)

## Current State (verified 2026-07-23)
- `GET /api/me/now-playing` (T20, `routers/now_playing.py`) returns
  `{ data: { isPlaying, track: { spotifyId, title, artistName, albumArtUrl, popularity } } }`
  or `{ data: null }` for EVERY empty/degraded case (nothing playing, no linked Spotify,
  outage) — the frontend needs exactly one null check.
- The composer (T40, `templates/feed.html` + `static/composer.js`) already has: a
  `.composer-selected` panel (track title/artist + caption input + Share), a
  `#composer-status` aria-live line for feedback, and a publish function that POSTs
  `/api/posts` with `CreatePostBody { track: TrackIn, source, caption? }` (camelCase).
- `PostSource` enum: `MANUAL` | `SPOTIFY`. The `SPOTIFY` value exists precisely for
  "came from their Spotify activity" — use it for these posts so they're distinguishable
  later (feed renders both kinds identically today; no template change needed for that).

## Scope
### In Scope
- The button in the composer card (near the search input), wired in `composer.js` (this is
  composer behavior — extend the existing file rather than adding a new one).
- On tap: disable button → fetch now-playing → if `data` present, populate the SAME
  selected-track state the search flow uses (so caption + Share + Cancel all just work)
  and set `source: "SPOTIFY"` for the eventual publish (search-flow posts stay `MANUAL`).
- If `data` is null: status line copy like "Nothing playing right now — start a song on
  Spotify and try again." (Or, for handle-only accounts, the same message is fine — the
  API can't distinguish, and that's acceptable v1.)
- Status/disabled states per the T81 accessibility conventions (aria-live status,
  `aria-busy` while fetching).
- Tests (template/JS-source level, per the repo pattern): button markup present + wired;
  composer.js contains the now-playing fetch + null-handling; a posts-API test asserting a
  `SPOTIFY`-source post round-trips (if not already covered by T10 tests — check first).

### Out of Scope
- Recent-plays fallback chips when nothing is playing (stated follow-up — pairs well with
  T100's fresher `Play` data).
- Any feed rendering change for SPOTIFY-source posts (identical cards is correct v1).
- Auto-posting without confirmation (the norm is one-tap TO the composer, not zero-tap
  publishing — the user always sees what they're about to share).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/templates/feed.html` | MODIFY | the button in the composer card |
| `backend/app/static/composer.js` | MODIFY | fetch now-playing → selected state → publish with SPOTIFY source |
| `backend/app/static/brink.css` | MODIFY | button styling (existing .btn system) |
| `backend/tests/test_pages.py` | MODIFY | markup + script-source assertions |
| `docs/plans/requirements.md` | MODIFY | UI-1/UI-10 rows (at close-out) |
| `docs/plans/tickets/README.md` | MODIFY | record completion (at close-out) |

## Testing Checklist
- [ ] the button renders in the composer and is wired to the new handler
- [ ] composer.js fetches `/api/me/now-playing` and handles the null case via the status line
- [ ] a now-playing selection publishes with `source: "SPOTIFY"`; search flow stays `MANUAL`
- [ ] status/disabled states follow the T81 conventions
- [ ] full backend suite passes

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Notes / Risks
- The now-playing endpoint hits Spotify live — the button should tolerate a slow (~1–2s)
  response with its busy state, and the T20 design already guarantees it never errors on
  the normal empty cases.
- Rate limiting on `POST /api/posts` (ADR-0011) already covers abuse of one-tap posting;
  no new limits needed.
- Soft ordering: works fine standalone, but T100 first makes the whole listening surface
  feel consistent.
