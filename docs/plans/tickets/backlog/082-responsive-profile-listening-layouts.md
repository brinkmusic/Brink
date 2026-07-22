---
status: Backlog
priority: Medium
complexity: Small
category: Fix
tags: [frontend, ui, responsive, profile]
blocked_by: []
blocks: []
parent_ticket: null
owner: Sebastian
---

# Fix: responsive profile + listening layouts (T82)

## Rationale
The profile page now carries a lot of real information: identity, follow counts, profile actions,
now-playing, listening summary, recent plays, artist posts, and shared songs. Several rows use
horizontal flex layouts with right-aligned metadata, which can squeeze or overflow with long names,
track titles, or narrow mobile widths.

## Summary
Add a focused responsive pass for profile/listening surfaces so long names and metadata wrap or stack
cleanly on mobile without overlapping actions or hiding important content.

## Source
- Spec reqs: **UI-5** (profiles/follow surface), **UI-6** (profile stats/listening surface),
  **UI-10** (now-playing indicator)
- ADRs: [ADR-0014](../../../decisions/adr/0014-feed-manual-posts-listening-summary.md)
  (listening surfaces live on profile)

## Scope
### In Scope
- Mobile-safe profile header/action layout.
- Wrapping/truncation rules for follower counts, now-playing rows, top tracks/artists, and recent
  listening rows.
- Stable metadata positioning so play counts and timestamps do not crush titles.
- Responsive comment/action rows where they appear inside profile and feed cards.

### Out of Scope
- New profile features or analytics fields.
- Changing the backend data shape for listening summaries.
- A visual redesign of the landing page.

## Current State (on `develop`)
- Profile counts, now-playing, top-list rows, and recent-list rows are mostly horizontal.
- Long content can compete with right-aligned metadata on small screens.
- T80 moved the "Become an artist" control into the normal profile action row; this ticket should
  preserve that flow while hardening the rest of the profile/listening layout.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/static/brink.css` | MODIFY | responsive profile/listening/feed layout rules |
| `backend/app/templates/profile.html` | MODIFY | minimal markup hooks if CSS alone is insufficient |
| `backend/tests/test_pages.py` | MODIFY | preserve critical profile markup |

## Testing Checklist
- [ ] profile header remains readable on narrow mobile widths
- [ ] profile counts wrap without overlap
- [ ] now-playing, top tracks, top artists, and recent rows handle long text
- [ ] action rows and comment forms do not squeeze buttons or inputs
- [ ] desktop layout remains compact and scannable

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `fix/T82-responsive-profile-listening-layouts`; one PR back into `develop`
(never `main`). This pairs naturally after T80, but can be implemented independently if scoped to
CSS-only responsive rules.
