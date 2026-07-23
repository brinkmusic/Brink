// WHAT THIS FILE IS
// A tiny fire-and-forget refresh that runs ONLY on your own profile (T100). On page load it asks
// the server to pull your latest Spotify plays right now (POST /api/me/plays/refresh), so your
// "recent listening" is up to the minute instead of waiting for the every-30-minutes cron. It is
// loaded from profile.html only when p.is_self is true, so it never runs when you're viewing
// someone else's profile.
//
// WHY fire-and-forget (no DOM update): keeping this dead simple. We don't touch the page after the
// call — the freshly ingested plays show up on the NEXT render (your next visit / refresh). Live-
// updating the listening section in place is a deliberate follow-up, out of scope for T100.
//
// WHY plain JavaScript (no framework/build step): ADR-0013 keeps the frontend buildless. The login
// session cookie is sent automatically because the request is same-origin, so the server knows whose
// plays to refresh — we never send an id (it can't be spoofed). A failure (offline, throttled 429,
// no linked Spotify) is harmless: we just swallow it and the cron path still fills history in.

fetch("/api/me/plays/refresh", { method: "POST" }).catch(() => {});
