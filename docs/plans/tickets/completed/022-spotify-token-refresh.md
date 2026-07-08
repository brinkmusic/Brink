---
status: Completed
priority: High
complexity: Medium
category: Feature
tags: [backend, spotify, auth, crypto, tokens]
blocked_by: [006]
blocks: [020, 021]
parent_ticket: null
owner: Andrea
---

# Feature: Server-side Spotify token refresh (T22)

## Rationale
Every server-side Spotify call (now-playing T20, the snapshot job T21) needs a **valid** access
token. Spotify access tokens expire after ~1 hour and Supabase does **not** refresh them for us — we
own that. We store an encrypted refresh token at capture time (T02/T06), but the piece that actually
*uses* it — decrypt the refresh token, exchange it at Spotify's token endpoint for a fresh access
token, and re-store the result — was never built. T20 and T21 both assumed it existed
(`get_valid_access_token` in `backend/app/spotify.py`); it doesn't. This ticket builds it, satisfying
the real **AUTH-5**, so the Spotify-reading tickets have a shared, reviewed helper to build on.

## Summary
Add `backend/app/spotify.py` with `get_valid_access_token(session, user_id)`: returns a usable
Spotify access token for a user — the stored one if it's still fresh, otherwise a newly refreshed one
(exchanged at Spotify's token endpoint using the encrypted refresh token, then re-encrypted and
persisted). Returns `None` for a user with no linked Spotify or when a refresh fails, so callers
degrade gracefully instead of 500ing. Also declares `SPOTIFY_CLIENT_ID`/`SPOTIFY_CLIENT_SECRET` in
`config.Settings`.

## Source
- Spec reqs: **AUTH-5** (server owns Spotify token refresh) — currently mis-marked ✅ against T02; this
  ticket is what actually implements it.
- ADRs: [ADR-0005](../../../decisions/adr/0005-identity.md) (server-side token refresh) ·
  [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md) ·
  [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md).

## Scope
### In Scope
- `backend/app/spotify.py` — `get_valid_access_token(session, user_id) -> str | None`:
  - no `SpotifyToken` row → `None` (unlinked handle account);
  - token still valid (expiry beyond a small buffer) → return the decrypted access token, no network;
  - expired → POST to Spotify's token endpoint (`grant_type=refresh_token`, client id/secret),
    re-encrypt + persist the new access token / expiry (and refresh token if Spotify rotates it),
    return it;
  - refresh failure (bad response / network / missing client creds) → `None`, logged, never raises to
    the caller.
- `config.Settings` — add `spotify_client_id` / `spotify_client_secret` (Optional; already in root `.env`).

### Out of Scope
- The now-playing endpoint (**T20**) and the recently-played fetch + snapshot (**T21**) — they *consume*
  this helper.
- Re-capturing / re-linking tokens (that's the capture endpoint, T02/T09).
- Any change to the encryption scheme or `TOKEN_ENC_KEY` (reuse `security/crypto.py` as-is).

## Validation & authz (ADR-0007 — required on this ticket)
- **Crypto:** refresh + access tokens are only ever handled decrypted in memory; the DB row stays
  encrypted (reuse `crypto.encrypt`/`decrypt`).
- **Graceful degradation:** unlinked user and refresh failure both return `None` — a Spotify outage or
  a revoked token must never surface as a 500 to a caller.
- **Config:** missing `SPOTIFY_CLIENT_ID`/`SECRET` → treated as "cannot refresh" (`None`), not a crash.

## Current State (on `develop`)
- `backend/app/routers/auth.py` captures + encrypts the access/refresh tokens into `SpotifyToken`
  (`user_id` PK, `access_token`, `refresh_token`, `expires_at` naive-UTC, `scopes`).
- `backend/app/security/crypto.py` — `encrypt`/`decrypt` (AES-256-GCM). `httpx` is a dependency.
- **No `backend/app/spotify.py` exists yet** and there is no token-refresh code anywhere (despite T20/T21
  "Current State" claiming it was built in T06 — those notes are wrong and are corrected as part of this
  ticket's close-out).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/spotify.py` | CREATE | `get_valid_access_token` + the Spotify token-endpoint refresh |
| `backend/app/config.py` | MODIFY | declare `spotify_client_id` / `spotify_client_secret` |
| `backend/tests/test_spotify.py` | CREATE | valid / expired-refresh / no-token / refresh-failure cases |
| `backend/tests/conftest.py` | MODIFY | add `SpotifyToken` to the in-memory test DB tables |

## Testing Checklist
- [ ] no `SpotifyToken` row → `None`, no network call
- [ ] unexpired token → returns the decrypted access token, no refresh attempted
- [ ] expired token → refresh called, new token persisted (re-encrypted) + expiry bumped, returned
- [ ] refresh returns a rotated refresh token → the new refresh token is stored
- [ ] refresh fails (non-200 / network error / missing client creds) → `None`, no crash

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T06 auth/crypto port done; unblocks T20, T21)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T22-spotify-token-refresh`; one PR into `develop`. **Auth/crypto change**
(handles decrypted tokens + `SpotifyToken` writes) — per CLAUDE.md it needs a deliberate second review
and **must not be self-merged**. Discovered while starting T20, whose "Current State" wrongly assumed
this helper existed; T20/T21 resume once this merges.
