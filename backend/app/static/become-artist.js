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
  btn.disabled = true;
  const original = btn.textContent;
  btn.textContent = "Switching…";

  try {
    const res = await fetch("/api/me/become-artist", { method: "POST" });
    if (!res.ok) throw new Error(`become-artist failed: ${res.status}`);
    // Reload so the nav (Artist studio link) and this profile re-render for an artist account.
    window.location.reload();
  } catch (err) {
    btn.textContent = original;
    btn.disabled = false;
    console.warn(err);
  }
}
