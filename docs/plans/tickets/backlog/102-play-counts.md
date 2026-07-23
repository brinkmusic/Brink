---
status: Backlog
priority: Medium
complexity: Small
category: Feature
tags: [backend, frontend, feed, listening, stats]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Feature: play counts on feed cards — "played 9 times by andrea" (T102)

## Rationale
Last.fm proved people love seeing play counts: "×14 plays" turns raw history into identity
("I'm *obsessed* with this song"). Brink can go one better with an endorsement signal no
mainstream social app has: on a shared song, show how many times the AUTHOR has actually
played it. "andrea has played this 9 times" is a far stronger recommendation than a
caption. The data already exists in `silver.Play`; this is one batched query plus a line
of template.

## Summary
Each song post in the feed gains an optional play-count line: when the post's author has
played the shared track at least twice, the card shows "▶ played N times by {author}"
(one play = they just heard it; from two it's a signal — hide below that). Computed in
`build_feed` as one grouped query over the exact (author, track) pairs in the feed batch,
following the established no-N+1 pattern.

## Source
- Spec reqs: **UI-2** (feed cards), **AN-7** (aggregations over `Play`)
- ADRs: [ADR-0012](../../decisions/adr/0012-dto-allowlist.md) (DTO allow-list),
  [ADR-0014](../../decisions/adr/0014-feed-manual-posts-listening-summary.md) (listening
  data surfaces)

## Current State (verified 2026-07-23)
- `silver.Play` rows: `(user_id, track_id, played_at)`, written by the T21 snapshot (and
  T100's refresh, if that lands first — not a dependency).
- `backend/app/routers/feed.py` `_build_song_items()` already runs one batched grouped
  query each for reaction counts, comment counts, viewer reactions, latest comments (T95),
  and liked-by (T96). **Add the play counts the same way**: one query grouping `Play` by
  `(user_id, track_id)` filtered to the batch's exact author/track pairs (SQLAlchemy
  `tuple_(...).in_(...)` works on Postgres AND the SQLite test DB; alternatively filter on
  `user_id IN authors AND track_id IN tracks` and keep only the exact pairs in Python —
  either is acceptable, say which in the PR).
- `FeedPostOut` (`schemas.py`) — add `author_play_count: int = 0` → alias
  `authorPlayCount`. Always present (0 default), per the stable-shape convention.
- `pages.py` `_feed_items()` passes song fields through; `feed.html`'s song card renders it.
- Profile top-tracks (T44, `app/stats.py::_top_tracks`) ALREADY returns per-track play
  counts — check `templates/profile.html`: if the count is already displayed there, this
  ticket touches only the feed; if the profile renders titles without counts, showing the
  existing number there is in scope (it's already computed — display only).

## Scope
### In Scope
- Batched `authorPlayCount` on song feed items (0 when none; artist posts excluded — no
  track).
- Template line on the song card (near `post-meta`), shown only when count ≥ 2:
  "▶ played {N} times by {author display name}" (plural handling: exactly "played 2 times"
  and up — no "1 time" case ever renders).
- Muted styling consistent with `.post-meta`.
- Profile top-tracks count display IF currently missing (see Current State — verify first,
  don't duplicate).
- Tests: feed API returns the count (seed plays, assert N and the 0 default), threshold
  rendering on the page (1 play hidden, 2+ shown), artist items unaffected.

### Out of Scope
- Viewer's own play count on other people's posts ("you've played this 4 times" — fun
  follow-up, second query).
- Time-windowed counts ("this week") — all-time is v1; windows need product wording
  decisions.
- Any new endpoint (this rides the feed DTO).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/schemas.py` | MODIFY | `author_play_count` on `FeedPostOut` |
| `backend/app/routers/feed.py` | MODIFY | one batched (author, track) count query |
| `backend/app/routers/pages.py` | MODIFY | pass the count to the template |
| `backend/app/templates/feed.html` | MODIFY | the threshold-gated line |
| `backend/app/static/brink.css` | MODIFY | muted line styling |
| `backend/app/templates/profile.html` | MODIFY? | show existing top-track counts if missing |
| `backend/tests/test_feed.py` | MODIFY | count + default coverage |
| `backend/tests/test_pages.py` | MODIFY | threshold rendering |
| `docs/plans/requirements.md` | MODIFY | UI-2/AN-7 rows (at close-out) |
| `docs/plans/tickets/README.md` | MODIFY | record completion (at close-out) |

## Testing Checklist
- [ ] feed item carries `authorPlayCount` (seeded N; 0 when the author never played it)
- [ ] the count is the AUTHOR's plays of THAT track (not the viewer's, not other tracks)
- [ ] card hides the line at 0–1 plays, shows it at 2+
- [ ] artist posts unaffected
- [ ] no N+1: still a fixed number of feed queries
- [ ] full backend suite passes

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Notes / Risks
- Most REAL posts today are by accounts whose plays exist only if they linked Spotify —
  synthetic users get plays via T32 seeding. Until listening data is richer, many cards
  will simply not show the line (correct behavior, not a bug). T100 first improves this.
- Cross-schema join (`Play` in `silver`, `Post`/`User` in `public`) is already handled by
  the models' schema-qualified FKs and the test `schema_translate_map` — nothing new
  needed, but don't hand-write schema names in queries.
