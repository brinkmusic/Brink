---
status: Completed
priority: Medium
complexity: Medium
category: Feature
tags: [backend, frontend, feed, artist]
blocked_by: [013, 050, 052, 054]
blocks: []
parent_ticket: null
owner: Andrea
---

# Feature: Followed artists' posts in the feed (T049)

## Rationale
The feed only ever showed song-share `Post`s from followed users + self. It never looked at
`ArtistPost` (the behind-the-scenes posts from T50/T51), so following an artist did nothing for your
home feed — their posts were only reachable by visiting their profile (T54). A follower should see a
followed artist's BTS posts alongside the songs their friends share.

## Summary
`build_feed` now also fetches the `ArtistPost`s of the artists the caller follows (or their own, if
they're an artist), signs each image, gathers its T52 engagement, and interleaves them with the song
posts newest-first. Every feed item carries a `kind` discriminator (`"song"` / `"artist"`) so the
frontend renders the right card. Artist cards reuse the exact T54 artist-card markup +
`static/artist-engagement.js`, which calls the existing T52 `/api/artist/posts/{id}/...` endpoints —
no new engagement API.

## What shipped
### Backend (`backend/app/routers/feed.py`)
- `build_feed` split into `_build_song_items` (the original T13 behaviour) + `_build_artist_items`
  (new), each returning `(created_at, item)` pairs; the two lists are merged and sorted by the raw
  datetime, newest-first.
- `_build_artist_items` fetches followed artists' `ArtistPost`s joined to their author, then batches
  reaction counts, comment counts, and the viewer's own reactions over `ArtistReaction`/`ArtistComment`
  (three grouped queries — the same no-N+1 pattern as the song half). Each image path is turned into a
  signed read URL via `create_signed_read_url("artist-images", ...)` (T53) before it leaves the server.
- Song items keep their shape unchanged except for the added `kind: "song"`.

### Schemas (`backend/app/schemas.py`)
- `FeedPostOut` gained `kind: Literal["song"] = "song"`.
- New `ArtistFeedPostOut` (`kind: "artist"`): id, author, caption, signed `image_url`, createdAt, and
  the same `reaction_counts` / `comment_count` / `viewer_reactions` engagement shape (ADR-0012 camelCase).

### UI (`backend/app/routers/pages.py`, `backend/app/templates/feed.html`)
- `_feed_items` passes `kind` through and reshapes song vs artist items.
- `feed.html` branches on `p.kind`: `"song"` → the existing song card; `"artist"` → an artist card
  (signed image, "@author · behind the scenes", audience reaction/comment controls) reusing the T54
  markup. `static/artist-engagement.js` is loaded only when an artist item is present.

## Source
- Spec reqs: **UI-2** (feed UI) / **BE-7** (feed respects the follow graph)
- ADRs: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (Jinja frontend),
  [ADR-0012](../../../decisions/adr/0012-camelcase-response-dtos.md) (response DTOs)

## Scope
### In Scope
- Followed artists' `ArtistPost`s in the feed, interleaved by time, with working T52 like/comment
  controls reusing the existing engagement API and JS.

### Out of Scope
- No new artist-engagement API (reuse T52). No new Supabase bucket or migration (tables already exist).
- `GET /api/feed`'s route signature is unchanged (still returns the list) — the T61 route-inventory
  test needs no change (verified).

## Current State (on `develop`)
- `ArtistPost` / `ArtistReaction` / `ArtistComment` exist (T50/T52); `create_signed_read_url` exists
  (T53); the artist-card markup + `artist-engagement.js` exist (T54).

## Files Created/Modified
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/feed.py` | MODIFY | split `build_feed`; add followed-artist posts + batched engagement |
| `backend/app/schemas.py` | MODIFY | add `kind` to `FeedPostOut`; add `ArtistFeedPostOut` |
| `backend/app/routers/pages.py` | MODIFY | reshape feed items per `kind` for the template |
| `backend/app/templates/feed.html` | MODIFY | branch on `kind`; artist card + conditional engagement script |
| `backend/tests/test_feed.py` | MODIFY | backend cases (kind, signed image, follow gate, interleave, engagement) |
| `backend/tests/test_pages.py` | MODIFY | feed-page cases (artist card renders + script; song-only omits script) |

## Testing Checklist
- [x] a followed artist's `ArtistPost` appears with `kind == "artist"` and a signed image URL
- [x] an artist you do NOT follow does not appear
- [x] song + artist items interleave in `created_at` order
- [x] artist item carries per-type reaction counts, comment count, viewer's own reactions
- [x] feed page renders the artist card + loads `artist-engagement.js`; song-only feed omits it
- [x] full suite green (`cd backend && uv run pytest` — 229 passed)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T13 feed, T50 artist posts, T52 engagement, T54 artist card/JS)
- [x] Scope boundaries defined

## Outcome
Followed artists' behind-the-scenes posts now appear in the feed, interleaved newest-first with song
posts, with working like/comment controls backed by the existing T52 API. No API route, migration, or
bucket change; `GET /api/feed` still returns a list (T61 inventory unchanged). One PR into `develop`.
