# WHAT THIS FILE IS
# Tests for app/stats.py (T44): the live listening-summary aggregation over a user's Play
# history (top tracks, top artists, recent listens, 30-day play total, listening streak).
# These are pure read helpers computed on demand (ADR-0003, no UserStats table), so the tests
# drive a real in-memory SQLite DB (the shared db_session fixture, foreign keys ON) and assert
# on the numbers. WHY a real DB not a mock: the correctness IS the SQL group-by / ordering, which
# a MagicMock can't reproduce (see conftest's NOTE FOR T10+).

from datetime import datetime, timedelta, timezone

from app.models import Play, Track, User
from app.stats import listening_summary


def _now():
    # Naive UTC "now" — matches how Play.playedAt is stored (the snapshot writes naive UTC), so
    # the 30-day cutoff and streak day-math line up with the seeded rows.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _seed_user(session, uid="u1"):
    session.add(User(id=uid, handle=uid, display_name=uid, created_at=datetime.now(timezone.utc)))
    session.commit()


def _seed_track(session, spotify_id, title, artist):
    # Track must exist BEFORE any Play references it (foreign keys are enforced in this fixture).
    session.add(Track(spotify_id=spotify_id, title=title, artist_name=artist))
    session.commit()


def _play(session, uid, track_id, when):
    session.add(Play(user_id=uid, track_id=track_id, played_at=when))
    session.commit()


def test_empty_user_returns_zeroed_summary(db_session):
    # A user with no plays must degrade to empty lists / zeros — never crash (ADR-0007).
    _seed_user(db_session)
    s = listening_summary(db_session, "u1")
    assert s["top_tracks"] == []
    assert s["top_artists"] == []
    assert s["recent"] == []
    assert s["plays_30d"] == 0
    assert s["streak"] == 0


def test_top_tracks_ranked_by_play_count(db_session):
    _seed_user(db_session)
    _seed_track(db_session, "t_a", "Alpha", "Artist One")
    _seed_track(db_session, "t_b", "Bravo", "Artist Two")
    now = _now()
    # Alpha played 3x, Bravo played 1x -> Alpha ranks first.
    for i in range(3):
        _play(db_session, "u1", "t_a", now - timedelta(hours=i))
    _play(db_session, "u1", "t_b", now - timedelta(hours=5))

    s = listening_summary(db_session, "u1")
    assert [t["title"] for t in s["top_tracks"]] == ["Alpha", "Bravo"]
    assert s["top_tracks"][0]["plays"] == 3
    assert s["top_tracks"][0]["artist"] == "Artist One"


def test_top_artists_aggregate_across_tracks(db_session):
    # Two different tracks by the same artist should sum into one artist row.
    _seed_user(db_session)
    _seed_track(db_session, "t_a", "Alpha", "Solo")
    _seed_track(db_session, "t_b", "Bravo", "Solo")
    _seed_track(db_session, "t_c", "Charlie", "Other")
    now = _now()
    _play(db_session, "u1", "t_a", now - timedelta(hours=1))
    _play(db_session, "u1", "t_b", now - timedelta(hours=2))
    _play(db_session, "u1", "t_c", now - timedelta(hours=3))

    s = listening_summary(db_session, "u1")
    assert s["top_artists"][0]["name"] == "Solo"
    assert s["top_artists"][0]["plays"] == 2


def test_recent_listens_newest_first(db_session):
    _seed_user(db_session)
    _seed_track(db_session, "t_a", "Older", "A")
    _seed_track(db_session, "t_b", "Newer", "B")
    now = _now()
    _play(db_session, "u1", "t_a", now - timedelta(hours=3))
    _play(db_session, "u1", "t_b", now - timedelta(minutes=5))

    s = listening_summary(db_session, "u1")
    assert [r["title"] for r in s["recent"]] == ["Newer", "Older"]


def test_plays_30d_excludes_older_plays(db_session):
    _seed_user(db_session)
    _seed_track(db_session, "t_a", "Alpha", "A")
    now = _now()
    _play(db_session, "u1", "t_a", now - timedelta(days=1))    # in window
    _play(db_session, "u1", "t_a", now - timedelta(days=10))   # in window
    _play(db_session, "u1", "t_a", now - timedelta(days=40))   # outside 30 days

    s = listening_summary(db_session, "u1")
    assert s["plays_30d"] == 2


def test_streak_counts_consecutive_days_from_most_recent(db_session):
    # Plays on three consecutive days -> streak 3; a play 5 days back does NOT extend it (gap).
    _seed_user(db_session)
    _seed_track(db_session, "t_a", "Alpha", "A")
    now = _now()
    for d in (0, 1, 2):
        _play(db_session, "u1", "t_a", now - timedelta(days=d))
    _play(db_session, "u1", "t_a", now - timedelta(days=5))

    s = listening_summary(db_session, "u1")
    assert s["streak"] == 3


def test_summary_is_scoped_to_the_user(db_session):
    # Another user's plays must not leak into this user's summary.
    _seed_user(db_session, "u1")
    _seed_user(db_session, "u2")
    _seed_track(db_session, "t_a", "Alpha", "A")
    now = _now()
    _play(db_session, "u2", "t_a", now - timedelta(hours=1))

    s = listening_summary(db_session, "u1")
    assert s["plays_30d"] == 0
    assert s["top_tracks"] == []
