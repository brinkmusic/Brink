# WHAT THIS FILE IS
# The scheduled play-snapshot endpoint (T21):
#   POST /api/snapshot -> for every Spotify-linked user, pull their recently-played tracks and
#                         record them, so 30-day stats / streaks are based on real history (Spotify
#                         only ever returns the last 50 plays, so we must capture them on a cadence).
# It is NOT a user endpoint — it's triggered by a GitHub Actions cron (see
# .github/workflows/snapshot.yml) and authenticated by a shared secret in the `X-Cron-Secret`
# header (the endpoint is a public URL on Render).
#
# The flow follows the medallion layering (ADR-0009): first LAND the raw Spotify response into
# `bronze.spotify_recently_played_raw` (append-only, untouched), then CONFORM it into the silver
# tables — upsert each `Track` and insert a `Play` row, deduplicated on (userId, playedAt) so a
# double-run never double-counts.

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header
from sqlmodel import Session, select

from app.config import get_settings
from app.db import get_session
from app.models import Play, SpotifyRecentlyPlayedRaw, SpotifyToken, Track, User
from app.responses import fail, ok
from app.schemas import TrackIn
from app.spotify import get_recently_played
from app.tracks import upsert_track

logger = logging.getLogger(__name__)

router = APIRouter(tags=["snapshot"])


# Turn one Spotify "track" object into the TrackIn our upsert helper expects (same normalization
# the now-playing endpoint uses: join multiple artists, take the first album image).
def _track_meta(track: dict) -> TrackIn:
    artist_name = ", ".join(a.get("name", "") for a in track.get("artists", []))
    images = track.get("album", {}).get("images", [])
    return TrackIn(
        spotify_id=track["id"],
        title=track["name"],
        artist_name=artist_name,
        album_art_url=images[0]["url"] if images else None,
        popularity=track.get("popularity"),
    )


# Parse Spotify's ISO-8601 timestamp (e.g. "2026-07-08T20:00:00.000Z") into the naive-UTC datetime
# our Play.playedAt column stores. Returns None for an unparseable value so one bad row is skipped.
def _parse_played_at(value: str) -> Optional[datetime]:
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError, TypeError):
        return None
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


# Land the raw payload (bronze) + conform it into Track/Play (silver) for one user. Returns how many
# new Play rows were inserted. Dedup: we only insert plays whose playedAt isn't already stored for
# this user (the (userId, playedAt) unique index would otherwise reject them).
def _ingest_user(session: Session, user_id: str, payload: dict) -> int:
    # Bronze: keep the raw response verbatim, append-only.
    session.add(SpotifyRecentlyPlayedRaw(user_id=user_id, payload=payload))

    # Parse the items into (playedAt, track-metadata) pairs, dropping anything unparseable.
    parsed = []
    for item in payload.get("items", []):
        played_at = _parse_played_at(item.get("played_at"))
        track = item.get("track")
        if played_at is None or not track or not track.get("id"):
            continue
        parsed.append((played_at, track))
    if not parsed:
        return 0

    # Which of these plays do we already have for this user? One query, not one per row.
    candidate_times = [p[0] for p in parsed]
    existing = set(session.exec(
        select(Play.played_at).where(
            Play.user_id == user_id, Play.played_at.in_(candidate_times)
        )
    ).all())

    inserted = 0
    seen: set[datetime] = set()  # also guard against duplicates within this same batch
    for played_at, track in parsed:
        if played_at in existing or played_at in seen:
            continue
        upsert_track(session, _track_meta(track))         # silver: ensure the song exists
        # Write the Track to the database NOW, before we add the Play that points at it. WHY:
        # Play.trackId is a foreign key to Track.spotifyId — Postgres rejects a Play whose Track
        # doesn't yet physically exist. Without this flush, both the new Track and its Play sit
        # unwritten until a later query triggers an automatic flush, and that flush is not
        # guaranteed to insert the Track before the Play across this batched loop → a
        # ForeignKeyViolation (the T23 snapshot-500). flush() sends the pending Track (and the
        # bronze row) to the DB inside the same transaction; the per-user commit still happens
        # once, below, so nothing is half-committed if a later user errors.
        session.flush()
        session.add(Play(user_id=user_id, track_id=track["id"], played_at=played_at))
        seen.add(played_at)
        inserted += 1
    return inserted


@router.post("/api/snapshot")
def run_snapshot(
    x_cron_secret: Optional[str] = Header(default=None),
    session: Session = Depends(get_session),
):
    # Authenticate the trigger: the request must carry the shared secret. If the secret isn't even
    # configured, refuse everything (fail closed) rather than run wide open.
    expected = get_settings().cron_secret
    if not expected or x_cron_secret != expected:
        return fail("unauthorized", 401)

    # Process only Spotify-linked users (those with a stored token); unlinked accounts have nothing
    # to snapshot. The join naturally skips them.
    users = session.exec(select(User).join(SpotifyToken, SpotifyToken.user_id == User.id)).all()

    processed = 0
    skipped = 0
    plays_inserted = 0
    for user in users:
        payload = get_recently_played(session, user.id)
        if payload is None:
            # No valid token / Spotify error for this user — skip them, keep going.
            skipped += 1
            continue
        plays_inserted += _ingest_user(session, user.id, payload)
        session.commit()  # commit per user so one user's failure can't undo another's
        processed += 1

    return ok({"usersProcessed": processed, "usersSkipped": skipped, "playsInserted": plays_inserted})
