# Brink — Implementation Tickets

One file per ticket. **Plain markdown — no tooling required** to read, review, or work them.

- **Backlog:** [`backlog/`](backlog/) — not yet done.
- **Completed:** [`completed/`](completed/) — done (T00–T02, T04–T08). The FastAPI/Render migration is complete; the legacy TS backend is removed.

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

## Dependency waves

Tickets in the same wave have no inter-dependencies and can run in parallel. A ticket starts once its `blocked_by` are merged.

| Wave | Tickets |
|---|---|
| **0 (ready)** | `003` `010`\* `020` `030` `039` `050` |
| 1 | `011` `012` `013` `021` `031` `040` `051` |
| 2 | `032` `034` `036` `041` `042` `043` `052` |
| 3 | `033` `038` `045` |
| 4 | `035` |
| 5 | `014` |
| 6 | `044` |
| 7 | `060` |
| 8 | `061` |

Critical path: `039 → 034 → 033 → 035 → 014 → 044` (the analytics-to-profile spine).

\* `010` is additionally blocked by `070` (error-envelope handlers) — see the remediation wave below.

### Review-remediation wave (2026-07-02) — `070`–`078`

A full code review of the T00–T08 surface ([findings report](../reviews/2026-07-02-code-review-t00-t08.md))
produced nine remediation tickets. All are independent (parallel-safe) except: `070`/`071` → `073`
(same test files), `075` → `076` (same `AuthContext.tsx`), and **`070` → `010`** (the social API
must land on envelope-complete error handling). Each ticket cites its finding IDs (H*/MB*/MF*/MI*/L*)
from the report, which is the traceability root.

| Ready now | Then |
|---|---|
| `070` `071` `072` `074` `075` `077` `078` | `073` (after 070+071) · `076` (after 075) · `010` (after 070) |

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
