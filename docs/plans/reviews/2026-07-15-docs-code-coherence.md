# Docs ↔ code coherence review (2026-07-15)

A read-only sweep for places where the documentation and the code disagree. **Findings only —
no fixes applied.** Scope: `CLAUDE.md`, `README.md`, `docs/decisions/adr/`, `docs/plans/`
(requirements + tickets), the FastAPI routers + shared modules under `backend/app/`, the CI/infra
config (`.github/workflows/`, `render.yaml`), and `.env.example`.

Each finding is classified:

- **EASY** — docs-only or a trivial one-line code fix; safe to bundle into a chore PR (`docs:` /
  `chore:`) with the `no-docs` escape hatch where it's code-only.
- **TICKET** — needs real work or a decision (owner sign-off, a code path to build, an ADR).

**Headline:** the endpoint/status claims are largely accurate — every endpoint CLAUDE.md's status
line claims to exist really does exist in `backend/app/routers/`, and every completed ticket is in
`completed/` with `status: Completed`. The drift is concentrated in **post-T60 leftovers** (docs and
config that still assume a `web` CI job / frontend build step / `apps/web/` tree), one **user-facing
copy bug ADR-0014 already flagged and left unfixed**, and the long-standing **`analytics/` doesn't
exist yet** gap.

---

## High — could mislead a teammate or break onboarding

### C1 — `apps/web/` was NOT fully deleted; a tracked leftover survives T60 · **EASY**
- **Where:** `apps/web/tsconfig.tsbuildinfo` (git-tracked); ADR-0013 update note (line 97) +
  `docs/plans/tickets/README.md:6` + `docs/plans/completed/060-retire-spa.md`.
- **Docs say:** "**T60 deleted `apps/web/` entirely**" (ADR-0013), "the repo now has no TypeScript,"
  "`apps/web/` deleted."
- **Reality:** `git ls-files apps/web/` returns exactly one tracked file — `apps/web/tsconfig.tsbuildinfo`
  (a TypeScript build artifact). It is **not** gitignored, so it's still in the repo. (The rest of
  `apps/web/` on Andrea's disk — `node_modules/`, `.env`, `tsconfig.tsbuildinfo`'s siblings — is
  untracked/gitignored local cruft and safe, but the tracked `.tsbuildinfo` contradicts the
  "deleted entirely / no TypeScript" claim.)
- **Fix:** `git rm apps/web/tsconfig.tsbuildinfo`. Docs then become true.
- **Severity:** low functional risk, but directly falsifies a headline T60 claim ("no TypeScript in
  the repo").

### C2 — CLAUDE.md hard rule #4 claims CI runs a "frontend build" that no longer exists · **EASY**
- **Where:** `CLAUDE.md:68` (hard rule #4): "CI (`.github/workflows/ci.yml`) runs the backend tests
  (`uv run pytest`), **the frontend build**, and a secret scan on every PR."
- **Reality:** `ci.yml` has two jobs — `api` (pytest) and `secrets` (gitleaks). The `web` build job
  was **removed in T60** (ci.yml:31-34 documents this). There is no frontend build step in CI.
  README.md:90-91 already states it correctly ("backend tests and a secret scan").
- **Fix:** drop "the frontend build," from CLAUDE.md line 68.
- **Severity:** a contributor reading the contract will expect a CI signal that doesn't exist.

### C3 — CLAUDE.md branch-protection line lists a removed `web` required check · **EASY**
- **Where:** `CLAUDE.md:221`: "checks `api/web/secrets/docs-sync` green."
- **Reality:** the `web` check was retired with the SPA (T60 / ADR-0013 line 98 explicitly removes
  "the `web` CI build job … and its branch-protection required check"). Current checks are `api`,
  `secrets`, `docs-sync` (job names in `ci.yml` + `docs-sync.yml`).
- **Fix:** change `api/web/secrets/docs-sync` → `api/secrets/docs-sync`.
- **Severity:** documents branch protection as still gating on a check that can never report.

### C4 — `close-session` skill still validates a "frontend build/lint" that doesn't exist · **EASY**
- **Where:** `CLAUDE.md:144` (close-session skill description) and
  `.claude/skills/close-session/SKILL.md:3` + `:63` ("runs the full backend suite + **frontend
  build/lint**", "frontend build/lint ✅/❌ — the gate result").
- **Reality:** there is no frontend build/lint step — the Jinja/HTMX frontend is server-rendered with
  no build (CLAUDE.md's own Commands section says so: "no separate build/lint step"). The
  close-session gate can't run one.
- **Fix:** reword to "backend suite (frontend is server-rendered — no build/lint step)" in all three
  spots.
- **Severity:** the end-of-session gate promises a validation it can't perform; a session could be
  signed off believing a nonexistent check ran.

### C5 — `home.html` landing copy contradicts ADR-0014 (feed is manual-only) · **TICKET**
- **Where:** `backend/app/templates/home.html:35`: "**No manual posting. Your real listening shows
  up live**, and friends react…"
- **Docs say:** ADR-0014 (Accepted, 2026-07-15) decided the feed is **manually shared songs only**;
  there is **no** `Play`→`Post` auto-posting. The ADR's own Consequences section (line 56-59) flags
  this exact line: "The landing page copy is now inaccurate and must be reworded … Flagged here as a
  follow-up."
- **Reality:** the copy still promises the *rejected* auto-posting behaviour to every visitor.
- **Fix:** reword to describe manual sharing + a profile listening summary. Small
  `home.html` change (Sebastian's area) — but it's a product-copy decision the ADR already made, so
  it's a tracked follow-up, hence TICKET (a `no-docs`-free content edit the ADR expects).
- **Severity:** user-facing; the landing page actively describes a feature the product deliberately
  does *not* have.

### C6 — `analytics/` directory is documented as existing but does not · **EASY (docs)**
- **Where:** `CLAUDE.md` Layout ("`analytics/` — Python pipeline (`uv`-managed). Created in T30."),
  CLAUDE.md Commands ("Analytics: `cd analytics && uv run pytest`"), README.md:56 + :76.
- **Reality:** no `analytics/` directory exists (`analytics/**` matches nothing; T30 is in
  `backlog/`). Running the documented `cd analytics && uv run pytest` fails. This was already
  flagged as **L10** in the 2026-07-02 review and is still unfixed.
- **Fix:** mark the analytics commands/layout as "(added in T30 — not yet created)" until T30 lands,
  or drop the standalone command line. Keep the note that it *will* live there.
- **Severity:** an onboarding contributor who runs the documented test command hits a missing-dir
  error.

---

## Medium — stale but lower blast radius

### C7 — `render.yaml` Blueprint still points `branch: develop`, contradicting "Render deploys from `main`" · **TICKET**
- **Where:** `render.yaml:14` — `branch: develop  # switch to \`main\` for production once the release PR lands`.
- **Docs say:** CLAUDE.md deployment topology + README.md §4 state definitively that **Render deploys
  production from `main`**; T62 even "corrected the CLAUDE.md line that wrongly said Render deploys
  from `develop`."
- **Reality:** the committed Blueprint still declares `develop`. The live service was created via the
  dashboard (this file is only a recreation record, per its own header), so production is fine
  *today* — but recreating the service from this Blueprint would wire it to `develop`, silently
  re-introducing the exact bug the first release (#79) hit. TICKET because flipping it is a real
  infra decision (should the Blueprint match prod, or stay a dev convenience?) with owner sign-off.
- **Severity:** latent — safe now, a trap if the Blueprint is ever applied.

### C8 — `render.yaml` env-var list omits `CRON_SECRET` · **EASY**
- **Where:** `render.yaml` envVars (lines 26-41) list 7 secrets + `PYTHON_VERSION`; `CRON_SECRET` is
  absent.
- **Docs say:** CLAUDE.md deployment section lists `CRON_SECRET` among the Render env vars, and the
  snapshot endpoint (`routers/snapshot.py`, authed by `X-Cron-Secret`) requires it — CLAUDE.md's own
  "Deploy step for Andrea" says "set `CRON_SECRET` on Render."
- **Reality:** the Blueprint wouldn't provision the `CRON_SECRET` slot. Minor drift (it's set by hand
  in the dashboard anyway), but the versioned "source of truth for settings" is incomplete.
- **Fix:** add `- key: CRON_SECRET` / `sync: false` to `render.yaml`.
- **Severity:** low; cosmetic Blueprint completeness.

### C9 — `responses.py` header still says "so the **React** frontend always knows what to expect" · **EASY**
- **Where:** `backend/app/responses.py:2`.
- **Reality:** there is no React frontend (retired T60). The envelope now serves the Jinja frontend +
  API clients. The neighbouring `api/_lib/respond.ts` reference is correctly historical; only "React"
  is wrong.
- **Fix:** "so the frontend always knows what to expect" (drop "React").
- **Severity:** trivial.

### C10 — `auth.py` header calls the capture-spotify endpoint "Kept until the SPA is retired in T60" · **EASY**
- **Where:** `backend/app/routers/auth.py:7` (also the scopes comment at :33 "before T60").
- **Reality:** T60 is **done** (SPA retired), yet `POST /api/auth/capture-spotify` still exists
  (auth.py:201) and is fully wired. So the comment's premise ("kept *until* T60") is now false — the
  endpoint outlived the retirement. Either it's genuinely dead code that T60 should have removed, or
  it's intentionally retained and the comment is stale. This is a judgement call, but a one-line
  comment fix at minimum; if the endpoint is dead it's a small cleanup.
- **Fix:** update the comment to state why the endpoint is retained post-T60 (or open a tiny cleanup
  to remove it if it's dead — no server-rendered caller now posts to it).
- **Severity:** low; a stale "will be removed" note that a reader will trust.

---

## Low / notes (not clear-cut disagreements — recorded for completeness)

### C11 — ADR-0003 (Accepted) describes analytics inference "in the TS API," which no longer exists · **note / TICKET-adjacent**
- **Where:** `docs/decisions/adr/0003-analytics-runtime.md` (Decision §2 "Inference = on-demand, in
  the TS API"; §Consequences "Inference math is reimplemented in TS"; "Ticket ripples … T37 becomes
  a TS aggregation endpoint").
- **Situation:** ADR-0003 is **Accepted and unsuperseded**. The *analytics runtime split* it decides
  (batch train in Python / infer on read / aggregate live) is still the plan and is faithfully
  reflected by `app/stats.py` (which does live on-read aggregation). But the ADR names the API layer
  "**TS**," and the whole app is now Python/FastAPI (ADR-0010) — so the language in this accepted ADR
  no longer matches reality. It *also* references "T37 becomes a TS aggregation endpoint," but T37
  was renumbered to Alembic schema reflection.
- **Why only a note:** ADRs are append-only history and the *decision* still holds; the analytics
  inference code isn't built yet (T14/T33/T35 backlog), so no code contradicts it — only the stack
  wording is stale. Per the append-only rule the clean fix is a **short amendment note** on ADR-0003
  (like ADR-0013's "Update — 2026-07-15" block) saying "inference now lands in the FastAPI/Python
  API, not TS (ADR-0010/0013)," rather than editing the body. TICKET-adjacent because it's an ADR
  edit, not a code change.
- **Severity:** low today; will become confusing when T14/T33/T35 are picked up and the ticket author
  reads "reimplement in TS."

### C12 — requirements.md uses "on-read TS" / "live TS" phrasing for an all-Python app · **EASY (docs)**
- **Where:** `docs/plans/requirements.md` rows AN-4/AN-5 ("on-read TS"), the AN-2/4/5/7/9 note ("are
  computed **on read in TS**"), and line 113 in Superseded ("computed **on read in TS**").
- **Reality:** these describe future analytics inference (still backlog) but say "TS." Since the app
  is Python, the accurate word is "on read in the API" / "on-read Python." Inherited from the
  ADR-0003 wording (C11).
- **Fix:** s/TS/the API (Python)/ in those rows when ADR-0003 gets its amendment note, so the two
  stay consistent.
- **Severity:** low; cosmetic, but compounds C11's confusion.

---

## Verified accurate (no action)

- **Every endpoint CLAUDE.md's status line claims exists, exists.** Cross-checked `@router` decorators
  in all 13 router files against the status-line prose: `POST/GET /api/posts`, `POST/DELETE
  /api/posts/{id}/reactions`, `POST/GET /api/posts/{id}/comments`, `POST/DELETE /api/follow/{userId}`,
  `GET /api/feed`, `GET /api/search`, `GET /api/me/now-playing`, `POST /api/snapshot`,
  `POST /api/artist/sign-upload`, `POST /api/artist/posts`, artist reactions/comments/engagement,
  `GET /auth/login|callback|logout`, and the pages `/`, `/feed`, `/u/{handle}`, `/artist` — all present.
- **Ticket folder placement + frontmatter are consistent.** Every ticket the README/CLAUDE mark done
  is in `completed/` with `status: Completed`; every backlog ticket is in `backlog/` with
  `status: Backlog`. No misfiled tickets, no stale frontmatter status. README wave table (strikethroughs
  for done tickets) matches the folders.
- **requirements.md traceability matches code** for the shipped features (BE-3..7, BE-9, SP-2/3/4/5,
  UI-1..5, MEDIA-1..4, AUTH-1/2/5) — each ✅ row has a real router/endpoint behind it; the ◧ partials
  (AN-7, UI-6, UI-10) are honestly annotated as partial with the deferred half named.
- **`.env.example` matches what the code reads.** `config.py`'s `Settings` reads exactly
  `DATABASE_URL`, `DIRECT_URL`, `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `TOKEN_ENC_KEY`,
  `SPOTIFY_CLIENT_ID/SECRET`, `CRON_SECRET` — all present in `.env.example`, none extra. No
  `os.getenv`/`os.environ` reads anywhere in `backend/` (all config flows through `Settings`).
  `SUPABASE_JWT_SECRET` is correctly *absent* and documented as intentionally so (fixes old MI1).
- **Backend module headers correctly describe the old TS backend as removed** (past tense): `deps.py`,
  `spotify.py`, `stats.py`, `crypto.py`, `db.py`, `models.py`, `pages.py` all say "old … removed in
  T08" or "ported from." Only `responses.py` (C9) and `auth.py` (C10) carry stale present-tense refs.
- **ADR-0010** (Vercel/SPA references) is correctly marked "frontend decision later amended by
  ADR-0013" and its Vercel wording is appropriate historical content for an amended-but-accepted ADR
  — not a finding.
- **Snapshot cadence** (~2h) and the `X-Cron-Secret` contract match between CLAUDE.md, `snapshot.yml`,
  and `routers/snapshot.py`.

---

## Suggested bundling

- **One `chore:` PR (docs + trivial code):** C1 (`git rm` the leftover), C2, C3, C4, C6, C8, C9, C12.
  All docs-only or one-line; the code-touching ones (C1, C9) need a doc touch too so they clear
  docs-sync naturally.
- **ADR amendment note:** C11 (+ its C12 requirements.md wording) — a small append to ADR-0003.
- **Needs a decision / owner (TICKET):** C5 (landing copy — ADR-0014 already sanctioned the reword),
  C7 (render.yaml deploy branch), and the C10 judgement (retain-and-recomment vs remove the
  capture-spotify endpoint).
