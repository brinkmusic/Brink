// WHAT THIS FILE IS
// The browser code behind an artist's upload box (T51). You pick a JPEG/PNG image (≤ 10 MB),
// add a caption, and hit Share. Three steps happen: (1) ask our server for a one-time signed
// upload URL (T50), (2) upload the file straight to Supabase Storage with that URL, (3) create
// the artist post that references it. We validate type/size in the browser for a fast, friendly
// error; the server is the real gate (ADR-0008: technical checks only, no moderation).
//
// WHY plain JavaScript (no framework/build step): ADR-0013 keeps the frontend buildless.

const ARTIST_MAX_BYTES = 10 * 1024 * 1024; // 10 MB, matching the server's SignUploadBody limit
const ARTIST_ALLOWED_TYPES = ["image/jpeg", "image/png"];

let _artistFile = null; // the currently-picked, validated file

// Runs when a file is chosen: validate type + size, and only enable Share if it's good.
function artistFilePicked(input) {
  const box = input.closest(".artist-upload");
  const status = box.querySelector(".artist-status");
  const shareBtn = box.querySelector(".artist-share");
  const file = input.files[0];

  _artistFile = null;
  shareBtn.disabled = true;

  if (!file) {
    status.textContent = "";
    return;
  }
  if (!ARTIST_ALLOWED_TYPES.includes(file.type)) {
    status.textContent = "Please pick a JPEG or PNG image.";
    return;
  }
  if (file.size > ARTIST_MAX_BYTES) {
    status.textContent = "That image is over 10 MB. Please pick a smaller one.";
    return;
  }
  _artistFile = file;
  status.textContent = `Ready to share: ${file.name}`;
  shareBtn.disabled = false;
}

// The three-step upload. Any failure leaves a friendly message and re-enables Share.
async function artistUpload(btn) {
  const box = btn.closest(".artist-upload");
  const status = box.querySelector(".artist-status");
  const caption = box.querySelector(".artist-caption").value.trim();

  if (!_artistFile) return;
  if (!caption) {
    status.textContent = "Add a caption to go with it.";
    return;
  }

  btn.disabled = true;
  status.textContent = "Uploading…";
  try {
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

    // 3) Create the artist post referencing the stored object.
    const postRes = await fetch("/api/artist/posts", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ imageUrl: path, caption }),
    });
    if (!postRes.ok) throw new Error(`create post failed: ${postRes.status}`);

    status.textContent = "Posted!";
    window.location.reload(); // show the new post
  } catch (err) {
    status.textContent = "Upload failed. Please try again.";
    console.warn(err);
    btn.disabled = false;
  }
}
