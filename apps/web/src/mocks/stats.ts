import type { UserStats, CompatScore } from "../types/stats";

// Mock data shaped exactly like Jonah's pipeline output.
// Real numbers come from the Python K-means + aggregation job once it's deployed.

export const mockUserStats: Record<string, UserStats> = {
  me: {
    user_id: "me",
    display_name: "Sebastian A.",
    computed_at: new Date().toISOString(),
    streak_days: 14,
    total_plays_30d: 312,
    cluster_id: 2,
    cluster_label: "mellow indie",
    top_tracks: [
      { track_id: "t3", title: "Apocalypse", artist: "Cigarettes After Sex", play_count: 24 },
      { track_id: "t1", title: "Mystery of Love", artist: "Sufjan Stevens", play_count: 19 },
      { track_id: "t9", title: "Motion Sickness", artist: "Phoebe Bridgers", play_count: 17 },
      { track_id: "t11", title: "The Night We Met", artist: "Lord Huron", play_count: 15 },
      { track_id: "t14", title: "Heat Waves", artist: "Glass Animals", play_count: 12 },
    ],
    top_artists: [
      { artist_id: "a1", name: "Phoebe Bridgers", play_count: 41 },
      { artist_id: "a2", name: "Cigarettes After Sex", play_count: 35 },
      { artist_id: "a3", name: "Sufjan Stevens", play_count: 28 },
      { artist_id: "a4", name: "Bon Iver", play_count: 22 },
      { artist_id: "a5", name: "The National", play_count: 18 },
    ],
    top_genres: [
      { name: "indie folk", weight: 0.32 },
      { name: "dream pop", weight: 0.21 },
      { name: "indie rock", weight: 0.17 },
      { name: "ambient", weight: 0.12 },
      { name: "alt rock", weight: 0.10 },
      { name: "shoegaze", weight: 0.08 },
    ],
  },

  u1: {
    user_id: "u1",
    display_name: "Andrea V.",
    computed_at: new Date().toISOString(),
    streak_days: 31,
    total_plays_30d: 487,
    cluster_id: 2,
    cluster_label: "mellow indie",
    top_tracks: [
      { track_id: "t1", title: "Mystery of Love", artist: "Sufjan Stevens", play_count: 28 },
      { track_id: "t20", title: "Skinny Love", artist: "Bon Iver", play_count: 22 },
      { track_id: "t9", title: "Motion Sickness", artist: "Phoebe Bridgers", play_count: 20 },
      { track_id: "t22", title: "Holocene", artist: "Bon Iver", play_count: 18 },
      { track_id: "t23", title: "Vincent", artist: "Don McLean", play_count: 14 },
    ],
    top_artists: [
      { artist_id: "a4", name: "Bon Iver", play_count: 52 },
      { artist_id: "a3", name: "Sufjan Stevens", play_count: 38 },
      { artist_id: "a1", name: "Phoebe Bridgers", play_count: 30 },
      { artist_id: "a6", name: "Fleet Foxes", play_count: 25 },
    ],
    top_genres: [
      { name: "indie folk", weight: 0.41 },
      { name: "folk", weight: 0.22 },
      { name: "indie rock", weight: 0.14 },
      { name: "dream pop", weight: 0.11 },
      { name: "chamber pop", weight: 0.07 },
      { name: "ambient", weight: 0.05 },
    ],
  },

  u2: {
    user_id: "u2",
    display_name: "Jonah W.",
    computed_at: new Date().toISOString(),
    streak_days: 7,
    total_plays_30d: 198,
    cluster_id: 4,
    cluster_label: "high-energy mainstream",
    top_tracks: [
      { track_id: "t2", title: "Redbone", artist: "Childish Gambino", play_count: 31 },
      { track_id: "t30", title: "Sicko Mode", artist: "Travis Scott", play_count: 24 },
      { track_id: "t31", title: "DNA.", artist: "Kendrick Lamar", play_count: 19 },
      { track_id: "t32", title: "Bad Guy", artist: "Billie Eilish", play_count: 15 },
      { track_id: "t33", title: "Levitating", artist: "Dua Lipa", play_count: 12 },
    ],
    top_artists: [
      { artist_id: "a10", name: "Kendrick Lamar", play_count: 44 },
      { artist_id: "a11", name: "Travis Scott", play_count: 32 },
      { artist_id: "a12", name: "Childish Gambino", play_count: 31 },
      { artist_id: "a13", name: "Drake", play_count: 21 },
    ],
    top_genres: [
      { name: "hip hop", weight: 0.38 },
      { name: "trap", weight: 0.21 },
      { name: "r&b", weight: 0.17 },
      { name: "pop", weight: 0.14 },
      { name: "alternative", weight: 0.10 },
    ],
  },
};

// Mock compat scores. Real values = cosine similarity of taste vectors (Jonah).
export const mockCompat: Record<string, CompatScore> = {
  "me::u1": {
    a: "me",
    b: "u1",
    score: 0.87,
    shared_genres: ["indie folk", "dream pop", "indie rock", "ambient"],
    shared_artists: ["Phoebe Bridgers", "Sufjan Stevens", "Bon Iver"],
  },
  "me::u2": {
    a: "me",
    b: "u2",
    score: 0.23,
    shared_genres: ["alternative"],
    shared_artists: [],
  },
  "me::me": {
    a: "me",
    b: "me",
    score: 1.0,
    shared_genres: [],
    shared_artists: [],
  },
};

export function compatKey(a: string, b: string): string {
  return `${a}::${b}`;
}
