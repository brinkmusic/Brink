# WHAT THIS FILE IS
# One small helper: upsert_track. "Upsert" = update-or-insert. Before a post can link to a
# song, that song must exist in our Track table. This ensures it does: if we already have the
# song (matched by its Spotify id), we refresh its details; if not, we add it. WHY separate
# from the posts endpoint: other features that "see" a track (e.g. the snapshot job, T21) will
# reuse the exact same logic (spec requirement SP-3: upsert tracks whenever seen).

from sqlmodel import Session

from app.models import Track
from app.schemas import TrackIn


def upsert_track(session: Session, meta: TrackIn) -> Track:
    # A Track's primary key IS its Spotify id, so we look it up directly by that id.
    track = session.get(Track, meta.spotify_id)
    if track is None:
        # Never seen this song: create the row.
        track = Track(
            spotify_id=meta.spotify_id,
            title=meta.title,
            artist_name=meta.artist_name,
            album_art_url=meta.album_art_url,
            popularity=meta.popularity,
        )
        session.add(track)
    else:
        # Seen it before: refresh the details we were given (they may have changed).
        track.title = meta.title
        track.artist_name = meta.artist_name
        track.album_art_url = meta.album_art_url
        track.popularity = meta.popularity
    # NOTE: we do not commit here — the caller commits, so creating the post and upserting
    # its track happen together as one unit of work.
    return track
