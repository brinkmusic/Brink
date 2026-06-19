// Thin API client. Swap MOCK to false once Andrea publishes the backend.
import { mockFeed } from "../mocks/feed";
import { mockUserStats, mockCompat, compatKey } from "../mocks/stats";
import type { Post } from "../components/PostCard";
import type { UserStats, CompatScore } from "../types/stats";

const MOCK = true;
const BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:4000";

// Simulate network latency so loading skeletons get exercised during dev.
const delay = (ms: number) => new Promise((r) => setTimeout(r, ms));

export async function getFeed(): Promise<Post[]> {
  if (MOCK) {
    await delay(250);
    return mockFeed;
  }
  const res = await fetch(`${BASE}/api/feed`);
  if (!res.ok) throw new Error(`Feed request failed: ${res.status}`);
  return res.json();
}

export async function getUserStats(userId: string): Promise<UserStats> {
  if (MOCK) {
    await delay(400);
    return mockUserStats[userId] ?? mockUserStats["me"];
  }
  const res = await fetch(`${BASE}/api/users/${userId}/stats`);
  if (!res.ok) throw new Error(`Stats request failed: ${res.status}`);
  return res.json();
}

export async function getCompat(a: string, b: string): Promise<CompatScore | null> {
  if (a === b) return null;
  if (MOCK) {
    await delay(300);
    return mockCompat[compatKey(a, b)] ?? mockCompat[compatKey(b, a)] ?? null;
  }
  const res = await fetch(`${BASE}/api/compat?a=${a}&b=${b}`);
  if (!res.ok) throw new Error(`Compat request failed: ${res.status}`);
  return res.json();
}
