---
status: Completed
priority: Low
complexity: Low
category: Tooling
tags: [tooling, docs, developer-experience, claude-skill]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Tooling: "Get me started" session warm-up skill (T90)

## Rationale
Brink's contract says *"keep docs in sync in the same PR — stale docs are a bug"* and closes each
ticket with a fixed check-list (move `backlog/ → completed/`, flip requirement traceability,
update the `CLAUDE.md` status line, prune the wave table). Both are easy to forget when picking a
session back up, and drift is only caught by whoever happens to notice — the T78 doc-drift sweep
existed precisely because a wave of PRs left the docs contradicting the code. A repeatable
start-of-session routine turns that from ad-hoc vigilance into a habit the whole team shares.

## Summary
Add a committed Claude Code skill, **`get-me-started`**, that runs a start-of-session briefing:
pull in what changed, survey open PRs and new branches, **audit each incoming change for
documentation sync** (code moved but `CLAUDE.md` / an ADR / a ticket / `requirements.md` didn't),
and report where the project stands and what's next. It flags drift; it does not fix it.

## Source
- Project norms: `CLAUDE.md` → "Keep docs in sync in the same PR", "ADRs are append-only",
  team close-out pattern.
- Spec reqs: **INFRA-2** (docs consistency).
- Prior art: [T78](../completed/078-doc-drift-sweep.md) (one-off version of the same audit,
  done by hand).

## Scope
### In Scope
- `.claude/skills/get-me-started/SKILL.md` — the skill: four passes (pull → look at code →
  doc-sync audit → where-am-I / what's-next), the code-change → required-doc mapping table, the
  ownership/blast-radius map, and the "don't false-flag the deferred close-out pattern" carve-out.
- `docs/plans/tickets/README.md` — add the `09x` "Developer tooling / automation" row to the
  Numbering table (this ticket opens that epic range).

### Out of Scope
- Any automation that *edits* docs or auto-closes tickets — the skill flags, a human fixes.
- A pre-commit/CI hook that blocks doc drift — a possible later ticket; this is a read-only
  briefing, not an enforcement gate.

## Acceptance
- The skill is discoverable in-session and, run against the current repo, produces: pulled-state,
  open-PR summaries, a per-PR doc-sync verdict, the next unblocked ticket, and any reviews/CI
  waiting on the developer.
- It correctly treats a deferred close-out (T10/T30 precedent) as on-pattern, not a violation.
- Committed to the repo (shared with the team), not a personal `~/.claude` skill.

## Notes
Validated on first use against PRs #60 (ADR-0013 Python frontend — flagged: `CLAUDE.md`
contradicted, ADR-0010 status not annotated, ticket re-pointing claimed but not in the diff) and
#61 (T30 analytics — on-pattern deferred close-out). Findings drove the review feedback on #60.
