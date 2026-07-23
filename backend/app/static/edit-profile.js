// WHAT THIS FILE IS
// The browser code behind the "Edit profile" form on your own profile (T48). You optionally pick a
// new profile picture (JPEG/PNG ≤ 10 MB) and edit your bio, then hit Save. On save: if a new image
// was chosen, run the 3-step upload (ask our server for a signed upload URL → PUT the file straight
// to Supabase Storage → tell our server to point your avatar at it); then PATCH the bio; then reload
// so the page re-renders with the new picture + bio. We validate the image type/size in the browser
// for a fast, friendly error; the server is the real gate (ADR-0008: technical checks only).
//
// WHY plain JavaScript (no framework/build step): ADR-0013 keeps the frontend buildless. The login
// session cookie is sent automatically (same-origin), so the server always acts on YOUR account —
// we never send an id, so it can't be spoofed.

const EDIT_MAX_BYTES = 10 * 1024 * 1024; // 10 MB, matching the server's SignUploadBody limit
const EDIT_ALLOWED_TYPES = ["image/jpeg", "image/png"];

// Show/hide the edit form when the "Edit profile" button is clicked.
function toggleEditProfile(btn) {
  const form = btn.closest(".edit-profile").querySelector(".edit-profile-form");
  const opening = form.hasAttribute("hidden");
  if (opening) {
    form.removeAttribute("hidden");
  } else {
    form.setAttribute("hidden", "");
  }
  btn.setAttribute("aria-expanded", opening ? "true" : "false");
}

// The Save handler. `event` is the form submit; we stop the browser's default page reload so we can
// do the work ourselves. `form` is the <form> element.
async function saveProfile(event, form) {
  event.preventDefault();
  const status = form.querySelector(".edit-profile-status");
  const saveBtn = form.querySelector(".edit-profile-save");
  const fileInput = form.querySelector(".edit-avatar-file");
  const bio = form.querySelector(".edit-bio").value.trim();
  const file = fileInput.files[0];

  // If a file was picked, validate it up front for a friendly error before any network call.
  if (file) {
    if (!EDIT_ALLOWED_TYPES.includes(file.type)) {
      status.textContent = "Please pick a JPEG or PNG image.";
      return;
    }
    if (file.size > EDIT_MAX_BYTES) {
      status.textContent = "That image is over 10 MB. Please pick a smaller one.";
      return;
    }
  }

  saveBtn.disabled = true;
  status.textContent = "Saving…";
  try {
    // 1) The avatar (only if a new image was chosen): the same 3-step signed-upload flow the artist
    //    upload uses (T50/T51), but against the public avatars bucket.
    if (file) {
      const signRes = await fetch("/api/me/avatar/sign-upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contentType: file.type, sizeBytes: file.size }),
      });
      if (!signRes.ok) throw new Error(`avatar sign-upload failed: ${signRes.status}`);
      const { path, signedUrl } = (await signRes.json()).data;

      // Upload the file straight to Supabase Storage with the signed URL.
      const putRes = await fetch(signedUrl, {
        method: "PUT",
        headers: { "Content-Type": file.type },
        body: file,
      });
      if (!putRes.ok) throw new Error(`avatar storage upload failed: ${putRes.status}`);

      // Tell our server to store this uploaded object as our avatar.
      const avatarRes = await fetch("/api/me/avatar", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path }),
      });
      if (!avatarRes.ok) throw new Error(`avatar save failed: ${avatarRes.status}`);
    }

    // 2) The bio — always sent (an empty string clears it on the server).
    const bioRes = await fetch("/api/me/profile", {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bio }),
    });
    if (!bioRes.ok) throw new Error(`profile update failed: ${bioRes.status}`);

    status.textContent = "Saved!";
    window.location.reload(); // re-render with the new picture + bio
  } catch (err) {
    status.textContent = "Couldn't save. Please try again.";
    console.warn(err);
    saveBtn.disabled = false;
  }
}
