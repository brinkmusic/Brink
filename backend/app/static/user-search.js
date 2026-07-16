// WHAT THIS FILE IS
// The browser code for T46's "Find people" box in the authenticated nav. It calls the existing
// T15 endpoint (GET /api/users/search?q=...) and renders each result as a link to /u/<handle>,
// where the profile page already has the Follow/Unfollow button.
//
// WHY plain JavaScript: ADR-0013 keeps Brink's frontend buildless. The API returns user-controlled
// display names/handles, so every value is inserted with textContent instead of innerHTML.

let _userSearchDebounce = null;
let _userSearchRequestId = 0;

// Called on every keystroke. A two-character minimum mirrors the API contract and avoids making
// noisy requests for one-letter queries that match nearly everyone.
function userSearch(input) {
  const form = input.closest(".user-search");
  const q = input.value.trim();
  clearTimeout(_userSearchDebounce);

  if (q.length < 2) {
    renderUserSearchHint(form, "Type at least 2 characters");
    return;
  }

  _userSearchDebounce = setTimeout(() => runUserSearch(form, q), 250);
}

// Submit sends the first visible result if there is one; otherwise it keeps the user on the page.
function userSearchSubmit(form) {
  const firstLink = form.querySelector(".user-search-results a");
  if (firstLink) window.location.href = firstLink.href;
  return false;
}

async function runUserSearch(form, q) {
  const requestId = ++_userSearchRequestId;

  try {
    const res = await fetch(`/api/users/search?q=${encodeURIComponent(q)}`);
    if (!res.ok) throw new Error(`user search failed: ${res.status}`);
    const users = (await res.json()).data;
    if (requestId !== _userSearchRequestId) return; // ignore an older response that arrived late
    renderUserSearchResults(form, users);
  } catch (err) {
    console.warn(err);
    if (requestId === _userSearchRequestId) renderUserSearchHint(form, "Search is unavailable");
  }
}

function renderUserSearchResults(form, users) {
  const list = clearUserSearchResults(form);

  if (users.length === 0) {
    list.appendChild(emptyUserSearchRow("No one found"));
  } else {
    users.forEach((user) => list.appendChild(userSearchRow(user)));
  }

  list.hidden = false;
}

function renderUserSearchHint(form, message) {
  const list = clearUserSearchResults(form);
  list.appendChild(emptyUserSearchRow(message));
  list.hidden = false;
}

function clearUserSearchResults(form) {
  const list = form.querySelector(".user-search-results");
  list.textContent = "";
  return list;
}

function emptyUserSearchRow(message) {
  const li = document.createElement("li");
  li.className = "user-search-empty";
  li.textContent = message;
  return li;
}

function userSearchRow(user) {
  const li = document.createElement("li");
  li.className = "user-search-result";

  const link = document.createElement("a");
  link.href = `/u/${encodeURIComponent(user.handle)}`;

  const name = document.createElement("span");
  name.className = "user-search-name";
  name.textContent = user.displayName || `@${user.handle}`;

  const meta = document.createElement("span");
  meta.className = "user-search-meta";
  meta.textContent = `@${user.handle}`;
  if (user.isArtist) {
    const badge = document.createElement("span");
    badge.className = "user-search-badge";
    badge.textContent = " artist";
    meta.appendChild(badge);
  }

  link.appendChild(name);
  link.appendChild(meta);
  li.appendChild(link);
  return li;
}
