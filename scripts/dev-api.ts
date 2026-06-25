// Local dev runner for the Vercel serverless functions in /api.
// Vite proxies /api/* here (see apps/web/vite.config.ts) so the same handlers
// that run on Vercel also run locally, reading secrets from the root .env.
// Run with:  npm run dev:api
import express from "express";
import path from "node:path";
import { existsSync } from "node:fs";
import { pathToFileURL } from "node:url";

const app = express();
app.use(express.json());

const apiDir = path.resolve(import.meta.dirname, "..", "api");

app.use("/api", async (req, res) => {
  const route = req.path.replace(/^\/+|\/+$/g, ""); // e.g. "auth/capture-spotify"
  const file = path.join(apiDir, `${route}.ts`);
  if (!existsSync(file)) {
    res.status(404).json({ error: `no handler: /api/${route}` });
    return;
  }
  try {
    const mod = await import(pathToFileURL(file).href);
    await mod.default(req, res);
  } catch (err) {
    res.status(500).json({ error: (err as Error).message });
  }
});

const PORT = 3001;
app.listen(PORT, () => console.log(`dev API -> http://127.0.0.1:${PORT} (proxied from Vite /api)`));
