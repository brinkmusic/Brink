---
status: Backlog
priority: Medium
complexity: Low
category: Feature
tags: [backend, ts, inference, compatibility]
blocked_by: [033]
blocks: [014]
parent_ticket: null
---

# Feature: Compatibility on read (cosine) (T35)

## Rationale
Compatibility between two listeners is a headline social-analytics feature. Under ADR-0003 it's the cosine similarity of their taste vectors, computed **on read in TS** — fresh, and cheap at our scale (~200 users).

## Summary
A TS helper that returns the 0..1 cosine similarity between a viewer's and another user's taste vectors, reusing the T33 inference core.

## Source
- Spec reqs: **AN-5**
- ADRs: [ADR-0003](../../../decisions/adr/0003-analytics-runtime.md) (cosine on read) · [ADR-0004](../../../decisions/adr/0004-analytics-data-strategy.md)

## ⚠ Changed from draft
The draft's T35 was a **Python** `compat.py` writing a pairwise `Compatibility` table. Under option A there is no table (T39) — compatibility is computed **on demand in TS** between the viewer and the profile being viewed.

## Scope
### In Scope
- `api/_lib/inference/compatibility.ts` — `cosine(vectorA, vectorB)` over taste vectors from T33; clamp to 0..1; symmetric.
- Used by the profile API (T14) for viewer-vs-profile compatibility.

### Out of Scope
- Any pairwise precompute / table (dropped). The donut UI is T44.

## Validation & authz (ADR-0007)
- **Correctness:** both vectors must come from the same T33 builder (same feature space) before cosine.
- **Business rule:** if either user has no taste vector yet (no plays / no artifact), return null compatibility, not an error.

## Current State (on `develop`)
- T33 inference core (`tasteVector.ts`) available; no `Compatibility` table (T39).
- No `compatibility.ts` yet.

## Files to Create/Modify
| File | Action | Purpose |
|------|--------|---------|
| `api/_lib/inference/compatibility.ts` | CREATE | cosine over two taste vectors |
| `api/__tests__/compatibility.test.ts` | CREATE | tests |

## Testing Checklist
- [ ] identical vectors → 1.0
- [ ] orthogonal vectors → 0.0
- [ ] symmetric: compat(A,B) == compat(B,A)
- [ ] a user with no taste vector → null, not a crash

## Readiness Checklist
- [x] Summary is specific and actionable
- [x] Files to Create/Modify is populated
- [x] Testing Checklist has items
- [x] Dependencies identified (T33 → blocked_by 033)
- [x] Scope boundaries defined

## Notes
Branch off `develop` as `feat/T35-compatibility`; one PR back into `develop` (never `main`). Owner: Andrea (TS).
