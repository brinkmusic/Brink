# ADR-0005: Identity via Supabase Auth

**Status:** Accepted — *magic-link/OTP mechanism for handle accounts superseded by
[ADR-0015](0015-email-password-auth.md) (email + password); Spotify OAuth and the
one-account/identity-linking model below remain in force.*
**Date:** 2026-06-22
**First captured as:** spec decision-log row D

## Context

Brink needs managed login and sessions, must honor the in-scope feature of manual posting without a Spotify account, and must capture + refresh each user's Spotify tokens so the snapshot pipeline (see [ADR-0004](0004-analytics-data-strategy.md), C1) can pull plays when the user isn't present. The starting point used browser-side Spotify PKCE only — no account system and no server-side tokens.

## Decision

Use **Supabase Auth** (part of the platform choice, [ADR-0002](0002-api-and-persistence.md)): Spotify OAuth via Supabase's Spotify provider, plus email magic-link / OTP for handle accounts. Spotify tokens are captured from the provider (`provider_refresh_token`) and persisted **server-side, encrypted (AES-256-GCM, `TOKEN_ENC_KEY`)**; we own token refresh (Supabase does not refresh the provider token).

**One account per person — handle and Spotify are identities on a single Supabase auth user.** A user may start with an email/handle account and **link Spotify later**, keeping one account. Linking uses Supabase identity-linking (`linkIdentity` on the logged-in account, plus same-email auto-link) so the Spotify provider attaches to the *existing* identity rather than creating a second one. Our `public.User` is keyed by `supabaseUserId`, so there is never a duplicate row to merge — the link flow updates the existing user (sets `spotifyId`, runs the same token-capture path as a fresh Spotify login).

Sessions use **Supabase's session defaults** (no custom session layer).

## Alternatives considered

- **Build our own auth** — login, sessions, and email delivery to operate and secure ourselves; unnecessary given Supabase is already the platform.
- **Resend for auth emails** — a separate vendor; Supabase Auth's built-in magic-link/OTP removes the need.
- **Browser-side Spotify PKCE only (the starting point)** — no handle accounts, and tokens never reach the server, so the unattended snapshot job can't run.
- **Separate handle and Spotify accounts (no merge)** — simpler, but a user who joined by email then connected Spotify would end up with two identities and split data. Rejected in favor of identity-linking into one account.

## Consequences

- Handle accounts via email OTP satisfy "manual posting without Spotify" with no custom auth.
- We own Spotify token refresh server-side, which is what makes the C1 snapshot job possible.
- Encrypted server-side token storage (AES-256-GCM) becomes a security obligation.
- A handle user can link Spotify later and keep **one** account (no duplicate `User`); the link flow reuses the existing token-capture path.
- **Edge case to enforce:** a Spotify-first login and a later same-email OTP must resolve to the **same** identity (Supabase email-based identity linking), not two accounts — needs a test.
