---
status: Completed
priority: Medium
complexity: Medium
category: Feature
tags: [frontend, artist, upload, validation]
blocked_by: [050]
blocks: []
parent_ticket: null
owner: Sebastian
---

# Feature: Artist upload UI + validation (T51)

## Rationale
Artists need a real upload flow to replace the hardcoded `SAMPLE_BTS` placeholder content on the artist page.

## Summary
`ArtistPage` gets a file picker with client + server JPEG/PNG ≤ 10 MB validation, uploads to the Supabase Storage signed URL (T50), shows progress/error, and replaces `SAMPLE_BTS`.

## Source
- Spec reqs: **MEDIA-2**, **MEDIA-5**
- ADRs: [ADR-0008](../../../decisions/adr/0008-no-content-moderation.md) (technical validation only) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)

## Scope
### In Scope
- `ArtistPage.tsx` — file picker; client validation (JPEG/PNG, ≤ 10 MB); request a signed URL (T50); upload; progress + error states; create the `ArtistPost`.
- Replace `SAMPLE_BTS` with real artist posts.

### Out of Scope
- Storage backend (T50); engagement analytics (T52).
- **Moderation — none (ADR-0008).**

## Validation & authz (ADR-0007 + ADR-0008)
- Client validates type/size for UX; the server (T50) is the real gate. **No moderation** — technical validation only.

## Current State (on `develop`)
- `pages/ArtistPage.tsx` renders `SAMPLE_BTS` (line ~149, defined ~179).
- Signed-upload + create endpoints come from T50 (`blocked_by: [050]`).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `apps/web/src/pages/ArtistPage.tsx` | MODIFY | upload flow + validation; remove `SAMPLE_BTS` |

## Testing Checklist
- [~] JPEG/PNG ≤ 10 MB uploads successfully via the signed URL (flow built; real-Storage upload
  can't be verified locally — see Outcome)
- [x] oversized or wrong-type file rejected client-side (and server rejects if forced)
- [x] progress + error states render
- [x] `SAMPLE_BTS` removed; real `ArtistPost`s render (n/a — the Python frontend had no artist page;
  built fresh, rendering real `ArtistPost` rows)
- [ ] ≥ 98% upload success across 5 file types up to 10 MB (integration check — needs the real
  Supabase bucket; not runnable in CI/local)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T50 → blocked_by 050)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T51-artist-upload-ui`; one PR back into `develop` (never `main`). Owner: Sebastian.

## Outcome (as built)
Built as the Python/Jinja frontend (ADR-0013). The Python frontend had **no artist page**, so this
built the surface: `GET /artist` (`pages.py` + `artist.html`) shows the artist's promo posts, and —
for artist accounts (`User.is_artist`) — an upload box. `static/artist-upload.js` validates the
file (JPEG/PNG, ≤ 10 MB) client-side, then does the T50 flow: `POST /api/artist/sign-upload` → PUT
the file to the Supabase Storage signed URL → `POST /api/artist/posts`. Progress/error states shown
inline. The upload box is hidden for non-artists (the T50 API is the real 403 gate). Satisfies
**MEDIA-2**. Tests: `backend/tests/test_pages.py` (artist sees the box, non-artist doesn't, existing
posts render).

**⚠ Two things need a real environment / an Andrea decision before this is truly done end-to-end:**
1. **The actual Storage upload is unverified.** The signed-URL PUT to Supabase Storage can't be run
   locally or in CI (needs the real `artist-images` bucket + credentials). The code follows the
   standard signed-upload pattern, but the **MEDIA-5 ≥98%-success integration check is not run** —
   left unchecked above.
2. **Image display from the private bucket is an open question.** The post stores the object **path**
   as `imageUrl`; a private bucket needs a **signed read URL** to actually display the image, which
   doesn't exist yet. This is a T50/storage-layer decision for Andrea (public bucket vs. signed read
   URLs). Until it's resolved, uploaded images may not render.

- **Files:** `backend/app/routers/pages.py`, `backend/app/templates/artist.html`,
  `backend/app/static/artist-upload.js`, `brink.css`, `backend/tests/test_pages.py`.
