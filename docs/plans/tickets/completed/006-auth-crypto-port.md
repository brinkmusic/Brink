---
status: Completed
priority: High
complexity: High
category: Feature
tags: [auth, crypto, security, fastapi, migration]
blocked_by: [005]
blocks: [007]
parent_ticket: null
owner: Andrea
---

# Feature: Port auth + crypto + capture-spotify to FastAPI (T06)

## Rationale
The security-critical backend code — Supabase JWT validation, AES-256-GCM token encryption, and
the Spotify token-capture endpoint (all from T02) — must move to Python. This is the ticket the
whole migration exists for: it puts the auth/crypto the team most needs to review into a language
the team can read ([ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md)).

## Summary
Port `api/_lib/crypto.ts`, `api/_lib/supabase.ts`, `api/_lib/auth.ts` (`requireUser`), and
`api/auth/capture-spotify.ts` to FastAPI, preserving the exact wire contract and the
AES-256-GCM ciphertext format so existing stored tokens still decrypt.

## Source
- ADRs: [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md),
  [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)
- Reqs: AUTH-* (same as T02 — Supabase JWT validation server-side; encrypted Spotify tokens)

## Scope
### In Scope
- `backend/app/security/crypto.py` — AES-256-GCM via `cryptography`, reusing `TOKEN_ENC_KEY`
  (base64 32 bytes) and the **exact** `base64(iv).base64(tag).base64(ct)` encoding.
- `backend/app/security/supabase.py` — service-role admin client (`supabase-py`).
- `backend/app/deps.py` — `require_user()` FastAPI dependency: validate the bearer token via
  `auth.get_user(token)`; on first sign-in create the `User` with the **exact** handle policy
  (`slugify(displayName)` + 6 chars of the Supabase user id) and field mapping from
  `api/_lib/auth.ts`.
- `backend/app/routers/auth.py` — `POST /api/auth/capture-spotify`: same body
  (`{access_token: provider_token, refresh_token, scopes}`), same `SpotifyToken` upsert, same
  status codes and `{data}`/`{error}` envelope.

### Out of Scope
- Deploy/hosting (T07); removing the TS originals (T08).
- New auth providers or token-refresh job (T21).

## Validation & authz (ADR-0007 — required on this ticket)
- **Schema:** missing `refresh_token`/`access_token` → 400 via `fail()`.
- **Authorization:** `require_user` gates the endpoint; `userId` is the authenticated user, never
  client-supplied. Missing/invalid JWT → 401.
- **Integrity:** `SpotifyToken` upsert keyed by `userId`; tokens stored **encrypted** at rest.
- **Crypto parity:** a test decrypts a blob produced by the current TS `crypto.ts` to prove the
  format is byte-compatible (plus round-trip).

## Current State (on `develop` after T05)
- SQLModel models + session exist (T05). `User` and `SpotifyToken` are mapped.
- TS originals (`api/_lib/auth.ts`, `crypto.ts`, `supabase.ts`, `api/auth/capture-spotify.ts`)
  still present as the reference contract (removed in T08).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/security/crypto.py` | CREATE | AES-256-GCM (TS-compatible) |
| `backend/app/security/supabase.py` | CREATE | service-role client |
| `backend/app/deps.py` | CREATE | `require_user` dependency |
| `backend/app/routers/auth.py` | CREATE | `POST /api/auth/capture-spotify` |
| `backend/tests/test_crypto.py` | CREATE | round-trip + TS-blob parity |
| `backend/tests/test_auth.py` | CREATE | 401/400/upsert + handle policy |

## Testing Checklist
- [ ] crypto round-trips; decrypts a TS-`crypto.ts`-encrypted blob (format parity)
- [ ] malformed ciphertext → error; wrong key length → error
- [ ] `require_user` rejects missing/invalid bearer (401)
- [ ] first sign-in creates `User` with the same handle (`slug-<6id>`) and field mapping
- [ ] `capture-spotify` missing tokens → 400; success upserts encrypted `SpotifyToken`, returns `{ data: { captured: true } }`

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T05 → blocked_by 005)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T06-auth-crypto-port`; one PR into `develop`.
**Auth/crypto change — needs a deliberate second review per CLAUDE.md. Do not self-merge.**
