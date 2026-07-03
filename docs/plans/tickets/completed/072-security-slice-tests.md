---
status: Completed
priority: Medium
complexity: Low
category: Test
tags: [backend, security, crypto, tests, review-remediation, second-review]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Test: Security-slice test gaps + contract fixes (T72)

## Rationale
Findings **MB2**, **MB3**, **L2**, **L3** of the [2026-07-02 code review](../../reviews/2026-07-02-code-review-t00-t08.md).
The security-critical properties of the AES-256-GCM port are unverified: nothing tests that
tampering with a stored blob makes `decrypt` raise, that a wrong (but valid-length) key fails, or
that the iv is unique per encryption — a fixed-iv regression (the classic catastrophic GCM
failure) would pass today's suite. Separately, `security/supabase.py`'s contract comment is wrong
(verified against installed `supabase_auth` 2.31.0: `get_user` **raises** `AuthApiError` on an
invalid token; it returns `None` only for an empty one) — a future caller trusting "check for
None" would 500 on bad tokens.

## Summary
Add the missing tamper / wrong-key / nonce-uniqueness / branch tests; correct the `get_user`
contract comment; make malformed base64 fail as the intended `ValueError` (`validate=True`); type
the `get_user_from_token` return properly.

## Source
- Review findings: **MB2**, **MB3**, **L2**, **L3**
- Spec reqs: **AUTH-3** (encrypted token storage)
- ADRs: [ADR-0005](../../../decisions/adr/0005-identity.md) (encrypted server-side tokens are a security obligation) · [ADR-0010](../../../decisions/adr/0010-fastapi-render-backend.md) (crypto port + encoding compatibility)

## Scope
### In Scope
- `test_crypto.py`: tamper test (corrupt one base64 part of a valid blob → `InvalidTag`);
  wrong-key test (second random 32-byte key → `InvalidTag`); nonce-uniqueness test (encrypt the
  same plaintext twice → iv parts differ); branch tests for `TOKEN_ENC_KEY` unset, empty-part
  blob (`"a..c"`), and key-length check via `decrypt`.
- `crypto.py`: `base64.b64decode(p, validate=True)` (`binascii.Error` subclasses `ValueError`, so
  the existing test contract holds) + one comment line documenting what raises what
  (`ValueError` = malformed format, `InvalidTag` = tamper/wrong key) — T21 is the first real
  consumer of that contract.
- `supabase.py`: correct the return-contract comment; type the return as
  `Optional[supabase_auth.types.User]` instead of `Optional[Any]`.

### Out of Scope
- Any change to key management, `TOKEN_ENC_KEY` policy, the encoding format (compatibility
  constraint), or the `getUser()` validation approach.
- `deps.py` (T71) and the shared test fixtures (T73).

## Validation & authz (ADR-0007)
Test-and-comment ticket; locks down the integrity guarantees the encrypted-token store already
claims to have.

## Current State (on `develop`)
- `test_crypto.py` covers format parity (TS-era vector), round-trip, malformed format, bad key
  length — but none of the tamper/wrong-key/nonce properties.
- `supabase.py:25-29` documents a `None` return that real invalid tokens never produce.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/tests/test_crypto.py` | MODIFY | tamper, wrong-key, nonce, branch tests |
| `backend/app/security/crypto.py` | MODIFY | `validate=True` + exception-contract comment |
| `backend/app/security/supabase.py` | MODIFY | contract comment + return type |

## Testing Checklist
- [ ] failing tests first: tamper (iv, tag, and ct each corrupted) → `InvalidTag`
- [ ] wrong 32-byte key → `InvalidTag`
- [ ] two encryptions of one plaintext → different blobs (different ivs)
- [ ] stray non-base64 characters in a part → `ValueError` (not `InvalidTag`)
- [ ] `TOKEN_ENC_KEY` unset → `ValueError("TOKEN_ENC_KEY not set")`
- [ ] TS-era vector still decrypts (compat unchanged); full suite passes

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (none)
- [x] Scope boundaries defined

## Notes
Branch `test/T72-security-slice-tests`. **`security/*` is on the second-review list — do not
self-merge.** The `validate=True` change is the only behavior change; everything else is tests
and comments.
