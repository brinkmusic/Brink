# WHAT THIS FILE IS
# Tests for T31's Kaggle ingest (analytics/ingest_kaggle.py): the bronze landing of
# the raw CSV + the silver join that fills in audio features on Track rows we
# already know about. We use a tiny CSV built on the fly (not the real ~114k
# dataset, which is gitignored and won't exist on another machine or in CI) and
# two disposable Track rows created just for this test, so the suite never
# rewrites real listening data in brink-dev.

import csv
import os
import uuid
from pathlib import Path

import pytest
from sqlalchemy import text

from db import get_engine
from ingest_kaggle import run_ingest

# The exact columns of the real Kaggle CSV (SpotifyAudioFeaturesApril2019.csv) —
# ingest_kaggle.py only reads the ones Track has columns for; the rest are
# preserved as-is in the bronze raw landing.
_CSV_FIELDS = [
    "artist_name", "track_id", "track_name", "acousticness", "danceability",
    "duration_ms", "energy", "instrumentalness", "key", "liveness", "loudness",
    "mode", "speechiness", "tempo", "time_signature", "valence", "popularity",
]


def _insert_track(conn, spotify_id: str) -> None:
    conn.execute(
        text(
            'INSERT INTO silver."Track" ("spotifyId", title, "artistName") '
            "VALUES (:id, :title, :artist)"
        ),
        {"id": spotify_id, "title": "Test Track", "artist": "Test Artist"},
    )


def _delete_track(conn, spotify_id: str) -> None:
    conn.execute(text('DELETE FROM silver."Track" WHERE "spotifyId" = :id'), {"id": spotify_id})


def _fetch_track(conn, spotify_id: str):
    return conn.execute(
        text(
            'SELECT danceability, energy, valence, tempo, loudness, popularity, "kaggleMatched" '
            'FROM silver."Track" WHERE "spotifyId" = :id'
        ),
        {"id": spotify_id},
    ).one()


def _write_fixture_csv(path: Path, matched_id: str) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        writer.writerow({
            "artist_name": "Test Artist", "track_id": matched_id, "track_name": "Test Track",
            "acousticness": "0.5", "danceability": "0.7", "duration_ms": "200000",
            "energy": "0.6", "instrumentalness": "0.0", "key": "1", "liveness": "0.1",
            "loudness": "-6.5", "mode": "1", "speechiness": "0.05", "tempo": "120.0",
            "time_signature": "4", "valence": "0.8", "popularity": "42",
        })
        # A Kaggle row with no corresponding Track row — should land in bronze
        # but have nothing to join against.
        writer.writerow({
            "artist_name": "Nobody", "track_id": "kaggle_only_" + uuid.uuid4().hex,
            "track_name": "Unheard", "acousticness": "0.1", "danceability": "0.1",
            "duration_ms": "100000", "energy": "0.1", "instrumentalness": "0.9",
            "key": "0", "liveness": "0.1", "loudness": "-20.0", "mode": "0",
            "speechiness": "0.1", "tempo": "80.0", "time_signature": "4",
            "valence": "0.1", "popularity": "0",
        })


@pytest.mark.skipif(
    os.getenv("RUN_ANALYTICS_DB_TESTS") != "1",
    reason="live Supabase analytics DB check; set RUN_ANALYTICS_DB_TESTS=1 to run",
)
def test_join_sets_features_and_leaves_unmatched_alone(tmp_path):
    engine = get_engine()
    matched_id = "test_matched_" + uuid.uuid4().hex
    unmatched_id = "test_unmatched_" + uuid.uuid4().hex
    csv_path = tmp_path / "kaggle_sample.csv"
    _write_fixture_csv(csv_path, matched_id)

    with engine.begin() as conn:
        _insert_track(conn, matched_id)
        _insert_track(conn, unmatched_id)

    try:
        summary = run_ingest(csv_path, engine=engine)

        with engine.connect() as conn:
            matched_row = _fetch_track(conn, matched_id)
            unmatched_row = _fetch_track(conn, unmatched_id)

        assert matched_row.danceability == 0.7
        assert matched_row.energy == 0.6
        assert matched_row.valence == 0.8
        assert matched_row.tempo == 120.0
        assert matched_row.loudness == -6.5
        assert matched_row.popularity == 42
        assert matched_row.kaggleMatched is True

        # A Track that exists but has no row in the Kaggle CSV must stay
        # unmatched — the genre-only fallback for these is a separate ticket (T33).
        assert unmatched_row.kaggleMatched is False

        assert summary["matched"] >= 1
        assert summary["coverage_pct"] > 0

        # Coverage % is reported, not silently dropped (ADR-0004).
        assert isinstance(summary["coverage_pct"], float)
    finally:
        with engine.begin() as conn:
            _delete_track(conn, matched_id)
            _delete_track(conn, unmatched_id)


@pytest.mark.skipif(
    os.getenv("RUN_ANALYTICS_DB_TESTS") != "1",
    reason="live Supabase analytics DB check; set RUN_ANALYTICS_DB_TESTS=1 to run",
)
def test_ingest_is_idempotent(tmp_path):
    engine = get_engine()
    matched_id = "test_idempotent_" + uuid.uuid4().hex
    csv_path = tmp_path / "kaggle_sample.csv"
    _write_fixture_csv(csv_path, matched_id)

    with engine.begin() as conn:
        _insert_track(conn, matched_id)

    try:
        first = run_ingest(csv_path, engine=engine)
        second = run_ingest(csv_path, engine=engine)

        assert first == second

        with engine.connect() as conn:
            bronze_count = conn.execute(
                text("SELECT COUNT(*) FROM bronze.kaggle_tracks_raw")
            ).scalar()
        # Re-running must not accumulate duplicate raw rows — the bronze
        # landing table always mirrors just the latest ingest.
        assert bronze_count == 2
    finally:
        with engine.begin() as conn:
            _delete_track(conn, matched_id)
