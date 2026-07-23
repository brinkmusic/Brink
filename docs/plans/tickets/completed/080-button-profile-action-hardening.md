---
status: Completed
priority: High
complexity: Small
category: Fix
tags: [frontend, ui, accessibility, profile, artist]
blocked_by: []
blocks: []
parent_ticket: null
owner: Sebastian
---

# Fix: button system + visible profile artist action (T80)

## Rationale
The T56 contrast fix is present on `develop`, but the UI still has two problems:
1. `.btn-ghost` is fixed, but base `.btn` has no default foreground/background contract. Any future
   bare `<button class="btn">` can fall back to browser styling and reintroduce low-contrast buttons.
2. The "Become an artist" button exists only on your own non-artist profile, but it is pinned as a
   small absolute-positioned control in the top-right of the profile card. That keeps it secondary,
   but also makes it easy to miss and fragile on narrow screens.

## Summary
Harden the shared button system so every button state is readable by default, then make the
own-profile "Become an artist" action a clear secondary profile action with mobile-safe placement
and visible failure feedback.

## Source
- Spec reqs: **MEDIA-6** (self-serve artist designation), **UI-5** (usable profile controls),
  **UI-9** (visible loading/error states)
- ADRs: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (Jinja/HTMX frontend) +
  [ADR-0008](../../../decisions/adr/0008-media-technical-validation-only.md) (artist/media scope)

## Scope
### In Scope
- Give `.btn` a safe default color/background/border contract.
- Add readable `.btn:disabled` and loading/busy states shared by primary and ghost buttons.
- Reposition `.become-artist-btn` so it remains secondary but is visible on own non-artist profiles.
- Add mobile rules so the profile actions stack naturally without overlap.
- Add visible failure feedback for `become-artist.js` instead of console-only failure.

### Out of Scope
- Changing the `POST /api/me/become-artist` API behavior.
- Showing the button to artists, signed-out users, or people viewing someone else's profile.
- Replacing the native irreversible-action confirmation with a custom modal.

## Current State (on `develop`)
- `.btn-ghost` is explicitly transparent and readable, per T56.
- `.btn` itself does not set a default foreground/background.
- `.become-artist-btn` is rendered in `profile.html` when `p.is_self and not p.is_artist`, then
  absolutely positioned at the top-right of `.profile-header`.
- `become-artist.js` restores the button and logs to the console if the request fails.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/static/brink.css` | MODIFY | button defaults, disabled states, profile action layout |
| `backend/app/templates/profile.html` | MODIFY | profile action grouping/status markup if needed |
| `backend/app/static/become-artist.js` | MODIFY | busy/error feedback for the artist conversion action |
| `backend/tests/test_pages.py` | MODIFY | preserve own-profile render conditions |

## Testing Checklist
- [x] every `.btn` variant has readable normal/hover/focus/disabled states
- [x] own non-artist profile clearly shows "Become an artist"
- [x] own artist profile hides "Become an artist"
- [x] someone else's profile hides "Become an artist"
- [x] failed artist conversion shows visible feedback, not only a console warning
- [x] mobile profile header/action row does not overlap or squeeze text

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `fix/T80-button-profile-action-hardening`; one PR back into `develop`
(never `main`). This is UI-only; no backend behavior change.

## Outcome
T80 hardened the shared button and own-profile artist action UI without changing the backend artist
conversion behavior.

- **Button defaults:** `.btn` now has an explicit dark-theme background, foreground, and border, so a
  bare button cannot fall back to browser light-button styling. Primary buttons set their border to
  the lavender action color, and ghost buttons gain a subtle hover fill while staying transparent by
  default.
- **Disabled/loading states:** shared `.btn:disabled` and `.btn[aria-busy="true"]` styling keeps
  temporary states readable and non-jumpy.
- **Profile action placement:** `profile.html` now renders profile controls in `.profile-actions`.
  On your own listener profile, "Edit profile" and "Become an artist" sit together as clear secondary
  actions instead of pinning the artist action absolutely to the card corner.
- **Visible failure path:** `become-artist.js` writes progress/failure text into
  `#become-artist-status` and marks the button busy while the request is in flight.
- **Tests:** `backend/tests/test_pages.py` now asserts the own non-artist profile renders the action
  row, script, and live status target. Full backend suite: **244 passed**.

Deliberate scope: T80 did not change `POST /api/me/become-artist`, the one-way confirmation, or the
conditions for showing the button. It still appears only on your own profile when you are not already
an artist.
