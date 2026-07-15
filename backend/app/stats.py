# WHAT THIS FILE IS
# The "what does this person actually listen to?" number-cruncher (T44). Given a user, it reads
# their listening history (the `Play` rows the snapshot job lands, T21) and returns a compact
# summary for the profile page: their most-played tracks, most-played artists, most recent
# listens, how many plays in the last 30 days, and their current day-by-day listening streak.
#
# WHY it's computed here, on demand, every time (ADR-0003): we deliberately DON'T keep a
# pre-calculated "stats" table that could go stale — we add these up straight from `Play` when a
# profile is viewed. A user's play history is small, so this is cheap.
#
# PORTABILITY NOTE: the counts and "recent" list are plain SQL group-by / order-by, which work the
# same on our test database (SQLite) and production (Postgres). The streak is the one thing we work
# out in Python instead of SQL, because "which calendar day did this play fall on?" is written
# differently in SQLite vs Postgres — doing it in Python keeps one behaviour for both.

from datetime import datetime, timedelta, timezone

from sqlalchemy import func
from sqlmodel import Session, select

from app.models import Play, Track

# How many rows we show in each list on the profile. Small on purpose — this is a summary.
TOP_LIMIT = 5
RECENT_LIMIT = 8
# "Recent activity" window for the play count, in days.
WINDOW_DAYS = 30


def _now_naive() -> datetime:
    # Current UTC time WITHOUT a timezone attached. WHY naive: the snapshot stores each play's
    # `playedAt` as naive UTC, so our cutoff has to be naive too or the comparison fails/ is skewed.
    return datetime.now(timezone.utc).replace(tzinfo=None)


def listening_summary(session: Session, user_id: str) -> dict:
    # Assemble the whole summary for one user. Every piece degrades to empty/zero on its own when
    # the user has no plays, so a brand-new or handle-only account renders fine (never an error).
    return {
        "top_tracks": _top_tracks(session, user_id),
        "top_artists": _top_artists(session, user_id),
        "recent": _recent(session, user_id),
        "plays_30d": _plays_in_window(session, user_id),
        "streak": _streak(session, user_id),
    }


def _top_tracks(session: Session, user_id: str) -> list[dict]:
    # Most-played tracks. We join each Play to its Track (for the title/artist/art), group by the
    # track, and count the plays; `.desc()` puts the most-played first, with title as a stable
    # tie-breaker so equal counts always come back in the same order.
    rows = session.exec(
        select(
            Track.title,
            Track.artist_name,
            Track.album_art_url,
            func.count(Play.id).label("plays"),
        )
        .join(Track, Track.spotify_id == Play.track_id)
        .where(Play.user_id == user_id)
        .group_by(Track.spotify_id, Track.title, Track.artist_name, Track.album_art_url)
        .order_by(func.count(Play.id).desc(), Track.title)
        .limit(TOP_LIMIT)
    ).all()
    return [
        {"title": title, "artist": artist, "album_art": art, "plays": plays}
        for title, artist, art, plays in rows
    ]


def _top_artists(session: Session, user_id: str) -> list[dict]:
    # Most-played artists. Same idea as top tracks, but grouped by artist name so two different
    # songs by the same artist add up into a single row.
    rows = session.exec(
        select(Track.artist_name, func.count(Play.id).label("plays"))
        .join(Track, Track.spotify_id == Play.track_id)
        .where(Play.user_id == user_id)
        .group_by(Track.artist_name)
        .order_by(func.count(Play.id).desc(), Track.artist_name)
        .limit(TOP_LIMIT)
    ).all()
    return [{"name": name, "plays": plays} for name, plays in rows]


def _recent(session: Session, user_id: str) -> list[dict]:
    # The latest handful of plays, newest first. `played_at` is returned raw (a datetime) so the
    # page can format it however it likes ("3h ago"); keeping formatting out of here keeps this
    # file pure and easy to test.
    rows = session.exec(
        select(Track.title, Track.artist_name, Track.album_art_url, Play.played_at)
        .join(Track, Track.spotify_id == Play.track_id)
        .where(Play.user_id == user_id)
        .order_by(Play.played_at.desc())
        .limit(RECENT_LIMIT)
    ).all()
    return [
        {"title": title, "artist": artist, "album_art": art, "played_at": played_at}
        for title, artist, art, played_at in rows
    ]


def _plays_in_window(session: Session, user_id: str) -> int:
    # How many plays in the last WINDOW_DAYS days. A single COUNT with a date filter.
    cutoff = _now_naive() - timedelta(days=WINDOW_DAYS)
    return session.exec(
        select(func.count(Play.id)).where(
            Play.user_id == user_id, Play.played_at >= cutoff
        )
    ).one()


def _streak(session: Session, user_id: str) -> int:
    # The listening streak: how many calendar days in a row — counting back from the user's most
    # recent play — have at least one play. We pull the play timestamps, reduce them to the set of
    # distinct days, then walk from newest to oldest counting consecutive days until we hit a gap.
    timestamps = session.exec(
        select(Play.played_at).where(Play.user_id == user_id).order_by(Play.played_at.desc())
    ).all()
    if not timestamps:
        return 0

    # Distinct calendar days, newest first. A set removes multiple plays on the same day.
    days = sorted({ts.date() for ts in timestamps}, reverse=True)

    streak = 1
    # Compare each day to the next-oldest: exactly one day apart extends the streak; anything
    # more is a gap, which ends it.
    for newer, older in zip(days, days[1:]):
        if (newer - older).days == 1:
            streak += 1
        else:
            break
    return streak
