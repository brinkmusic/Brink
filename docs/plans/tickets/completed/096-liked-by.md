---
status: Completed
priority: High
complexity: Small
category: Feature
tags: [frontend, backend, ui, feed, reactions, migration]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Feature: "Liked by X and N others" + reactors list on song posts (T96)

## Rationale
Reaction counts are anonymous numbers; the Instagram/Facebook norm — naming a reactor
("Liked by sebastian and 12 others") — turns them into visible social proof, which is what
makes a feed feel alive. Part of the 2026-07-22 social quick-wins wave (T94–T97).

## Summary
Under each song post's reaction bar, a server-rendered line names the post's MOST RECENT
reactor plus the remaining count ("Liked by **X**", "… and 1 other", "… and N others").
Tapping the line opens a small panel listing everyone who reacted (name linked to their
profile + the emoji of each reaction type they left), fetched lazily from a new
`GET /api/posts/{post_id}/reactions` endpoint.

**Schema change (the one in this wave):** `Reaction` had no timestamp — its cuid id is
random, so "most recent" was impossible. An additive Alembic migration (`f4a2d81c96e0`)
adds `Reaction.createdAt` with `server_default CURRENT_TIMESTAMP`, backfilling existing
rows with the migration time. This column also unblocks a future activity feed
("X liked your post"), which needs reaction times anyway.

## Source
- Spec reqs: **UI-3** (reactions), **BE-5**
- ADRs: [ADR-0012](../../../decisions/adr/0012-dto-allowlist.md) (DTO allow-list),
  [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (Jinja/HTMX frontend)

## Scope
### In Scope
- `Reaction.createdAt` (model + additive backfilled migration).
- `GET /api/posts/{post_id}/reactions`: login-gated, 404 on missing post, returns unique
  reactors newest-first with their combined `types` (new `ReactorOut` DTO — public fields only).
- Batched `likedBy` (most recent reactor, or null) on `FeedPostOut`; the no-N+1 rule holds.
- The server-rendered line + lazy reactors panel (`liked-by.js`) with correct grammar
  (1 → "Liked by X"; 2 → "and 1 other"; N → "and N-1 others").

### Out of Scope
- Artist posts (`ArtistReaction` has no timestamp either) — **explicit follow-up**: mirror
  the column + endpoint when artist-post parity is wanted.
- Live-updating the line after the viewer reacts (would mean editing `reactions.js`, which
  the parallel T97 deliberately avoids touching too) — the line refreshes on reload;
  noted as a possible polish follow-up.
- Reaction notifications / activity feed (future wave; this ticket just makes it possible).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/models.py` | MODIFY | `Reaction.created_at` |
| `backend/alembic/versions/f4a2d81c96e0_add_reaction_created_at_t96.py` | CREATE | additive backfilled migration |
| `backend/app/schemas.py` | MODIFY | `ReactorOut`; `liked_by` on `FeedPostOut` |
| `backend/app/routers/reactions.py` | MODIFY | GET reactors endpoint |
| `backend/app/routers/feed.py` | MODIFY | batched most-recent-reactor lookup |
| `backend/app/routers/pages.py` | MODIFY | pass `liked_by` to the template |
| `backend/app/templates/feed.html` | MODIFY | the line + panel markup |
| `backend/app/static/liked-by.js` | CREATE | panel toggle + lazy reactors fetch |
| `backend/app/static/brink.css` | MODIFY | line + panel styles |
| `backend/tests/test_reactions.py` | MODIFY | endpoint auth/404/grouping/order/no-leak |
| `backend/tests/test_feed.py` | MODIFY | `likedBy` most-recent + null coverage |
| `backend/tests/test_pages.py` | MODIFY | rendered line regression |
| `backend/tests/test_api_surface.py` | MODIFY | route inventory (T61 gate) |
| `docs/plans/requirements.md` | MODIFY | UI-3 traceability |
| `docs/plans/tickets/README.md` | MODIFY | record completion |

## Testing Checklist
- [x] GET reactors: 401 unauthenticated, 404 missing post, empty list stable shape
- [x] reactors are unique per user, newest-reaction-first, types combined, public fields only
- [x] feed `likedBy` names the most recent reactor; null when unreacted
- [x] the line renders with correct "and N other(s)" grammar and loads liked-by.js
- [x] full backend suite passes

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Outcome
T96 gives reactions faces: song posts name their most recent reactor with an Instagram-style
tappable line, backed by a real reactors endpoint.

- The migration is additive and backfilled (`server_default CURRENT_TIMESTAMP`) — existing
  reactions get the migration time, future ones the real time. **Owner step: run
  `uv run alembic upgrade head` from `backend/` against brink-dev (and production at the
  next release) before this feature can order reactions in those environments.**
- Validation: full backend suite **257 passed** (6 new tests).

Deliberate scope: artist-post parity and live line refresh are stated follow-ups.
