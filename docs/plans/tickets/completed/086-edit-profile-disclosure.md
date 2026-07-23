---
status: Completed
priority: High
complexity: Small
category: Fix
tags: [frontend, ui, profile, accessibility]
blocked_by: []
blocks: []
parent_ticket: null
owner: Sebastian
---

# Fix: edit-profile disclosure state (T86)

## Rationale
The edit-profile form is intended to appear only after the owner clicks **Edit profile**, but
`.edit-profile-form { display: grid; }` overrides the browser's default rendering for the HTML
`hidden` attribute. The avatar input, bio field, and Save button therefore appear on initial load.

## Summary
Restore the collapsed initial state and keep the Edit profile button's accessibility state in sync
when the form opens and closes.

## Source
- Spec reqs: **UI-11** (editable profile), **UI-9** (complete interface states)
- ADR: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (Jinja/HTMX frontend)

## Scope
### In Scope
- Explicitly hide `.edit-profile-form[hidden]` despite the form's grid layout.
- Mark the Edit profile button collapsed initially and update `aria-expanded` when toggled.
- Add regression coverage for the collapsed markup and CSS state.

### Out of Scope
- Changing profile fields, upload behavior, or save APIs.
- Redesigning the profile header or form.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/static/brink.css` | MODIFY | preserve the hidden form state |
| `backend/app/static/edit-profile.js` | MODIFY | synchronize disclosure accessibility state |
| `backend/app/templates/profile.html` | MODIFY | declare the initial collapsed state |
| `backend/tests/test_pages.py` | MODIFY | prevent initial-open regressions |
| `docs/plans/requirements.md` | MODIFY | trace UI-9/UI-11 to T86 |
| `docs/plans/tickets/README.md` | MODIFY | record completion |

## Testing Checklist
- [x] edit controls are hidden on initial profile load
- [x] clicking Edit profile reveals the controls
- [x] clicking again collapses the controls
- [x] `aria-expanded` matches the visible state
- [x] full backend suite passes

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Outcome
T86 restores Edit profile as a collapsed disclosure instead of exposing its controls on page load.

- `.edit-profile-form[hidden]` explicitly uses `display: none`, preventing the open-state grid rule
  from overriding the HTML hidden state.
- The button starts with `aria-expanded="false"`, identifies its controlled form, and updates the
  expanded state whenever the form opens or closes.
- Regression tests cover the CSS hidden contract, initial markup, and script state synchronization.
- Validation: full backend suite **251 passed**; Impeccable found no T86-specific issue.

Deliberate scope: no profile fields, upload behavior, save API, or visual redesign changed.
