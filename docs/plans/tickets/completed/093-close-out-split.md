---
status: Completed
priority: Medium
complexity: Low
category: Chore
tags: [tooling, skills, workflow, docs]
blocked_by: [092]
blocks: []
parent_ticket: null
owner: Andrea
---

# Chore: Split close-out into pre-merge ticket close-out + a session close-out skill (T93)

## Rationale
The original `close-out` skill (T92) ran **after** a feature PR merged, as its own follow-up PR
(the T10/T30 "deferred close-out" pattern). In practice that means every finished ticket needs a
*second* PR just to flip its "done" markers — extra overhead and a window where `develop` says a
merged feature is still open. We'd rather close the ticket **in the same PR that implements it**,
so the PR that merges is already fully done. That leaves the *session-level* wrap-up (final test
run, branch cleanup, handoff) without a home, so we split it into its own skill.

## Summary
Two changes to the committed `.claude/skills/`:
1. **`close-out` becomes pre-merge.** It now runs as the last step of the feature work — its doc
   edits (move ticket backlog→completed, flip status + requirement traceability, sync CLAUDE.md
   status, refresh the tickets README) are **committed onto the feature branch**, so they ride the
   same PR as the code. Branch deletion and handoff are removed from it.
2. **New `close-session` skill** — the bookend to `get-me-started`: final validation (run the full
   backend suite + frontend build, confirm the tree is clean and pushed, PRs green), clean up
   already-merged branches, and write the `.remember` handoff.

## Source
- ADRs: none (developer tooling / workflow; no architectural decision).
- Supersedes the post-merge close-out workflow introduced in **T92** (`092-close-out-skill.md`).

## Scope
### In Scope
- Rewrite `.claude/skills/close-out/SKILL.md` to the pre-merge model (drop branch-delete + handoff).
- Add `.claude/skills/close-session/SKILL.md` (validate + clean up + handoff).
- Update the `get-me-started` doc-sync audit so a feature PR is now *expected* to carry its own
  close-out; a silent missing close-out becomes a flag (deferral is the explicit exception, not the
  default).
- Sync `CLAUDE.md` status + `docs/plans/tickets/README.md` (close-out description + Completed list).

### Out of Scope
- Any change to `get-me-started`'s four-pass structure beyond the deferred-pattern paragraph.
- Automating either skill (both stay guided checklists, not auto-runners).

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `.claude/skills/close-out/SKILL.md` | MODIFY | pre-merge ticket close-out (folded into the feature PR) |
| `.claude/skills/close-session/SKILL.md` | CREATE | session close-out: validate + clean up + handoff |
| `.claude/skills/get-me-started/SKILL.md` | MODIFY | flip the deferred-close-out guidance |
| `CLAUDE.md` | MODIFY | status line: record T93 + the new skill |
| `docs/plans/tickets/README.md` | MODIFY | close-out description + Completed list |

## Outcome
Completed ✅. Close-out now runs pre-merge (this ticket dogfoods it — created and closed in one
PR); `close-session` handles final validation + branch cleanup + handoff. First use of the
pre-merge close-out pattern.

## Notes
This ticket was created and closed out in a single PR, demonstrating the new pattern. Deferred
close-out (a separate follow-up PR) is still permitted as a deliberate exception — e.g. a very
large feature PR, or one owned by someone who isn't doing the bookkeeping — but it must be stated
in the PR body, and it's no longer the default.
