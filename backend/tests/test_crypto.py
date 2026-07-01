# WHAT THIS FILE IS
# Checks the token encryption (app/security/crypto.py). The most important test proves
# our Python code can decrypt a value produced by the OLD TypeScript backend — that's
# what guarantees the tokens already stored in the live database still work after the
# migration.

import base64
from types import SimpleNamespace

import pytest

from app.security import crypto

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
