---
status: Completed
priority: High
complexity: High
category: Feature
tags: [auth, supabase, spotify, crypto]
blocked_by: []
blocks: []
parent_ticket: null
owner: Andrea
---

# Feature: Supabase Auth + Spotify provider token capture (T02)

## Summary
Supabase Auth with Spotify provider; `api/_lib/auth.ts` (`requireUser`), `api/_lib/crypto.ts` (AES-256-GCM), `api/auth/capture-spotify.ts` (encrypted `SpotifyToken`), `api/_lib/spotify.ts` (`getValidAccessToken`). `requireUser` auto-creates a `public.User` with a derived unique handle.

## Source
- Spec reqs: AUTH-1, AUTH-2, AUTH-4, AUTH-5

## Outcome
Completed ✅. Spotify login creates a `User` + stores the encrypted refresh token; auth verified end-to-end. ([ADR-0005](../../../decisions/adr/0005-identity.md).)

## Notes
Stub recorded for dependency traceability; full history in git + `docs/plans/`.
