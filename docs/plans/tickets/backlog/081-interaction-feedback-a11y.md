---
status: Backlog
priority: High
complexity: Medium
category: Fix
tags: [frontend, ui, accessibility, comments, search]
blocked_by: []
blocks: []
parent_ticket: null
owner: Sebastian
---

# Fix: interaction feedback + keyboard accessibility pass (T81)

## Rationale
Several live Jinja surfaces work for pointer users but are thin for keyboard and screen-reader users.
Composer search results are plain interactive rows, comment toggles do not expose expanded state, and
failed comment actions mostly fail silently or log to the console. The app needs predictable feedback
for loading, expanded, error, and keyboard states.

## Summary
Harden interactive controls across feed/profile/artist surfaces: real keyboard activation for search
results, accessible comment toggles, visible loading/error states, and consistent focus indicators.

## Source
- Spec reqs: **UI-1** (composer), **UI-4** (comments), **UI-9** (loading/empty/error states)
- ADRs: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (buildless Jinja/HTMX frontend)

## Scope
### In Scope
- Make composer search results keyboard-activatable with Enter/Space, or render real buttons/links.
- Add labels or `sr-only` labels where inputs currently rely on placeholders.
- Add `aria-expanded` / controlled-panel relationships for comment toggles.
- Add visible loading and failure states for comment fetch/submit flows.
- Add consistent `:focus-visible` treatment for nav links, profile links, comment toggles, and
  secondary action buttons.

### Out of Scope
- Changing API contracts for comments, reactions, feed, or search.
- Replacing the buildless frontend with a JavaScript framework.
- Full component extraction or template refactor; keep the pass focused on behavior and states.

## Current State (on `develop`)
- Composer results are focusable rows with click handling, but no complete keyboard semantics.
- Comment panels use hidden DOM panels toggled by JavaScript, but toggles do not expose expanded
  state.
- Some failed JavaScript actions restore controls or log to the console without user-facing feedback.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/templates/feed.html` | MODIFY | labels, comment panel ids/ARIA if needed |
| `backend/app/templates/profile.html` | MODIFY | artist-comment panel ids/ARIA if needed |
| `backend/app/static/composer.js` | MODIFY | keyboard activation / semantics for results |
| `backend/app/static/comments.js` | MODIFY | expanded/loading/error states |
| `backend/app/static/artist-engagement.js` | MODIFY | expanded/loading/error states for artist comments |
| `backend/app/static/brink.css` | MODIFY | focus/error/loading styles |
| `backend/tests/test_pages.py` | MODIFY | assert key ARIA/label markup where server-rendered |

## Testing Checklist
- [ ] composer result can be selected with keyboard
- [ ] comment toggles expose expanded/collapsed state
- [ ] comment loading and submit failures show visible text
- [ ] focus indicators are visible on nav, profile links, comment toggles, and buttons
- [ ] no API behavior changes

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `fix/T81-interaction-feedback-a11y`; one PR back into `develop`
(never `main`).
