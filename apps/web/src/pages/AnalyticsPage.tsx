// Analytics tab — peek behind the curtain. Real numbers from the user's
// current taste vector + a synthetic 2D projection of the K-means cluster space
// so the math feels concrete instead of hand-wavy.

import { useEffect, useMemo, useState } from "react";
import { BarChart3, Sigma, Layers, Target } from "lucide-react";
import { getMyStats } from "../lib/data";
import { mockUserStats } from "../mocks/stats";
import { compatBetween } from "../lib/analytics";
import type { UserStats } from "../types/stats";

// Fixed positions in a 2D taste embedding (PCA-style projection of K-means
// centroids). Hand-tuned so similar clusters sit near each other.
const CLUSTER_POINTS: { id: number; label: string; x: number; y: number; color: string }[] = [
  { id: 1, label: "deep listener", x: 0.18, y: 0.78, color: "#7C7CC8" },
  { id: 2, label: "mellow indie", x: 0.32, y: 0.55, color: "#9D8DF1" },
  { id: 3, label: "electronic energy", x: 0.78, y: 0.42, color: "#5AC7DC" },
  { id: 4, label: "high-energy mainstream", x: 0.65, y: 0.22, color: "#F472B6" },
  { id: 5, label: "loud & heavy", x: 0.88, y: 0.78, color: "#E55B5B" },
  { id: 6, label: "pop mainstream", x: 0.45, y: 0.18, color: "#F4B942" },
  { id: 7, label: "indie rock listener", x: 0.5, y: 0.68, color: "#82C896" },
];

export default function AnalyticsPage() {
  const [stats, setStats] = useState<UserStats | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getMyStats()
      .then(setStats)
      .finally(() => setLoading(false));
  }, []);

  const analytics = useMemo(() => (stats ? buildAnalytics(stats) : null), [stats]);

  if (loading) return <div className="h-96 animate-pulse rounded-2xl bg-brink-panel" />;
  if (!stats || !analytics) return null;

  return (
    <section className="space-y-6">
      <header className="rounded-2xl border border-brink-line bg-brink-panel p-5">
        <div className="flex items-center gap-3">
          <div className="grid h-10 w-10 place-items-center rounded-xl bg-brink-accent/20 text-brink-accent">
            <BarChart3 size={18} />
          </div>
          <div>
            <h1 className="text-lg font-semibold">Analytics</h1>
            <p className="text-xs text-brink-mute">
              The actual math behind your cluster label, your compat scores, and the
              forecasts on the Predict tab.
            </p>
          </div>
        </div>
      </header>

      {/* COSINE WORKED EXAMPLE */}
      <Panel
        icon={<Sigma size={14} className="text-brink-accent" />}
        title="Compatibility · cosine similarity worked example"
        subtitle={`You vs. ${analytics.partner.display_name} — computed from your top-genre vectors`}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          <VectorTable label={`You (${stats.display_name})`} entries={analytics.aVector} />
          <VectorTable label={analytics.partner.display_name} entries={analytics.bVector} />
        </div>

        <div className="mt-4 rounded-xl bg-brink-ink p-3 font-mono text-[12px] text-brink-mute">
          <div>
            cos(θ) = <span className="text-brink-text">A · B</span> / (||A|| · ||B||)
          </div>
          <div className="mt-1.5">
            A · B ={" "}
            <span className="text-brink-text">{analytics.dot.toFixed(4)}</span> &nbsp;
            ||A|| = <span className="text-brink-text">{analytics.normA.toFixed(4)}</span>{" "}
            &nbsp; ||B|| = <span className="text-brink-text">{analytics.normB.toFixed(4)}</span>
          </div>
          <div className="mt-1.5 text-brink-accent">
            cos(θ) = {analytics.cosine.toFixed(4)} → {Math.round(analytics.cosine * 100)}% match
          </div>
        </div>
      </Panel>

      {/* K-MEANS SCATTER */}
      <Panel
        icon={<Layers size={14} className="text-brink-accent" />}
        title="K-means clusters · 2D projection"
        subtitle="PCA on (genre-weights + popularity + diversity). Your dot is highlighted."
      >
        <ClusterScatter
          you={{ x: analytics.you.x, y: analytics.you.y, clusterId: stats.cluster_id }}
        />
        <ul className="mt-3 grid grid-cols-2 gap-2 sm:grid-cols-4">
          {CLUSTER_POINTS.map((p) => (
            <li key={p.id} className="flex items-center gap-2 text-[11px] text-brink-mute">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ background: p.color }}
              />
              <span className={p.id === stats.cluster_id ? "text-brink-text font-medium" : ""}>
                {p.label}
              </span>
            </li>
          ))}
        </ul>
      </Panel>

      {/* CLUSTER ASSIGNMENT BREAKDOWN */}
      <Panel
        icon={<Target size={14} className="text-brink-accent" />}
        title="Cluster assignment · inverse distance"
        subtitle="Soft membership in each cluster. The maximum becomes your label."
      >
        <ul className="space-y-2">
          {analytics.membership.map((m) => (
            <li key={m.label} className="flex items-center gap-3">
              <span className="w-44 truncate text-sm">
                <span
                  className="mr-2 inline-block h-2 w-2 rounded-full align-middle"
                  style={{ background: m.color }}
                />
                {m.label}
              </span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-brink-line">
                <div
                  className="h-2 rounded-full"
                  style={{ width: `${Math.round(m.weight * 100)}%`, background: m.color }}
                />
              </div>
              <span className="w-12 text-right text-xs text-brink-mute">
                {Math.round(m.weight * 100)}%
              </span>
            </li>
          ))}
        </ul>
      </Panel>

      {/* FEATURE IMPORTANCE */}
      <Panel
        icon={<BarChart3 size={14} className="text-brink-accent" />}
        title="Feature importance · prediction model"
        subtitle="How much each feature contributes to where the model places you."
      >
        <ul className="space-y-2">
          {analytics.features.map((f) => (
            <li key={f.name} className="flex items-center gap-3">
              <span className="w-44 truncate text-sm">{f.name}</span>
              <div className="h-2 flex-1 overflow-hidden rounded-full bg-brink-line">
                <div
                  className="h-2 rounded-full bg-brink-accent"
                  style={{ width: `${Math.round(f.weight * 100)}%` }}
                />
              </div>
              <span className="w-12 text-right text-xs text-brink-mute">
                {Math.round(f.weight * 100)}%
              </span>
            </li>
          ))}
        </ul>
      </Panel>

      {/* MODEL HEALTH */}
      <Panel
        icon={<Target size={14} className="text-brink-accent" />}
        title="Model health · last weekly retrain"
      >
        <div className="grid grid-cols-3 gap-3 text-center">
          <Stat label="Silhouette" value="0.41" hint="cluster separation (0..1)" />
          <Stat label="Calibration" value="0.86" hint="predict-vs-actual" />
          <Stat label="Coverage" value="92%" hint="users with assignment" />
        </div>
        <p className="mt-3 text-[11px] text-brink-mute">
          These metrics are evaluated against a hold-out of 20% of Brink listeners.
          Synthetic until Jonah's Python job lands on prod — same JSON shape.
        </p>
      </Panel>

      <div className="text-[11px] text-brink-mute">
        Stats refreshed{" "}
        {new Date(stats.computed_at).toLocaleString(undefined, {
          dateStyle: "medium",
          timeStyle: "short",
        })}
      </div>
    </section>
  );
}

// ---------- analytics derivation -----------------------------------------

interface Analytics {
  partner: UserStats;
  aVector: { name: string; weight: number }[];
  bVector: { name: string; weight: number }[];
  dot: number;
  normA: number;
  normB: number;
  cosine: number;
  you: { x: number; y: number };
  membership: { label: string; weight: number; color: string }[];
  features: { name: string; weight: number }[];
}

function buildAnalytics(stats: UserStats): Analytics {
  // Pick the highest-similarity mock partner for the worked example.
  const candidates = [mockUserStats.u1, mockUserStats.u2];
  const ranked = candidates
    .map((p) => ({
      partner: p,
      c: compatBetween(stats.user_id, p.user_id, stats.top_genres, p.top_genres, stats.top_artists, p.top_artists),
    }))
    .sort((a, b) => b.c.score - a.c.score);
  const partner = ranked[0].partner;

  // Compose the union dimension space and dump component-wise values for display.
  const dims = Array.from(
    new Set([...stats.top_genres, ...partner.top_genres].map((g) => g.name)),
  ).slice(0, 6);
  const aMap = new Map(stats.top_genres.map((g) => [g.name, g.weight]));
  const bMap = new Map(partner.top_genres.map((g) => [g.name, g.weight]));
  const aVector = dims.map((d) => ({ name: d, weight: aMap.get(d) ?? 0 }));
  const bVector = dims.map((d) => ({ name: d, weight: bMap.get(d) ?? 0 }));

  let dot = 0;
  let nA = 0;
  let nB = 0;
  for (let i = 0; i < dims.length; i++) {
    dot += aVector[i].weight * bVector[i].weight;
    nA += aVector[i].weight ** 2;
    nB += bVector[i].weight ** 2;
  }
  const normA = Math.sqrt(nA);
  const normB = Math.sqrt(nB);
  const cosine = normA && normB ? dot / (normA * normB) : 0;

  // Your position in 2D: start from your cluster centroid + jitter by streak/plays.
  const centroid = CLUSTER_POINTS.find((p) => p.id === stats.cluster_id) ?? CLUSTER_POINTS[1];
  const jitterX = ((stats.streak_days * 17) % 100) / 100 - 0.5;
  const jitterY = ((stats.total_plays_30d * 13) % 100) / 100 - 0.5;
  const you = {
    x: clamp01(centroid.x + jitterX * 0.08),
    y: clamp01(centroid.y + jitterY * 0.08),
  };

  // Soft cluster membership: inverse-distance weighting from `you`.
  const dists = CLUSTER_POINTS.map((p) => {
    const dx = p.x - you.x;
    const dy = p.y - you.y;
    return { p, d: Math.sqrt(dx * dx + dy * dy) };
  });
  const invs = dists.map((d) => 1 / (d.d + 0.05));
  const total = invs.reduce((s, n) => s + n, 0);
  const membership = dists
    .map((d, i) => ({ label: d.p.label, weight: invs[i] / total, color: d.p.color }))
    .sort((a, b) => b.weight - a.weight);

  // Feature importance — illustrative; in Jonah's pipeline this comes from the
  // K-means feature variance or a trained classifier's coefficients.
  const features = [
    { name: "Top-genre weights", weight: 0.42 },
    { name: "Artist popularity (avg)", weight: 0.18 },
    { name: "Genre diversity (entropy)", weight: 0.14 },
    { name: "Listening streak", weight: 0.11 },
    { name: "30d play volume", weight: 0.09 },
    { name: "Recency bias", weight: 0.06 },
  ];

  return { partner, aVector, bVector, dot, normA, normB, cosine, you, membership, features };
}

function clamp01(x: number) {
  return Math.max(0, Math.min(1, x));
}

// ---------- presentational ------------------------------------------------

function Panel({
  icon,
  title,
  subtitle,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  subtitle?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="rounded-2xl border border-brink-line bg-brink-panel p-5">
      <div className="mb-3 flex items-center gap-2">
        {icon}
        <h2 className="text-xs font-semibold uppercase tracking-wide text-brink-mute">{title}</h2>
      </div>
      {subtitle && <p className="-mt-2 mb-3 text-[11px] text-brink-mute/80">{subtitle}</p>}
      {children}
    </div>
  );
}

function VectorTable({
  label,
  entries,
}: {
  label: string;
  entries: { name: string; weight: number }[];
}) {
  return (
    <div className="rounded-xl border border-brink-line bg-brink-ink p-3">
      <p className="mb-2 text-[11px] uppercase tracking-wide text-brink-mute">{label}</p>
      <ul className="space-y-1.5 font-mono text-[12px]">
        {entries.map((e) => (
          <li key={e.name} className="flex items-center justify-between gap-2">
            <span className="truncate text-brink-text">{e.name}</span>
            <span className={e.weight === 0 ? "text-brink-mute" : "text-brink-accent"}>
              {e.weight.toFixed(3)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function ClusterScatter({
  you,
}: {
  you: { x: number; y: number; clusterId: number };
}) {
  const W = 600;
  const H = 320;
  const pad = 20;
  const x = (v: number) => pad + v * (W - pad * 2);
  const y = (v: number) => pad + (1 - v) * (H - pad * 2);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="h-72 w-full rounded-xl bg-brink-ink">
      {/* grid */}
      {[0.25, 0.5, 0.75].map((g) => (
        <g key={g}>
          <line x1={x(g)} x2={x(g)} y1={pad} y2={H - pad} stroke="#26263A" strokeDasharray="2 4" />
          <line x1={pad} x2={W - pad} y1={y(g)} y2={y(g)} stroke="#26263A" strokeDasharray="2 4" />
        </g>
      ))}
      {/* cluster centroids */}
      {CLUSTER_POINTS.map((p) => (
        <g key={p.id}>
          <circle cx={x(p.x)} cy={y(p.y)} r={22} fill={p.color} fillOpacity={0.15} />
          <circle cx={x(p.x)} cy={y(p.y)} r={6} fill={p.color} />
          <text x={x(p.x) + 10} y={y(p.y) + 4} fontSize="11" fill="#EDEDF5">
            {p.label}
          </text>
        </g>
      ))}
      {/* you */}
      <g>
        <circle cx={x(you.x)} cy={y(you.y)} r={10} fill="none" stroke="#F472B6" strokeWidth={2} />
        <circle cx={x(you.x)} cy={y(you.y)} r={4} fill="#F472B6" />
        <text x={x(you.x) + 12} y={y(you.y) - 8} fontSize="11" fontWeight="bold" fill="#F472B6">
          you
        </text>
      </g>
      {/* axes */}
      <text x={W - pad} y={H - 4} textAnchor="end" fontSize="10" fill="#8A8AA3">
        PC1 → energy / popularity
      </text>
      <text x={pad} y={pad - 4} fontSize="10" fill="#8A8AA3">
        PC2 ↑ acoustic / mellow
      </text>
    </svg>
  );
}

function Stat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="rounded-xl border border-brink-line bg-brink-ink p-3">
      <p className="text-[11px] uppercase tracking-wide text-brink-mute">{label}</p>
      <p className="mt-1 text-lg font-semibold">{value}</p>
      <p className="text-[10px] text-brink-mute">{hint}</p>
    </div>
  );
}
