// 4-week heatmap that visualizes a listening streak.
// In production Jonah's pipeline would emit per-day play counts; for now we
// derive a plausible pattern from streak_days so the visual feels real.

export default function StreakHeatmap({ streakDays }: { streakDays: number }) {
  const days = 28;
  const cells: number[] = Array.from({ length: days }, (_, i) => {
    const fromEnd = days - 1 - i;
    if (fromEnd < streakDays) return 2 + ((fromEnd * 7) % 3); // 2–4 plays
    return Math.random() < 0.35 ? Math.floor(Math.random() * 3) : 0;
  });

  const shade = (n: number) => {
    if (n === 0) return "bg-brink-line/40";
    if (n === 1) return "bg-brink-accent/30";
    if (n === 2) return "bg-brink-accent/55";
    if (n === 3) return "bg-brink-accent/75";
    return "bg-brink-accent";
  };

  return (
    <div>
      <div className="grid grid-cols-7 gap-1">
        {cells.map((n, i) => (
          <div
            key={i}
            className={`h-4 rounded-sm ${shade(n)}`}
            title={`${n} plays`}
          />
        ))}
      </div>
      <p className="mt-2 text-[11px] text-brink-mute">
        Last 28 days · darker = more plays
      </p>
    </div>
  );
}
