---
status: Completed
priority: High
complexity: Simple
category: Tech-Debt
tags: [cleanup, infra, secrets]
blocked_by: []
blocks: []
parent_ticket: null
---

# Feature: Secret hygiene & repo cleanup (T00)

## Summary
Ensure `.env*` git-ignored, remove dead legacy `lib/api.ts` (`MOCK=true`), confirm no secrets tracked.

## Source
- Spec reqs: INFRA-5, BE-2 (partial), DATA-4 (partial)

## Outcome
Completed (foundation). Dead file removed, build green, secrets not tracked. Recorded as done in `CLAUDE.md` status.

## Notes
Stub recorded for dependency traceability; full history in git + `docs/plans/`.
