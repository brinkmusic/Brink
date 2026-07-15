<!-- One ticket = one PR. See CLAUDE.md "Hard rules". -->

## Ticket

<!-- e.g. T10 — Posts API. Link the ticket section in docs/plans/...-implementation-tickets.md -->

## What changed

<!-- 1-3 sentences. What does this PR do and why? -->

## Checklist

- [ ] Branch is named `<type>/<ticket-id>-<slug>` and targets `develop` (never pushed to `develop`/`main` directly).
- [ ] Scope matches exactly one ticket — no extra features, abstractions, or error handling.
- [ ] The ticket's acceptance criteria are met.
- [ ] Reused existing helpers instead of duplicating logic where one already existed.
- [ ] Tests added/updated and the backend suite passes (`cd backend && uv run pytest`).
- [ ] No secrets committed — `.env` files stay git-ignored.
- [ ] Docs updated in this PR: ADR for any decision/deviation (`docs/decisions/adr/`), spec/ticket
      changes (`docs/plans/`), and `CLAUDE.md` if commands/env/conventions/status changed.

## Assumptions & risks

<!-- What did you assume or guess? What could break, or what should the reviewer watch?
     If the ticket was unclear, say what you decided and why (or that you asked first). -->

## Notes for reviewer

<!-- Anything else: tradeoffs, follow-ups you deliberately left out. -->

<!-- After merge: delete the branch. -->

