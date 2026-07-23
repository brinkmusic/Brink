// WHAT THIS FILE IS
// The bit of browser code that makes feed song cards playable (T94). Tapping a card's
// album art (a <button>, see feed.html) opens Spotify's free "embed" player — a small
// iframe (a web page inside the page, served by Spotify) — right inside the card, and
// tapping the art again closes it. No Spotify login is needed for the embed; listeners
// without Premium simply get a 30-second preview.
//
// WHY the iframe is built here in JavaScript instead of rendered in the HTML: a feed can
// hold many posts, and loading one third-party frame per post up front would make the page
// heavy and could autoplay-collide. So the page ships with NO iframes; we create one only
// when the listener asks for it, and we keep at most ONE player open at a time (opening a
// second card closes the first, so two songs never play over each other).

// The card (<article class="post">) whose player is currently open, or null. Module-level
// so every call of togglePlayer can see (and close) the previously opened one.
let openPlayerCard = null;

// Called from each song card's art button (see feed.html). `btn` is the button that was
// tapped; its data-spotify-id says which track to play.
function togglePlayer(btn) {
  const card = btn.closest(".post");

  // Tapping the art of an already-open card closes its player (a simple toggle).
  if (card.querySelector(".post-player")) {
    closeOpenPlayer();
    return;
  }

  // One player at a time: close whichever card is open before opening this one.
  closeOpenPlayer();

  // Build the player: a wrapper div (styled full-width in brink.css) holding Spotify's
  // compact 152px-tall embed for this track. encodeURIComponent guards the URL in case a
  // track id ever contains unexpected characters.
  const wrap = document.createElement("div");
  wrap.className = "post-player";
  const frame = document.createElement("iframe");
  frame.src = "https://open.spotify.com/embed/track/" + encodeURIComponent(btn.dataset.spotifyId);
  frame.loading = "lazy"; // let the browser deprioritize fetching it
  frame.allow = "encrypted-media"; // Spotify needs this permission to play protected audio
  frame.title = btn.getAttribute("aria-label"); // e.g. "Play Redbone" — labels the frame for screen readers
  wrap.appendChild(frame);
  card.appendChild(wrap);

  openPlayerCard = card;
  btn.setAttribute("aria-expanded", "true"); // tell assistive tech the player is open
}

// Remove the currently-open player (if any) and reset its card's button state.
function closeOpenPlayer() {
  if (!openPlayerCard) return;
  const player = openPlayerCard.querySelector(".post-player");
  if (player) player.remove();
  const btn = openPlayerCard.querySelector(".post-art");
  if (btn) btn.setAttribute("aria-expanded", "false");
  openPlayerCard = null;
}
