---
status: Backlog
priority: High
complexity: Low
category: Fix
tags: [backend, artist, storage, supabase, enablement-gap]
blocked_by: []
blocks: [054]
parent_ticket: null
owner: Andrea
---

# Fix: Signed READ urls for artist images — they currently cannot display (T53)

## Rationale
Gap #3 of the [2026-07-15 frontend-enablement audit](../../reviews/2026-07-15-frontend-enablement-gaps.md),
confirming the open question T50/T51 shipped with: uploads store a bare storage **path** into the
**private** `artist-images` bucket, and `artist.html` renders that path directly as `<img src>`.
A private bucket rejects unauthenticated GETs, so **no artist image can render anywhere — not
even to the artist who uploaded it**. Only `create_signed_upload_url` exists; there is no signed
READ helper.

## Summary
Mint short-lived signed read URLs server-side when rendering artist posts: a
`create_signed_read_url(path)` sibling in `security/supabase.py` (service role, same REST
pattern), used by the `/artist` page route (and T54's audience page) so templates receive a
displayable URL instead of a raw path. MEDIA-5's "verify a real upload+display end-to-end"
check rides along.

## Source
- Spec reqs: **MEDIA-2**, **MEDIA-5** (unverified integration half)
- ADRs: [ADR-0008](../../../decisions/adr/0008-artist-media.md) (private bucket decision — if we
  instead flip the bucket public, that's a new ADR; default is to stay private + signed reads)

## Scope
### In Scope
- `create_signed_read_url(path, expires_in)` in `security/supabase.py` + unit tests (mock the
  Supabase REST call, same style as the upload-url tests).
- `/artist` page route: convert each post's stored path → signed URL before rendering.
- One manual end-to-end verification against `brink-dev` storage (upload → render), noted in the
  PR (closes the MEDIA-5 caveat from T51).

### Out of Scope
- The audience-facing artist page (T54 — it consumes this helper).
- Caching/CDN for signed URLs; image resizing.

## Validation & authz (ADR-0007)
- Signed URLs are minted server-side with the service role; expiry keeps leaked URLs short-lived.
- Only rendered to logged-in viewers via the page routes (no anonymous image API).

## Current State (on `develop`)
- `security/supabase.py`: `create_signed_upload_url` only. `artist.html`: `<img src="{{ path }}">`
  with a raw bucket path — broken for everyone.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/security/supabase.py` | MODIFY | signed read helper |
| `backend/app/routers/pages.py` (artist route) | MODIFY | path → signed URL for templates |
| `backend/tests/test_artist_pages.py` (or existing) | MODIFY | route passes signed URLs |

## Testing Checklist
- [ ] helper builds the correct Supabase sign endpoint call and returns the URL
- [ ] artist page renders `<img>` with a signed URL, not a raw path
- [ ] manual: a real upload on brink-dev displays in the browser (MEDIA-5)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (none)
- [x] Scope boundaries defined

## Notes
Branch `fix/T53-artist-image-signed-read`. Do before T54 — an audience page full of broken
images is worse than none.
