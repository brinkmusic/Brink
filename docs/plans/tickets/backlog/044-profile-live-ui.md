---
status: Backlog
priority: Medium
complexity: Medium
category: Feature
tags: [frontend, profile, analytics, spotify]
blocked_by: [014, 020]
blocks: [060]
parent_ticket: null
owner: Sebastian
---

# Feature: Profile page live + now-playing badge (T44)

## Rationale
The profile page currently renders mock stats. This wires it to the real profile API (live stats + cluster + compatibility) and adds the now-playing badge, turning it into the real "Wrapped"-style surface.

## Summary
`ProfilePage` reads `/api/users/:id/profile`; renders stats (streak heatmap, top lists), cluster label, compatibility donut, the now-playing badge (T20), and a "link Spotify" prompt for handle users.

## Source
- Spec reqs: **UI-6**, **UI-10**
- ADRs: [ADR-0003](../../../decisions/adr/0003-analytics-runtime.md) · [ADR-0005](../../../decisions/adr/0005-identity.md) (handle users)

## Scope
### In Scope
- `ProfilePage.tsx` — fetch the profile API; render via existing `StreakHeatmap`, `CompatDonut` components; show cluster label; loading/empty/error states.
- Now-playing badge from `GET /api/me/now-playing` (T20).
- "Link Spotify" prompt for handle users (no Spotify identity).

### Out of Scope
- Backend profile/now-playing (T14/T20); analytics page (T45); the follow button (T43).

## Validation & authz (ADR-0007)
- Client renders only what the API authorizes; no analytics values are computed client-side (they come from T14/T33/T35).

## Current State (on `develop`)
- `apps/web/src/pages/ProfilePage.tsx`, `components/StreakHeatmap.tsx`, `components/CompatDonut.tsx` exist (mock-driven via `lib/data.ts`).
- Profile API (T14) + now-playing (T20) provide the real data.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `apps/web/src/pages/ProfilePage.tsx` | MODIFY | read real profile API; render stats/cluster/compat; now-playing; link-Spotify prompt |

## Testing Checklist
- [ ] profile renders real stats from the API (no mock import on this path)
- [ ] empty profile renders gracefully (no crash on null cluster/compat)
- [ ] now-playing badge shows current track / hides when nothing playing
- [ ] handle user (no Spotify) sees the "link Spotify" prompt
- [ ] loading and error states present

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T14, T20 → blocked_by 014, 020)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T44-profile-live`; one PR back into `develop` (never `main`). Owner: Sebastian (frontend).
