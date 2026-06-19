# apps/web — Brink Frontend (POC with real Spotify login)

React + Vite + TypeScript + TailwindCSS.

This is a working proof of concept: real Spotify OAuth (PKCE, no client secret in the browser), real listening data pulled from Spotify, and analytics — top tracks, top artists, genre weights, streak, taste cluster, and compatibility score — computed live in the browser from that data.

## One-time setup

### 1. Create a Spotify app

1. Go to https://developer.spotify.com/dashboard and click **Create app**.
2. App name / description: whatever (e.g. "Brink Dev").
3. **Redirect URIs** — add EXACTLY this (paste it, don't retype):
   ```
   http://127.0.0.1:5173/callback
   ```
   > Spotify rejects `http://localhost` as a redirect URI now. You **must** use `127.0.0.1` for loopback dev. See [Spotify's redirect URI rules](https://developer.spotify.com/documentation/web-api/concepts/redirect_uri).
4. Which APIs/SDKs: check **Web API**.
5. Save. Copy the **Client ID** from the app's settings page.

> The Spotify development-mode user cap (25 users) means each tester must be added under **User Management** in your app settings before they can log in. For the demo team that's enough.

### 2. Local env file

```powershell
cd apps/web
Copy-Item .env.example .env.local
```

Edit `apps/web/.env.local` and set:

```
VITE_SPOTIFY_CLIENT_ID=<paste the Client ID here>
VITE_SPOTIFY_REDIRECT_URI=http://127.0.0.1:5173/callback
```

> `.env.local` is gitignored — don't commit it. The Client ID isn't a secret (it's exposed in the OAuth redirect anyway), but keep it out of git as a habit.

### 3. Install + run

```powershell
npm install
npm run dev
```

Open **http://127.0.0.1:5173/** (NOT `localhost` — Spotify's redirect rules require the loopback IP). You should see the Brink landing page with a green **Sign in with Spotify** button. Clicking it sends you to Spotify's consent page; approving it lands you back on `/feed` with your real listening data loaded.

## Scripts

| Script | What it does |
|---|---|
| `npm run dev` | Vite dev server with HMR on http://127.0.0.1:5173 |
| `npm run build` | Type-check + production build into `dist/` |
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
│   ├── PostCard.tsx      # feed card (cluster badge + genre tags from analytics)
│   ├── CompatDonut.tsx   # SVG donut for compatibility %
│   └── StreakHeatmap.tsx # 28-day grid
├── context/
│   └── AuthContext.tsx   # auth state hook
├── pages/
│   ├── LoginPage.tsx     # marketing splash + Spotify button
│   ├── CallbackPage.tsx  # handles ?code=… return from Spotify
│   ├── FeedPage.tsx      # your real recent plays + mock friends
│   ├── ProfilePage.tsx   # Wrapped-style stats (real for /profile/me)
│   └── ArtistPage.tsx    # BTS portal scaffold
├── lib/
│   ├── spotify-auth.ts   # PKCE flow: login, callback, refresh, logout
│   ├── spotify-api.ts    # /me, /me/top/tracks, /me/top/artists, recently-played
│   ├── analytics.ts      # genre aggregation, streak, cluster, cosine compat
│   ├── data.ts           # unified data layer (real for self, mocked for friends)
│   └── api.ts            # legacy mock client, kept for reference
├── mocks/
│   ├── feed.ts           # mock friend posts that stay visible alongside real data
│   └── stats.ts          # mock friend profiles for /profile/u1, /profile/u2
└── types/
    └── stats.ts          # UserStats / CompatScore contract — locks Jonah's pipeline shape
```

## How the analytics work today

Everything Jonah's Python pipeline will eventually do, the browser does today against the same JSON contract:

| Metric | Today (browser) | Production (Jonah's Python on Render) |
|---|---|---|
| Top tracks | `/me/top/tracks?time_range=short_term` | Same Spotify call, persisted to Postgres |
| Top artists | `/me/top/artists?time_range=short_term` | Same |
| Top genres | Weighted aggregation across top artists' `genres[]`, normalized to sum=1 | Same algorithm, run as a scheduled job |
| Streak | Consecutive days back from today in `/me/player/recently-played` (≤ 30d cap) | Same, but over the full historical play table |
| Cluster | Rule-based classifier over top genres → label (`mellow indie`, `high-energy mainstream`, …) | K-means over the full feature vector (genres + audio features from the Kaggle dataset) |
| Compat | Cosine similarity of genre-weight vectors | Same formula; vectors include audio features |

Same JSON shape ([src/types/stats.ts](src/types/stats.ts)) for both — the swap from in-browser to backend-served stats is a single edit in `lib/data.ts`.

## Demo flow

1. Land on `/` → marketing splash.
2. Click **Sign in with Spotify** → consent → bounce back to `/feed`.
3. Feed shows your last few real plays interleaved with mocked friend posts. Each post shows a cluster badge under the user name and genre pills under the track.
4. Click **Profile** in the nav → real Wrapped-style page from your last 4 weeks of listening.
5. Click **Andrea V.** in the feed → `/profile/u1`, see the cosine-similarity compatibility donut between you and that mock persona, plus shared genres.
6. Hit the logout icon top-right when done.

## Troubleshooting

- **"Login failed: redirect_uri MISMATCH" / "redirect URI is not secure"** — use `http://127.0.0.1:5173/callback` everywhere (Spotify dashboard, `.env.local`, the URL you open in the browser). `localhost` is no longer accepted as a loopback redirect.
- **"User not registered in the developer app"** — Spotify dev mode caps at 25 testers. Add the tester's email in **User Management** in the Spotify dashboard.
- **Stats look thin / streak shows 0** — Spotify's `recently-played` only returns the last 50 items / 30 days. New accounts will look sparse.
- **"VITE_SPOTIFY_CLIENT_ID is not set"** — restart `npm run dev` after creating `.env.local`. Vite only loads env vars at server start.
