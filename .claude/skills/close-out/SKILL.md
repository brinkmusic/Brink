---
name: close-out
description: Close out a finished Brink ticket by folding its bookkeeping into the SAME PR that implements it — the pre-merge counterpart to close-session. Walks the fixed close-out ritual: move the ticket backlog→completed, flip its status and the matching requirements.md traceability rows, sync the CLAUDE.md status line, and refresh the tickets/README wave table + completed list — all committed onto the feature branch so they ride the feature PR (no separate follow-up PR). Use when someone says "close out T<NN>", "close the ticket", "wrap up this ticket", "mark it done", or once a ticket's code is complete and green and you're about to open/finalize its PR.
---

# Close Out (Brink ticket close-out — pre-merge)

WHAT THIS SKILL IS: the guided ritual that marks a Brink ticket *done* by syncing the source-of-
truth docs (tickets, requirement traceability, status) **in the same PR that implements the
ticket**. Brink keeps those docs as the source of truth, so a finished ticket isn't done until
they're synced — otherwise the next person (or agent) reads a stale map. Running this **before
merge** means the PR that lands is already fully closed out: no second "docs follow-up" PR, and
`develop` never claims a merged feature is still open.

**This is a guided checklist, not an auto-runner.** Several steps need judgement — which
requirement rows to flip, whether the CLAUDE.md status wording is right. Do each step against the
*actual* repo state, confirm before moving files, and stop to ask if something doesn't match.

## When to run it

Run close-out as the **last step of the feature work**, once:

- the ticket's code + tests are complete and the **full suite is green** locally, and
- you're on the ticket's feature branch (`feat/T<NN>-...`), about to open its PR or with the PR
  already open (the close-out edits become additional commits on that same branch).

Do **not** wait for the PR to merge — that was the old post-merge model, now replaced (see T93).
The close-out is a docs change that belongs *with* the code, exactly as the `docs-sync` CI gate
expects.

## The close-out steps

Work the checklist on the feature branch, then commit the doc changes alongside (or right after)
the code:

1. **Move the ticket to completed.** `git mv docs/plans/tickets/backlog/<nnn>-<slug>.md
   docs/plans/tickets/completed/<nnn>-<slug>.md`. Using `git mv` (not delete+create) keeps the
   file history.

2. **Flip the ticket status.** In the moved file's frontmatter, `status: Backlog → Completed`.
   Check off any remaining Testing/Readiness boxes that the work satisfied, and add a short
   **Outcome** / as-built note (endpoints, files, precedents, deliberate scope calls).

3. **Flip requirement traceability.** Open `docs/plans/requirements.md`. For each requirement the
   ticket's **Source** section cites (`AUTH-* / BE-* / SP-* / AN-* / UI-* / MEDIA-* / INFRA-* /
   DATA-*`), set its status to ✅ **only if the ticket actually satisfied it** — a ticket can
   partially touch a requirement that's still owned/finished elsewhere, so verify, don't
   auto-flip. Add the `†` superseded marker where a row now points at replaced code. If the ticket
   is pure tooling/governance with no catalog requirement, there's nothing to flip — say so.

4. **Sync the CLAUDE.md status line.** Update the `## Watch-outs` **Status:** paragraph: add the
   ticket to the done list and note what shipped (endpoints, files, precedents) in one or two
   plain-English clauses, matching the existing voice. Move the **"Next feature work"** pointer to
   whatever this unblocks. If the ticket changed commands, env, layout, or deployment, update those
   sections too (the same doc-sync rule the CI gate enforces).

5. **Refresh `tickets/README.md`.** Add the ticket to the **Completed** list line. If it was in a
   **dependency wave**, remove it and update the "Ready to start now" list for anything its merge
   just unblocked (a ticket becomes startable once all its `blocked_by` are merged). Keep the wave
   table honest.

Then commit these onto the feature branch (`docs(T<NN>): close out — move ticket, flip
traceability, sync status`) and push, so they're part of the feature PR. Branch **deletion** and
the session **handoff** are NOT part of ticket close-out anymore — they belong to `close-session`,
which you run when you're done working (branch deletion also happens automatically if you merge
with `gh pr merge --delete-branch`).

## Judgement calls (don't skip these)

- **Default: fold close-out into the feature PR.** One ticket = one PR, and that PR is now
  self-closing. Don't open a separate docs PR just to flip "done" markers.
- **Deferred close-out is the exception, not the default.** It's still legitimate to close a ticket
  in a *follow-up* PR when there's a real reason — e.g. a very large feature PR, or one owned by
  someone who isn't doing the bookkeeping. If you defer, **say so in the PR body** and make sure
  the follow-up actually happens. A silent missing close-out is drift, and `get-me-started` will
  flag it.
- **Don't invent a requirement flip.** If you're unsure whether a requirement is fully satisfied,
  leave it and flag it for the owner rather than marking ✅ prematurely.

## Output shape

End with a short confirmation: ticket moved + status flipped, which requirement rows changed (or
"none — tooling ticket"), which docs synced, and — the useful part — **what this ticket's merge
will unblock** (the next ready tickets). Note that branch cleanup + handoff are `close-session`'s
job. Then hand back to the developer to finalize/merge the PR.
