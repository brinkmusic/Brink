---
status: Completed
priority: Medium
complexity: Small
category: Feature
tags: [frontend, ui, feed, reactions]
blocked_by: []
blocks: []
parent_ticket: null
owner: Sebastian
---

# Feature: double-tap a song card to heart it (T97)

## Rationale
Double-tap-to-like is Instagram's most muscle-memory gesture — everyone's thumbs already
know it. Brink's reaction plumbing (T11 API + `reactions.js` optimistic UI) already does all
the hard work, so the gesture is a thin, JS-only layer on top: high delight, near-zero new
machinery. Part of the 2026-07-22 social quick-wins wave (T94–T97).

## Summary
Double-clicking (desktop) or double-tapping (touch) anywhere on a feed song card — except
its buttons, links, and inputs — leaves a HEART reaction and floats a big heart over the
card. Instagram semantics: the gesture only ever ADDS a heart; if the viewer already
hearted the post it replays the animation and changes nothing (removal stays on the ❤️
button). All reaction logic is delegated to the existing `react()` so there is exactly one
code path talking to the reactions API.

## Source
- Spec reqs: **UI-3** (reactions call BE-5; counts reflect server truth)
- ADR: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (Jinja/HTMX frontend)

## Scope
### In Scope
- New `static/double-tap.js`: delegated dblclick (desktop) + timed two-tap detection
  (touch, ~300ms) on song cards, excluding interactive controls; add-only hearting via the
  existing `react()`; floating-heart animation honoring `prefers-reduced-motion`.
- `brink.css`: card anchors the heart (`position: relative`), `touch-action: manipulation`
  to stop double-tap zoom, and the `double-tap-pop` keyframes.
- Load the script on the feed page (after `reactions.js`, whose `react()` it reuses).

### Out of Scope
- Artist behind-the-scenes cards (their reactions use the mirrored T52 API — follow-up if
  the gesture proves popular).
- Any change to `reactions.js` or the reactions API (deliberate: the parallel T96 also
  works near reactions, so this ticket adds a new file instead of editing shared JS).
- Un-hearting via gesture (not the norm; removal stays on the button).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/static/double-tap.js` | CREATE | the gesture + animation logic |
| `backend/app/templates/feed.html` | MODIFY | load the script after reactions.js |
| `backend/app/static/brink.css` | MODIFY | heart animation + gesture-friendly card CSS |
| `backend/tests/test_pages.py` | MODIFY | script loading, add-only guard, animation CSS |
| `docs/plans/requirements.md` | MODIFY | UI-3 traceability |
| `docs/plans/tickets/README.md` | MODIFY | record completion |

## Testing Checklist
- [x] feed page loads double-tap.js when song posts render
- [x] script checks `classList.contains("reacted")` before hearting (add-only)
- [x] script delegates to `react()` (no second API path)
- [x] script honors `prefers-reduced-motion`
- [x] stylesheet has the `.double-tap-heart` element + `double-tap-pop` keyframes
- [x] full backend suite passes

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Outcome
T97 ships the double-tap gesture as a pure additive layer: one new script, a CSS animation,
and zero changes to the shared reaction code or API.

- The gesture targets the whole song card minus its controls — a deliberate choice so it
  can't collide with T94's play button (the album art becomes a button in that ticket).
- Touch devices get hand-rolled two-tap detection (`pointerup` within 300ms) because mobile
  browsers don't reliably fire `dblclick`; `touch-action: manipulation` stops the browser's
  own double-tap zoom from swallowing the gesture.
- Validation: full backend suite **254 passed** (3 new tests).

Deliberate scope: artist cards excluded (mirrored-API follow-up); no reactions.js edits.
