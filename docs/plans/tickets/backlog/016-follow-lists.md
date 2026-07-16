---
status: Backlog
priority: Medium
complexity: Low
category: Feature
tags: [backend, frontend, social, enablement-gap]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Feature: Follower / following lists (T16)

## Rationale
Gap #6 of the [2026-07-15 frontend-enablement audit](../../reviews/2026-07-15-frontend-enablement-gaps.md):
the profile page shows follower/following **counts** as plain text — you can't see *who* follows
someone or browse outward through the social graph. Combined with user search (T15/T46) this is
the second discovery path: find one person, then walk their graph.

## Summary
`GET /api/users/{userId}/followers` and `GET /api/users/{userId}/following` (login-gated,
paginated or capped, camelCase user DTOs), plus making the counts on `/u/{handle}` links that
expand/navigate to those lists.

## Source
- Spec reqs: **BE-4**, **UI-5**
- Patterns: T13 follow tables; T15's `UserSearchOut` DTO (reuse it).

## Scope
### In Scope
- The two list endpoints in `routers/users.py` (created by T15) + tests.
- Profile template: counts become clickable, rendering the lists (simple server-rendered section
  or small JS fetch — implementer's choice, note it in the PR).

### Out of Scope
- Mutual-follow indicators, private accounts, pagination beyond a simple cap (~50).

## Validation & authz (ADR-0007)
Login-gated, read-only, rate-limited.

## Current State (on `develop`)
- `Follow` table + counts queried in the profile route; no list endpoint exists.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/users.py` | MODIFY | the two list endpoints |
| `backend/app/templates/profile.html` | MODIFY | clickable counts + list rendering |
| `backend/tests/test_users_follow_lists.py` | CREATE | list behavior + gating |

## Testing Checklist
- [ ] lists return the right users after follow/unfollow; login required
- [ ] counts on the profile match the list lengths
- [ ] empty states render

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T15 creates `routers/users.py`; can be reordered if T16 goes first)
- [x] Scope boundaries defined

## Notes
Branch `feat/T16-follow-lists`. Lower priority than T15/T46/T47.
