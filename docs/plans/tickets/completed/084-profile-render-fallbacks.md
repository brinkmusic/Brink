---
status: Completed
priority: High
complexity: Small
category: Fix
tags: [frontend, profile, artist, reliability]
blocked_by: []
blocks: []
parent_ticket: null
owner: Sebastian
---

# Fix: profile render fallbacks (T84)

## Rationale
A signed-in user's profile can render optional data from multiple systems: Spotify now-playing,
artist posts, private Storage signing, and artist-post engagement counts. A failure in any optional
enrichment should not turn the whole profile into a plain 500 page.

## Summary
Keep `/u/{handle}` available when optional profile enrichments fail. The core profile header,
listening summary, artist-post cards, and shared songs should render whenever their base data is
available; optional now-playing and engagement data should degrade to hidden/zero states.

## Source
- Spec reqs: **UI-9** (loading/empty/error states; no silent mock fallback), **UI-5** (usable profile controls)
- ADRs: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (server-rendered frontend)

## Scope
### In Scope
- Guard own-profile now-playing so Spotify/API/token issues do not 500 the profile page.
- Guard artist-post and artist-engagement reads so profile pages render when optional artist
  enrichment tables or reads are unavailable.
- Guard artist image signing so a storage-signing issue does not 500 the profile page.
- Add regression tests for profile rendering under these failures.

### Out of Scope
- Changing the `GET /api/me/now-playing` JSON endpoint behavior.
- Applying or designing production database migrations.
- Changing artist engagement write APIs.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/pages.py` | MODIFY | profile render fallbacks for optional enrichment failures |
| `backend/tests/test_pages.py` | MODIFY | regression tests for profile-only 500 paths |

## Testing Checklist
- [x] own profile still renders when now-playing raises
- [x] artist profile still renders when artist engagement reads fail
- [x] targeted profile regression tests pass

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Outcome
T84 makes optional profile enrichments fail closed instead of taking down `/u/{handle}`.

- **Now-playing:** own-profile Spotify lookup is wrapped; failures log and hide the badge.
- **Artist profile:** optional artist-post/engagement reads are wrapped; failures log, roll back the
  session if needed, and keep the profile page available.
- **Image signing:** artist image signing failures log and return an empty image URL rather than
  raising through the profile route.
- **Tests:** `backend/tests/test_pages.py` covers profile-only failure modes. Full backend suite:
  **247 passed**.
