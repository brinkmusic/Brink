---
name: close-session
description: Close out a working session on the Brink repo — the end-of-session bookend to get-me-started. Runs the final-validation gate (full backend test suite + frontend build/lint, working tree clean and pushed, open PRs' CI green), cleans up already-merged branches, and writes the .remember handoff so the next session starts clean. Use at the end of a working session or when someone says "close out the session", "wrap up for the day", "I'm done", "sign off", "final validation", "am I safe to stop", or "write the handoff".
---

# Close Session (Brink session close-out)

WHAT THIS SKILL IS: the end-of-session ritual that answers *"am I safe to stop?"*. It's the
bookend to `get-me-started` (which opens a session): where that pulls in state and briefs you, this
one **validates** the work is sound, **cleans up** what's finished, and **records a handoff** so
the next session — you or a teammate — picks up from a truthful, clean starting point.

Distinct from `close-out`: `close-out` marks a single *ticket* done (its doc bookkeeping, folded
into the feature PR **before** merge). `close-session` is about the *session* as a whole — it runs
after your tickets are closed out, validates the repo end-to-end, and hands off. Run `close-out`
per ticket; run `close-session` once, when you're done working.

**This is a guided checklist, not an auto-runner.** It runs real checks and reports, but it does
**not** silently fix, commit, or force anything. Surface problems and confirm before any
destructive step (branch deletion). If validation fails, say so plainly — a failing gate is the
point, not something to paper over.

## The four passes

### Pass 1 — Final validation (the gate)

Run the same checks CI will, so nothing merges on a red suite:

- **Backend tests:** `cd backend && uv run pytest`. Report pass/fail with the count. A failure here
  is a stop — do not proceed to cleanup/handoff as if the work is done.
- **Frontend:** the frontend is server-rendered Jinja/HTMX inside the FastAPI app (the React/Vite SPA
  was retired in T60), so it's covered by the backend `pytest` run above (`tests/test_pages.py`).
  There is no separate `npm build`/`lint` step.
- Note anything skipped and why. This pass is a report, not a fix; if it's red, the session's real
  state is "work in progress," and the handoff must say that.

### Pass 2 — Working tree clean and pushed

- `git status` — is everything committed? **Uncommitted changes are surfaced, never auto-committed**
  — tell the developer what's dirty and let them decide.
- Is the current branch pushed and up to date with its remote (`git status -sb`, `git log
  origin/<branch>..HEAD`)? Unpushed commits mean the work isn't safe yet — flag it.

### Pass 3 — Clean up merged branches

- `git fetch --prune`, then find local branches already merged into `develop`
  (`git branch --merged develop`) and any whose PR has merged.
- Delete the merged ones (local, and remote if still present) so the branch list stays honest —
  hard rule #2 (delete a branch after its PR merges). **Confirm before deleting**, and never delete
  `develop`, `main`, or a branch with unmerged/unpushed work.

### Pass 4 — Write the handoff

- Write `.remember/remember.md` capturing: what state the repo is in, which PRs are open and their
  CI status, what was closed out this session, and the single most useful "next step" for whoever
  picks up. (The `remember` skill can do this — use it, or write the file directly in the same
  shape.) This is what the next `get-me-started` reads.

## Output shape

End with a compact sign-off:

1. **Validation:** backend tests ✅/❌ (count), frontend build/lint ✅/❌ — the gate result.
2. **Tree:** clean + pushed, or exactly what's dirty/unpushed.
3. **Branches:** what was pruned (or nothing to prune).
4. **Handoff:** written to `.remember/remember.md` — one line on the headline state + next step.

If the gate is green, tree clean, and handoff written, say plainly it's safe to stop. If not, lead
with what's blocking a clean stop.
