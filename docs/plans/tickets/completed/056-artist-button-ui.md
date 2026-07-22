---
status: Completed
priority: Medium
complexity: Small
category: Fix
tags: [frontend, ui, accessibility, artist]
blocked_by: []
blocks: []
parent_ticket: null
owner: Sebastian
---

# Fix: readable ghost buttons + safer "become an artist" action (T56)

## Rationale
Two UI problems on the profile page, both around the T55 "Become an artist" button:
1. **Low-contrast buttons** — `.btn-ghost` sets text colour + border but no `background`, so on a
   `<button>` element it falls back to the browser's default light button background: light text on
   a light button ("white on white"), hard to read. Affects the "Become an artist" button and the
   "Following" state of the follow button. (`<a>` ghost buttons like Log out are unaffected —
   anchors have no default background.)
2. **Mis-click risk** — becoming an artist is a **one-way** action (T55), but the button sits inline
   in the profile header where it's easy to tap by accident, with no confirmation.

## Summary
Give `.btn-ghost` a transparent background so ghost buttons are readable on the dark theme; move the
"Become an artist" button to the **top-right corner** of the profile header, out of the main flow;
and add a confirmation prompt before the irreversible flip.

## Source
- Spec reqs: **MEDIA-6** (T55 — refines its UI), **UI-2** (app shell / usable controls)
- ADRs: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (Jinja/HTMX frontend)

## Scope
### In Scope
- `backend/app/static/brink.css` — `.btn-ghost { background: transparent }` contrast fix; position
  `.become-artist-btn` top-right of `.profile-header`.
- `backend/app/static/become-artist.js` — confirm ("this cannot be undone") before POSTing; bail if
  the user cancels.
- `backend/app/templates/profile.html` — button placement markup if needed.

### Out of Scope
- Any change to the `POST /api/me/become-artist` behaviour (T55) — this is UI only.
- A full custom modal component — a native confirm dialog is enough for a one-way action.

## Current State (on `develop`)
- `.btn-ghost` (brink.css) sets `border-color` + `color`, no `background`.
- `.become-artist-btn` is an inline `<button class="btn btn-ghost">` in the profile header
  (`profile.html`), made live by `static/become-artist.js` (POST then reload).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/static/brink.css` | MODIFY | ghost-button contrast fix + top-right button placement |
| `backend/app/static/become-artist.js` | MODIFY | confirm before the irreversible POST |
| `backend/app/templates/profile.html` | MODIFY | button placement markup |
| `backend/tests/test_pages.py` | MODIFY | keep/settle the button-render assertions |

## Testing Checklist
- [x] ghost buttons render with a transparent (not light) background — readable light text
- [x] "Become an artist" button appears top-right on your own non-artist profile
- [x] clicking it prompts a confirmation; cancelling does not call the API
- [x] confirming still upgrades the account (T55 behaviour unchanged)

## Outcome (as built)
UI-only refinement of the T55 button; no API/behaviour change.

- **Contrast fix:** `.btn-ghost` now sets `background: transparent` (`brink.css`). A `<button>`
  element defaults to the browser's light button background, so ghost buttons were light text on a
  light fill ("white on white"); transparent lets the dark card show through so the light text is
  readable. Fixes the "Become an artist" button **and** the follow button's "Following" state.
- **Placement:** `.profile-header` is now `position: relative` and `.become-artist-btn` is pinned
  `position: absolute; top:0; right:0`, small/quiet (0.8rem) — top-right corner of the profile card,
  out of the main action flow so it isn't tapped by accident.
- **Confirmation:** `become-artist.js` now calls `window.confirm("Are you sure you want to create an
  artist profile? … cannot be undone.")` and returns early (no API call) if the user cancels — a
  guard for the one-way action.
- **Files:** `backend/app/static/brink.css` · `backend/app/static/become-artist.js` · (no template
  change needed — the button already carried `.become-artist-btn` inside the header).
- **Tests:** no new server logic; full backend suite **222 passed**. The visual/confirm behaviour is
  CSS/JS (owner-verified in the browser after deploy). Existing `test_pages.py` button-render
  assertions still hold.

## Notes
Branch off `develop` as `feat/T56-artist-button-ui`; one PR back into `develop` (never `main`).
Frontend area (owner: Sebastian); implemented by Andrea.
