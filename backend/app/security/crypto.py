# WHAT THIS FILE IS
# Encrypts and decrypts the secret Spotify tokens we have to store in the database.
# WHY: we must keep a user's Spotify refresh token so a background job can fetch
# their listening history later, but storing it in plain text would be a serious
# leak risk. So we scramble it with AES-256-GCM (a strong, standard cipher) and can
# only unscramble it with a secret key (TOKEN_ENC_KEY).
#
# IMPORTANT — format compatibility: the old TypeScript backend (api/_lib/crypto.ts)
# already encrypted tokens and saved them in the live database. This file MUST read
# and write the EXACT same format so those existing tokens still decrypt. The format
# is three base64 chunks joined by dots:  base64(iv).base64(tag).base64(ciphertext)
#   - iv  ("initialization vector"): 12 random bytes; makes each encryption unique.
#   - tag ("authentication tag"): 16 bytes; proves the data wasn't tampered with.
#   - ciphertext: the scrambled token itself.

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.config import get_settings


def _key() -> bytes:
    # The secret key, stored as base64 text in TOKEN_ENC_KEY. Decoded it must be
    # exactly 32 bytes (that's what "AES-256" means). We fail loudly otherwise so a
    # misconfigured key never silently produces unreadable data.
    raw = get_settings().token_enc_key
    if not raw:
        raise ValueError("TOKEN_ENC_KEY not set")
    buf = base64.b64decode(raw)
    if len(buf) != 32:
        raise ValueError("TOKEN_ENC_KEY must decode to 32 bytes")
    return buf


def encrypt(plaintext: str) -> str:
    iv = os.urandom(12)  # fresh random iv every time
    # AESGCM in Python returns ciphertext WITH the 16-byte tag stuck on the end.
    # Node keeps them separate, so we split the tag off to rebuild Node's exact
    # 3-part layout (iv . tag . ciphertext).
    ct_and_tag = AESGCM(_key()).encrypt(iv, plaintext.encode("utf-8"), None)
    ct, tag = ct_and_tag[:-16], ct_and_tag[-16:]
    return ".".join((_b64(iv), _b64(tag), _b64(ct)))


def decrypt(blob: str) -> str:
    # Split the stored value back into its three parts. If any part is missing, it
    # isn't a valid ciphertext we produced — reject it clearly.
    parts = blob.split(".")
    if len(parts) != 3 or not all(parts):
        raise ValueError("malformed ciphertext")
    # validate=True makes base64 decoding STRICT: stray non-base64 characters raise
    # binascii.Error (a subclass of ValueError) instead of being silently dropped.
    # This keeps the exception contract crisp for callers (T21 is the first real one):
    #   - ValueError  -> the blob's FORMAT is bad (wrong shape / not base64)
    #   - InvalidTag  -> the format is fine but the data was tampered with or the key
    #                    is wrong (raised by AESGCM.decrypt below)
    iv, tag, ct = (base64.b64decode(p, validate=True) for p in parts)
    plaintext = AESGCM(_key()).decrypt(iv, ct + tag, None)
    return plaintext.decode("utf-8")


def _b64(data: bytes) -> str:
    # Standard base64 with padding, matching Node's Buffer.toString("base64").
    return base64.b64encode(data).decode("ascii")
