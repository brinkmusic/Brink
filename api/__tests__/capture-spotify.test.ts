import type { VercelRequest, VercelResponse } from "@vercel/node";
import handler from "../auth/capture-spotify";
import { prisma } from "../_lib/prisma";
import { requireUser } from "../_lib/auth";

jest.mock("../_lib/prisma", () => ({ prisma: { spotifyToken: { upsert: jest.fn() } } }));
jest.mock("../_lib/auth", () => ({
  requireUser: jest.fn(),
  AuthError: class AuthError extends Error {
    status = 401;
  },
}));
jest.mock("../_lib/crypto", () => ({ encrypt: (s: string) => `enc(${s})` }));

function mockRes() {
  const res = {} as Record<string, jest.Mock>;
  res.status = jest.fn().mockReturnValue(res);
  res.json = jest.fn().mockReturnValue(res);
  return res as unknown as VercelResponse;
}
function req(method: string, body?: unknown): VercelRequest {
  return { method, body } as unknown as VercelRequest;
}

beforeEach(() => jest.clearAllMocks());

describe("POST /api/auth/capture-spotify", () => {
  it("rejects non-POST", async () => {
    const res = mockRes();
    await handler(req("GET"), res);
    expect((res.status as jest.Mock)).toHaveBeenCalledWith(405);
  });

  it("400s when tokens are missing", async () => {
    (requireUser as jest.Mock).mockResolvedValue({ id: "u1" });
    const res = mockRes();
    await handler(req("POST", { access_token: "a" }), res);
    expect((res.status as jest.Mock)).toHaveBeenCalledWith(400);
  });

  it("encrypts + upserts the tokens for the signed-in user", async () => {
    (requireUser as jest.Mock).mockResolvedValue({ id: "u1" });
    const res = mockRes();
    await handler(req("POST", { access_token: "AT", refresh_token: "RT", scopes: "x" }), res);
    expect((prisma.spotifyToken.upsert as jest.Mock)).toHaveBeenCalledWith(
      expect.objectContaining({
        where: { userId: "u1" },
        create: expect.objectContaining({ userId: "u1", accessToken: "enc(AT)", refreshToken: "enc(RT)" }),
      }),
    );
    expect((res.status as jest.Mock)).toHaveBeenCalledWith(200);
  });
});
