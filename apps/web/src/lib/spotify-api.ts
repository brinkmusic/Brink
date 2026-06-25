// Thin wrapper over the Spotify Web API. Only the endpoints Brink needs.
// Docs: https://developer.spotify.com/documentation/web-api

import { supabase } from "./supabase";

const API = "https://api.spotify.com/v1";

// The Spotify access token comes from the Supabase session (provider_token),
// set when the user signs in with Spotify. Valid for ~1h within a session.
async function spotifyToken(): Promise<string | null> {
  const { data } = await supabase.auth.getSession();
  return data.session?.provider_token ?? null;
}

async function spotify<T>(path: string, params?: Record<string, string | number>): Promise<T> {
  const token = await spotifyToken();
  if (!token) throw new Error("No Spotify access — sign in with Spotify");
  const url = new URL(`${API}${path}`);
  if (params) {
    for (const [k, v] of Object.entries(params)) url.searchParams.set(k, String(v));
  }
  const res = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
  if (res.status === 401) {
    throw new Error("Spotify session expired — sign in again");
  }
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`Spotify ${path} ${res.status}: ${body}`);
  }
  return (await res.json()) as T;
}

// ---- Response shapes ----------------------------------------------------

export interface SpotifyUser {
  id: string;
  display_name: string;
  email?: string;
  images: { url: string; width?: number; height?: number }[];
}

export interface SpotifyArtistRef {
  id: string;
  name: string;
}

export interface SpotifyArtist {
  id: string;
  name: string;
  genres: string[];
  popularity: number;
  images: { url: string }[];
}

export interface SpotifyTrack {
  id: string;
  name: string;
  popularity: number;
  duration_ms: number;
  artists: SpotifyArtistRef[];
  album: {
    id: string;
    name: string;
    images: { url: string; width?: number; height?: number }[];
  };
  external_urls: { spotify: string };
}

export interface PlayHistoryItem {
  track: SpotifyTrack;
  played_at: string; // ISO
}

interface PagedResponse<T> {
  items: T[];
}

// ---- Endpoints ----------------------------------------------------------

export function getMe() {
  return spotify<SpotifyUser>("/me");
}

export async function getTopTracks(timeRange: "short_term" | "medium_term" | "long_term" = "short_term", limit = 20) {
  const res = await spotify<PagedResponse<SpotifyTrack>>("/me/top/tracks", {
    time_range: timeRange,
    limit,
  });
  return res.items;
}

export async function getTopArtists(timeRange: "short_term" | "medium_term" | "long_term" = "short_term", limit = 20) {
  const res = await spotify<PagedResponse<SpotifyArtist>>("/me/top/artists", {
    time_range: timeRange,
    limit,
  });
  return res.items;
}

export async function getRecentlyPlayed(limit = 50) {
  const res = await spotify<PagedResponse<PlayHistoryItem>>("/me/player/recently-played", { limit });
  return res.items;
}
