---
status: Completed
priority: Medium
complexity: Medium
category: Tech-Debt
tags: [backend, tests, sqlmodel, foreign-keys, posts, resilience]
blocked_by: [023]
blocks: []
parent_ticket: 023
owner: Andrea
---

# Tech-Debt: FK-ordering hardening — enforce FKs in tests + fix the posts endpoint (T62)

## Rationale
Follow-up to [T23](023-snapshot-500-remediation.md). T23 found that the snapshot endpoint inserted a child row (`Play`) before its parent (`Track`) in one commit, which Postgres rejects — and that the SQLite test suite couldn't catch it because SQLite ignores foreign keys by default. This ticket closes that whole class of gap:

1. **Enable FK enforcement suite-wide** so the tests behave like Postgres.
2. **Fix the one real production bug it surfaced** — `POST /api/posts` has the identical parent-before-child problem (`upsert_track` + `Post` in one commit).
3. Correct the CLAUDE.md deployment line that wrongly said Render deploys from `develop`.

**Root cause (why ordering matters):** the models declare foreign-key *columns* but no ORM `relationship()`, so SQLAlchemy's unit of work does **not** insert rows in FK-dependency order — it can emit a child `INSERT` before its parent within a single commit. So any code (or test seed) that adds a parent and child in the same `commit()` can violate a FK on Postgres. The fix is to `flush()` (or `commit()`) the parent before the child.

## Scope
### In Scope
- **`backend/tests/conftest.py`** — `db_session` now sets `PRAGMA foreign_keys=ON` (SQLite enforces FKs); `as_user(user, session=<real Session>)` persists the acting user via `merge()` so caller-referencing FKs (Post/Reaction/Comment/Follow) are satisfied (skipped for MagicMock sessions).
- **`backend/app/routers/posts.py`** — `session.flush()` after `upsert_track` so the `Track` is written before the `Post` that references it (the production bug).
- **Test seed fixes** (parents committed before children; missing author/caller users seeded with unique handles) across `test_posts`, `test_reactions`, `test_comments`, `test_feed`, `test_follow`, `test_spotify`, `test_pages`.
- **`CLAUDE.md`** — deployment-topology line corrected: both Vercel and Render deploy from `main`; note the post-release back-merge requirement.

### Out of Scope
- Adding ORM relationships to the models (large blast radius; the schema deliberately avoids them). The `flush()`-before-child pattern is the local fix.
- The snapshot endpoint (already fixed in T23).

## Validation & authz (ADR-0007)
- No request-surface change. The posts fix converts a potential Postgres 500 (on a brand-new track) into the intended 201.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `backend/tests/conftest.py` | MODIFY | enforce FKs in `db_session`; persist caller in `as_user` |
| `backend/app/routers/posts.py` | MODIFY | flush Track before Post |
| `backend/tests/test_{posts,reactions,comments,feed,follow,spotify,pages}.py` | MODIFY | FK-safe seed ordering + seed missing parents |
| `CLAUDE.md` | MODIFY | correct the Render deploy-branch line |

## Testing Checklist
- [x] `db_session` now enforces FKs; the suite reproduces the class of bug (30 failures surfaced, then fixed)
- [x] `POST /api/posts` FK-ordering fix verified by the (now FK-enforced) posts tests
- [x] `cd backend && uv run pytest` green — **130 passed**

## Notes
Branch `fix/T62-fk-ordering-hardening` off `develop`; one PR into `develop`. The 30 surfaced failures were 1 real production bug (posts) + 29 test-seed conveniences that SQLite's lax default had hidden.
