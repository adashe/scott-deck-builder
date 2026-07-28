"""Authentication helpers for the SCOTT Automation Deck Builder.

Auth model (the "token handoff" pattern):
  1. The portal authenticates the user against Supabase and redirects to
     /scott-deck-builder/auth-callback?token=<supabase_access_token>
  2. api/auth_callback.py verifies that token's signature against
     SUPABASE_JWT_SECRET, and if valid, sets its OWN short-lived httpOnly
     cookie scoped to the deck builder's domain, then redirects to the form
     with the token stripped from the URL.
  3. Every subsequent request (page loads, /api/generate) just checks for
     that cookie — no further calls to Supabase, no JWT re-verification of
     the original Supabase token needed after step 2.

This file is intentionally the ONLY place that knows about the cookie name,
the signing secret, and the verification logic, so both api/index.py and
api/generate.py stay in sync by importing from here rather than duplicating
logic.

Required environment variables (set in Vercel → Settings → Environment Variables):
  SUPABASE_JWT_SECRET   — the JWT secret from Supabase project settings
                          (Settings → API → JWT Secret). Used to verify the
                          signature of the access_token Supabase issues.
  SESSION_SECRET        — a separate, randomly generated secret used to sign
                          this app's OWN session cookie. Do NOT reuse the
                          Supabase secret for this. Generate one with:
                            python -c "import secrets; print(secrets.token_hex(32))"
"""

import os
import json
import time
import hmac
import hashlib
import base64

PORTAL_LOGIN_URL = "https://www.siscc-portal.com/login"

# Name of this app's own session cookie (NOT the Supabase token).
SESSION_COOKIE_NAME = "scott_deck_session"

# How long our own session cookie lasts after a successful handoff.
SESSION_LIFETIME_SECONDS = 8 * 60 * 60  # 8 hours


# ---------------------------------------------------------------------------
# Base64url helpers (JWTs use base64url without padding)
# ---------------------------------------------------------------------------

def _b64url_decode(segment: str) -> bytes:
    padding = "=" * (-len(segment) % 4)
    return base64.urlsafe_b64decode(segment + padding)


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


# ---------------------------------------------------------------------------
# Step 2 verification: validate the Supabase access_token signature
# ---------------------------------------------------------------------------

def verify_supabase_token(token: str) -> dict:
    """Verify a Supabase Auth JWT's signature and expiry.

    Returns the decoded payload dict if valid.
    Raises ValueError with a specific reason if invalid.

    This checks the signature using HS256 against SUPABASE_JWT_SECRET — it
    does NOT call out to Supabase over the network. This is the standard,
    correct way to verify a Supabase access_token server-side.
    """
    secret = os.environ.get("SUPABASE_JWT_SECRET")
    if not secret:
        raise ValueError(
            "SUPABASE_JWT_SECRET is not set in environment variables. "
            "Find it in Supabase: Settings -> API -> JWT Secret."
        )

    if not token or token.count(".") != 2:
        raise ValueError("Malformed token (expected a 3-part JWT)")

    header_b64, payload_b64, sig_b64 = token.split(".")

    # Re-verify the signature ourselves (do not trust the alg header blindly —
    # always force HS256 verification rather than reading the alg from the token).
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual_sig = _b64url_decode(sig_b64)

    if not hmac.compare_digest(expected_sig, actual_sig):
        raise ValueError("Token signature verification failed")

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError):
        raise ValueError("Token payload is not valid JSON")

    exp = payload.get("exp")
    if exp is None:
        raise ValueError("Token has no expiry claim")
    if time.time() >= float(exp):
        raise ValueError("Token has expired")

    return payload


# ---------------------------------------------------------------------------
# Step 3: this app's OWN session cookie (separate from the Supabase token)
# ---------------------------------------------------------------------------

def _session_secret() -> bytes:
    secret = os.environ.get("SESSION_SECRET")
    if not secret:
        raise ValueError(
            "SESSION_SECRET is not set in environment variables. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return secret.encode("utf-8")


def create_session_cookie_value(user_id: str) -> str:
    """Create a signed, self-contained session value: base64(payload).signature

    This is NOT a Supabase token — it's a small token this app mints itself
    after verifying the Supabase token once, so subsequent requests don't
    need to re-verify the original Supabase JWT.
    """
    payload = {
        "sub": user_id,
        "iat": int(time.time()),
        "exp": int(time.time()) + SESSION_LIFETIME_SECONDS,
    }
    payload_b64 = _b64url_encode(json.dumps(payload).encode("utf-8"))
    sig = hmac.new(_session_secret(), payload_b64.encode("ascii"), hashlib.sha256).digest()
    sig_b64 = _b64url_encode(sig)
    return f"{payload_b64}.{sig_b64}"


def verify_session_cookie_value(value: str) -> bool:
    """Return True if the session cookie value is valid and unexpired."""
    try:
        payload_b64, sig_b64 = value.split(".")
    except ValueError:
        return False

    expected_sig = hmac.new(_session_secret(), payload_b64.encode("ascii"), hashlib.sha256).digest()
    actual_sig = _b64url_decode(sig_b64)
    if not hmac.compare_digest(expected_sig, actual_sig):
        return False

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError):
        return False

    exp = payload.get("exp")
    if exp is None or time.time() >= float(exp):
        return False

    return True


def build_session_cookie_header(user_id: str) -> str:
    """Build the Set-Cookie header value for a fresh, valid session."""
    value = create_session_cookie_value(user_id)
    return (
        f"{SESSION_COOKIE_NAME}={value}; "
        f"Max-Age={SESSION_LIFETIME_SECONDS}; "
        f"Path=/; "
        f"HttpOnly; "
        f"Secure; "
        f"SameSite=Lax"
    )


def build_clear_cookie_header() -> str:
    """Build a Set-Cookie header that immediately expires the session cookie."""
    return f"{SESSION_COOKIE_NAME}=deleted; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=None"


def request_has_valid_session(headers) -> bool:
    """Check an incoming request's Cookie header for a valid session.

    `headers` is anything with a .get(name, default) interface, e.g. the
    BaseHTTPRequestHandler's self.headers.
    """
    cookie_header = headers.get("Cookie", "") or ""
    cookies = _parse_cookie_header(cookie_header)
    session_value = cookies.get(SESSION_COOKIE_NAME)
    if not session_value:
        return False
    return verify_session_cookie_value(session_value)


def _parse_cookie_header(cookie_header: str) -> dict:
    cookies = {}
    for part in cookie_header.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies
