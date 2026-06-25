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
- [ ] Any architecture decision or deviation from the proposal is recorded as an ADR in `docs/decisions/adr/`.

## Notes for reviewer

<!-- Anything the reviewer should know: tradeoffs, follow-ups, things you're unsure about. -->
