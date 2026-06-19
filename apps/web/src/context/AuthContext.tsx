import { createContext, useCallback, useContext, useEffect, useState } from "react";
import {
  beginLogin,
  isConfigured,
  loadToken,
  logout as clearToken,
} from "../lib/spotify-auth";
import { getMe, type SpotifyUser } from "../lib/spotify-api";

type Status = "loading" | "unauthenticated" | "authenticated" | "misconfigured";

interface AuthValue {
  status: Status;
  profile: SpotifyUser | null;
  error: string | null;
  login: () => Promise<void>;
  logout: () => void;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<Status>("loading");
  const [profile, setProfile] = useState<SpotifyUser | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    if (!isConfigured()) {
      setStatus("misconfigured");
      return;
    }
    const tok = loadToken();
    if (!tok) {
      setStatus("unauthenticated");
      setProfile(null);
      return;
    }
    try {
      const me = await getMe();
      setProfile(me);
      setStatus("authenticated");
      setError(null);
    } catch (e) {
      setProfile(null);
      setStatus("unauthenticated");
      setError(e instanceof Error ? e.message : "Auth failed");
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async () => {
    try {
      await beginLogin();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Login failed");
    }
  }, []);

  const logout = useCallback(() => {
    clearToken();
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
