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
from typing import Annotated, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, StringConstraints
from pydantic.alias_generators import to_camel

from app.models import PostSource, ReactionType


# The base every request/response shape inherits from. It turns snake_case Python field
# names into camelCase JSON (and back), so we define fields once in idiomatic Python.
class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


# --- Requests ----------------------------------------------------------------------

# Track metadata supplied when creating a post. Required fields (no default) mean a missing
# title/artist/id is rejected as a 400 by the global validation handler — the strict-schema
# rule from ADR-0007 / ADR-0012 (required fields stay required; validation errors get envelopes).
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


# The body of POST /api/artist/sign-upload (T50). Both fields are the "technical validation"
# ADR-0007/ADR-0008 call for — enforced here so a bad request is a 400 before any logic runs
# (there is NO content/NSFW moderation, only these format/size checks):
#   content_type -> a Literal of exactly the two allowed image types, so anything else (gif,
#                   pdf, ...) is rejected as a 400. The frontend sends the file's MIME type.
#   size_bytes   -> the file's size; gt=0 rejects an empty/absent size and le=10 MiB caps it.
# There is deliberately no artistUserId field: the artist is always the authenticated caller.
class SignUploadBody(CamelModel):
    content_type: Literal["image/jpeg", "image/png"]
    size_bytes: Annotated[int, Field(gt=0, le=10 * 1024 * 1024)]


# The body of POST /api/artist/posts (T50). image_url is the object URL of the already-uploaded
# image (via the signed URL above); caption is required (the ArtistPost.caption column is NOT
# NULL); linked_track_id optionally ties the post to a song. No artistUserId here either — the
# author is always the authenticated caller, so it cannot be spoofed from the body.
class CreateArtistPostBody(CamelModel):
    image_url: str
    caption: str
    linked_track_id: Optional[str] = None


# The body of PATCH /api/me/profile (T48). `bio` is the user's short profile blurb.
# StringConstraints does the up-front ADR-0007 validation:
#   strip_whitespace -> surrounding spaces are trimmed before length-checking AND when stored,
#   max_length=300   -> an over-long bio is rejected as a 400.
# There is no min_length: an empty string is allowed and means "clear my bio" (the endpoint turns a
# now-empty value into NULL). No userId field — the profile edited is always the authenticated caller.
class UpdateProfileBody(CamelModel):
    bio: Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]


# The body of POST /api/me/avatar (T48): the storage `path` the browser just uploaded the new
# profile picture to (via the signed URL from /api/me/avatar/sign-upload). The endpoint verifies the
# path is inside the caller's own folder before turning it into the stored public avatar URL.
class AvatarSaveBody(CamelModel):
    path: str


# --- Responses ---------------------------------------------------------------------

# The linked-track part of a post response.
class TrackOut(CamelModel):
    spotify_id: str
    title: str
    artist_name: str
    album_art_url: Optional[str] = None
    popularity: Optional[int] = None


# What GET /api/me/now-playing returns: the currently-playing track plus whether it's actively
# playing (vs paused). Reuses TrackOut so a "now playing" card renders the same track fields as a
# post. The endpoint returns this OR null (nothing playing / no linked Spotify).
class NowPlayingOut(CamelModel):
    is_playing: bool
    track: TrackOut


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


# One user in the results of GET /api/users/search (T15): just enough to render a clickable
# result that links to /u/{handle} — an explicit allow-list, never the whole User row (no email,
# supabaseUserId, etc.). `is_artist` lets the search UI badge artist accounts.
class UserSearchOut(CamelModel):
    id: str
    handle: str
    display_name: str
    is_artist: bool


# What POST /api/me/become-artist returns: just the resulting artist state of the caller's own
# account (T55). A single allow-listed field so the browser can confirm the flip succeeded.
class ArtistStateOut(CamelModel):
    is_artist: bool


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


# One person in GET /api/posts/{id}/reactions' "who reacted" list (T96): the same public
# author fields as AuthorOut, plus every reaction type they left on the post (a user can
# leave up to one of EACH type, so `types` combines them, e.g. ["FIRE", "HEART"]).
class ReactorOut(CamelModel):
    display_name: str
    handle: str
    avatar_url: Optional[str] = None
    types: list[str]


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
    kind: Literal["song"] = "song"  # discriminator: a song-share post (vs an artist post below)
    user_id: str
    author: AuthorOut
    caption: Optional[str]
    source: PostSource
    created_at: datetime
    track: TrackOut
    reaction_counts: dict[str, int]
    comment_count: int
    viewer_reactions: dict[str, bool]
    # The post's NEWEST comments (capped at 3, chronological within that subset) so the feed
    # can show them inline without a click (T95). Always a list — empty when uncommented,
    # never null — a stable shape for the frontend. Reuses CommentOut (the same DTO the
    # comments API returns), so both surfaces expose identical, allow-listed fields.
    latest_comments: list[CommentOut] = []
    # Whoever reacted MOST RECENTLY (T96), or null when the post has no reactions — backs the
    # "Liked by X and N others" line. Reuses the public AuthorOut shape (no leaks).
    liked_by: Optional[AuthorOut] = None


# An artist "behind-the-scenes" post as the feed returns it (T049): a followed artist's promo image
# post, interleaved with the song posts above. It carries `kind == "artist"` so the template branches
# on it, and the SAME engagement fields (reaction_counts / comment_count / viewer_reactions) as a song
# post, computed over the ArtistReaction/ArtistComment tables (T52), so the artist card's like/comment
# controls render from a stable shape. `image_url` is the SIGNED read URL (the artist-images bucket is
# private), not the raw stored path. There's no track/source — an artist post is an image + caption.
class ArtistFeedPostOut(CamelModel):
    id: str
    kind: Literal["artist"] = "artist"
    author: AuthorOut
    caption: str
    image_url: str
    created_at: datetime
    reaction_counts: dict[str, int]
    comment_count: int
    viewer_reactions: dict[str, bool]
    # Same inline latest-comments shape as FeedPostOut above (T95), computed over the
    # mirrored ArtistComment table (T52).
    latest_comments: list[CommentOut] = []


# What POST /api/artist/sign-upload returns (T50): the pieces the browser needs to upload the
# file itself. `path` is the object's location in the bucket (also stored later as part of the
# image URL); `signed_url` + `token` are Supabase's single-use upload credentials.
class SignUploadOut(CamelModel):
    path: str
    signed_url: str
    token: str


# What PATCH /api/me/profile returns (T48): just the resulting bio (or null if cleared). A tiny
# allow-listed shape so the browser can confirm the save; the page reloads to re-render.
class ProfileBioOut(CamelModel):
    bio: Optional[str] = None


# What POST /api/me/avatar/sign-upload returns (T48): like SignUploadOut but for the PUBLIC avatars
# bucket, so it also carries `public_url` — the permanent, world-readable URL the object will have
# once uploaded, which POST /api/me/avatar stores on the user. `signed_url` + `token` are Supabase's
# single-use upload credentials; `path` is where the object lands.
class AvatarSignUploadOut(CamelModel):
    path: str
    signed_url: str
    token: str
    public_url: str


# What POST /api/me/avatar returns (T48): the resulting stored avatar URL of the caller's account.
class AvatarOut(CamelModel):
    avatar_url: Optional[str] = None


# An ArtistPost as the API returns it (T50): its own fields only, an explicit allow-list.
class ArtistPostOut(CamelModel):
    id: str
    artist_user_id: str
    image_url: str
    caption: str
    linked_track_id: Optional[str] = None
    created_at: datetime


# What GET /api/artist/posts/{id}/engagement returns to the OWNING artist (T52, MEDIA-4): how their
# post is performing. `reaction_counts` always carries an entry for every reaction type (zeros
# included), like ReactionCountsOut, so the artist page renders a stable set of badges; `comment_count`
# is how many comments the post has. (A view count is a deferred follow-up — there is no public
# artist-post read path to count views from yet; that surface is the artist UI, T51.)
class ArtistEngagementOut(CamelModel):
    post_id: str
    reaction_counts: dict[str, int]
    comment_count: int
