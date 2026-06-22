import type { VercelRequest, VercelResponse } from "@vercel/node";
import { prisma } from "./_lib/prisma";
import { ok, fail } from "./_lib/respond";

// GET /api/health — liveness + DB reachability. Used to verify T01 foundation.
export default async function handler(_req: VercelRequest, res: VercelResponse) {
  try {
    const rows = await prisma.$queryRaw<{ one: number }[]>`SELECT 1 as one`;
    return ok(res, { ok: true, db: rows[0]?.one === 1 });
  } catch (e) {
    return fail(res, `db unreachable: ${(e as Error).message}`, 500);
  }
}
