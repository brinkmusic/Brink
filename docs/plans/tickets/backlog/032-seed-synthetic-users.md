---
status: Backlog
priority: High
complexity: Medium
category: Feature
tags: [analytics, python, data, synthetic]
blocked_by: [030, 031]
blocks: []
parent_ticket: null
owner: Jonah
---

# Feature: Synthetic user seeding — genre-coherent personas (T32)

## Rationale
The live user base is tiny, so clusters wouldn't separate and compatibility scores would be meaningless. Seeding ~100–200 synthetic listeners gives the models real population. The `User.isSynthetic` flag already exists for exactly this.

## Summary
Seed ~100–200 `User(isSynthetic=true)` as **genre-coherent personas**, each with a `Play` history sampled from Kaggle tracks matching that persona's 1–3 genres / audio profile.

## Source
- Spec reqs: **DATA-2**, **DATA-3**, ADR-0004 **C3**
- ADRs: [ADR-0004](../../../decisions/adr/0004-analytics-data-strategy.md) C3 (genre-coherent personas; disclosed as demo data)

## ⚠ Changed from draft
The draft said "varied taste profiles." **ADR-0004 C3 is more specific:** build each synthetic user as a **genre-coherent persona** (e.g. "mellow indie," "high-energy mainstream") from 1–3 genres/audio-profiles sampled from real Kaggle tracks. Personas — not random sampling — are what make clusters actually separate and compatibility meaningful on screen. Disclosed as demo data in the final report.

## Scope
### In Scope
- `analytics/seed_users.py` — create ~100–200 `User(isSynthetic=true)`; assign each a persona (1–3 genres / audio profile); generate plausible `Play` rows sampled from Kaggle tracks fitting that persona.
- Personas span the feature space so clusters separate.

### Out of Scope
- Clustering / taste vectors (T33/T34); compatibility (T35).

## Validation & authz (ADR-0007)
- **Integrity:** every seeded user flagged `isSynthetic=true`; `Play` rows respect the `@@unique([userId, playedAt])` dedup; FKs valid.
- **Business rule:** synthetic data is disclosed (demo data) — recorded for the report, not hidden.

## Current State (on `develop`)
- `backend/app/models.py`: `User.isSynthetic` (default false); `Play` with a unique constraint on `(userId, playedAt)`.
- `analytics/db.py` (T30) + Kaggle-joined `Track` features (T31) available.
- No `seed_users.py` yet.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `analytics/seed_users.py` | CREATE | persona-based synthetic user + play seeding |
| `analytics/tests/test_seed_users.py` | CREATE | seeding tests |

## Testing Checklist
- [ ] seeds N users, all flagged `isSynthetic=true`
- [ ] each user's plays are genre-coherent (sampled within their persona)
- [ ] personas vary across users (distinct regions of the feature space)
- [ ] `Play` rows respect the dedup constraint

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T30, T31 → blocked_by 030, 031)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T32-seed-users`; one PR back into `develop` (never `main`). Owner: Jonah (analytics).
