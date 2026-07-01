import { PrismaClient } from "@prisma/client";

// Serverless-safe singleton: reuse one client across warm invocations to avoid
// exhausting Postgres connections. Supabase's transaction-mode pooler handles the rest.
const globalForPrisma = globalThis as unknown as { prisma?: PrismaClient };

export const prisma = globalForPrisma.prisma ?? new PrismaClient();

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma;
