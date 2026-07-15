// WHAT THIS FILE IS
// The browser code behind the feed's comments (T42). Each post has a "💬 N" button that
// opens a panel showing that post's comments (loaded from the T12 API on first open) and a
// box to add one. Posting a comment calls the API, then drops the new comment straight to
// the top of the list and bumps the count — no page reload.
//
// WHY plain JavaScript (no framework/build step): ADR-0013 keeps the frontend buildless.
// The login session cookie is sent automatically because the requests are same-origin.
//
// SECURITY: comment text and author names are other people's input, so we put them on the
// page with textContent (never innerHTML), which cannot inject HTML/script.

// Open or close a post's comment panel. On the first open, fetch its comments once.
async function toggleComments(btn) {
  const box = btn.closest(".comments");
  const panel = box.querySelector(".comment-panel");
  const opening = panel.hasAttribute("hidden");
  if (!opening) {
    panel.setAttribute("hidden", "");
    return;
  }
  panel.removeAttribute("hidden");
  if (!box.dataset.loaded) {
    await loadComments(box);
    box.dataset.loaded = "1"; // don't re-fetch every time it's reopened
  }
}

// Fetch and render a post's comments (newest-first, each with its author).
async function loadComments(box) {
  const list = box.querySelector(".comment-list");
  try {
    const res = await fetch(`/api/posts/${box.dataset.postId}/comments`);
    if (!res.ok) throw new Error(`comments GET failed: ${res.status}`);
    const comments = (await res.json()).data;
    list.textContent = "";
    if (comments.length === 0) {
      list.appendChild(emptyRow("No comments yet. Be the first."));
    } else {
      comments.forEach((c) => list.appendChild(renderComment(c)));
    }
  } catch (err) {
    list.textContent = "";
    list.appendChild(emptyRow("Couldn't load comments."));
    console.warn(err);
  }
}

// Send a new comment for this post, then show it at the top of the list.
async function submitComment(event, form) {
  event.preventDefault(); // stop the browser from doing a full-page form submit
  const box = form.closest(".comments");
  const input = form.querySelector('input[name="body"]');
  const text = input.value.trim();
  if (!text) return; // client-side non-empty guard (the server is the real gate)

  const submitBtn = form.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  try {
    const res = await fetch(`/api/posts/${box.dataset.postId}/comments`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ body: text }),
    });
    if (!res.ok) throw new Error(`comment POST failed: ${res.status}`);
    const comment = (await res.json()).data;

    const list = box.querySelector(".comment-list");
    const empty = list.querySelector(".comment-empty");
    if (empty) empty.remove(); // drop the "no comments yet" placeholder
    list.prepend(renderComment(comment)); // newest-first
    input.value = "";
    bumpCommentCount(box, 1);
  } catch (err) {
    console.warn(err);
  } finally {
    submitBtn.disabled = false;
  }
}

// Build one comment's list row: author, text, and a "3m ago" time.
function renderComment(c) {
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
  when.textContent = timeAgo(c.createdAt);

  li.append(author, body, when);
  return li;
}

// A plain one-line row used for the empty / error states.
function emptyRow(text) {
  const li = document.createElement("li");
  li.className = "comment-empty";
  li.textContent = text;
  return li;
}

// Add `delta` to a post's comment count, never below zero.
function bumpCommentCount(box, delta) {
  const el = box.querySelector(".comment-count");
  el.textContent = Math.max(0, parseInt(el.textContent, 10) + delta);
}

// A friendly "3m ago" label from an ISO timestamp (Brink stores UTC).
function timeAgo(iso) {
  const minutes = Math.round((Date.now() - new Date(iso).getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.round(hours / 24)}d ago`;
}
