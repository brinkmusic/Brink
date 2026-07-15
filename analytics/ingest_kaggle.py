# WHAT THIS FILE IS
# T31: loads a Kaggle audio-features CSV into two layers (ADR-0009 medallion):
#   - bronze.kaggle_tracks_raw — every CSV row landed as-is (raw JSON), so the
#     original source data is preserved even if our join logic changes later.
#     Each run replaces the table's contents (delete-then-insert), so re-running
#     never piles up duplicate raw rows.
#   - silver.Track — for tracks we already know about (from real Spotify plays/
#     posts, T21/T10), look up their Kaggle audio features by spotifyId ==
#     Kaggle's track_id and fill in danceability/energy/valence/tempo/loudness/
#     popularity + set kaggleMatched=True. A Track with no Kaggle match is left
#     alone (kaggleMatched keeps its default False) — the fallback for those is
#     a separate ticket (T33), not this file's job.
# WHY coverage is logged: ADR-0004 says match coverage must be reported, not
# hidden, since the Kaggle set never covers every real-world track.
#
# Run it directly against a downloaded CSV: `uv run python ingest_kaggle.py <path>`.

import csv
import json
import sys
import uuid
from pathlib import Path
from typing import Optional

from sqlalchemy import Engine, text

from db import get_engine

# The Track columns we fill in from a Kaggle row, and the Kaggle column each
# one comes from.
_FEATURE_COLUMNS = {
    "danceability": "danceability",
    "energy": "energy",
    "valence": "valence",
    "tempo": "tempo",
    "loudness": "loudness",
    "popularity": "popularity",
}


def _read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _dedupe_by_track_id(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    # Some Kaggle exports repeat a track_id (e.g. re-released singles); keep
    # the first occurrence so the join is deterministic.
    by_id: dict[str, dict[str, str]] = {}
    for row in rows:
        by_id.setdefault(row["track_id"], row)
    return by_id


def _land_bronze(engine: Engine, rows: list[dict[str, str]]) -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM bronze.kaggle_tracks_raw"))
        if not rows:
            return
        conn.execute(
            text(
                "INSERT INTO bronze.kaggle_tracks_raw (id, payload) "
                "VALUES (:id, CAST(:payload AS JSONB))"
            ),
            [{"id": uuid.uuid4().hex, "payload": json.dumps(row)} for row in rows],
        )


def _join_silver(engine: Engine, kaggle_by_id: dict[str, dict[str, str]]) -> dict[str, float]:
    with engine.begin() as conn:
        track_ids = [
            row[0]
            for row in conn.execute(text('SELECT "spotifyId" FROM silver."Track"')).fetchall()
        ]
        total_tracks = len(track_ids)

        matches = [
            {
                "id": track_id,
                "danceability": float(kaggle_row["danceability"]),
                "energy": float(kaggle_row["energy"]),
                "valence": float(kaggle_row["valence"]),
                "tempo": float(kaggle_row["tempo"]),
                "loudness": float(kaggle_row["loudness"]),
                "popularity": int(kaggle_row["popularity"]),
            }
            for track_id in track_ids
            if (kaggle_row := kaggle_by_id.get(track_id)) is not None
        ]

        if matches:
            conn.execute(
                text(
                    'UPDATE silver."Track" SET '
                    "danceability = :danceability, energy = :energy, valence = :valence, "
                    'tempo = :tempo, loudness = :loudness, popularity = :popularity, '
                    '"kaggleMatched" = true '
                    'WHERE "spotifyId" = :id'
                ),
                matches,
            )

    matched = len(matches)
    coverage_pct = (matched / total_tracks * 100) if total_tracks else 0.0
    return {"total_tracks": total_tracks, "matched": matched, "coverage_pct": coverage_pct}


def run_ingest(csv_path: Path | str, engine: Optional[Engine] = None) -> dict[str, float]:
    engine = engine or get_engine()
    rows = _read_csv_rows(Path(csv_path))
    _land_bronze(engine, rows)
    summary = _join_silver(engine, _dedupe_by_track_id(rows))
    print(
        f"Kaggle match coverage: {summary['matched']}/{summary['total_tracks']} "
        f"({summary['coverage_pct']:.1f}%)"
    )
    return summary


if __name__ == "__main__":
    run_ingest(sys.argv[1])
