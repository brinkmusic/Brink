import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { completeLogin } from "../lib/spotify-auth";
import { useAuth } from "../context/AuthContext";

export default function CallbackPage() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get("code");
    const errParam = params.get("error");
    if (errParam) {
      setError(errParam);
      return;
    }
    if (!code) {
      setError("No auth code returned from Spotify");
      return;
    }
    (async () => {
      try {
        await completeLogin(code);
        await refresh();
        navigate("/feed", { replace: true });
      } catch (e) {
        setError(e instanceof Error ? e.message : "Token exchange failed");
      }
    })();
  }, [navigate, refresh]);

  if (error) {
    return (
      <div className="mx-auto max-w-md p-8 text-center">
        <h1 className="text-lg font-semibold text-brink-hot">Login failed</h1>
        <p className="mt-2 text-sm text-brink-mute">{error}</p>
        <button
          onClick={() => navigate("/")}
          className="mt-6 rounded-full bg-brink-accent px-4 py-2 text-sm font-medium text-brink-ink"
        >
          Back to start
        </button>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-md p-8 text-center text-sm text-brink-mute">
      Signing you in with Spotify…
    </div>
  );
}
