---
status: Completed
priority: High
complexity: Low
category: Bug
tags: [backend, spotify, crypto, snapshot, resilience]
blocked_by: [022]
blocks: []
parent_ticket: 022
owner: Andrea
---

# Bug: guard token decryption so one unreadable token can't 500 the snapshot (T23)

## Rationale
Found in production during the first `develop → main` release: the T21 snapshot cron returned **HTTP 500**, not 401 — so the `X-Cron-Secret` was correct and the failure was inside the handler. Root cause: `spotify.get_valid_access_token` calls `decrypt(row.access_token)` / `decrypt(row.refresh_token)` **without a guard**. `decrypt` raises `InvalidTag` when the stored token was encrypted with a different `TOKEN_ENC_KEY`, and `ValueError` on a malformed value (see `security/crypto.py`). That exception propagates through `get_recently_played` → `run_snapshot` (which has no try/except) and 500s the **entire** run — even though the function's own docstring promises "None (never an exception)."

The immediate trigger was a `TOKEN_ENC_KEY` mismatch on the stored token (a token first created by the local T09 login, then read by Render under a different key). That data issue is fixed operationally (fresh login on the live Render `/auth/login`), but the code should degrade gracefully regardless — one bad token must not take down the snapshot for every other user.

## Summary
Add `_safe_decrypt` (catches `ValueError`/`InvalidTag`, logs, returns `None`) and use it at both decrypt sites in `get_valid_access_token`. An unreadable stored token now behaves exactly like a missing/expired one: that user is skipped, the snapshot continues.

## Source
- Parent: [T22](022-spotify-token-refresh.md) (the function being hardened) · [T21](021-snapshot-github-actions.md) (the caller that 500'd).
- Crypto contract: `backend/app/security/crypto.py` (`InvalidTag` = wrong key/tamper; `ValueError` = malformed).

## Scope
### In Scope
- `backend/app/spotify.py`: `_safe_decrypt` helper; guard the fresh-token and refresh-token decrypt calls; when the refresh token is unreadable, skip the network refresh and return `None`.
- Tests: unreadable fresh token → `None`; unreadable refresh token → `None` and no refresh attempt.

### Out of Scope
- The operational `TOKEN_ENC_KEY`/re-login remediation (config, done by Andrea).
- Any change to the snapshot router or the crypto format.

## Validation & authz (ADR-0007)
- No request-surface change. This only converts an unhandled exception into the documented graceful `None`.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/spotify.py` | MODIFY | `_safe_decrypt` + guarded decrypt at both sites |
| `backend/tests/test_spotify.py` | MODIFY | two regression tests (fresh + refresh unreadable → None) |

## Testing Checklist
- [x] Failing tests first: unreadable token raised through `get_valid_access_token` (reproduced the 500 path)
- [x] After fix: both return `None`; no refresh attempted when the refresh token is unreadable
- [x] `cd backend && uv run pytest` green — **129 passed**

## Notes
Branch `fix/T23-token-decrypt-guard` off `develop`; one PR into `develop`. Auth/crypto-adjacent (`app/spotify.py` reads encrypted tokens) — second review encouraged but not required (owner may self-merge). Discovered while validating the release PR #79 snapshot cron.
