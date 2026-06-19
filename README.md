# Brink — Music-Native Social

A proof-of-concept social app that turns a user's real Spotify listening
history into a feed friends can react to, plus a compatibility match-score
between any two users.

Built as a course project for BUSA 649 at McGill University's Desautels
Faculty of Management.

**Team:** Andrea Vreugdenhil · Sebastian Arguedas Soley · Jonah Walker
**Live demo:** <https://brink-self.vercel.app>

---

## 1. What is in this repo

```
.
├── apps/web/         ← the entire front-end (React + TypeScript + Vite)
├── api/              ← the entire back-end (one Vercel serverless function)
├── vercel.json       ← deploy config (static SPA + /api/* routes)
├── .env.example      ← copy to apps/web/.env.local and fill in
├── .gitignore
└── README.md         ← you are here
```

There is no other hidden piece — those folders **are** the product.
No Python, no Django, no separate server to spin up.

---

## 2. Architecture in one picture

```
┌──────────────────────────────────────────────────────────────────────┐
│                        USER'S BROWSER                                │
│                                                                      │
│   apps/web/index.html  ──loads──▶  src/main.tsx                      │
│                                          │                           │
│                                          ▼                           │
│                                   src/App.tsx  (auth + layout)       │
│                                          │                           │
│                                          ▼                           │
│                              src/pages/FeedPage.tsx                  │
│                                          │                           │
│                                          ▼                           │
│                          src/components/PostCard.tsx                 │
│                                          │                           │
│                              click ❤  ──┘                           │
│                                          │                           │
│                                          ▼                           │
│                                src/lib/backend.ts                    │
│                                          │                           │
│                                fetch("/api/state")                   │
└──────────────────────────────────────────┼───────────────────────────┘
                                           │
                                           ▼
┌──────────────────────────────────────────────────────────────────────┐
│                  VERCEL SERVERLESS (Node 20)                         │
│                                                                      │
│                          api/state.js                                │
│                              │                                       │
│                              ▼                                       │
│                       jsonblob.com                                   │
│              (one shared JSON document — no signup)                  │
└──────────────────────────────────────────────────────────────────────┘
```

### The four files that actually run the app

| # | File | What it does |
|---|---|---|
| 1 | `apps/web/index.html` | Browser entry. One `<div id="root">` + `<script src="/src/main.tsx">`. |
| 2 | `apps/web/src/main.tsx` | Boots React, declares every route (`/feed`, `/profile/:id`, `/artist`, `/predict`, `/analytics`, `/callback`). |
| 3 | `apps/web/src/App.tsx` | Auth gate. If signed-out → `<LoginPage />`, otherwise renders the nav bar + the matched route. |
| 4 | `api/state.js` | The only backend. `GET /api/state` returns all users + reactions; `POST /api/state` either upserts a user or increments a reaction count. |

---

## 3. Folder cheat-sheet (`apps/web/src/`)

| Folder | Purpose |
|---|---|
| `pages/` | One file per route in `main.tsx` — `LoginPage`, `CallbackPage`, `FeedPage`, `ProfilePage`, `ArtistPage`, `PredictPage`, `AnalyticsPage`. |
| `components/` | Reusable UI pieces. `PostCard.tsx` is where the heart / fire / sparkle reactions live. |
| `lib/` | All logic, no UI: `spotify-auth.ts` (PKCE OAuth), `spotify-api.ts` (Web-API calls), `analytics.ts` (builds the `UserStats` object), `data.ts` (caching + merge with backend), `backend.ts` (the only file that talks to `/api/state`), `api.ts` (compatibility match score). |
| `context/` | `AuthContext.tsx` — holds the Spotify access token in memory. |
| `types/` | TypeScript shapes (`UserStats`, `RecentTrack`, etc.). |
| `mocks/` | Fake users shown only when no real friends have signed in yet. |

---

## 4. Running it locally

### Prerequisites
- Node.js 20+
- A Spotify developer app (Client ID — no secret needed, we use PKCE)
- A jsonblob.com bucket ID (create one at <https://jsonblob.com> and copy the ID from the URL)

### Setup

```bash
git clone https://github.com/j-jwalker/Brink.git
cd Brink
cp .env.example apps/web/.env.local
# then edit apps/web/.env.local and fill in VITE_SPOTIFY_CLIENT_ID etc.

cd apps/web
npm install
npm run dev          # http://127.0.0.1:5173
```

The front end will hit the **production** `/api/state` endpoint by default
because that URL is same-origin in production and proxied during `vite dev`.
If you want a local backend too:

```bash
# from repo root
npx vercel dev       # serves api/state.js at http://localhost:3000/api/state
```

### Environment variables

| Variable | Where | What |
|---|---|---|
| `VITE_SPOTIFY_CLIENT_ID` | front end (`apps/web/.env.local`) | Spotify app Client ID |
| `VITE_SPOTIFY_REDIRECT_URI` | front end | e.g. `http://127.0.0.1:5173/callback` for dev, `https://brink-self.vercel.app/callback` for prod |
| `JSONBLOB_ID` | back end (Vercel project settings) | The bucket id from jsonblob.com |

The Spotify app must be in **Development Mode** with each tester's email
added under "Users and Access" until the app is submitted for review.

---

## 5. Deploying

The repo is wired to Vercel. Any push to `main` triggers a deploy.

- Build command: `cd apps/web && npm install && npm run build`
- Output dir: `apps/web/dist`
- `vercel.json` sends `/api/*` to the serverless function and everything else
  to the static `index.html` (SPA routing).

To deploy from a clean clone:

```bash
npm i -g vercel
vercel link            # link to the existing brink2/brink project
vercel --prod
```

---

## 6. How a feature flows end-to-end (example: a heart reaction)

1. User clicks the heart on `<PostCard postId="abc" />`.
2. `PostCard.tsx` optimistically bumps the local count and writes
   `localStorage["brink.reacted.abc.heart"] = "1"`.
3. It calls `reactToPost("abc", "heart", +1)` from `lib/backend.ts`.
4. `backend.ts` does `POST /api/state` with
   `{ action: "react", payload: { postId: "abc", kind: "heart", delta: 1 } }`.
5. `api/state.js` (running on Vercel) fetches the current blob from
   jsonblob.com, increments `reactions.abc.heart`, writes it back, returns
   the new counts.
6. Every other browser that opens the app within 30 s sees the new count
   via `getBackendState()` (which has a 30-second in-memory cache).

To add a new reaction kind, the only files you touch are `PostCard.tsx`
(UI) and `api/state.js` (allowed kinds list). No database migration —
the blob is schemaless.

---

## 7. Tech choices, briefly

| Layer | Pick | Why |
|---|---|---|
| Front-end framework | **React 18 + Vite 5** | Instant HMR, smallest learning curve for the team. |
| Language | **TypeScript 5** | Catch shape mismatches in Spotify responses before runtime. |
| Styling | **Tailwind CSS 3** | No CSS files to chase; design tokens live in `tailwind.config.js`. |
| Routing | **react-router 6** | Standard. |
| Icons | **lucide-react** | Tree-shakeable, MIT. |
| Auth | **Spotify PKCE OAuth** | No client secret means we can ship auth purely in the browser. |
| Back end | **Vercel Serverless Functions** | Zero ops, scales to zero, same deploy as the front end. |
| Storage | **jsonblob.com** | Gives the POC shared state without provisioning Postgres yet. Swappable: only the four `fetch()` calls inside `api/state.js` need to change when we move to a real DB. |

---

## 8. Contributing

If you are picking this up to keep building:

1. Read `apps/web/src/main.tsx` first — it is the route map.
2. Each route is a single file in `apps/web/src/pages/`. Start there.
3. Anything that talks to Spotify lives in `apps/web/src/lib/spotify-*.ts`.
4. Anything cross-user (feed of friends, reactions, match score input) goes
   through `apps/web/src/lib/backend.ts` → `api/state.js`. Don't add new
   network code anywhere else.
5. Run `npm run build` inside `apps/web/` before you push — Vercel will fail
   the deploy on a TypeScript error.
