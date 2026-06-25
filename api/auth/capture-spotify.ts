import type { VercelRequest, VercelResponse } from "@vercel/node";
import { prisma } from "../_lib/prisma";
import { requireUser, AuthError } from "../_lib/auth";
import { encrypt } from "../_lib/crypto";
import { ok, fail } from "../_lib/respond";

// POST /api/auth/capture-spotify
// Called by the browser right after a Supabase Spotify login, passing the
// provider tokens (Supabase exposes them once, in the post-OAuth session).
// Body: { refresh_token, access_token, scopes? }
// Stores them encrypted so the server-side snapshot job can pull plays later.
export default async function handler(req: VercelRequest, res: VercelResponse) {
  if (req.method !== "POST") return fail(res, "method not allowed", 405);
  try {
    const user = await requireUser(req);
    const body = typeof req.body === "string" ? JSON.parse(req.body) : req.body || {};
    const { refresh_token, access_token, scopes } = body;
    if (!refresh_token || !access_token) return fail(res, "missing spotify tokens", 400);

    const expiresAt = new Date(Date.now() + 3600 * 1000); // Spotify access tokens last ~1h
    const fields = {
      accessToken: encrypt(access_token),
      refreshToken: encrypt(refresh_token),
      expiresAt,
      scopes: scopes || "",
    };
    await prisma.spotifyToken.upsert({
      where: { userId: user.id },
      create: { userId: user.id, ...fields },
      update: fields,
    });
    return ok(res, { captured: true });
  } catch (e) {
    if (e instanceof AuthError) return fail(res, e.message, e.status);
    return fail(res, (e as Error).message, 500);
  }
}
