---
status: Completed
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
- [x] sign-upload returns a valid signed URL for the owning artist
- [x] non-owner cannot mint an upload for another artist → 403 (a non-artist account, `isArtist=false`)
- [x] create persists an `ArtistPost` with object URL (+ optional track)
- [x] oversized / non-JPEG-PNG intent rejected at the contract level

## Outcome (as built)
Shipped per **Option A — artist-account gate** (chosen with the owner). Both routes are login-gated
**and artist-only**: the caller must be an artist account (`User.isArtist == true`), and the artist
is **always** the authenticated caller (never read from the body), so it can't be spoofed — the same
unspoofable-author precedent as `Post` (T10). A non-artist caller gets **403**.

- `POST /api/artist/sign-upload` — mints a Supabase Storage signed upload URL (service role) for the
  private `artist-images` bucket, at a path namespaced under the caller: `<artistUserId>/<uuid>.<ext>`.
  JPEG/PNG ≤ 10 MB is enforced at the **contract level** (`SignUploadBody`: `contentType` is a
  `Literal`, `sizeBytes` bounded) → a bad request is a 400 before any logic runs (ADR-0007/0008,
  technical validation only; **no** moderation).
- `POST /api/artist/posts` — creates an `ArtistPost` (image URL + caption + optional `linkedTrackId`),
  returning the camelCase `ArtistPostOut` (ADR-0012).
- **Files:** `backend/app/routers/artist.py` (new) · `backend/app/schemas.py` (`SignUploadBody`,
  `SignUploadOut`, `CreateArtistPostBody`, `ArtistPostOut`) · `backend/app/security/supabase.py`
  (`create_signed_upload_url` helper) · `backend/app/main.py` (router registered) ·
  `backend/app/models.py` (`ArtistPost.imageUrl` now documents Supabase Storage, not Cloudinary) ·
  `backend/tests/test_artist.py` (11 tests) · `backend/tests/conftest.py` (ArtistPost in the test DB).
- **Tests:** 11 new; full backend suite **141 passed**. No DB migration (comment-only model change).
- **Deploy step for Andrea:** create the **private** Supabase Storage bucket `artist-images` in
  `brink-dev`, or `sign-upload` errors in production (tests stub storage, so CI can't catch a missing
  bucket).
- **Deliberate scope calls:** no rate-limit on these writes (not in ticket scope; closed
  team-controlled demo per ADR-0008), and no `is_artist`-provisioning path (setting the flag is out
  of scope here).

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T01, T02 done)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T50-storage-backend`; one PR back into `develop` (never `main`). Owner: Andrea.
