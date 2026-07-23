---
status: Completed
priority: High
complexity: Small
category: Feature
tags: [frontend, backend, ui, feed, comments]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Feature: latest comments inline on feed cards (T95)

## Rationale
Comments were hidden behind the 💬 toggle and only loaded on click, so a lively conversation
looked identical to silence. The Instagram norm — the newest few comments visible on the card
itself — makes the feed read as *populated* at a glance. The feed builder already batches
per-post engagement queries, so this is one more batched query, not a redesign. Part of the
2026-07-22 social quick-wins wave (T94–T97).

## Summary
Each feed item (song posts AND artist behind-the-scenes posts) now carries its newest
comments — capped at 3, shown in chronological order within that subset (oldest of the shown
ones first, so the newest sits nearest the comment box) — rendered directly on the card with
each author linked to their profile. The 💬 toggle becomes "View all N" when more exist and
still opens the existing full-list/add-comment panel. Posting a comment from the panel also
appends it to the inline list live.

## Source
- Spec reqs: **UI-4** (comments become real input + list)
- ADRs: [ADR-0012](../../../decisions/adr/0012-dto-allowlist.md) (DTO allow-list),
  [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (Jinja/HTMX frontend)

## Scope
### In Scope
- `latestComments` on both feed DTOs (`FeedPostOut`, `ArtistFeedPostOut`), reusing the
  existing `CommentOut`/`AuthorOut` DTOs (reuse before reinventing; no field leaks).
- One batched query per feed half (a shared `_latest_comments` helper works against both the
  `Comment` and mirrored `ArtistComment` tables) — the no-N+1 rule is preserved.
- Template renders the inline list above the 💬 toggle for both card kinds; toggle reads
  "View all N" when the count exceeds what's shown.
- `comments.js`/`artist-engagement.js`: a just-posted comment also appends inline.

### Out of Scope
- Comment pagination, deletion, or editing.
- The artist PROFILE page's comment panels (feed-only; the shared JS no-ops there).
- Any change to the comments API endpoints.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/schemas.py` | MODIFY | `latest_comments` on both feed DTOs |
| `backend/app/routers/feed.py` | MODIFY | batched `_latest_comments` helper, wired per kind |
| `backend/app/routers/pages.py` | MODIFY | pass template-shaped inline comments through |
| `backend/app/templates/feed.html` | MODIFY | render inline lists + "View all N" toggle |
| `backend/app/static/comments.js` | MODIFY | `appendInlineComment` + live append |
| `backend/app/static/artist-engagement.js` | MODIFY | live append (guarded reuse) |
| `backend/app/static/brink.css` | MODIFY | inline comment list styles |
| `backend/tests/test_feed.py` | MODIFY | cap/order/empty-shape/no-leak/artist coverage |
| `backend/tests/test_pages.py` | MODIFY | inline rendering regression test |
| `docs/plans/requirements.md` | MODIFY | UI-4 traceability |
| `docs/plans/tickets/README.md` | MODIFY | record completion |

## Testing Checklist
- [x] song post carries its newest 3 comments, chronological within the subset
- [x] uncommented post carries a stable empty list (never null)
- [x] comment authors expose only public fields (no email/ids — ADR-0012)
- [x] artist item carries latest comments from the mirrored table
- [x] feed page renders the inline list with linked authors
- [x] full backend suite passes

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Outcome
T95 puts conversations on the surface: every feed card now shows its newest comments without
a click, for both song and artist posts.

- The batched `_latest_comments` helper runs once per feed half (parameterized over the
  mirrored comment tables), keeping the feed at a fixed number of queries.
- `CommentOut` is reused verbatim, so the feed and the comments API expose identical
  allow-listed comment shapes.
- Validation: full backend suite **255 passed** (4 new tests: 3 API + 1 page).

Deliberate scope: no API endpoint changes; artist-profile comment panels untouched.
