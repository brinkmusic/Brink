---
status: Backlog
priority: Medium
complexity: Medium
category: Feature
tags: [backend, artist, storage, supabase, validation]
blocked_by: []
blocks: [051, 052]
parent_ticket: null
owner: Andrea
---

# Feature: Supabase Storage signed-upload backend (T50)

## Rationale
The artist BTS portal needs a way to store uploaded images and create artist posts. Storage is Supabase (not Cloudinary) — chosen in ADR-0002, retained under ADR-0010 — via signed upload URLs minted with the service role.

## Summary
`POST /api/artist/sign-upload` mints a Supabase Storage signed upload URL; `POST /api/artist/posts` creates an `ArtistPost` with the stored object URL + optional `linkedTrackId`.

## Source
- Spec reqs: **MEDIA-1**, **MEDIA-3**, **BE-9**
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md) (FastAPI/Supabase; Supabase Storage retained) · [ADR-0008](../../../decisions/adr/0008-no-content-moderation.md) (technical validation only) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)

## ⚠ Fix stale schema comment
`ArtistPost.imageUrl` carries a stale `Cloudinary secure URL` comment. The choice is Supabase Storage; update the comment to Supabase Storage on the `ArtistPost` model in `backend/app/models.py` in this PR.

## Scope
### In Scope
- `backend/app/routers/artist.py` (`POST /api/artist/sign-upload`) — mint a Supabase Storage signed upload URL (service role) for the private `artist-images` bucket; enforce JPEG/PNG ≤ 10 MB intent in the contract.
- `backend/app/routers/artist.py` (`POST /api/artist/posts`) — create an `ArtistPost` (image object URL + caption + optional `linkedTrackId`).
- Update the `ArtistPost.imageUrl` model comment.

### Out of Scope
- The upload UI (T51); engagement analytics (T52).
- **Content moderation — none (ADR-0008).** Technical validation only.

## Validation & authz (ADR-0007 + ADR-0008)
- **Authorization:** `require_user` + **ownership** — only the owning artist mints uploads / creates their `ArtistPost`.
- **Business rule (technical only):** uploads ≤ 10 MB, JPEG/PNG. **No NSFW/abuse scanning, no approval queue** (ADR-0008 — closed demo, team-controlled).
- **Integrity:** FK `ArtistPost.artistUserId → User`.

## Current State (on `develop`)
- `backend/app/models.py` `ArtistPost { artistUserId, imageUrl, caption, linkedTrackId }` (imageUrl comment stale).
- `backend/app/security/supabase.py` + `SUPABASE_SERVICE_ROLE_KEY` in env (CLAUDE.md). `require_user` exists.
- No artist router (`backend/app/routers/artist.py`) yet.

## Manual (user)
- Create a **private** Supabase Storage bucket `artist-images`. (`SUPABASE_SERVICE_ROLE_KEY` already in env.)

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/artist.py` | CREATE | `sign-upload` + `posts` routes |
| `backend/app/models.py` | MODIFY | fix `imageUrl` comment (Cloudinary → Supabase Storage) |
| `backend/tests/test_artist.py` | CREATE | tests |

## Testing Checklist
- [ ] sign-upload returns a valid signed URL for the owning artist
- [ ] non-owner cannot mint an upload for another artist → 403
- [ ] create persists an `ArtistPost` with object URL (+ optional track)
- [ ] oversized / non-JPEG-PNG intent rejected at the contract level

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T01, T02 done)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T50-storage-backend`; one PR back into `develop` (never `main`). Owner: Andrea.
