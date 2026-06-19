// Client for the Brink shared-state backend (/api/state on Vercel).
// Falls back gracefully when the backend is unreachable (e.g. running
// `vite dev` locally where there's no serverless runtime in front of us).

import type { UserStats } from "../types/stats";

export interface ReactionCounts {
  heart: number;
  fire: number;
  sparkle: number;
}

export interface BackendState {
  users: Record<string, UserStats>;
  reactions: Record<string, ReactionCounts>;
}

const EMPTY: BackendState = { users: {}, reactions: {} };

const BASE = "/api/state";
const FRESH_MS = 30_000;

let cache: { at: number; state: BackendState } | null = null;
let inflight: Promise<BackendState> | null = null;

export function getCachedState(): BackendState {
  return cache?.state ?? EMPTY;
}

export async function getBackendState(force = false): Promise<BackendState> {
  if (!force && cache && Date.now() - cache.at < FRESH_MS) return cache.state;
  if (inflight && !force) return inflight;
  inflight = (async () => {
    try {
      const res = await fetch(BASE, { method: "GET" });
      if (!res.ok) throw new Error(`/api/state GET ${res.status}`);
      const state = (await res.json()) as BackendState;
      cache = { at: Date.now(), state };
      return state;
    } catch (e) {
      // Backend missing (local dev or transient) — keep last good copy.
      if (!cache) console.info("[brink] backend not reachable, using mocks only:", e);
      return cache?.state ?? EMPTY;
    } finally {
      inflight = null;
    }
  })();
  return inflight;
}

export async function upsertUserStats(stats: UserStats): Promise<void> {
  try {
    const res = await fetch(BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "upsertUser", payload: stats }),
    });
    if (!res.ok) {
      console.warn("[brink] upsertUserStats failed:", res.status, await res.text().catch(() => ""));
      return;
    }
    const state = (await res.json()) as BackendState;
    cache = { at: Date.now(), state };
  } catch (e) {
    console.warn("[brink] upsertUserStats network error:", e);
  }
}

export async function reactToPost(
  postId: string,
  kind: keyof ReactionCounts,
  delta: 1 | -1,
): Promise<ReactionCounts> {
  try {
    const res = await fetch(BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ action: "react", payload: { postId, kind, delta } }),
    });
    if (!res.ok) throw new Error(`react ${res.status}`);
    const state = (await res.json()) as BackendState;
    cache = { at: Date.now(), state };
    return state.reactions[postId] ?? { heart: 0, fire: 0, sparkle: 0 };
  } catch (e) {
    console.warn("[brink] reactToPost failed:", e);
    // Optimistic local update only.
    const local = cache?.state ?? EMPTY;
    local.reactions[postId] = local.reactions[postId] ?? { heart: 0, fire: 0, sparkle: 0 };
    local.reactions[postId][kind] = Math.max(0, local.reactions[postId][kind] + delta);
    return local.reactions[postId];
  }
}
