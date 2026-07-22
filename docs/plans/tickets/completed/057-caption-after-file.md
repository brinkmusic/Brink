---
status: Completed
priority: Medium
complexity: Small
category: Fix
tags: [frontend, ui, artist]
blocked_by: []
blocks: []
parent_ticket: null
owner: Sebastian
---

# Fix: show the caption box only after an image is picked (T57)

## Rationale
An artist post **requires an image** (the server creates an `ArtistPost` only after a file is
uploaded — T50/T51). But on the `/artist` upload card the caption text box is shown up front,
before any file is chosen, which gives the false impression that you can write a caption and post
**without** an image. (The Share button is already disabled until a valid file is picked, so a
caption-only post can't actually happen — this is purely a misleading UI.)

## Summary
Hide the caption input until a valid JPEG/PNG has been selected; reveal it once the file passes the
type/size check, and hide it again if the selection is cleared or invalid. This makes the required
order obvious: pick an image first, then caption it.

## Source
- Spec reqs: **MEDIA-2** (upload UI), **UI-1** (composer UX)
- ADRs: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (Jinja/HTMX frontend)

## Scope
### In Scope
- `backend/app/templates/artist.html` — caption input hidden by default.
- `backend/app/static/artist-upload.js` — reveal the caption on a valid pick; hide it when the
  file is cleared/invalid.

### Out of Scope
- Any change to the upload/post API (T50) or the validation rules — UI ordering only.
- Making the caption optional (still required, unchanged).

## Current State (on `develop`)
- `artist.html`: `.artist-file` picker, then an always-visible `.artist-caption` input, then a
  disabled `.artist-share` button.
- `artist-upload.js` `artistFilePicked()` validates the file and enables Share; `artistUpload()`
  still requires a non-empty caption.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/templates/artist.html` | MODIFY | caption input hidden by default |
| `backend/app/static/artist-upload.js` | MODIFY | reveal/hide caption on file pick |
| `backend/tests/test_pages.py` | MODIFY | assert caption is hidden by default |

## Testing Checklist
- [x] caption input is hidden on initial page load (before a file is picked)
- [x] full backend suite green (no server logic changed)

## Outcome (as built)
UI ordering fix, no API/behaviour change.

- `artist.html` — the `.artist-caption` input now renders with `hidden`, so it's not shown until an
  image is chosen.
- `artist-upload.js` `artistFilePicked()` — sets `caption.hidden = true` up front (so a cleared or
  invalid pick keeps it hidden) and `caption.hidden = false` only once a valid JPEG/PNG passes the
  type/size check — the same moment Share is enabled.
- **Files:** `backend/app/templates/artist.html` · `backend/app/static/artist-upload.js` ·
  `backend/tests/test_pages.py` (asserts the caption renders `hidden`).
- **Tests:** full backend suite **222 passed**. The reveal-on-pick behaviour is JS (owner-verified
  in the browser after deploy).

## Notes
Branch off `develop` as `feat/T57-caption-after-file`; one PR back into `develop` (never `main`).
Frontend area (owner: Sebastian); implemented by Andrea.
