# Brink — The Music-Native Social Platform

A music-first social web app built as a course project for BUSA 649 at McGill University's Desautels Faculty of Management. Brink gives artists and listeners a dedicated hub for music — surfacing Spotify listening activity as a persistent social identity and giving emerging artists a space to share their creative process without becoming social media personalities.

**Team:** Andrea Vreugdenhil · Sebastian Arguedas Soley · Jonah Walker
**Deadline:** July 30, 2026

---

## What it does

- Sign up with an email and password, then optionally link your Spotify account
- A social feed where connected users can share what they're listening to, with genre tags and listening context
- Listener profile pages with Wrapped-style stats — top tracks, top genres, listening streaks, and taste compatibility with friends
- A friend/follow system
- An artist portal for sharing behind-the-scenes image and text posts linked to specific Spotify tracks
- Per-post engagement analytics for artists

---

## Tech stack

| Layer | Technology | Hosted on |
|---|---|---|
| Frontend | React (Vite) | Vercel |
| Backend | Node.js + Express | Render |
| Database | PostgreSQL via Prisma | Render |
| Image storage | Cloudinary | Cloudinary (free tier) |
| Listening data | Spotify Web API | — |

---

## Spotify setup

This app uses the Spotify Web API in Development Mode, which limits connected users to a manually approved allowlist.

To connect your Spotify account as a test user:
1. Contact a team member to be added to the Spotify app's allowlist in the developer dashboard
2. Once added, log into Brink and click **Connect Spotify** on your profile page
3. Approve the permissions in the Spotify popup

> **Note:** Development Mode supports a maximum of 5 allowlisted users. Users without a connected Spotify account can still use all social features — listening stats and currently-playing will show as empty until a Spotify account is linked.

---

## Roles

| Team member | Primary ownership |
|---|---|
| Andrea Vreugdenhil | Backend architecture, Spotify API integration, Prisma schema, artist portal, deployment |
| Sebastian Arguedas Soley | React frontend, TailwindCSS, feed UI, listener profile pages, QA |
| Jonah Walker | Analytics pipeline, listening stats aggregation, Wrapped-style features, taste compatibility scoring |
