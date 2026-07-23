// WHAT THIS FILE IS
// The browser code behind the "Become an artist" button on your own profile (T55). Clicking it
// tells the server to flip YOUR account to an artist account (POST /api/me/become-artist), then
// reloads the page so the artist studio + upload nav and the "Artist posts" section appear. If the
// call fails, the button re-enables and says so, so it never silently does nothing.
//
// WHY plain JavaScript (no framework/build step): ADR-0013 keeps the frontend buildless. The login
// session cookie is sent automatically because the request is same-origin, so the server knows which
// account to upgrade — we never send an id (it can't be spoofed).

async function becomeArtist(btn) {
  // Becoming an artist is a ONE-WAY action (T55) — there's no in-app way back to a listener
  // account — and the button sits on your profile where a stray tap is easy, so confirm first.
  // window.confirm returns false when the user cancels; we bail without touching the API.
  const ok = window.confirm(
    "Are you sure you want to create an artist profile?\n\nThis unlocks the artist studio and cannot be undone.",
  );
  if (!ok) return;

  const status = document.getElementById("become-artist-status");
  btn.disabled = true;
  btn.setAttribute("aria-busy", "true");
  const original = btn.textContent;
  btn.textContent = "Switching...";
  if (status) status.textContent = "Creating your artist profile...";

  try {
    const res = await fetch("/api/me/become-artist", { method: "POST" });
    if (!res.ok) throw new Error(`become-artist failed: ${res.status}`);
    // Reload so the nav (Artist studio link) and this profile re-render for an artist account.
    window.location.reload();
  } catch (err) {
    btn.textContent = original;
    btn.disabled = false;
    btn.removeAttribute("aria-busy");
    if (status) status.textContent = "Couldn't create the artist profile. Please try again.";
    console.warn(err);
  }
}
