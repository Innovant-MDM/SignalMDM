"""
signalmdm/schemas/auth_schema.py
---------------------------------
Pydantic v2 schemas for the authentication endpoints.

All schemas use strict validation and clear field descriptions
to provide useful OpenAPI documentation.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class LoginRequest(BaseModel):
    """Step 1 — credential submission."""

    email:    EmailStr = Field(..., description="Admin email address.")
    password: str      = Field(..., min_length=1, description="Admin password.")


class VerifyOtpRequest(BaseModel):
    """Step 2 — submit the emailed OTP code."""

    admin_id: uuid.UUID = Field(..., description="Returned from /login.")
    code:     str       = Field(..., min_length=6, max_length=6, description="6-digit OTP from email.")


class Verify2FARequest(BaseModel):
    """Step 3 — submit TOTP code from authenticator app."""

    admin_id: uuid.UUID = Field(..., description="Returned from /verify-otp.")
    code:     str       = Field(..., min_length=6, max_length=6, description="6-digit TOTP code.")


class ResendOtpRequest(BaseModel):
    """Resend the OTP email."""

    admin_id: uuid.UUID = Field(..., description="Admin ID from the initial /login response.")


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class AdminProfile(BaseModel):
    """Safe admin profile — never includes password_hash or 2FA secret."""

    admin_id:   uuid.UUID       = Field(..., description="Admin UUID.")
    email:      str             = Field(..., description="Admin email.")
    username:   str             = Field(..., description="Display name.")
    role:       str             = Field(default="admin", description="Role key, e.g. 'super_admin', 'admin'.")
    tenant_id:  str             = Field(default="platform", description="'platform' for platform admins.")
    is_active:  bool
    last_login_at: Optional[datetime]

    model_config = {"from_attributes": True}

    @field_validator("role", mode="before")
    @classmethod
    def coerce_role(cls, v: object) -> str:
        """
        When loading from ORM, PlatformAdmin.role is a PlatformRole relationship
        object (not a string). Extract role_key; fall back to 'admin'.
        """
        if isinstance(v, str):
            return v
        role_key = getattr(v, "role_key", None)
        return role_key if role_key else "admin"


class LoginResponse(BaseModel):
    """
    Returned from POST /login.

    message='verify'  → OTP sent, proceed to /verify-otp
    """

    message:  Literal["verify"]
    admin_id: uuid.UUID = Field(..., description="Use in subsequent verify calls.")
    email:    str       = Field(..., description="Email address where OTP was sent.")


class OtpVerifyResponse(BaseModel):
    """
    Returned from POST /verify-otp.

    message='2fa_setup'    → First-time 2FA: show QR code, then POST /verify-2fa
    message='2fa_required' → 2FA enrolled: enter TOTP code, then POST /verify-2fa
    message='success'      → Authenticated (no 2FA). Cookies set.
    """

    message:  Literal["2fa_setup", "2fa_required", "success"]
    admin_id: Optional[uuid.UUID] = None

    # Only present when message='2fa_setup'
    totp_secret:   Optional[str] = Field(None, description="Base32 TOTP secret for QR code generation.")
    totp_uri:      Optional[str] = Field(None, description="otpauth:// URI for QR code.")

    # Only present when message='success'
    admin:      Optional[AdminProfile] = None
    expires_at: Optional[int]          = Field(None, description="JWT expiry as Unix timestamp.")


class AuthSuccessResponse(BaseModel):
    """
    Returned from POST /verify-2fa and POST /refresh.

    Access token + refresh token are set as httpOnly cookies.
    The response body contains non-sensitive session info only.
    """

    message:    Literal["success"]
    admin:      AdminProfile
    expires_at: int = Field(..., description="Access token expiry as Unix timestamp.")


class MeResponse(BaseModel):
    """Returned from GET /auth/me."""

    admin:      AdminProfile
    role:       str = "admin"


class LogoutResponse(BaseModel):
    """Returned from POST /auth/logout."""

    message: str = "Logged out successfully."


class ErrorResponse(BaseModel):
    """Standard error shape (matches global exception handler)."""

    success: bool  = False
    message: str
    data:    None  = None
    errors:  list[str] = []
