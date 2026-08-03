"""Vercel serverless function — /auth-callback

Handles the redirect from the portal after login:

  https://www.siscc-portal.com/scott-deck-builder/auth-callback?token=<supabase_access_token>

Flow:

  1. Read the Supabase access_token from the query string.
  2. Verify its signature + expiry against SUPABASE_JWT_SECRET.
  3. If valid: mint a SHORT-LIVED handoff token (this app's own) and 302 to
       https://scott-deck-builder.vercel.app/?st=<handoff_token>
     We do NOT set the session cookie here. This function is reached on the
     portal domain (siscc-portal.com), so any cookie it set would be scoped to
     the portal and never sent to vercel.app. index.py — running on vercel.app —
     trades the handoff token for the real cookie on the correct domain.
  4. If invalid/missing: show the friendly auth page (Log in / Return), instead
     of silently bouncing to portal login (which produced an oblique loop).

The Supabase token is read once from the query string and discarded; it never
touches a cookie, localStorage, or a log line (only non-secret claims are
logged on rejection, for diagnosis). The handoff token it's exchanged for lives
~2 minutes and is stripped from the URL by index.py on arrival.
"""

import os
import sys
import time
import base64
import traceback
import json as _json
from urllib.parse import urlparse, parse_qs, quote
from http.server import BaseHTTPRequestHandler

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from lib.auth import (
    verify_supabase_token,
    create_handoff_token,
    render_auth_error_page,
    SESSION_TOKEN_URL_PARAM,
)

# Where to send the user after a successful login handoff. Must be the absolute
# vercel.app URL so the browser lands on the domain that will own the cookie.
FORM_URL = "https://scott-deck-builder.vercel.app/"


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        try:
            query = parse_qs(urlparse(self.path).query)
            token_values = query.get("token")
            token = token_values[0] if token_values else None

            if not token:
                return self._serve_auth_error(
                    title="Not signed in",
                    message="No login token was provided. Please log in through the portal.",
                )

            try:
                payload = verify_supabase_token(token)
            except ValueError as e:
                self._log_rejected_token(token, e)
                return self._serve_auth_error(
                    title="Login could not be verified",
                    message="Your login token was rejected. Please log in through the portal again.",
                )

            # Token is valid. Forward identity to vercel.app as a short-lived
            # handoff token; index.py mints the real cookie there.
            user_id = payload.get("sub", "unknown")
            handoff = create_handoff_token(user_id)
            location = f"{FORM_URL}?{SESSION_TOKEN_URL_PARAM}={quote(handoff)}"

            self.send_response(302)
            self.send_header("Location", location)
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()

        except Exception:
            print("ERROR in /auth-callback:", traceback.format_exc(), file=sys.stderr)
            self._serve_auth_error(
                status=500,
                title="Something went wrong",
                message="An unexpected error occurred during login. Please try again.",
            )

    # -- helpers ----------------------------------------------------------

    def _serve_auth_error(self, status: int = 401, title: str = "", message: str = ""):
        body = render_auth_error_page(title=title, message=message)
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _log_rejected_token(self, token: str, err: Exception):
        """Log non-secret token claims to help diagnose rejections. Never logs
        the token itself or the signing secret value."""
        try:
            parts = token.split(".")
            if len(parts) == 3:
                pad = lambda s: s + "=" * (-len(s) % 4)
                hdr = _json.loads(base64.urlsafe_b64decode(pad(parts[0])))
                pay = _json.loads(base64.urlsafe_b64decode(pad(parts[1])))
                print(f"AUTH CALLBACK: token rejected — {err}", file=sys.stderr)
                print(f"AUTH CALLBACK: header alg={hdr.get('alg')}, typ={hdr.get('typ')}", file=sys.stderr)
                print(f"AUTH CALLBACK: payload iss={pay.get('iss')}, aud={pay.get('aud')}, role={pay.get('role')}", file=sys.stderr)
                exp = pay.get("exp")
                print(f"AUTH CALLBACK: exp={exp}, now={int(time.time())}, expired={bool(exp and time.time() >= float(exp))}", file=sys.stderr)
                secret = os.environ.get("SUPABASE_JWT_SECRET", "")
                print(f"AUTH CALLBACK: SUPABASE_JWT_SECRET present={bool(secret)}, length={len(secret)}", file=sys.stderr)
        except Exception as diag_err:
            print(f"AUTH CALLBACK: token rejected — {err} (diagnostic also failed: {diag_err})", file=sys.stderr)
