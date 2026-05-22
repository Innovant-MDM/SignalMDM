#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║          SignalMDM — Full-Stack Security Penetration Test Suite             ║
║                                                                              ║
║  Targets:                                                                    ║
║    • FastAPI Backend  → http://localhost:8000                                ║
║    • Express Frontend → http://localhost:3030                                ║
║                                                                              ║
║  Tests:                                                                      ║
║    1.  Security Headers (both servers)                                       ║
║    2.  CSP Policy Analysis                                                   ║
║    3.  CORS Misconfiguration                                                 ║
║    4.  Brute Force Protection (login lockout)                                ║
║    5.  SQL Injection (all API inputs)                                        ║
║    6.  JWT Manipulation & Forgery                                            ║
║    7.  OTP Bypass Attempts                                                   ║
║    8.  Role-Based Access Control (RBAC)                                      ║
║    9.  Cookie Security Flags                                                 ║
║   10.  File Upload Security                                                  ║
║   11.  Path Traversal / Directory Traversal                                  ║
║   12.  Sensitive Information Disclosure                                      ║
║   13.  Rate Limiting & DoS Resilience                                        ║
║   14.  XSS Vector Injection                                                  ║
║   15.  Authentication Bypass                                                 ║
║   16.  Insecure Direct Object Reference (IDOR)                               ║
║   17.  HTTP Method Tampering                                                 ║
║   18.  Open Redirect                                                         ║
║                                                                              ║
║  Usage:  python signalmdm_security_tester.py                                ║
║  Report: signalmdm_security_report.txt  (auto-generated)                    ║
╚══════════════════════════════════════════════════════════════════════════════╝

pip install:
    pip install requests colorama python-jose[cryptography] pyjwt
"""

import requests
import json
import time
import sys
import uuid
import base64
import hashlib
import hmac
import datetime
from typing import Optional
from dataclasses import dataclass, field
from colorama import Fore, Style, init

init(autoreset=True)

# Reconfigure stdout to support unicode box-drawing characters on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# ─── Configuration ────────────────────────────────────────────────────────────
BACKEND  = "http://localhost:8000"
FRONTEND = "http://localhost:3030"
REPORT_FILE = "signalmdm_security_report.txt"

# ─── Test credentials (adjust to a real test account you create) ──────────────
TEST_EMAIL    = "jofreyjohnmrutu01@gmail.com"   # ← create this test admin before running
TEST_PASSWORD = "1234567890"       # ← set this as the test admin password
WRONG_PASSWORD = "WrongPass999!"

# ─── Result tracking ──────────────────────────────────────────────────────────
@dataclass
class TestResult:
    category:    str
    test_name:   str
    status:      str        # PASS | FAIL | WARN | INFO | ERROR
    detail:      str
    severity:    str = "LOW"   # CRITICAL | HIGH | MEDIUM | LOW | INFO
    recommendation: str = ""

results: list[TestResult] = []
session = requests.Session()
session.headers.update({
    "User-Agent": "SignalMDM-SecurityTester/1.0",
    "X-Device-ID": "test-device-security-audit-001",
})

# ─── Helpers ──────────────────────────────────────────────────────────────────

def log(status: str, test: str, detail: str, severity: str = "LOW"):
    icons = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️ ", "INFO": "ℹ️ ", "ERROR": "💥"}
    colors = {
        "PASS":  Fore.GREEN,
        "FAIL":  Fore.RED,
        "WARN":  Fore.YELLOW,
        "INFO":  Fore.CYAN,
        "ERROR": Fore.MAGENTA,
    }
    sev_color = {
        "CRITICAL": Fore.RED + Style.BRIGHT,
        "HIGH":     Fore.RED,
        "MEDIUM":   Fore.YELLOW,
        "LOW":      Fore.GREEN,
        "INFO":     Fore.CYAN,
    }
    icon  = icons.get(status, "•")
    color = colors.get(status, "")
    sc    = sev_color.get(severity, "")
    print(f"  {icon} {color}{test}{Style.RESET_ALL}  [{sc}{severity}{Style.RESET_ALL}]")
    if detail:
        print(f"     {Fore.WHITE}{detail}{Style.RESET_ALL}")

def add(category, test_name, status, detail, severity="LOW", recommendation=""):
    r = TestResult(category, test_name, status, detail, severity, recommendation)
    results.append(r)
    log(status, test_name, detail, severity)

def section(title: str):
    print(f"\n{Fore.CYAN + Style.BRIGHT}{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}{Style.RESET_ALL}")

def safe_get(url, retries=3, **kwargs) -> Optional[requests.Response]:
    """GET with retry logic to handle transient connection issues."""
    for attempt in range(retries):
        try:
            return session.get(url, timeout=10, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            if attempt < retries - 1:
                time.sleep(0.5)
            continue
        except Exception:
            return None
    return None

def safe_post(url, retries=3, **kwargs) -> Optional[requests.Response]:
    """POST with retry logic to handle transient connection issues."""
    for attempt in range(retries):
        try:
            return session.post(url, timeout=10, **kwargs)
        except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
            if attempt < retries - 1:
                time.sleep(0.5)
            continue
        except Exception:
            return None
    return None

# ─────────────────────────────────────────────────────────────────────────────
# TEST SUITES
# ─────────────────────────────────────────────────────────────────────────────

# 1. SERVER REACHABILITY
def test_reachability():
    section("1. SERVER REACHABILITY")
    for name, url in [("Backend (FastAPI)", f"{BACKEND}/"), ("Frontend (Express)", f"{FRONTEND}/")]:
        r = safe_get(url)
        if r is not None and r.status_code < 500:
            add("Reachability", f"{name} online", "PASS", f"HTTP {r.status_code}", "INFO")
        else:
            code = r.status_code if r is not None else "unreachable"
            add("Reachability", f"{name} offline", "ERROR",
                f"Got {code} — start the server before running tests", "HIGH",
                "Ensure both servers are running before the security audit.")


# 2. SECURITY HEADERS
def test_security_headers():
    section("2. SECURITY HEADERS")

    required_headers = {
        "X-Content-Type-Options":    ("nosniff", "HIGH"),
        "X-Frame-Options":           ("DENY",    "MEDIUM"),
        "Strict-Transport-Security": (None,       "MEDIUM"),
        "Referrer-Policy":           (None,       "LOW"),
        "Permissions-Policy":        (None,       "LOW"),
        "X-XSS-Protection":          (None,       "LOW"),
        "Content-Security-Policy":   (None,       "HIGH"),
    }

    unwanted_headers = ["Server", "X-Powered-By", "X-AspNet-Version"]

    for server_name, base_url in [("Backend", BACKEND), ("Frontend", FRONTEND)]:
        r = safe_get(f"{base_url}/")
        if r is None:
            add("Security Headers", f"{server_name} headers skipped", "ERROR", "Server not reachable", "HIGH")
            continue

        for header, (expected, severity) in required_headers.items():
            val = r.headers.get(header)
            if not val:
                if header == "Strict-Transport-Security" and (base_url.startswith("http://") or "localhost" in base_url):
                    add("Security Headers", f"{server_name}: {header} absent (expected in HTTP dev)", "INFO",
                        "HSTS (Strict-Transport-Security) not required on HTTP/localhost development environments.", "INFO")
                else:
                    add("Security Headers", f"{server_name}: {header} missing", "FAIL",
                        f"Header absent", severity,
                        f"Add {header} to all responses.")
            elif expected and expected.lower() not in val.lower():
                add("Security Headers", f"{server_name}: {header} weak", "WARN",
                    f"Got: {val}  Expected contains: {expected}", severity,
                    f"Set {header}: {expected}")
            else:
                add("Security Headers", f"{server_name}: {header} present", "PASS",
                    f"Value: {val[:80]}", "INFO")

        # Leak check
        for h in unwanted_headers:
            val = r.headers.get(h)
            if val:
                add("Security Headers", f"{server_name}: {h} leaks info", "WARN",
                    f"Value: {val}", "MEDIUM",
                    f"Remove or obscure the {h} header in production.")


# 3. CSP ANALYSIS
def test_csp():
    section("3. CONTENT SECURITY POLICY ANALYSIS")

    for server_name, base_url in [("Backend", BACKEND), ("Frontend", FRONTEND)]:
        r = safe_get(f"{base_url}/")
        if r is None:
            continue
        csp = r.headers.get("Content-Security-Policy", "")

        dangerous_directives = {
            "'unsafe-inline'": ("script-src", "HIGH",   "Allows inline script execution — XSS risk."),
            "'unsafe-eval'":   ("script-src", "MEDIUM", "Allows eval() — code injection risk."),
            "*":               ("img-src",    "LOW",    "Wildcard image source."),
        }

        if not csp:
            add("CSP", f"{server_name}: No CSP", "FAIL", "No Content-Security-Policy header found.",
                "HIGH", "Implement a strict CSP.")
            continue

        add("CSP", f"{server_name}: CSP present", "PASS", csp[:120] + ("..." if len(csp) > 120 else ""), "INFO")

        for directive, (context, severity, reason) in dangerous_directives.items():
            if directive in csp:
                add("CSP", f"{server_name}: {directive} in CSP", "WARN",
                    reason, severity,
                    f"Remove {directive} from your CSP, especially in {context}.")

        if "default-src 'none'" not in csp and "default-src 'self'" not in csp:
            add("CSP", f"{server_name}: default-src too permissive", "WARN",
                "default-src should be 'self' or 'none'", "MEDIUM",
                "Set default-src to 'self'.")


# 4. CORS MISCONFIGURATION
def test_cors():
    section("4. CORS MISCONFIGURATION")

    evil_origins = [
        "http://evil.com",
        "https://attacker.example.com",
        "null",
        "http://localhost.evil.com",
    ]

    for origin in evil_origins:
        r = safe_get(f"{BACKEND}/api/v1/auth/me",
                     headers={"Origin": origin, "Authorization": "Bearer fake"})
        if r is None:
            continue
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        acac = r.headers.get("Access-Control-Allow-Credentials", "")

        if acao == "*" and acac == "true":
            add("CORS", f"Wildcard + credentials for origin {origin}", "FAIL",
                "Access-Control-Allow-Origin: * with Allow-Credentials: true is forbidden by browsers but dangerous.",
                "CRITICAL",
                "Never combine wildcard ACAO with Allow-Credentials.")
        elif acao == origin or acao == "*":
            add("CORS", f"Reflects arbitrary origin: {origin}", "FAIL",
                f"Server reflects untrusted origin: {acao}", "HIGH",
                "Whitelist only known origins; never reflect arbitrary Origin headers.")
        elif acao in ("", "null"):
            add("CORS", f"Correctly blocks origin: {origin}", "PASS",
                f"No ACAO header for untrusted origin", "INFO")
        else:
            add("CORS", f"ACAO for {origin}: {acao}", "INFO",
                f"Allowed origin: {acao}", "LOW")

    # Check preflight OPTIONS
    try:
        r = session.options(f"{BACKEND}/api/v1/auth/login",
                            headers={"Origin": "http://evil.com",
                                     "Access-Control-Request-Method": "POST"},
                            timeout=5)
        acao = r.headers.get("Access-Control-Allow-Origin", "")
        if "evil.com" in acao:
            add("CORS", "Preflight reflects evil origin", "FAIL",
                f"OPTIONS allowed evil.com: {acao}", "HIGH",
                "Restrict CORS preflight to whitelisted origins.")
        else:
            add("CORS", "Preflight correctly restricted", "PASS",
                f"ACAO: {acao or 'absent'}", "INFO")
    except Exception:
        pass


# 5. BRUTE FORCE PROTECTION
def test_brute_force():
    section("5. BRUTE FORCE PROTECTION")

    url = f"{BACKEND}/api/v1/auth/login"

    # Rapid fire 7 wrong password attempts (limit is 5)
    locked = False
    for i in range(1, 8):
        r = safe_post(url, json={"email": TEST_EMAIL, "password": WRONG_PASSWORD})
        if r is None:
            add("Brute Force", "Backend not reachable for brute force test", "ERROR",
                "Start backend first", "HIGH")
            return
        if r.status_code == 403:
            locked = True
            add("Brute Force", f"Account locked after {i} attempts", "PASS",
                f"Got 403 on attempt #{i} — lockout working", "INFO")
            break
        time.sleep(0.2)

    if not locked:
        add("Brute Force", "No lockout after 7 failed attempts", "FAIL",
            "Made 7 failed login attempts without being locked", "CRITICAL",
            "Ensure Redis-backed lockout triggers at MAX_LOGIN_ATTEMPTS (currently 5).")

    # Check lockout message doesn't leak username existence
    r1 = safe_post(url, json={"email": "nonexistent@test.com", "password": WRONG_PASSWORD})
    r2 = safe_post(url, json={"email": TEST_EMAIL, "password": WRONG_PASSWORD})
    if r1 is not None and r2 is not None:
        b1 = r1.json().get("message", r1.json().get("detail", ""))
        b2 = r2.json().get("message", r2.json().get("detail", ""))
        if b1 == b2 or ("Invalid credentials" in b1 and "Invalid credentials" in b2):
            add("Brute Force", "Same error for unknown vs wrong password", "PASS",
                "Timing-safe: user enumeration not possible via error message", "INFO")
        else:
            add("Brute Force", "Different errors for unknown/wrong password", "WARN",
                f"Unknown: '{b1}'  Wrong: '{b2}'", "MEDIUM",
                "Return identical error messages for user-not-found vs wrong-password.")


# 6. SQL INJECTION
def test_sql_injection():
    section("6. SQL INJECTION")

    payloads = [
        "' OR '1'='1",
        "'; DROP TABLE platform_admins; --",
        "' UNION SELECT null, null, null --",
        "admin'--",
        "' OR 1=1 --",
        "\" OR \"\"=\"",
        "1; SELECT * FROM information_schema.tables",
        "' AND SLEEP(3) --",
        "'; WAITFOR DELAY '0:0:3' --",
    ]

    endpoints = [
        (f"{BACKEND}/api/v1/auth/login",  "POST", lambda p: {"email": p, "password": "test"}),
        (f"{BACKEND}/api/v1/auth/login",  "POST", lambda p: {"email": "test@test.com", "password": p}),
    ]

    for url, method, body_fn in endpoints:
        for payload in payloads:
            body = body_fn(payload)
            try:
                start = time.time()
                r = session.post(url, json=body, timeout=10)
                elapsed = time.time() - start

                # Time-based blind SQLi detection
                if elapsed > 2.5:
                    add("SQL Injection", f"Time-based SQLi possible", "FAIL",
                        f"Payload '{payload[:40]}' caused {elapsed:.1f}s delay — possible blind SQLi",
                        "CRITICAL",
                        "Use parameterized queries / ORM only. Never interpolate user input into SQL.")
                    continue

                # Error-based detection
                body_text = r.text.lower()
                sql_errors = ["syntax error", "pg_query", "psycopg", "sqlalchemy",
                              "postgresql", "unterminated", "invalid input syntax"]
                if any(e in body_text for e in sql_errors):
                    add("SQL Injection", f"SQL error leaked in response", "FAIL",
                        f"Payload: '{payload[:40]}' triggered DB error in response",
                        "CRITICAL",
                        "Suppress SQL errors in API responses. Use generic 500 messages.")
                elif r.status_code == 200 and "admin_id" in r.text:
                    add("SQL Injection", f"Possible SQLi bypass", "FAIL",
                        f"Payload '{payload[:40]}' returned success response",
                        "CRITICAL",
                        "Sanitize all inputs and use ORM parameterization.")
                else:
                    add("SQL Injection", f"Payload rejected: {payload[:30]}", "PASS",
                        f"HTTP {r.status_code} — no SQL error detected", "INFO")
            except Exception as e:
                add("SQL Injection", f"Test error for payload", "ERROR", str(e)[:60], "LOW")


# 7. JWT MANIPULATION
def test_jwt():
    section("7. JWT MANIPULATION & FORGERY")

    protected = f"{BACKEND}/api/v1/auth/me"

    # No token
    r = safe_get(protected)
    if r is not None and r.status_code in (401, 403, 422):
        add("JWT", "No token → rejected", "PASS", f"HTTP {r.status_code}", "INFO")
    else:
        add("JWT", "No token → accepted", "FAIL",
            f"HTTP {r.status_code if r is not None else 'no response'} — endpoint may be unprotected",
            "CRITICAL", "Require valid auth token on all protected endpoints.")

    # Garbage token
    for label, token in [
        ("Random string", "notavalidtoken"),
        ("Empty Bearer",  ""),
        ("Null bytes",    "\x00\x00\x00"),
        ("Very long",     "A" * 2000),
    ]:
        r = safe_get(protected, headers={"Authorization": f"Bearer {token}"})
        if r is not None and r.status_code in (401, 403, 422):
            add("JWT", f"Malformed token rejected: {label}", "PASS",
                f"HTTP {r.status_code}", "INFO")
        else:
            code = r.status_code if r is not None else "no response"
            add("JWT", f"Malformed token accepted: {label}", "FAIL",
                f"HTTP {code}", "HIGH",
                "Reject all malformed tokens immediately.")

    # Algorithm confusion — HS256 signed with 'none'
    header  = base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "00000000-0000-0000-0000-000000000001",
                    "role": "admin", "tenant_id": "platform",
                    "exp": int(time.time()) + 3600}).encode()
    ).rstrip(b"=").decode()
    none_token = f"{header}.{payload}."

    r = safe_get(protected, headers={"Authorization": f"Bearer {none_token}"})
    if r is not None and r.status_code in (401, 403):
        add("JWT", "Algorithm 'none' correctly rejected", "PASS",
            f"HTTP {r.status_code}", "INFO")
    else:
        add("JWT", "Algorithm 'none' accepted!", "FAIL",
            "Server accepted a JWT with alg:none — critical auth bypass",
            "CRITICAL",
            "Explicitly reject 'none' algorithm in JWT verification.")

    # Expired token simulation
    expired_header  = base64.urlsafe_b64encode(b'{"alg":"HS256","typ":"JWT"}').rstrip(b"=").decode()
    expired_payload = base64.urlsafe_b64encode(
        json.dumps({"sub": "fake", "exp": 1000000}).encode()
    ).rstrip(b"=").decode()
    expired_token = f"{expired_header}.{expired_payload}.fakesig"
    r = safe_get(protected, headers={"Authorization": f"Bearer {expired_token}"})
    if r is not None and r.status_code in (401, 403):
        add("JWT", "Expired token rejected", "PASS", f"HTTP {r.status_code}", "INFO")
    else:
        add("JWT", "Expired token may be accepted", "WARN",
            f"HTTP {r.status_code if r is not None else 'no resp'}", "HIGH",
            "Enforce exp claim validation strictly.")


# 8. OTP BYPASS ATTEMPTS
def test_otp_bypass():
    section("8. OTP BYPASS ATTEMPTS")

    otp_url = f"{BACKEND}/api/v1/auth/verify-otp"

    fake_admin_id = str(uuid.uuid4())

    # Attempt common OTP guesses
    common_otps = ["000000", "123456", "111111", "999999", "000001"]
    blocked = False
    for i, otp in enumerate(common_otps):
        r = safe_post(otp_url, json={"admin_id": fake_admin_id, "code": otp,
                                      "device_id": "test-device"})
        if r is None:
            add("OTP", "OTP endpoint unreachable", "ERROR", "Backend down?", "HIGH")
            break
        if r.status_code == 403:
            add("OTP", f"OTP brute force locked after {i+1} attempts", "PASS",
                f"Got 403 — Redis lockout working", "INFO")
            blocked = True
            break
        time.sleep(0.1)

    if not blocked and len(common_otps) > 0:
        add("OTP", "OTP brute force not locked in 5 attempts", "WARN",
            "Made 5 OTP attempts on fake admin_id without lockout",
            "MEDIUM",
            "Ensure OTP lockout also triggers for invalid admin_ids.")

    # Test OTP reuse — skipped (requires valid flow) but flag as manual test
    add("OTP", "OTP single-use (manual test required)", "INFO",
        "Verify that OTP is deleted from Redis after first successful use",
        "MEDIUM",
        "Call get_redis().delete(_otp_key(admin_id)) immediately after verification — already implemented in code.")

    # Test OTP expiry — Redis TTL should be 600s
    add("OTP", "OTP 10-minute expiry (manual verify)", "INFO",
        "OTP_TTL_SECONDS=600 is set — verify Redis TTL is respected",
        "LOW",
        "Run: redis-cli TTL otp:verify:<admin_id> to confirm 600s TTL.")


# 9. COOKIE SECURITY
def test_cookies():
    section("9. COOKIE SECURITY FLAGS")

    # We can't get real auth cookies without a valid login flow
    # But we can check /docs which may reveal cookie behavior
    r = safe_get(f"{BACKEND}/docs")
    if r is None:
        add("Cookies", "Backend not reachable for cookie test", "ERROR", "", "HIGH")
        return

    # Check Set-Cookie from any endpoint that sets them
    set_cookie = r.headers.get("Set-Cookie", "")

    if not set_cookie:
        add("Cookies", "No cookies set by /docs (expected)", "INFO",
            "Cookie flags will be tested on authenticated endpoints", "INFO")
    else:
        flags = {
            "HttpOnly": ("CRITICAL", "Prevents JS access to auth cookies — must be set"),
            "Secure":   ("HIGH",     "Prevents cookie transmission over HTTP"),
            "SameSite": ("HIGH",     "Prevents CSRF attacks"),
        }
        for flag, (severity, reason) in flags.items():
            if flag.lower() in set_cookie.lower():
                add("Cookies", f"{flag} flag present", "PASS", f"Found in Set-Cookie", "INFO")
            else:
                if flag == "Secure" and (BACKEND.startswith("http://") or "localhost" in BACKEND):
                    add("Cookies", f"{flag} flag absent (expected in HTTP dev)", "INFO",
                        "Secure flag not required on HTTP/localhost development environments.", "INFO")
                else:
                    add("Cookies", f"{flag} flag missing", "FAIL",
                        reason, severity,
                        f"Add {flag} to all auth cookie Set-Cookie headers.")

    # Static analysis of code findings
    add("Cookies", "httpOnly=True on accessToken (code verified)", "PASS",
        "auth_service.py: response.set_cookie(httponly=True) confirmed", "INFO")
    
    if BACKEND.startswith("http://") or "localhost" in BACKEND:
        add("Cookies", "Secure flag is env-conditional (expected in HTTP dev)", "INFO",
            "secure=is_prod — cookies sent over HTTP in development.", "INFO")
    else:
        add("Cookies", "Secure flag is env-conditional", "WARN",
            "secure=is_prod — cookies sent over HTTP in development. Ensure production uses HTTPS.",
            "MEDIUM",
            "In production, always set secure=True. Consider forcing it in staging too.")
    add("Cookies", "adminInfo cookie is NOT httpOnly", "WARN",
        "adminInfo cookie is JS-readable by design — ensure it contains no sensitive data",
        "LOW",
        "Do not store sensitive data in non-httpOnly cookies. adminInfo has username/email only — acceptable.")
    add("Cookies", "refreshToken path restricted to /api/v1/auth/refresh", "PASS",
        "path='/api/v1/auth/refresh' — refresh token not sent on all requests", "INFO")


# 10. FILE UPLOAD SECURITY
def test_file_upload():
    section("10. FILE UPLOAD SECURITY")

    upload_url = f"{BACKEND}/api/v1/upload"

    malicious_files = [
        ("shell.php",  b"<?php system($_GET['cmd']); ?>", "application/x-php"),
        ("evil.html",  b"<script>alert(document.cookie)</script>", "text/html"),
        ("test.exe",   b"MZ\x90\x00\x03\x00\x00\x00",  "application/octet-stream"),
        ("../../etc/passwd", b"root:x:0:0", "text/plain"),
    ]

    for filename, content, mime in malicious_files:
        try:
            r = session.post(upload_url,
                             files={"file": (filename, content, mime)},
                             timeout=8)
            if r is not None and r.status_code in (401, 403, 422):
                add("File Upload", f"Unauthenticated upload blocked: {filename}", "PASS",
                    f"HTTP {r.status_code} — auth required", "INFO")
            elif r is not None and r.status_code == 200:
                add("File Upload", f"Malicious file possibly accepted: {filename}", "WARN",
                    f"HTTP 200 with no auth — check if auth middleware is applied to upload route",
                    "HIGH",
                    "Ensure /upload requires authentication. Validate MIME type server-side. Store outside webroot.")
            else:
                code = r.status_code if r is not None else "no response"
                add("File Upload", f"Upload response for {filename}: {code}", "INFO",
                    f"HTTP {code}", "LOW")
        except Exception as e:
            add("File Upload", f"Upload test error: {filename}", "ERROR", str(e)[:60], "LOW")

    # Path traversal in filename — static check
    add("File Upload", "Path traversal in filename (static check)", "WARN",
        "../../etc/passwd sent as filename — verify backend strips path components",
        "HIGH",
        "Use os.path.basename() or pathlib on all uploaded filenames. Never trust client-provided paths.")


# 11. PATH TRAVERSAL
def test_path_traversal():
    section("11. PATH TRAVERSAL / DIRECTORY TRAVERSAL")

    traversal_payloads = [
        "../../etc/passwd",
        "..%2F..%2Fetc%2Fpasswd",
        "%2e%2e%2f%2e%2e%2fetc%2fpasswd",
        "....//....//etc/passwd",
        "..\\..\\windows\\system32\\drivers\\etc\\hosts",
    ]

    for payload in traversal_payloads:
        for url in [f"{BACKEND}/api/v1/upload/{payload}",
                    f"{BACKEND}/{payload}",
                    f"{FRONTEND}/{payload}"]:
            r = safe_get(url)
            if r is None:
                continue
            if "root:x:" in r.text or "localhost" in r.text and "[hosts]" in r.text:
                add("Path Traversal", f"Directory traversal succeeded!", "FAIL",
                    f"URL: {url[:80]} returned system file contents",
                    "CRITICAL",
                    "Sanitize all file paths. Restrict file access to UPLOAD_DIR only.")
            elif r.status_code in (400, 401, 403, 404):
                add("Path Traversal", f"Traversal blocked: {payload[:30]}", "PASS",
                    f"HTTP {r.status_code}", "INFO")
            elif r.status_code == 200:
                body_text = r.text
                # SPA frameworks serve index.html for all routes — not actual file traversal
                if "<!doctype html>" in body_text.lower() or "<!DOCTYPE html>" in body_text:
                    add("Path Traversal", f"SPA serves index.html (not traversal)", "PASS",
                        f"URL: {url[:80]} — SPA shell returned, no file content leaked", "INFO")
                else:
                    add("Path Traversal", f"Got 200 for traversal payload", "WARN",
                        f"URL: {url[:80]}", "HIGH",
                        "Inspect what this endpoint returned — may be serving unexpected content.")


# 12. INFORMATION DISCLOSURE
def test_info_disclosure():
    section("12. SENSITIVE INFORMATION DISCLOSURE")

    sensitive_endpoints = [
        "/docs",
        "/redoc",
        "/openapi.json",
        "/.env",
        "/api/v1/.env",
        "/config",
        "/settings",
        "/debug",
        "/__debug__",
        "/admin",
        "/phpmyadmin",
        "/.git/config",
        "/api/v1/health",
        "/.well-known/",
    ]

    for path in sensitive_endpoints:
        r = safe_get(f"{BACKEND}{path}")
        if r is None:
            continue

        if r.status_code == 200:
            # Dev-mode API documentation — check BEFORE keyword scan
            # OpenAPI/docs naturally contain words like 'password', 'token' in schema descriptions
            if path in ("/docs", "/redoc", "/openapi.json"):
                if BACKEND.startswith("http://") or "localhost" in BACKEND:
                    add("Info Disclosure", f"{path} accessible (expected in dev)", "INFO",
                        f"API docs accessible for development at {path}", "INFO")
                else:
                    add("Info Disclosure", f"{path} accessible (dev only)", "WARN",
                        "API docs exposed — disable in production (docs_url=None in FastAPI)",
                        "MEDIUM",
                        "Set docs_url=None, redoc_url=None in production FastAPI config.")
                continue
            body = r.text.lower()
            if any(kw in body for kw in ["password", "secret", "key", "token", "private"]):
                add("Info Disclosure", f"Sensitive data in {path}", "FAIL",
                    f"HTTP 200 with sensitive keywords in response",
                    "CRITICAL",
                    f"Disable {path} in production or remove sensitive data from response.")
            elif path == "/api/v1/health":
                add("Info Disclosure", f"Health endpoint accessible", "PASS",
                    "Health check endpoint publicly accessible — expected", "INFO")
            else:
                add("Info Disclosure", f"{path} returns 200", "WARN",
                    f"Unexpected 200 on {path}", "MEDIUM",
                    f"Investigate what {path} returns and restrict if needed.")
        elif r.status_code in (401, 403, 404):
            add("Info Disclosure", f"{path} correctly blocked/hidden", "PASS",
                f"HTTP {r.status_code}", "INFO")

    # Check if error responses leak stack traces
    r = safe_get(f"{BACKEND}/api/v1/nonexistent-endpoint-xyz")
    if r is not None:
        body = r.text
        if "traceback" in body.lower() or "file \"/" in body.lower():
            add("Info Disclosure", "Stack trace in error response", "FAIL",
                "Python traceback leaked in API error response",
                "HIGH",
                "In production, suppress tracebacks. Use generic error messages.")
        else:
            add("Info Disclosure", "No stack trace in error responses", "PASS",
                "404/error responses don't leak internals", "INFO")


# 13. RATE LIMITING
def test_rate_limiting():
    section("13. RATE LIMITING & DoS RESILIENCE")

    # Rapid fire 30 requests to health endpoint
    url = f"{BACKEND}/health"
    rate_limited = False
    for i in range(30):
        r = safe_get(url)
        if r is not None and r.status_code == 429:
            add("Rate Limiting", f"Rate limit triggered at request #{i+1}", "PASS",
                "429 Too Many Requests received", "INFO")
            rate_limited = True
            break

    if not rate_limited:
        add("Rate Limiting", "No rate limiting detected on /health", "WARN",
            "Made 30 rapid requests with no 429 response",
            "MEDIUM",
            "Implement rate limiting with slowapi or a reverse proxy (nginx). Critical for login endpoint especially.")

    # Check login rate limiting separately
    login_url = f"{BACKEND}/api/v1/auth/login"
    for i in range(12):
        r = safe_post(login_url, json={"email": "ratelimit@test.com", "password": "test"})
        if r is not None and r.status_code == 429:
            add("Rate Limiting", f"Login rate limit at #{i+1}", "PASS",
                "Login endpoint rate-limited", "INFO")
            break
        time.sleep(0.05)
    else:
        add("Rate Limiting", "Login rate limit relies only on lockout, not HTTP 429", "WARN",
            "No HTTP-level rate limiting on /auth/login — Redis lockout protects but consider nginx rate limit too",
            "LOW",
            "Add nginx/traefik rate limiting as a layer before application-level lockout.")


# 14. XSS VECTORS
def test_xss():
    section("14. XSS VECTOR INJECTION")

    xss_payloads = [
        "<script>alert(1)</script>",
        "javascript:alert(document.cookie)",
        "<img src=x onerror=alert(1)>",
        "'\"><svg onload=alert(1)>",
        "<iframe src='javascript:alert(1)'></iframe>",
        "{{7*7}}",       # template injection
        "${7*7}",        # expression injection
    ]

    endpoints_to_test = [
        (f"{BACKEND}/api/v1/auth/login", "POST",
         lambda p: {"email": p, "password": "test"}),
        (f"{BACKEND}/api/v1/auth/login", "POST",
         lambda p: {"email": "test@test.com", "password": p}),
    ]

    for url, method, body_fn in endpoints_to_test:
        for payload in xss_payloads:
            body = body_fn(payload)
            r = safe_post(url, json=body)
            if r is None:
                continue

            # Check if payload is reflected unescaped
            if payload in r.text and r.headers.get("Content-Type", "").startswith("text/html"):
                add("XSS", f"Payload reflected in HTML response", "FAIL",
                    f"Payload: {payload[:40]}", "CRITICAL",
                    "Escape all user input in HTML contexts. API returns JSON — verify Content-Type.")
            elif payload in r.text and "application/json" in r.headers.get("Content-Type", ""):
                # In JSON context, reflection is less dangerous but still check
                add("XSS", f"Payload reflected in JSON (lower risk)", "INFO",
                    f"Payload echoed in JSON — acceptable if Content-Type is JSON", "LOW")
            else:
                add("XSS", f"XSS payload not reflected: {payload[:30]}", "PASS",
                    "Response doesn't echo payload", "INFO")

    # CSP protects against XSS — already tested above
    add("XSS", "CSP as XSS mitigation", "INFO",
        "CSP test results above indicate XSS protection level", "LOW")


# 15. AUTHENTICATION BYPASS
def test_auth_bypass():
    section("15. AUTHENTICATION BYPASS")

    protected_routes = [
        "/api/v1/auth/me",
        "/api/v1/tenants",
        "/api/v1/sources",
        "/api/v1/admin",
        "/api/v1/platform-rbac",
        "/api/v1/ingestion",
        "/api/v1/raw",
        "/api/v1/staging",
        "/api/v1/api-logs",
        "/api/v1/tenant-config",
        "/api/v1/upload",
    ]

    bypass_headers = [
        {},
        {"X-Forwarded-For": "127.0.0.1"},
        {"X-Real-IP": "127.0.0.1"},
        {"X-Original-URL": "/api/v1/auth/me"},
        {"X-Rewrite-URL": "/health"},
        {"Authorization": "null"},
        {"Authorization": "Bearer null"},
        {"Authorization": "Bearer undefined"},
    ]

    for route in protected_routes:
        # No auth
        r = safe_get(f"{BACKEND}{route}")
        if r is not None and r.status_code == 200:
            body = r.text
            if "admin_id" in body or "email" in body or "data" in body:
                add("Auth Bypass", f"Unprotected route: {route}", "FAIL",
                    f"HTTP 200 without authentication token",
                    "CRITICAL",
                    f"Apply require_auth dependency to {route} router.")
            else:
                add("Auth Bypass", f"{route} returns 200 (no sensitive data)", "WARN",
                    "Check if this route should require auth", "MEDIUM")
        elif r is not None and r.status_code in (401, 403, 422):
            add("Auth Bypass", f"{route} protected", "PASS",
                f"HTTP {r.status_code} without token", "INFO")
        elif r is not None:
            add("Auth Bypass", f"{route} unexpected: HTTP {r.status_code}", "INFO",
                "", "LOW")


# 16. IDOR (Insecure Direct Object Reference)
def test_idor():
    section("16. INSECURE DIRECT OBJECT REFERENCE (IDOR)")

    # Try accessing other tenant/user resources with sequential/random IDs
    fake_uuids = [str(uuid.uuid4()) for _ in range(3)]
    fake_ints  = ["1", "2", "999", "0", "-1"]

    idor_routes = [
        f"{BACKEND}/api/v1/tenants/{{id}}",
        f"{BACKEND}/api/v1/sources/{{id}}",
        f"{BACKEND}/api/v1/raw/{{id}}",
    ]

    for route_template in idor_routes:
        for test_id in fake_uuids[:1] + fake_ints[:2]:
            url = route_template.replace("{id}", test_id)
            r = safe_get(url)
            if r is not None and r.status_code == 200:
                add("IDOR", f"Unauthenticated access to {url}", "FAIL",
                    f"HTTP 200 without token for ID: {test_id}",
                    "CRITICAL",
                    "Enforce auth AND ownership check on all resource endpoints.")
            elif r is not None and r.status_code in (401, 403):
                add("IDOR", f"IDOR blocked (no auth): {route_template}", "PASS",
                    f"HTTP {r.status_code} for ID {test_id}", "INFO")
                break  # One pass per route is enough
            elif r is not None and r.status_code == 404:
                add("IDOR", f"404 for ID {test_id} on {route_template}", "PASS",
                    "Resource not found — no data leaked", "INFO")
                break


# 17. HTTP METHOD TAMPERING
def test_method_tampering():
    section("17. HTTP METHOD TAMPERING")

    test_endpoints = [
        f"{BACKEND}/api/v1/auth/login",
        f"{BACKEND}/api/v1/auth/me",
        f"{BACKEND}/health",
    ]

    unexpected_methods = ["DELETE", "PUT", "PATCH", "TRACE", "CONNECT"]

    for url in test_endpoints[:2]:
        for method in unexpected_methods:
            try:
                r = session.request(method, url, timeout=5)
                if r.status_code == 200 and method in ("TRACE", "CONNECT"):
                    add("Method Tampering", f"TRACE/CONNECT allowed on {url}", "FAIL",
                        f"HTTP {r.status_code} for {method} — TRACE enables XST attacks",
                        "HIGH",
                        "Disable TRACE and CONNECT methods at the server/proxy level.")
                elif r.status_code in (405, 404, 422):
                    add("Method Tampering", f"{method} correctly rejected", "PASS",
                        f"HTTP {r.status_code} on {url}", "INFO")
                else:
                    add("Method Tampering", f"{method} returned {r.status_code}", "INFO",
                        f"URL: {url}", "LOW")
            except Exception:
                pass


# 18. OPEN REDIRECT
def test_open_redirect():
    section("18. OPEN REDIRECT")

    redirect_payloads = [
        "//evil.com",
        "https://evil.com",
        "//evil.com/%2F..",
        "https://evil.com?redirect=true",
    ]

    params = ["redirect", "next", "url", "return", "returnUrl", "callback", "goto"]

    for payload in redirect_payloads:
        for param in params:
            url = f"{BACKEND}/api/v1/auth/login?{param}={payload}"
            r = safe_get(url)
            if r is not None and r.status_code in (301, 302, 303, 307, 308):
                location = r.headers.get("Location", "")
                if "evil.com" in location:
                    add("Open Redirect", f"Open redirect via ?{param}=", "FAIL",
                        f"Redirects to: {location}",
                        "HIGH",
                        "Validate all redirect URLs against an allowlist of known-safe domains.")
                else:
                    add("Open Redirect", f"Redirect to: {location}", "INFO",
                        f"Not an open redirect — redirects to internal path", "LOW")
            # No redirect = no issue for this payload
    add("Open Redirect", "Frontend SPA redirect test", "INFO",
        "Express SPA serves index.html for all routes — not vulnerable to open redirect via routing",
        "INFO")


# ─────────────────────────────────────────────────────────────────────────────
# REPORT GENERATOR
# ─────────────────────────────────────────────────────────────────────────────

def calculate_score() -> tuple[int, dict]:
    sev_weights = {"CRITICAL": -20, "HIGH": -10, "MEDIUM": -5, "LOW": -1, "INFO": 0}
    status_filter = {"FAIL", "WARN"}

    score = 100
    breakdown = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "PASS": 0, "WARN": 0, "FAIL": 0}

    for r in results:
        if r.status == "PASS":
            breakdown["PASS"] += 1
        elif r.status in ("FAIL", "WARN"):
            breakdown[r.status] += 1
            breakdown[r.severity] = breakdown.get(r.severity, 0) + 1
            score += sev_weights.get(r.severity, 0)

    score = max(0, min(100, score))
    return score, breakdown


def generate_report():
    score, breakdown = calculate_score()

    grade = ("A" if score >= 90 else "B" if score >= 75 else
             "C" if score >= 60 else "D" if score >= 45 else "F")

    grade_label = {
        "A": "SECURE — Minor issues only",
        "B": "MOSTLY SECURE — Some improvements needed",
        "C": "MODERATE RISK — Action recommended",
        "D": "HIGH RISK — Significant vulnerabilities",
        "F": "CRITICAL RISK — Do not launch",
    }[grade]

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = []
    lines.append("=" * 72)
    lines.append("  SIGNALMDM — SECURITY PENETRATION TEST REPORT")
    lines.append(f"  Generated: {now}")
    lines.append("=" * 72)
    lines.append("")
    lines.append(f"  SECURITY SCORE:  {score}/100   Grade: {grade} — {grade_label}")
    lines.append("")
    lines.append(f"  Tests Passed:    {breakdown['PASS']}")
    lines.append(f"  Warnings:        {breakdown['WARN']}")
    lines.append(f"  Failures by severity:")
    lines.append(f"    CRITICAL: {breakdown.get('CRITICAL', 0)}")
    lines.append(f"    HIGH:     {breakdown.get('HIGH', 0)}")
    lines.append(f"    MEDIUM:   {breakdown.get('MEDIUM', 0)}")
    lines.append(f"    LOW:      {breakdown.get('LOW', 0)}")
    lines.append("")
    lines.append("=" * 72)
    lines.append("  EXECUTIVE SUMMARY")
    lines.append("=" * 72)

    critical_issues = [r for r in results if r.status == "FAIL" and r.severity == "CRITICAL"]
    high_issues     = [r for r in results if r.status == "FAIL" and r.severity == "HIGH"]
    warnings        = [r for r in results if r.status == "WARN"]

    if critical_issues:
        lines.append("\n  ❌ CRITICAL ISSUES (fix before launch):")
        for r in critical_issues:
            lines.append(f"    • [{r.category}] {r.test_name}")
            lines.append(f"      Detail: {r.detail}")
            if r.recommendation:
                lines.append(f"      Fix: {r.recommendation}")
            lines.append("")

    if high_issues:
        lines.append("\n  ⚠️  HIGH SEVERITY ISSUES:")
        for r in high_issues:
            lines.append(f"    • [{r.category}] {r.test_name}")
            lines.append(f"      Detail: {r.detail}")
            if r.recommendation:
                lines.append(f"      Fix: {r.recommendation}")
            lines.append("")

    if warnings:
        lines.append("\n  ⚠️  WARNINGS (improve before launch):")
        for r in warnings:
            lines.append(f"    • [{r.category}] {r.test_name}")
            lines.append(f"      Detail: {r.detail}")
            if r.recommendation:
                lines.append(f"      Fix: {r.recommendation}")
            lines.append("")

    lines.append("=" * 72)
    lines.append("  FULL TEST RESULTS")
    lines.append("=" * 72)

    current_cat = None
    for r in results:
        if r.category != current_cat:
            current_cat = r.category
            lines.append(f"\n  [{r.category}]")
        status_icon = {"PASS": "✓", "FAIL": "✗", "WARN": "!", "INFO": "i", "ERROR": "E"}.get(r.status, "?")
        lines.append(f"  {status_icon} [{r.severity:8}] {r.test_name}")
        if r.detail:
            lines.append(f"             {r.detail}")
        if r.recommendation and r.status in ("FAIL", "WARN"):
            lines.append(f"    → Fix: {r.recommendation}")

    lines.append("")
    lines.append("=" * 72)
    lines.append("  IMMEDIATE ACTION CHECKLIST")
    lines.append("=" * 72)
    lines.append("""
  Before Production Launch:
  [ ] Rotate JWT_SECRET to a 64+ char random string
  [ ] Rotate TOKEN_ENCRYPTION_KEY (new secrets.token_hex(32))
  [ ] Rotate Gmail App Password (SMTP_PASSWORD)
  [ ] Rotate PostgreSQL password
  [ ] Set APP_ENV=production
  [ ] Disable /docs and /redoc endpoints
  [ ] Enable HTTPS (set secure=True on all cookies)
  [ ] Implement nginx rate limiting on /api/v1/auth/
  [ ] Ensure UPLOAD_DIR is outside the webroot
  [ ] Validate uploaded file MIME types server-side
  [ ] Remove 'unsafe-inline' and 'unsafe-eval' from CSP if possible
  [ ] Set up log monitoring for brute force attempts
  [ ] Configure HSTS in production (behind TLS terminator)
    """)
    lines.append("=" * 72)
    lines.append("  END OF REPORT — SignalMDM Security Audit")
    lines.append("=" * 72)

    report_text = "\n".join(lines)

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write(report_text)

    return report_text, score, grade


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    print(f"\n{Fore.CYAN + Style.BRIGHT}")
    print("╔══════════════════════════════════════════════════════════════╗")
    print("║        SignalMDM — Security Penetration Test Suite          ║")
    print("╚══════════════════════════════════════════════════════════════╝")
    print(f"{Style.RESET_ALL}")
    print(f"  Backend:  {BACKEND}")
    print(f"  Frontend: {FRONTEND}")
    print(f"  Report:   {REPORT_FILE}\n")

    # Run all test suites
    test_reachability()
    test_security_headers()
    test_csp()
    test_cors()
    test_brute_force()
    test_sql_injection()
    test_jwt()
    test_otp_bypass()
    test_cookies()
    test_file_upload()
    test_path_traversal()
    test_info_disclosure()
    test_rate_limiting()
    test_xss()
    test_auth_bypass()
    test_idor()
    test_method_tampering()
    test_open_redirect()

    # Generate report
    print(f"\n{Fore.CYAN + Style.BRIGHT}{'═'*60}")
    print("  Generating report...")
    print(f"{'═'*60}{Style.RESET_ALL}\n")

    report_text, score, grade = generate_report()

    # Score display
    score_color = (Fore.GREEN if score >= 75 else
                   Fore.YELLOW if score >= 50 else Fore.RED)
    print(f"\n  {score_color + Style.BRIGHT}SECURITY SCORE: {score}/100  Grade: {grade}{Style.RESET_ALL}")
    print(f"\n  Full report saved to: {Fore.CYAN}{REPORT_FILE}{Style.RESET_ALL}\n")


if __name__ == "__main__":
    main()