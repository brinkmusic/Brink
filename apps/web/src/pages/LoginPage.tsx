import { Music2, Sparkles, Users, BarChart3 } from "lucide-react";
import { useAuth } from "../context/AuthContext";

export default function LoginPage() {
  const { status, login, error } = useAuth();

  return (
    <div className="mx-auto max-w-2xl px-4 py-12">
      <div className="rounded-3xl border border-brink-line bg-gradient-to-br from-brink-panel to-brink-ink p-10">
        <div className="flex items-center gap-3">
          <span className="text-3xl font-bold tracking-tight text-brink-accent">brink</span>
          <span className="text-xs uppercase tracking-wider text-brink-mute">
            music-native social
          </span>
        </div>

        <h1 className="mt-6 text-3xl font-bold leading-tight">
          Your listening is your identity.
        </h1>
        <p className="mt-3 max-w-md text-brink-mute">
          Sign in with Spotify and Brink turns your last 30 days of plays into a live
          Wrapped — top tracks, top artists, taste cluster, and a compatibility score
          with anyone else on the platform.
        </p>

        <button
          onClick={() => void login()}
          disabled={status === "loading" || status === "misconfigured"}
          className="mt-8 inline-flex items-center gap-2 rounded-full bg-[#1DB954] px-6 py-3 text-sm font-semibold text-black transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <Music2 size={18} /> Sign in with Spotify
        </button>

        {status === "misconfigured" && (
          <p className="mt-4 max-w-lg rounded-lg border border-brink-hot/40 bg-brink-hot/10 p-3 text-xs text-brink-hot">
            <strong>Setup needed:</strong> create <code>apps/web/.env.local</code>{" "}
            (copy from <code>.env.example</code>) and set{" "}
            <code>VITE_SPOTIFY_CLIENT_ID</code>. Also add{" "}
            <code>http://127.0.0.1:5173/callback</code> to your Spotify app's
            Redirect URIs at developer.spotify.com/dashboard, and open the app
            at <code>http://127.0.0.1:5173</code> (not localhost).
          </p>
        )}

        {error && status !== "misconfigured" && (
          <p className="mt-4 text-xs text-brink-hot">{error}</p>
        )}

        <div className="mt-10 grid gap-4 sm:grid-cols-3">
          <Feature icon={<BarChart3 size={18} />} title="Wrapped, always-on">
            Top tracks, artists, genres, and listening streak computed from your real
            Spotify data — no waiting until December.
          </Feature>
          <Feature icon={<Sparkles size={18} />} title="Taste cluster">
            We classify your listening into a cluster like <em>mellow indie</em> or{" "}
            <em>high-energy mainstream</em> so you can see at a glance how you listen.
          </Feature>
          <Feature icon={<Users size={18} />} title="Compatibility score">
            Cosine similarity over genre vectors gives you a 0–100% match with any
            other user.
          </Feature>
        </div>

        <p className="mt-8 text-[11px] text-brink-mute">
          Brink only reads listening data; it never posts on your behalf. Auth uses
          PKCE — your credentials never touch our servers.
        </p>
      </div>
    </div>
  );
}

function Feature({
  icon,
  title,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-brink-line bg-brink-panel p-4">
      <div className="flex items-center gap-2 text-brink-accent">{icon}</div>
      <h3 className="mt-2 text-sm font-semibold">{title}</h3>
      <p className="mt-1 text-xs leading-relaxed text-brink-mute">{children}</p>
    </div>
  );
}
