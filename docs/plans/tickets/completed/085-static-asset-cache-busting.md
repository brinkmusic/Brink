---
status: Completed
priority: High
complexity: Small
category: Fix
tags: [frontend, ui, static-assets, caching]
blocked_by: []
blocks: []
parent_ticket: null
owner: Sebastian
---

# Fix: static asset cache busting (T85)

## Rationale
The T80/T83 HTML and CSS are deployed, but production screenshots show fresh profile markup using
an older cached copy of `brink.css`. That mixed release state leaves ghost buttons with a light
browser background and light text, and exposes the edit-profile form as unstyled native controls.
The live page currently links to the unversioned `/static/brink.css`, while static responses do not
tell browsers to revalidate before reuse.

## Summary
Force affected browsers onto the current stylesheet once, then make Brink's static responses
revalidate so later CSS and JavaScript releases cannot leave fresh HTML paired with stale assets.

## Source
- Spec reqs: **UI-9** (complete, readable interface states), **UI-11** (editable profile)
- ADR: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (Jinja/HTMX frontend)

## Scope
### In Scope
- Add a version query to the shared stylesheet URL so existing stale caches are bypassed.
- Send an explicit revalidation cache policy on `/static/*` responses.
- Add regression coverage for both the versioned stylesheet URL and response header.
- Verify the current ghost-button and edit-profile styles remain present.

### Out of Scope
- Redesigning the profile or changing its behavior.
- Changing CDN, Render, or Cloudflare configuration.
- Fingerprinted build tooling or a separate frontend build step.

## Current State (on `develop`)
- `base.html` links to `/static/brink.css` without a version.
- `StaticFiles` serves assets with validators but no explicit `Cache-Control` revalidation policy.
- The deployed CSS already contains the intended T80/T83 button and edit-profile styles.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/main.py` | MODIFY | require static asset revalidation |
| `backend/app/templates/base.html` | MODIFY | bypass already-cached pre-T80/T83 CSS |
| `backend/app/templates/feed.html` | MODIFY | bypass already-cached feed scripts |
| `backend/app/templates/profile.html` | MODIFY | bypass already-cached profile scripts |
| `backend/app/templates/artist.html` | MODIFY | bypass already-cached artist script |
| `backend/tests/test_pages.py` | MODIFY | cover the asset URL and cache policy |
| `docs/plans/requirements.md` | MODIFY | trace UI-9/UI-11 to T85 |
| `docs/plans/tickets/README.md` | MODIFY | record the completed cache fix |
| `CLAUDE.md` | MODIFY | keep the current UI-wave status accurate |

## Testing Checklist
- [x] the page links to a versioned stylesheet URL
- [x] static asset responses include an explicit revalidation policy
- [x] existing ghost-button and edit-profile CSS remains served
- [x] full backend suite passes

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `fix/T85-static-asset-cache-busting`; one PR back into `develop`
(never `main`).

## Outcome
T85 fixes the mixed-release state visible in production screenshots without redesigning the
already-correct T80/T83 interface.

- The shared stylesheet and current JavaScript references use a one-time `v=85` query, bypassing
  assets cached before the button and edit-profile polish shipped.
- `RevalidatingStaticFiles` adds `Cache-Control: no-cache` to `/static/*`, allowing browser storage
  while requiring ETag revalidation before reuse.
- Regression tests cover the versioned stylesheet URL and static response policy.
- Validation: full backend suite **249 passed**; Impeccable reported no blocking UI findings.

Deliberate scope: no profile redesign, API behavior, build tooling, or hosting configuration change.
