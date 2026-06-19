// Shapes match the contract Jonah's Python pipeline will produce.
// Keep this file in sync with docs/analytics-contract.md (once Jonah commits it).

export interface TopTrack {
  track_id: string;
  title: string;
  artist: string;
  play_count: number;
  album_art?: string;
}

export interface TopArtist {
  artist_id: string;
  name: string;
  play_count: number;
  image?: string;
}

export interface TopGenre {
  name: string;
  weight: number; // 0–1, sums across genres ≈ 1
}

export interface RecentTrack {
  track_id: string;
  title: string;
  artist: string;
  played_at: string; // ISO
  album_art?: string;
}

export interface UserStats {
  user_id: string;
  display_name: string;
  computed_at: string; // ISO
  top_tracks: TopTrack[];
  top_artists: TopArtist[];
  top_genres: TopGenre[];
  streak_days: number;
  total_plays_30d: number;
  cluster_id: number;
  cluster_label: string; // e.g. "mellow indie", "high-energy mainstream"
  // Optional cross-user feed payload + avatar — populated when stats are
  // synced to the shared backend so other users can see them.
  recent_tracks?: RecentTrack[];
  avatar_url?: string;
}

export interface CompatScore {
  a: string;
  b: string;
  score: number; // 0–1, frontend renders as 0–100%
  shared_genres: string[];
  shared_artists: string[];
}
