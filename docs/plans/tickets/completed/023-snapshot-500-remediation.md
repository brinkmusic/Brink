---
status: Completed
priority: High
complexity: Low
category: Bug
tags: [backend, spotify, snapshot, sqlmodel, crypto, resilience]
blocked_by: [021, 022]
blocks: []
parent_ticket: 021
owner: Andrea
---

# Bug: snapshot cron 500 remediation — FK insert-ordering + token-decrypt guard (T23)

## Rationale
The first `develop → main` release (#79) put the T21 snapshot cron live, and it returned **HTTP 500**, not 401 — so the `X-Cron-Secret` was correct and the crash was inside the handler. Diagnosed by reproducing the run against `brink-dev` with a full traceback. Two independent defects, both fixed here (one incident = one PR):

### 1. Foreign-key insert-ordering (the actual cause)
`snapshot._ingest_user` upserts a `Track`, then adds a `Play` that foreign-key-references it, in a loop. It relied on SQLAlchemy's autoflush to insert each `Track` before its `Play`, but across the batched loop that ordering isn't guaranteed on Postgres — a batch of new tracks raised:
```
psycopg.errors.ForeignKeyViolation: insert or update on table "Play" violates
constraint "Play_trackId_fkey" — Key (trackId)=(…) is not present in table "Track".
```
**Why the suite missed it:** the shared `db_session` test fixture uses SQLite, which does **not** enforce foreign keys unless asked (`PRAGMA foreign_keys=ON`), and the existing snapshot test used a single track (no interleaved autoflush). So the FK path was never exercised.

### 2. Unguarded token decryption (defensive hardening)
`spotify.get_valid_access_token` called `decrypt(...)` on the stored access/refresh tokens with no guard. `decrypt` raises `InvalidTag` when a token was encrypted under a different `TOKEN_ENC_KEY`, and `ValueError` on a malformed value — either would propagate through `get_recently_played` → `run_snapshot` and 500 the whole run, despite the function's docstring promising "None (never an exception)."

## Summary
- **snapshot.py:** `session.flush()` after each `upsert_track`, so the Track is written before the Play that references it.
- **spotify.py:** `_safe_decrypt` (catches `ValueError`/`InvalidTag`, logs, returns `None`); used at both decrypt sites so an unreadable token is skipped like a missing/expired one.
- **tests:** a `fk_session` fixture with SQLite FK enforcement + a multi-new-track regression test (reproduces the 500); two decrypt-failure tests. `_linked_user` now commits the User before the token (FK-safe under enforcement).

## Source
- Parents: [T21](021-snapshot-github-actions.md) (the failing cron), [T22](022-spotify-token-refresh.md) (the decrypt path). Crypto contract: `app/security/crypto.py`.

## Scope
### In Scope
- `backend/app/routers/snapshot.py` — flush Track before Play.
- `backend/app/spotify.py` — `_safe_decrypt` guard at both sites.
- `backend/tests/test_snapshot.py` + `test_spotify.py` — regression tests + FK-enforcing fixture.

### Out of Scope
- The operational `TOKEN_ENC_KEY`/re-login remediation (config; turned out the key already matched — the token was readable).
- Enabling FK enforcement in the **shared** `db_session` fixture (wider blast radius) — noted as a follow-up.
- The likely same insert-ordering gap in the T10 posts endpoint (upsert_track + Post in one commit) — noted as a follow-up to verify.

## Validation & authz (ADR-0007)
- No request-surface change. Converts two unhandled-exception paths into the documented graceful behavior.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/routers/snapshot.py` | MODIFY | `session.flush()` before adding each `Play` |
| `backend/app/spotify.py` | MODIFY | `_safe_decrypt` + guarded decrypt at both sites |
| `backend/tests/test_snapshot.py` | MODIFY | `fk_session` fixture + FK-ordering regression test; FK-safe `_linked_user` |
| `backend/tests/test_spotify.py` | MODIFY | two unreadable-token regression tests |

## Testing Checklist
- [x] Reproduced the FK 500 on SQLite-with-FK-enforcement (red), then fixed (green)
- [x] Reproduced the decrypt-raise path (red), then fixed (green)
- [x] `cd backend && uv run pytest` green — **130 passed**
- [x] End-to-end against `brink-dev` (real Spotify token): snapshot ingested **50 plays**, committed, idempotent on re-run

## Notes
Branch `fix/T23-token-decrypt-guard` off `develop`; one PR into `develop`. Discovered while validating the release-#79 snapshot cron. Auth/crypto-adjacent — second review encouraged, not required (owner may self-merge). **This fix reaches production only at the next `develop → main` release** (Render builds `main`).
