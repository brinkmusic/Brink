import { randomBytes } from "crypto";
import { encrypt, decrypt } from "../_lib/crypto";

beforeAll(() => {
  process.env.TOKEN_ENC_KEY = randomBytes(32).toString("base64");
});

describe("token encryption (AES-256-GCM)", () => {
  it("round-trips a secret and never exposes it in the ciphertext", () => {
    const secret = "AQB-spotify-refresh-token-xyz";
    const enc = encrypt(secret);
    expect(enc).not.toContain(secret);
    expect(decrypt(enc)).toBe(secret);
  });

  it("produces a different ciphertext each time (random IV)", () => {
    expect(encrypt("same")).not.toBe(encrypt("same"));
  });

  it("rejects tampered ciphertext", () => {
    const parts = encrypt("hello").split(".");
    parts[2] = Buffer.from("tampered").toString("base64");
    expect(() => decrypt(parts.join("."))).toThrow();
  });
});
