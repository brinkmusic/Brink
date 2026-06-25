import type { VercelResponse } from "@vercel/node";

// Consistent JSON envelope for all /api/* functions: { data } on success, { error } on failure.
export function ok<T>(res: VercelResponse, data: T, status = 200) {
  return res.status(status).json({ data });
}

export function fail(res: VercelResponse, message: string, status = 400) {
  return res.status(status).json({ error: message });
}
