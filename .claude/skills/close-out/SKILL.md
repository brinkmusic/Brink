---
name: close-out
description: Close out a finished Brink ticket once its PR has merged — the end-of-work bookend to get-me-started. Walks the fixed close-out ritual: move the ticket backlog→completed, flip its status and the matching requirements.md traceability rows, sync the CLAUDE.md status line, refresh the tickets/README wave table + completed list, delete the merged branch, and write the handoff. Use when someone says "close out T<NN>", "close the ticket", "wrap up this ticket", "the PR merged, finish it off", "mark it done", or after a ticket's PR merges and the bookkeeping needs doing.
---

# Close Out (Brink ticket close-out)

WHAT THIS SKILL IS: the guided end-of-work ritual for a Brink ticket whose PR has merged. Brink
keeps its tickets, requirement traceability, and status docs as the source of truth, so a finished
ticket isn't *done* until those are synced — otherwise the next person (or agent) reads a stale
map. This skill walks the fixed steps so nothing is missed, and pairs with `get-me-started` (which
opens a session) as the bookend that closes a unit of work.

**This is a guided checklist, not an auto-runner.** Several steps need judgement — which
requirement rows to flip, whether close-out should be its own PR or bundled, whether it's a
deferred follow-up. Do each step against the *actual* repo state, confirm before destructive
actions (branch deletion, moving files), and stop to ask if something doesn't match.

## Before you start — confirm it's actually closeable

- **The PR is merged**, not just approved. Check: `gh pr view <n> --json state,mergedAt`. If it's
  not merged, stop — there's nothing to close out yet.
- You know the **ticket id** and its file in `docs/plans/tickets/backlog/`.
- `develop` is synced locally (`git checkout develop && git pull`) so you branch from the merged
  state, not a stale one.

## The close-out steps

Close-out is itself a docs change, so — like any change — it goes on a branch and through a PR into
`develop` (branch protection now blocks direct pushes). Name it `docs/close-t<NN>` (or
`docs/close-t<NN>-t<MM>` for a coupled pair; see the bundling note). Then work the checklist:

1. **Move the ticket to completed.** `git mv docs/plans/tickets/backlog/<nnn>-<slug>.md
   docs/plans/tickets/completed/<nnn>-<slug>.md`. Using `git mv` (not delete+create) keeps the
   file history.

2. **Flip the ticket status.** In the moved file's frontmatter, `status: Backlog → Completed`.

3. **Flip requirement traceability.** Open `docs/plans/requirements.md`. For each requirement the
   ticket's **Source** section cites (`AUTH-* / BE-* / SP-* / AN-* / UI-* / MEDIA-* / INFRA-* /
   DATA-*`), set its status to ✅ **only if the ticket actually satisfied it** — a ticket can
   partially touch a requirement that's still owned/finished elsewhere, so verify, don't
   auto-flip. Add the `†` superseded marker where a row now points at replaced code. If the
   ticket is pure tooling/governance with no catalog requirement, there's nothing to flip — say so.

4. **Sync the CLAUDE.md status line.** Update the `## Watch-outs` **Status:** paragraph: add the
   ticket to the done list and note what shipped (endpoints, files, precedents) in one or two
   plain-English clauses, matching the existing voice. If the ticket changed commands, env, layout,
   or deployment, update those sections too (the same doc-sync rule the CI gate enforces).

5. **Refresh `tickets/README.md`.** Add the ticket to the **Completed** list line. If it was in a
   **dependency wave**, remove it and update the "Ready to start now" list for anything its merge
   just unblocked (a ticket becomes startable once all its `blocked_by` are merged). Keep the wave
   table honest.

6. **Delete the merged branch** (hard rule #2). If you merged via `gh pr merge --delete-branch`
   it's already gone; otherwise `git push origin --delete <feature-branch>` and prune the local
   copy. Confirm before deleting.

7. **Open the close-out PR**, let its checks go green (it's docs-only, so `docs-sync` passes
   trivially — it's the "docs moved" case), and merge it. Then **write the handoff** to
   `.remember/remember.md` recording what closed and what's now unblocked.

## Judgement calls (don't skip these)

- **One PR or bundled?** Default: **one ticket = one PR** (hard rule). Exception: a coupled set
  finished together that all edit the *same* lines (e.g. the CLAUDE.md status paragraph + README
  completed list) — separate PRs would just conflict. Then bundle them in one `docs/close-...` PR
  and **state the deliberate exception** in the PR body, as done for the review-remediation wave
  and the T90/T91 tooling pair.
- **Deferred close-out is legitimate.** Brink sometimes lands a feature PR and closes its ticket
  in a *follow-up* PR on purpose (the T10/T30 precedent) — especially when the feature PR is large
  or owned by someone else. If the team chose to defer, that's the pattern working, not an
  omission. Just make sure the follow-up actually happens.
- **Don't invent a requirement flip.** If you're unsure whether a requirement is fully satisfied,
  leave it and flag it for the owner rather than marking ✅ prematurely.

## Output shape

End with a short confirmation: ticket moved + status flipped, which requirement rows changed (or
"none — tooling ticket"), which docs synced, branch deleted, close-out PR link, and — the useful
part — **what this merge just unblocked** (the next ready tickets). Then hand back to the developer.
