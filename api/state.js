// Brink shared-state backend.
// One Vercel serverless function that proxies a single JSON blob on jsonblob.com.
// Schema:
//   { users: { [user_id]: UserStats }, reactions: { [post_id]: {heart,fire,sparkle} } }

const BLOB_ID = process.env.JSONBLOB_ID;
const BLOB_URL = `https://jsonblob.com/api/jsonBlob/${BLOB_ID}`;
const HEADERS = { "Content-Type": "application/json", Accept: "application/json" };

async function getState() {
  if (!BLOB_ID) return { users: {}, reactions: {} };
  const res = await fetch(BLOB_URL, { headers: HEADERS });
  if (res.status === 404) return { users: {}, reactions: {} };
  if (!res.ok) throw new Error(`jsonblob GET ${res.status}: ${await res.text()}`);
  const text = await res.text();
  if (!text) return { users: {}, reactions: {} };
  try {
    const parsed = JSON.parse(text);
    return {
      users: parsed.users || {},
      reactions: parsed.reactions || {},
    };
  } catch {
    return { users: {}, reactions: {} };
  }
}

async function setState(state) {
  if (!BLOB_ID) throw new Error("JSONBLOB_ID not configured");
  const res = await fetch(BLOB_URL, {
    method: "PUT",
    headers: HEADERS,
    body: JSON.stringify(state),
  });
  if (!res.ok) throw new Error(`jsonblob PUT ${res.status}: ${await res.text()}`);
}

module.exports = async function handler(req, res) {
  res.setHeader("Access-Control-Allow-Origin", "*");
  res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  res.setHeader("Access-Control-Allow-Headers", "Content-Type");
  if (req.method === "OPTIONS") return res.status(204).end();

  try {
    if (req.method === "GET") {
      const state = await getState();
      return res.status(200).json(state);
    }
    if (req.method === "POST") {
      const body = typeof req.body === "string" ? JSON.parse(req.body) : req.body || {};
      const { action, payload } = body;
      const state = await getState();
      state.users = state.users || {};
      state.reactions = state.reactions || {};

      if (action === "upsertUser") {
        if (!payload || !payload.user_id) {
          return res.status(400).json({ error: "missing user_id" });
        }
        state.users[payload.user_id] = { ...payload, _updated_at: Date.now() };
      } else if (action === "react") {
        const { postId, kind, delta } = payload || {};
        if (!postId || !["heart", "fire", "sparkle"].includes(kind)) {
          return res.status(400).json({ error: "bad postId or kind" });
        }
        state.reactions[postId] = state.reactions[postId] || { heart: 0, fire: 0, sparkle: 0 };
        state.reactions[postId][kind] = Math.max(
          0,
          (state.reactions[postId][kind] || 0) + Number(delta || 0),
        );
      } else {
        return res.status(400).json({ error: "unknown action" });
      }

      await setState(state);
      return res.status(200).json(state);
    }
    return res.status(405).json({ error: "method not allowed" });
  } catch (e) {
    return res.status(500).json({ error: String((e && e.message) || e) });
  }
};
