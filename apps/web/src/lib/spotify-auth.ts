// Spotify OAuth 2.0 with PKCE (Proof Key for Code Exchange).
// Why PKCE: lets a public client (browser SPA) authenticate without exposing a client secret.
// Reference: https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow

const AUTH_URL = "https://accounts.spotify.com/authorize";
const TOKEN_URL = "https://accounts.spotify.com/api/token";

const CLIENT_ID = import.meta.env.VITE_SPOTIFY_CLIENT_ID ?? "";
const REDIRECT_URI =
  import.meta.env.VITE_SPOTIFY_REDIRECT_URI ?? `${window.location.origin}/callback`;

const SCOPES = [
  "user-read-private",
  "user-read-email",
  "user-read-recently-played",
  "user-top-read",
  "user-read-currently-playing",
].join(" ");

const LS_TOKEN = "brink.spotify.token";
const SS_VERIFIER = "brink.spotify.pkce_verifier";

export interface StoredToken {
  access_token: string;
  refresh_token: string;
  expires_at: number; // epoch ms
}

export function isConfigured(): boolean {
  return CLIENT_ID.length > 0;
}

// ---- PKCE helpers --------------------------------------------------------

function base64UrlEncode(bytes: ArrayBuffer): string {
  const s = String.fromCharCode(...new Uint8Array(bytes));
  return btoa(s).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
}

function randomString(len = 64): string {
  const alphabet =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-~.";
  const arr = new Uint8Array(len);
  crypto.getRandomValues(arr);
  return Array.from(arr, (n) => alphabet[n % alphabet.length]).join("");
}

async function sha256(text: string): Promise<ArrayBuffer> {
  return crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
}

// ---- Login -> Spotify redirect ------------------------------------------

export async function beginLogin(): Promise<void> {
  if (!isConfigured()) {
    throw new Error(
      "VITE_SPOTIFY_CLIENT_ID is not set. Copy apps/web/.env.example to apps/web/.env.local and fill it in.",
    );
  }
  const verifier = randomString(64);
  const challenge = base64UrlEncode(await sha256(verifier));
  sessionStorage.setItem(SS_VERIFIER, verifier);

  const params = new URLSearchParams({
    response_type: "code",
    client_id: CLIENT_ID,
    scope: SCOPES,
    redirect_uri: REDIRECT_URI,
    code_challenge_method: "S256",
    code_challenge: challenge,
  });
  window.location.assign(`${AUTH_URL}?${params}`);
}

// ---- Callback: exchange code -> tokens ----------------------------------

export async function completeLogin(code: string): Promise<StoredToken> {
  const verifier = sessionStorage.getItem(SS_VERIFIER);
  if (!verifier) throw new Error("Missing PKCE verifier — did you start the login flow?");

  const body = new URLSearchParams({
    grant_type: "authorization_code",
    code,
    redirect_uri: REDIRECT_URI,
    client_id: CLIENT_ID,
    code_verifier: verifier,
  });
  const res = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) {
    const err = await res.text();
    throw new Error(`Token exchange failed: ${res.status} ${err}`);
  }
  const json = (await res.json()) as {
    access_token: string;
    refresh_token: string;
    expires_in: number;
  };
  const token: StoredToken = {
    access_token: json.access_token,
    refresh_token: json.refresh_token,
    expires_at: Date.now() + json.expires_in * 1000,
  };
  saveToken(token);
  sessionStorage.removeItem(SS_VERIFIER);
  return token;
}

// ---- Refresh ------------------------------------------------------------

async function refresh(token: StoredToken): Promise<StoredToken> {
  const body = new URLSearchParams({
    grant_type: "refresh_token",
    refresh_token: token.refresh_token,
    client_id: CLIENT_ID,
  });
  const res = await fetch(TOKEN_URL, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body,
  });
  if (!res.ok) throw new Error(`Refresh failed: ${res.status}`);
  const json = (await res.json()) as {
    access_token: string;
    refresh_token?: string;
    expires_in: number;
  };
  const next: StoredToken = {
    access_token: json.access_token,
    refresh_token: json.refresh_token ?? token.refresh_token,
    expires_at: Date.now() + json.expires_in * 1000,
  };
  saveToken(next);
  return next;
}

// ---- Token storage ------------------------------------------------------

function saveToken(token: StoredToken) {
  localStorage.setItem(LS_TOKEN, JSON.stringify(token));
}

export function loadToken(): StoredToken | null {
  const raw = localStorage.getItem(LS_TOKEN);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredToken;
  } catch {
    return null;
  }
}

export function logout(): void {
  localStorage.removeItem(LS_TOKEN);
}

// Returns a fresh access_token, refreshing if it's within 60s of expiry.
export async function getAccessToken(): Promise<string | null> {
  let token = loadToken();
  if (!token) return null;
  if (token.expires_at - Date.now() < 60_000) {
    try {
      token = await refresh(token);
    } catch {
      logout();
      return null;
    }
  }
  return token.access_token;
}
