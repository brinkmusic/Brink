# WHAT THIS FILE IS
# Automated checks for the data model in app/models.py. WHY: these run in CI on
# every change and fail loudly if a model drifts from what we expect (a missing
# table, a broken "no duplicates" rule, a wrong delete rule). A test named
# test_* is picked up and run automatically by pytest; `assert X` means "X must be
# true, or the test fails."

from sqlmodel import SQLModel

from app import models

# The exact set of tables we expect to exist. If a table is added or removed
# without updating this, the first test below fails on purpose.
EXPECTED_TABLES = {
    "User",
    "SpotifyToken",
    "Track",
    "Play",
    "Post",
    "Reaction",
    "Comment",
    "Follow",
    "ArtistPost",
    "UserStats",
    "TasteVector",
    "Cluster",
    "Compatibility",
    "ModelMetrics",
    "RateLimitHit",  # added in T10 for rate limiting (ADR-0011)
}


# All expected tables are present (no more, no fewer).
def test_all_expected_tables_registered():
    assert set(SQLModel.metadata.tables) == EXPECTED_TABLES


# The fixed value lists (enums) still match what the database expects.
def test_enums_preserve_prisma_values_and_type_names():
    assert [e.value for e in models.PostSource] == ["MANUAL", "SPOTIFY"]
    assert [e.value for e in models.ReactionType] == ["HEART", "FIRE", "SPARKLE"]
    assert models.Post.__table__.c.source.type.name == "PostSource"
    assert models.Reaction.__table__.c.type.type.name == "ReactionType"


# The "no duplicates" rules exist and are actually marked unique.
def test_unique_dedup_indexes():
    idx = {i.name: i for i in models.Reaction.__table__.indexes}
    assert idx["Reaction_postId_userId_type_key"].unique
    play_idx = {i.name: i for i in models.Play.__table__.indexes}
    assert play_idx["Play_userId_playedAt_key"].unique


# Tables whose ID is made of two columns together (e.g. follower + following).
def test_composite_primary_keys():
    assert {c.name for c in models.Follow.__table__.primary_key.columns} == {
        "followerId",
        "followingId",
    }
    assert {c.name for c in models.Compatibility.__table__.primary_key.columns} == {
        "userAId",
        "userBId",
    }


# The "what happens on delete" rules are set correctly for a few key links.
def test_cascade_and_restrict_delete_rules():
    def ondelete(attr):
        # Dig out the delete rule attached to a linking (foreign key) column.
        fk = next(iter(attr.property.columns[0].foreign_keys))
        return fk.ondelete

    assert ondelete(models.SpotifyToken.user_id) == "CASCADE"   # delete user -> delete their token
    assert ondelete(models.Play.track_id) == "RESTRICT"         # can't delete a song still in use
    assert ondelete(models.User.cluster_id) == "SET NULL"       # delete cluster -> clear the link


def test_snake_case_attrs_map_to_camelcase_columns():
    # The ORM attribute is snake_case; the actual DB column stays camelCase.
    assert models.User.display_name.property.columns[0].name == "displayName"
    assert models.UserStats.total_plays_30d.property.columns[0].name == "totalPlays30d"
