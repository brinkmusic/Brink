# =============================================================================
# WHAT THIS FILE IS
# -----------------------------------------------------------------------------
# This is the "data model": the Python description of every table in our database.
# A database is just a set of spreadsheets ("tables"). Each table has columns
# (like spreadsheet headers) and rows (one row = one record, e.g. one user).
#
# Each `class` below describes ONE table. Each attribute inside a class describes
# ONE column. When the backend wants to read or save data, it uses these classes
# instead of writing raw database commands — safer and easier to read.
#
# WHY it looks the way it does: our database was originally created by a tool
# called Prisma, which named the tables in PascalCase ("User", "SpotifyToken")
# and the columns in camelCase ("displayName", "createdAt"). Real data already lives
# in those columns, so renaming them is a live-data migration we've deliberately
# deferred (see the T08 notes) — until then we keep the exact database names.
# But in Python we prefer snake_case ("display_name"), so each column below says
# both: the Python name we use in our code, and the real database name in quotes.
#
# HOW TO READ ONE LINE, e.g.:
#     display_name: str = Field(sa_column=Column("displayName", Text, nullable=False))
#   - display_name   -> the name WE use in Python code (user.display_name)
#   - : str          -> the kind of value it holds (str = text, int = whole number,
#                        float = decimal, bool = true/false, datetime = a timestamp)
#   - Column("displayName", ...) -> the real column name in the database
#   - Text           -> stored as text in the database
#   - nullable=False -> this column is REQUIRED (can't be left empty)
#   - Optional[...] / default=None / nullable=True -> the column is allowed to be empty
#
# A few recurring ideas, explained once here so the classes below stay short:
#   - primary_key=True : this column is the row's unique ID (its "fingerprint").
#   - ForeignKey / _fk(): a link from one table to another. Example: a Post has a
#     user_id that points at the User who made it. This is how tables connect.
#   - ondelete: what happens to the linked rows when the thing they point to is
#     deleted. "CASCADE" = delete them too (e.g. delete a user -> delete their
#     posts). "RESTRICT" = block the delete. "SET NULL" = keep the row but empty
#     the link.
#   - Index(..., unique=True): a rule that a value (or combination) can't repeat,
#     e.g. two users can't share the same handle.
#   - server_default: a value the database fills in automatically if we don't
#     provide one (e.g. createdAt defaults to "right now").
# =============================================================================

import enum
from datetime import datetime
from typing import Any, Optional

from cuid2 import Cuid
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum as SAEnum,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
)
from sqlalchemy import text as sa_text
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel

# Every row needs a unique ID string. cuid2 generates one (e.g. "xqvazr7u...").
# WHY cuid2: it's random and hard to guess. We create the ID in Python (not the
# database) so we know a new record's ID the moment we make it.
_cuid = Cuid()


def cuid() -> str:
    return _cuid.generate()


# An "enum" is a fixed list of the only allowed values for a column. WHY: a post's
# source can ONLY be one of these, so the database rejects anything else — no typos.
class PostSource(str, enum.Enum):
    MANUAL = "MANUAL"    # the user posted this song themselves
    SPOTIFY = "SPOTIFY"  # it came in automatically from their Spotify activity


# The only reactions someone can leave on a post.
class ReactionType(str, enum.Enum):
    HEART = "HEART"
    FIRE = "FIRE"
    SPARKLE = "SPARKLE"


# Shortcut used by most tables: an "id" column that is the unique ID (primary key)
# and auto-fills with a fresh cuid2 when a new row is created. Defined once here so
# we don't repeat it in every table below.
def _pk_cuid() -> Any:
    return Field(default_factory=cuid, sa_column=Column("id", Text, primary_key=True))


# Shortcut for building a "link to another table" column (a foreign key). WHY a
# helper: almost every link in our app updates automatically if an ID changes
# (onupdate="CASCADE"); only the "what happens on delete" part differs, so we pass
# that in each time and keep the rest identical.
def _fk(
    db_name: str,
    target: str,
    *,
    ondelete: str,
    nullable: bool = False,
    primary_key: bool = False,
) -> Column:
    return Column(
        db_name,
        Text,
        ForeignKey(target, ondelete=ondelete, onupdate="CASCADE"),
        nullable=nullable,
        primary_key=primary_key,
    )


# Shortcut for the "createdAt" timestamp column that most tables share: the database
# stamps it with the current time on insert (server_default CURRENT_TIMESTAMP). Defined
# once here so the five tables that use it don't each repeat the same four lines. Each
# call builds a FRESH Column (SQLAlchemy Columns can't be shared between tables).
def _created_at() -> Any:
    return Field(
        sa_column=Column(
            "createdAt", DateTime, nullable=False, server_default=sa_text("CURRENT_TIMESTAMP")
        )
    )


# A person on Brink. This is the central table — most others link back to it.
class User(SQLModel, table=True):
    __tablename__ = "User"  # the real table name in the database
    # These are "no duplicates allowed" rules: no two users can share the same
    # handle, email, Spotify ID, or Supabase login ID.
    __table_args__ = (
        Index("User_supabaseUserId_key", "supabaseUserId", unique=True),
        Index("User_handle_key", "handle", unique=True),
        Index("User_email_key", "email", unique=True),
        Index("User_spotifyId_key", "spotifyId", unique=True),
    )

    id: str = _pk_cuid()  # unique ID for this user
    # Links this Brink user to their login account in Supabase (our auth system).
    # Optional/nullable because seeded fake users don't have a real login.
    supabase_user_id: Optional[str] = Field(
        default=None, sa_column=Column("supabaseUserId", Text, nullable=True)
    )
    handle: str = Field(sa_column=Column("handle", Text, nullable=False))        # e.g. "@andrea"
    display_name: str = Field(sa_column=Column("displayName", Text, nullable=False))  # shown name
    email: Optional[str] = Field(default=None, sa_column=Column("email", Text, nullable=True))
    avatar_url: Optional[str] = Field(
        default=None, sa_column=Column("avatarUrl", Text, nullable=True)  # profile picture link
    )
    spotify_id: Optional[str] = Field(
        default=None, sa_column=Column("spotifyId", Text, nullable=True)
    )
    # is_synthetic: true for the fake users we generate to make the app feel alive.
    # server_default "false" means real sign-ups are marked false automatically.
    is_synthetic: bool = Field(
        default=False,
        sa_column=Column("isSynthetic", Boolean, nullable=False, server_default=sa_text("false")),
    )
    is_artist: bool = Field(
        default=False,
        sa_column=Column("isArtist", Boolean, nullable=False, server_default=sa_text("false")),
    )
    # When the account was created. The database fills this in with the current
    # time automatically (server_default CURRENT_TIMESTAMP).
    created_at: datetime = _created_at()
    # Which taste "cluster" this user was grouped into by the analytics job.
    # ondelete SET NULL: if a cluster is deleted, keep the user but clear this link.
    cluster_id: Optional[str] = Field(
        default=None, sa_column=_fk("clusterId", "Cluster.id", ondelete="SET NULL", nullable=True)
    )


# The Spotify access keys for one user, so the backend can talk to Spotify on
# their behalf. One row per user (user_id is both the ID and the link to User).
# The tokens themselves are encrypted before being stored here.
class SpotifyToken(SQLModel, table=True):
    __tablename__ = "SpotifyToken"

    # user_id is the primary key AND a link to User. ondelete CASCADE: if the user
    # is deleted, their stored tokens are deleted too.
    user_id: str = Field(sa_column=_fk("userId", "User.id", ondelete="CASCADE", primary_key=True))
    access_token: str = Field(sa_column=Column("accessToken", Text, nullable=False))
    refresh_token: str = Field(sa_column=Column("refreshToken", Text, nullable=False))
    expires_at: datetime = Field(sa_column=Column("expiresAt", DateTime, nullable=False))
    scopes: str = Field(sa_column=Column("scopes", Text, nullable=False))  # what we're allowed to do


# A song. Its ID is Spotify's own track ID (spotify_id). The lower fields are
# audio features (how danceable/energetic a song is) used by the analytics job;
# they're optional because we don't always have them.
class Track(SQLModel, table=True):
    __tablename__ = "Track"

    spotify_id: str = Field(sa_column=Column("spotifyId", Text, primary_key=True))
    title: str = Field(sa_column=Column("title", Text, nullable=False))
    artist_name: str = Field(sa_column=Column("artistName", Text, nullable=False))
    album_art_url: Optional[str] = Field(
        default=None, sa_column=Column("albumArtUrl", Text, nullable=True)
    )
    popularity: Optional[int] = Field(
        default=None, sa_column=Column("popularity", Integer, nullable=True)
    )
    danceability: Optional[float] = Field(
        default=None, sa_column=Column("danceability", Float, nullable=True)
    )
    energy: Optional[float] = Field(default=None, sa_column=Column("energy", Float, nullable=True))
    valence: Optional[float] = Field(default=None, sa_column=Column("valence", Float, nullable=True))
    tempo: Optional[float] = Field(default=None, sa_column=Column("tempo", Float, nullable=True))
    loudness: Optional[float] = Field(
        default=None, sa_column=Column("loudness", Float, nullable=True)
    )
    # kaggle_matched: whether we found this song's audio features in the Kaggle
    # dataset. Defaults to false until the matching job confirms it.
    kaggle_matched: bool = Field(
        default=False,
        sa_column=Column("kaggleMatched", Boolean, nullable=False, server_default=sa_text("false")),
    )


# A record that a user played a song at a certain time (their listening history).
class Play(SQLModel, table=True):
    __tablename__ = "Play"
    __table_args__ = (
        # No duplicates: the same user can't have two plays at the exact same time.
        # WHY: we take periodic snapshots from Spotify and this stops double-counting.
        Index("Play_userId_playedAt_key", "userId", "playedAt", unique=True),
        # A plain (non-unique) index just makes "find all plays for this user" fast.
        Index("Play_userId_idx", "userId"),
    )

    id: str = _pk_cuid()
    user_id: str = Field(sa_column=_fk("userId", "User.id", ondelete="CASCADE"))
    # ondelete RESTRICT: you can't delete a Track while plays still point to it.
    track_id: str = Field(sa_column=_fk("trackId", "Track.spotifyId", ondelete="RESTRICT"))
    played_at: datetime = Field(sa_column=Column("playedAt", DateTime, nullable=False))


# A post: a user sharing a song, optionally with a caption. Indexes make "posts by
# this user" and "newest posts first" (the feed) fast to load.
class Post(SQLModel, table=True):
    __tablename__ = "Post"
    __table_args__ = (
        Index("Post_userId_idx", "userId"),
        Index("Post_createdAt_idx", "createdAt"),
    )

    id: str = _pk_cuid()
    user_id: str = Field(sa_column=_fk("userId", "User.id", ondelete="CASCADE"))
    track_id: str = Field(sa_column=_fk("trackId", "Track.spotifyId", ondelete="RESTRICT"))
    caption: Optional[str] = Field(default=None, sa_column=Column("caption", Text, nullable=True))
    # Must be one of the PostSource values (MANUAL or SPOTIFY) — see the enum above.
    source: PostSource = Field(
        sa_column=Column("source", SAEnum(PostSource, name="PostSource"), nullable=False)
    )
    created_at: datetime = _created_at()


# A reaction (heart / fire / sparkle) that a user left on a post.
class Reaction(SQLModel, table=True):
    __tablename__ = "Reaction"
    __table_args__ = (
        # No duplicates: a user can't leave the SAME reaction type on the SAME post
        # twice. (They could leave a heart AND a fire — just not two hearts.)
        Index("Reaction_postId_userId_type_key", "postId", "userId", "type", unique=True),
    )

    id: str = _pk_cuid()
    post_id: str = Field(sa_column=_fk("postId", "Post.id", ondelete="CASCADE"))
    user_id: str = Field(sa_column=_fk("userId", "User.id", ondelete="CASCADE"))
    type: ReactionType = Field(
        sa_column=Column("type", SAEnum(ReactionType, name="ReactionType"), nullable=False)
    )


# A text comment a user left on a post.
class Comment(SQLModel, table=True):
    __tablename__ = "Comment"
    __table_args__ = (Index("Comment_postId_idx", "postId"),)  # speed up "comments on this post"

    id: str = _pk_cuid()
    post_id: str = Field(sa_column=_fk("postId", "Post.id", ondelete="CASCADE"))
    user_id: str = Field(sa_column=_fk("userId", "User.id", ondelete="CASCADE"))
    body: str = Field(sa_column=Column("body", Text, nullable=False))
    created_at: datetime = _created_at()


# "User A follows User B." Both columns together are the unique ID (you can't
# follow the same person twice). Both link to the User table.
class Follow(SQLModel, table=True):
    __tablename__ = "Follow"
    __table_args__ = (Index("Follow_followingId_idx", "followingId"),)  # "who follows this person"

    follower_id: str = Field(
        sa_column=_fk("followerId", "User.id", ondelete="CASCADE", primary_key=True)
    )
    following_id: str = Field(
        sa_column=_fk("followingId", "User.id", ondelete="CASCADE", primary_key=True)
    )
    created_at: datetime = _created_at()


# A post made by an artist account (a promotional image + caption, optionally
# tied to a song). Separate from normal Posts because it works differently.
class ArtistPost(SQLModel, table=True):
    __tablename__ = "ArtistPost"
    __table_args__ = (Index("ArtistPost_artistUserId_idx", "artistUserId"),)

    id: str = _pk_cuid()
    artist_user_id: str = Field(sa_column=_fk("artistUserId", "User.id", ondelete="CASCADE"))
    image_url: str = Field(sa_column=Column("imageUrl", Text, nullable=False))
    caption: str = Field(sa_column=Column("caption", Text, nullable=False))
    linked_track_id: Optional[str] = Field(
        default=None, sa_column=Column("linkedTrackId", Text, nullable=True)
    )
    created_at: datetime = _created_at()


# ---------------------------------------------------------------------------
# The tables below are RESULTS written by the Python analytics job (not by users).
# JSONB columns hold flexible structured data (lists/objects), like a mini
# document inside one cell — used where the shape varies (e.g. a list of top
# tracks). One row per user for the per-user stats tables.
# ---------------------------------------------------------------------------


# Pre-computed stats shown on a user's profile (their top tracks, streak, etc.).
class UserStats(SQLModel, table=True):
    __tablename__ = "UserStats"

    user_id: str = Field(sa_column=_fk("userId", "User.id", ondelete="CASCADE", primary_key=True))
    top_tracks: Any = Field(sa_column=Column("topTracks", JSONB, nullable=False))
    top_artists: Any = Field(sa_column=Column("topArtists", JSONB, nullable=False))
    top_genres: Any = Field(sa_column=Column("topGenres", JSONB, nullable=False))
    streak_days: int = Field(sa_column=Column("streakDays", Integer, nullable=False))
    total_plays_30d: int = Field(sa_column=Column("totalPlays30d", Integer, nullable=False))
    computed_at: datetime = Field(sa_column=Column("computedAt", DateTime, nullable=False))


# A user's "taste fingerprint" — a list of numbers summarizing their music taste,
# used to compare how similar two people are.
class TasteVector(SQLModel, table=True):
    __tablename__ = "TasteVector"

    user_id: str = Field(sa_column=_fk("userId", "User.id", ondelete="CASCADE", primary_key=True))
    vector: Any = Field(sa_column=Column("vector", JSONB, nullable=False))
    coverage: float = Field(sa_column=Column("coverage", Float, nullable=False))  # how complete it is
    computed_at: datetime = Field(sa_column=Column("computedAt", DateTime, nullable=False))


# A group of users with similar taste, produced by the clustering algorithm.
# (Note: id is set by the analytics job, so it has no auto cuid default here.)
class Cluster(SQLModel, table=True):
    __tablename__ = "Cluster"

    id: str = Field(sa_column=Column("id", Text, primary_key=True))
    label: str = Field(sa_column=Column("label", Text, nullable=False))          # human-friendly name
    centroid: Any = Field(sa_column=Column("centroid", JSONB, nullable=False))   # the group's "center"
    size: int = Field(sa_column=Column("size", Integer, nullable=False))         # how many users in it
    computed_at: datetime = Field(sa_column=Column("computedAt", DateTime, nullable=False))


# A similarity score between two users (0..1). Both user IDs together form the ID.
class Compatibility(SQLModel, table=True):
    __tablename__ = "Compatibility"
    __table_args__ = (Index("Compatibility_userAId_idx", "userAId"),)

    user_a_id: str = Field(sa_column=Column("userAId", Text, primary_key=True))
    user_b_id: str = Field(sa_column=Column("userBId", Text, primary_key=True))
    score: float = Field(sa_column=Column("score", Float, nullable=False))


# Quality metrics about the machine-learning models themselves (how well they did).
# One row per model, keyed by its name.
class ModelMetrics(SQLModel, table=True):
    __tablename__ = "ModelMetrics"
    # WHY this line: the tool we use (Pydantic) reserves names starting with
    # "model_", so we tell it to allow our "model_name" field without complaining.
    model_config = {"protected_namespaces": ()}

    model_name: str = Field(sa_column=Column("modelName", Text, primary_key=True))
    silhouette: Optional[float] = Field(
        default=None, sa_column=Column("silhouette", Float, nullable=True)
    )
    k: Optional[int] = Field(default=None, sa_column=Column("k", Integer, nullable=True))
    r2: Optional[float] = Field(default=None, sa_column=Column("r2", Float, nullable=True))
    rmse: Optional[float] = Field(default=None, sa_column=Column("rmse", Float, nullable=True))
    feature_importances: Optional[Any] = Field(
        default=None, sa_column=Column("featureImportances", JSONB, nullable=True)
    )
    computed_at: datetime = Field(sa_column=Column("computedAt", DateTime, nullable=False))
