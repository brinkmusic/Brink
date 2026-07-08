---
status: Backlog
priority: Low
complexity: Low
category: Tooling
tags: [tooling, docs, developer-experience, claude-skill]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Tooling: Ticket close-out skill (T92)

## Rationale
Every finished Brink ticket ends with the same fixed ritual — move `backlog/ → completed/`, flip
`status` and the matching `requirements.md` traceability rows, sync the `CLAUDE.md` status line,
refresh the wave table + completed list in `tickets/README.md`, delete the branch, write the
handoff. It's multi-step, easy to half-do, and (like the doc-sync it depends on) only "caught"
when someone notices a stale doc later. [T90](090-session-warmup-skill.md) gave the team a
committed *start-of-session* skill; this is its **end-of-work bookend**, encoding the close-out so
any agent runs it consistently.

## Summary
Add a committed Claude Code skill, **`close-out`**, that walks the ticket close-out steps against
real repo state and produces the bookkeeping PR — a *guided checklist*, not an auto-runner
(several steps need judgement: which requirement rows to flip, one-PR vs bundled, deferred
close-out).

## Source
- Project norms: `CLAUDE.md` → close-out pattern, "keep docs in sync in the same PR",
  hard rule #2 (delete branch after merge).
- Spec reqs: **INFRA-2** (docs consistency).
- Prior art: [T90](090-session-warmup-skill.md) (the get-me-started bookend),
  [T91](091-doc-sync-enforcement.md) (the docs-sync gate this close-out PR must satisfy),
  [T78](../completed/078-doc-drift-sweep.md) (what stale close-outs cause).

## Scope
### In Scope
- `.claude/skills/close-out/SKILL.md` — the skill: the "is it closeable" pre-check, the seven
  close-out steps, the judgement-call section (one-PR-vs-bundled, deferred close-out, don't
  invent requirement flips), and the output shape (what merged + what it unblocked).

### Out of Scope
- Any automation that closes tickets *without a human confirming* the merge and the requirement
  flips — the skill guides and verifies; it does not blindly move files or mark requirements ✅.
- A CI/bot that auto-detects merged-but-not-closed tickets — a possible later ticket; this is a
  human-invoked helper, not a gate. (Close-out is a "do the ritual right" task, not a "block a
  bad merge" task — the latter is what T91's CI gate is for.)

## Acceptance
- Invoked with a merged ticket, the skill produces a correct close-out: ticket moved + status
  flipped, only the genuinely-satisfied requirement rows changed, CLAUDE.md/README synced, branch
  deleted, a docs-only close-out PR opened, and a handoff written.
- It correctly handles the bundled-pair exception and the deferred-close-out pattern rather than
  forcing one rigid path.
- Committed to the repo (team-shared), not a personal `~/.claude` skill.

## Notes
Validated implicitly against the T90/T91 close-out done by hand this session (bundled pair, no
requirement flips, CLAUDE.md status + README synced) — the skill encodes exactly that flow.
