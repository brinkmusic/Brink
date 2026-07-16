---
status: Completed
priority: High
complexity: Low
category: Chore
tags: [infra, render, ci, performance]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Chore: Stop the Render cold-start "warm up" screen (T64)

## Rationale
Owner report (2026-07-15): "when I open the app it brings me to Render where there is a long
warm up, then it brings me to the app." Root cause: `render.yaml` runs the service on Render's
**free plan**, which spins the instance down after ~15 idle minutes; the next request triggers a
~50-second cold boot behind Render's "waking up" interstitial. Bad for the course demo — a
grader's first impression is a loading wall.

## Summary
A GitHub Actions cron (`.github/workflows/keepalive.yml`, same pattern as `snapshot.yml`) pings
`GET /api/health` every 10 minutes so the service never idles long enough to sleep. Free: one
always-warm service ≈ 720 instance-hours/month, inside the free tier's 750.

## Options considered
1. **Paid Starter plan (~$7/mo)** — no spin-down ever, zero code. The bulletproof fix; needs
   owner budget sign-off, so not done unilaterally.
2. **GitHub Actions keep-alive ping** ← chosen — free, versioned in-repo, snapshot.yml
   precedent. Caveat: GitHub cron can drift 3–15 min, so a rare cold start remains possible.
3. **External pinger (UptimeRobot etc.)** — more punctual than GH cron but adds an external
   account/config outside the repo. Fallback if drift proves annoying in practice.

## Source
- Spec reqs: none directly (demo quality / INFRA hygiene). ADR-0006 precedent for GH-Actions cron.

## Scope
### In Scope
- `keepalive.yml` (10-min cron + manual dispatch, hardcoded public health URL, `--max-time` cap).
- Docs sync: CLAUDE.md deployment section + status line, tickets README.

### Out of Scope
- Plan upgrade (owner decision #1 above). Any app code change — `/api/health` already exists.

## Validation & authz (ADR-0007)
N/A — unauthenticated GET to the public health endpoint; no secrets involved.

## Current State (on `develop`)
- `render.yaml`: `plan: free`. `/api/health` live and cheap (returns `db: true`).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `.github/workflows/keepalive.yml` | CREATE | the 10-minute ping |
| `CLAUDE.md`, `docs/plans/tickets/README.md` | MODIFY | doc sync |

## Testing Checklist
- [x] workflow YAML valid (mirrors snapshot.yml structure)
- [ ] **post-release:** manual `workflow_dispatch` run from `main` returns green (owner step —
  `schedule` only fires from the default branch, so this activates at the next release)
- [ ] after a quiet evening, opening the site skips the warm-up screen

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (none)
- [x] Scope boundaries defined

## Outcome
Shipped as written. **Activates only after the next `develop → main` release** (GitHub runs
scheduled workflows from the default branch — the exact lesson of the #79 snapshot release).
If cold starts still bite after that, the escalation path is option 1 (Starter plan) or
option 3 (UptimeRobot at 5-min).
