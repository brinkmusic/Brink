# ADR-0011: Rate limiting — Postgres-backed store with a swappable seam (Redis in production)

**Status:** Accepted
**Date:** 2026-07-03

## Context

[ADR-0007](0007-validation-and-data-integrity.md) §5 requires per-user caps on write and
expensive endpoints (post create, catalog search, sign-upload) so one client can't flood the API,
and notes that stateless serverless functions can't use in-memory counters — the limit needs a
**shared store**. ADR-0007's consequences already picked a direction: *default to a Postgres-backed
counter rather than adding Upstash/Redis, acceptable at demo scale, revisit if throughput needs it.*

T10 (`POST /api/posts`) is the first write endpoint, so it's where the rate-limit mechanism is
actually built. This ADR records the concrete implementation choice and — importantly — how we'd
change it later, so the decision reads as deliberate rather than as a shortcut.

## Decision

Rate limiting is enforced through a single helper (`backend/app/rate_limit.py`) backed by a generic
Postgres table (`RateLimitHit`). Every limited action records one row `(subject, action, createdAt)`;
the helper counts rows for that `(subject, action)` inside a time window and rejects with `429` once
the cap is reached. Endpoints call the helper — they never touch the table or counting logic
directly.

Two properties are deliberate:

1. **Generic, not post-specific.** The table and helper key on an arbitrary `action` string
   (`"post_create"`, later `"catalog_search"`, `"sign_upload"`), so future write endpoints reuse the
   same helper with a different `action` and cap — no new machinery per endpoint.
2. **A single swappable seam.** All storage/counting lives inside `rate_limit.py` behind one
   function signature. Nothing outside that module knows the limit is Postgres-backed.

## Production would use Redis (why we're not, here)

In a real, high-traffic deployment this belongs in an in-memory store — **Redis** (e.g. Upstash),
with a token-bucket or sliding-window algorithm — because the check runs on every request, must
answer in well under a millisecond, holds only throwaway short-lived counts, and must be shared
across many server instances. Postgres is the wrong tool at that scale (a disk-backed round-trip per
request; counter rows piling up in the primary datastore).

We deliberately do **not** use Redis for Brink because:

- **No extra infrastructure.** [ADR-0002](0002-api-and-persistence.md) commits to consolidating on
  the one Supabase Postgres we already run; adding Redis means another service, another account,
  more secrets to manage, and one more thing that can fail during a demo.
- **Demo scale.** The plan's load test is 5 concurrent users. The throughput that justifies Redis
  simply doesn't exist here, so a Postgres counter is comfortably sufficient.

**Migration path:** swapping to Redis is a one-file change — reimplement `rate_limit.py`'s helper
against a Redis client (and drop the `RateLimitHit` table). No endpoint or test that calls the
helper needs to change. That is the whole point of keeping the seam narrow.

## Consequences

- One new additive table (`RateLimitHit`) + an index on `(subject, action, createdAt)`; delivered as
  an Alembic migration. Additive and reversible.
- Rows accumulate over time. At demo scale this is negligible; a periodic prune (or a follow-up
  ticket) would handle it if the app ran long-term — noted, not built now.
- **Documented scope decision:** name Redis as the production choice in the final report, with this
  ADR as the rationale, so the Postgres approach reads as a scale-appropriate decision rather than an
  oversight.
- If Brink ever needed real throughput, a new ADR supersedes this one and points the seam at Redis.
