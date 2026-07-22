---
status: Completed
priority: Medium
complexity: Small
category: Feature
tags: [backend, frontend, profile, storage]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Feature: Editable profile — bio + profile picture (T48)

## Rationale
Users can't set a bio, and email sign-ups have no profile picture (Spotify users get `avatar_url`
from Spotify metadata; email users leave it `null`). There was no in-app way to change either. This
adds an "Edit profile" surface so any user can set a bio and upload a profile picture. Bundled as one
ticket because the two share the same edit surface, the `User` model, and one migration.

## Summary
On your **own** profile an "Edit profile" control reveals a small form: a profile-picture file input
(JPEG/PNG ≤ 10 MB) + a bio textarea (≤ 300 chars), prefilled with your current bio. Save uploads the
new picture (if picked) via a signed-upload flow to a public `avatars` bucket, then PATCHes the bio,
then reloads. The bio renders under the profile header on every profile.

## Source
- Spec reqs: **UI-11** (new — editable profile: user bio + profile-picture upload)
- ADRs: [ADR-0013](../../../decisions/adr/0013-python-frontend.md) (Jinja/HTMX frontend) ·
  [ADR-0012](../../../decisions/adr/0012-camelcase-dtos.md) (camelCase DTOs) ·
  [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md) (validation/authz) ·
  [ADR-0008](../../../decisions/adr/0008-media-technical-validation-only.md) (technical validation
  only, no moderation)

## Scope
### In Scope
- `PATCH /api/me/profile` — set the caller's own bio (trim, ≤ 300, empty clears to NULL).
- `POST /api/me/avatar/sign-upload` — signed upload URL for the caller's own path in the **public**
  `avatars` bucket; returns `{ signedUrl, token, path, publicUrl }`.
- `POST /api/me/avatar` — set the caller's `avatar_url` to the public object URL (path must be in the
  caller's own folder, else 400).
- New `User.bio` column (nullable Text) + hand-written Alembic migration.
- Own-profile "Edit profile" form (file input + bio textarea) + `static/edit-profile.js`.
- Bio rendered under the profile header (own + others').

### Out of Scope
- Editing display name / handle.
- Image cropping / resizing / moderation (ADR-0008: technical validation only).
- Deleting an avatar back to null through the UI (re-upload replaces it).

## Validation & authz (ADR-0007)
- **Authorization:** `require_user` on all three endpoints; every write is on the authenticated
  caller (resolved from the session), never a client-supplied id.
- **Integrity:** bio trimmed + length-capped by the schema; empty bio → NULL. Avatar path must start
  with `<callerUserId>/` so a caller can't point their avatar at someone else's object.
- **Media:** `contentType` Literal jpeg/png + `sizeBytes` ≤ 10 MB at the request contract (reuses
  `SignUploadBody`).

## Current State (on `develop`)
- `User.avatar_url` already exists and already renders on profiles (Spotify metadata fills it).
- `backend/app/routers/me.py` exists (T55) with `POST /api/me/become-artist`.
- `create_signed_upload_url` exists in `security/supabase.py` (T50).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/models.py` | MODIFY | add `User.bio` (nullable Text) |
| `backend/alembic/versions/a1c47f9e2b30_add_user_bio_t48.py` | CREATE | hand-written migration |
| `backend/app/security/supabase.py` | MODIFY | `public_object_url(bucket, path)` helper |
| `backend/app/schemas.py` | MODIFY | `UpdateProfileBody`, `AvatarSaveBody`, `ProfileBioOut`, `AvatarSignUploadOut`, `AvatarOut` |
| `backend/app/routers/me.py` | MODIFY | the three new endpoints |
| `backend/app/routers/pages.py` | MODIFY | add `bio` to `_profile_data` |
| `backend/app/templates/profile.html` | MODIFY | bio display + own-profile Edit form |
| `backend/app/static/edit-profile.js` | CREATE | upload avatar + PATCH bio + reload |
| `backend/tests/test_me.py` | MODIFY | endpoint tests |
| `backend/tests/test_artist.py` | MODIFY | `public_object_url` unit test |
| `backend/tests/test_pages.py` | MODIFY | bio-renders + edit-control page tests |
| `backend/tests/test_api_surface.py` | MODIFY | add the 3 routes to the T61 inventory |

## Testing Checklist
- [x] PATCH profile sets / trims / length-limits (400) / clears bio + persists
- [x] avatar sign-upload returns a signed url for the caller's own path in the public `avatars` bucket
- [x] avatar save sets `avatar_url`; a path outside the caller's folder is rejected (400)
- [x] all three endpoints 401 when unauthenticated
- [x] `public_object_url` builds the public storage path
- [x] a user's bio renders on their profile; own profile shows the Edit control + script

## Outcome (as built)
- `PATCH /api/me/profile` (`backend/app/routers/me.py`) — sets `user.bio` on the authenticated
  caller; `UpdateProfileBody` trims + caps at 300 (over-long → 400); an empty bio stores NULL.
  Returns `ProfileBioOut` (`{ bio }`, ADR-0012).
- `POST /api/me/avatar/sign-upload` — reuses `SignUploadBody` (jpeg/png + ≤ 10 MB) to mint a signed
  upload URL via `create_signed_upload_url` for a **public** `avatars` bucket at
  `<callerUserId>/<uuid>.<ext>`; returns `AvatarSignUploadOut` (`{ path, signedUrl, token, publicUrl }`).
- `POST /api/me/avatar` — verifies `path` starts with `<callerUserId>/` (else 400), then stores
  `public_object_url("avatars", path)` on `user.avatar_url`; returns `AvatarOut` (`{ avatarUrl }`).
- New `User.bio` (nullable Text) + hand-written migration `a1c47f9e2b30` (single head off
  `3978f11ad4da`). `public_object_url` added to `security/supabase.py`.
- Frontend: bio renders under the profile header (autoescaped — never marked safe); own-profile
  "Edit profile" form (file input + bio textarea, prefilled) driven by `static/edit-profile.js`
  (avatar 3-step upload → PATCH bio → reload).
- **Tests:** full backend suite **237 passed**.
- **Deliberate scope calls:** public `avatars` bucket (so avatars render without a signed read URL,
  unlike the private artist-images bucket); no rate-limit on these (a self-only profile edit has no
  abuse pattern the way posting does — consistent with become-artist).

## Manual steps (owner)
1. Create a **public** Supabase Storage bucket named `avatars` in `brink-dev`.
2. Apply the migration: `cd backend && uv run alembic upgrade head` (adds `User.bio`).

## Notes
Branch off `develop` as `feat/T048-editable-profile`; one PR back into `develop` (never `main`).
Owner: Andrea.
