import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { Session } from "@supabase/supabase-js";
import { supabase } from "../lib/supabase";
import { getMe, type SpotifyUser } from "../lib/spotify-api";

const SPOTIFY_SCOPES =
  "user-read-email user-read-recently-played user-top-read user-read-currently-playing";

const configured = !!(
  import.meta.env.VITE_SUPABASE_URL && import.meta.env.VITE_SUPABASE_ANON_KEY
);

type Status = "loading" | "unauthenticated" | "authenticated" | "misconfigured";

interface AuthValue {
  status: Status;
  profile: SpotifyUser | null;
  error: string | null;
  login: () => Promise<void>;
  logout: () => Promise<void>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

// Supabase exposes the Spotify provider tokens only once, in the session right
// after OAuth. Hand them to our backend so it can refresh + pull plays later.
async function captureSpotifyTokens(session: Session) {
  if (!session.provider_refresh_token || !session.provider_token) return;
  try {
    await fetch("/api/auth/capture-spotify", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${session.access_token}`,
      },
      body: JSON.stringify({
        refresh_token: session.provider_refresh_token,
        access_token: session.provider_token,
        scopes: SPOTIFY_SCOPES,
      }),
    });
  } catch {
    // best-effort: the /api functions aren't served under plain `vite dev`
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>(configured ? "loading" : "misconfigured");
  const [profile, setProfile] = useState<SpotifyUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadProfile = useCallback(async () => {
    try {
      setProfile(await getMe());
    } catch {
      setProfile(null); // email-only users, or no Spotify provider token
    }
  }, []);

  const refresh = useCallback(async () => {
    if (!configured) return;
    const { data } = await supabase.auth.getSession();
    if (data.session) {
      setStatus("authenticated");
      await loadProfile();
    } else {
      setStatus("unauthenticated");
      setProfile(null);
    }
  }, [loadProfile]);

  useEffect(() => {
    if (!configured) return;
    const { data: sub } = supabase.auth.onAuthStateChange((event, session) => {
      if (session) {
        setStatus("authenticated");
        if (event === "SIGNED_IN") void captureSpotifyTokens(session);
        void loadProfile();
      } else {
        setStatus("unauthenticated");
        setProfile(null);
      }
    });
    return () => sub.subscription.unsubscribe();
  }, [loadProfile]);

  const login = useCallback(async () => {
    setError(null);
    const { error: err } = await supabase.auth.signInWithOAuth({
      provider: "spotify",
      options: { scopes: SPOTIFY_SCOPES, redirectTo: `${window.location.origin}/callback` },
    });
    if (err) setError(err.message);
  }, []);

  const logout = useCallback(async () => {
    await supabase.auth.signOut();
    setProfile(null);
    setStatus("unauthenticated");
  }, []);

  return (
    <AuthContext.Provider value={{ status, profile, error, login, logout, refresh }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
