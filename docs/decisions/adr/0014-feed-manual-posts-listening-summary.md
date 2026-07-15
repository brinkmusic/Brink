# ADR-0014: The feed is manually shared songs only; listening history surfaces as a profile summary (no auto-posting)

**Status:** Accepted
**Date:** 2026-07-15
**Relates to:** [ADR-0013](0013-python-frontend.md) (the Jinja/HTMX frontend these screens live in);
requirements `UI-2`, `SP-1`, `SP-2`, `AN-7` in [requirements.md](../../plans/requirements.md).

## Context

Two parts of the design quietly implied that a user's Spotify listening would post itself to the
feed automatically:

1. The data model's `PostSource` enum has a `SPOTIFY` value commented *"it came in automatically
   from their Spotify activity"* (`backend/app/models.py`).
2. Requirement **UI-2** says the feed shows *"manual **+ Spotify** cards"*, and **BE-3** lets
   `POST /api/posts` accept `source = MANUAL | SPOTIFY`.

But nothing was ever built — or specified — to actually produce those Spotify-sourced posts. The
scheduled snapshot (**SP-2 / T21**) pulls each user's recently-played tracks and lands them in
`silver.Play`, the **analytics** data lake, and stops there. The only thing that writes a `Post` is
the manual composer (**T40**), which always sends `source = MANUAL`. So the captured listening
history and the social feed are two disconnected halves: **no requirement or ticket bridges a
`Play` into a feed `Post`.**

When we looked at closing that gap, the owner's product judgement was that auto-posting every listen
is the wrong behaviour: a person plays dozens of tracks a day, so piping all of them into the feed
would bury the songs people *intentionally* share under a wall of passive noise.

## Decision

- **The feed is manually shared songs only.** The T40 composer — the "Search a song to share…" box
  at the top of `/feed` — is the single way a post is created. There is **no dedicated post page**;
  the composer stays inline on the feed.
- **A user's listening history is surfaced as a compact summary on their profile, not as feed
  posts.** "Latest listens", top tracks, and a "now playing" indicator live on the profile, built
  from data we already capture. This is the existing plan: **T44** (profile UI) + **T14** (the stats
  API behind it, requirement AN-7) + **T20** (now-playing, backend already done).
- **No `Play` → `Post` bridge will be built.** `PostSource.SPOTIFY` stays in the schema as a
  currently-unused option — retained deliberately so a future "auto-share" feature would need no
  migration — but nothing writes it for now.

## Alternatives considered

- **Auto-post every recently-played track to the feed.** This is what the schema/UI-2 hinted at.
  Rejected: it floods the feed and drowns intentional shares. The snapshot also runs in ~2-hour
  batches, so posts would arrive in clumps rather than live.
- **Auto-post a curated subset** (e.g. one "top track of the day" per user). Rejected *for now*: it
  needs ranking/dedup logic and product rules we don't have time to get right before the
  2026-07-30 deadline. It can be revisited after launch — the retained `SPOTIFY` enum value leaves
  the door open.

## Consequences

- **UI-2 is amended** in the same PR as this ADR: the feed is manual-only, so the *"+ Spotify
  cards"* clause is dropped from its acceptance text.
- **The landing page copy is now inaccurate and must be reworded.** `home.html` currently promises
  *"No manual posting. Your real listening shows up live"* — that describes the rejected behaviour.
  It should be changed to describe manual sharing plus a listening summary on your profile. Flagged
  here as a follow-up (a small `backend/app/templates/home.html` change, Sebastian's area).
- **The captured listening data is not wasted.** It powers the profile summary (T44/T14) and the
  analytics page (T45) — it simply doesn't feed the social timeline.
- **No new "auto-post" ticket is created.** The previously-missing `Play` → `Post` bridge is
  intentionally left unbuilt; this ADR is the record of *why*, so it isn't rediscovered as a bug
  later.
