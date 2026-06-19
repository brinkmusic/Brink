// Build a real UserStats payload from the live Spotify API for the signed-in user.
// Mocked "friends" (u1, u2) stay as fallback. Real friends arrive via the
// shared backend (/api/state) — every signed-in user uploads their stats and
// recent plays, so everyone else's feed/profile/compat sees them live.

import {
  getMe,
  getRecentlyPlayed,
  getTopArtists,
  getTopTracks,
} from "./spotify-api";
import { buildStats, compatBetween } from "./analytics";
import { mockUserStats } from "../mocks/stats";
import { mockFeed } from "../mocks/feed";
import type { Post } from "../components/PostCard";
import type { CompatScore, UserStats } from "../types/stats";
import { getBackendState, upsertUserStats } from "./backend";

const SS_KEY_STATS = (id: string) => `brink.stats.v4.${id}`;
const SS_KEY_RECENT = "brink.spotify.recent_v4";
const SS_KEY_MY_ID = "brink.my_user_id";

export function getMyUserId(): string | null {
  return sessionStorage.getItem(SS_KEY_MY_ID);
}

interface CachedStats {
  fetched_at: number;
  stats: UserStats;
}

interface CachedRecent {
  fetched_at: number;
  items: { track_id: string; title: string; artist: string; played_at: string; album_art?: string }[];
}

const FRESH_MS = 5 * 60_000; // 5-min in-tab cache so navs feel snappy

// ---- Real signed-in user ------------------------------------------------

export async function getMyStats(force = false): Promise<UserStats> {
  if (!force) {
    const cached = readCache<CachedStats>(SS_KEY_STATS("me"));
    if (cached && Date.now() - cached.fetched_at < FRESH_MS) return cached.stats;
  }

  // Run the 4 Spotify calls independently. /me and /me/player/recently-played
  // are load-bearing; the top-tracks / top-artists endpoints often return
  // empty for accounts without enough play history, so we tolerate them.
  const [meR, topTracksR, topArtistsR, recentR] = await Promise.allSettled([
    getMe(),
    getTopTracks("short_term", 20),
    getTopArtists("short_term", 20),
    getRecentlyPlayed(50),
  ]);

  if (meR.status !== "fulfilled" || recentR.status !== "fulfilled") {
    const err =
      meR.status === "rejected"
        ? meR.reason
        : recentR.status === "rejected"
          ? recentR.reason
          : new Error("unknown");
    console.warn("[brink] core Spotify calls failed, falling back to demo:", err);
    return { ...mockUserStats.me, computed_at: new Date().toISOString() };
  }

  const me = meR.value;
  const recent = recentR.value;
  const topTracks = topTracksR.status === "fulfilled" ? topTracksR.value : [];
  const topArtists = topArtistsR.status === "fulfilled" ? topArtistsR.value : [];
  if (topTracksR.status === "rejected") {
    console.warn("[brink] /me/top/tracks failed (using recent-only):", topTracksR.reason);
  }
  if (topArtistsR.status === "rejected") {
    console.warn("[brink] /me/top/artists failed (no genres/artists panel):", topArtistsR.reason);
  }

  const stats = buildStats({ me, topTracks, topArtists, recent });
  writeCache(SS_KEY_STATS("me"), { fetched_at: Date.now(), stats });
  sessionStorage.setItem(SS_KEY_MY_ID, stats.user_id);

  // Push to the shared backend so other users see this user on their feed +
  // can be matched for compatibility. Fire-and-forget; never blocks the UI.
  void upsertUserStats(stats);

  const compact: CachedRecent = {
    fetched_at: Date.now(),
    items: recent.map((r) => {
      const imgs = r.track.album?.images ?? [];
      return {
        track_id: r.track.id,
        title: r.track.name,
        artist: (r.track.artists ?? []).map((a) => a.name).join(", "),
        played_at: r.played_at,
        album_art: imgs[imgs.length - 1]?.url,
      };
    }),
  };
  writeCache(SS_KEY_RECENT, compact);
  return stats;
}

export async function getStatsFor(userId: string): Promise<UserStats> {
  if (userId === "me") return getMyStats();
  // Real users uploaded to the shared backend take priority over mocks.
  const state = await getBackendState();
  const live = state.users[userId];
  if (live) return live;
  // Mocked friends — Andrea / Jonah personas as fallback.
  const s = mockUserStats[userId];
  if (s) return s;
  // Unknown user: fall through to the "me" persona so the page still renders.
  return getMyStats();
}

export async function getCompatBetween(
  aId: string,
  bId: string,
): Promise<CompatScore | null> {
  if (aId === bId) return null;
  const [a, b] = await Promise.all([getStatsFor(aId), getStatsFor(bId)]);
  return compatBetween(aId, bId, a.top_genres, b.top_genres, a.top_artists, b.top_artists);
}

// ---- Feed: user's recent plays + real friends + mock fallback ----------

export async function getFeed(): Promise<Post[]> {
  let mine: Post[] = [];
  let myId: string | null = null;
  try {
    const me = await getMe();
    myId = me.id;
    const recent = readCache<CachedRecent>(SS_KEY_RECENT);
    let items = recent?.items;
    if (!items || Date.now() - (recent?.fetched_at ?? 0) > FRESH_MS) {
      const live = await getRecentlyPlayed(20);
      items = live.map((r) => {
        const imgs = r.track.album?.images ?? [];
        return {
          track_id: r.track.id,
          title: r.track.name,
          artist: (r.track.artists ?? []).map((a) => a.name).join(", "),
          played_at: r.played_at,
          album_art: imgs[imgs.length - 1]?.url,
        };
      });
      writeCache<CachedRecent>(SS_KEY_RECENT, { fetched_at: Date.now(), items });
    }
    const myStats = readCache<CachedStats>(SS_KEY_STATS("me"))?.stats;
    const clusterLabel = myStats?.cluster_label;

    mine = items.slice(0, 4).map((it, i) => ({
      id: `me-${it.track_id}-${i}`,
      user: {
        id: "me",
        name: me.display_name || me.id,
        clusterLabel,
        avatarUrl: me.images?.[0]?.url,
      },
      track: {
        id: it.track_id,
        title: it.title,
        artist: it.artist,
        albumArt: it.album_art,
      },
      playedAt: it.played_at,
      reactions: { heart: 0, fire: 0, sparkle: 0 },
      commentCount: 0,
    }));
  } catch {
    // If Spotify call fails, fall back to mocks so the page never breaks.
  }

  // Pull every other user's recent plays from the shared backend so the
  // feed shows real people, not just mocks.
  const friends: Post[] = [];
  try {
    const state = await getBackendState();
    for (const [uid, stats] of Object.entries(state.users)) {
      if (uid === myId) continue;
      const recent = stats.recent_tracks ?? [];
      for (let i = 0; i < Math.min(recent.length, 3); i++) {
        const it = recent[i];
        friends.push({
          id: `bk-${uid}-${it.track_id}-${i}`,
          user: {
            id: uid,
            name: stats.display_name,
            clusterLabel: stats.cluster_label,
            avatarUrl: stats.avatar_url,
          },
          track: {
            id: it.track_id,
            title: it.title,
            artist: it.artist,
            albumArt: it.album_art,
          },
          playedAt: it.played_at,
          reactions: { heart: 0, fire: 0, sparkle: 0 },
          commentCount: 0,
        });
      }
    }
  } catch {
    /* backend down — just skip friend posts */
  }

  // Mocks are only used when no real friends arrived from the backend, so a
  // fully populated room doesn't show ghost personas alongside live people.
  const filler = friends.length > 0 ? [] : mockFeed;

  return [...mine, ...friends, ...filler].sort(
    (a, b) => new Date(b.playedAt).getTime() - new Date(a.playedAt).getTime(),
  );
}

// ---- tiny sessionStorage helpers ----------------------------------------

function readCache<T>(key: string): T | null {
  const raw = sessionStorage.getItem(key);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as T;
  } catch {
    return null;
  }
}

function writeCache<T>(key: string, value: T) {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* quota exceeded — ignore */
  }
}
