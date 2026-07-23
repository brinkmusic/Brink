---
status: Completed
priority: High
complexity: Small
category: Fix
tags: [backend, feed, artist, storage, resilience]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Fix: one unsignable artist image must not blank the feed or 500 the artist page (T103)

## Rationale
On 2026-07-22, right after the Wave 2 release, production showed an **empty feed** ("No songs
shared yet") and a raw **500 Internal Server Error** on `/artist`. Root cause was environmental —
production's Supabase `SUPABASE_SERVICE_ROLE_KEY` couldn't sign private `artist-images` objects, so
`create_signed_read_url` raised `StorageApiError: 404 Object not found` (fixed by correcting the
Render env var). But the **code fragility is ours**: a single artist image that can't be signed
takes down the *entire* feed and the whole artist page, because the two call sites let the exception
propagate. `build_feed` builds song + artist items and merges — so an artist-image signing failure
throws the whole builder, and the feed page's `try/except` then renders an EMPTY feed (songs and
all). `/artist` has no guard at all → 500.

This is the same class of fragility [T84](../completed/) fixed for the profile page — and the
profile's artist-post signing was *already* hardened (`pages.py::_signed_artist_image_url`
try/except → `""`). The feed and artist page never got the same treatment.

## Summary
Make artist-image signing **degrade gracefully everywhere**: a signing failure yields a blank URL
(logged), and the template renders a muted placeholder instead of a broken `<img>` — so one bad
object never blanks the feed or 500s a page. Factor the safe-signing pattern (already present in
`_signed_artist_image_url`) into ONE shared helper reused at all three call sites.

## Source
- Bug: production incident 2026-07-22 (feed empty + `/artist` 500), traceback
  `storage3 ... StorageApiError: {'statusCode': 404, ... 'Object not found'}` at
  `pages.py:479 -> security/supabase.py:130`.
- Spec reqs: **UI-2** (feed cards), **MEDIA-5**/**BE-9** (artist posts + signed reads, T53/T54),
  robustness sibling of **T84**.

## Current State (verified 2026-07-22)
- `create_signed_read_url(bucket, path)` (`app/security/supabase.py`) calls Supabase Storage and
  **raises** `StorageApiError` on any failure (missing object, bad key, outage).
- Three call sites:
  - `feed.py:311` (`_build_artist_items`) — **unguarded** → kills the whole feed.
  - `pages.py:479` (`artist_page`) — **unguarded** → 500s `/artist`.
  - `pages.py:397` (`_signed_artist_image_url`, used by the profile) — **already** try/except →
    `""` + log. Good; this is the pattern to share.
- Templates: `profile.html:222` already guards `{% if post.image_url %}`. `feed.html:76` and
  `artist.html:52` render `<img src="{{ image_url }}">` **unconditionally** (empty src → broken img).

## Scope
### In Scope
- One shared safe wrapper `create_signed_read_url_or_blank(bucket, path)` in `security/supabase.py`:
  try/except around `create_signed_read_url`, `logger.warning` on failure, return `""`.
- Use it at `feed.py:311` and `pages.py:479`; refactor `_signed_artist_image_url` to delegate (no
  duplicated try/except).
- Template placeholders for a blank image URL in `feed.html` and `artist.html` (muted box,
  consistent with `profile.html`'s existing guard); add a matching `{% else %}` placeholder to
  `profile.html` for consistency.
- Muted `.artist-post-img-missing` placeholder style in `brink.css`.
- Tests: unit (wrapper returns `""` on inner raise, passes through on success); feed integration
  (signing raises → `build_feed` still returns items, artist item `imageUrl == ""`, song items
  intact); `/artist` integration (signing raises → 200 with placeholder, not 500).

### Out of Scope
- The production env fix itself (correcting Render's `SUPABASE_SERVICE_ROLE_KEY`) — already done by
  the owner, not a code change.
- Retry/backoff or caching of signed URLs (a signing failure is rare; a placeholder is enough v1).
- Any change to `create_signed_read_url`'s success behavior or to upload signing.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/security/supabase.py` | MODIFY | `create_signed_read_url_or_blank` + module logger |
| `backend/app/routers/feed.py` | MODIFY | use the safe wrapper for artist images |
| `backend/app/routers/pages.py` | MODIFY | use the safe wrapper (artist page + profile helper) |
| `backend/app/templates/feed.html` | MODIFY | placeholder when image URL blank |
| `backend/app/templates/artist.html` | MODIFY | placeholder when image URL blank |
| `backend/app/templates/profile.html` | MODIFY | matching placeholder (consistency) |
| `backend/app/static/brink.css` | MODIFY | `.artist-post-img-missing` style |
| `backend/tests/test_supabase_signing.py` | CREATE | wrapper unit test |
| `backend/tests/test_feed.py` | MODIFY | signing-failure feed resilience + stub update |
| `backend/tests/test_pages.py` | MODIFY | `/artist` stays 200 on signing failure |
| `docs/plans/requirements.md` | MODIFY | UI-2 note (at close-out) |
| `docs/plans/tickets/README.md` | MODIFY | record completion (at close-out) |

## Testing Checklist
- [x] wrapper returns `""` (and logs) when `create_signed_read_url` raises; passes value through on success
- [x] `build_feed` with signing raising → returns items (artist `imageUrl == ""`), song items intact — no throw
- [x] `GET /artist` with signing raising → 200 with a placeholder, not 500
- [x] feed/artist templates render a placeholder (not a broken `<img>`) for a blank URL
- [x] existing artist-image signing tests still pass (stub updated to the wrapper)
- [x] full backend suite passes (283 passed)

## Outcome (as built)
- **Shared helper:** `create_signed_read_url_or_blank(bucket, path, expires_in=3600)` in
  `app/security/supabase.py` (with a module `logger`): wraps `create_signed_read_url` in try/except,
  logs a warning, returns `""` on any failure.
- **Call sites now resilient:** `feed.py::_build_artist_items` (was unguarded → blanked the whole
  feed) and `pages.py::artist_page` (was unguarded → 500'd `/artist`) both use the wrapper. The
  profile's local `_signed_artist_image_url` helper was **deleted** and its call site now uses the
  same shared wrapper — one pattern, no duplication.
- **Templates:** `feed.html`, `artist.html`, and `profile.html` render a muted
  `.artist-post-img-missing` placeholder (styled in `brink.css`) when `image_url` is `""`, instead
  of a broken `<img>` with an empty `src`.
- **Verified against the real incident:** with signing forced to fail (StorageApiError 404) on the
  live DB + render path, `/feed` returns 200 with songs still visible and `/artist` returns 200 —
  both with the placeholder, the failure logged.
- **Tests:** new `test_supabase_signing.py` (wrapper pass-through + returns `""` on raise); feed
  integration (signing raises → feed keeps all items, artist `imageUrl == ""`); `/artist`
  integration (signing raises → 200 + placeholder, not 500); the profile signing-failure test now
  exercises the real wrapper via the underlying signer; existing success stubs retargeted to the
  wrapper name.
- **Root cause note:** the incident's *trigger* was a production env issue (wrong Render
  `SUPABASE_SERVICE_ROLE_KEY` → Supabase 404), fixed outside this ticket. T103 fixes the *code
  fragility* that let one un-signable image take down whole surfaces.

## Notes / Risks
- `security/supabase.py` is a security-sensitive file (auth/crypto area). This change only adds a
  defensive *display* helper + a logger — no change to auth, token, or upload-signing behavior — but
  call it out in the PR and run the full suite.
- The shared dev/prod database (T99) means the same objects are read from both; this fix is purely
  about not crashing when a read-URL can't be minted, regardless of why.
