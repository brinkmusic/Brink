# ADR-0008: No artist-upload content moderation (out of scope)

**Status:** Accepted
**Date:** 2026-06-25

## Context

The artist BTS portal lets artists upload images + text ([`MEDIA`] layer). "Moderation" here means deciding whether an uploaded image is *allowed* — automated NSFW/abuse scanning, or a manual approval queue — as opposed to technical validation (type/size), which we do regardless.

## Decision

**No content moderation.** Uploads are accepted after technical validation only (JPEG/PNG ≤ 10 MB — see [ADR-0007](0007-validation-and-data-integrity.md)). No NSFW scanning, no approval queue.

## Why this is safe here

The uploaders are **the team posing as mock artists** in a closed, seeded demo — there is no public/open upload surface. The proposal never scoped moderation. Automated scanning (a third-party API + cost) or a manual review queue (admin UI + workflow) would be production concerns added for no demo benefit.

## Consequences

- One less subsystem to build before the deadline.
- **Documented scope cut** — name it in the final report as a deliberate exclusion (closed demo, team-controlled uploads), so it reads as a decision, not an oversight.
- If Brink ever opened uploads to real external artists, moderation would become mandatory — a new ADR superseding this one.
