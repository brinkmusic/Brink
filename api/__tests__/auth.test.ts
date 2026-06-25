import type { VercelRequest } from "@vercel/node";
import { requireUser, AuthError } from "../_lib/auth";
import { prisma } from "../_lib/prisma";
import { supabaseAdmin } from "../_lib/supabase";

jest.mock("../_lib/prisma", () => ({
  prisma: { user: { findUnique: jest.fn(), create: jest.fn() } },
}));
jest.mock("../_lib/supabase", () => ({ supabaseAdmin: jest.fn() }));

const getUser = jest.fn();

function req(authorization?: string): VercelRequest {
  return { headers: authorization ? { authorization } : {} } as unknown as VercelRequest;
}

beforeEach(() => {
  jest.clearAllMocks();
  (supabaseAdmin as jest.Mock).mockReturnValue({ auth: { getUser } });
});

describe("requireUser", () => {
  it("rejects a request with no bearer token", async () => {
    await expect(requireUser(req())).rejects.toBeInstanceOf(AuthError);
  });

  it("rejects an invalid token", async () => {
    getUser.mockResolvedValue({ data: { user: null }, error: { message: "bad jwt" } });
    await expect(requireUser(req("Bearer x"))).rejects.toThrow("invalid session");
  });

  it("returns the existing user without creating", async () => {
    getUser.mockResolvedValue({ data: { user: { id: "sb-1" } }, error: null });
    (prisma.user.findUnique as jest.Mock).mockResolvedValue({ id: "u1", supabaseUserId: "sb-1" });
    const u = await requireUser(req("Bearer x"));
    expect(u.id).toBe("u1");
    expect(prisma.user.create).not.toHaveBeenCalled();
  });

  it("creates a new user with a derived, unique handle on first sign-in", async () => {
    getUser.mockResolvedValue({
      data: {
        user: {
          id: "abcdef12-3456-7890",
          email: "jo@example.com",
          user_metadata: { full_name: "Jo Doe", avatar_url: "http://img/a.png" },
          app_metadata: { provider: "spotify" },
        },
      },
      error: null,
    });
    (prisma.user.findUnique as jest.Mock).mockResolvedValue(null);
    (prisma.user.create as jest.Mock).mockImplementation(({ data }) => ({ id: "new", ...data }));

    const u = await requireUser(req("Bearer x"));
    expect(prisma.user.create).toHaveBeenCalledTimes(1);
    expect(u.supabaseUserId).toBe("abcdef12-3456-7890");
    expect(u.displayName).toBe("Jo Doe");
    expect(u.handle).toMatch(/^jo-doe-[a-z0-9]{6}$/);
    expect(u.avatarUrl).toBe("http://img/a.png");
  });
});
