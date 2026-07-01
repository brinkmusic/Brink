import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { supabase } from "../lib/supabase";

// Supabase's client auto-detects the OAuth response in the URL and exchanges it
// for a session. We just wait for that session, then move on to the feed.
export default function CallbackPage() {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const hash = new URLSearchParams(window.location.hash.replace(/^#/, "?"));
    const search = new URLSearchParams(window.location.search);
    const errDesc = search.get("error_description") || hash.get("error_description");
    if (errDesc) setError(errDesc);

    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) navigate("/feed", { replace: true });
    });
    supabase.auth.getSession().then(({ data }) => {
      if (data.session) navigate("/feed", { replace: true });
    });
    return () => sub.subscription.unsubscribe();
  }, [navigate]);

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
