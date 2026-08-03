"""Authentication helpers for the SCOTT Automation Deck Builder.

Auth model (the "token handoff" pattern), CORRECTED for cross-domain cookies
--------------------------------------------------------------------------
The portal login runs on  www.siscc-portal.com  and the deck builder app runs
on  scott-deck-builder.vercel.app . A cookie set by a response served from the
portal domain is NOT sent on requests to the vercel.app domain. That was the
old bug: auth_callback (reached at siscc-portal.com/scott-deck-builder/
auth-callback) set the session cookie on the *portal* domain, then redirected
to vercel.app, where the cookie was invisible — so the page guard always
bounced the user to login.

The fix is to make the credential travel to vercel.app in the URL and let code
running ON vercel.app mint the cookie there:

  1. Portal authenticates the user against Supabase and redirects to
       .../scott-deck-builder/auth-callback?token=<supabase_access_token>
  2. api/auth_callback.py verifies that Supabase token's signature. If valid it
     mints a SHORT-LIVED handoff token (this app's own, ~2 min) and redirects to
       https://scott-deck-builder.vercel.app/?st=<handoff_token>
     It does NOT try to set the session cookie here — that would land on the
     wrong domain.
  3. api/index.py (on vercel.app) sees no valid cookie but a valid handoff
     token in ?st=. It sets this app's httpOnly session cookie (now correctly
     scoped to vercel.app) and 302-redirects to "/" to strip the token from the
     URL. The follow-up request carries the cookie and the page is served.
  4. Every later request (page loads, /api/generate) just checks the cookie.

Two distinct app-minted tokens, both signed with SESSION_SECRET but NOT
interchangeable (they carry a "typ" claim that is enforced on verification):
  * handoff token  — lives ~2 minutes, only ever appears in a URL, consumed once
                     by index.py and traded for a cookie.
  * session token  — lives 8 hours, only ever lives in the httpOnly cookie.

Required environment variables (Vercel -> Settings -> Environment Variables):
  SUPABASE_JWT_SECRET   — JWT secret from Supabase (Settings -> API -> JWT
                          Secret). Verifies the access_token Supabase issues.
  SESSION_SECRET        — a separate random secret used to sign this app's own
                          handoff + session tokens. Do NOT reuse the Supabase
                          secret. Generate with:
                            python -c "import secrets; print(secrets.token_hex(32))"
"""

import os
import json
import time
import hmac
import hashlib
import base64
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------------------------------------
# Portal URLs. Adjust these to the real portal endpoints.
# (These were temporarily pointed at monday.com during Andrea's redirect trace;
#  restored to the real portal here.)
# ---------------------------------------------------------------------------
PORTAL_LOGIN_URL = "https://www.siscc-portal.com/login"
PORTAL_HOME_URL = "https://www.siscc-portal.com/"

# Name of this app's own session cookie (NOT the Supabase token).
SESSION_COOKIE_NAME = "scott_deck_session"

# How long our own session cookie lasts after a successful handoff.
SESSION_LIFETIME_SECONDS = 8 * 60 * 60  # 8 hours

# How long the one-hop handoff token in the URL stays valid. Keep this small:
# it only has to survive one browser redirect from the portal to vercel.app.
HANDOFF_LIFETIME_SECONDS = 120  # 2 minutes

# Query-string parameter that carries the handoff token from auth_callback to
# index.py. Deliberately different from auth_callback's own ?token= (which is
# the raw Supabase access token) to avoid confusing the two.
SESSION_TOKEN_URL_PARAM = "st"


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

    Verifies HS256 against SUPABASE_JWT_SECRET — no network call to Supabase.
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

    # Re-verify the signature ourselves. Force HS256 rather than trusting the
    # alg header in the token.
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
# This app's own signed tokens (handoff + session). Both signed with
# SESSION_SECRET; distinguished — and NOT interchangeable — via a "typ" claim.
# ---------------------------------------------------------------------------

def _session_secret() -> bytes:
    secret = os.environ.get("SESSION_SECRET")
    if not secret:
        raise ValueError(
            "SESSION_SECRET is not set in environment variables. "
            "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
        )
    return secret.encode("utf-8")


def _sign(payload: dict) -> str:
    """Return  base64url(payload_json).base64url(hmac_sig)  ."""
    payload_b64 = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    sig = hmac.new(_session_secret(), payload_b64.encode("ascii"), hashlib.sha256).digest()
    return f"{payload_b64}.{_b64url_encode(sig)}"


def _verify_signed(value: str, expected_typ: str):
    """Verify signature, expiry and typ. Return payload dict, or None if invalid.

    For backward compatibility, a session token minted before this change (no
    "typ" claim) is still accepted as a session token. Handoff tokens are new,
    so typ=="handoff" is required strictly.
    """
    if not value or value.count(".") != 1:
        return None
    payload_b64, sig_b64 = value.split(".")

    expected_sig = hmac.new(_session_secret(), payload_b64.encode("ascii"), hashlib.sha256).digest()
    try:
        actual_sig = _b64url_decode(sig_b64)
    except Exception:
        return None
    if not hmac.compare_digest(expected_sig, actual_sig):
        return None

    try:
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError):
        return None

    exp = payload.get("exp")
    if exp is None or time.time() >= float(exp):
        return None

    typ = payload.get("typ")
    if expected_typ == "session":
        if typ not in (None, "session"):
            return None
    else:
        if typ != expected_typ:
            return None

    return payload


# --- Session token (lives in the cookie, 8h) -------------------------------

def create_session_cookie_value(user_id: str) -> str:
    """Mint this app's own session token. Goes ONLY in the httpOnly cookie."""
    now = int(time.time())
    return _sign({
        "sub": user_id,
        "typ": "session",
        "iat": now,
        "exp": now + SESSION_LIFETIME_SECONDS,
    })


def verify_session_cookie_value(value: str) -> bool:
    """Return True if the session cookie value is valid and unexpired."""
    return _verify_signed(value, "session") is not None


# --- Handoff token (lives in the URL for one hop, ~2 min) ------------------

def create_handoff_token(user_id: str) -> str:
    """Mint a short-lived handoff token to carry identity to vercel.app in a URL."""
    now = int(time.time())
    return _sign({
        "sub": user_id,
        "typ": "handoff",
        "iat": now,
        "exp": now + HANDOFF_LIFETIME_SECONDS,
    })


def verify_handoff_token(value: str):
    """Return the user_id (sub) if the handoff token is valid, else None."""
    payload = _verify_signed(value, "handoff")
    if payload is None:
        return None
    return payload.get("sub", "unknown")


# ---------------------------------------------------------------------------
# Cookie header builders
# ---------------------------------------------------------------------------

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
    return f"{SESSION_COOKIE_NAME}=deleted; Max-Age=0; Path=/; HttpOnly; Secure; SameSite=Lax"


# ---------------------------------------------------------------------------
# Request-side checks
# ---------------------------------------------------------------------------

def request_has_valid_session(headers) -> bool:
    """Check an incoming request's Cookie header for a valid session cookie.

    Pure predicate: it inspects the cookie only. The URL handoff-token path is
    handled explicitly in api/index.py, because turning a token into a session
    requires SETTING a cookie and redirecting — side effects a boolean check
    shouldn't own.

    `headers` is anything with a .get(name, default) interface, e.g. the
    BaseHTTPRequestHandler's self.headers.
    """
    cookie_header = headers.get("Cookie", "") or ""
    cookies = _parse_cookie_header(cookie_header)
    session_value = cookies.get(SESSION_COOKIE_NAME)
    if not session_value:
        return False
    return verify_session_cookie_value(session_value)


def get_handoff_token_from_path(path: str):
    """Extract the ?st=<handoff_token> value from a request path, or None."""
    try:
        query = parse_qs(urlparse(path).query)
    except Exception:
        return None
    values = query.get(SESSION_TOKEN_URL_PARAM)
    return values[0] if values else None


def _parse_cookie_header(cookie_header: str) -> dict:
    cookies = {}
    for part in cookie_header.split(";"):
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            cookies[k.strip()] = v.strip()
    return cookies


# ---------------------------------------------------------------------------
# Friendly terminal page shown on auth failure — replaces the silent redirect
# loop to the portal login (which was oblique and hard to diagnose). It does
# NOT auto-redirect; the user chooses a button, which breaks any loop.
# ---------------------------------------------------------------------------

def render_auth_error_page(
    title: str = "Session expired",
    message: str = "We couldn't verify your session for the Deck Builder.",
) -> bytes:
    """Return a self-contained HTML page (bytes) with Login / Return buttons."""
    html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="referrer" content="no-referrer">
<title>__TITLE__ · SCOTT Automation Deck Builder</title>
<style>
  :root { --scott-blue:#0b3d6b; --scott-accent:#1f7ac0; --ink:#1a2733; --muted:#5b6b7a; }
  * { box-sizing:border-box; }
  body { margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center;
         font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
         background:#eef2f6; color:var(--ink); padding:24px; }
  .card { background:#fff; max-width:460px; width:100%; border-radius:14px; padding:40px 36px;
          box-shadow:0 10px 40px rgba(11,61,107,.12); text-align:center; }
  .badge { width:56px; height:56px; border-radius:50%; margin:0 auto 20px;
           background:var(--scott-blue); color:#fff; display:flex; align-items:center;
           justify-content:center; font-size:26px; font-weight:700; }
  h1 { font-size:22px; margin:0 0 10px; color:var(--scott-blue); }
  p { color:var(--muted); line-height:1.55; margin:0 0 28px; font-size:15px; }
  .actions { display:flex; flex-direction:column; gap:12px; }
  a.btn { display:block; text-decoration:none; padding:13px 18px; border-radius:9px;
          font-weight:600; font-size:15px; transition:filter .15s ease; }
  a.btn:hover { filter:brightness(.94); }
  .btn-primary { background:var(--scott-accent); color:#fff; }
  .btn-secondary { background:#fff; color:var(--scott-blue); border:1.5px solid #cdd8e2; }
  .foot { margin-top:24px; font-size:12px; color:#9aa8b4; }
</style>
</head>
<body>
  <div class="card">
    <div class="badge">S</div>
    <h1>__TITLE__</h1>
    <p>__MESSAGE__</p>
    <div class="actions">
      <a class="btn btn-primary" href="__LOGIN__">Log in</a>
      <a class="btn btn-secondary" href="__HOME__">Return to main app</a>
    </div>
    <div class="foot">SCOTT Automation Deck Builder</div>
  </div>
</body>
</html>"""
    html = (
        html.replace("__TITLE__", _escape(title))
        .replace("__MESSAGE__", _escape(message))
        .replace("__LOGIN__", _escape(PORTAL_LOGIN_URL))
        .replace("__HOME__", _escape(PORTAL_HOME_URL))
    )
    return html.encode("utf-8")


def _escape(s: str) -> str:
    return (
        str(s)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
