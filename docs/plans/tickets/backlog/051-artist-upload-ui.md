---
status: Backlog
priority: Medium
complexity: Medium
category: Feature
tags: [frontend, artist, upload, validation]
blocked_by: [050]
blocks: []
parent_ticket: null
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
- [ ] JPEG/PNG ≤ 10 MB uploads successfully via the signed URL
- [ ] oversized or wrong-type file rejected client-side (and server rejects if forced)
- [ ] progress + error states render
- [ ] `SAMPLE_BTS` removed; real `ArtistPost`s render
- [ ] ≥ 98% upload success across 5 file types up to 10 MB (integration check)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T50 → blocked_by 050)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T51-artist-upload-ui`; one PR back into `develop` (never `main`). Owner: Sebastian.
