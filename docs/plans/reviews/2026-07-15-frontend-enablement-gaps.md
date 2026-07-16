# Frontend Enablement Gap Audit — 2026-07-15

**Scope:** Read-only audit of the Brink app (FastAPI JSON API + Jinja2/HTMX frontend). Goal: find
backend capabilities the frontend doesn't let a user reach, dead UI links, and dead ends in the
core user journeys. No code was changed.

**Owner complaint being investigated:** "Backend features exist that the frontend doesn't let you
reach." Confirmed example: you can *follow* a user, but there is **no way to find one**.

**Headline:** The single biggest structural gap is that **there is no in-app navigation at all.**
`base.html` ships the public landing-page nav (brand + "Features"/"How it works" anchors + "Log in
with Spotify") to *every* page, logged in or not. As a result several shipped pages and features are
reachable only by hand-typing a URL, and there is no logout link anywhere.

---

## 1. API endpoint inventory (`backend/app/routers/`)

| Method + path | Auth | Router |
|---|---|---|
| `GET /` (home page) | public | pages.py |
| `GET /feed` (page) | login (redirect to `/auth/login`) | pages.py |
| `GET /u/{handle}` (profile page) | login | pages.py |
| `GET /artist` (page) | login | pages.py |
| `GET /auth/login` | public | auth.py |
| `GET /auth/callback` | public (OAuth) | auth.py |
| `GET /auth/logout` | public | auth.py |
| `POST /api/auth/capture-spotify` | login | auth.py |
| `GET /api/health` | public | health.py |
| `POST /api/posts` | login | posts.py |
| `GET /api/posts?userId=` | public | posts.py |
| `POST /api/posts/{id}/reactions` | login | reactions.py |
| `DELETE /api/posts/{id}/reactions` | login | reactions.py |
| `POST /api/posts/{id}/comments` | login | comments.py |
| `GET /api/posts/{id}/comments` | login | comments.py |
| `POST /api/follow/{userId}` | login | follow.py |
| `DELETE /api/follow/{userId}` | login | follow.py |
| `GET /api/feed` | login | feed.py |
| `GET /api/search?q=` (Spotify tracks) | login | search.py |
| `GET /api/me/now-playing` | login | now_playing.py |
| `POST /api/snapshot` | cron secret (`X-Cron-Secret`) | snapshot.py |
| `POST /api/artist/sign-upload` | artist-only | artist.py |
| `POST /api/artist/posts` | artist-only | artist.py |
| `POST /api/artist/posts/{id}/reactions` | login (any user) | artist.py |
| `DELETE /api/artist/posts/{id}/reactions` | login (any user) | artist.py |
| `POST /api/artist/posts/{id}/comments` | login (any user) | artist.py |
| `GET /api/artist/posts/{id}/comments` | login (any user) | artist.py |
| `GET /api/artist/posts/{id}/engagement` | artist owner-only | artist.py |

## 2. UI affordance inventory

**Pages:** `/`, `/feed`, `/u/{handle}`, `/artist` (all in `pages.py`).

**Every internal link in every template** (from `grep href`):
- `base.html`: `/` (brand), `#features`, `#how`, `/auth/login`
- `home.html`: `/auth/login` (x2), `#how`
- `feed.html`: `/u/{handle}` (feed author link) — the **only** discovery path to a profile
- `profile.html`: `/auth/login` (link-Spotify prompt)
- `profile_missing.html`: `/feed`

**Client-side fetches (`static/*.js`):**
- `composer.js` → `GET /api/search`, `POST /api/posts`
- `reactions.js` → `POST/DELETE /api/posts/{id}/reactions`
- `comments.js` → `GET/POST /api/posts/{id}/comments`
- `follow.js` → `POST/DELETE /api/follow/{userId}`
- `artist-upload.js` → `POST /api/artist/sign-upload`, `PUT` to Supabase, `POST /api/artist/posts`

**Not called by any JS or linked by any template:** `/auth/logout`, `/api/me/now-playing` (used
only server-side in profile render), all four **artist-post engagement** endpoints
(`/api/artist/posts/{id}/reactions|comments|engagement`).

## 3. Capability → UI matrix

| Backend capability | UI path that reaches it | Class |
|---|---|---|
| Log in (`/auth/login`) | Nav + home CTAs | FULLY ENABLED |
| Log out (`/auth/logout`) | **none** — no logout link anywhere | NOT ENABLED |
| View feed page (`/feed`) | Only via `/auth/callback` redirect or `profile_missing`; **not linked from nav or home** | PARTIALLY ENABLED |
| Compose/post a track (`/api/search`+`/api/posts`) | Composer card on `/feed` | FULLY ENABLED |
| React to a post | Reaction buttons on feed cards | FULLY ENABLED |
| Comment on a post | Comment panel on feed cards | FULLY ENABLED |
| View a user's profile (`/u/{handle}`) | Only via a feed author link | PARTIALLY ENABLED |
| **Find a user** (search / directory) | **none** — must hand-type `/u/{handle}` | NOT ENABLED |
| Follow / unfollow (`/api/follow`) | Follow button on profile | FULLY ENABLED (but see "find a user") |
| See who you follow / your followers | **none** — counts are plain text, not clickable; no list endpoint | NOT ENABLED |
| Listening summary / now-playing (own) | Rendered on own `/u/{handle}` | FULLY ENABLED (own profile only) |
| Now-playing for others / in feed (UI-10) | **none** (me-scoped endpoint only) | NOT ENABLED (known partial) |
| Artist upload (`/api/artist/*`) | Upload box on `/artist` | PARTIALLY ENABLED — `/artist` is unlinked (hand-type only) **and images are broken** (§5) |
| **View artist posts as audience** | **none** — `/artist` shows only YOUR OWN posts | NOT ENABLED |
| **Artist-post reactions/comments (T52)** | **none** — no template renders them | NOT ENABLED |
| **Artist-post engagement counts (T52, owner)** | **none** — no template renders it | NOT ENABLED |
| Compatibility / taste community (marketed on home) | **none** — not built (T14 deferred) | NOT ENABLED |

## 4. Reverse check — dead links / calls to nowhere

- No template links to a route that doesn't exist (no 404 hrefs). All `href`s resolve.
- No JS calls a missing endpoint.
- **But the reverse gap is severe:** shipped endpoints with *no* caller — `/auth/logout`, all four
  T52 artist-engagement endpoints. These are dead code from the UI's point of view.
- `base.html`'s own comment admits it: "later steps swap this for the in-app nav (Feed, Profile,
  ...) — those pages don't exist yet." They exist now; the nav was never updated.

## 5. Artist flow deep-dive (T51 + T52)

1. **No audience view of artist posts.** `pages.py::artist_page` queries
   `ArtistPost.artist_user_id == user.id` — it only ever shows the *logged-in user's own* posts.
   A fan visiting `/artist` sees the "Artist accounts only" empty state and **zero posts**. There
   is no page that lists other artists' posts, and no per-artist BTS page (e.g. `/artist/{handle}`).
2. **T52 engagement is 100% unreachable.** `add_artist_reaction`, `remove_artist_reaction`,
   `create_artist_comment`, `list_artist_comments`, `get_artist_post_engagement` all exist and are
   tested, but **no template renders reaction buttons, a comment panel, or engagement counts on an
   artist post.** `artist.html` renders only `image_url`, `caption`, and a timestamp.
3. **Broken image display (the known open question — CONFIRMED).** `artist-upload.js` sends the
   storage **path** (`<artistUserId>/<uuid>.jpg`) as `imageUrl`; `create_artist_post` stores it raw;
   `artist.html` renders `<img src="{{ post.image_url }}">`. That's a bare path against a **private**
   bucket (`artist-images`). There is **no signed-read-URL helper anywhere** (grep for
   `create_signed_url`/`get_public_url`/signed read → nothing). So even the artist's own uploaded
   images will not load. `security/supabase.py` only has `create_signed_upload_url` (write side).

## 6. Core-journey walk-through (new user)

1. Land on `/` → clear pitch, "Continue with Spotify". OK.
2. Log in → `/auth/callback` redirects to `/feed`. OK. **But if a returning logged-in user visits
   `/` again, there is no button to get back into the app** — the nav still says "Log in with
   Spotify" (which re-triggers OAuth) and nothing links to `/feed`.
3. Feed → compose, react, comment all work. OK.
4. **Find another user → DEAD END.** No search box, no directory, no "suggested users", no
   browse. The only way to reach a profile is to wait for that person to appear as a feed author —
   and you can't follow anyone until you already follow someone (chicken-and-egg). This is the
   owner's exact complaint.
5. View a profile → works if you got there via a feed link. Follow button works. **But
   follower/following counts aren't clickable**, so you can't traverse the social graph.
6. **Log out → DEAD END.** No logout affordance anywhere.
7. **Artist:** `/artist` is not linked from anything — an artist must know to type the URL. Upload
   works up to storage, but the resulting image won't render (§5.3), and no audience can see it.

## 7. Proposed minimal fixes (ranked, with backend-vs-frontend tag)

| # | Gap | Minimal fix | Needs backend? |
|---|---|---|---|
| 1 | **No user search / directory** (owner's complaint) | Add a search box in a real in-app nav that hits a **new** `GET /api/users/search?q=` (matches handle/display_name). Note: `/api/search` searches **Spotify tracks**, not users — it cannot be reused. | **Yes — new endpoint** + template/JS |
| 2 | No in-app nav / no logout / `/feed` & `/artist` unreachable | Add an authenticated nav (Feed, Profile, Artist-if-artist, Log out) to `base.html`. Requires the templates to know if the viewer is logged in — thread a `viewer` into the page context. | Frontend-mostly (pass `viewer` from existing page routes; no new endpoint) |
| 3 | **Artist images broken** (private bucket, no signed read) | Add a signed-read helper + serve/return signed URLs when rendering artist posts (or make the bucket public-read if acceptable per ADR-0007/0008). | **Yes — new backend (signed read)** |
| 4 | **No audience view of artist posts** | New page/route listing artist posts to fans (e.g. `/artist/{handle}` or a global BTS feed) instead of own-only. | **Yes — new page route** (query change) + template |
| 5 | **T52 artist engagement unreachable** | Render reaction buttons + comment panel on artist post cards (reuse reactions.js/comments.js patterns against `/api/artist/posts/...`); show owner engagement counts. Depends on #4 existing first. | Frontend (JS/template) — endpoints exist |
| 6 | Can't traverse social graph (followers/following) | Make profile counts link to follower/following lists. | **Yes — new list endpoint** + template |
| 7 | Home markets compatibility / taste community that doesn't exist | Either build (blocked on T14 analytics) or soften the landing copy so it doesn't promise unshipped features. | Copy-only (frontend) or blocked ticket |
| 8 | Feed/other-user now-playing (UI-10) | Known partial; needs a per-user now-playing endpoint. | **Yes — new endpoint** |
