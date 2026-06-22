import handler from "../health";
import { prisma } from "../_lib/prisma";

jest.mock("../_lib/prisma", () => ({
  prisma: { $queryRaw: jest.fn() },
}));

function mockRes() {
  const res = {} as Record<string, jest.Mock>;
  res.status = jest.fn().mockReturnValue(res);
  res.json = jest.fn().mockReturnValue(res);
  return res as never;
}

describe("GET /api/health", () => {
  it("returns 200 with db:true when the DB query succeeds", async () => {
    (prisma.$queryRaw as jest.Mock).mockResolvedValue([{ one: 1 }]);
    const res = mockRes();
    await handler({} as never, res);
    expect((res as never as { status: jest.Mock }).status).toHaveBeenCalledWith(200);
    expect((res as never as { json: jest.Mock }).json).toHaveBeenCalledWith({
      data: { ok: true, db: true },
    });
  });

  it("returns 500 when the DB is unreachable", async () => {
    (prisma.$queryRaw as jest.Mock).mockRejectedValue(new Error("boom"));
    const res = mockRes();
    await handler({} as never, res);
    expect((res as never as { status: jest.Mock }).status).toHaveBeenCalledWith(500);
  });
});
