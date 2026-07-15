// WHAT THIS FILE IS
// The tiny bit of browser code that makes the feed's reaction buttons live (T41).
// When you tap a reaction it (1) updates the button immediately so it feels instant
// ("optimistic UI"), then (2) tells the server by calling the T11 reactions API, and
// (3) corrects the counts to whatever the server reports (the source of truth). If the
// call fails, it undoes the optimistic change so the screen never lies.
//
// WHY plain JavaScript (no framework/build step): ADR-0013 keeps the frontend simple and
// buildless. This is a single self-contained function loaded by feed.html; the login
// session cookie is sent automatically because the request is same-origin.

// Called from each button's onclick (see feed.html). `btn` is the button that was tapped.
async function react(btn) {
  const bar = btn.closest(".reactions"); // the row of buttons for one post
  const postId = bar.dataset.postId; // which post to react to
  const type = btn.dataset.type; // "HEART" | "FIRE" | "SPARKLE"
  const countEl = btn.querySelector(".react-count");

  // Are we currently reacted with this type? If so, tapping removes it; otherwise adds it.
  const wasReacted = btn.classList.contains("reacted");
  const method = wasReacted ? "DELETE" : "POST";

  // 1) Optimistic update: flip the button and nudge the count now, before the network.
  setReacted(btn, !wasReacted);
  bumpCount(countEl, wasReacted ? -1 : 1);
  btn.disabled = true; // stop double-taps racing while the request is in flight

  try {
    // 2) Tell the server. The API attributes the reaction to the logged-in user (from the
    //    session cookie), so we only send the type. It returns the post's fresh counts.
    const res = await fetch(`/api/posts/${postId}/reactions`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type }),
    });
    if (!res.ok) throw new Error(`reaction ${method} failed: ${res.status}`);

    // 3) Reconcile: overwrite every count on this post with the server's numbers, so the
    //    display matches reality even if other people reacted at the same time.
    const counts = (await res.json()).data.counts;
    bar.querySelectorAll(".react-btn").forEach((b) => {
      const c = counts[b.dataset.type];
      if (c !== undefined) b.querySelector(".react-count").textContent = c;
    });
  } catch (err) {
    // The server rejected us (e.g. rate limited, or offline): undo the optimistic change
    // so the button and count go back to the truth.
    setReacted(btn, wasReacted);
    bumpCount(countEl, wasReacted ? 1 : -1);
    console.warn(err);
  } finally {
    btn.disabled = false;
  }
}

// Toggle a button's "reacted" look and its accessibility state together.
function setReacted(btn, on) {
  btn.classList.toggle("reacted", on);
  btn.setAttribute("aria-pressed", on ? "true" : "false");
}

// Add `delta` to a count element, never letting it show below zero.
function bumpCount(countEl, delta) {
  const next = Math.max(0, parseInt(countEl.textContent, 10) + delta);
  countEl.textContent = next;
}
