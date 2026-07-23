// WHAT THIS FILE IS
// The browser code behind the feed's "Liked by X and N others" line (T96). The line itself
// is server-rendered; tapping it opens a small panel listing EVERYONE who reacted to the
// post — fetched lazily (only on first open) from GET /api/posts/{id}/reactions, which
// returns unique reactors newest-first with the reaction types each one left.
//
// WHY plain JavaScript (no framework/build step): ADR-0013 keeps the frontend buildless.
// The login session cookie is sent automatically because the request is same-origin.
//
// SECURITY: reactor names come from other people's profiles, so we put them on the page
// with textContent (never innerHTML), which cannot inject HTML/script.

// The emoji shown for each reaction type — mirrors the feed's reaction buttons.
const REACTION_EMOJI = { HEART: "❤️", FIRE: "🔥", SPARKLE: "✨" };

// Open or close a post's reactors panel. On the first open, fetch the list once.
async function toggleReactors(btn) {
  const box = btn.closest(".liked-by");
  const panel = box.querySelector(".reactors-panel");
  const opening = panel.hasAttribute("hidden");
  if (!opening) {
    panel.setAttribute("hidden", "");
    btn.setAttribute("aria-expanded", "false");
    return;
  }
  panel.removeAttribute("hidden");
  btn.setAttribute("aria-expanded", "true");
  if (!box.dataset.loaded) {
    const loaded = await loadReactors(box);
    if (loaded) box.dataset.loaded = "1"; // don't re-fetch every time it's reopened
  }
}

// Fetch and render who reacted: one row per person — their name (a profile link) and the
// emoji(s) of every reaction they left.
async function loadReactors(box) {
  const list = box.querySelector(".reactor-list");
  const status = box.querySelector(".reactors-status");
  list.textContent = "";
  if (status) status.textContent = "Loading…";
  try {
    const res = await fetch(`/api/posts/${box.dataset.postId}/reactions`);
    if (!res.ok) throw new Error(`reactors GET failed: ${res.status}`);
    const reactors = (await res.json()).data.reactors;
    if (status) status.textContent = "";
    reactors.forEach((r) => {
      const li = document.createElement("li");
      li.className = "reactor";

      const name = document.createElement("a");
      name.className = "reactor-name";
      name.href = `/u/${encodeURIComponent(r.handle)}`;
      name.textContent = r.displayName;

      const emojis = document.createElement("span");
      emojis.className = "reactor-types";
      emojis.textContent = r.types.map((t) => REACTION_EMOJI[t] || "").join(" ");

      li.append(name, emojis);
      list.appendChild(li);
    });
    return true;
  } catch (err) {
    if (status) status.textContent = "Couldn't load who reacted. Close and reopen to try again.";
    console.warn(err);
    return false;
  }
}
