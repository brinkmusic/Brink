# WHAT THIS FILE IS
# Checks the upsert_track helper (app/tracks.py): "if we already know this song, update
# its details; if not, add it." Uses a real in-memory SQLite database (the db_session
# fixture) because the whole point of an upsert is real database behavior — a MagicMock
# would happily "succeed" on both paths and prove nothing.

from sqlmodel import select

from app.models import Track
from app.schemas import TrackIn
from app.tracks import upsert_track


def _meta(**overrides):
    base = dict(spotify_id="spot-1", title="Mystery of Love", artist_name="Sufjan Stevens",
                album_art_url="http://img/a.png", popularity=42)
    base.update(overrides)
    return TrackIn(**base)


# A song we've never seen before is inserted as a new Track row.
def test_upsert_inserts_new_track(db_session):
    track = upsert_track(db_session, _meta())
    db_session.commit()

    assert isinstance(track, Track)
    assert track.spotify_id == "spot-1"
    assert track.title == "Mystery of Love"
    assert db_session.get(Track, "spot-1") is not None


# Upserting the same spotify_id updates the existing row in place — no duplicate is created.
def test_upsert_updates_existing_track_without_duplicating(db_session):
    upsert_track(db_session, _meta(title="Old Title", popularity=1))
    db_session.commit()

    upsert_track(db_session, _meta(title="New Title", popularity=99))
    db_session.commit()

    row = db_session.get(Track, "spot-1")
    assert row.title == "New Title"       # updated in place
    assert row.popularity == 99
    # Still exactly one row for this id.
    assert len(db_session.exec(select(Track)).all()) == 1
