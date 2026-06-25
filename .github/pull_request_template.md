<!-- One ticket = one PR. See CLAUDE.md "Hard rules". -->

## Ticket

<!-- e.g. T10 — Posts API. Link the ticket section in docs/plans/...-implementation-tickets.md -->

## What changed

<!-- 1-3 sentences. What does this PR do and why? -->

## Checklist

- [ ] Branch is named `feat/<ticket-id>-<slug>` and targets `main` (never pushed to `main` directly).
- [ ] Scope matches exactly one ticket — no extra features, abstractions, or error handling.
- [ ] Tests added/updated and `npm test` passes (Python: `uv run pytest`).
- [ ] Frontend builds (`cd apps/web && npm run build`) and lints (`npm run lint`) if `apps/web/` changed.
- [ ] No secrets committed — `.env` files stay git-ignored.
- [ ] Docs updated in this PR: ADR for any decision/deviation (`docs/decisions/adr/`), spec/ticket
      changes (`docs/plans/`), and `CLAUDE.md` if commands/env/conventions/status changed.

## Assumptions & risks

<!-- What did you assume or guess? What could break, or what should the reviewer watch?
     If the ticket was unclear, say what you decided and why (or that you asked first). -->

## Notes for reviewer

<!-- Anything else: tradeoffs, follow-ups you deliberately left out. -->
