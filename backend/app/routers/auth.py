# WHAT THIS FILE IS
# The endpoint the browser calls right after a user logs in with Spotify:
#   POST /api/auth/capture-spotify
# Supabase hands the browser the Spotify tokens once (just after login). The browser
# forwards them here, and we store them ENCRYPTED so a background job can later use
# them to fetch the user's listening history. Ported 1:1 from api/auth/capture-spotify.ts.

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlmodel import Session

from app.db import get_session
from app.deps import require_user
from app.models import SpotifyToken, User
from app.responses import fail, ok
from app.security.crypto import encrypt

router = APIRouter()


# The expected request body. All optional so we can return our own clear 400 below
# when a token is missing, rather than a generic validation error.
class CaptureBody(BaseModel):
    access_token: Optional[str] = None
    refresh_token: Optional[str] = None
    scopes: Optional[str] = None


@router.post("/api/auth/capture-spotify")
def capture_spotify(
    body: CaptureBody,
    user: User = Depends(require_user),  # ensures the caller is logged in; gives us their record
    session: Session = Depends(get_session),
):
    # Both tokens are required. WHY check here (not via the model): we want the exact
    # same 400 + message the old backend returned.
    if not body.refresh_token or not body.access_token:
        return fail("missing spotify tokens", 400)

    # Spotify access tokens last ~1 hour. Store an expiry as a plain UTC timestamp to
    # match how the existing rows (written by the old backend) were saved.
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)

    # "Upsert": update the user's token row if it exists, otherwise create it. The row
    # is keyed by user id, and both tokens are encrypted before saving.
    row = session.get(SpotifyToken, user.id)
    if row is None:
        row = SpotifyToken(user_id=user.id)
        session.add(row)
    row.access_token = encrypt(body.access_token)
    row.refresh_token = encrypt(body.refresh_token)
    row.expires_at = expires_at
    row.scopes = body.scopes or ""

    session.commit()
    return ok({"captured": True})
