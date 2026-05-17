"""
MDM_Backend/signalmdm/middleware/auth.py
------------------------------
FastAPI security dependency — mirrors the JS auth.js middleware exactly.

Flow (per request):
    1. Extract  Authorization: Bearer <AES-encrypted-JWT>
    2. AES-256-CBC decrypt  → raw JWT string
    3. Check Redis blacklist → 401 if revoked
    4. jose.jwt.decode       → 401 if expired / bad signature
    5. Recompute fingerprint SHA256(deviceId|userAgent|userId)
                             → 401 if mismatch
    6. Return TokenPayload   → available as Depends(require_auth)

Role guard:
    Use Depends(require_admin) to restrict an endpoint to role="admin".

Usage in a router:
    from signalmdm.middleware.auth import require_auth, require_admin, TokenPayload

    @router.get("/secure")
    def secure_endpoint(auth: TokenPayload = Depends(require_auth)):
        return {"tenant": auth.tenant_id}

    @router.delete("/admin-only")
    def admin_endpoint(auth: TokenPayload = Depends(require_admin)):
        ...
"""

from __future__ import annotations

import logging
import uuid
from typing import Optional

from fastapi import Depends, Header, HTTPException, Request, status
from jose import JWTError
from pydantic import BaseModel

from signalmdm.middleware.token_utils import (
    aes_decrypt,
    compute_fingerprint,
    decode_token,
    is_token_revoked,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Token payload model
# ---------------------------------------------------------------------------

class TokenPayload(BaseModel):
    """Decoded, validated JWT payload — injected via Depends(require_auth)."""

    user_id:   str
    email:     str
    username:  str
    tenant_id: str  # Can be UUID string or "platform"
    role:      str
    fp_hash:   str
    raw_jwt:   str   # kept for revocation (logout endpoint)

    model_config = {"arbitrary_types_allowed": True}


# ---------------------------------------------------------------------------
# Core auth dependency
# ---------------------------------------------------------------------------

async def require_auth(
    request: Request,
    authorization: Optional[str] = Header(None, alias="Authorization"),
    x_device_id: Optional[str]   = Header(None, alias="X-Device-ID"),
) -> TokenPayload:
    """
    Validate the encrypted JWT on every protected request.

    Token source priority:
        1. Authorization: Bearer <encrypted_jwt>  (explicit header)
        2. accessToken httpOnly cookie            (browser auth flow)

    Headers expected from the frontend:
        X-Device-ID:   <stable device fingerprint string>
        User-Agent:    <browser/app user-agent>   (standard header)

    Raises HTTP 401 for any security violation.
    """
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # --- 1. Extract encrypted token: header first, then cookie ---
    encrypted_token: Optional[str] = None

    if authorization and authorization.startswith("Bearer "):
        encrypted_token = authorization.split(" ", 1)[1].strip() or None

    if not encrypted_token:
        # Fall back to httpOnly cookie set by the auth endpoints
        cookie_token = request.cookies.get("accessToken")
        if cookie_token:
            encrypted_token = cookie_token

    if not encrypted_token:
        logger.warning("[auth] No token in Authorization header or accessToken cookie.")
        raise credentials_exc

    # --- 2. AES-256-CBC decrypt → raw JWT -----------------------------------
    try:
        raw_jwt = aes_decrypt(encrypted_token)
    except ValueError:
        logger.warning("[auth] Token decryption failed.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token encryption.",
        )

    # --- 3. Redis revocation check ------------------------------------------
    if is_token_revoked(raw_jwt):
        logger.warning("[auth] Revoked token presented.")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked.",
        )

    # --- 4. JWT signature + expiry verification -----------------------------
    try:
        payload = decode_token(raw_jwt)
    except JWTError as exc:
        logger.warning("[auth] JWT verification failed: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
        )

    user_id   = payload.get("sub")
    email     = payload.get("email", "")
    tenant_id = payload.get("tenant_id")
    role      = payload.get("role", "viewer")
    fp_hash   = payload.get("fpHash", "")

    if not user_id or not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed token payload.",
        )

    # --- 5. Device fingerprint validation -----------------------------------
    device_id  = x_device_id or request.headers.get("X-Device-ID") or "unknown"
    user_agent = request.headers.get("user-agent") or ""

    expected_fp = compute_fingerprint(device_id, user_agent, user_id)
    if expected_fp != fp_hash:
        logger.warning(
            "[auth] Fingerprint mismatch. user=%s device=%s", user_id, device_id
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid device fingerprint.",
        )

    # --- 6. Attach to request state + return --------------------------------
    raw_username = payload.get("username", "Unknown")
    email_str = payload.get("email", "")
    if raw_username == "Unknown" and email_str:
        raw_username = email_str.split("@")[0]

    token_payload = TokenPayload(
        user_id=user_id,
        email=email_str,
        username=raw_username,
        tenant_id=tenant_id,
        role=role,
        fp_hash=fp_hash,
        raw_jwt=raw_jwt,
    )
    request.state.user = token_payload
    return token_payload


# ---------------------------------------------------------------------------
# Role-based guards
# ---------------------------------------------------------------------------

def require_admin(auth: TokenPayload = Depends(require_auth)) -> TokenPayload:
    """
    Extends require_auth — additionally enforces role == "admin".

    Usage:
        @router.delete("/sources/{id}")
        def delete_source(auth: TokenPayload = Depends(require_admin)):
            ...
    """
    if auth.role != "admin":
        logger.warning("[auth] Admin access denied for user=%s role=%s", auth.user_id, auth.role)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required.",
        )
    return auth


# ---------------------------------------------------------------------------
# Platform Guards
# ---------------------------------------------------------------------------

def is_super_admin(auth: TokenPayload = Depends(require_auth)) -> TokenPayload:
    """
    Dependency that enforces tenant_id == "platform".
    Used for global configuration (Tenants, Platform Admins).
    """
    logger.info("[auth] Checking SuperAdmin access: user=%s tenant=%s", auth.user_id, auth.tenant_id)
    if auth.tenant_id != "platform":
        logger.warning("[auth] SuperAdmin access denied for user=%s tenant=%s", auth.user_id, auth.tenant_id)
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform-level privileges required.",
        )
    return auth

# Alias for standard usage if needed
get_current_active_user = require_auth
