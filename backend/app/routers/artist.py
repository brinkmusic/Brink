# WHAT THIS FILE IS
# The artist "behind-the-scenes" (BTS) endpoints (T50) — how an artist account gets a promo
# image into storage and publishes an ArtistPost about it:
#   POST /api/artist/sign-upload -> mint a Supabase Storage signed upload URL for one image
#   POST /api/artist/posts       -> create an ArtistPost (stored image URL + caption + track?)
#
# AUTHORIZATION (ADR-0007/ADR-0008): both routes are login-gated (require_user) AND artist-only —
# the caller must be an artist account (User.isArtist == true). The artist is ALWAYS the
# authenticated caller (taken from require_user, never from the request body), so it can't be
# spoofed. There is NO content moderation (ADR-0008) — only the technical format/size checks that
# the request schema enforces (JPEG/PNG, <= 10 MB).

import uuid

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.db import get_session
from app.deps import AuthError, require_user
from app.models import ArtistPost, User
from app.responses import ok
from app.schemas import ArtistPostOut, CreateArtistPostBody, SignUploadBody, SignUploadOut
from app.security.supabase import create_signed_upload_url

# The private Supabase Storage bucket that holds artist promo images (created manually by Andrea —
# see the ticket's "Manual (user)" step). "Private" means objects aren't publicly readable; uploads
# go through the short-lived signed URL minted below.
UPLOAD_BUCKET = "artist-images"

# Map each allowed image MIME type to the file extension we give the stored object. The request
# schema already guarantees content_type is one of these two, so this lookup can't miss.
_EXTENSION = {"image/jpeg": "jpg", "image/png": "png"}

# prefix=... puts every route below under /api/artist; tags=... groups them in the API docs.
router = APIRouter(prefix="/api/artist", tags=["artist"])


def _require_artist(user: User) -> None:
    # The artist-only gate. A logged-in but non-artist account (isArtist == false, the default for
    # normal listeners) is refused with 403 Forbidden — it's authenticated, just not allowed here.
    # Raising AuthError(status=403) reuses the app-wide handler that emits our { "error": ... }
    # envelope, so the response shape matches every other error.
    if not user.is_artist:
        raise AuthError("artist account required", status=403)


@router.post("/sign-upload")
def sign_upload(
    body: SignUploadBody,
    user: User = Depends(require_user),   # ensures the caller is logged in; gives us their record
):
    # No DB access here — this route only mints a storage URL — so it takes no session dependency.
    _require_artist(user)

    # Build the object path INSIDE the caller's own folder: "<artistUserId>/<random>.<ext>". WHY
    # namespace by the caller's id: it keeps each artist's uploads separate and means the signed
    # permission we mint can only ever target this artist's own space. uuid4 is a random,
    # collision-free name so two uploads never clash.
    extension = _EXTENSION[body.content_type]
    path = f"{user.id}/{uuid.uuid4().hex}.{extension}"

    # Ask Supabase (as the server, holding the service-role key) to sign a one-time upload URL for
    # exactly that path. The browser then uploads the file straight to storage with it.
    signed = create_signed_upload_url(UPLOAD_BUCKET, path)

    out = SignUploadOut(
        path=signed["path"],
        signed_url=signed["signed_url"],
        token=signed["token"],
    )
    return ok(out.model_dump(by_alias=True, mode="json"))


@router.post("/posts")
def create_artist_post(
    body: CreateArtistPostBody,
    user: User = Depends(require_user),
    session: Session = Depends(get_session),
):
    _require_artist(user)

    # The author is ALWAYS the authenticated artist — never read from the body, so it can't be
    # spoofed. image_url/caption/linked_track_id come from the (already validated) request.
    post = ArtistPost(
        artist_user_id=user.id,
        image_url=body.image_url,
        caption=body.caption,
        linked_track_id=body.linked_track_id,
    )
    session.add(post)
    session.commit()
    session.refresh(post)

    out = ArtistPostOut(
        id=post.id,
        artist_user_id=post.artist_user_id,
        image_url=post.image_url,
        caption=post.caption,
        linked_track_id=post.linked_track_id,
        created_at=post.created_at,
    )
    # 201 Created is the standard "a new thing was made" status.
    return ok(out.model_dump(by_alias=True, mode="json"), status=201)
