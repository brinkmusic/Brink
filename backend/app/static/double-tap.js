// WHAT THIS FILE IS
// The browser code for Instagram's signature gesture on Brink (T97): double-tapping a feed
// song card leaves a ❤️ HEART reaction and floats a big heart over the card. The gesture is
// deliberately ADD-ONLY — if you already hearted the post, double-tapping just replays the
// animation and never removes your heart (removal stays on the ❤️ button, exactly like
// Instagram). All the real reaction work (optimistic update, API call, rollback on failure)
// is delegated to react() from reactions.js, so there is exactly one reaction code path.
//
// WHY "delegated" listeners on the whole document instead of a handler attribute on every
// card: one listener covers every card (including any added later), and keeps the template
// clean. Each event walks up from what was tapped (e.target) to find the enclosing card.
//
// Interactive elements are excluded: double-tapping a button, link, or the comment box must
// keep its normal meaning (e.g. the T94 play button, the reaction buttons). So the gesture
// target is "anywhere on a song card EXCEPT its controls".

(function () {
  // Two taps within this many milliseconds count as a double-tap (touch devices don't
  // reliably fire the browser's built-in dblclick event, so we time taps ourselves).
  const DOUBLE_TAP_MS = 300;
  let lastTap = { card: null, time: 0 };

  // Is this element (or anything it sits inside) an interactive control we must not hijack?
  function insideControl(el) {
    return el.closest("button, a, input, textarea, select, label, iframe");
  }

  // The enclosing song card for whatever was tapped, or null. Artist cards
  // (<article class="artist-post">) are deliberately not matched — no gesture there.
  function songCard(el) {
    return el.closest("article.post");
  }

  // Heart the card: find its HEART button and reuse react() from reactions.js — but only
  // when not already hearted (add-only) and not mid-request (react() disables the button
  // while its API call is in flight). The animation plays either way, as feedback.
  function heartCard(card) {
    const btn = card.querySelector('.reactions .react-btn[data-type="HEART"]');
    if (btn && !btn.classList.contains("reacted") && !btn.disabled) react(btn);
    floatHeart(card);
  }

  // Drop a temporary big heart over the card; CSS animates it (scale up, fade out) and we
  // remove the element when the animation says it's done. Skipped entirely for people who
  // asked their device for less motion.
  function floatHeart(card) {
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const heart = document.createElement("span");
    heart.className = "double-tap-heart";
    heart.textContent = "❤️";
    heart.setAttribute("aria-hidden", "true"); // pure decoration — screen readers skip it
    card.appendChild(heart);
    heart.addEventListener("animationend", () => heart.remove());
  }

  // Desktop path: the browser detects the double-click for us.
  document.addEventListener("dblclick", (e) => {
    const card = songCard(e.target);
    if (!card || insideControl(e.target)) return;
    heartCard(card);
  });

  // Touch path: count two quick taps on the SAME card ourselves.
  document.addEventListener("pointerup", (e) => {
    if (e.pointerType !== "touch") return;
    const card = songCard(e.target);
    if (!card || insideControl(e.target)) return;
    const now = Date.now();
    if (lastTap.card === card && now - lastTap.time < DOUBLE_TAP_MS) {
      heartCard(card);
      lastTap = { card: null, time: 0 }; // reset so a triple-tap doesn't heart twice
    } else {
      lastTap = { card: card, time: now };
    }
  });
})();
