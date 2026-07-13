# Brink — Implementation Tickets

One file per ticket. **Plain markdown — no tooling required** to read, review, or work them.

- **Backlog:** [`backlog/`](backlog/) — not yet done.
- **Completed:** [`completed/`](completed/) — done (T00–T02, T04–T08, **T09**, **T10–T13**, **T20**, **T22**, **T23**, **T37**, **T39**, **T50**, **T62**, T70–T74, T77, T78, **T90–T93**). The FastAPI/Render migration is complete; the legacy TS backend is removed. T70–T78 are the 2026-07-02 code-review remediation wave. **T10 (posts API) is the first social-API feature — its merge unblocks the frontend social UI and the rest of the backend social endpoints.** T90–T93 are the developer-tooling wave: the `get-me-started` session-warmup skill, the `docs-sync` CI gate that enforces "docs in the same PR," the `close-out` skill that runs the ticket close-out ritual **pre-merge** (folded into the feature PR, per T93), and the `close-session` end-of-session skill (final validation + branch cleanup + handoff).

## How these relate to the rest of the docs

`docs/decisions/` (the ADRs) is the **source of truth**. These tickets are *derived from* the ADRs and the spec — when an ADR changes, the tickets follow. Each ticket cites its requirement IDs (`AUTH-*`, `BE-*`, …) and the ADRs it implements.

This directory **supersedes** the old single-file `2026-06-22-brink-implementation-tickets.md`.

## Reading a ticket

Each file has YAML frontmatter + sections:

- **frontmatter** — `status`, `priority`, `complexity`, `category`, `owner`, `tags`, `blocked_by`, `blocks`. `owner` is the default reviewer/assignee by code area: **Andrea** (backend — `backend/`, auth, Spotify, DB), **Jonah** (analytics — `analytics/`), **Sebastian** (frontend — `apps/web/`).
- **Rationale / Summary** — why it exists, what it does.
- **Source** — requirement IDs + ADRs.
- **Scope (In / Out)** — explicit boundaries.
- **Validation & authz** — the ADR-0007 layers every API ticket must cover.
- **Current State** — what already exists on `develop`.
- **Files to Create/Modify** + **Testing / Readiness checklists**.

## Numbering

`NNN` = `epic-major . ticket-minor`, so the tens digit groups by system area (gaps are intentional slack to add tickets within an epic):

| Range | Epic |
|---|---|
| `00x` | Foundation + Auth |
| `01x` | Backend social API |
| `02x` | Spotify |
| `03x` | Analytics pipeline |
| `04x` | Frontend wiring |
| `05x` | Artist portal |
| `06x` | Cleanup + QA |
| `07x` | Review remediation (from the [2026-07-02 code review](../reviews/2026-07-02-code-review-t00-t08.md)) |
| `09x` | Developer tooling / automation |

## Dependency waves

Tickets in the same wave have no inter-dependencies and can run in parallel. A ticket starts once its `blocked_by` are merged.

| Wave | Tickets |
|---|---|
| **0 (ready)** | `003` `030` ~~`050`~~ ✅ |
| 1 | `021` `031` `040` `051` |
| 2 | `032` `034` `036` `041` `042` `043` `052` |
| 3 | `033` `038` `045` |
| 4 | `035` |
| 5 | `014` |
| 6 | `044` |
| 7 | `060` |
| 8 | `061` |

**Ready to start now** (all `blocked_by` merged, as of T13):
- `003` (Sebastian) · `030` (Jonah) — these never had blockers.
- **Newly unblocked by T50 (artist storage backend):** **`051` — artist upload UI (Sebastian)** and
  **`052` — per-post engagement (Andrea)** (`052`'s other blockers `011`/`012` are done).
- **Newly unblocked by T10:** **`040` — post composer + Spotify catalog search (Sebastian).** (`011`, `012` done.)
- **Newly unblocked by T13 (follow + feed):** the follow/feed UIs — `041` `043` (Sebastian) — once their own remaining blockers are merged.
- **`009` (server-side Spotify login) done** — the ADR-0013 Jinja shell (PR #60) merged and this landed on top; the Python frontend can now sign users in and gate `/feed`.

The wave numbers below are *dependency depth*, not live status — a ticket is startable as soon as its `blocked_by` are merged, which is what the "Ready to start now" list above reflects. Update that list whenever a wave of blockers merges.

Critical path: `039 → 034 → 033 → 035 → 014 → 044` (the analytics-to-profile spine).

### Review-remediation wave (2026-07-02) — `070`–`078`

A full code review of the T00–T08 surface ([findings report](../reviews/2026-07-02-code-review-t00-t08.md))
produced nine remediation tickets. Each ticket cites its finding IDs (H*/MB*/MF*/MI*/L*) from the
report, which is the traceability root.

| Done ✅ | Remaining |
|---|---|
| `070` `071` `072` `073` `074` `077` `078` | `075` · `076` (after 075) |

### Backend migration spine (TS/Vercel → FastAPI/Render) — ✅ complete

Per [ADR-0010](../../decisions/adr/0010-fastapi-render-backend.md), the backend moved from
TypeScript/Vercel to FastAPI/Python on Render. This ran as a sequential chain, now finished:

`004 → 005 → 006 → 007 → 008` (all done)

`004` scaffold · `005` SQLModel + Alembic · `006` auth/crypto port · `007` Render deploy + Vercel
cutover · `008` retire the TS backend + doc sync. The FastAPI backend is live on Render and the
legacy TS `api/` is removed. The social-API tickets (`010`–`014`, `050`, `052`) target the FastAPI
pattern (`backend/app/...`).

## Working a ticket

Per `CLAUDE.md`: branch off `develop` as `<type>/T<NN>-<slug>`, **one ticket = one PR into `develop`** (never `main`), TDD with a failing test first. The owner of the touched area (Andrea = backend, Sebastian = apps/web, Jonah = analytics) is the default reviewer.

> The `.tdd/` directory (if present) is an optional local tooling workspace for the maintainer and is gitignored — it is **not** the source of truth. These files are.
