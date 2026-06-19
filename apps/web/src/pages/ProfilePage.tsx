import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Flame, Sparkles, ArrowUpRight } from "lucide-react";
import CompatDonut from "../components/CompatDonut";
import StreakHeatmap from "../components/StreakHeatmap";
import { getStatsFor, getCompatBetween } from "../lib/data";
import type { UserStats, CompatScore } from "../types/stats";

const VIEWER_ID = "me";

export default function ProfilePage() {
  const { userId = "me" } = useParams();
  const [stats, setStats] = useState<UserStats | null>(null);
  const [compat, setCompat] = useState<CompatScore | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([getStatsFor(userId), getCompatBetween(VIEWER_ID, userId)])
      .then(([s, c]) => {
        setStats(s);
        setCompat(c);
      })
      .catch((err) => {
        console.error(err);
        setError(err instanceof Error ? err.message : String(err));
      })
      .finally(() => setLoading(false));
  }, [userId]);

  if (loading) return <ProfileSkeleton />;
  if (error || !stats) {
    return (
      <div className="rounded-2xl border border-brink-line bg-brink-panel p-6 text-sm text-brink-mute">
        <p className="font-semibold text-brink-text">Couldn't load profile</p>
        <p className="mt-1">{error ?? "No data returned."}</p>
        <p className="mt-3 text-xs">
          If you just signed up the Spotify app, your account needs to be added under
          User Management in the Spotify developer dashboard before live data works.
        </p>
      </div>
    );
  }

  const isSelf = userId === VIEWER_ID;

  return (
    <section className="space-y-6">
      {/* HEADER */}
      <header className="flex items-center gap-4 rounded-2xl border border-brink-line bg-brink-panel p-5">
        <div className="h-16 w-16 shrink-0 rounded-full bg-gradient-to-br from-brink-accent to-brink-hot" aria-hidden />
        <div className="min-w-0 flex-1">
          <h1 className="truncate text-lg font-semibold">{stats.display_name}</h1>
          <p className="text-xs text-brink-mute">@{stats.user_id}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-xs">
            <span className="rounded-full bg-brink-accent/15 px-2 py-0.5 font-medium uppercase tracking-wide text-brink-accent">
              {stats.cluster_label}
            </span>
            <span className="text-brink-mute">
              · {stats.total_plays_30d} plays · 30d
            </span>
          </div>
        </div>
        {!isSelf && compat && (
          <div className="hidden shrink-0 sm:block">
            <CompatDonut score={compat.score} />
          </div>
        )}
        {!isSelf && (
          <button className="shrink-0 rounded-full bg-brink-accent px-4 py-2 text-sm font-medium text-brink-ink hover:opacity-90">
            Follow
          </button>
        )}
      </header>

      {/* COMPAT DETAIL */}
      {!isSelf && compat && (
        <div className="rounded-2xl border border-brink-line bg-brink-panel p-5">
          <div className="flex items-center gap-4">
            <div className="sm:hidden">
              <CompatDonut score={compat.score} size={72} stroke={8} />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-xs uppercase tracking-wide text-brink-mute">
                Taste compatibility · cosine similarity
              </p>
              <p className="mt-1 text-sm">
                You and {stats.display_name.split(" ")[0]} share{" "}
                <span className="font-semibold text-brink-text">
                  {compat.shared_genres.length}
                </span>{" "}
                genres
                {compat.shared_artists.length > 0 && (
                  <>
                    {" "}
                    and{" "}
                    <span className="font-semibold text-brink-text">
                      {compat.shared_artists.length}
                    </span>{" "}
                    top artists
                  </>
                )}
                .
              </p>
              {compat.shared_genres.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1">
                  {compat.shared_genres.map((g) => (
                    <span
                      key={g}
                      className="rounded-full border border-brink-accent/40 bg-brink-accent/10 px-2 py-0.5 text-[11px] text-brink-accent"
                    >
                      {g}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* STAT TILES */}
      <div className="grid grid-cols-2 gap-3">
        <StatTile
          icon={<Flame size={16} className="text-brink-hot" />}
          label="Listening streak"
          value={`${stats.streak_days} ${stats.streak_days === 1 ? "day" : "days"}`}
        />
        <StatTile
          icon={<Sparkles size={16} className="text-brink-accent" />}
          label="Taste cluster"
          value={`#${stats.cluster_id} · ${stats.cluster_label}`}
        />
      </div>

      {/* STREAK HEATMAP */}
      <Panel title="Activity">
        <StreakHeatmap streakDays={stats.streak_days} />
      </Panel>

      {/* TOP TRACKS */}
      <Panel title="Top Tracks · from your recent plays">
        <ol className="divide-y divide-brink-line">
          {stats.top_tracks.map((t, i) => (
            <li key={t.track_id} className="flex items-center gap-3 py-2.5">
              <span className="w-5 text-right text-sm font-bold text-brink-mute">
                {i + 1}
              </span>
              <div className="h-10 w-10 shrink-0 overflow-hidden rounded-md bg-brink-line">
                {t.album_art && (
                  <img src={t.album_art} alt="" className="h-full w-full object-cover" />
                )}
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{t.title}</p>
                <p className="truncate text-xs text-brink-mute">{t.artist}</p>
              </div>
              {t.play_count > 0 ? (
                <span className="shrink-0 text-[11px] text-brink-mute">
                  {t.play_count} {t.play_count === 1 ? "play" : "plays"}
                </span>
              ) : (
                <span
                  className="shrink-0 rounded-full border border-brink-line bg-brink-ink px-2 py-0.5 text-[10px] uppercase tracking-wide text-brink-mute"
                  title="From your 4-week top tracks — you haven't replayed this recently"
                >
                  top 4w
                </span>
              )}
              <ArrowUpRight size={14} className="shrink-0 text-brink-mute" />
            </li>
          ))}
        </ol>
      </Panel>

      {/* TOP ARTISTS */}
      <Panel title="Top Artists · last 4 weeks">
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-4">
          {stats.top_artists.slice(0, 4).map((a) => (
            <li
              key={a.artist_id}
              className="rounded-xl border border-brink-line bg-brink-ink p-3 text-center"
            >
              <div className="mx-auto h-12 w-12 overflow-hidden rounded-full bg-brink-line">
                {a.image && (
                  <img src={a.image} alt="" className="h-full w-full object-cover" />
                )}
              </div>
              <p className="mt-2 truncate text-xs font-medium">{a.name}</p>
            </li>
          ))}
        </ul>
      </Panel>

      {/* TOP GENRES */}
      <Panel title="Top Genres">
        <div className="flex flex-wrap items-baseline gap-2">
          {stats.top_genres.map((g) => {
            // Size pills by weight so the cloud feels weighted, not uniform.
            const size = 11 + Math.round(g.weight * 24);
            return (
              <span
                key={g.name}
                className="rounded-full border border-brink-line bg-brink-ink px-3 py-1 font-medium text-brink-text"
                style={{ fontSize: `${size}px`, lineHeight: 1.2 }}
                title={`${Math.round(g.weight * 100)}%`}
              >
                {g.name}
              </span>
            );
          })}
        </div>
        <p className="mt-3 text-[11px] text-brink-mute">
          Weighted by share of last 30 days of plays. Genres come from Spotify
          artist metadata, aggregated by the analytics pipeline.
        </p>
      </Panel>

      {/* FOOTER META */}
      <p className="text-[11px] text-brink-mute">
        Stats computed{" "}
        {new Date(stats.computed_at).toLocaleString(undefined, {
          dateStyle: "medium",
          timeStyle: "short",
        })}{" "}
        · derived from Spotify top-tracks / top-artists / recently-played ·{" "}
        <Link to="/profile/me" className="underline hover:text-brink-text">
          View your own profile
        </Link>
      </p>
    </section>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-brink-line bg-brink-panel p-5">
      <h2 className="mb-3 text-xs font-semibold uppercase tracking-wide text-brink-mute">
        {title}
      </h2>
      {children}
    </div>
  );
}

function StatTile({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-2xl border border-brink-line bg-brink-panel p-4">
      <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-brink-mute">
        {icon}
        {label}
      </div>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
  );
}

function ProfileSkeleton() {
  return (
    <div className="space-y-4">
      <div className="h-24 animate-pulse rounded-2xl bg-brink-panel" />
      <div className="grid grid-cols-2 gap-3">
        <div className="h-20 animate-pulse rounded-2xl bg-brink-panel" />
        <div className="h-20 animate-pulse rounded-2xl bg-brink-panel" />
      </div>
      <div className="h-40 animate-pulse rounded-2xl bg-brink-panel" />
      <div className="h-64 animate-pulse rounded-2xl bg-brink-panel" />
    </div>
  );
}
