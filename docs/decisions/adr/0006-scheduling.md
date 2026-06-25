# ADR-0006: Scheduling — GitHub Actions cron times both jobs

**Status:** Accepted
**Date:** 2026-06-22
**First captured as:** spec decision-log row E

## Context

Two recurring jobs must run on a schedule with no extra hosting cost: the Python analytics pipeline (see [ADR-0003](0003-analytics-runtime.md)) and the Spotify recently-played snapshots (see [ADR-0004](0004-analytics-data-strategy.md), C1). These are different concerns with different runtimes.

## Decision

**GitHub Actions cron times both jobs** — the team is on Vercel **Hobby**, whose Cron is capped at once per day, too coarse for snapshots:

- **Analytics pipeline** — GitHub Actions runs the Python job **nightly**, plus `workflow_dispatch` for an on-demand run before a demo ([ADR-0003](0003-analytics-runtime.md)).
- **Spotify snapshots** — GitHub Actions runs **every ~2h** and triggers the snapshot by calling the Vercel function endpoint (`api/jobs/snapshot.ts`) with `CRON_SECRET`. The snapshot logic stays a Vercel serverless function; only its *trigger* is external ([ADR-0004](0004-analytics-data-strategy.md), C1).

## Alternatives considered

- **Vercel Cron for snapshots** — the natural home (the snapshot is already a Vercel function), but Hobby caps Cron at once-per-day — too coarse for a 2h cadence.
- **Upgrade to Vercel Pro** — unlocks arbitrary Vercel Cron, but a paid upgrade for something GitHub Actions does for free.
- **A dedicated scheduling host (e.g. a worker dyno)** — extra hosting and cost for something the free tiers already cover.

## Consequences

- No extra hosting or cost, and stays on Vercel **Hobby** (no Pro upgrade needed).
- **One scheduler (GitHub Actions)** times both jobs; the snapshot still *executes* on Vercel. Monitoring is mostly in one place (Actions run history). The two runtimes (Python pipeline in Actions; snapshot function on Vercel) are unchanged — only the snapshot's timer moved.
- The snapshot endpoint must **authenticate the trigger** (`CRON_SECRET`), since it's now reachable as a normal URL rather than a Vercel-internal cron.
- Cadence locked: pipeline **nightly** (+ manual dispatch), snapshots **~2h**.
- **Ticket ripple (for the redo):** T21 changes from a `vercel.json` `crons` entry to a **GitHub Actions workflow that curls the snapshot endpoint**; `vercel.json` crons are not used.
