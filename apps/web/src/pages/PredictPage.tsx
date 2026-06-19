// Predictions tab. Synthetic numbers, but every prediction is derived
// deterministically from the user's real stats so the demo holds together:
// re-running with the same stats produces the same numbers.

import { useEffect, useMemo, useState } from "react";
import { TrendingUp, Sparkles, Flame, Music2 } from "lucide-react";
import { getMyStats } from "../lib/data";
import { mockUserStats } from "../mocks/stats";
import { compatBetween } from "../lib/analytics";
import type { UserStats } from "../types/stats";

// Hand-curated genre adjacency map: which genres are "one step away" from each
// genre in our latent taste space. Used to recommend the next genre to explore.
const ADJACENT: Record<string, string[]> = {
  "indie folk": ["chamber pop", "americana", "indie rock"],
  "indie rock": ["shoegaze", "post-punk", "alt rock"],
  "dream pop": ["shoegaze", "bedroom pop", "ambient pop"],
  "alt rock": ["indie rock", "post-punk", "grunge"],
  "ambient": ["drone", "post-rock", "modern classical"],
  "shoegaze": ["dream pop", "noise pop", "post-rock"],
  "folk": ["indie folk", "americana", "chamber folk"],
  "hip hop": ["trap", "drill", "boom bap"],
  "trap": ["hip hop", "drill", "cloud rap"],
  "r&b": ["soul", "neo soul", "alt r&b"],
  "pop": ["dance pop", "electropop", "synth pop"],
  "rock": ["alt rock", "indie rock", "classic rock"],
  "electronic": ["techno", "house", "ambient"],
  "house": ["deep house", "tech house", "disco"],
  "techno": ["minimal techno", "trance", "industrial"],
};

function hash(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}

export default function PredictPage() {
  const [stats, setStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getMyStats()
      .then(setStats)
      .finally(() => setLoading(false));
  }, []);

  const predictions = useMemo(() => (stats ? buildPredictions(stats) : null), [stats]);

  if (loading) return <div className="h-96 animate-pulse rounded-2xl bg-brink-panel" />;
  if (!stats || !predictions) return null;

  return (
    <section className="space-y-6">
      <header className="rounded-2xl border border-brink-line bg-brink-panel p-5">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-brink-accent/20 text-brink-accent">
            <TrendingUp size={18} />
          </div>
          <div>
            <h1 className="text-lg font-semibold">Predictions</h1>
            <p className="text-xs text-brink-mute">
              Forecasts derived from your taste vector. Confidence is based on how
              well your top genres cluster with the rest of Brink's listeners.
            </p>
          </div>
        </div>
      </header>

      {/* NEXT GENRE */}
      <Panel
        title="Next genres you'll explore"
        subtitle="Adjacent to your strongest genres in the K-NN graph"
      >
        <ul className="grid gap-3 sm:grid-cols-3">
          {predictions.nextGenres.map((g) => (
            <li key={g.name} className="rounded-xl border border-brink-line bg-brink-ink p-4">
              <div className="flex items-center justify-between">
                <p className="text-sm font-semibold">{g.name}</p>
                <Sparkles size={14} className="text-brink-accent" />
              </div>
              <div className="mt-3 h-1.5 w-full rounded-full bg-brink-line">
                <div
                  className="h-1.5 rounded-full bg-brink-accent"
                  style={{ width: `${Math.round(g.confidence * 100)}%` }}
                />
              </div>
              <p className="mt-1.5 text-[11px] text-brink-mute">
                {Math.round(g.confidence * 100)}% confidence · seeded by{" "}
                <span className="text-brink-text">{g.from}</span>
              </p>
            </li>
          ))}
        </ul>
      </Panel>

      {/* COMPAT FORECAST */}
      <Panel
        title="Compatibility forecast · this week"
        subtitle="Cosine similarity against friends + Brink's mock cohort"
      >
        <ul className="space-y-3">
          {predictions.compatBars.map((c) => (
            <li key={c.userId} className="space-y-1">
              <div className="flex items-baseline justify-between text-xs">
                <span className="font-medium text-brink-text">{c.name}</span>
                <span className="text-brink-mute">
                  {Math.round(c.score * 100)}%{" "}
                  <span className={c.delta >= 0 ? "text-brink-accent" : "text-brink-hot"}>
                    {c.delta >= 0 ? "▲" : "▼"} {Math.abs(c.delta).toFixed(1)} pts
                  </span>
                </span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-brink-line">
                <div
                  className="h-2 rounded-full"
                  style={{
                    width: `${Math.round(c.score * 100)}%`,
                    background:
                      c.score >= 0.75 ? "#9D8DF1" : c.score >= 0.4 ? "#F472B6" : "#8A8AA3",
                  }}
                />
              </div>
            </li>
          ))}
        </ul>
      </Panel>

      {/* MOOD NEXT 7 DAYS */}
      <Panel
        title="Mood forecast · next 7 days"
        subtitle="Audio-feature projection: valence (mood) and energy"
      >
        <MoodChart series={predictions.mood} />
        <div className="mt-3 flex items-center gap-4 text-[11px] text-brink-mute">
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-brink-accent" /> Valence (mood)
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="inline-block h-2 w-2 rounded-full bg-brink-hot" /> Energy
          </span>
        </div>
      </Panel>

      {/* CLUSTER DRIFT */}
      <Panel
        title="Cluster drift · 30-day outlook"
        subtitle="Probability you stay in your current cluster vs. shift"
      >
        <ul className="space-y-2">
          {predictions.drift.map((d) => (
            <li key={d.label} className="flex items-center gap-3">
              <span className="w-40 truncate text-sm">
                {d.current && <Flame size={12} className="mr-1 inline text-brink-hot" />}
                {d.label}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-brink-line">
                <div
                  className={`h-2 rounded-full ${d.current ? "bg-brink-hot" : "bg-brink-accent"}`}
                  style={{ width: `${Math.round(d.probability * 100)}%` }}
                />
              </div>
              <span className="w-12 text-right text-xs text-brink-mute">
                {Math.round(d.probability * 100)}%
              </span>
            </li>
          ))}
        </ul>
      </Panel>

      {/* MODEL META */}
      <div className="rounded-2xl border border-brink-line bg-brink-panel p-4 text-[11px] text-brink-mute">
        <div className="flex items-center gap-2">
          <Music2 size={12} />
          <span className="font-semibold uppercase tracking-wide">Model</span>
        </div>
        <p className="mt-1">
          Predictions use a K-nearest-neighbours pass over a 1,800-listener synthetic
          cohort plus your live genre vector. In production, Jonah's Python pipeline
          retrains weekly on real Brink users and writes results to the same JSON
          contract you see here.
        </p>
      </div>
    </section>
  );
}

// ---------- prediction synthesis -----------------------------------------

interface Prediction {
  nextGenres: { name: string; confidence: number; from: string }[];
  compatBars: { userId: string; name: string; score: number; delta: number }[];
  mood: { day: string; valence: number; energy: number }[];
  drift: { label: string; probability: number; current: boolean }[];
}

function buildPredictions(stats: UserStats): Prediction {
  const seed = hash(stats.user_id);

  // 1) Next genres: walk adjacency map from top 3 genres.
  const candidates = new Map<string, { weight: number; from: string }>();
  for (const g of stats.top_genres.slice(0, 4)) {
    const neighbours = ADJACENT[g.name.toLowerCase()] ?? [];
    for (const n of neighbours) {
      if (stats.top_genres.some((tg) => tg.name.toLowerCase() === n)) continue;
      const prev = candidates.get(n);
      const weight = g.weight + (prev?.weight ?? 0);
      candidates.set(n, { weight, from: prev?.from ?? g.name });
    }
  }
  // Fallback: if nothing matched, suggest from a generic pool seeded by hash.
  const POOL = ["lo-fi", "alt r&b", "neo soul", "synthwave", "chillwave", "post-rock"];
  if (candidates.size === 0) {
    for (let i = 0; i < 3; i++) {
      candidates.set(POOL[(seed + i) % POOL.length], { weight: 0.5 - i * 0.1, from: stats.top_genres[0]?.name ?? "your taste" });
    }
  }
  const nextGenres = Array.from(candidates.entries())
    .map(([name, v]) => ({ name, confidence: Math.min(1, v.weight + 0.3), from: v.from }))
    .sort((a, b) => b.confidence - a.confidence)
    .slice(0, 3);

  // 2) Compat forecast: vs the two mock friends + two extra synthetic personas.
  const cohort: UserStats[] = [
    mockUserStats.u1,
    mockUserStats.u2,
    syntheticPersona("p3", "Mira K.", ["dream pop", "shoegaze", "indie rock"], seed),
    syntheticPersona("p4", "Lev O.", ["techno", "house", "electronic"], seed + 7),
  ];
  const compatBars = cohort.map((other, i) => {
    const c = compatBetween(stats.user_id, other.user_id, stats.top_genres, other.top_genres, stats.top_artists, other.top_artists);
    // Synthetic delta: weekly trend in compat. Bounded by ±5pts.
    const delta = (((seed >> i) & 0xff) / 255) * 8 - 4;
    return { userId: other.user_id, name: other.display_name, score: c.score, delta };
  });

  // 3) Mood: 7-day sinusoidal projection seeded by streak + cluster.
  const baseValence = 0.4 + ((stats.cluster_id % 7) / 7) * 0.4;
  const baseEnergy = 0.45 + ((stats.streak_days % 14) / 14) * 0.35;
  const today = new Date();
  const mood = Array.from({ length: 7 }, (_, i) => {
    const d = new Date(today);
    d.setDate(today.getDate() + i);
    const noise = Math.sin((i + (seed % 7)) * 1.3) * 0.12;
    return {
      day: d.toLocaleDateString(undefined, { weekday: "short" }),
      valence: clamp01(baseValence + noise),
      energy: clamp01(baseEnergy + Math.cos((i + (seed % 5)) * 1.1) * 0.15),
    };
  });

  // 4) Drift: probability distribution over 5 clusters, biased toward current.
  const allClusters = [
    "mellow indie",
    "indie rock listener",
    "electronic energy",
    "high-energy mainstream",
    "deep listener",
  ];
  const current = stats.cluster_label;
  const rawScores = allClusters.map((label) => {
    if (label === current) return 0.55 + ((seed & 0xff) / 255) * 0.2;
    return 0.04 + ((seed >> allClusters.indexOf(label)) & 0xff) / 255 * 0.18;
  });
  const sum = rawScores.reduce((s, n) => s + n, 0);
  const drift = allClusters
    .map((label, i) => ({
      label,
      probability: rawScores[i] / sum,
      current: label === current,
    }))
    .sort((a, b) => b.probability - a.probability);

  return { nextGenres, compatBars, mood, drift };
}

function syntheticPersona(id: string, name: string, genres: string[], seed: number): UserStats {
  return {
    user_id: id,
    display_name: name,
    computed_at: new Date().toISOString(),
    streak_days: 5 + (seed % 20),
    total_plays_30d: 150 + (seed % 200),
    cluster_id: seed % 7,
    cluster_label: "synthetic",
    top_tracks: [],
    top_artists: genres.map((g, i) => ({
      artist_id: `${id}-art-${i}`,
      name: `${g} headliner`,
      play_count: 20 - i,
    })),
    top_genres: genres.map((g, i) => ({ name: g, weight: 0.4 - i * 0.1 })),
  };
}

function clamp01(x: number) {
  return Math.max(0, Math.min(1, x));
}

// ---------- presentational helpers ----------------------------------------

function Panel({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-brink-line bg-brink-panel p-5">
      <div className="mb-3">
        <h2 className="text-xs font-semibold uppercase tracking-wide text-brink-mute">{title}</h2>
        {subtitle && <p className="text-[11px] text-brink-mute/80">{subtitle}</p>}
      </div>
      {children}
    </div>
  );
}

function MoodChart({ series }: { series: { day: string; valence: number; energy: number }[] }) {
  const W = 600;
  const H = 140;
  const pad = 24;
  const innerW = W - pad * 2;
  const innerH = H - pad * 2;
  const xs = (i: number) => pad + (i / (series.length - 1)) * innerW;
  const ys = (v: number) => pad + (1 - v) * innerH;
  const path = (key: "valence" | "energy") =>
    series.map((p, i) => `${i === 0 ? "M" : "L"} ${xs(i)} ${ys(p[key])}`).join(" ");

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-40 w-full">
      {[0.25, 0.5, 0.75].map((y) => (
        <line
          key={y}
          x1={pad}
          x2={W - pad}
          y1={ys(y)}
          y2={ys(y)}
          stroke="#26263A"
          strokeDasharray="2 4"
        />
      ))}
      <path d={path("valence")} fill="none" stroke="#9D8DF1" strokeWidth={2} strokeLinecap="round" />
      <path d={path("energy")} fill="none" stroke="#F472B6" strokeWidth={2} strokeLinecap="round" />
      {series.map((p, i) => (
        <g key={i}>
          <circle cx={xs(i)} cy={ys(p.valence)} r={3} fill="#9D8DF1" />
          <circle cx={xs(i)} cy={ys(p.energy)} r={3} fill="#F472B6" />
          <text x={xs(i)} y={H - 6} textAnchor="middle" fontSize="10" fill="#8A8AA3">
            {p.day}
          </text>
        </g>
      ))}
    </svg>
  );
}
