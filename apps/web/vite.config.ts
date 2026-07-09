import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  // Spotify rejects http://localhost as a redirect URI; loopback must be 127.0.0.1.
  // /api/* is proxied to the local FastAPI backend (uvicorn on :3001).
  server: {
    host: "127.0.0.1",
    port: 5173,
    proxy: { "/api": "http://127.0.0.1:3001" },
  },
});
