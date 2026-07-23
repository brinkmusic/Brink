// WHAT THIS FILE IS
// The browser code behind the "post a song" composer at the top of the feed (T40). You type a
// song name, it searches Spotify (GET /api/search), you pick a result, add an optional caption,
// and hit Share — which publishes the post (POST /api/posts, T10) and reloads the feed so your
// new post appears at the top.
//
// WHY plain JavaScript (no framework/build step): ADR-0013 keeps the frontend buildless. Requests
// are same-origin, so the login session cookie rides along automatically.
//
// SECURITY: track titles/artists come from Spotify (external data), so we put them on the page
// with textContent (never innerHTML), which cannot inject HTML.

let _composerDebounce = null;

// Called on every keystroke in the search box. We debounce (wait 250ms after the last keystroke)
// so we don't fire a search — and hit Spotify — on every single letter.
function composerSearch(input) {
  const section = input.closest(".composer");
  const q = input.value.trim();
  clearTimeout(_composerDebounce);
  if (!q) {
    hideResults(section);
    return;
  }
  _composerDebounce = setTimeout(() => runSearch(section, q), 250);
}

// Fetch matching tracks and show them as a clickable list.
async function runSearch(section, q) {
  const list = section.querySelector(".composer-results");
  const status = section.querySelector(".composer-status");
  if (status) status.textContent = "Searching...";
  try {
    const res = await fetch(`/api/search?q=${encodeURIComponent(q)}`);
    if (!res.ok) throw new Error(`search failed: ${res.status}`);
    const tracks = (await res.json()).data;
    list.textContent = "";
    if (tracks.length === 0) {
      list.appendChild(resultRow("No matches", null));
      if (status) status.textContent = "No matches found.";
    } else {
      tracks.forEach((t) => list.appendChild(resultRow(`${t.title} · ${t.artistName}`, t)));
      if (status) status.textContent = `${tracks.length} result${tracks.length === 1 ? "" : "s"} found.`;
    }
    list.hidden = false;
  } catch (err) {
    list.textContent = "";
    list.hidden = true;
    if (status) status.textContent = "Couldn't search right now. Please try again.";
    console.warn(err);
  }
}

// One row in the results list. When it carries a track, clicking it selects that track.
function resultRow(label, track) {
  const li = document.createElement("li");
  li.className = "composer-result";
  if (track) {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "composer-result-button";
    btn.textContent = label;
    btn.onclick = () => selectTrack(li.closest(".composer"), track);
    li.appendChild(btn);
  } else {
    li.textContent = label;
    li.classList.add("composer-result-empty");
  }
  return li;
}

// Lock in the chosen track: stash it on the section, show the caption + Share step, hide search.
// `source` records HOW the track was chosen so publish can label the post: "MANUAL" for a typed
// search pick (the default), "SPOTIFY" for the one-tap "share what you're hearing" flow (T101).
function selectTrack(section, track, source = "MANUAL") {
  section._track = track; // stash the whole track for publish
  section._source = source; // remember MANUAL vs SPOTIFY for the publish body
  section.querySelector(".composer-track-title").textContent = track.title;
  section.querySelector(".composer-track-artist").textContent = track.artistName;
  section.querySelector(".composer-results").hidden = true;
  const status = section.querySelector(".composer-status");
  if (status) status.textContent = `${track.title} selected. Add a caption or share it.`;
  section.querySelector(".composer-search").hidden = true;
  section.querySelector(".composer-selected").hidden = false;
  section.querySelector(".composer-caption").focus();
}

// T101 — the one-tap "🎧 Share what you're hearing" button. Ask the server what the caller is
// playing on Spotify right now (GET /api/me/now-playing, T20); if a track comes back, drop it into
// the SAME selected-track step the search flow uses (so caption + Share + Cancel all just work),
// tagged SPOTIFY. If nothing is playing — or Spotify isn't linked — the endpoint returns data:null
// (it never errors on the empty cases), so we just explain that in the status line and leave the
// composer as it was. Nothing here can break the page.
async function shareNowPlaying(btn) {
  const section = btn.closest(".composer");
  const status = section.querySelector(".composer-status");
  // Busy state (T81 a11y): disable + aria-busy while the live Spotify call is in flight (~1-2s).
  btn.disabled = true;
  btn.setAttribute("aria-busy", "true");
  if (status) status.textContent = "Checking what's playing…";
  try {
    const res = await fetch("/api/me/now-playing");
    if (!res.ok) throw new Error(`now-playing failed: ${res.status}`);
    // `data` is null for EVERY empty/degraded case (nothing playing, no linked Spotify, outage),
    // so this one null check covers them all.
    const data = (await res.json()).data;
    if (data && data.track) {
      selectTrack(section, data.track, "SPOTIFY");
    } else if (status) {
      status.textContent = "Nothing playing right now — start a song on Spotify and try again.";
    }
  } catch (err) {
    if (status) status.textContent = "Couldn't check Spotify right now. Please try again.";
    console.warn(err);
  } finally {
    // Always re-enable so a slow/failed call never leaves the button stuck.
    btn.disabled = false;
    btn.removeAttribute("aria-busy");
  }
}

// Back out of a selection and return to the search box.
function composerReset(btn) {
  const section = btn.closest(".composer");
  section._track = null;
  section._source = null;
  const searchBox = section.querySelector(".composer-search");
  const status = section.querySelector(".composer-status");
  searchBox.value = "";
  searchBox.hidden = false;
  section.querySelector(".composer-caption").value = "";
  section.querySelector(".composer-selected").hidden = true;
  if (status) status.textContent = "";
  hideResults(section);
}

// Publish the selected track as a post, then reload the feed so the new post shows at the top.
async function composerPublish(btn) {
  const section = btn.closest(".composer");
  const track = section._track;
  if (!track) return;
  const caption = section.querySelector(".composer-caption").value.trim();
  const status = section.querySelector(".composer-status");

  btn.disabled = true;
  if (status) status.textContent = "Sharing...";
  try {
    const res = await fetch("/api/posts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        // MANUAL for a typed search pick, SPOTIFY for the one-tap now-playing flow (set in
        // selectTrack). Fall back to MANUAL if somehow unset so the body is always valid.
        source: section._source || "MANUAL",
        caption: caption || null,
        track: {
          spotifyId: track.spotifyId,
          title: track.title,
          artistName: track.artistName,
          albumArtUrl: track.albumArtUrl ?? null,
          popularity: track.popularity ?? null,
        },
      }),
    });
    if (!res.ok) throw new Error(`publish failed: ${res.status}`);
    window.location.reload(); // simplest reliable way to show the new post at the top
  } catch (err) {
    if (status) status.textContent = "Couldn't share that song. Please try again.";
    console.warn(err);
    btn.disabled = false;
  }
}

// Hide and clear the results list.
function hideResults(section) {
  const list = section.querySelector(".composer-results");
  list.hidden = true;
  list.textContent = "";
  const status = section.querySelector(".composer-status");
  if (status) status.textContent = "";
}
