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
from typing import Optional

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

from app.models import PostSource


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
