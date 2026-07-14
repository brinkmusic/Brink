// WHAT THIS FILE IS
// The browser code behind the Follow / Unfollow button on a profile page (T43). Tapping it
// flips the button immediately ("optimistic"), tells the server via the T13 follow API, then
// trusts the server's answer for the final state. If the call fails, it undoes the change so
// the button never lies. The follower count next to it nudges up/down to match.
//
// WHY plain JavaScript (no framework/build step): ADR-0013 keeps the frontend buildless. The
// login session cookie is sent automatically because the request is same-origin.

async function toggleFollow(btn) {
  const userId = btn.dataset.userId;
  const following = btn.dataset.following === "true"; // are we currently following them?
  const method = following ? "DELETE" : "POST"; // DELETE unfollows, POST follows

  btn.disabled = true;
  setFollow(btn, !following); // optimistic flip
  bumpFollowerCount(following ? -1 : 1);

  try {
    // The follow API attributes the action to the logged-in user (from the session cookie),
    // so we only send the target's id in the URL. It returns the resulting {following: bool}.
    const res = await fetch(`/api/follow/${userId}`, { method });
    if (!res.ok) throw new Error(`follow ${method} failed: ${res.status}`);
    const data = (await res.json()).data;
    setFollow(btn, data.following); // reconcile with the server's truth
  } catch (err) {
    setFollow(btn, following); // revert the optimistic change
    bumpFollowerCount(following ? 1 : -1);
    console.warn(err);
  } finally {
    btn.disabled = false;
  }
}

// Put the button into the "following" or "not following" look + state.
function setFollow(btn, following) {
  btn.dataset.following = following ? "true" : "false";
  btn.setAttribute("aria-pressed", following ? "true" : "false");
  btn.textContent = following ? "Following" : "Follow";
  btn.classList.toggle("btn-ghost", following); // quiet, outlined once you follow
  btn.classList.toggle("btn-spotify", !following); // filled call-to-action when you don't
}

// Nudge the follower count on the page by delta, never below zero.
function bumpFollowerCount(delta) {
  const el = document.querySelector(".follower-count");
  if (el) el.textContent = Math.max(0, parseInt(el.textContent, 10) + delta);
}
