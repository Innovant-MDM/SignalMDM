"""
signalmdm/services/auth_service.py
------------------------------------
Authentication business logic for PlatformAdmin.

Flow summary:
    1. login()          → validate credentials → generate OTP → email → return admin_id
    2. verify_otp()     → validate OTP → (if 2FA) return 2fa step → else issue tokens
    3. verify_2fa()     → validate TOTP → issue tokens
    4. logout()         → revoke token → clear cookies
    5. refresh()        → validate refresh token → issue new tokens
    6. get_me()         → return admin profile from JWT

Security features:
    - Brute-force protection: Redis-backed lock/attempt keys per step
    - Timing-safe dummy bcrypt compare on unknown email
    - OTP stored ONLY in Redis (hashed), never in the database
    - TOTP (pyotp) for 2FA — works with Google Authenticator / Authy
    - Tokens issued as httpOnly cookies (AES-encrypted JWT + refresh token)
    - Token revocation via Redis blacklist (carried over from existing middleware)
"""

from __future__ import annotations

import logging
import secrets
import smtplib
import ssl
import uuid
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

import bcrypt
import pyotp
from fastapi import Response
from sqlalchemy.orm import Session

from core.config import settings
from core.redis_client import get_redis
from db.models.platform_admin import PlatformAdmin
from middleware.token_utils import (
    aes_encrypt,
    compute_fingerprint,
    create_access_token,
    revoke_token,
    is_token_revoked,
    decode_token,
    aes_decrypt,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Redis key helpers
# ---------------------------------------------------------------------------
def _lock_key(step: str, identifier: str) -> str:
    return f"lock:{step}:{identifier.lower()}"

def _attempt_key(step: str, identifier: str) -> str:
    return f"attempt:{step}:{identifier.lower()}"

def _otp_key(admin_id: str) -> str:
    return f"otp:verify:{admin_id}"

def _refresh_key(token: str) -> str:
    return f"refresh:{token}"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_LOGIN_ATTEMPTS  = 5
MAX_OTP_ATTEMPTS    = 5
MAX_2FA_ATTEMPTS    = 5
LOCK_TTL_SECONDS    = 7200   # 2 hours
ATTEMPT_TTL_SECONDS = 3600   # 1 hour
OTP_TTL_SECONDS     = 600    # 10 minutes
REFRESH_TTL_SECONDS = 604800 # 7 days
ACCESS_COOKIE_MAX_AGE  = 2700   # 45 min in seconds
REFRESH_COOKIE_MAX_AGE = 604800 # 7 days in seconds

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _check_lock(step: str, identifier: str) -> bool:
    """Return True if the identifier is currently locked for this step."""
    try:
        return bool(get_redis().exists(_lock_key(step, identifier)))
    except Exception:
        return False  # Redis unavailable → fail open (JWT still protects endpoint)


def _increment_attempt(step: str, identifier: str, max_attempts: int) -> int:
    """
    Increment the attempt counter. Lock the account when max is reached.
    Returns the new attempt count.
    """
    r = get_redis()
    key = _attempt_key(step, identifier)
    attempts = r.incr(key)
    if attempts == 1:
        r.expire(key, ATTEMPT_TTL_SECONDS)
    if attempts >= max_attempts:
        r.setex(_lock_key(step, identifier), LOCK_TTL_SECONDS, "locked")
        r.delete(key)
        logger.warning("[auth_service] %s locked after %d failed %s attempts.", identifier, max_attempts, step)
    return attempts


def _clear_attempts(step: str, identifier: str) -> None:
    """Reset attempt counter on success."""
    try:
        get_redis().delete(_attempt_key(step, identifier))
    except Exception:
        pass


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode(), bcrypt.gensalt(12)).decode()


def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def _generate_otp(length: int = 6) -> str:
    """Cryptographically secure numeric OTP."""
    return "".join([str(secrets.randbelow(10)) for _ in range(length)])


def _store_otp_redis(admin_id: str, plain_otp: str) -> None:
    """Hash the OTP and store it in Redis for OTP_TTL_SECONDS."""
    hashed = bcrypt.hashpw(plain_otp.encode(), bcrypt.gensalt(10)).decode()
    get_redis().setex(_otp_key(admin_id), OTP_TTL_SECONDS, hashed)


def _verify_otp_redis(admin_id: str, plain_otp: str) -> bool:
    """Retrieve hash from Redis and verify. Deletes key on success."""
    stored = get_redis().get(_otp_key(admin_id))
    if not stored:
        return False
    stored_str = stored.decode() if isinstance(stored, bytes) else stored
    return bcrypt.checkpw(plain_otp.encode(), stored_str.encode())


def _send_otp_email(to_email: str, otp_code: str) -> bool:
    """Send OTP email via SMTP. Returns True on success."""
    if not settings.smtp_username or not settings.smtp_password:
        logger.warning("[auth_service] SMTP credentials not configured — skipping email send.")
        # In development, log OTP to console so you can test without SMTP
        logger.info("[DEV] OTP for %s: %s", to_email, otp_code)
        return True

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 480px; margin: 0 auto; padding: 40px 32px; background: #0d1b35; border-radius: 12px;">
        <div style="margin-bottom: 28px;">
            <span style="font-size: 20px; font-weight: 700; color: #ffffff;">Signal<strong style="color: #1557ff;">MDM</strong></span>
        </div>
        <h2 style="font-size: 22px; font-weight: 700; color: #ffffff; margin: 0 0 8px;">Your verification code</h2>
        <p style="font-size: 14px; color: rgba(255,255,255,0.6); margin: 0 0 32px;">
            Enter this code on the SignalMDM login page to continue.
        </p>
        <div style="background: rgba(21,87,255,0.12); border: 1px solid rgba(21,87,255,0.35); border-radius: 10px; padding: 28px; text-align: center; margin-bottom: 28px;">
            <span style="font-size: 40px; font-weight: 800; color: #1557ff; letter-spacing: 12px; font-family: 'Courier New', monospace;">{otp_code}</span>
        </div>
        <p style="font-size: 13px; color: rgba(255,255,255,0.4); margin: 0;">
            This code expires in <strong style="color: rgba(255,255,255,0.6);">10 minutes</strong>.<br>
            If you did not attempt to sign in, please contact your administrator immediately.
        </p>
    </div>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "SignalMDM — Verification Code"
        msg["From"]    = settings.smtp_from or settings.smtp_username
        msg["To"]      = to_email
        msg.attach(MIMEText(html, "html"))

        if settings.smtp_use_tls:
            context = ssl.create_default_context()
            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(settings.smtp_username, to_email, msg.as_string())
        else:
            with smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port) as server:
                server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(settings.smtp_username, to_email, msg.as_string())

        logger.info("[auth_service] OTP email sent to %s.", to_email)
        return True
    except Exception as exc:
        logger.error("[auth_service] SMTP send failed: %s", exc)
        return False


def _issue_tokens(
    admin: PlatformAdmin,
    device_id: str,
    user_agent: str,
    response: Response,
) -> int:
    """
    Create AES-encrypted JWT + refresh token.
    Set both as httpOnly cookies on the response.
    Returns the JWT expiry as Unix timestamp.
    """
    raw_jwt = create_access_token(
        user_id    = str(admin.admin_id),
        tenant_id  = "platform",
        role       = "admin",
        device_id  = device_id,
        user_agent = user_agent,
        extra_claims = {"email": admin.email, "username": admin.username},
        expires_minutes = 45,
    )

    # Decode to read expiry (jose already validated it)
    payload    = decode_token(raw_jwt)
    expires_at = int(payload["exp"])

    encrypted_jwt = aes_encrypt(raw_jwt)
    refresh_token = secrets.token_hex(64)

    # Store refresh token in Redis
    fp_hash = compute_fingerprint(device_id, user_agent, str(admin.admin_id))
    get_redis().setex(
        _refresh_key(refresh_token),
        REFRESH_TTL_SECONDS,
        f"{admin.admin_id}|{fp_hash}",
    )

    is_prod = settings.app_env == "production"

    # Access token cookie — httpOnly, short-lived
    response.set_cookie(
        key      = "accessToken",
        value    = encrypted_jwt,
        httponly = True,
        secure   = is_prod,
        samesite = "lax",
        max_age  = ACCESS_COOKIE_MAX_AGE,
        path     = "/",
    )

    # Refresh token cookie — httpOnly, long-lived
    response.set_cookie(
        key      = "refreshToken",
        value    = refresh_token,
        httponly = True,
        secure   = is_prod,
        samesite = "lax",
        max_age  = REFRESH_COOKIE_MAX_AGE,
        path     = "/api/v1/auth/refresh",  # restrict to refresh endpoint
    )

    # Non-httpOnly info cookie (JS-readable, non-sensitive)
    response.set_cookie(
        key      = "adminInfo",
        value    = f'{{"username":"{admin.username}","email":"{admin.email}","role":"admin","tenant_id":"platform"}}',
        httponly = False,
        secure   = is_prod,
        samesite = "lax",
        max_age  = ACCESS_COOKIE_MAX_AGE,
        path     = "/",
    )

    # Update last_login_at (caller must commit the session)
    admin.last_login_at = datetime.now(timezone.utc)

    return expires_at


# ---------------------------------------------------------------------------
# Service functions
# ---------------------------------------------------------------------------

def login(email: str, password: str, db: Session) -> dict:
    """
    Step 1 — validate credentials, send OTP, return admin_id.

    Raises HTTPException on any failure (called by router).
    Returns plain dict so router can build the typed response.
    """
    from fastapi import HTTPException, status

    # Lock check
    if _check_lock("login", email):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account locked due to multiple failed attempts. Try again in 2 hours.",
        )

    logger.info("[auth_service] Login attempt for email: %s", email)
    admin: Optional[PlatformAdmin] = (
        db.query(PlatformAdmin)
        .filter(PlatformAdmin.email == email)
        .first()
    )

    # Timing-safe: always run bcrypt even if user not found
    # Using a validly formatted hash to avoid ValueError: Invalid salt
    dummy_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TiGTmLwCEZxgcJsf3DeMrVUFlDIG"
    if not admin:
        logger.warning("[auth_service] User not found: %s", email)
        bcrypt.checkpw(b"dummy", dummy_hash.encode())
        _increment_attempt("login", email, MAX_LOGIN_ATTEMPTS)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    if not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled. Contact your administrator.",
        )

    if not _verify_password(password, admin.password_hash):
        logger.warning("[auth_service] Password mismatch for user: %s", email)
        _increment_attempt("login", email, MAX_LOGIN_ATTEMPTS)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    # Success — clear attempts, generate OTP
    _clear_attempts("login", email)
    _clear_attempts("login", str(admin.admin_id))

    otp = _generate_otp()
    _store_otp_redis(str(admin.admin_id), otp)

    sent = _send_otp_email(admin.email, otp)
    if not sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email. Check SMTP configuration.",
        )

    return {"admin_id": admin.admin_id, "email": admin.email}


def verify_otp(
    admin_id: uuid.UUID,
    code: str,
    device_id: str,
    user_agent: str,
    db: Session,
    response: Response,
) -> dict:
    """
    Step 2 — verify emailed OTP.

    Returns a dict with message='2fa_setup' | '2fa_required' | 'success'.
    """
    from fastapi import HTTPException, status

    admin_id_str = str(admin_id)

    # Lock check
    if _check_lock("otp", admin_id_str):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Too many failed OTP attempts. Try again in 2 hours.",
        )

    admin: Optional[PlatformAdmin] = db.get(PlatformAdmin, admin_id)
    if not admin:
        _increment_attempt("otp", admin_id_str, MAX_OTP_ATTEMPTS)
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found.")

    if getattr(admin, 'is_blocked', False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been blocked. Contact your administrator.",
        )

    if not _verify_otp_redis(admin_id_str, code):
        _increment_attempt("otp", admin_id_str, MAX_OTP_ATTEMPTS)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired verification code.",
        )

    # Success
    _clear_attempts("otp", admin_id_str)
    get_redis().delete(_otp_key(admin_id_str))

    if admin.two_fa_enabled:
        if not admin.two_fa_setup_complete:
            # Generate TOTP secret for first-time setup
            secret = pyotp.random_base32()
            admin.two_fa_secret = secret
            admin.updated_at = datetime.now(timezone.utc)
            db.commit()
            totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
                name=admin.email, issuer_name="SignalMDM"
            )
            return {
                "message":     "2fa_setup",
                "admin_id":    admin.admin_id,
                "totp_secret": secret,
                "totp_uri":    totp_uri,
            }
        return {"message": "2fa_required", "admin_id": admin.admin_id}

    # No 2FA — issue tokens
    expires_at = _issue_tokens(admin, device_id, user_agent, response)
    db.commit()

    return {
        "message":    "success",
        "admin":      admin,
        "expires_at": expires_at,
    }


def verify_2fa(
    admin_id: uuid.UUID,
    code: str,
    device_id: str,
    user_agent: str,
    db: Session,
    response: Response,
) -> dict:
    """Step 3 — verify TOTP code, complete authentication."""
    from fastapi import HTTPException, status

    admin_id_str = str(admin_id)

    if _check_lock("2fa", admin_id_str):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Too many failed 2FA attempts. Try again in 2 hours.",
        )

    admin: Optional[PlatformAdmin] = db.get(PlatformAdmin, admin_id)
    if not admin or not admin.two_fa_secret:
        _increment_attempt("2fa", admin_id_str, MAX_2FA_ATTEMPTS)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="2FA not configured.")

    totp = pyotp.TOTP(admin.two_fa_secret)
    if not totp.verify(code, valid_window=1):
        _increment_attempt("2fa", admin_id_str, MAX_2FA_ATTEMPTS)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid 2FA code.",
        )

    _clear_attempts("2fa", admin_id_str)

    # Mark setup complete on first verified use
    if not admin.two_fa_setup_complete:
        admin.two_fa_setup_complete = True

    expires_at = _issue_tokens(admin, device_id, user_agent, response)
    db.commit()

    return {"message": "success", "admin": admin, "expires_at": expires_at}


def resend_otp(admin_id: uuid.UUID, db: Session) -> dict:
    """Regenerate and resend OTP (rate-limited: check lock)."""
    from fastapi import HTTPException, status

    admin_id_str = str(admin_id)

    if _check_lock("otp", admin_id_str):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="OTP requests are rate-limited. Wait before requesting a new code.",
        )

    admin: Optional[PlatformAdmin] = db.get(PlatformAdmin, admin_id)
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin not found.")

    otp = _generate_otp()
    _store_otp_redis(admin_id_str, otp)
    sent = _send_otp_email(admin.email, otp)

    if not sent:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email.",
        )
    return {"message": "Verification code resent."}


def logout(raw_jwt: str, refresh_cookie: Optional[str], response: Response) -> dict:
    """Revoke access token in Redis, delete refresh token, clear cookies."""
    revoke_token(raw_jwt)

    if refresh_cookie:
        try:
            get_redis().delete(_refresh_key(refresh_cookie))
        except Exception:
            pass

    response.delete_cookie("accessToken",  path="/")
    response.delete_cookie("refreshToken", path="/api/v1/auth/refresh")
    response.delete_cookie("adminInfo",    path="/")

    return {"message": "Logged out successfully."}


def refresh_tokens(
    refresh_cookie: Optional[str],
    device_id: str,
    user_agent: str,
    db: Session,
    response: Response,
) -> dict:
    """Validate refresh token, reissue access + refresh cookies."""
    from fastapi import HTTPException, status

    if not refresh_cookie:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No refresh token.")

    stored = None
    try:
        stored = get_redis().get(_refresh_key(refresh_cookie))
    except Exception:
        pass

    if not stored:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired refresh token.")

    stored_str = stored.decode() if isinstance(stored, bytes) else stored
    parts = stored_str.split("|", 1)
    if len(parts) != 2:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Malformed refresh token.")

    admin_id_str, stored_fp = parts
    current_fp = compute_fingerprint(device_id, user_agent, admin_id_str)
    if current_fp != stored_fp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Device mismatch. Please log in again.",
        )

    try:
        admin_uuid = uuid.UUID(admin_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token data.")

    admin: Optional[PlatformAdmin] = db.get(PlatformAdmin, admin_uuid)
    if not admin or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found or disabled.")

    # Rotate: delete old refresh token, issue new tokens
    get_redis().delete(_refresh_key(refresh_cookie))
    expires_at = _issue_tokens(admin, device_id, user_agent, response)
    db.commit()

    return {"message": "success", "admin": admin, "expires_at": expires_at}


def get_me(admin_id_str: str, db: Session) -> PlatformAdmin:
    """Return admin profile from verified JWT sub."""
    from fastapi import HTTPException, status

    try:
        admin_uuid = uuid.UUID(admin_id_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token.")

    admin: Optional[PlatformAdmin] = db.get(PlatformAdmin, admin_uuid)
    if not admin or not admin.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Admin not found.")
    return admin
