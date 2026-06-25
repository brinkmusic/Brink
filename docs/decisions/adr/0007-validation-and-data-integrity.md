# ADR-0007: Validation, authorization & data integrity (defense in depth)

**Status:** Accepted
**Date:** 2026-06-25

## Context

The API is the boundary between untrusted clients (the SPA, plus handle users with no Spotify) and the database. A single validation layer is fragile: if the one check is missed or bypassed, bad data reaches the DB. We want invalid states to be **structurally impossible**, not merely discouraged — and the proposal (§6) already requires server-side validation and peer review. This decision sets validation as a layered concern, not a per-endpoint afterthought.

## Decision

Validate at **every layer** data passes through. Each layer is independently sufficient to reject bad input; together they're defense in depth.

1. **Input / schema** — every request body and query param is parsed against a schema (zod) at the top of the handler, before any logic. Failures return `400` through the existing `{data} | {error}` helper (`api/_lib/respond.ts`). No handler trusts raw `req.body`.

2. **Business rules** — domain invariants enforced server-side regardless of what the client sends: one reaction per `(user, post, type)`, non-empty comment body, handle uniqueness, post `source ∈ {MANUAL, SPOTIFY}`, uploads ≤ 10 MB JPEG/PNG. These live in the handler / service layer.

3. **Authorization** — every private or mutating route passes through `requireUser` (Supabase JWT verified server-side via `getUser()`, `api/_lib/auth.ts`). Beyond authentication, routes check **ownership**: only a post's author edits/deletes it; only the owning artist manages their `ArtistPost`. Authentication ≠ authorization — both are required.

4. **Data integrity** — the last line is the schema itself: Prisma/Postgres constraints make violations impossible even if app checks are skipped — `@@unique([postId, userId, type])`, unique `handle`, unique `supabaseUserId`, foreign keys, `NOT NULL`, enums. The DB is the source of truth for what *can* exist.

5. **Rate limiting / abuse** — per-user (and per-IP for unauthenticated) caps on write and expensive endpoints (post create, catalog search, sign-upload). Because Vercel functions are stateless, in-memory counters don't work; limits use a **shared store**.

## Alternatives considered

- **Single-layer validation (schema only, or DB only)** — one missed/bypassed check lets bad data through; no ownership story.
- **Client-side validation as the gate** — trivially bypassed; the server must assume hostile input.
- **No rate limiting** — fine functionally, but leaves write/search/upload endpoints open to abuse and skews the k6 load test.

## Consequences

- Some rules are enforced in two places (e.g. reaction dedup as both a business rule and a DB `@@unique`). That redundancy is intentional — it's the "in depth" — not a violation of single-source-of-truth, because the **DB constraint is authoritative** and the app check just fails faster with a friendlier error.
- **Rate-limit store is an open sub-decision:** default to a **Postgres-backed counter** (keeps Supabase consolidation, [ADR-0002](0002-api-and-persistence.md)) rather than adding Upstash/Redis — acceptable at demo scale (k6 at 5 concurrent users). Revisit if throughput needs it.
- Validation is a cross-cutting requirement on **every** API ticket, not a standalone one — each endpoint ticket must cover schema + rules + authz; integrity lives in the Prisma schema; rate limiting is a shared middleware.
