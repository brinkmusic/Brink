// Donut chart for the taste-compatibility score.
// Pure SVG so we don't pull in a chart library for one number.

export default function CompatDonut({
  score, // 0–1
  size = 96,
  stroke = 10,
}: {
  score: number;
  size?: number;
  stroke?: number;
}) {
  const pct = Math.max(0, Math.min(1, score));
  const pct100 = Math.round(pct * 100);
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const dash = c * pct;
  const color =
    pct >= 0.75 ? "#9D8DF1" : pct >= 0.4 ? "#F472B6" : "#8A8AA3";

  return (
    <div className="relative inline-flex items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke="#26263A"
          strokeWidth={stroke}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={r}
          fill="none"
          stroke={color}
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${dash} ${c - dash}`}
        />
      </svg>
      <div className="absolute flex flex-col items-center">
        <span className="text-xl font-bold leading-none" style={{ color }}>
          {pct100}
        </span>
        <span className="text-[10px] uppercase tracking-wide text-brink-mute">match</span>
      </div>
    </div>
  );
}
