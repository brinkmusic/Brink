import type { VercelRequest } from "@vercel/node";
import type { User } from "@prisma/client";
import { prisma } from "./prisma";
import { supabaseAdmin } from "./supabase";

export class AuthError extends Error {
  status: number;
  constructor(message: string, status = 401) {
    super(message);
    this.status = status;
  }
}

function bearerToken(req: VercelRequest): string {
  const header = req.headers.authorization || "";
  const match = header.match(/^Bearer (.+)$/i);
  if (!match) throw new AuthError("missing bearer token");
  return match[1];
}

function slugify(s: string): string {
  return s
    .toLowerCase()
    .normalize("NFKD")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 20);
}

// Validates the Supabase access token (revalidated against the Auth server) and
// returns the matching public.User, creating it on first sign-in.
//
// Handle policy: derive a readable slug from the display name/email, then append
// 6 chars of the (unique) Supabase user id. This guarantees uniqueness with no
// DB retry loop; users can rename their handle later (out of scope here).
export async function requireUser(req: VercelRequest): Promise<User> {
  const token = bearerToken(req);
  const { data, error } = await supabaseAdmin().auth.getUser(token);
  if (error || !data.user) throw new AuthError("invalid session");
  const su = data.user;

  const existing = await prisma.user.findUnique({ where: { supabaseUserId: su.id } });
  if (existing) return existing;

  const meta = (su.user_metadata ?? {}) as Record<string, string>;
  const isSpotify = (su.app_metadata?.provider ?? "") === "spotify";
  const displayName = meta.full_name || meta.name || (su.email ? su.email.split("@")[0] : "Listener");
  const base = slugify(displayName) || "user";
  const handle = `${base}-${su.id.replace(/-/g, "").slice(0, 6)}`;

  return prisma.user.create({
    data: {
      supabaseUserId: su.id,
      email: su.email ?? null,
      displayName,
      handle,
      avatarUrl: meta.avatar_url || meta.picture || null,
      spotifyId: isSpotify ? meta.provider_id || meta.sub || null : null,
    },
  });
}
