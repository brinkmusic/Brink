import { useEffect, useState } from "react";
import PostCard, { type Post } from "../components/PostCard";
import { getFeed } from "../lib/data";

export default function FeedPage() {
  const [posts, setPosts] = useState<Post[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getFeed()
      .then(setPosts)
      .catch((e) => setError(e instanceof Error ? e.message : String(e)));
  }, []);

  if (error) {
    return <p className="text-sm text-red-400">Couldn't load feed: {error}</p>;
  }
  if (!posts) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div
            key={i}
            className="h-28 animate-pulse rounded-2xl border border-brink-line bg-brink-panel"
          />
        ))}
      </div>
    );
  }
  if (posts.length === 0) {
    return (
      <p className="text-sm text-brink-mute">
        Nothing in your feed yet. Follow some friends to see what they're playing.
      </p>
    );
  }

  return (
    <section className="space-y-3">
      <div className="flex items-baseline justify-between">
        <h1 className="text-lg font-semibold">Feed</h1>
        <p className="text-xs text-brink-mute">
          Your recent plays mixed with friends · genre + cluster from analytics
        </p>
      </div>
      {posts.map((p) => (
        <PostCard key={p.id} post={p} />
      ))}
    </section>
  );
}
