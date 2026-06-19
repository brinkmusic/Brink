import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { Mic2, MessageCircle, Heart, Music2 } from "lucide-react";
import { getMyStats } from "../lib/data";
import type { TopArtist, UserStats } from "../types/stats";

export default function ArtistPage() {
  const { artistId } = useParams();
  const [stats, setStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getMyStats()
      .then(setStats)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="space-y-3">
        <div className="h-24 animate-pulse rounded-2xl bg-brink-panel" />
        <div className="h-48 animate-pulse rounded-2xl bg-brink-panel" />
      </div>
    );
  }

  // INDEX MODE — no specific artist selected
  if (!artistId) {
    return (
      <section className="space-y-6">
        <header className="rounded-2xl border border-brink-line bg-brink-panel p-5">
          <div className="flex items-center gap-3">
            <div className="grid h-10 w-10 place-items-center rounded-xl bg-brink-accent/20 text-brink-accent">
              <Mic2 size={18} />
            </div>
            <div>
              <h1 className="text-lg font-semibold">Artists you listen to</h1>
              <p className="text-xs text-brink-mute">
                Click any artist to see their Brink page — top tracks, fan stats, and behind-the-scenes posts.
              </p>
            </div>
          </div>
        </header>

        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          {(stats?.top_artists ?? []).map((a) => (
            <Link
              key={a.artist_id}
              to={`/artist/${a.artist_id}`}
              className="group rounded-2xl border border-brink-line bg-brink-panel p-4 transition hover:border-brink-accent/60"
            >
              <div className="mx-auto h-20 w-20 overflow-hidden rounded-full bg-brink-line">
                {a.image && (
                  <img
                    src={a.image}
                    alt=""
                    className="h-full w-full object-cover transition group-hover:scale-105"
                  />
                )}
              </div>
              <p className="mt-3 truncate text-center text-sm font-medium">{a.name}</p>
              <p className="mt-0.5 text-center text-[11px] text-brink-mute">
                rank #{stats!.top_artists.indexOf(a) + 1}
              </p>
            </Link>
          ))}
        </div>
      </section>
    );
  }

  // DETAIL MODE — specific artist
  const artist =
    stats?.top_artists.find((a) => a.artist_id === artistId) ??
    ({
      artist_id: artistId,
      name: artistId,
      play_count: 0,
    } satisfies TopArtist);
  const rank = stats?.top_artists.findIndex((a) => a.artist_id === artistId) ?? -1;
  const tracksByArtist =
    stats?.top_tracks.filter((t) => t.artist.toLowerCase().includes(artist.name.toLowerCase())) ?? [];

  // Synthetic but plausible fan metrics so the page feels real.
  const followers = 12_400 + (artist.artist_id.charCodeAt(0) % 9) * 4_300;
  const monthly = Math.round(followers * (1.6 + (artist.artist_id.charCodeAt(1) % 5) / 10));
  const fans30d = 38 + (artist.artist_id.charCodeAt(2) % 7) * 11;

  return (
    <section className="space-y-6">
      <header className="flex items-center gap-4 rounded-2xl border border-brink-line bg-brink-panel p-5">
        <div className="h-20 w-20 shrink-0 overflow-hidden rounded-2xl bg-brink-line">
          {artist.image && <img src={artist.image} alt="" className="h-full w-full object-cover" />}
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-xs uppercase tracking-wide text-brink-mute">Artist</p>
          <h1 className="truncate text-xl font-semibold">{artist.name}</h1>
          <div className="mt-2 flex flex-wrap gap-2 text-xs">
            {rank >= 0 && (
              <span className="rounded-full bg-brink-accent/15 px-2 py-0.5 text-brink-accent">
                Your #{rank + 1} artist
              </span>
            )}
            <span className="rounded-full border border-brink-line bg-brink-ink px-2 py-0.5 text-brink-mute">
              {followers.toLocaleString()} followers
            </span>
            <span className="rounded-full border border-brink-line bg-brink-ink px-2 py-0.5 text-brink-mute">
              {monthly.toLocaleString()} monthly listeners
            </span>
          </div>
        </div>
        <button className="shrink-0 rounded-full bg-brink-accent px-4 py-2 text-sm font-medium text-brink-ink hover:opacity-90">
          Follow
        </button>
      </header>

      <div className="grid grid-cols-3 gap-3">
        <Tile label="On Brink · 30d" value={`${fans30d} fans`} />
        <Tile label="Avg. plays / fan" value="14.2" />
        <Tile label="Cluster overlap" value={`${72 + (rank % 5)}%`} />
      </div>

      <Panel title="Your top tracks by this artist">
        {tracksByArtist.length > 0 ? (
          <ol className="divide-y divide-brink-line">
            {tracksByArtist.map((t, i) => (
              <li key={t.track_id} className="flex items-center gap-3 py-2.5">
                <span className="w-5 text-right text-sm font-bold text-brink-mute">{i + 1}</span>
                <div className="h-10 w-10 shrink-0 overflow-hidden rounded-md bg-brink-line">
                  {t.album_art && <img src={t.album_art} alt="" className="h-full w-full object-cover" />}
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{t.title}</p>
                </div>
                <span className="text-xs text-brink-mute">{t.play_count} plays</span>
              </li>
            ))}
          </ol>
        ) : (
          <p className="text-sm text-brink-mute">
            No tracks from this artist in your top 8 right now.
          </p>
        )}
      </Panel>

      <Panel title="Behind-the-scenes · sample posts">
        <ul className="space-y-3">
          {SAMPLE_BTS.map((p) => (
            <li key={p.id} className="rounded-xl border border-brink-line bg-brink-ink p-3">
              <div className="flex items-center gap-2 text-xs text-brink-mute">
                <Music2 size={12} /> {p.context}
              </div>
              <p className="mt-1 text-sm">{p.caption}</p>
              <div className="mt-2 flex gap-3 text-xs text-brink-mute">
                <span className="inline-flex items-center gap-1">
                  <Heart size={12} /> {p.hearts}
                </span>
                <span className="inline-flex items-center gap-1">
                  <MessageCircle size={12} /> {p.comments}
                </span>
              </div>
            </li>
          ))}
        </ul>
        <p className="mt-3 text-[11px] text-brink-mute">
          Artist BTS portal is wireframed for Week 4 — real artists post audio snippets,
          studio photos, and short clips tied to a Spotify track id.
        </p>
      </Panel>

      <Link to="/artist" className="block text-xs text-brink-accent hover:underline">
        ← Back to all artists
      </Link>
    </section>
  );
}

const SAMPLE_BTS = [
  {
    id: "p1",
    context: "Studio · linked to Track #2",
    caption: "Re-cut the bridge today. Trumpets stay. Strings get a second pass tomorrow.",
    hearts: 142,
    comments: 18,
  },
  {
    id: "p2",
    context: "Tour · linked to Album",
    caption: "Soundcheck in Montreal. Crowd's already inside the lobby — wild.",
    hearts: 312,
    comments: 47,
  },
  {
    id: "p3",
    context: "Demo",
    caption: "Idea I had at 3am. Honest opinion: does the chorus drag?",
    hearts: 89,
    comments: 64,
  },
];

function Tile({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-brink-line bg-brink-panel p-4">
      <p className="text-[11px] uppercase tracking-wide text-brink-mute">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
    </div>
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
