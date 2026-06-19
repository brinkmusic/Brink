import { useEffect, useState } from "react";
import { Heart, MessageCircle, Flame, Sparkles } from "lucide-react";
import { Link } from "react-router-dom";
import { getBackendState, reactToPost, type ReactionCounts } from "../lib/backend";

export interface Post {
  id: string;
  user: { id: string; name: string; avatarUrl?: string; clusterLabel?: string };
  track: { id: string; title: string; artist: string; albumArt?: string; genres?: string[] };
  playedAt: string; // ISO
  reactions: { heart: number; fire: number; sparkle: number };
  commentCount: number;
}

type Kind = keyof ReactionCounts;

const VOTED_KEY = (postId: string, kind: Kind) => `brink.reacted.${postId}.${kind}`;

function hasVoted(postId: string, kind: Kind): boolean {
  try {
    return localStorage.getItem(VOTED_KEY(postId, kind)) === "1";
  } catch {
    return false;
  }
}

function setVoted(postId: string, kind: Kind, voted: boolean) {
  try {
    if (voted) localStorage.setItem(VOTED_KEY(postId, kind), "1");
    else localStorage.removeItem(VOTED_KEY(postId, kind));
  } catch {
    /* storage disabled — fine */
  }
}

export default function PostCard({ post }: { post: Post }) {
  const when = relativeTime(post.playedAt);
  const [counts, setCounts] = useState<ReactionCounts>(post.reactions);
  const [voted, setVotedState] = useState<Record<Kind, boolean>>({
    heart: hasVoted(post.id, "heart"),
    fire: hasVoted(post.id, "fire"),
    sparkle: hasVoted(post.id, "sparkle"),
  });
  const [busy, setBusy] = useState<Kind | null>(null);

  // Merge shared backend counts on mount so refreshes pick up other users' clicks.
  useEffect(() => {
    let cancelled = false;
    getBackendState().then((state) => {
      if (cancelled) return;
      const shared = state.reactions[post.id];
      if (shared) {
        setCounts((c) => ({
          heart: Math.max(c.heart, shared.heart),
          fire: Math.max(c.fire, shared.fire),
          sparkle: Math.max(c.sparkle, shared.sparkle),
        }));
      }
    });
    return () => {
      cancelled = true;
    };
  }, [post.id]);

  async function onReact(kind: Kind) {
    if (busy) return;
    const wasVoted = voted[kind];
    const delta: 1 | -1 = wasVoted ? -1 : 1;
    setCounts((c) => ({ ...c, [kind]: Math.max(0, c[kind] + delta) }));
    setVotedState((v) => ({ ...v, [kind]: !wasVoted }));
    setVoted(post.id, kind, !wasVoted);
    setBusy(kind);
    try {
      const next = await reactToPost(post.id, kind, delta);
      setCounts((c) => ({ ...c, [kind]: next[kind] }));
    } finally {
      setBusy(null);
    }
  }

  return (
    <article className="flex gap-3 rounded-2xl border border-brink-line bg-brink-panel p-4">
      <Link
        to={`/profile/${post.user.id}`}
        className="h-12 w-12 shrink-0 overflow-hidden rounded-full bg-gradient-to-br from-brink-accent to-brink-hot"
        aria-label={`${post.user.name}'s profile`}
      >
        {post.user.avatarUrl && (
          <img src={post.user.avatarUrl} alt="" className="h-full w-full object-cover" />
        )}
      </Link>
      <div className="min-w-0 flex-1">
        <header className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
          <Link
            to={`/profile/${post.user.id}`}
            className="truncate text-sm font-semibold hover:underline"
          >
            {post.user.name}
          </Link>
          {post.user.clusterLabel && (
            <span className="shrink-0 rounded-full bg-brink-accent/15 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-brink-accent">
              {post.user.clusterLabel}
            </span>
          )}
          <span className="ml-auto shrink-0 text-xs text-brink-mute">played · {when}</span>
        </header>

        <div className="mt-2 flex gap-3 rounded-xl border border-brink-line bg-brink-ink p-3">
          <div className="h-14 w-14 shrink-0 overflow-hidden rounded-md bg-brink-line">
            {post.track.albumArt && (
              <img src={post.track.albumArt} alt="" className="h-full w-full object-cover" />
            )}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{post.track.title}</p>
            <p className="truncate text-xs text-brink-mute">{post.track.artist}</p>
            {post.track.genres && post.track.genres.length > 0 && (
              <div className="mt-1.5 flex flex-wrap gap-1">
                {post.track.genres.slice(0, 3).map((g) => (
                  <span
                    key={g}
                    className="rounded-full border border-brink-line px-1.5 py-0.5 text-[10px] text-brink-mute"
                  >
                    {g}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>

        <footer className="mt-3 flex items-center gap-4 text-xs text-brink-mute">
          <ReactionBtn
            kind="heart"
            count={counts.heart}
            voted={voted.heart}
            busy={busy === "heart"}
            onClick={() => onReact("heart")}
            activeClass="text-brink-hot"
            hoverClass="hover:text-brink-hot"
            icon={<Heart size={14} fill={voted.heart ? "currentColor" : "none"} />}
          />
          <ReactionBtn
            kind="fire"
            count={counts.fire}
            voted={voted.fire}
            busy={busy === "fire"}
            onClick={() => onReact("fire")}
            activeClass="text-brink-hot"
            hoverClass="hover:text-brink-hot"
            icon={<Flame size={14} fill={voted.fire ? "currentColor" : "none"} />}
          />
          <ReactionBtn
            kind="sparkle"
            count={counts.sparkle}
            voted={voted.sparkle}
            busy={busy === "sparkle"}
            onClick={() => onReact("sparkle")}
            activeClass="text-brink-accent"
            hoverClass="hover:text-brink-accent"
            icon={<Sparkles size={14} fill={voted.sparkle ? "currentColor" : "none"} />}
          />
          <button
            type="button"
            className="ml-auto flex items-center gap-1 hover:text-brink-text"
            aria-label="comments"
          >
            <MessageCircle size={14} /> {post.commentCount}
          </button>
        </footer>
      </div>
    </article>
  );
}

function ReactionBtn({
  kind,
  count,
  voted,
  busy,
  onClick,
  activeClass,
  hoverClass,
  icon,
}: {
  kind: Kind;
  count: number;
  voted: boolean;
  busy: boolean;
  onClick: () => void;
  activeClass: string;
  hoverClass: string;
  icon: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={busy}
      aria-pressed={voted}
      aria-label={`${voted ? "un-react" : "react"} ${kind}`}
      className={`flex items-center gap-1 transition disabled:opacity-50 ${voted ? activeClass : hoverClass}`}
    >
      {icon} {count}
    </button>
  );
}

function relativeTime(iso: string) {
  const ms = Date.now() - new Date(iso).getTime();
  const m = Math.round(ms / 60000);
  if (m < 1) return "just now";
  if (m < 60) return `${m}m ago`;
  const h = Math.round(m / 60);
  if (h < 24) return `${h}h ago`;
  return `${Math.round(h / 24)}d ago`;
}
