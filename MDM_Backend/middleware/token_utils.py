"""
MDM_Backend/signalmdm/middleware/token_utils.py
-------------------------------------
Cryptographic utilities for the security layer:

  1. AES-256-CBC  — encrypts / decrypts the JWT before it travels over the
                    wire.  Format: base64( IV[16] | CIPHERTEXT )
  2. Device fingerprint — SHA-256( deviceId | userAgent | userId )
  3. Token creation / revocation via Redis blacklist

AES key format
--------------
TOKEN_ENCRYPTION_KEY in .env must be exactly 64 hex characters (32 bytes).
Generate one with:
    python -c "import secrets; print(secrets.token_hex(32))"

TypeScript / CryptoJS compatibility
------------------------------------
Frontend encrypts the JWT like this (using crypto-js ≥ 4):

    import CryptoJS from 'crypto-js';

    function encryptToken(jwt: string, keyHex: string): string {
        const key = CryptoJS.enc.Hex.parse(keyHex);       // 32-byte key
        const iv  = CryptoJS.lib.WordArray.random(16);    // random IV
        const enc = CryptoJS.AES.encrypt(jwt, key, {
            iv,
            mode:    CryptoJS.mode.CBC,
            padding: CryptoJS.pad.Pkcs7,
        });
        // Combine IV + ciphertext bytes, then base64-encode
        const combined = iv.concat(enc.ciphertext);
        return CryptoJS.enc.Base64.stringify(combined);
    }

Device fingerprint (TypeScript)
---------------------------------
    function buildFingerprint(deviceId: string, userAgent: string, userId: string): string {
        return CryptoJS.SHA256(`${deviceId}|${userAgent}|${userId}`).toString();
    }
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from jose import jwt, JWTError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Read config once at import time
# ---------------------------------------------------------------------------
_JWT_SECRET: str = os.getenv("JWT_SECRET", "supersecretkey")
_JWT_ALGORITHM: str = os.getenv("JWT_ALGORITHM", "HS256")
_JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 h
_TOKEN_ENCRYPTION_KEY_HEX: str = os.getenv("TOKEN_ENCRYPTION_KEY", "")


def _get_aes_key() -> bytes:
    """Decode the 64-hex-char env var into 32 raw bytes."""
    if len(_TOKEN_ENCRYPTION_KEY_HEX) != 64:
        raise RuntimeError(
            "TOKEN_ENCRYPTION_KEY must be exactly 64 hex characters (32 bytes). "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return bytes.fromhex(_TOKEN_ENCRYPTION_KEY_HEX)


# ---------------------------------------------------------------------------
# AES-256-CBC  (matches CryptoJS.AES with WordArray key)
# ---------------------------------------------------------------------------

def aes_encrypt(plaintext: str) -> str:
    """
    Encrypt *plaintext* with AES-256-CBC.

    Returns base64-encoded string: base64( IV[16] + CIPHERTEXT ).
    """
    key = _get_aes_key()
    iv = os.urandom(16)

    # PKCS7 padding
    data = plaintext.encode("utf-8")
    pad_len = 16 - (len(data) % 16)
    data += bytes([pad_len] * pad_len)

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    ciphertext = cipher.encryptor().update(data) + cipher.encryptor().finalize()

    # Re-create to avoid using the same encryptor object twice
    encryptor = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend()).encryptor()
    ciphertext = encryptor.update(data) + encryptor.finalize()

    return base64.b64encode(iv + ciphertext).decode("utf-8")


def aes_decrypt(encrypted_b64: str) -> str:
    """
    Decrypt an AES-256-CBC ciphertext produced by *aes_encrypt* or the
    TypeScript counterpart.

    Raises ValueError on any decryption failure.
    """
    try:
        key = _get_aes_key()
        raw = base64.b64decode(encrypted_b64)
        if len(raw) < 32:
            raise ValueError("Ciphertext too short.")

        iv, ciphertext = raw[:16], raw[16:]
        decryptor = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend()).decryptor()
        padded = decryptor.update(ciphertext) + decryptor.finalize()

        # Remove PKCS7 padding
        pad_len = padded[-1]
        if pad_len < 1 or pad_len > 16:
            raise ValueError("Invalid padding.")
        return padded[:-pad_len].decode("utf-8")

    except Exception as exc:
        logger.warning("[token_utils] AES decrypt failed: %s", exc)
        raise ValueError("Token decryption failed.") from exc


# ---------------------------------------------------------------------------
# Device fingerprint
# ---------------------------------------------------------------------------

def compute_fingerprint(device_id: str, user_agent: str, user_id: str) -> str:
    """
    Return SHA-256( deviceId | userAgent | userId ) as a lowercase hex string.

    Must match the TypeScript implementation exactly:
        CryptoJS.SHA256(`${deviceId}|${userAgent}|${userId}`).toString()
    """
    raw = f"{device_id}|{user_agent}|{user_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# JWT creation (used by the login endpoint, not the middleware)
# ---------------------------------------------------------------------------

def create_access_token(
    *,
    user_id: str,
    tenant_id: str,
    role: str,
    device_id: str,
    user_agent: str,
    extra_claims: dict[str, Any] | None = None,
    expires_minutes: int | None = None,
) -> str:
    """
    Create a signed JWT.

    The `fpHash` claim binds the token to the specific device + browser that
    logged in. Any request from a different device fingerprint will be rejected
    by the auth middleware even if the token is otherwise valid.

    Returns the RAW (unencrypted) JWT string.
    Use `aes_encrypt(create_access_token(...))` to get the encrypted form.
    """
    exp_minutes = expires_minutes or _JWT_EXPIRE_MINUTES
    expire = datetime.now(timezone.utc) + timedelta(minutes=exp_minutes)

    fp_hash = compute_fingerprint(device_id, user_agent, user_id)

    payload: dict[str, Any] = {
        "sub":       user_id,
        "tenant_id": tenant_id,
        "role":      role,
        "fpHash":    fp_hash,
        "exp":       expire,
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(payload, _JWT_SECRET, algorithm=_JWT_ALGORITHM)


# ---------------------------------------------------------------------------
# JWT verification (used internally by auth middleware)
# ---------------------------------------------------------------------------

def decode_token(raw_jwt: str) -> dict[str, Any]:
    """
    Verify and decode a raw JWT.

    Raises jose.JWTError on failure (expired, invalid signature, etc.).
    """
    try:
        header = jwt.get_unverified_header(raw_jwt)
    except Exception as exc:
        raise JWTError("Invalid JWT header") from exc

    if header.get("alg") != _JWT_ALGORITHM:
        raise JWTError(f"Unsupported algorithm: {header.get('alg')}")

    return jwt.decode(raw_jwt, _JWT_SECRET, algorithms=[_JWT_ALGORITHM])


# ---------------------------------------------------------------------------
# Token blacklist (Redis-backed revocation)
# ---------------------------------------------------------------------------

def revoke_token(raw_jwt: str, ttl_seconds: int = 86400) -> None:
    """
    Add a token to the Redis revocation blacklist.

    The key expires automatically after *ttl_seconds* (default 24 h = same as
    the maximum token lifetime), so the blacklist stays small.
    """
    try:
        from core.redis_client import get_redis
        key = f"revoked:{raw_jwt}"
        get_redis().setex(key, ttl_seconds, "1")
    except Exception as exc:
        logger.error("[token_utils] Could not revoke token: %s", exc)


def is_token_revoked(raw_jwt: str) -> bool:
    """Return True if the token appears in the Redis blacklist."""
    try:
        from core.redis_client import get_redis
        return bool(get_redis().exists(f"revoked:{raw_jwt}"))
    except Exception:
        # Redis unavailable → do NOT block requests (fail open for revocation).
        # Log and continue; the JWT signature + expiry still protect the endpoint.
        logger.warning("[token_utils] Redis unavailable for revocation check — skipping.")
        return False
