# WHAT THIS FILE IS
# The shared "shapes" for data going IN to and OUT of the API. Requests are parsed into the
# *In classes (so a bad shape is rejected before any logic runs); responses are built as the
# *Out classes so we only ever send back the exact fields we intend — never a raw database
# row (which would leak internal column names and possibly secret columns). See ADR-0012.
#
# CASING: our database columns and the frontend both speak camelCase (trackId, albumArtUrl),
# but Python code prefers snake_case (track_id, album_art_url). CamelModel below bridges that:
# we write fields in snake_case, and they are read/written as camelCase JSON automatically.
# `populate_by_name=True` means requests may also send snake_case, so tests and internal
# callers aren't forced to use aliases.

from datetime import datetime
from typing import Annotated, Optional

from pydantic import BaseModel, ConfigDict, StringConstraints
from pydantic.alias_generators import to_camel

from app.models import PostSource, ReactionType


# The base every request/response shape inherits from. It turns snake_case Python field
# names into camelCase JSON (and back), so we define fields once in idiomatic Python.
class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# --- Requests ----------------------------------------------------------------------

# Track metadata supplied when creating a post. Required fields (no default) mean a missing
# title/artist/id is rejected as a 400 by the global validation handler — the strict-schema
# rule from ADR-0007 / ADR-0012 (do NOT make everything Optional like capture-spotify did).
class TrackIn(CamelModel):
    spotify_id: str
    title: str
    artist_name: str
    album_art_url: Optional[str] = None
    popularity: Optional[int] = None


# The body of POST /api/posts. `source` is the PostSource enum, so any value other than
# MANUAL/SPOTIFY is rejected as a 400. There is deliberately NO author/user field here:
# the author is always the authenticated caller, so it cannot be spoofed from the body.
class CreatePostBody(CamelModel):
    track: TrackIn
    source: PostSource
    caption: Optional[str] = None


# The body of POST/DELETE /api/posts/{id}/reactions. `type` is parsed against the
# ReactionType enum, so any value other than HEART/FIRE/SPARKLE is rejected as a 400.
# There is deliberately no user field: the reactor is always the authenticated caller.
class ReactionBody(CamelModel):
    type: ReactionType


# The comment text for POST /api/posts/{id}/comments. StringConstraints does the ADR-0007
# validation up front (the Comment table has no length limit of its own):
#   strip_whitespace -> leading/trailing spaces are removed before checking AND when stored,
#   min_length=1     -> a blank or whitespace-only body is rejected as a 400,
#   max_length=2000  -> an over-long body is rejected as a 400.
# There is deliberately no user field: the author is always the authenticated caller.
class CommentBody(CamelModel):
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]


# --- Responses ---------------------------------------------------------------------

# The linked-track part of a post response.
class TrackOut(CamelModel):
    spotify_id: str
    title: str
    artist_name: str
    album_art_url: Optional[str] = None
    popularity: Optional[int] = None


# A post as the API returns it: the post's own fields plus its linked track. Note this is an
# explicit allow-list — only these fields ever go out, regardless of what the table stores.
class PostOut(CamelModel):
    id: str
    user_id: str
    caption: Optional[str]
    source: PostSource
    created_at: datetime
    track: TrackOut


# What the reaction endpoints return: the post's id plus a count for EVERY reaction type
# (including zeros), so the frontend always gets the same stable shape to render badges from.
# `counts` is a plain map like {"HEART": 3, "FIRE": 1, "SPARKLE": 0}.
class ReactionCountsOut(CamelModel):
    post_id: str
    counts: dict[str, int]


# The public bits of a comment's author (never the whole User row — no email, ids, etc.).
class AuthorOut(CamelModel):
    display_name: str
    handle: str
    avatar_url: Optional[str] = None


# A comment as the API returns it: its own fields plus the nested author. Explicit allow-list.
class CommentOut(CamelModel):
    id: str
    body: str
    created_at: datetime
    author: AuthorOut


# What POST/DELETE /api/follow/{userId} return: the target's id and whether the caller now follows
# them (true after a follow, false after an unfollow). A tiny, explicit shape — never a raw row.
class FollowStateOut(CamelModel):
    following_id: str
    following: bool


# A single post as the feed returns it: the post's own fields + its track, plus the engagement
# numbers the feed shows. `reaction_counts` and `viewer_reactions` ALWAYS carry an entry for every
# reaction type (like ReactionCountsOut) so the frontend renders a stable set of badges:
#   reaction_counts  -> how many of each type the post has, e.g. {"HEART": 3, "FIRE": 0, ...}
#   viewer_reactions -> whether the CURRENT viewer left each type, e.g. {"HEART": true, ...}
#   comment_count    -> how many comments the post has.
class FeedPostOut(CamelModel):
    id: str
    user_id: str
    author: AuthorOut
    caption: Optional[str]
    source: PostSource
    created_at: datetime
    track: TrackOut
    reaction_counts: dict[str, int]
    comment_count: int
    viewer_reactions: dict[str, bool]
