# WHAT THIS FILE IS
# Checks the token encryption (app/security/crypto.py). The most important test proves
# our Python code can decrypt a value produced by the OLD TypeScript backend — that's
# what guarantees the tokens already stored in the live database still work after the
# migration.

import base64
from types import SimpleNamespace

import pytest
from cryptography.exceptions import InvalidTag

from app.security import crypto

# A second, unrelated 32-byte key (base64), built from fixed bytes so the test is
# repeatable. Used to prove that decrypting with the WRONG key fails loudly instead
# of silently returning garbage. gitleaks:allow — throwaway test material.
OTHER_KEY_B64 = base64.b64encode(b"\x11" * 32).decode()  # gitleaks:allow

# A real ciphertext produced by the legacy Node/TypeScript crypto.ts, captured once.
# Decrypting this with the matching key MUST return the original text.
# gitleaks:allow — this is a throwaway key generated just for this test vector, NOT a
# real secret and used nowhere else. The annotation tells the secret scanner to skip it.
TS_KEY_B64 = "DDgucS0Bj9D7jMYszgzIr5uymWddcZz0c4ZlEOHcuo8="  # gitleaks:allow
TS_PLAINTEXT = "AQCpt_test-spotify-refresh-token_9f3"
TS_BLOB = "xULODjNkeXqY48No.FaPjg5vyqQCZJaBzOzaIxw==.WNTphX/DrMZI4jJqJfO9cN5p2W3xL7B21RgEdz7xLG5nR2ZC"


def _use_key(monkeypatch, key_b64):
    # Point crypto at a known key without needing a real .env file.
    monkeypatch.setattr(crypto, "get_settings", lambda: SimpleNamespace(token_enc_key=key_b64))


# Format parity: decrypt something the old TypeScript code encrypted.
def test_decrypts_blob_from_typescript_crypto(monkeypatch):
    _use_key(monkeypatch, TS_KEY_B64)
    assert crypto.decrypt(TS_BLOB) == TS_PLAINTEXT


# Encrypt then decrypt returns the original (and looks like the 3-part format).
def test_round_trip(monkeypatch):
    _use_key(monkeypatch, TS_KEY_B64)
    blob = crypto.encrypt("hello-secret")
    assert blob.count(".") == 2  # iv . tag . ciphertext
    assert crypto.decrypt(blob) == "hello-secret"


# A value that isn't our 3-part format is rejected clearly.
def test_malformed_ciphertext_raises(monkeypatch):
    _use_key(monkeypatch, TS_KEY_B64)
    with pytest.raises(ValueError):
        crypto.decrypt("not-a-valid-blob")


# A key that doesn't decode to 32 bytes is rejected (prevents silent misconfiguration).
def test_wrong_key_length_raises(monkeypatch):
    _use_key(monkeypatch, base64.b64encode(b"too-short").decode())
    with pytest.raises(ValueError):
        crypto.encrypt("x")


def _tamper_part(blob, index):
    # Take a valid 3-part blob, flip one byte inside part `index` (0=iv, 1=tag,
    # 2=ciphertext), and re-encode. The result is still valid base64 — so it passes
    # the format check — but the contents are corrupted, which is what AES-GCM's
    # authentication tag is designed to catch.
    parts = blob.split(".")
    raw = bytearray(base64.b64decode(parts[index]))
    raw[0] ^= 0x01  # flip the lowest bit of the first byte
    parts[index] = base64.b64encode(bytes(raw)).decode("ascii")
    return ".".join(parts)


# Tampering with ANY part of a stored blob must be detected — GCM's whole point is
# integrity. A corrupted iv, tag, or ciphertext each raises InvalidTag, never a
# silently-wrong plaintext.
@pytest.mark.parametrize("index", [0, 1, 2])
def test_tampered_blob_raises_invalid_tag(monkeypatch, index):
    _use_key(monkeypatch, TS_KEY_B64)
    tampered = _tamper_part(TS_BLOB, index)
    with pytest.raises(InvalidTag):
        crypto.decrypt(tampered)


# Decrypting with a different (but valid-length) key must fail, not return garbage.
def test_wrong_key_raises_invalid_tag(monkeypatch):
    _use_key(monkeypatch, TS_KEY_B64)
    blob = crypto.encrypt("secret-value")
    _use_key(monkeypatch, OTHER_KEY_B64)
    with pytest.raises(InvalidTag):
        crypto.decrypt(blob)


# The iv must be fresh on every encryption. A fixed/reused nonce is the classic
# catastrophic GCM failure, so encrypting the same plaintext twice must produce
# different iv parts (and therefore different blobs).
def test_iv_is_unique_per_encryption(monkeypatch):
    _use_key(monkeypatch, TS_KEY_B64)
    a = crypto.encrypt("same-plaintext")
    b = crypto.encrypt("same-plaintext")
    assert a != b
    assert a.split(".")[0] != b.split(".")[0]  # iv parts differ


# Stray non-base64 characters in an otherwise 3-part blob are a malformed-format
# error (ValueError), NOT a tamper error — callers distinguish the two.
def test_non_base64_part_raises_value_error(monkeypatch):
    _use_key(monkeypatch, TS_KEY_B64)
    parts = TS_BLOB.split(".")
    parts[2] = "!!!" + parts[2]  # not valid base64
    with pytest.raises(ValueError):
        crypto.decrypt(".".join(parts))


# A blob with an empty part ("a..c") is malformed, rejected before any crypto runs.
def test_empty_part_raises_value_error(monkeypatch):
    _use_key(monkeypatch, TS_KEY_B64)
    with pytest.raises(ValueError):
        crypto.decrypt("a..c")


# Missing TOKEN_ENC_KEY surfaces as a clear ValueError, not a confusing crypto error.
def test_missing_key_raises_value_error(monkeypatch):
    _use_key(monkeypatch, "")
    with pytest.raises(ValueError, match="TOKEN_ENC_KEY not set"):
        crypto.encrypt("x")
