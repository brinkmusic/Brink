---
status: Completed
priority: Medium
complexity: Small
category: Fix
tags: [frontend, ui, forms, empty-states, polish]
blocked_by: []
blocks: []
parent_ticket: null
owner: Sebastian
---

# Fix: form controls + empty-state polish (T83)

## Rationale
The app has accumulated several working forms and empty states: login/signup, composer, edit profile,
artist upload, comments, feed empty state, artist empty state, and profile empty states. The behavior
works, but visual treatment is uneven. Native file inputs and edit-profile fields can fall back to
browser defaults, and empty states often explain what is missing without offering the next useful
action.

## Summary
Polish repeated form controls and empty states so the server-rendered frontend feels consistent:
dark-theme file inputs, edit-profile field styling, clearer inline status text, and empty states with
the next relevant action where one exists.

## Source
- Spec reqs: **UI-9** (loading/empty/error states), **UI-11** (editable profile), **MEDIA-2**
  (artist upload UI)
- ADRs: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (Jinja/HTMX frontend) +
  [ADR-0008](../../../decisions/adr/0008-media-technical-validation-only.md) (media validation scope)

## Scope
### In Scope
- Style `artist-file` and edit-profile avatar file inputs, including the native file selector button.
- Add/complete CSS for `.edit-profile-*` fields, status text, and textarea states.
- Normalize empty cards on feed, profile, missing-profile, and artist surfaces.
- Add next-action links/buttons where the action is already implemented and appropriate.
- Keep copy short, concrete, and product-specific.

### Out of Scope
- New upload endpoints or storage behavior.
- New onboarding flows.
- Broad visual redesign or component extraction.

## Current State (on `develop`)
- `backend/app/templates/profile.html` has edit-profile markup, but `brink.css` has limited
  matching styling for those controls.
- `artist.html` uses a native file input for image upload.
- Empty states exist across feed/profile/artist, but their treatment and next actions are uneven.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/static/brink.css` | MODIFY | form, file input, empty-state, and status styles |
| `backend/app/templates/profile.html` | MODIFY | empty-state/action copy or markup hooks |
| `backend/app/templates/feed.html` | MODIFY | empty-state/action copy or markup hooks |
| `backend/app/templates/artist.html` | MODIFY | upload/empty-state polish |
| `backend/app/templates/profile_missing.html` | MODIFY | missing-profile empty-state polish |
| `backend/tests/test_pages.py` | MODIFY | preserve important empty-state/action markup |

## Testing Checklist
- [x] artist upload file input matches the dark UI
- [x] edit-profile file input and bio textarea are visually consistent
- [x] empty states remain truthful and offer an existing next action where appropriate
- [x] status/error text is readable on dark cards
- [x] no backend behavior changes

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `fix/T83-forms-empty-states-polish`; one PR back into `develop`
(never `main`).

## Outcome
T83 polished existing form controls and empty states without changing backend behavior.

- **File inputs:** artist upload and edit-profile avatar file inputs now use dark-theme file selector
  buttons instead of browser-default light controls.
- **Edit profile:** the edit profile form, avatar input, bio textarea, status text, and save action
  now have matching Brink CSS.
- **Empty states:** feed, artist, and profile empty states keep their existing truthful copy and add
  small next-action cues where an action already exists (`/feed`, `/artist`, `/auth/login`, or the
  viewer's own profile).
- **Tests:** `backend/tests/test_pages.py` asserts the new empty-state actions. Focused page suite:
  **36 passed**.

Deliberate scope: no new upload endpoints, onboarding flows, storage behavior, or backend data shape
changes.
