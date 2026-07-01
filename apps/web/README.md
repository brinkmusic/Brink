# apps/web — Brink Frontend

React + Vite + TypeScript + TailwindCSS. The single-page app for Brink — see the
[root README](../../README.md) for what the product is.

**Auth:** users sign in with Spotify **through Supabase Auth** (Supabase is the OAuth broker — the
browser never handles a Spotify client secret). After sign-in, the browser uses the Spotify access
token from the Supabase session to pull the user's listening data directly, and hands the
longer-lived tokens to our backend (`POST /api/auth/capture-spotify`) so it can refresh them and
snapshot plays later. Taste analytics (top tracks/artists/genres, streak, cluster, compatibility)
are still computed live in the browser today; the Python backend takes them over in later tickets.

## Setup

### 1. Environment

The frontend needs just two public Supabase values. Copy the example and fill them in (get them
from Andrea, or from the Supabase project → **Settings → API**):

```powershell
cd apps/web
Copy-Item .env.example .env
```

```
VITE_SUPABASE_URL=https://<project-ref>.supabase.co
VITE_SUPABASE_ANON_KEY=<public anon key>
```

The anon key is meant to be public (it ships in the browser bundle), but `.env` is gitignored —
don't commit it. If these aren't set, the app renders a "misconfigured" state.

> **Spotify is configured in Supabase, not here.** The Spotify OAuth app (Client ID + Secret) and
> its redirect URI live in the Supabase dashboard (**Authentication → Providers → Spotify**) at the
> project level — already set up for `brink-dev`. You do **not** create your own Spotify app or set
> any `VITE_SPOTIFY_*` variable.

### 2. Run (two terminals)

The app calls `/api/*`, which Vite proxies to the FastAPI backend on `127.0.0.1:3001`, so run the
backend alongside it:

```
# Terminal 1 — backend (FastAPI)
cd backend && uv run uvicorn app.main:app --reload --port 3001

# Terminal 2 — frontend
cd apps/web && npm install && npm run dev
```

Open **http://127.0.0.1:5173/** and click **Sign in with Spotify** → you bounce to Spotify's consent
page (via Supabase) and land back on `/feed` with your real listening data.

> For the login round-trip to return, your dev URL `http://127.0.0.1:5173/callback` must be in
> Supabase's allowed **Redirect URLs** (**Authentication → URL Configuration**). It's already added
> for the team's dev setup. Use `127.0.0.1`, not `localhost`, consistently.

## Scripts

| Script | What it does |
|---|---|
| `npm run dev` | Vite dev server with HMR on http://127.0.0.1:5173 |
| `npm run build` | Type-check (`tsc -b`) + production build into `dist/` |
| `npm run preview` | Serve the built bundle locally |
| `npm run lint` | ESLint pass |

## Layout

```
src/
├── main.tsx              # router + <AuthProvider>
├── App.tsx               # login gate + app shell
├── index.css
├── components/
│   ├── NavBar.tsx        # nav + profile avatar + logout
│   ├── PostCard.tsx      # feed card (cluster badge + genre tags)
│   ├── CompatDonut.tsx   # SVG donut for compatibility %
│   └── StreakHeatmap.tsx # 28-day listening grid
├── context/
│   └── AuthContext.tsx   # Supabase session + one-time Spotify-token capture to the backend
├── pages/
│   ├── LoginPage.tsx     # splash + "Sign in with Spotify"
│   ├── CallbackPage.tsx  # waits for Supabase to finish OAuth, then → /feed
│   ├── FeedPage.tsx      # your real recent plays + mock friends
│   ├── ProfilePage.tsx   # Wrapped-style stats (real for /profile/me)
│   ├── AnalyticsPage.tsx # taste breakdown views
│   ├── PredictPage.tsx   # compatibility / prediction view
│   └── ArtistPage.tsx    # artist portal scaffold
├── lib/
│   ├── supabase.ts       # browser Supabase client (session in localStorage, auto-refresh)
│   ├── spotify-api.ts    # Spotify Web API calls using the session's provider_token
│   ├── analytics.ts      # genre aggregation, streak, rule-based cluster, cosine compatibility
│   ├── data.ts           # unified data layer (real for self, mocked for friends)
│   └── backend.ts        # client for the legacy /api/state shared-state store (being retired)
├── mocks/
│   ├── feed.ts           # mock friend posts shown alongside real data
│   └── stats.ts          # mock friend profiles for /profile/u1, /profile/u2
└── types/
    └── stats.ts          # UserStats / CompatScore contract — the shape the Python pipeline fills
```

## How the analytics work today

Everything the Python pipeline will eventually do, the browser does today against the same JSON
contract ([src/types/stats.ts](src/types/stats.ts)):

| Metric | Today (browser) | Later (Python backend) |
|---|---|---|
| Top tracks / artists | `/me/top/*?time_range=short_term` | Same Spotify call, persisted to Postgres |
| Top genres | Weighted aggregation across top artists' `genres[]`, normalized to sum=1 | Same algorithm, as a scheduled job |
| Streak | Consecutive days back from today in recently-played (≤30d) | Same, over the full play history |
| Cluster | Rule-based classifier over top genres → label | K-means over the full feature vector |
| Compat | Cosine similarity of genre-weight vectors | Same formula, with audio features added |

Swapping from in-browser to backend-served stats is a single edit in `lib/data.ts`.

## Demo flow

1. Land on `/` → splash. Click **Sign in with Spotify** → Supabase/Spotify consent → back to `/feed`.
2. Feed shows your last few real plays interleaved with mocked friend posts (cluster badge + genre pills).
3. **Profile** → real Wrapped-style page from your last 4 weeks of listening.
4. Click a mock friend → their compatibility donut vs you, plus shared genres.
5. Logout icon top-right when done.

## Troubleshooting

- **App shows "misconfigured" / blank** — `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` aren't set. Fill in `.env` and **restart** `npm run dev` (Vite only reads env vars at startup).
- **Login doesn't come back / redirect error** — your dev URL `http://127.0.0.1:5173/callback` must be in Supabase's **Redirect URLs**. Use `127.0.0.1` everywhere, not `localhost`.
- **"User not registered in the developer app"** — Spotify dev mode caps at 25 testers; add the tester's email under **User Management** in the Spotify dashboard.
- **Tokens not captured locally** — `/api/auth/capture-spotify` needs the backend running on `:3001`. Login still works without it, but the backend won't have the refresh token.
- **Stats look thin / streak 0** — Spotify's recently-played only returns the last 50 items / ~30 days; new accounts look sparse.
