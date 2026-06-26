---
status: Backlog
priority: Medium
complexity: Medium
category: Feature
tags: [backend, artist, storage, supabase, validation]
blocked_by: []
blocks: [051, 052]
parent_ticket: null
---

# Feature: Supabase Storage signed-upload backend (T50)

## Rationale
The artist BTS portal needs a way to store uploaded images and create artist posts. Per ADR-0002 storage is Supabase (not Cloudinary), via signed upload URLs minted with the service role.

## Summary
`POST /api/artist/sign-upload` mints a Supabase Storage signed upload URL; `POST /api/artist/posts` creates an `ArtistPost` with the stored object URL + optional `linkedTrackId`.

## Source
- Spec reqs: **MEDIA-1**, **MEDIA-3**, **BE-9**
- ADRs: [ADR-0002](../../../decisions/adr/0002-api-and-persistence.md) (Supabase Storage) · [ADR-0008](../../../decisions/adr/0008-no-content-moderation.md) (technical validation only) · [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)

## ⚠ Fix stale schema comment
`ArtistPost.imageUrl` is commented `// Cloudinary secure URL` — that's stale. ADR-0002 chose Supabase Storage; update the comment to Supabase Storage in this PR.

## Scope
### In Scope
- `api/artist/sign-upload.ts` — mint a Supabase Storage signed upload URL (service role) for the private `artist-images` bucket; enforce JPEG/PNG ≤ 10 MB intent in the contract.
- `api/artist/posts.ts` — create an `ArtistPost` (image object URL + caption + optional `linkedTrackId`).
- Update the `ArtistPost.imageUrl` schema comment.

### Out of Scope
- The upload UI (T51); engagement analytics (T52).
- **Content moderation — none (ADR-0008).** Technical validation only.

## Validation & authz (ADR-0007 + ADR-0008)
- **Authorization:** `requireUser` + **ownership** — only the owning artist mints uploads / creates their `ArtistPost`.
- **Business rule (technical only):** uploads ≤ 10 MB, JPEG/PNG. **No NSFW/abuse scanning, no approval queue** (ADR-0008 — closed demo, team-controlled).
- **Integrity:** FK `ArtistPost.artistUserId → User`.

## Current State (on `develop`)
- `prisma/schema.prisma` `ArtistPost { artistUserId, imageUrl, caption, linkedTrackId }` (imageUrl comment stale).
- `api/_lib/supabase.ts` + `SUPABASE_SERVICE_ROLE_KEY` in env (CLAUDE.md). `requireUser` exists.
- No `api/artist/*` yet.

## Manual (user)
- Create a **private** Supabase Storage bucket `artist-images`. (`SUPABASE_SERVICE_ROLE_KEY` already in env.)

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `api/artist/sign-upload.ts` | CREATE | mint signed upload URL |
| `api/artist/posts.ts` | CREATE | create `ArtistPost` |
| `prisma/schema.prisma` | MODIFY | fix `imageUrl` comment (Cloudinary → Supabase Storage) |
| `api/__tests__/artist.test.ts` | CREATE | tests |

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
