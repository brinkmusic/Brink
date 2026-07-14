---
name: get-me-started
description: Session warm-up for the Brink repo — pull in what changed, survey open PRs and new branches, audit each incoming change for documentation sync (code changed but CLAUDE.md / ADRs / tickets didn't), and brief the developer on where things stand and what's next. Use at the start of a working session or whenever someone says "get me started", "catch me up", "what's new", "where am I", "warm me up", "pull in changes", "what's ready to review", or asks whether incoming PRs kept their docs in sync.
---

# Get Me Started (Brink session warm-up)

WHAT THIS SKILL IS: a start-of-session briefing for anyone (human or agent) picking up work on
Brink. It pulls in what changed, looks at the code that's landed or is up for review, checks
whether the **documentation was kept in sync with that code**, and tells you plainly where the
project stands and what to do next. It exists because Brink's hard rule is *"keep docs in sync in
the same PR"* — this skill is the routine that actually catches drift before it piles up.

Run it, produce the briefing, then stop and let the developer choose what to tackle. Don't start
changing code or docs as part of the warm-up — flag, don't fix (unless asked).

## The four passes

Work through these in order. Each is a few shell/`gh` calls plus judgement. Keep the final output
short and scannable — this is a briefing, not a report.

### Pass 1 — Pull in what changed

- `git fetch origin` (note any *new* remote branches it prints — those are usually fresh PRs).
- Compare local `develop` to `origin/develop`. If behind, say so and offer to fast-forward
  (don't do it silently — the developer may have local work).
- `gh pr list --state open` — this is the incoming-work queue. Note number, title, author, branch.

### Pass 2 — Look at the code

For each open PR (and any unmerged branch that matters):

- `gh pr view <n> --json title,body,files` to get the changed-file list and the author's own
  summary / assumptions / test plan.
- Read the *actual* diff for anything non-trivial (`git show origin/<branch>:<path>` reads a file
  from a branch without checking it out — handy on Windows to avoid switching working trees).
- Form a one-line take on **what the change really does** and its **blast radius** (see the
  ownership map below).

### Pass 3 — Did the docs keep up? (the core of this skill)

This is the whole point. Brink's contract (`CLAUDE.md` → "Keep docs in sync in the same PR")
maps *kinds of change* to *docs that must move with them*. For each PR, check the change type and
confirm the matching doc was touched **in the same PR's file list**:

| If the PR changes… | The same PR must also… |
|---|---|
| Architecture / a past decision | Add a new ADR in `docs/decisions/adr/`, **and** set the superseded/amended ADR's `Status:` line to point forward to it (ADRs are append-only — never rewrite them). |
| Commands, env vars, conventions, dev workflow, or project status | Update `CLAUDE.md` (the Commands / Environment / Deployment-topology / Status sections). |
| Feature scope, or a ticket's shape | Update `docs/plans/` — the ticket file in `docs/plans/tickets/` and the requirement→ticket traceability in `docs/plans/requirements.md`. |
| Behavior the requirements catalog tracks | Flip the relevant `AUTH-* / BE-* / SP-* / …` status in `docs/plans/requirements.md`. |

**How to check it well:**

- Diff the *shape* of the file list: does it contain only code paths, or code **plus** the doc
  paths the change type demands? A pure-code file list on an architecture or command change is the
  classic red flag.
- Read the ADR/PR body's *claims* and verify them against the file list. If the body says
  "tickets T40–T45 are re-pointed" but no `docs/plans/tickets/` file is in the diff, the claim
  isn't backed by a change — flag it.
- When an ADR says it "amends" or "supersedes" another, open the older ADR and confirm its
  `Status:` line was actually updated. "Amends" in the new ADR is not enough on its own.

**Expect close-out folded into the feature PR (T93).** Brink now closes a ticket *in the same PR
that implements it*: the feature PR should also move the ticket `backlog/ → completed/`, flip its
traceability rows, and update the `CLAUDE.md` status line (the `close-out` skill does this
pre-merge). So for a PR that finishes a ticket, a code diff with **no** matching ticket/requirements
move is now a **flag** (a missing close-out), not on-pattern — the reverse of the old post-merge
model. Two exceptions are still legitimate and should NOT be flagged: (1) a PR body that *explicitly*
says close-out is a deliberate deferred follow-up (allowed for very large PRs or ones owned by
someone not doing the bookkeeping — just note the pending follow-up), and (2) a PR that doesn't
finish a ticket (partial/scaffold work). Real drift is a finished ticket whose docs *silently* stay
in `backlog/` with the requirement rows unflipped and no stated reason.

Sort your findings by severity: **contradiction** (a doc now states the opposite of reality) >
**missing update** (a doc that should have moved didn't) > **pending follow-up** (deferred on
purpose, just track it).

### Pass 4 — Where am I / what's next

- Current branch and working-tree state (`git status`).
- **Next ticket:** read `docs/plans/tickets/README.md` for the dependency waves and the current
  status line in `CLAUDE.md`; name the next unblocked ticket and any that are gated.
- **CI / review state:** for open PRs, `gh pr checks <n>` — call out anything red or anything
  waiting on the developer's review (auth/crypto PRs are the highest-risk area, so a second review
  is encouraged where a reviewer is available — but it's not required and the owner may self-merge).
- **Stale branches:** local branches already merged or far behind `develop` that could be pruned.

## Ownership map (use it to judge blast radius and review routing)

- **Andrea** — backend / API / auth / DB (`backend/`). Auth & crypto files
  (`backend/app/deps.py`, `backend/app/security/*`, anything touching tokens / `TOKEN_ENC_KEY`)
  are highest-risk — a second review is encouraged but not required; the owner may self-merge.
- **Sebastian** — frontend (`apps/web/`, and — per ADR-0013 — the Jinja/HTMX page layer that
  lives in `backend/app/templates|static|routers/pages.py`).
- **Jonah** — analytics (`analytics/`).

If a PR lands code in someone else's owned area (e.g. frontend templates inside `backend/`), note
it — it changes who the natural reviewer is.

## Output shape

End with a compact briefing, roughly:

1. **Pulled:** what fetch/compare found (behind/ahead, new branches).
2. **Open PRs:** one line each — what it does + your take.
3. **Doc-sync:** per PR, ✅ in sync · ⚠️ missing update · ⛔ contradiction · ⏳ deferred follow-up,
   each with the specific doc that's affected.
4. **You are here:** branch, next unblocked ticket, anything gated.
5. **Needs you:** reviews waiting, red CI, branches to prune.

Then stop and ask what they want to tackle. Flag, don't fix.
