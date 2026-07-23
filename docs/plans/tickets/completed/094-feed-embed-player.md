---
status: Completed
priority: High
complexity: Small
category: Feature
tags: [frontend, ui, feed, playback]
blocked_by: []
blocks: []
parent_ticket: null
owner: Sebastian
---

# Feature: playable feed tracks via the Spotify embed player (T94)

## Rationale
Every feed song card already stores its Spotify track id, but the feed is silent — you read
about a song instead of hearing it. Spotify offers a free "embed" player (an iframe, no login
required) for any track, so making cards playable is display work, not new plumbing. This is
the highest value-for-effort item of the 2026-07-22 social quick-wins wave (T94–T97): the
TikTok/Reels norm that the sound *is* the content.

## Summary
Turn each song card's album art into a play button. Tapping it opens Spotify's compact
(152px) embed player for that track inside the card; tapping again closes it. Players are
built lazily in JavaScript — the page ships with zero iframes, and at most one player is
open at a time so songs never overlap. Non-Premium listeners get Spotify's 30-second
preview, which is fine for a feed.

## Source
- Spec reqs: **UI-12** (new — in-place playable feed tracks)
- ADR: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (Jinja/HTMX frontend)

## Scope
### In Scope
- Pass the track's `spotifyId` through the feed page adapter to the template.
- The song card's art becomes an accessible `<button>` (aria-label "Play {title}",
  aria-expanded) with a ▶ overlay; playable with or without album art.
- New `static/player.js`: lazy iframe creation, one open player at a time, toggle to close.
- Embed iframe attributes: `loading="lazy"`, `allow="encrypted-media"`, a real `title`.
- Card/player styles in `brink.css` matching the existing dark-card design.

### Out of Scope
- Artist behind-the-scenes posts (no track id on the card today, even when `linkedTrackId`
  exists — a possible follow-up).
- Autoplay, playlists, or any playback beyond Spotify's stock embed.
- The profile page's track lists (follow-up if the feed version proves out).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/static/player.js` | CREATE | lazy embed-player toggle logic |
| `backend/app/routers/pages.py` | MODIFY | pass `spotifyId` to song items |
| `backend/app/templates/feed.html` | MODIFY | art becomes a play button; load player.js |
| `backend/app/static/brink.css` | MODIFY | play overlay + player row styles |
| `backend/tests/test_pages.py` | MODIFY | playable-card markup regression tests |
| `docs/plans/requirements.md` | MODIFY | add UI-12 traceability row |
| `docs/plans/tickets/README.md` | MODIFY | record completion |

## Testing Checklist
- [x] song card carries `data-spotify-id` and a labelled play button
- [x] player script is loaded by the feed page
- [x] no iframe is present in the initial HTML (lazy player)
- [x] a track without album art still renders a playable button
- [x] full backend suite passes

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Outcome
T94 makes the feed audible: every song card now plays its track in place via Spotify's
compact embed, opened lazily on tap with at most one player open at a time.

- The art button keeps the existing 3.5rem art footprint (gradient placeholder when no art)
  and adds a ▶ overlay that brightens on hover/focus; the player drops in as a full-width
  row under the card content.
- No version-param bumps were needed: T85's `cache-control: no-cache` revalidation already
  guarantees browsers fetch the updated CSS/JS (`player.js` ships with `?v=94` to match the
  existing tag pattern).
- Validation: full backend suite **253 passed** (2 new template regression tests).

Deliberate scope: artist posts and profile track lists stay non-playable (noted follow-ups);
no changes to the feed API or data model.
