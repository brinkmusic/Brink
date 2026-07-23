// WHAT THIS FILE IS
// The browser code behind an artist's upload box (T51, reworked in T104). An artist post can now be
// a photo, just text, or both. You optionally pick a JPEG/PNG image (≤ 10 MB), optionally add a
// caption, and hit Share. When there's a photo, three steps happen: (1) ask our server for a
// one-time signed upload URL (T50), (2) upload the file straight to Supabase Storage with that URL,
// (3) create the artist post that references it. A text-only post skips straight to step 3 with no
// image. We validate type/size in the browser for a fast, friendly error; the server is the real
// gate (ADR-0008: technical checks only, no moderation).
//
// WHY plain JavaScript (no framework/build step): ADR-0013 keeps the frontend buildless.

const ARTIST_MAX_BYTES = 10 * 1024 * 1024; // 10 MB, matching the server's SignUploadBody limit
const ARTIST_ALLOWED_TYPES = ["image/jpeg", "image/png"];

let _artistFile = null; // the currently-picked, validated file (null = text-only post)

// Enable Share when the post has SOMETHING to send — a valid photo OR some text — and disable it
// when it's empty. Called from both the file picker and the caption box so either one can satisfy
// the "not empty" rule (mirrors the server's 400 guard).
function _artistRefreshShare(box) {
  const shareBtn = box.querySelector(".artist-share");
  const caption = box.querySelector(".artist-caption").value.trim();
  shareBtn.disabled = !_artistFile && !caption;
}

// Runs on every keystroke in the caption box: a text-only post becomes shareable as soon as there
// are some words, even with no photo picked.
function artistCaptionInput(input) {
  _artistRefreshShare(input.closest(".artist-upload"));
}

// Runs when a file is chosen: validate type + size. A valid file makes the post shareable; an
// invalid one is rejected with a message and cleared (the caption alone may still allow sharing).
function artistFilePicked(input) {
  const box = input.closest(".artist-upload");
  const status = box.querySelector(".artist-status");
  const file = input.files[0];

  _artistFile = null;

  if (!file) {
    // The picker was cleared — a caption alone can still allow a text-only post.
    status.textContent = "";
    _artistRefreshShare(box);
    return;
  }
  if (!ARTIST_ALLOWED_TYPES.includes(file.type)) {
    status.textContent = "Please pick a JPEG or PNG image.";
    _artistRefreshShare(box);
    return;
  }
  if (file.size > ARTIST_MAX_BYTES) {
    status.textContent = "That image is over 10 MB. Please pick a smaller one.";
    _artistRefreshShare(box);
    return;
  }
  _artistFile = file;
  status.textContent = `Ready to share: ${file.name}`;
  _artistRefreshShare(box);
}

// Publish the post. With a photo it's the three-step upload; text-only skips to the create call
// with no image. A post needs a photo OR text — with neither we just nudge (matching the 400 guard).
// Any failure leaves a friendly message and re-enables Share.
async function artistUpload(btn) {
  const box = btn.closest(".artist-upload");
  const status = box.querySelector(".artist-status");
  const caption = box.querySelector(".artist-caption").value.trim();

  if (!_artistFile && !caption) {
    status.textContent = "Add a photo or some text to share.";
    return;
  }

  btn.disabled = true;
  status.textContent = _artistFile ? "Uploading…" : "Sharing…";
  try {
    // The create-post body: caption is always sent (null when empty); imageUrl is filled in below
    // only when there's a photo to upload.
    const body = { caption: caption || null };

    if (_artistFile) {
      // 1) One-time signed upload URL from our server (artist-only route, T50).
      const signRes = await fetch("/api/artist/sign-upload", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ contentType: _artistFile.type, sizeBytes: _artistFile.size }),
      });
      if (!signRes.ok) throw new Error(`sign-upload failed: ${signRes.status}`);
      const { path, signedUrl } = (await signRes.json()).data;

      // 2) Upload the file straight to Supabase Storage with that signed URL.
      const putRes = await fetch(signedUrl, {
        method: "PUT",
        headers: { "Content-Type": _artistFile.type },
        body: _artistFile,
      });
      if (!putRes.ok) throw new Error(`storage upload failed: ${putRes.status}`);
      body.imageUrl = path;
    }

    // 3) Create the artist post (with the stored object path, or text-only when there's no photo).
    const postRes = await fetch("/api/artist/posts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!postRes.ok) throw new Error(`create post failed: ${postRes.status}`);

    status.textContent = "Posted!";
    window.location.reload(); // show the new post
  } catch (err) {
    status.textContent = "Couldn't share that. Please try again.";
    console.warn(err);
    btn.disabled = false;
  }
}
