// Browser-side analytics layer. In production this work moves to Jonah's Python
// pipeline running on a schedule; the JSON shape it emits is identical to what
// this file produces, so the UI doesn't change when we swap.

import type {
  PlayHistoryItem,
  SpotifyArtist,
  SpotifyTrack,
  SpotifyUser,
} from "./spotify-api";
import type {
  CompatScore,
  TopArtist,
  TopGenre,
  TopTrack,
  UserStats,
} from "../types/stats";

// ---- Top tracks / artists -----------------------------------------------

export function tracksToTop(tracks: SpotifyTrack[]): TopTrack[] {
  return tracks.slice(0, 8).map((t, i) => {
    const imgs = t.album?.images ?? [];
    return {
      track_id: t.id,
      title: t.name,
      artist: (t.artists ?? []).map((a) => a.name).join(", "),
      play_count: tracks.length - i,
      album_art: imgs[imgs.length - 1]?.url ?? imgs[0]?.url,
    };
  });
}

// Build top_tracks from recently-played history so Profile matches Feed.
// Dedupe by track_id, count plays, sort by play_count then recency. Pads with
// /me/top/tracks fallbacks AFTER the real recent plays if fewer than `limit`
// unique tracks are available.
export function topTracksFromRecent(
  recent: PlayHistoryItem[],
  fallback: SpotifyTrack[] = [],
  limit = 8,
): TopTrack[] {
  const byId = new Map<
    string,
    { track: SpotifyTrack; count: number; lastPlayedAt: number }
  >();
  for (const item of recent) {
    const t = item.track;
    const prev = byId.get(t.id);
    const ts = new Date(item.played_at).getTime();
    if (prev) {
      prev.count += 1;
      prev.lastPlayedAt = Math.max(prev.lastPlayedAt, ts);
    } else {
      byId.set(t.id, { track: t, count: 1, lastPlayedAt: ts });
    }
  }
  const real = Array.from(byId.values())
    .sort((a, b) => b.count - a.count || b.lastPlayedAt - a.lastPlayedAt)
    .slice(0, limit)
    .map(({ track, count }) => {
      const imgs = track.album?.images ?? [];
      return {
        track_id: track.id,
        title: track.name,
        artist: (track.artists ?? []).map((a) => a.name).join(", "),
        play_count: count,
        album_art: imgs[imgs.length - 1]?.url ?? imgs[0]?.url,
      };
    });

  if (real.length >= limit) return real;

  // Pad with /me/top/tracks (4-week relevance ranking) for any tracks not
  // already in the recent list. Marked with play_count = 0 so the UI can
  // visually distinguish padded entries if desired.
  const seen = new Set(real.map((r) => r.track_id));
  const padded = fallback
    .filter((t) => !seen.has(t.id))
    .slice(0, limit - real.length)
    .map((t) => {
      const imgs = t.album?.images ?? [];
      return {
        track_id: t.id,
        title: t.name,
        artist: (t.artists ?? []).map((a) => a.name).join(", "),
        play_count: 0,
        album_art: imgs[imgs.length - 1]?.url ?? imgs[0]?.url,
      };
    });

  return [...real, ...padded];
}

export function artistsToTop(artists: SpotifyArtist[]): TopArtist[] {
  return artists.slice(0, 8).map((a, i) => {
    const imgs = a.images ?? [];
    return {
      artist_id: a.id,
      name: a.name,
      play_count: artists.length - i,
      image: imgs[imgs.length - 1]?.url ?? imgs[0]?.url,
    };
  });
}

// ---- Top genres: weight by inverse rank of artists they appear on --------

export function genresFromArtists(artists: SpotifyArtist[], topN = 8): TopGenre[] {
  const counts = new Map<string, number>();
  artists.forEach((a, i) => {
    const weight = 1 / (i + 1); // top artist contributes most
    const genres = Array.isArray(a?.genres) ? a.genres : [];
    for (const g of genres) {
      counts.set(g, (counts.get(g) ?? 0) + weight);
    }
  });
  const total = Array.from(counts.values()).reduce((s, n) => s + n, 0) || 1;
  return Array.from(counts.entries())
    .map(([name, w]) => ({ name, weight: w / total }))
    .sort((a, b) => b.weight - a.weight)
    .slice(0, topN);
}

// ---- Listening streak: consecutive days back from today with >=1 play ----

export function streakFromHistory(items: PlayHistoryItem[]): number {
  const days = new Set(
    items.map((i) => new Date(i.played_at).toISOString().slice(0, 10)),
  );
  let streak = 0;
  const cursor = new Date();
  for (;;) {
    const key = cursor.toISOString().slice(0, 10);
    if (!days.has(key)) break;
    streak += 1;
    cursor.setUTCDate(cursor.getUTCDate() - 1);
  }
  return streak;
}

// ---- Taste cluster: heuristic version of Jonah's K-means ----------------
// In production: each user becomes a feature vector (top-N genre weights +
// avg popularity + diversity) and K-means assigns a cluster id 0..k-1.
// Here we use a transparent rule pass over top genres so the demo is honest.

export interface Cluster {
  id: number;
  label: string;
}

const CLUSTERS: { id: number; label: string; match: (s: string) => boolean }[] = [
  { id: 1, label: "deep listener", match: (s) => /classical|jazz|ambient|post-rock|drone/.test(s) },
  { id: 2, label: "mellow indie", match: (s) => /indie folk|folk|singer-songwriter|chamber|dream pop/.test(s) },
  { id: 3, label: "electronic energy", match: (s) => /electronic|house|techno|edm|trance|drum and bass|dnb/.test(s) },
  { id: 4, label: "high-energy mainstream", match: (s) => /hip hop|rap|trap|drill|r&b/.test(s) },
  { id: 5, label: "loud & heavy", match: (s) => /metal|hardcore|punk|emo/.test(s) },
  { id: 6, label: "pop mainstream", match: (s) => /(^|\s)pop(\s|$)|dance pop|electropop|k-pop/.test(s) },
  { id: 7, label: "indie rock listener", match: (s) => /indie rock|alt rock|alternative|garage rock|shoegaze/.test(s) },
];

export function clusterFromGenres(genres: TopGenre[]): Cluster {
  for (const c of CLUSTERS) {
    const hits = genres.filter((g) => c.match(g.name));
    const weight = hits.reduce((s, g) => s + g.weight, 0);
    if (weight >= 0.25) return { id: c.id, label: c.label };
  }
  return { id: 0, label: genres[0]?.name ?? "eclectic" };
}

// ---- Compat: cosine similarity over genre-weight vectors ---------------
// This IS the algorithm; the only thing that differs in Jonah's pipeline is
// that vectors include audio features (danceability, energy, valence, tempo)
// joined from the Kaggle dataset on track_id.

export function compatBetween(
  aId: string,
  bId: string,
  aGenres: TopGenre[],
  bGenres: TopGenre[],
  aArtists: TopArtist[],
  bArtists: TopArtist[],
): CompatScore {
  const dims = new Set<string>([...aGenres, ...bGenres].map((g) => g.name));
  const va = new Map(aGenres.map((g) => [g.name, g.weight]));
  const vb = new Map(bGenres.map((g) => [g.name, g.weight]));

  let dot = 0;
  let na = 0;
  let nb = 0;
  for (const d of dims) {
    const x = va.get(d) ?? 0;
    const y = vb.get(d) ?? 0;
    dot += x * y;
    na += x * x;
    nb += y * y;
  }
  const score = na && nb ? dot / (Math.sqrt(na) * Math.sqrt(nb)) : 0;

  const aArtistIds = new Set(aArtists.map((a) => a.artist_id));
  const sharedArtists = bArtists.filter((a) => aArtistIds.has(a.artist_id)).map((a) => a.name);
  const aGenreSet = new Set(aGenres.map((g) => g.name));
  const sharedGenres = bGenres.filter((g) => aGenreSet.has(g.name)).map((g) => g.name);

  return {
    a: aId,
    b: bId,
    score: Math.max(0, Math.min(1, score)),
    shared_genres: sharedGenres,
    shared_artists: sharedArtists,
  };
}

// ---- Build the full UserStats payload ----------------------------------

export interface RawListeningData {
  me: SpotifyUser;
  topTracks: SpotifyTrack[];
  topArtists: SpotifyArtist[];
  recent: PlayHistoryItem[];
}

export function buildStats(raw: RawListeningData): UserStats {
  const top_artists = artistsToTop(raw.topArtists);
  const top_genres = genresFromArtists(raw.topArtists);
  // Top tracks come from the recently-played stream first (so Profile matches
  // Feed), then pad with /me/top/tracks if the user hasn't played 8 unique
  // tracks in their recent history.
  const top_tracks = topTracksFromRecent(raw.recent, raw.topTracks, 8);
  const cluster = clusterFromGenres(top_genres);

  // Compact last-N plays so other users' browsers can render this user in
  // the social feed without needing their Spotify token.
  const recent_tracks = raw.recent.slice(0, 8).map((r) => {
    const imgs = r.track.album?.images ?? [];
    return {
      track_id: r.track.id,
      title: r.track.name,
      artist: (r.track.artists ?? []).map((a) => a.name).join(", "),
      played_at: r.played_at,
      album_art: imgs[imgs.length - 1]?.url ?? imgs[0]?.url,
    };
  });

  const avatar_url = raw.me.images?.[0]?.url;

  return {
    user_id: raw.me.id,
    display_name: raw.me.display_name || raw.me.id,
    computed_at: new Date().toISOString(),
    top_tracks,
    top_artists,
    top_genres,
    streak_days: streakFromHistory(raw.recent),
    total_plays_30d: raw.recent.length, // capped at 50 by Spotify API
    cluster_id: cluster.id,
    cluster_label: cluster.label,
    recent_tracks,
    avatar_url,
  };
}
