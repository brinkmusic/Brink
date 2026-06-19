import type { Post } from "../components/PostCard";

// Each post is enriched by Jonah's analytics pipeline with: genre tags + listener cluster label.
// Mocked here, will come from Postgres user_stats / track_genres join in production.
export const mockFeed: Post[] = [
  {
    id: "p1",
    user: { id: "u1", name: "Andrea V.", clusterLabel: "mellow indie" },
    track: {
      id: "t1",
      title: "Mystery of Love",
      artist: "Sufjan Stevens",
      genres: ["indie folk", "chamber pop"],
    },
    playedAt: new Date(Date.now() - 5 * 60_000).toISOString(),
    reactions: { heart: 12, fire: 3, sparkle: 7 },
    commentCount: 2,
  },
  {
    id: "p2",
    user: { id: "u2", name: "Jonah W.", clusterLabel: "high-energy mainstream" },
    track: {
      id: "t2",
      title: "Redbone",
      artist: "Childish Gambino",
      genres: ["hip hop", "r&b", "funk"],
    },
    playedAt: new Date(Date.now() - 42 * 60_000).toISOString(),
    reactions: { heart: 5, fire: 9, sparkle: 1 },
    commentCount: 0,
  },
  {
    id: "p3",
    user: { id: "me", name: "Sebastian A.", clusterLabel: "mellow indie" },
    track: {
      id: "t3",
      title: "Apocalypse",
      artist: "Cigarettes After Sex",
      genres: ["dream pop", "shoegaze"],
    },
    playedAt: new Date(Date.now() - 3 * 3600_000).toISOString(),
    reactions: { heart: 21, fire: 4, sparkle: 11 },
    commentCount: 5,
  },
];
