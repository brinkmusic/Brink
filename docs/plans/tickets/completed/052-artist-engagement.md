---
status: Completed
priority: Low
complexity: Medium
category: Feature
tags: [backend, frontend, artist, engagement]
blocked_by: [050, 011, 012]
blocks: []
parent_ticket: null
owner: Andrea
---

# Feature: Artist engagement analytics (T52)

## Rationale
Artists should see how their BTS posts perform — reactions, comments, and views surfaced back to them.

## Summary
Per-`ArtistPost` engagement (reaction/comment counts) surfaced **owner-only** to the artist who made
the post. **Scope note:** the ticket originally assumed reactions/comments from T11/T12 already
attached to artist posts — they don't (their FKs target `Post`, not `ArtistPost`), so there was no
engagement to aggregate. With the owner's sign-off this ticket was **widened** from a read-only
aggregate to also build the write path (reactions/comments that target artist posts), which makes it
Medium, not Low. A **view count is deferred** as a stated follow-up: there's no public artist-post
read endpoint to increment views from yet; that surface is the artist UI (T51).

## What shipped (backend)
Added under `/api/artist` in `backend/app/routers/artist.py`:
- `POST`/`DELETE /posts/{id}/reactions` — **any logged-in user** (the audience), idempotent add /
  own-only remove, returns fresh per-type counts (reuses `ReactionCountsOut`, T11 shape).
- `POST`/`GET /posts/{id}/comments` — any logged-in user; create is rate-limited + trims/validates
  `body`; list is newest-first with author (reuses `CommentOut`/`AuthorOut`, T12 shape).
- `GET /posts/{id}/engagement` — **owner-only** (403 for a non-owner, 404 for a missing post):
  reaction counts + comment count for the owning artist. This is the MEDIA-4 deliverable.

**Data model (design decision).** New `ArtistReaction` + `ArtistComment` tables (mirrors of
`Reaction`/`Comment`) that FK to `ArtistPost`. A foreign key targets exactly one table, and
`ArtistPost` is not `Post`, so engagement on artist posts needs its own tables. Chosen over adding a
second nullable FK to the existing `Reaction`/`Comment` (a polymorphic target), which would have
weakened the constraint guarding regular-post reactions and touched the busy T10–T13 social path.
Both reuse the shared `ReactionType` enum and rate-limit helper (ADR-0011, own action names).

## Source
- Spec reqs: **MEDIA-4**
- ADRs: [ADR-0007](../../../decisions/adr/0007-validation-and-data-integrity.md)

## Scope
### In Scope
- Aggregate reactions/comments per `ArtistPost`; expose owner-only. (Widened: also the write path so
  those counts are real — reactions/comments that target artist posts.)

### Out of Scope
- Storage/upload (T50/T51).
- View counting (deferred — no artist-post read path to count from yet; T51).
- Rendering on the artist page (`apps/web/src/pages/ArtistPage.tsx`) — frontend, T51's surface.

## Validation & authz (ADR-0007)
- **Authorization + ownership:** any logged-in user may react/comment; only the owning artist may
  read a post's engagement summary (403 otherwise).

## Current State (on `develop`)
- `ArtistPost` exists (T50). New `ArtistReaction`/`ArtistComment` tables added here (migration
  `3978f11ad4da`).

## Files Created/Modified
| File | Action | Purpose |
|------|--------|---------|
| `backend/app/models.py` | MODIFY | add `ArtistReaction` + `ArtistComment` tables |
| `backend/app/schemas.py` | MODIFY | add `ArtistEngagementOut`; reuse reaction/comment shapes |
| `backend/app/routers/artist.py` | MODIFY | add reactions/comments + owner-only engagement routes |
| `backend/alembic/versions/3978f11ad4da_*.py` | CREATE | migration for the two new tables |
| `backend/tests/test_artist_engagement.py` | CREATE | 13 tests |
| `backend/tests/conftest.py`, `test_models.py` | MODIFY | register the two new tables |

## Testing Checklist
- [x] engagement counts correct per post (reactions grouped by type + comment count)
- [x] only the owning artist can read their engagement (403 otherwise; 404 for a missing post)
- [x] reactions idempotent add / own-only remove; comments trimmed/validated + newest-first
- [x] login required on every route; full suite green (`uv run pytest` — 154 passed, 13 new)

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T50, T11, T12 → blocked_by 050, 011, 012)
- [x] Scope boundaries defined

## Deploy step (owner — Andrea)
Apply the migration to `brink-dev`: `cd backend && uv run alembic upgrade head` (creates
`ArtistReaction` + `ArtistComment`; reuses the existing `ReactionType` enum, so no `CREATE TYPE`).
Not auto-applied by CI — same manual-apply pattern as T39.

## Notes
Branch `feat/T52-artist-engagement`; one PR into `develop` (never `main`). View counting deferred
(best-effort, and depends on a read path that doesn't exist yet — T51). Frontend render is T51's job.
