// WHAT THIS FILE IS
// Browser code for T54's artist-post engagement on profile pages. It mirrors the regular feed's
// reactions/comments scripts, but points at the T52 artist-post endpoints:
//   /api/artist/posts/{id}/reactions
//   /api/artist/posts/{id}/comments
//
// SECURITY: comments and author names come from users, so every rendered value uses textContent.

async function artistReact(btn) {
  const bar = btn.closest(".artist-reactions");
  const postId = bar.dataset.postId;
  const type = btn.dataset.type;
  const countEl = btn.querySelector(".react-count");
  const wasReacted = btn.classList.contains("reacted");
  const method = wasReacted ? "DELETE" : "POST";

  setArtistReacted(btn, !wasReacted);
  bumpArtistCount(countEl, wasReacted ? -1 : 1);
  btn.disabled = true;

  try {
    const res = await fetch(`/api/artist/posts/${postId}/reactions`, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type }),
    });
    if (!res.ok) throw new Error(`artist reaction ${method} failed: ${res.status}`);

    const counts = (await res.json()).data.counts;
    bar.querySelectorAll(".react-btn").forEach((b) => {
      const c = counts[b.dataset.type];
      if (c !== undefined) b.querySelector(".react-count").textContent = c;
    });
  } catch (err) {
    setArtistReacted(btn, wasReacted);
    bumpArtistCount(countEl, wasReacted ? 1 : -1);
    console.warn(err);
  } finally {
    btn.disabled = false;
  }
}

function setArtistReacted(btn, on) {
  btn.classList.toggle("reacted", on);
  btn.setAttribute("aria-pressed", on ? "true" : "false");
}

function bumpArtistCount(countEl, delta) {
  countEl.textContent = Math.max(0, parseInt(countEl.textContent, 10) + delta);
}

async function toggleArtistComments(btn) {
  const box = btn.closest(".artist-comments");
  const panel = box.querySelector(".comment-panel");
  const opening = panel.hasAttribute("hidden");
  if (!opening) {
    panel.setAttribute("hidden", "");
    return;
  }
  panel.removeAttribute("hidden");
  if (!box.dataset.loaded) {
    await loadArtistComments(box);
    box.dataset.loaded = "1";
  }
}

async function loadArtistComments(box) {
  const list = box.querySelector(".comment-list");
  try {
    const res = await fetch(`/api/artist/posts/${box.dataset.postId}/comments`);
    if (!res.ok) throw new Error(`artist comments GET failed: ${res.status}`);
    const comments = (await res.json()).data;
    list.textContent = "";
    if (comments.length === 0) {
      list.appendChild(artistEmptyRow("No comments yet. Be the first."));
    } else {
      comments.forEach((c) => list.appendChild(renderArtistComment(c)));
    }
  } catch (err) {
    list.textContent = "";
    list.appendChild(artistEmptyRow("Couldn't load comments."));
    console.warn(err);
  }
}

async function submitArtistComment(event, form) {
  event.preventDefault();
  const box = form.closest(".artist-comments");
  const input = form.querySelector('input[name="body"]');
  const text = input.value.trim();
  if (!text) return;

  const submitBtn = form.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  try {
    const res = await fetch(`/api/artist/posts/${box.dataset.postId}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body: text }),
    });
    if (!res.ok) throw new Error(`artist comment POST failed: ${res.status}`);
    const comment = (await res.json()).data;

    const list = box.querySelector(".comment-list");
    const empty = list.querySelector(".comment-empty");
    if (empty) empty.remove();
    list.prepend(renderArtistComment(comment));
    input.value = "";
    bumpArtistCommentCount(box, 1);
  } catch (err) {
    console.warn(err);
  } finally {
    submitBtn.disabled = false;
  }
}

function renderArtistComment(c) {
  const li = document.createElement("li");
  li.className = "comment";

  const author = document.createElement("span");
  author.className = "comment-author";
  author.textContent = c.author.displayName;

  const body = document.createElement("span");
  body.className = "comment-body";
  body.textContent = c.body;

  const when = document.createElement("span");
  when.className = "comment-when";
  when.textContent = artistTimeAgo(c.createdAt);

  li.append(author, body, when);
  return li;
}

function artistEmptyRow(text) {
  const li = document.createElement("li");
  li.className = "comment-empty";
  li.textContent = text;
  return li;
}

function bumpArtistCommentCount(box, delta) {
  const el = box.querySelector(".comment-count");
  el.textContent = Math.max(0, parseInt(el.textContent, 10) + delta);
}

function artistTimeAgo(iso) {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}
