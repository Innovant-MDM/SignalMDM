"""
signalmdm/routers/auth_router.py
----------------------------------
Authentication endpoints for PlatformAdmin.

All endpoints return the global StandardResponse envelope:
    { success, message, data, errors }

Protected endpoints use Depends(require_auth) which now reads
the accessToken httpOnly cookie (see middleware/auth.py).

Endpoints:
    POST /api/v1/auth/login          — no auth required
    POST /api/v1/auth/verify-otp     — no auth required
    POST /api/v1/auth/verify-2fa     — no auth required
    POST /api/v1/auth/resend-otp     — no auth required
    POST /api/v1/auth/refresh        — no auth required (reads refresh cookie)
    POST /api/v1/auth/logout         — require_auth
    GET  /api/v1/auth/me             — require_auth
"""

from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Cookie, Depends, Header, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from db.sessions.database import get_db
from middleware.auth import require_auth, TokenPayload
from schemas.auth_schema import (
    AdminProfile,
    AuthSuccessResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    MeResponse,
    OtpVerifyResponse,
    ResendOtpRequest,
    Verify2FARequest,
    VerifyOtpRequest,
)
from services.auth import auth_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Helper — standard response wrapper
# ---------------------------------------------------------------------------

def ok(message: str, data=None) -> dict:
    return {"success": True, "message": message, "data": data, "errors": []}


# ---------------------------------------------------------------------------
# Step 1 — Login
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    summary="Submit credentials (Step 1 of login)",
    response_description="OTP sent to admin email.",
)
def login(
    body: LoginRequest,
    db: Session = Depends(get_db),
) -> dict:
    """
    Validate email + password.
    On success, a 6-digit OTP is emailed to the admin.

    Returns `admin_id` which must be passed to `/verify-otp`.
    """
    result = auth_service.login(
        email    = body.email,
        password = body.password,
        db       = db,
    )
    return ok(
        "verify",
        LoginResponse(
            message  = "verify",
            admin_id = result["admin_id"],
            email    = result["email"],
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Step 2 — Verify OTP
# ---------------------------------------------------------------------------

@router.post(
    "/verify-otp",
    summary="Submit emailed OTP (Step 2 of login)",
)
def verify_otp(
    body:       VerifyOtpRequest,
    request:    Request,
    response:   Response,
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Verify the 6-digit OTP sent to the admin's email.

    Possible outcomes:
    - `message='2fa_setup'`    → first-time 2FA, QR code data returned
    - `message='2fa_required'` → submit TOTP to `/verify-2fa`
    - `message='success'`      → fully authenticated, cookies set
    """
    device_id  = x_device_id or request.headers.get("X-Device-ID") or "web-client"
    user_agent = request.headers.get("user-agent") or ""

    result = auth_service.verify_otp(
        admin_id   = body.admin_id,
        code       = body.code,
        device_id  = device_id,
        user_agent = user_agent,
        db         = db,
        response   = response,
    )

    msg = result["message"]

    if msg == "success":
        return ok(
            "Authentication successful.",
            OtpVerifyResponse(
                message    = "success",
                admin      = AdminProfile.model_validate(result["admin"]),
                expires_at = result["expires_at"],
            ).model_dump(),
        )

    if msg == "2fa_setup":
        return ok(
            "2FA setup required.",
            OtpVerifyResponse(
                message      = "2fa_setup",
                admin_id     = result["admin_id"],
                totp_secret  = result["totp_secret"],
                totp_uri     = result["totp_uri"],
            ).model_dump(),
        )

    # 2fa_required
    return ok(
        "2FA verification required.",
        OtpVerifyResponse(
            message  = "2fa_required",
            admin_id = result["admin_id"],
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Step 3 — Verify TOTP 2FA
# ---------------------------------------------------------------------------

@router.post(
    "/verify-2fa",
    summary="Submit TOTP code (Step 3 — only if 2FA enabled)",
)
def verify_2fa(
    body:       Verify2FARequest,
    request:    Request,
    response:   Response,
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    db: Session = Depends(get_db),
) -> dict:
    """Verify a 6-digit TOTP code from an authenticator app."""
    device_id  = x_device_id or request.headers.get("X-Device-ID") or "web-client"
    user_agent = request.headers.get("user-agent") or ""

    result = auth_service.verify_2fa(
        admin_id   = body.admin_id,
        code       = body.code,
        device_id  = device_id,
        user_agent = user_agent,
        db         = db,
        response   = response,
    )

    return ok(
        "Authentication successful.",
        AuthSuccessResponse(
            message    = "success",
            admin      = AdminProfile.model_validate(result["admin"]),
            expires_at = result["expires_at"],
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Resend OTP
# ---------------------------------------------------------------------------

@router.post(
    "/resend-otp",
    summary="Resend OTP email",
)
def resend_otp(
    body: ResendOtpRequest,
    db: Session = Depends(get_db),
) -> dict:
    """Generate a fresh OTP and resend to the admin's email."""
    result = auth_service.resend_otp(admin_id=body.admin_id, db=db)
    return ok(result["message"])


# ---------------------------------------------------------------------------
# Refresh tokens
# ---------------------------------------------------------------------------

@router.post(
    "/refresh",
    summary="Refresh access token using refresh cookie",
)
def refresh(
    request:  Request,
    response: Response,
    x_device_id: Optional[str] = Header(None, alias="X-Device-ID"),
    refresh_token: Optional[str] = Cookie(None, alias="refreshToken"),
    db: Session = Depends(get_db),
) -> dict:
    """
    Issue a new access token using the httpOnly refresh cookie.
    Both cookies are rotated (refresh token is single-use).
    """
    device_id  = x_device_id or request.headers.get("X-Device-ID") or "web-client"
    user_agent = request.headers.get("user-agent") or ""

    result = auth_service.refresh_tokens(
        refresh_cookie = refresh_token,
        device_id      = device_id,
        user_agent     = user_agent,
        db             = db,
        response       = response,
    )

    return ok(
        "Token refreshed.",
        AuthSuccessResponse(
            message    = "success",
            admin      = AdminProfile.model_validate(result["admin"]),
            expires_at = result["expires_at"],
        ).model_dump(),
    )


# ---------------------------------------------------------------------------
# Logout  (protected)
# ---------------------------------------------------------------------------

@router.post(
    "/logout",
    summary="Logout — revoke tokens and clear cookies",
)
def logout(
    request:  Request,
    response: Response,
    auth: TokenPayload = Depends(require_auth),
    refresh_token: Optional[str] = Cookie(None, alias="refreshToken"),
) -> dict:
    """
    Revoke the current access token in Redis and clear all auth cookies.
    Requires a valid `accessToken` cookie (or Authorization header).
    """
    result = auth_service.logout(
        raw_jwt        = auth.raw_jwt,
        refresh_cookie = refresh_token,
        response       = response,
    )
    return ok(result["message"])


# ---------------------------------------------------------------------------
# Me  (protected)
# ---------------------------------------------------------------------------

@router.get(
    "/me",
    summary="Return the authenticated admin's profile",
)
def me(
    auth: TokenPayload = Depends(require_auth),
    db: Session = Depends(get_db),
) -> dict:
    """
    Return the profile of the currently authenticated admin.
    Validates the JWT and returns non-sensitive admin data.
    """
    admin = auth_service.get_me(admin_id_str=auth.user_id, db=db)
    return ok(
        "Admin profile.",
        MeResponse(
            admin = AdminProfile.model_validate(admin),
            role  = "admin",
        ).model_dump(),
    )
